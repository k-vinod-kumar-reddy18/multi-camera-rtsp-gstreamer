$projectRoot = Split-Path -Parent $PSScriptRoot
$ffmpeg = "C:\Users\VinodKumarReddy\Downloads\ffmpeg-8.1.2-essentials_build\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe"
$inputFile = Join-Path $projectRoot "01_video_sources\cam2_trim 1.mp4"

& $ffmpeg -re -i $inputFile -c:v copy -an -f rtsp -rtsp_transport tcp "rtsp://localhost:8554/camera2"