"""Record the fictional demo with the macOS voice and rendered slide posters."""
import re
import subprocess
from pathlib import Path


DEMO = Path(__file__).resolve().parent
OUTPUT = DEMO.parents[1] / ".local" / "demo"


def run(*args):
    subprocess.run(args, check=True, cwd=OUTPUT)


def main():
    speech = (DEMO / "teleprompter.md").read_text(encoding="utf-8")
    blocks = re.split(r"^## [0-9]+\. [^\n]+\n", speech, flags=re.MULTILINE)[1:]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    tracks = []
    for i, speech_block in enumerate(blocks, 1):
        poster = DEMO / "animation" / "poster" / f"slide-{i:02d}.png"
        if not poster.is_file():
            raise SystemExit("Сначала отрендерите все слайды примера.")
        voice = f"voice-{i}.aiff"
        clip = f"clip-{i}.mp4"
        run("say", "-v", "Milena", "-r", "132", "-o", voice, " ".join(speech_block.split()))
        run(
            "ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", "24", "-i", str(poster),
            "-i", voice, "-af", "apad=pad_dur=0.7", "-ar", "48000", "-ac", "1",
            "-vf", "scale=1280:720", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", clip,
        )
        tracks.append(f"file '{clip}'")
    (OUTPUT / "tracks.txt").write_text("\n".join(tracks) + "\n", encoding="utf-8")
    run("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "1",
        "-i", "tracks.txt", "-c", "copy", "test-video.mp4")
    print(OUTPUT / "test-video.mp4")


if __name__ == "__main__":
    main()
