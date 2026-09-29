import os
import signal
import subprocess
import time


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_DIR = r"C:\Users\VinodKumarReddy\Downloads\multi_camera_rtsp_gstreamer"

MEDIAMTX_EXE = (
    r"C:\Users\VinodKumarReddy\Downloads"
    r"\mediamtx_v1.19.3_windows_amd64"
    r"\mediamtx.exe"
)

FFMPEG_EXE = (
    r"C:\Users\VinodKumarReddy\Downloads"
    r"\ffmpeg-8.1.2-essentials_build"
    r"\ffmpeg-8.1.2-essentials_build"
    r"\bin\ffmpeg.exe"
)

GSTREAMER_EXE = (
    r"C:\Program Files"
    r"\gstreamer\1.0\msvc_x86_64"
    r"\bin\gst-launch-1.0.exe"
)

MEDIAMTX_CONFIG = os.path.join(
    PROJECT_DIR,
    "02_rtsp_server",
    "mediamtx.yml"
)

VIDEO_DIR = os.path.join(
    PROJECT_DIR,
    "01_video_sources"
)

RESULTS_DIR = os.path.join(
    PROJECT_DIR,
    "05_results",
    "recordings"
)

os.makedirs(RESULTS_DIR, exist_ok=True)


# ============================================================
# CAMERA CONFIGURATION
# ============================================================

CAMERAS = [
    {
        "name": "camera1",
        "video": "cam1_trim 1.mp4"
    },
    {
        "name": "camera2",
        "video": "cam2_trim 1.mp4"
    },
    {
        "name": "camera3",
        "video": "cam3_trim.mp4"
    }
]


# ============================================================
# CHECK PROGRAMS AND FILES
# ============================================================

def check_requirements():

    print()
    print("=" * 60)
    print("CHECKING REQUIREMENTS")
    print("=" * 60)

    programs = {
        "MediaMTX": MEDIAMTX_EXE,
        "FFmpeg": FFMPEG_EXE,
        "GStreamer": GSTREAMER_EXE,
        "MediaMTX config": MEDIAMTX_CONFIG
    }

    for name, path in programs.items():

        if os.path.exists(path):
            print(f"[OK] {name}")
        else:
            print(f"[ERROR] {name} not found:")
            print(path)
            return False

    print()

    for camera in CAMERAS:

        video_path = os.path.join(
            VIDEO_DIR,
            camera["video"]
        )

        if os.path.exists(video_path):

            print(
                f"[OK] {camera['name']}: "
                f"{camera['video']}"
            )

        else:

            print(
                f"[ERROR] Video not found for "
                f"{camera['name']}:"
            )

            print(video_path)

            return False

    print()

    return True


# ============================================================
# START MEDIAMTX
# ============================================================

def start_mediamtx():

    print("=" * 60)
    print("STARTING MEDIAMTX")
    print("=" * 60)

    process = subprocess.Popen(
        [
            MEDIAMTX_EXE,
            MEDIAMTX_CONFIG
        ],
        cwd=PROJECT_DIR
    )

    time.sleep(3)

    if process.poll() is not None:

        raise RuntimeError(
            "MediaMTX stopped unexpectedly."
        )

    print(
        f"MediaMTX started. PID: {process.pid}"
    )

    print()

    return process


# ============================================================
# START FFMPEG
# ============================================================

def start_ffmpeg(camera):

    name = camera["name"]

    video_path = os.path.join(
        VIDEO_DIR,
        camera["video"]
    )

    rtsp_url = (
        f"rtsp://localhost:8554/{name}"
    )

    print(
        f"Starting FFmpeg for {name}..."
    )

    process = subprocess.Popen(
        [
            FFMPEG_EXE,

            # Real-time playback
            "-re",

            # Input video
            "-i",
            video_path,

            # Copy H264 without re-encoding
            "-c:v",
            "copy",

            # No audio
            "-an",

            # RTSP output
            "-f",
            "rtsp",

            # TCP
            "-rtsp_transport",
            "tcp",

            # RTSP URL
            rtsp_url
        ],
        cwd=PROJECT_DIR
    )

    print(
        f"FFmpeg {name} started. "
        f"PID: {process.pid}"
    )

    return process


# ============================================================
# START GSTREAMER
# ============================================================

def start_gstreamer(camera):

    name = camera["name"]

    rtsp_url = (
        f"rtsp://localhost:8554/{name}"
    )

    video_name = os.path.splitext(
        camera["video"]
    )[0]

    output_file = os.path.join(
        RESULTS_DIR,
        f"{video_name}_rtsp_output.mp4"
    )

    # Remove old output
    if os.path.exists(output_file):

        try:
            os.remove(output_file)
        except Exception:
            pass

    print(
        f"Starting GStreamer for {name}..."
    )

    process = subprocess.Popen(
        [
            GSTREAMER_EXE,

            "-e",

            "rtspsrc",

            f"location={rtsp_url}",

            "protocols=tcp",

            "latency=200",

            "!",

            "rtph264depay",

            "!",

            "h264parse",

            "!",

            "mp4mux",

            "!",

            "filesink",

            f"location={output_file}"
        ],
        cwd=PROJECT_DIR
    )

    print(
        f"GStreamer {name} started. "
        f"PID: {process.pid}"
    )

    return process, output_file


# ============================================================
# STOP PROCESS SAFELY
# ============================================================

def stop_process(process, name):

    if process is None:
        return

    if process.poll() is None:

        print(
            f"Stopping {name}..."
        )

        try:

            process.terminate()

            process.wait(
                timeout=8
            )

        except subprocess.TimeoutExpired:

            print(
                f"{name} did not stop normally."
            )

            try:
                process.kill()
                process.wait(timeout=3)
            except Exception:
                pass

        except Exception as error:

            print(
                f"Error stopping {name}: "
                f"{error}"
            )


# ============================================================
# MAIN
# ============================================================

def main():

    mediamtx_process = None

    ffmpeg_processes = []

    gst_processes = []

    recordings = []

    try:

        print()
        print("=" * 60)
        print("MULTI-CAMERA RTSP + GSTREAMER")
        print("=" * 60)

        # ----------------------------------------------------
        # CHECK EVERYTHING
        # ----------------------------------------------------

        if not check_requirements():

            print()
            print(
                "Requirement check failed."
            )

            return

        # ----------------------------------------------------
        # START MEDIAMTX
        # ----------------------------------------------------

        mediamtx_process = start_mediamtx()

        # ----------------------------------------------------
        # START ALL FFMPEG STREAMS
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("STARTING ALL RTSP STREAMS")
        print("=" * 60)

        for camera in CAMERAS:

            process = start_ffmpeg(
                camera
            )

            ffmpeg_processes.append(
                (
                    camera["name"],
                    process
                )
            )

            # Small delay between publishers
            time.sleep(1)

        # ----------------------------------------------------
        # WAIT FOR RTSP STREAMS
        # ----------------------------------------------------

        print()
        print(
            "Waiting for all RTSP streams..."
        )

        time.sleep(4)

        # ----------------------------------------------------
        # START ALL GSTREAMER RECORDERS
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("STARTING ALL GSTREAMER RECORDERS")
        print("=" * 60)

        for camera in CAMERAS:

            gst_process, output_file = (
                start_gstreamer(camera)
            )

            gst_processes.append(
                (
                    camera["name"],
                    gst_process
                )
            )

            recordings.append(
                (
                    camera["name"],
                    output_file
                )
            )

            time.sleep(1)

        # ----------------------------------------------------
        # SYSTEM RUNNING
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("ALL CAMERAS ARE RUNNING")
        print("=" * 60)

        for camera in CAMERAS:

            name = camera["name"]

            rtsp_url = (
                f"rtsp://localhost:8554/{name}"
            )

            print()
            print(
                f"{name}:"
            )

            print(
                f"  RTSP: {rtsp_url}"
            )

        print()
        print(
            "All videos are being processed "
            "simultaneously."
        )

        print()
        print(
            "Waiting for all videos to finish..."
        )

        print()

        # ----------------------------------------------------
        # WAIT FOR ALL FFMPEG PROCESSES
        # ----------------------------------------------------

        for name, process in ffmpeg_processes:

            return_code = process.wait()

            print(
                f"{name} FFmpeg finished. "
                f"Exit code: {return_code}"
            )

        # ----------------------------------------------------
        # GIVE GSTREAMER TIME TO RECEIVE EOS
        # ----------------------------------------------------

        print()
        print(
            "All input videos finished."
        )

        print(
            "Waiting for GStreamer to finalize "
            "recordings..."
        )

        time.sleep(3)

        # ----------------------------------------------------
        # STOP GSTREAMER
        # ----------------------------------------------------

        for name, process in gst_processes:

            if process.poll() is None:

                print(
                    f"Stopping GStreamer {name}..."
                )

                try:

                    process.send_signal(
                        signal.SIGINT
                    )

                    process.wait(
                        timeout=10
                    )

                except subprocess.TimeoutExpired:

                    print(
                        f"GStreamer {name} "
                        f"did not stop normally."
                    )

                    process.terminate()

                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()

                except Exception as error:

                    print(
                        f"GStreamer {name} "
                        f"error: {error}"
                    )

        # ----------------------------------------------------
        # VERIFY RECORDINGS
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("RECORDING RESULTS")
        print("=" * 60)

        for name, output_file in recordings:

            if os.path.exists(output_file):

                size = os.path.getsize(
                    output_file
                )

                print()
                print(
                    f"[SUCCESS] {name}"
                )

                print(
                    f"File: {output_file}"
                )

                print(
                    f"Size: "
                    f"{size / (1024 * 1024):.2f} MB"
                )

            else:

                print()
                print(
                    f"[FAILED] {name}"
                )

                print(
                    "Output file was not created."
                )

    except KeyboardInterrupt:

        print()
        print("=" * 60)
        print("CTRL+C DETECTED")
        print("=" * 60)

        print(
            "Stopping all processes..."
        )

    except Exception as error:

        print()
        print("=" * 60)
        print("ERROR")
        print("=" * 60)

        print(error)

    finally:

        # ----------------------------------------------------
        # STOP GSTREAMER
        # ----------------------------------------------------

        for name, process in gst_processes:

            stop_process(
                process,
                f"GStreamer-{name}"
            )

        # ----------------------------------------------------
        # STOP FFMPEG
        # ----------------------------------------------------

        for name, process in ffmpeg_processes:

            stop_process(
                process,
                f"FFmpeg-{name}"
            )

        # ----------------------------------------------------
        # STOP MEDIAMTX
        # ----------------------------------------------------

        stop_process(
            mediamtx_process,
            "MediaMTX"
        )

        # ----------------------------------------------------
        # FINAL OUTPUT
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("FINAL OUTPUT")
        print("=" * 60)

        print()
        print(
            "Recordings are stored in:"
        )

        print(RESULTS_DIR)

        print()

        if os.path.exists(RESULTS_DIR):

            files = [
                file
                for file in os.listdir(
                    RESULTS_DIR
                )
                if file.lower().endswith(".mp4")
            ]

            if files:

                for file in files:

                    path = os.path.join(
                        RESULTS_DIR,
                        file
                    )

                    size = os.path.getsize(
                        path
                    )

                    print(
                        f"  {file} "
                        f"({size / (1024 * 1024):.2f} MB)"
                    )

            else:

                print(
                    "No MP4 recordings found."
                )

        print()
        print(
            "All processes stopped."
        )

        print("=" * 60)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()