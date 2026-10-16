"""Transcribe EVERY input subtitle interval, without reference prompting.
Outputs evidence only. Never selects or generates delivery subtitles.
"""
import os
import argparse,difflib,hashlib,importlib.metadata,json,re,time
from pathlib import Path
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

def sec(t):
 h,m,s=t.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)
def read_srt(p):
 rows=[]
 for b in re.split(r'\n\s*\n',p.read_text().strip()):
  lines=b.splitlines();a,z=lines[1].split(' --> ')
  rows.append(dict(id=int(lines[0]),start=sec(a),end=sec(z),reference=' '.join(lines[2:])))
 return rows

def norm(s):
 s=re.sub('<[^>]*>','',s).lower().replace('’',"'")
 for a,b in {"i'm":"i am","you're":"you are","we're":"we are","they're":"they are","it's":"it is","that's":"that is","what's":"what is","there's":"there is","he's":"he is","she's":"she is","isn't":"is not","aren't":"are not","wasn't":"was not","weren't":"were not","don't":"do not","doesn't":"does not","didn't":"did not","can't":"cannot","couldn't":"could not","won't":"will not","wouldn't":"would not","shouldn't":"should not","haven't":"have not","hasn't":"has not","hadn't":"had not","i've":"i have","you've":"you have","we've":"we have","they've":"they have","i'll":"i will","you'll":"you will","we'll":"we will","they'll":"they will","he'll":"he will","she'll":"she will","would've":"would have","could've":"could have","should've":"should have","what're":"what are","anymore":"any more","no-one":"no one","staffroom":"staff room"}.items():
  s=re.sub(r'(?<!\w)'+re.escape(a)+r'(?!\w)',b,s)
 return re.findall(r"\w+(?:'\w+)*",s)

def compare(a,b):
 x,y=norm(a),norm(b);prev=list(range(len(y)+1))
 for i,u in enumerate(x,1):
  cur=[i]
  for j,v in enumerate(y,1):cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(u!=v)))
  prev=cur
 diffs=[dict(operation=tag,reference=' '.join(x[i:j]),asr=' '.join(y[k:l])) for tag,i,j,k,l in difflib.SequenceMatcher(None,x,y,autojunk=False).get_opcodes() if tag!='equal']
 return dict(normalized_wer=round(prev[-1]/max(1,len(x)),4),reference_tokens=len(x),differences=diffs)

p=argparse.ArgumentParser();p.add_argument('audio');p.add_argument('subtitles');p.add_argument('output_dir');p.add_argument('--padding',type=float,default=.2);a=p.parse_args();out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
audio,sr=sf.read(a.audio,dtype='float32');assert sr==16000 and audio.ndim==1
rows=read_srt(Path(a.subtitles));settings=dict(model=os.environ.get('ASR_MODEL','large-v3'),compute_type=os.environ.get('ASR_COMPUTE_TYPE','int8_float16'),device=os.environ.get('ASR_DEVICE','cuda'),beam_size=5,language='en',vad_filter=False,condition_on_previous_text=False,initial_prompt=None,padding_seconds=a.padding,reference_used_for_timing_only=True,audio_sha256=hashlib.file_digest(open(a.audio,'rb'),'sha256').hexdigest(),srt_sha256=hashlib.file_digest(open(a.subtitles,'rb'),'sha256').hexdigest(),faster_whisper_version=importlib.metadata.version('faster-whisper'))
sp=out/'settings.json'
if sp.exists():assert json.loads(sp.read_text())==settings,'Different inputs/settings: use another output directory.'
sp.write_text(json.dumps(settings,indent=2));record=out/'entries.jsonl';done={}
if record.exists():
 for line in record.read_text().splitlines():
  z=json.loads(line);done[z['id']]=z
m=WhisperModel(os.environ.get('ASR_MODEL','large-v3'),device=os.environ.get('ASR_DEVICE','cuda'),compute_type=os.environ.get('ASR_COMPUTE_TYPE','int8_float16'),cpu_threads=6,download_root='.cache/models')
for c in rows:
 if c['id'] in done:continue
 st=max(0,c['start']-a.padding);en=min(len(audio)/sr,c['end']+a.padding);t=time.monotonic()
 segs,_=m.transcribe(audio[int(st*sr):int(en*sr)],language='en',beam_size=5,condition_on_previous_text=False,vad_filter=False,word_timestamps=True);ss=list(segs);text=' '.join(s.text.strip() for s in ss);words=[dict(word=w.word,start=round(st+w.start,3),end=round(st+w.end,3),probability=round(w.probability,4)) for s in ss for w in s.words or []]
 z=dict(**c,crop_start=st,crop_end=en,asr=text,words=words,segments=[dict(text=s.text,avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob) for s in ss],**compare(c['reference'],text),elapsed=round(time.monotonic()-t,2))
 with record.open('a') as f:f.write(json.dumps(z,ensure_ascii=False)+'\n')
 done[c['id']]=z;print(f"{c['id']:03}/{len(rows)} WER={z['normalized_wer']:.2f} | {text}",flush=True)
result=[done[c['id']] for c in rows];assert len(result)==len(rows)
(out/'entries.json').write_text(json.dumps(result,indent=2,ensure_ascii=False));(out/'comparison.txt').write_text('\n\n'.join(f"{z['id']:03} {z['start']:.2f}-{z['end']:.2f} WER={z['normalized_wer']:.2f}\nREF: {z['reference']}\nASR: {z['asr']}\nDIFF: {z['differences']}" for z in result))
(out/'coverage.json').write_text(json.dumps(dict(source_entries=len(rows),transcribed_entries=len(result),missing_ids=[],every_entry_transcribed=True,raw_exact_normalized_matches=sum(z['normalized_wer']==0 for z in result),raw_wer_over_025=sum(z['normalized_wer']>.25 for z in result),note='Raw scores include SDH, songs, Latin and timing errors. Agent must review; scores do not prove audibility.'),indent=2))
