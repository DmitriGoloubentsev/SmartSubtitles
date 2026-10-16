from pathlib import Path
import subprocess,json,tempfile,sys
r=Path(__file__).resolve().parent;d=Path(tempfile.mkdtemp(prefix='smart-delivery-test-'));(d/'source.srt').write_text('1\n00:00:00,100 --> 00:00:01,500\nOriginal subtitle.\n');(d/'smart.srt').write_text('1\n00:00:00,200 --> 00:00:01,600\nExample [test only]\n')
def run(args):subprocess.run(args,check=True,stdout=subprocess.DEVNULL)
run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=black:s=160x90:r=10:d=2','-f','lavfi','-i','sine=frequency=440:duration=2','-i',str(d/'source.srt'),'-map','0:v','-map','1:a','-map','2:s','-c:v','libx264','-c:a','flac','-c:s','srt','-metadata:s:a:0','language=eng',str(d/'source.mkv')])
run(['ffmpeg','-v','error','-i',str(d/'smart.srt'),str(d/'smart.ass')])
c=dict(source=str(d/'source.mkv'),output=str(d/'first.mkv'),approved_ass=str(d/'smart.ass'),work_dir=str(d/'first-work'),level='C1',reviewed_level='C1',english_audio_stream=1);cfg=d/'config.json';cfg.write_text(json.dumps(c))
for a in ['mux','verify']:run([sys.executable,str(r/'smart_subtitles_delivery.py'),str(cfg),a])
c.update(source=str(d/'first.mkv'),output=str(d/'rerun.mkv'),work_dir=str(d/'rerun-work'),preserve_streams=[0,1,2]);cfg.write_text(json.dumps(c))
for a in ['mux','verify']:run([sys.executable,str(r/'smart_subtitles_delivery.py'),str(cfg),a])
print('Original delivery and rerun replacing existing smart track: PASS',d)
