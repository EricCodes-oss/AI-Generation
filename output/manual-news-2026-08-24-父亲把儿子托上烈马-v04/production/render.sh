#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for f in "$ROOT/video/anchor-generated.mp4" "$ROOT/media/approved/grassland-youth-montage.mp4" "$ROOT/audio/master-voiceover.wav"; do test -s "$f"; done
ffmpeg -hide_banner -y -i "$ROOT/video/anchor-generated.mp4" -i "$ROOT/media/approved/grassland-youth-montage.mp4" -i "$ROOT/audio/master-voiceover.wav" \
-filter_complex "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=25,format=yuv420p,tpad=stop_mode=clone:stop_duration=0.2,split=2[ao][ac];[ao]trim=start=0:end=10.857042,setpts=PTS-STARTPTS[open];[1:v]trim=start=0:end=45.0,setpts=PTS-STARTPTS,setsar=1,fps=25,format=yuv420p[insert];[ac]trim=start=11.107042:end=35.473042,setpts=PTS-STARTPTS[close];[open][insert][close]concat=n=3:v=1:a=0[vout]" \
-map "[vout]" -map 2:a:0 -t 80.223042 -c:v libx264 -preset medium -crf 18 -profile:v high -level 4.1 -pix_fmt yuv420p -r 25 -c:a aac -b:a 192k -ar 48000 -ac 1 -movflags +faststart "$ROOT/video/final-clean.mp4"
