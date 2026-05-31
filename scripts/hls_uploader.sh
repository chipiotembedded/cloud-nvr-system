#!/bin/bash
HLS_DIR="/var/www/recordings/hls"
BUCKET="gs://recording-bucket-01/live"

echo "$(date) HLS uploader started"

while true; do
    find "$HLS_DIR" -type f \( -name "*.ts" -o -name "*.m3u8" \) | while read FILE; do
        RELATIVE="${FILE#$HLS_DIR/}"
        gcloud storage cp "$FILE" "$BUCKET/$RELATIVE" --quiet
    done
    sleep 30
done
