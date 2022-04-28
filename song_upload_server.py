from __future__ import unicode_literals
from concurrent.futures import process
from flask import Flask, jsonify, render_template, request,json,send_from_directory, flash, url_for, redirect, session,send_file,redirect
from flask_wtf import FlaskForm
from wtforms import SelectField,HiddenField,SubmitField,FieldList,FormField
import vamp
import librosa
import ffmpeg
import os
import pyin
import subprocess
import pretty_midi
from madmom.features.downbeats import DBNDownBeatTrackingProcessor,RNNDownBeatProcessor
import pandas as pd
from functools import wraps
from wtforms import Form, BooleanField, TextField, PasswordField, validators,RadioField
import gc
import math
import requests
import sys,traceback
from pathlib import Path
import pydub
from pydub import AudioSegment
from IPython.display import Audio
import numpy as np
import scipy as sp
import scipy.signal
from scipy.io.wavfile import write
import os.path
import time


# from spleeter.separator import Separator


app = Flask(__name__)
app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = 'pretty secret key'
UPLOAD_FOLDER = './static/audio_uploads'
STEMS_FOLDER = './static/stems'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STEMS_FOLDER'] = STEMS_FOLDER
#dev_mode = 'TRUE'
#print("fn ",Flask(__name__))


# @app.route('/api/<filepath>/')
# def api_get_filepath(filepath):
#     return json.jsonify({
#         'filepath': filepath
#     })

def separate_stems(filePath,fileName):
    print("\nseparating stems")
    # sep = Separator('spleeter:2stems')
    print("separator ran")
    # sep.separate_to_file(file_path,output_path,codec='mp3')
    print("we do be having issues if this doesnt show")

    outputPath = "C:/Users/Duncan Hanson/Documents/GitHub/capstone2/separated/mdx_q/" + fileName.replace(".wav", "") + "/bass.wav"

    print(filePath)

    # WE USE SUBPROCESS NOW::

    demucsCommand = "demucs -d cpu -n mdx_q "

    subprocess.run(demucsCommand+filePath)

    return(outputPath)

    # return render_template('play_audio.html',filename=filePath)



    # subprocessCommand = "spleeter separate -p spleeter:4stems -o output/ "
    # print(filePath)
    # print(subprocessCommand+filePath)
    # subprocess.run(subprocessCommand+filePath)

    # if __name__ == "__main__":   
    #     separator = Separator('spleeter:2stems')
    #     separator.separate_to_file(filePath, outputPath)
    #     print('sep is running')

    # print('subprocess is done now')
# @app.route("/change_audio")
# def change_audio(filePath, sample):
#     return filePath, sample


#reading in stems from demucs separation

def bass_stem_definitions(path_to_bass,path_to_orig):
    [stem,sr1] = librosa.load(path_to_bass)        #### path for bass stem
    [original,sr2] = librosa.load(path_to_orig)                #### path for whole song

    #lowpass filter to remove extraneous signal noise
    lowpass = scipy.signal.butter(2, 5000, 'lowpass', fs=sr1, output='sos')
    filtered = scipy.signal.sosfilt(lowpass, stem)
    return filtered, original,sr1


def vocals_stem_definitions(path_to_vocals,path_to_orig):
    [stem,sr1] = librosa.load(path_to_vocals)        #### path for vocals stem
    [original,sr2] = librosa.load(path_to_orig)                #### path for whole song 

    #highpass filter to remove extraneous signal noise
    highpass = scipy.signal.butter(2, 5000, 'highpass', fs=sr1, output='sos')
    filtered = scipy.signal.sosfilt(highpass, stem)
    return filtered, original,sr1


#process single wav pyin
def process_video(videoid):
    
    base_fn = videoid 
    #decode_fn = 'C:/Users/Duncan Hanson/Documents/GitHub/capstone2/static/stems/bass.wav'
    print("base_fn: ", base_fn)
    try:
        data,rate = librosa.load(base_fn)
    except Exception as bad_file:
        print(bad_file)
        return "failure1"
    
    melody = vamp.collect(data,rate,"pyin:pyin")
    parm = {}
    #plugin, step_size, block_size = vamp.load.load_and_configure(data, rate, "mtg-melodia:melodiaviz",parm)
    plugin, step_size, block_size = vamp.load.load_and_configure(data, rate, "pyin:pyin",parm)
    output_desc = plugin.get_output(5)
    print("od",output_desc)
    output = output_desc["identifier"]
    ff = vamp.frames.frames_from_array(data, step_size, block_size)
    results = vamp.process.process_with_initialised_plugin(ff, rate, step_size, plugin, [output])
    print("results:", results)
    melody_tmp_fn = base_fn + ".lab"
    print("melody_tmp: ", melody_tmp_fn)
    outfile = open(melody_tmp_fn,'w') 
    try:
        result = next(results)
    except Exception as ex:
        print("failure2",ex)
        return "failure3" 

    while True:
    
        start = str(result['notes']['timestamp'])
        freq = result['notes']['values'][0]
        note_nbr = midi = str(round(69 + 12*np.log2(freq/440.)))
        duration = str(result['notes']['duration']) 
        if result['notes']['values'].shape[0] > 1:
            print("multiple notes",videoid)
        outfile.write(start + '\t' + duration + '\t' + note_nbr + '\n')
        #print("??",start + '\t' + duration + '\t' + note_nbr + '\n')
        try:
            
            result = next(results)    
            
        except:
            #outfile.write(start + '\t' + duration + '\t' + note_nbr )
            break
    
    outfile.close()


    #infile = melody_tmp_fn
    #melody_fn = base_fn + '.lab'        
    #audio_to_midi_melodia(infile, melody_fn, 95)
    
    
    return melody_tmp_fn


#convert pyin to midi
def convert_to_midi(note_matrix):
    song1 = pretty_midi.PrettyMIDI()
    # Create an Instrument instance for a cello instrument
    song1_program = pretty_midi.instrument_name_to_program('Acoustic Grand Piano')
    piano = pretty_midi.Instrument(program=song1_program)
    for row in note_matrix:
        song_id = row[0]
        note_number = int(row[3])
        start_time = float(row[1])
        end_time = float(row[2])
        note = pretty_midi.Note(velocity=100, pitch=note_number, start=start_time, end=end_time)
        piano.notes.append(note)
    song1.instruments.append(piano)
    # Write out the MIDI data
    song1.write(song_id + '_midi.mid')

    return 'success'

#Get song data and beat tracker
def get_song_data(track_id,videoid):
    
    print("song_id ",track_id)
    base_fn = videoid
    ###### Figure out the name of the file to open based on the track_id supplied
    fn = track_id
    transcription_file = open(fn)
    pitch_vector=[]
    midipitches = ['C','C#','D','Eb','E','F','F#','G','G#','A','Bb','B']
    for row in transcription_file.readlines():
        row = row.split('\t')
        start_time = float(row[0].strip(" "))
        end_time =  start_time + float(row[1].strip(" "))
        duration = end_time - start_time
        note_nbr = int(row[2].strip("\n"))
        pcname = midipitches[note_nbr % 12]
        octave = int((note_nbr / 12) + 1)
        pitch_vector.append([start_time,duration,note_nbr,pcname,octave])
    pitchdf = pd.DataFrame(pitch_vector,columns=['start','duration','notenbr','pcname','octave'])
    

    beat_vector = []
    nbrbeats = 0

    ######need to implement madmom beat tracker to get bpm
    ######read beat tracker file to get beats 

    #beat_fn = './capstone2/madmombeats/' + videoid.replace("C:/Users/Duncan Hanson/Documents/GitHub/capstone2/separated/mdx_q/Black_Water", "") + '.lab'
    proc = DBNDownBeatTrackingProcessor(beats_per_bar=[3,4], fps=100)
    act = RNNDownBeatProcessor()(base_fn)
    beatarray = proc(act) 
    print("out ",beatarray)
    #outfile = open(beat_fn,'w')
    x = 0
    firststart = 0

    #for c in beatarray:
        #if x == 0:
            #firststart = c[0]
            #x += 1
            #continue
        #outfile.write(str(np.round(firststart,2)))
        #outfile.write('\t')
        #firststart = c[0]
        #outfile.write(str(np.round(c[0],2)))
        #outfile.write('\t')
        #outfile.write(str(np.round(c[1],2)))
       # outfile.write('\t')

        #if x < len(beatarray) -1:
           # outfile.write('\n')
       # x += 1
   # outfile.close()

    
    previous_start = 0
    for row in range(len(beatarray)):
        if row == 0:
            previous_start = float(beatarray[row][0])
            beat_vector.append([float(beatarray[row][0]),float(0),beatarray[row][1],'beat'])
            nbrbeats += 1
        else:
            previous_start = float(beatarray[row-1][0])
            beat_vector.append([float(beatarray[row][0]),float(beatarray[row][0])-previous_start,beatarray[row][1],'beat'])
            nbrbeats += 1

    beatdf = pd.DataFrame(beat_vector,columns=['start','duration','metric_pos','type'])
    beatdf['duration'].fillna(value=beatdf.duration.mean)
    songlen = beatdf.start.max() + beatdf.duration.iloc[beatdf.start.idxmax()]
    bpm = nbrbeats / (songlen / 60) 
    print("songlen ", songlen, bpm)
    
    meanbeat = beatdf['duration'].mean()/4 ##### divide beat into sixteenth notes
    pitchdf['notelen'] = np.ceil(pitchdf['duration'] / meanbeat).astype(int).astype(str) + "n"
    pitchdf['16s'] = np.round(pitchdf['start'] / meanbeat)
    pitchdf['notestart'] = np.floor(np.round(pitchdf.start / meanbeat) / 16).astype(int)
    pitchdf['notestart4'] = (np.floor(np.round(pitchdf.start / meanbeat)  - (pitchdf.notestart) * 16) / 4).astype(int)
    pitchdf['notestart16'] = (np.round(pitchdf.start / meanbeat) - ((pitchdf.notestart * 16) + (pitchdf.notestart4 * 4 ))).astype(int)
    pitchdf['notestartarray'] = pitchdf['notestart'].map(str) + ":" + pitchdf['notestart4'].map(str) + ":" + pitchdf['notestart16'].map(str)
    pitchdf['notename'] = pitchdf['pcname'] + pitchdf['octave'].map(str)
    notearray = pitchdf[['notestartarray','notename','notelen']].to_numpy()
    pitchdf['notearray'] = notearray.tolist()
    print("nnn",pitchdf[['notearray','duration','notelen']].head(10))
    pitchdf.to_json(base_fn + "_pitchdf.json")
    print (pitchdf)
    return pitchdf, bpm


#if __name__ == '__main__':
    
    #outputpath = separate_stems(UPLOAD_FOLDER,)
    #target_wav = bass_stem_definitions(outputpath,path_to_orig)
    target_wav = 'bass.wav'
    rc = process_video(target_wav)
    print("rc",rc,target_wav)

# if __name__ == "__main__":
#     fn = 'C:/Users/Duncan Hanson/Documents/GitHub/capstone2/pyin/basslemon.wav.lab'
#     transcription_file = open(fn)
#     note_matrix = []
#     for row in transcription_file.readlines():
#         row = row.split('\t')
#         song_id = 'bass'
#         start_time = float(row[0].strip(" "))
#         end_time =  start_time + float(row[1].strip(" "))
#         note_nbr = int(row[2].strip("\n"))
#         note_matrix.append([song_id,' ',start_time,end_time,note_nbr])
#     # convert_to_midi(note_matrix)


@app.route('/audio_file_name')
def returnAudioFile(filePath):
    path_to_audio_file = filePath
    return send_file(
         path_to_audio_file, 
         mimetype="audio/wav", 
         as_attachment=True, 
         attachment_filename="test.wav")

@app.route('/upload')
def audio_upload():
    return render_template('upload.html')

@app.route("/")
def landing_load():
    return render_template("melody-editor.html")

@app.route('/explore')
def explore():
    ytid = request.args.get('ytid')
    if ytid == None:
        return render_template('melody-editor.html')
    else:
        return render_template('melody-editor.html',ytid=ytid)
    #return render_template('pixi-explore.html')

@app.route('/get_song',methods=['GET', 'POST'])
def create_time_series():
    song_id = request.args.get('song_id')
    song_title = request.args.get('title')
    chord_type = request.args.get('chord_type')
    midi_id = request.args.get('midi_id')
    print("midi id ",midi_id)
    songtitles,titleoptions = refresh_song_titles()
    if song_id == None:    
        print("using title")
        track_id=songtitles.loc[songtitles.loc[:,'Title']==song_title,'ChordinoFN'].values[0]
    else:
        track_id=songtitles.loc[songtitles.loc[:,'YoutubeID']==song_id,'ChordinoFN'].values[0]
    userid = request.args.get('userid')
    pitchdf,chorddf,secdf,songlen,bpm,beatdf,chordlist = get_song_data(track_id,chord_type,userid,midi_id)
    #firstdownbeat,signature,nbr_sixteenths = get_downbeat(beatdf,chordlist)
    beatlist = beatdf.start.tolist()
    nbr_rows = math.ceil(float(len(beatlist)) / (nbr_sixteenths))
    lyric_lines,lyricdf = get_lyrics(song_id,beatlist,nbr_rows,signature,beatdf)
    #print("ldf",lyricdf)
    lyricl = lyricdf.to_dict(orient='records')
    # if firstdownbeat > 0:
    #        emptybeats = [" " for i in range(signature - firstdownbeat)]
    #        chordlist = emptybeats + chordlist
    #        print("empty",emptybeats)
    print("cdf",pitchdf['notearray'].head())
    cdictlist = []
    notelist = pitchdf['notearray'].tolist()
    chord_tone_array = []
    note_index = 0
    note_beat_measure = (int(notelist[note_index][0].split(':')[0]) * signature) + (int(notelist[note_index][0].split(':')[1]))
    
    
    #print("chordl",chordl)
    pitchl = pitchdf.to_dict(orient='records')
    secl = secdf.to_dict(orient='records')
    #print("secl ",secl)
    D = {'data1' : pitchl, 'songlen' : songlen, 'bpm' : bpm,
         'downbeat': str(firstdownbeat), 'signature': str(signature),'lyrics': lyricl,'cta' : chord_tone_array}
         
    return jsonify(D)


@app.route("/edu")
def edu():
    return render_template("edu.html")



@app.route('/<path:filename>')
def serve_static(filename):
    print('serving static')
    root_dir = app.root_path
    print("root ",root_dir,app.root_path,app.instance_path)
    filedir = os.path.join(root_dir, 'static/')
    print(filedir,filename)
    return send_from_directory(os.path.join(root_dir, 'static/'), filename)


# @app.route('/play_audio')
# def play_audio():
#     return render_template('play_audio.html')

@app.route('/save_melody',methods=['GET','POST'])
def save_melody():
    request_data = request.get_json(silent = True)
    print("requestdata: ",request_data)
    melody_data = request_data["melody_data"]
    song_id = request_data["song_id"]
    print("songid:", song_id)
    note_matrix = []
    for x in range(len(melody_data)):
        end_time = melody_data[x][0] + melody_data[x][1]
        note_nbr = melody_data[x][2]
        note_matrix.append([song_id,melody_data[x][0],end_time,note_nbr])
    convert_to_midi(note_matrix)
    return "success"


@app.route('/save_audio',methods=['GET','POST'])
def save_audio():
    print("request title", request.args.get("title"))
    print("request type", request.args.get("type"))
    file_name = request.args.get("title")
    type = request.args.get("type")
    print("filename", file_name)
    print("type", type)

    if file_name != None:
        # this saves audio files into the "audio_uploads" folder. we will need to delete these in a cache on the webhosting possibly but for now it works fine
        #audio_file = request.files['audio']
        #print('audiofile: ', audio_file.filename)
        #print('newaudiofile: ', audio_file.filename.replace(" ","_").replace(".","_",audio_file.filename.count(".")-1))

        #file_id=audio_file.filename.replace(" ","_").replace(".","_",audio_file.filename.count(".")-1)
        #print("fileid", file_id)
        # file_path = UPLOAD_FOLDER + "/" + file_id
        # output_path = STEMS_FOLDER + "/" + file_id
        #orig_file_path = "C:/Users/Duncan Hanson/Documents/GitHub/capstone2/static/audio_uploads/"+ file_name + ".wav"
        

        #print("file path: ", orig_file_path)
        #print("output path", output_path)
        #audio_file.save(orig_file_path)   

         # convert file to wav for future use

        #orig_file_path = '"' + orig_file_path + '"'

        #output_path = separate_stems(orig_file_path, file_id)
        #output_path = "C:/Users/Duncan Hanson/Documents/GitHub/capstone2/separated/mdx_q/Black_Water/other.wav"

        #if ".mp3" in orig_file_path:
         #   print('yes there is mp3 here')
          # sound = AudioSegment.from_mp3(orig_file_path)
          #  sound.export(orig_file_path.replace(".mp3",".wav"), format="wav")
          # file_id = file_id.replace(".mp3",".wav")
         # orig_file_path = orig_file_path.replace(".mp3",".wav")

        #melody_fn = process_video(output_path)
        #melody_fn = "C:/Users/Duncan Hanson/Documents/GitHub/capstone2/separated/mdx_q/Black_Water/other.wav.lab"

        #pitch_df,bpm = get_song_data(melody_fn,output_path)
        pitch_df = pd.read_json("C:/Users/Duncan Hanson/Documents/GitHub/capstone2/processed/pitchdf/" + file_name + "/" + type + ".wav_pitchdf.json")
        
        bpm = pitch_df.bpm.mean()
        print("bpm: ", bpm)

        #name_of_file=file_id.split(".")[0]
        #bass_path = 'separated/mdx_q/'+ name_of_file + '/bass.wav'
        #vocals_path = 'separated/mdx_q/'+ name_of_file + '/vocals.wav'

        #stereo,sr=binauralizer(alpha,high,bass_path,orig_file_path)
        #binauralized_file_path = 'static/binauralized/' + file_id
        #write(binauralized_file_path,sr,stereo)
        #print(binauralized_file_path)
        pitchl = pitch_df.to_dict(orient='records')
        D = {'data1' : pitchl, 'bpm' : bpm }
        #return render_template('melody-editor.html', ytid=D)      
        return jsonify(D)  
        

    
    # return render_template('play_audio.html', file_path=binauralized_file_path)


#testcase   
#process_video(path_to_bass)
#write("stereo.wav",sr,stereo)



if __name__ == '__main__':
    #app = Flask(__name__)
    #sess = Session()
    dev_mode = 'TRUE'
    if dev_mode == 'TRUE':
        app.run(host='0.0.0.0',port=8100,debug=True)
    else:
        app.run()
        


   

            
