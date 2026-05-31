#!/bin/bash

WATCH_DIR="/var/www/recordings"
BUCKET_NAME="recording-bucket-01"

mkdir -p "$WATCH_DIR/24hr"
mkdir -p "$WATCH_DIR/roll"

echo "$(date) GCS Uploader started"
echo "$(date) Watching: $WATCH_DIR"
echo "$(date) Bucket:   gs://$BUCKET_NAME"

is_file_open() {
    lsof "$1" > /dev/null 2>&1
}

is_stable() {
    local file="$1"
    local size1 size2
    size1=$(stat -c%s "$file" 2>/dev/null)
    sleep 5
    size2=$(stat -c%s "$file" 2>/dev/null)
    [ "$size1" = "$size2" ]
}

while true; do

    for file in "$WATCH_DIR/roll/"*.mp4; do
        [ -e "$file" ] || continue
        filename=$(basename "$file")
        [ -f "${file}.uploaded" ] && continue
        [ ! -s "$file" ] && continue
        flv="${file%.mp4}.flv"
        if [ -f "$flv" ] && is_file_open "$flv"; then continue; fi
        if is_file_open "$file"; then continue; fi
        if ! is_stable "$file"; then echo "$(date) [ROLL] Still growing: $filename"; continue; fi
        echo "$(date) [ROLL] Uploading: $filename"
        gsutil cp "$file" "gs://$BUCKET_NAME/roll/$filename"
        if [ $? -eq 0 ]; then
            echo "$(date) [ROLL] Uploaded: $filename"
            touch "${file}.uploaded"
        else
            echo "$(date) [ROLL] Upload failed: $filename"
        fi
    done

    for flv in "$WATCH_DIR/24hr/"*.flv; do
        [ -e "$flv" ] || continue
        if is_file_open "$flv"; then continue; fi
        if ! is_stable "$flv"; then continue; fi
        mp4="${flv%.flv}.mp4"
        [ -f "$mp4" ] && continue
        echo "$(date) [24HR] Converting: $(basename $flv)"
        ffmpeg -y -i "$flv" -c:v copy -an -movflags +faststart "$mp4" 2>/dev/null
        if [ $? -eq 0 ]; then echo "$(date) [24HR] Converted: $(basename $mp4)"; fi
    done

    for file in "$WATCH_DIR/24hr/"*.mp4; do
        [ -e "$file" ] || continue
        [ -f "${file}.uploaded" ] && continue
        [ ! -s "$file" ] && continue
        flv="${file%.mp4}.flv"
        if [ -f "$flv" ] && is_file_open "$flv"; then continue; fi
        if is_file_open "$file"; then continue; fi
        if ! is_stable "$file"; then continue; fi
        filename=$(basename "$file")
        echo "$(date) [24HR] Uploading: $filename"
        gsutil cp "$file" "gs://$BUCKET_NAME/24hr/$filename"
        if [ $? -eq 0 ]; then
            echo "$(date) [24HR] Uploaded: $filename"
            touch "${file}.uploaded"
            if [ -f "$flv" ]; then rm -f "$flv"; echo "$(date) [24HR] Removed FLV: $(basename $flv)"; fi
        else
            echo "$(date) [24HR] Upload failed: $filename"
        fi
    done

    sleep 10
done
