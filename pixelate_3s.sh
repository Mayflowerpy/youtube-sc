#!/bin/bash

# Pixelate first 3 seconds of video using geq filter
# Usage: ./pixelate_3s.sh input.mp4 output.mp4

if [ $# -eq 0 ]; then
    INPUT_FILE="data/shorts/videos/short_1_1s-29s.mp4"
    OUTPUT_FILE="data/shorts/videos/output_pixelated.mp4"
elif [ $# -eq 1 ]; then
    INPUT_FILE="$1"
    OUTPUT_FILE="data/shorts/videos/output_pixelated.mp4"
else
    INPUT_FILE="$1"
    OUTPUT_FILE="$2"
fi

echo "Pixelating first 3 seconds of: $INPUT_FILE"
echo "Output will be saved to: $OUTPUT_FILE"

# Method: Split video, pixelate first 3s, concatenate (most reliable)
echo "Step 1: Extracting and pixelating first 3 seconds..."
ffmpeg -y -i "$INPUT_FILE" -t 3 \
  -vf "scale=iw/20:ih/20:flags=neighbor,scale=iw*20:ih*20:flags=neighbor" \
  "${OUTPUT_FILE%.*}_first3s.mp4"

echo "Step 2: Extracting remaining video..."
ffmpeg -y -ss 3 -i "$INPUT_FILE" -c:v libx264 -c:a aac -strict experimental "${OUTPUT_FILE%.*}_rest.mp4"

echo "Step 3: Concatenating both parts..."
# Use concat filter instead of concat demuxer for better compatibility
ffmpeg -y \
  -i "${OUTPUT_FILE%.*}_first3s.mp4" \
  -i "${OUTPUT_FILE%.*}_rest.mp4" \
  -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -c:a aac \
  "$OUTPUT_FILE"

# echo "Step 4: Cleaning up temporary files..."
# rm -f "${OUTPUT_FILE%.*}_first3s.mp4" "${OUTPUT_FILE%.*}_rest.mp4" "${OUTPUT_FILE%.*}_concat.txt"

echo "Processing complete: $OUTPUT_FILE"