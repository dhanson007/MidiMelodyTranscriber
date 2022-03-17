import pretty_midi

def convert_to_midi(note_matrix):
    song1 = pretty_midi.PrettyMIDI()
    # Create an Instrument instance for a cello instrument
    song1_program = pretty_midi.instrument_name_to_program('Acoustic Grand Piano')
    piano = pretty_midi.Instrument(program=song1_program)
    for row in note_matrix:
        song_id = row[0]
        note_number = int(row[4])
        start_time = float(row[2])
        end_time = float(row[3])
        note = pretty_midi.Note(velocity=100, pitch=note_number, start=start_time, end=end_time)
        piano.notes.append(note)
    song1.instruments.append(piano)
    # Write out the MIDI data
    song1.write(song_id + '_midi.mid')
    return 'success'

if __name__ == "__main__":
    fn = 'C:/Users/hanso/capstone/basslemon.wav.lab'
    transcription_file = open(fn)
    note_matrix = []
    for row in transcription_file.readlines():
        row = row.split('\t')
        song_id = 'basslemon'
        start_time = float(row[0].strip(" "))
        end_time =  start_time + float(row[1].strip(" "))
        note_nbr = int(row[2].strip("\n"))
        note_matrix.append([song_id,' ',start_time,end_time,note_nbr])
    convert_to_midi(note_matrix)

    