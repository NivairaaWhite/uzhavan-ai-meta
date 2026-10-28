"""
Uzhavan.AI × Meta AI: Playwright + FFmpeg 3-Minute Video Generator
Renders presentation.html at 1920x1080, 30 fps, with 0.3s scene crossfades,
sequential bullet reveals, Noto Sans Tamil typography, and video placeholders.
Muxes output with voice.wav using FFmpeg (-preset veryfast) to produce out.mp4.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: Playwright is not installed. Install with: pip install playwright && playwright install chromium")
    sys.exit(1)


def find_ffmpeg() -> str:
    """Find FFmpeg binary from imageio-ffmpeg or system PATH."""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(exe):
            return exe
    except Exception:
        pass

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    raise RuntimeError("FFmpeg not found! Please install imageio-ffmpeg or install FFmpeg to PATH.")


def mux_audio_and_video(ffmpeg_exe: str, video_in: str, audio_in: str, video_out: str):
    """Mux video with voice.wav using FFmpeg -preset veryfast."""
    print(f"\n[FFmpeg] Muxing video and audio into: {video_out}")
    if os.path.exists(audio_in):
        print(f"[FFmpeg] Found audio file: {audio_in}")
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", video_in,
            "-i", audio_in,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            video_out,
        ]
    else:
        print(f"[FFmpeg] Notice: '{audio_in}' not found. Generating clean silent MP4.")
        print("         (When you record voice.wav, place it in tools/ and re-run with --mux-only)")
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", video_in,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            video_out,
        ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print("[FFmpeg] Error:", res.stderr)
        sys.exit(res.returncode)
    print(f"[FFmpeg] Successfully generated: {video_out}")


def render_presentation(html_path: str, output_mp4: str, audio_path: str, duration: int = 180, fps: int = 30):
    ffmpeg_exe = find_ffmpeg()
    print("=" * 70)
    print("Uzhavan.AI Presentation Video Generator (Playwright + FFmpeg)")
    print(f"  Target Resolution: 1920x1080 @ {fps} fps")
    print(f"  Target Duration:   {duration} seconds ({duration * fps} frames)")
    print(f"  HTML Source:       {html_path}")
    print(f"  FFmpeg Preset:     veryfast")
    print(f"  Output MP4:        {output_mp4}")
    print("=" * 70)

    temp_dir = tempfile.mkdtemp(prefix="uzhavan_video_")
    recordings_dir = os.path.join(temp_dir, "playwright_rec")
    os.makedirs(recordings_dir, exist_ok=True)

    file_url = f"file:///{os.path.abspath(html_path).replace(os.sep, '/')}"

    with sync_playwright() as p:
        print("\n[Playwright] Launching Chromium (1920x1080 viewport)...")
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-web-security",
                "--allow-file-access-from-files",
                "--autoplay-policy=no-user-gesture-required",
            ],
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=recordings_dir,
            record_video_size={"width": 1920, "height": 1080},
        )

        page = context.new_page()
        print(f"[Playwright] Navigating to: {file_url}")
        page.goto(file_url, wait_until="networkidle")

        print("[Playwright] Starting animated presentation playback...")
        page.evaluate("window.playPresentation()")

        start_time = time.time()
        for sec in range(1, duration + 1):
            time.sleep(1.0)
            elapsed = time.time() - start_time
            if sec % 10 == 0 or sec == duration:
                mins = sec // 60
                secs = sec % 60
                print(f"  Progress: {mins:02d}:{secs:02d} / {duration//60:02d}:{duration%60:02d} (Elapsed: {elapsed:.1f}s)", flush=True)

        print("[Playwright] Playback complete. Finalizing Chromium recording...")
        page.close()
        context.close()
        browser.close()

    # Find recorded WebM file
    recorded_files = [os.path.join(recordings_dir, f) for f in os.listdir(recordings_dir) if f.endswith(".webm")]
    if not recorded_files:
        raise RuntimeError("No recorded video file found from Playwright.")

    raw_video = recorded_files[0]
    print(f"[Playwright] Video recorded to temporary file: {raw_video}")

    # Mux to final MP4 with FFmpeg -preset veryfast
    mux_audio_and_video(ffmpeg_exe, raw_video, audio_path, output_mp4)

    # Clean up temp directory
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Render Uzhavan.AI presentation video using Playwright & FFmpeg.")
    parser.add_argument("--html", default=os.path.join(os.path.dirname(__file__), "presentation.html"), help="Path to presentation.html")
    parser.add_argument("--audio", default=os.path.join(os.path.dirname(__file__), "voice.wav"), help="Path to voice.wav")
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "out.mp4"), help="Output video path (default: tools/out.mp4)")
    parser.add_argument("--duration", type=int, default=180, help="Duration in seconds (default: 180 for 3 minutes)")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second (default: 30)")
    parser.add_argument("--mux-only", action="store_true", help="Only mux an existing raw video with audio without re-rendering")

    args = parser.parse_args()

    if args.mux_only:
        ffmpeg_exe = find_ffmpeg()
        raw_video = os.path.join(os.path.dirname(__file__), "raw_presentation.mp4")
        if not os.path.exists(raw_video):
            raw_video = args.out
        mux_audio_and_video(ffmpeg_exe, raw_video, args.audio, args.out)
        return

    render_presentation(
        html_path=args.html,
        output_mp4=args.out,
        audio_path=args.audio,
        duration=args.duration,
        fps=args.fps,
    )


if __name__ == "__main__":
    main()
