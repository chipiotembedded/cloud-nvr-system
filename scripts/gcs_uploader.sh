#!/bin/bash

WATCH_DIR="/var/www/recordings"
BUCKET="gs://recording-bucket-0"

echo "Watching (polling mode): $WATCH_DIR"

while true
do
    find "$WATCH_DIR" -type f -name "*.mp4" | while read FILE
    do
        if [[ "$FILE" == *.uploaded ]]; then
            continue
        fi

        SIZE1=$(stat -c%s "$FILE")
        sleep 2
        SIZE2=$(stat -c%s "$FILE")

        if [ "$SIZE1" != "$SIZE2" ]; then
            continue
        fi

        echo "Processing: $FILE"

        if [[ "$FILE" == *"/roll/"* ]]; then
            DEST="roll"
        elif [[ "$FILE" == *"/24hr/"* ]]; then
            DEST="24hr"
        else
            continue
        fi

        gsutil cp "$FILE" "$BUCKET/$DEST/"

        if [ $? -eq 0 ]; then
            mv "$FILE" "$FILE.uploaded"
        fi

    done

    sleep 5
done
