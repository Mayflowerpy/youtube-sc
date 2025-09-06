#!/bin/bash
set -euo pipefail

# Gradually ease-out pixelation over the first 3 seconds.
# Heavy at t=0, almost none by t≈3, then clean for the rest.

if [ $# -eq 0 ]; then
    INPUT_FILE="data/shorts/videos/short_1_1s-29s.mp4"
    OUTPUT_FILE="data/shorts/videos/output_pixelated_easeout.mp4"
elif [ $# -eq 1 ]; then
    INPUT_FILE="$1"
    OUTPUT_FILE="data/shorts/videos/output_pixelated_easeout.mp4"
else
    INPUT_FILE="$1"
    OUTPUT_FILE="$2"
fi

echo "Input : $INPUT_FILE"
echo "Output: $OUTPUT_FILE"

FILTER="scale=w=max(1\,floor(iw/(1+19*if(lt(t\,3)\,(3-t)/3\,0)))):h=max(1\,floor(ih/(1+19*if(lt(t\,3)\,(3-t)/3\,0)))):flags=neighbor:eval=frame,scale=iw:ih:flags=neighbor"

ffmpeg -y -i "$INPUT_FILE" \
  -vf "$FILTER" \
  -c:v libx264 -preset veryfast -crf 18 \
  -c:a copy -pix_fmt yuv420p -movflags +faststart \
  "$OUTPUT_FILE"

echo "Done."
