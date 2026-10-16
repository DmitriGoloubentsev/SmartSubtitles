"""Independent unprompted local ASR, preserving word uncertainty and timing."""
import os
import argparse,json
from pathlib import Path
from faster_whisper import WhisperModel
p=argparse.ArgumentParser();p.add_argument('audio');p.add_argument('output');a=p.parse_args()
m=WhisperModel(os.environ.get('ASR_MODEL','large-v3'),device=os.environ.get('ASR_DEVICE','cuda'),compute_type=os.environ.get('ASR_COMPUTE_TYPE','int8_float16'),cpu_threads=6,download_root='.cache/models')
segments,info=m.transcribe(a.audio,language='en',beam_size=5,condition_on_previous_text=False,vad_filter=True,word_timestamps=True)
rows=[]
for s in segments:
 rows.append(dict(start=s.start,end=s.end,text=s.text,avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob,words=[dict(word=w.word,start=w.start,end=w.end,probability=w.probability) for w in s.words or []]))
 Path(a.output).write_text(json.dumps(rows,indent=2));print(round(s.end,1),s.text,flush=True)
