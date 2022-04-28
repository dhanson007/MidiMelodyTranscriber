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

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = 'pretty secret key'
UPLOAD_FOLDER = './static/audio_uploads'
STEMS_FOLDER = './static/stems'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STEMS_FOLDER'] = STEMS_FOLDER

def separate_stems(filePath,fileName):
    print("\nseparating stems")
    # sep = Separator('spleeter:2stems')
    print("separator ran")
    # sep.separate_to_file(file_path,output_path,codec='mp3')
    print("we do be having issues if this doesnt show")
    filePath = '"' + filePath + '"'

    outputPath = "C:/Users/Duncan Hanson/Documents/GitHub/capstone2/separated/mdx_q/" + fileName.replace(".wav", "")

    print(filePath)
    print(fileName)

    # WE USE SUBPROCESS NOW::

    demucsCommand = "demucs -d cpu -n mdx_q "

    subprocess.run(demucsCommand+filePath)

    return(outputPath)

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
    melody_tmp_fn = base_fn.replace("/separated/mdx_q/", "/pyin/") + ".lab"
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
    return melody_tmp_fn

def get_song_data(track_id,base_fn):
    
    print("song_id ",track_id)
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
    pitchdf['bpm'] = bpm
    print("nnn",pitchdf[['notearray','duration','notelen']].head(10))
    print("base_fn", base_fn)
    pitch_fn = base_fn.replace("/separated/mdx_q/","/processed/pitchdf/")
    print("pitch_fn: ", pitch_fn)
    pitchdf.to_json(pitch_fn + "_pitchdf.json")
    print (pitchdf)
    return pitchdf, bpm

if __name__ == '__main__':
   for file in os.listdir("C:/Users/Duncan Hanson/Documents/GitHub/capstone2/audio_uploads"):
    if file.endswith(".wav"):
        print(os.path.join("C:/Users/Duncan Hanson/Documents/GitHub/capstone2/audio_uploads", file))
        filePath = "C:/Users/Duncan Hanson/Documents/GitHub/capstone2/audio_uploads/" + file
        outputPath = separate_stems(filePath, file)
        #outputPath = "C:/Users/Duncan Hanson/Documents/GitHub/capstone2/separated/mdx_q/The_Lemon_Song"
        for type in ["vocals", "bass", "other"]:
            target_file = outputPath + "/" + type + ".wav"
            print("targetfile: ", target_file)
            track_id = process_video(target_file)
            pitch_df, bpm = get_song_data(track_id,target_file)
            # pitch_fn = target_file.replace("/separated/mdx_q/","/processed/pitchdf/")
            # pitch_fn = pitch_fn + "/" 
            # print("pitch_fn: ", pitch_fn)
            # pitch_df.to_json(pitch_fn + "_pitchdf.json")
            


    


