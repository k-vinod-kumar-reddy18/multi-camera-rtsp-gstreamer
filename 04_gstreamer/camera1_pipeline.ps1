$projectRoot = Split-Path -Parent $PSScriptRoot
$recordingsDir = Join-Path $projectRoot "05_results\recordings"
$outputFile = Join-Path $recordingsDir "cam1_trim 1_rtsp_output.mp4"
$gst = "C:\Program Files\gstreamer\1.0\msvc_x86_64\bin\gst-launch-1.0.exe"

New-Item -ItemType Directory -Force -Path $recordingsDir | Out-Null
$gstLocation = $outputFile.Replace('\', '/')

& $gst -e rtspsrc location=rtsp://localhost:8554/camera1 protocols=tcp latency=200 '!' rtph264depay '!' h264parse config-interval=-1 '!' video/x-h264,stream-format=avc,alignment=au '!' mp4mux '!' filesink "location=$gstLocation"