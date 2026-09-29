cd "C:\Users\VinodKumarReddy\Downloads\multi_camera_rtsp_gstreamer"

gst-launch-1.0 rtspsrc location=rtsp://localhost:8554/camera1 protocols=tcp latency=200 ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink