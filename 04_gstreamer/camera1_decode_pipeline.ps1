$gst = "C:\Program Files\gstreamer\1.0\msvc_x86_64\bin\gst-launch-1.0.exe"
$rtspUrl = "rtsp://localhost:8554/camera1"

# avdec_h264 decodes compressed H.264 into raw video frames.
# videoconvert adapts raw frames to a format supported by the display sink.
# autovideosink displays the decoded frames.
& $gst -e rtspsrc "location=$rtspUrl" protocols=tcp latency=200 '!' rtph264depay '!' h264parse '!' avdec_h264 '!' videoconvert '!' autovideosink
exit $LASTEXITCODE