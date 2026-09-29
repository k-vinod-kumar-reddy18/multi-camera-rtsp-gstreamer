cd "C:\Users\VinodKumarReddy\Downloads\multi_camera_rtsp_gstreamer"

& "C:\Users\VinodKumarReddy\Downloads\ffmpeg-8.1.2-essentials_build\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe" -re -stream_loop -1 -i ".\01_video_sources\cam2_trim 1.mp4" -vf "scale=1280:720" -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p -r 15 -f rtsp -rtsp_transport tcp "rtsp://localhost:8554/camera2"