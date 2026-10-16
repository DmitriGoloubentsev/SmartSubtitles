"""Recheck selected ASR disagreements in bounded audio context, without VAD."""
import os
import json,sys
from pathlib import Path
import soundfile as sf
from faster_whisper import WhisperModel
cfg=json.loads(Path(sys.argv[1]).read_text());w=Path(cfg['work_dir']);ev=[]
import re
def seconds(t):
 h,m,s=t.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)
for block in re.split(r'\n\s*\n',(w/'source.srt').read_text().strip()):
 lines=block.splitlines();a,b=lines[1].split(' --> ');ev.append(dict(id=int(lines[0]),start=seconds(a),end=seconds(b),text=' '.join(lines[2:])))
ids=cfg['context_review_cues'];audio,sr=sf.read(w/'english.wav',dtype='float32')
m=WhisperModel(os.environ.get('ASR_MODEL','large-v3'),device=os.environ.get('ASR_DEVICE','cuda'),compute_type=os.environ.get('ASR_COMPUTE_TYPE','int8_float16'),cpu_threads=6,download_root='.cache/models');rows=[]
for cid in ids:
 c=next(x for x in ev if x['id']==cid);a=max(0,c['start']-3);b=c['end']+3
 segs,_=m.transcribe(audio[int(a*sr):int(b*sr)],language='en',beam_size=5,condition_on_previous_text=False,vad_filter=False,word_timestamps=True);ss=list(segs)
 row=dict(cue=cid,source=c['text'],start=a,text=' '.join(s.text.strip() for s in ss),words=[dict(word=t.word,start=a+t.start,end=a+t.end,probability=t.probability) for s in ss for t in s.words or []]);rows.append(row);print(cid,row['text'],flush=True);(w/'context-asr.json').write_text(json.dumps(rows,indent=2))
