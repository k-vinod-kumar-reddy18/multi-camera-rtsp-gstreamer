cd "C:\Users\VinodKumarReddy\Downloads\multi_camera_rtsp_gstreamer"

gst-launch-1.0 rtspsrc location=rtsp://localhost:8554/camera3 protocols=tcp latency=200 ! rtph264depay ! avdec_h264 ! videoconvert ! x264enc tune=zerolatency speed-preset=veryfast ! h264parse ! mp4mux ! filesink location=".\05_results\recordings\camera3_rtsp_output.mp4"