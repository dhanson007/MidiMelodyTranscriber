from __future__ import unicode_literals
from flask import Flask, jsonify, render_template, request,json,send_from_directory, flash, url_for, redirect, session,send_file
import youtube_dl
import vamp
import librosa
#from madmom.audio.chroma import DeepChromaProcessor
#from madmom.features.chords import DeepChromaChordRecognitionProcessor
#from madmom.features.downbeats import DBNDownBeatTrackingProcessor,RNNDownBeatProcessor
import os
import subprocess
import csv
import operator
import numpy as np
import pandas as pd
import statistics
import math
from functools import wraps
import gc
import requests
import music21
import pretty_midi
import sys,traceback
#from audio_to_midi import audio_to_midi_melodia

#DATABASE_URL = os.environ['DATABASE_URL']
#print('db ',DATABASE_URL)
#if 'localhost' in DATABASE_URL:

midipitches = ['C','C#','D','Eb','E','F','F#','G','G#','A','Bb','B']

def get_song_data(track_id):
    
    print("song_id ",track_id)
    ###### Figure out the name of the file to open based on the track_id supplied
    fn = track_id
    transcription_file = open(fn)
    pitch_vector=[]
    for row in transcription_file.readlines():
        row = row.split('\t')
        start_time = float(row[0].strip(" "))
        end_time =  start_time + float(row[1].strip(" "))
        duration = end_time - start_time
        note_nbr = int(row[2].strip("\n"))
        pitch_vector.append([start_time,duration,note_nbr])
    pitchdf = pd.DataFrame(pitch_vector,columns=['start','duration','notenbr'])

    beat_vector = []
    nbrbeats = 0
    ######need to implement madmom beat tracker to get bpm
    ######read beat tracker file to get beats 
    
    
    for row in rows:
        beat_vector.append([float(row[0]),float(row[1])-float(row[0]),row[2],'beat'])
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
    return pitchdf

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = 'pretty secret key'
UPLOAD_FOLDER = './midi_uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#print("fn ",Flask(__name__))
@app.route('/')
def index():
    return render_template('index.html')




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

if __name__ == '__main__':
    #app = Flask(__name__)
    #sess = Session()
    dev_mode = 'TRUE'
    if dev_mode == 'TRUE':
        app.run(host='0.0.0.0',debug=True)
    else:
        app.run()
        
   

            
