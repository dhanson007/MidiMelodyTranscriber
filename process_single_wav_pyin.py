python process_single_wav_pyin#!/usr/bin/env python3
from __future__ import unicode_literals
import vamp
import librosa
import os
import numpy as np

def process_video(videoid):
    
    base_fn = videoid 
    decode_fn = '/Users/hanso/capstone/basslemon.wav'
    try:
        data,rate = librosa.load(decode_fn)
    except Exception as bad_file:
        print(bad_file)
        return "failure"
    
    melody = vamp.collect(data,rate,"pyin:pyin")
    parm = {}
    #plugin, step_size, block_size = vamp.load.load_and_configure(data, rate, "mtg-melodia:melodiaviz",parm)
    plugin, step_size, block_size = vamp.load.load_and_configure(data, rate, "pyin:pyin",parm)
    output_desc = plugin.get_output(5)
    print("od",output_desc)
    output = output_desc["identifier"]
    ff = vamp.frames.frames_from_array(data, step_size, block_size)
    results = vamp.process.process_with_initialised_plugin(ff, rate, step_size, plugin, [output])
    melody_tmp_fn = 'C:/Users/hanso/capstone' + base_fn + '.lab'
    outfile = open(melody_tmp_fn,'w') 
    try:
        result = next(results)
    except Exception as ex:
        print("failure",ex)
        return "failure" 

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


    infile = melody_tmp_fn
    melody_fn = '/Users/hanso/capstone/' + base_fn + '.lab'        
    #audio_to_midi_melodia(infile, melody_fn, 95)
    
    

    return "success"


if __name__ == '__main__':
    
    target_wav = 'basslemon.wav'
    rc = process_video(target_wav)
    print("rc",rc,target_wav)
    
        


    

