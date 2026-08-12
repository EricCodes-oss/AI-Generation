#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/video/白海豚-北方强降雨-新闻口播-无字净版-v5.mp4"

ffmpeg -hide_banner -y \
  -i "$ROOT/video/anchor-c2-pro-short-hair-v5-raw.mp4" \
  -i "$ROOT/media/candidates/pexels-trees-in-windy-weather-19280141.mp4" \
  -i "$ROOT/media/candidates/BiliBili-BV1zCJJzWEun-武汉暴雨现场实拍.mp4" \
  -i "$ROOT/audio/master-voiceover-future-tech-v5.wav" \
  -filter_complex "
    [0:v]crop=1080:1920:0:12,fps=25,scale=1080:1920:flags=lanczos,tpad=stop_mode=clone:stop_duration=0.2,trim=end=52.128,setsar=1,split=4[a0][a1][a2][a3];
    [a0]trim=start=0:end=6.5,setpts=PTS-STARTPTS[s0];
    [a1]trim=start=11.5:end=19.0,setpts=PTS-STARTPTS[s2];
    [a2]trim=start=25.0:end=34.5,setpts=PTS-STARTPTS[s4];
    [a3]trim=start=40.0:end=52.128,setpts=PTS-STARTPTS[s6];

    [1:v]trim=start=0.5:end=5.5,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920:(iw-ow)/2:(ih-oh)/2,fps=25,setsar=1,eq=contrast=1.03:saturation=0.90[s1];
    [2:v]trim=start=0.0:end=6.0,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920:(iw-ow)/2:(ih-oh)/2,fps=25,setsar=1,eq=contrast=1.02:saturation=0.94[s3];
    [2:v]trim=start=30.0:end=35.5,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920:(iw-ow)/2:(ih-oh)/2,fps=25,setsar=1,eq=contrast=1.02:saturation=0.94[s5];

    [s0][s1][s2][s3][s4][s5][s6]concat=n=7:v=1:a=0,trim=end=52.128,format=yuv420p[v];
    [3:a]asetpts=PTS-STARTPTS,apad=pad_dur=0.2,atrim=end=52.128[a]
  " \
  -map "[v]" -map "[a]" \
  -c:v libx264 -preset medium -crf 17 -profile:v high -level 4.1 -pix_fmt yuv420p -r 25 \
  -c:a aac -b:a 192k -ar 48000 -ac 1 -movflags +faststart \
  "$OUT"
