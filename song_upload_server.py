from __future__ import unicode_literals
from flask import Flask, jsonify, render_template, request,json,send_from_directory, flash, url_for, redirect, session,send_file,redirect
from flask_wtf import FlaskForm
from wtforms import SelectField,HiddenField,SubmitField,FieldList,FormField
import librosa
import ffmpeg
import os
import subprocess
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
dev_mode = 'TRUE'
#print("fn ",Flask(__name__))

@app.route("/")
def landing():
    return render_template("landing.html")
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

    outputPath = "static/stems/" + fileName

    print(filePath)

    # WE USE SUBPROCESS NOW::

    demucsCommand = "demucs -d cpu -n mdx_q "

    subprocess.run(demucsCommand+filePath)

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

@app.route('/audio_file_name')
def returnAudioFile(filePath):
    path_to_audio_file = filePath
    return send_file(
         path_to_audio_file, 
         mimetype="audio/wav", 
         as_attachment=True, 
         attachment_filename="test.wav")

@app.route('/audio_upload')
def audio_upload():
    return render_template('upload.html')

@app.route("/")
def landing_load():
    return render_template("landing.html")


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

@app.route('/save_audio',methods=['GET','POST'])
def save_audio():
    print("\nra",request.form,request.data,request.files,app.config)

    file_name = request.form.get('fname')

    if file_name is None:
        # this saves audio files into the "audio_uploads" folder. we will need to delete these in a cache on the webhosting possibly but for now it works fine
        audio_file = request.files['audio']
        print('audiofile: ', audio_file.filename)
        print('newaudiofile: ', audio_file.filename.replace(" ","_").replace(".","_",audio_file.filename.count(".")-1))

        file_id=audio_file.filename.replace(" ","_").replace(".","_",audio_file.filename.count(".")-1)

        # file_path = UPLOAD_FOLDER + "/" + file_id
        # output_path = STEMS_FOLDER + "/" + file_id
        orig_file_path = "static/audio_uploads/"+file_id

        print("file path: ", orig_file_path)
        # print("output path", output_path)
        audio_file.save(orig_file_path)   

        separate_stems(orig_file_path, file_id)
        name_of_file=file_id.split(".")[0]
        bass_path = 'separated/mdx_q/'+ name_of_file + '/bass.wav'

        stereo,sr=binauralizer(alpha,high,bass_path,orig_file_path)
        binauralized_file_path = 'static/binauralized/' + file_id
        write(binauralized_file_path,sr,stereo)
        print(binauralized_file_path)
        time.sleep(10)
        return render_template('play_audio.html', file_path=orig_file_path)         
        

    
    # return render_template('play_audio.html', file_path=binauralized_file_path)





#reading in stems from demucs separation

def binauralizer_definitions(path_to_bass,path_to_orig):
    [stem,sr1] = librosa.load(path_to_bass)        #### path for bass stem
    [original,sr2] = librosa.load(path_to_orig)                #### path for whole song

    #lowpass filter to remove extraneous signal noise
    lowpass = scipy.signal.butter(2, 5000, 'lowpass', fs=sr1, output='sos')
    filtered = scipy.signal.sosfilt(lowpass, stem)
    return filtered, original,sr1


#testcase   
# stereo,sr=binauralizer(alpha,high,path_to_bass,path_to_orig)
# write("stereo.wav",sr,stereo)



if __name__ == '__main__':
    #app = Flask(__name__)
    #sess = Session()
    if dev_mode == 'TRUE':
        app.run(host='0.0.0.0',port=8100,debug=True)
    else:
        app.run()
        
   

            
