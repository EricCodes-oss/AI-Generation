from pathlib import Path
import json, subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
RUN=Path('output/manual-news-2026-08-24-父亲把儿子托上烈马-v04'); RID=RUN.name
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def dur(p): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)],text=True).strip())
open_d=dur(RUN/'audio/parts/opening.wav'); close_d=dur(RUN/'audio/parts/closing.wav'); master_d=dur(RUN/'audio/master-voiceover.wav'); pres_d=dur(RUN/'audio/presenter-only.wav')
open_end=round(open_d+0.35,6); broll_end=round(open_end+45.0,6); close_source_start=round(open_end+0.25,6)
shots=json.loads((RUN/'production/shot-selection.json').read_text())['shots']; segments=[{'type':'anchor','start':0.0,'end':open_end,'script_segment_id':'anchor-opening','shot_id':None,'expected_silence':False}]
t=open_end
for i,s in enumerate(shots,1):
 d=s['target_duration_seconds']; segments.append({'type':'broll','start':round(t,6),'end':round(t+d,6),'script_segment_id':s['script_segment_id'],'shot_id':s['shot_id'],'expected_silence':True}); t+=d
segments.append({'type':'anchor','start':round(t,6),'end':master_d,'script_segment_id':'anchor-closing','shot_id':None,'expected_silence':False})
dump(RUN/'production/timeline.json',{'run_id':RID,'audio_duration_seconds':master_d,'segments':segments})
opening=(RUN/'copy/opening.txt').read_text().strip(); closing=(RUN/'copy/closing.txt').read_text().strip(); ts=[]
for s in segments:
 if s['type']=='anchor': text=opening if s['script_segment_id']=='anchor-opening' else closing; speaker='主持人'; role='presenter'
 else: text='静音插播，无可听源对白。'; speaker='节目音频'; role='source_audio'
 ts.append({'script_segment_id':s['script_segment_id'],'visual_type':s['type'],'audio_role':role,'start':s['start'],'end':s['end'],'lines':[{'speaker':speaker,'text':text}]})
dump(RUN/'production/program-transcript.json',{'run_id':RID,'title_path':'copy/title.txt','output_path':'copy/full-program-transcript.txt','director_approved':True,'segments':ts})
full=['标题：'+(RUN/'copy/title.txt').read_text().strip(),'','【主持人开场】',opening,'','【中段插播】','45秒静音混剪，无可听源对白。','','【主持人结尾】',closing,'']
(RUN/'copy/full-program-transcript.txt').write_text('\n'.join(full),encoding='utf-8')
plan={'run_id':RID,'output':'video/final-clean.mp4','video':{'codec':'h264','width':1080,'height':1920,'fps':25,'pixel_format':'yuv420p'},'audio':{'codec':'aac','sample_rate':48000,'channels':1,'source':'audio/master-voiceover.wav'},'edit':{'presenter_source':'video/anchor-generated.mp4','broll_source':'media/approved/grassland-youth-montage.mp4','opening_avatar_source':[0.0,open_end],'closing_avatar_source':[close_source_start,pres_d],'broll_target':[open_end,broll_end],'source_audio_used':False,'background_music_used':False,'approved_silent_broll':True,'text_overlay_used':False,'subtitles_used':False,'reverse_loop_pingpong':False,'broll_shot_count':len(shots),'broll_shot_durations_seconds':[s['target_duration_seconds'] for s in shots]}}
dump(RUN/'production/render-plan.json',plan)
sh=f'''#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for f in "$ROOT/video/anchor-generated.mp4" "$ROOT/media/approved/grassland-youth-montage.mp4" "$ROOT/audio/master-voiceover.wav"; do test -s "$f"; done
ffmpeg -hide_banner -y -i "$ROOT/video/anchor-generated.mp4" -i "$ROOT/media/approved/grassland-youth-montage.mp4" -i "$ROOT/audio/master-voiceover.wav" \\
-filter_complex "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=25,format=yuv420p,split=2[ao][ac];[ao]trim=start=0:end={open_end},setpts=PTS-STARTPTS[open];[1:v]trim=start=0:end=45.0,setpts=PTS-STARTPTS,setsar=1,fps=25,format=yuv420p[insert];[ac]trim=start={close_source_start}:end={pres_d},setpts=PTS-STARTPTS[close];[open][insert][close]concat=n=3:v=1:a=0[vout]" \\
-map "[vout]" -map 2:a:0 -t {master_d} -c:v libx264 -preset medium -crf 18 -profile:v high -level 4.1 -pix_fmt yuv420p -r 25 -c:a aac -b:a 192k -ar 48000 -ac 1 -movflags +faststart "$ROOT/video/final-clean.mp4"
'''
(RUN/'production/render.sh').write_text(sh); (RUN/'production/render.sh').chmod(0o755)
print(json.dumps({'master':master_d,'open_end':open_end,'broll_end':broll_end,'close_source_start':close_source_start,'presenter':pres_d},ensure_ascii=False))
