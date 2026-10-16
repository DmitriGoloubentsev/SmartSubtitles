"""Mechanical smart-subtitle delivery. Never selects or writes caption content.
Uses only the Python standard library plus ffmpeg/ffprobe. Originals are never deleted.
"""
import argparse,datetime,hashlib,json,subprocess
from pathlib import Path

def call(args):return subprocess.check_output(args,text=True)
def probe(p):return json.loads(call(['ffprobe','-v','error','-show_streams','-show_format','-show_chapters','-of','json',str(p)]))
def digest(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def streamhash(p,i):return call(['ffmpeg','-v','error','-i',str(p),'-map',f'0:{i}','-c','copy','-f','streamhash','-hash','sha256','-']).strip().split('=')[-1].strip()
def ass_events(t):return [line.split(':',1)[1].strip() for line in t.splitlines() if line.startswith('Dialogue:')]
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('config');ap.add_argument('action',choices=['mux','verify']);a=ap.parse_args();cfg=json.loads(Path(a.config).read_text())
 src=Path(cfg['source']).resolve();dst=Path(cfg['output']).resolve();ass=Path(cfg['approved_ass']).resolve();w=Path(cfg['work_dir']).resolve();w.mkdir(parents=True,exist_ok=True)
 assert src!=dst,'Never overwrite the source';assert cfg['level']==cfg['reviewed_level'],'A level change needs fresh manual review';assert ass_events(ass.read_text()),'No agent-approved ASS events'
 q=probe(src);by={s['index']:s for s in q['streams']};keep=cfg.get('preserve_streams',[s['index'] for s in q['streams']]);assert keep and len(set(keep))==len(keep) and all(i in by for i in keep)
 streams=[by[i] for i in keep];audio=[i for i in keep if by[i]['codec_type']=='audio'];subs=[i for i in keep if by[i]['codec_type']=='subtitle'];en=cfg['english_audio_stream'];assert en in audio
 if a.action=='mux':
  assert not dst.exists(),'Use a fresh output name; existing deliverables are not overwritten';dst.parent.mkdir(parents=True,exist_ok=True)
  cmd=['ffmpeg','-nostdin','-v','error','-n','-i',str(src),'-i',str(ass)]
  for i in keep:cmd+=['-map',f'0:{i}']
  cmd+=['-map','1:0','-map_metadata','0','-map_chapters','0','-c','copy','-disposition:a','0',f'-disposition:a:{audio.index(en)}','default','-disposition:s','0',f'-disposition:s:{len(subs)}','default',f'-metadata:s:s:{len(subs)}','language=eng',f'-metadata:s:s:{len(subs)}',f'title=Smart English — {cfg["level"]} — words, names and brief definitions','-max_interleave_delta','0',str(dst)]
  save(w/'mux-command.json',cmd);subprocess.run(cmd,check=True);save(w/'source-info.json',q);return
 p=probe(dst);save(w/'output-info.json',p);assert len(p['streams'])==len(keep)+1
 assert [s['index'] for s in p['streams'] if s['codec_type']=='audio' and s['disposition']['default']]==[keep.index(en)]
 assert [s['index'] for s in p['streams'] if s['codec_type']=='subtitle' and s['disposition']['default']]==[len(keep)]
 assert not p['streams'][-1]['disposition'].get('forced',0)
 assert q.get('chapters',[])==p.get('chapters',[]),'Chapters changed'
 assert abs(float(q['format']['duration'])-float(p['format']['duration']))<.1,'Duration changed'
 proof=[]
 for j,s in enumerate(streams):
  z=p['streams'][j];assert s['codec_type']==z['codec_type'] and s['codec_name']==z['codec_name']
  for key in ['channels','channel_layout','sample_rate','width','height','extradata_size']:
   assert s.get(key)==z.get(key),(j,key)
  for key,value in s.get('tags',{}).items():
   if key.lower() in ['language','title','filename','mimetype']:assert z.get('tags',{}).get(key)==value,(j,key)
  if s['codec_type'] in ['video','audio','data']:
   x,y=streamhash(src,s['index']),streamhash(dst,j);assert x==y,(j,'payload changed');proof.append(dict(source_stream=s['index'],output_stream=j,sha256=x,equal=True))
  elif s['codec_type']=='subtitle':
   if s['codec_name'] in ['subrip','ass','ssa','webvtt','mov_text']:
    vals=[call(['ffmpeg','-v','error','-i',str(f),'-map',f'0:{i}','-f','srt','-']) for f,i in [(src,s['index']),(dst,j)]];assert vals[0]==vals[1],(j,'subtitle timing/text changed')
   else:
    assert streamhash(src,s['index'])==streamhash(dst,j),(j,'bitmap subtitle changed')
  elif s['codec_type']=='attachment':
   # Attached font/image bytes are codec extradata, not ordinary media packets.
   vals=[]
   for f,i in [(src,s['index']),(dst,j)]:
    data=json.loads(call(['ffprobe','-v','error','-select_streams',str(i),'-show_entries','stream=extradata','-show_data','-of','json',str(f)]));vals.append(data['streams'][0]['extradata'])
   assert vals[0]==vals[1],(j,'attachment changed')
  else:raise ValueError('Unsupported stream type requires explicit verification: '+s['codec_type'])
 embedded=call(['ffmpeg','-v','error','-i',str(dst),'-map',f'0:{len(keep)}','-c','copy','-f','ass','-'])
 assert ass_events(embedded)==ass_events(ass.read_text()),'Smart ASS events changed'
 # Also compare actual ASS styling, ignoring muxer-added metadata and event format header.
 assert [l for l in embedded.splitlines() if l.startswith(('Style:','PlayResX:','PlayResY:'))]==[l for l in ass.read_text().splitlines() if l.startswith(('Style:','PlayResX:','PlayResY:'))]
 log=w/'final-decode.log'
 with log.open('w') as f:result=subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-threads','2','-i',str(dst),'-map','0:v','-map','0:a','-f','null','-'],stdout=subprocess.DEVNULL,stderr=f)
 assert result.returncode==0 and not log.read_text().strip(),f'Full decode failed; retain source and inspect {log}'
 save(w/'final-verification.json',dict(passed=True,checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source=str(src),output=str(dst),source_sha256=digest(src),output_sha256=digest(dst),approved_ass_sha256=digest(ass),preserved_streams=keep,original_av_payloads=proof,original_subtitle_text_and_timing_equal=True,attachments_preserved=True,chapters_equal=True,embedded_ass_exact_events=True,embedded_ass_style_equal=True,default_audio=keep.index(en),default_subtitle=len(keep),full_video_and_all_audio_decode_passed=True,decode_error_log_empty=True))
 print('PASS: preserved streams, defaults, ASS events/style, chapters, full audio/video decode.')
if __name__=='__main__':main()
