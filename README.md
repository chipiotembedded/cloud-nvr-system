1. #To run the recorder.py
ffmpeg -f dshow -i video="USB2.0 HD UVC WebCam" -c:v libx264 -preset veryfast -crf 26 -profile:v high -level 4.1 -pix_fmt yuv420p -g 300 -keyint_min 30 -f flv rtmp://34.93.215.198/live/stream

2. to start ffmpeg(for all 3 CCTV - rollplayback)(tip-if cmd don't use &) 
a.) 192.168.1.104
"C:\ffmpeg\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe" -rtsp_transport tcp -i "rtsp://admin:12345@192.168.1.104:554/stream1" -c:v libx264 -preset veryfast -crf 25 -an -f flv rtmp://35.244.35.20:1935/live/cam104
b.) 192.168.1.105
    & "C:\ffmpeg\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe" -rtsp_transport tcp -i "rtsp://admin:12345@192.168.1.105:554/stream1" -c:v libx264 -preset veryfast -crf 25 -an -f flv rtmp://35.244.35.20:1935/live/cam105    
c.) 192.168.1.106
    & "C:\ffmpeg\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe" -rtsp_transport tcp -i "rtsp://admin:12345@192.168.1.106:554/stream1" -c:v libx264 -preset veryfast -crf 25 -an -f flv rtmp://35.244.35.20:1935/live/cam106


3. to start watcher script
bash /home/cloud_user/gcs_uploader.sh

4. to open roll playback html page (frontend)
nano rollplayback.html

5. to open Flask (backend)
nano playback_server.py

6. to run the html page
python3 playback_server.py

7. to open nginx script
sudo nano /etc/nginx/nginx.conf
