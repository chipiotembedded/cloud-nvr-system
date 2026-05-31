#!/bin/bash
# Runs every 5 minutes, converts any FLV that has no matching MP4
while true; do
    for flv in /var/www/recordings/24hr/*.flv; do
        [ -e "$flv" ] || continue
        mp4="${flv%.flv}.mp4"
        [ -f "$mp4" ] && continue
        # Check if FLV is still open (being recorded)
        lsof "$flv" > /dev/null 2>&1 && continue
        echo "$(date) Recovering failed conversion: $(basename $flv)"
        ffmpeg -y \
            -fflags +genpts+igndts \
            -err_detect ignore_err \
            -i "$flv" \
            -c:v copy -an \
            -movflags +faststart \
            "$mp4" 2>/dev/null
        if [ -f "$mp4" ]; then
            echo "$(date) Recovered: $(basename $mp4)"
        else
            echo "$(date) Recovery failed: $(basename $flv)"
        fi
    done
    sleep 300
done
