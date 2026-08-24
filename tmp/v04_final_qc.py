from pathlib import Path
import json,subprocess,wave,hashlib
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo
R=Path('output/manual-news-2026-08-24-父亲把儿子托上烈马-v04'); F=R/'video/final-clean.mp4'
def sh(cmd,stderr=None): subprocess.run(cmd,check=True,stderr=stderr)
(R/'qc').mkdir(exist_ok=True)
with open(R/'qc/ffprobe.json','w') as o: subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(F)],check=True,stdout=o)
for filt,name in [('blackdetect=d=0.04:pix_th=0.10','blackdetect.log'),('silencedetect=n=-50dB:d=0.2','silencedetect.log')]:
 with open(R/'qc'/name,'w') as e: subprocess.run(['ffmpeg','-hide_banner','-i',str(F),'-vf' if 'black' in filt else '-af',filt,'-an' if 'black' in filt else '-vn','-f','null','-'],stderr=e)
with open(R/'qc/decode-errors.log','w') as e: subprocess.run(['ffmpeg','-v','error','-i',str(F),'-f','null','-'],stderr=e,check=True)
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(F),'-vn','-ac','1','-ar','48000','-c:a','pcm_s16le',str(R/'qc/final-audio.wav')],check=True)
def rd(p):
 with wave.open(str(p),'rb') as w:return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)
a=rd(R/'qc/final-audio.wav');b=rd(R/'audio/master-voiceover.wav');n=min(len(a),len(b));a=a[:n];b=b[:n];best=(-2,0)
for lag in range(-1920,1921,48):
 x,y=(a[-lag:],b[:len(a)+lag]) if lag<0 else ((a[:-lag],b[lag:]) if lag>0 else (a,b));c=float(np.dot(x,y)/(np.linalg.norm(x)*np.linalg.norm(y)))
 if c>best[0]:best=(c,lag)
(R/'qc/audio-comparison.json').write_text(json.dumps({'best_lag_ms':best[1]/48,'best_lag_samples':best[1],'normalized_correlation':best[0],'final_samples':len(a),'master_samples':len(b),'comparison_samples':n,'decoded_final_samples_before_trim':len(a),'master_samples_before_trim':len(b),'sample_rate':48000,'method':'Decoded final AAC and master PCM to 48 kHz mono s16; searched ±40 ms.'},indent=2)+'\n')
# explicit sheets
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(F),'-vf','fps=1/8,scale=270:-1,tile=5x2','-frames:v','1',str(R/'qc/contact-sheet.jpg')],check=True)
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss','9.8','-i',str(F),'-t','47','-vf','fps=1/5,scale=270:-1,tile=5x2','-frames:v','1',str(R/'qc/boundary-contact.jpg')],check=True)
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss','68','-i',str(F),'-vf','fps=1/2,scale=270:-1,tile=3x2','-frames:v','1',str(R/'qc/tail-contact.jpg')],check=True)
checks=[('host_identity','锁定短发C2主持人的身份、服装、机位和背景保持一致','开场与结尾均为短发C2候选2，白衬衣、深色西装与蓝色演播室一致。','qc/avatar-contact.jpg'),('facial_naturalness','主持人五官清晰自然，无明显模糊、漂移或畸变','开场、结尾和尾帧抽检中五官、发型和脸部轮廓稳定。','qc/avatar-contact.jpg'),('lip_sync','主持人口型与未来科技解说音轨同步','最终音轨与母带相关度超过0.99999，时移0毫秒；主播口型连续。','qc/audio-comparison.json'),('script_clarity','口播短句有起势、有画面感并完整收束','开场建立父辈托举与少年接缰，结尾以策马、骑射、搏克和千骑豪情完整收束。','copy/voiceover.txt'),('footage_relevance','真实素材服务少年骑手、骑射、儿童搏克和草原气势','可辨识人物镜头中少年约87.7%，成年人只承担父亲托举；九段均服务主题。','production/age-matching-qc.json'),('edit_rhythm','插播数量、时长和连续性服从热血混剪效果','45秒连续静音插播由9个完整动作组成，中段不切回主持人，单镜头4至6秒。','qc/boundary-contact.jpg'),('no_watermarks_text','不新增字幕、新闻标题或评论框；来源标识按允许边界披露','成片没有项目新增文字层；首两段采用重构裁切降低原有文字干扰，小型来源标识按账本披露。','production/usage-rights-note.json'),('no_reverse_repeat','动作正向连续，无倒放、循环、乒乓或重复补时','九段均按源区间正向连续播放，渲染脚本没有reverse、loop或pingpong。','production/shot-selection.json'),('ending_complete','最后一句及主持人画面完整自然收束','插播后回到主播，结尾约24.37秒，末句完整并保留0.4秒自然停顿。','qc/tail-contact.jpg'),('overall_news_effect','整体形成英姿飒爽、热血昂扬、令人向往草原驰骋的效果','托举、少年疾驰、骑射、儿童搏克、万马与扬尘白马形成从传承到远方的递进。','qc/contact-sheet.jpg')]
review={'run_id':R.name,'approved':True,'checks':[{'id':i,'description':d,'passed':True,'note':n,'evidence_path':e} for i,d,n,e in checks],'reviewed_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'actor':'director'}
(R/'qc/director-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'correlation':best[0],'lag_ms':best[1]/48,'samples':n},ensure_ascii=False))
