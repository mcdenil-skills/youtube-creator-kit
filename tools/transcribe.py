#!/usr/bin/env python3
"""Make a timestamped transcript with local Whisper or the author's Deepgram key."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


def line(start, text):
    minutes, seconds = divmod(int(start), 60)
    return f"[{minutes:02}:{seconds:02}] {text.strip()}"


def local(source, language, model):
    from faster_whisper import WhisperModel

    engine = WhisperModel(model, device="cpu", compute_type="int8")
    segments, _ = engine.transcribe(str(source), language=language)
    return [line(item.start, item.text) for item in segments if item.text.strip()]


def deepgram(source, language):
    import requests

    key = os.environ.get("DEEPGRAM_API_KEY")
    if not key:
        from dotenv import dotenv_values

        key = dotenv_values(Path(__file__).resolve().parents[1] / ".env").get("DEEPGRAM_API_KEY")
    if not key:
        raise ValueError("Добавьте свой DEEPGRAM_API_KEY в .env")
    with TemporaryDirectory(prefix="creator-audio-") as folder:
        audio = Path(folder) / "audio.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(source), "-vn", "-ar", "16000",
                        "-ac", "1", "-b:a", "64k", str(audio)], check=True)
        params = {"model": "nova-2", "smart_format": "true", "utterances": "true"}
        if language:
            params["language"] = language
        else:
            params["detect_language"] = "true"
        with audio.open("rb") as stream:
            response = requests.post(
                "https://api.deepgram.com/v1/listen", params=params,
                headers={"Authorization": f"Token {key}", "Content-Type": "audio/mpeg"},
                data=stream, timeout=(15, 900),
            )
        if not response.ok:
            raise ValueError(f"Deepgram вернул HTTP {response.status_code}")
        utterances = response.json().get("results", {}).get("utterances", [])
        return [line(item["start"], item["transcript"]) for item in utterances if item["transcript"].strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    parser.add_argument("--engine", choices=["local", "deepgram"], default="local")
    parser.add_argument("--language", help="Код языка, например ru. По умолчанию автоопределение.")
    parser.add_argument("--model", default="small", help="Имя или путь модели faster-whisper")
    args = parser.parse_args()
    try:
        source = args.source.resolve(strict=True)
        if not source.is_file() or source == args.output.resolve():
            raise ValueError("Укажите файл записи и отдельный путь для транскрипта")
        lines = (local(source, args.language, args.model) if args.engine == "local"
                 else deepgram(source, args.language))
        if not lines:
            raise ValueError("В записи не нашлась разборчивая речь")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except ImportError as error:
        print(f"Установите зависимости выбранного режима. {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Ошибка распознавания: {error}", file=sys.stderr)
        return 1
    print(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
