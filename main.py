import os
import socket
import subprocess
import sys
import time


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

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
    }
]


# ============================================================
# CHECK REQUIREMENTS
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

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        if listener.connect_ex(("127.0.0.1", 8554)) == 0:
            raise RuntimeError(
                "RTSP port 8554 is already in use; refusing to start a second MediaMTX process."
            )

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

            # Keep the required stream mapping visible without per-frame console traffic.
            "-nostats",

            # Play video in real time
            "-re",

            # Input
            "-i",
            video_path,

            # IMPORTANT:
            # Copy existing H.264.
            # No decode.
            # No re-encode.
            "-c:v",
            "copy",

            # No audio
            "-an",

            # RTSP
            "-f",
            "rtsp",

            # TCP
            "-rtsp_transport",
            "tcp",

            # URL
            rtsp_url
        ],
        cwd=PROJECT_DIR
    )

    print(
        f"FFmpeg {name} started. "
        f"PID: {process.pid}"
    )

    return process


def wait_for_rtsp_stream(camera, publisher_process, timeout=20):

    name = camera["name"]
    deadline = time.monotonic() + timeout
    request = (
        f"DESCRIBE rtsp://127.0.0.1:8554/{name} RTSP/1.0\r\n"
        "CSeq: 1\r\n"
        "Accept: application/sdp\r\n\r\n"
    ).encode("ascii")

    while time.monotonic() < deadline:

        if publisher_process.poll() is not None:
            raise RuntimeError(
                f"FFmpeg for {name} exited before its RTSP stream became available."
            )

        try:
            with socket.create_connection(
                ("127.0.0.1", 8554),
                timeout=1
            ) as connection:
                connection.settimeout(1)
                connection.sendall(request)
                response = connection.recv(1024)

            if response.startswith(b"RTSP/1.0 200"):
                print(f"RTSP stream available: rtsp://localhost:8554/{name}")
                return

        except OSError:
            pass

        time.sleep(0.2)

    raise TimeoutError(
        f"Timed out waiting for rtsp://localhost:8554/{name}."
    )


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

    output_file = os.path.abspath(
        os.path.join(
            RESULTS_DIR,
            f"{video_name}_rtsp_output.mp4"
        )
    )

    # Remove old output
    if os.path.exists(output_file):

        try:
            os.remove(output_file)

        except Exception as error:

            print(
                f"Could not remove old file: "
                f"{error}"
            )

    print(
        f"Starting GStreamer for {name}..."
    )

    # ========================================================
    # IMPORTANT PIPELINE
    #
    # RTSP
    #   ↓
    # RTP H264 depay
    #   ↓
    # H264 parser
    #   ↓
    # MP4 split muxer
    #   ↓
    # MP4 file
    #
    # H.264 remains compressed end to end.
    # ========================================================

    pipeline = [
        GSTREAMER_EXE,

        "-e",

        # RTSP source
        "rtspsrc",
        f"location={rtsp_url}",
        "protocols=tcp",
        "latency=200",

        "!",

        # RTP -> H264
        "rtph264depay",

        "!",

        # Parse H264
        "h264parse",
        "config-interval=-1",

        "!",

        # mp4mux requires AVC-format access units. Keep the stream
        # compressed and make the muxer's input contract explicit.
        "video/x-h264,stream-format=avc,alignment=au",

        "!",

        # Write and finalize one MP4 when the RTSP stream reaches EOS.
        "mp4mux",

        "!",

        "filesink",
        f'location="{output_file.replace(os.sep, "/")}"'
    ]

    print()
    print(
        f"GStreamer output:"
    )
    print(output_file)
    print()

    process = subprocess.Popen(
        pipeline,
        cwd=PROJECT_DIR
    )

    print(
        f"GStreamer {name} started. "
        f"PID: {process.pid}"
    )

    return process, output_file


# ============================================================
# STOP PROCESS
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

                process.wait(
                    timeout=3
                )

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
    exit_code = 1

    try:

        print()
        print("=" * 60)
        print("MULTI-CAMERA RTSP + GSTREAMER")
        print("=" * 60)

        # ----------------------------------------------------
        # CHECK
        # ----------------------------------------------------

        if not check_requirements():

            print()
            print(
                "Requirement check failed."
            )

            return exit_code

        # ----------------------------------------------------
        # MEDIAMTX
        # ----------------------------------------------------

        mediamtx_process = start_mediamtx()

        # ----------------------------------------------------
        # FFMPEG
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("STARTING ALL RTSP STREAMS")
        print("=" * 60)

        print()
        print("Starting each recorder as soon as its RTSP path is ready...")

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

            wait_for_rtsp_stream(camera, process)

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

            print()
            print("Both camera publishers and recorders are running.")

        # ----------------------------------------------------
        # RUNNING
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("ALL CAMERAS ARE RUNNING")
        print("=" * 60)

        for camera in CAMERAS:

            print()
            print(
                f"{camera['name']}:"
            )

            print(
                f"  RTSP: "
                f"rtsp://localhost:8554/"
                f"{camera['name']}"
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
        # WAIT FOR FFMPEG
        # ----------------------------------------------------

        for name, process in ffmpeg_processes:

            return_code = process.wait()

            print(
                f"{name} FFmpeg finished. "
                f"Exit code: {return_code}"
            )

            if return_code != 0:
                raise RuntimeError(
                    f"FFmpeg for {name} exited with code {return_code}."
                )

        # ----------------------------------------------------
        # WAIT FOR GSTREAMER EOS
        # ----------------------------------------------------

        print()
        print(
            "All input videos finished."
        )

        print(
            "Waiting for GStreamer to "
            "finalize MP4 files..."
        )

        # ----------------------------------------------------
        # WAIT GSTREAMER
        # ----------------------------------------------------

        for name, process in gst_processes:

            print(f"Waiting for GStreamer {name} EOS...")
            return_code = process.wait(timeout=30)
            print(f"GStreamer {name} finished. Exit code: {return_code}")

            if return_code != 0:
                raise RuntimeError(
                    f"GStreamer for {name} exited with code {return_code}."
                )

        # ----------------------------------------------------
        # RESULTS
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("RECORDING RESULTS")
        print("=" * 60)

        recordings_valid = True

        for name, output_file in recordings:

            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:

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

                recordings_valid = False

                print()
                print(
                    f"[FAILED] {name}"
                )

                print(
                    "Output file is missing or empty."
                )

        if not recordings_valid:
            raise RuntimeError("One or more MP4 recordings are missing or empty.")
        exit_code = 0

    except KeyboardInterrupt:

        print()
        print(
            "CTRL+C detected."
        )
        exit_code = 130

    except Exception as error:

        print()
        print("=" * 60)
        print("ERROR")
        print("=" * 60)

        print(error)
        exit_code = 1

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
                        f"("
                        f"{size / (1024 * 1024):.2f}"
                        f" MB)"
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
    return exit_code


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    sys.exit(main())