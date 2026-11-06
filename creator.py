#!/usr/bin/env python3
"""Build filming and publication files from the author's inputs."""
import argparse
from html import escape
import json
from pathlib import Path
import re
from string import Template
import sys
from urllib.parse import urlsplit


TEMPLATES = Path(__file__).resolve().parent / "templates"
TIMESTAMP = r"(?:[0-9]+:)?[0-9]+:[0-5][0-9]"


def require(value, expected, label):
    if not isinstance(value, expected) or (expected is str and not value.strip()):
        raise ValueError(f"{label}: ожидается {expected.__name__} с содержимым")
    return value.strip() if expected is str else value


def field(record, key, expected=str):
    return require(record.get(key), expected, key)


def strings(record, key, minimum=0, maximum=None):
    values = field(record, key, list)
    if len(values) < minimum or (maximum is not None and len(values) > maximum):
        raise ValueError(f"{key}: требуется минимум {minimum} элементов"
                         + (f", максимум {maximum}" if maximum is not None else ""))
    return [require(value, str, key) for value in values]


def read_json(path):
    return require(json.loads(path.read_text(encoding="utf-8")), dict, path.name)


def page(name, title, content):
    template = Template((TEMPLATES / f"{name}.html").read_text(encoding="utf-8"))
    return template.substitute(title=escape(title), content=content)


def bullets(items):
    return "\n".join(f"- {item}" for item in items)


def seconds(stamp):
    if not re.fullmatch(TIMESTAMP, stamp):
        raise ValueError(f"Некорректный таймкод {stamp}")
    parts = [int(part) for part in stamp.split(":")]
    if len(parts) == 3 and parts[1] > 59:
        raise ValueError(f"Некорректный таймкод {stamp}")
    return sum(part * 60 ** index for index, part in enumerate(reversed(parts)))


def clock(value):
    minutes, secs = divmod(value, 60)
    hours, minutes = divmod(minutes, 60)
    return (f"{hours:02}:" if hours else "") + f"{minutes:02}:{secs:02}"


def slide_content(slide):
    kind = slide.get("kind", "list")
    if kind not in ("cover", "list", "compare", "quote", "terminal", "cta"):
        raise ValueError("kind: выберите cover, list, compare, quote, terminal или cta")
    points = strings(slide, "points", minimum=1, maximum=4)
    items = [escape(point) for point in points]
    if kind == "compare":
        if len(items) != 2:
            raise ValueError("points: compare требует ровно две карточки")
        content = f'<ul class="duo"><li>{items[0]}</li><li>{items[1]}</li></ul>'
    elif kind == "quote":
        if len(items) > 2:
            raise ValueError("points: quote принимает цитату и необязательную подпись")
        caption = f"<figcaption>{items[1]}</figcaption>" if len(items) == 2 else ""
        content = f"<figure><blockquote>{items[0]}</blockquote>{caption}</figure>"
    elif kind == "terminal":
        content = "<pre><code>" + "\n".join(items) + "</code></pre>"
    else:
        content = '<ol class="points">' + "".join(f"<li>{item}</li>" for item in items) + "</ol>"
    return kind, content


def prepare(source):
    title = field(source, "title")
    audience = field(source, "audience")
    promise = field(source, "promise")
    facts = strings(source, "facts", minimum=1)
    cta = field(source, "cta", dict)
    intro = field(cta, "intro")
    outro = field(cta, "outro")
    telegram_reason = field(cta, "telegram_reason")
    blocks = field(source, "blocks", list)
    if not blocks:
        raise ValueError("blocks: добавьте хотя бы один блок сценария")

    scenario = [f"# {title}", f"**Аудитория**  {audience}", f"**Обещание**  {promise}",
                f"## Факты и источники\n\n{bullets(facts)}",
                f"## Призывы\n\n**После хука**  {intro}\n\n**В финале**  {outro}"
                f"\n\n**Причина подписаться на Telegram**  {telegram_reason}"]
    speech = [f"# {title}"]
    prompter = []
    slides = []
    for number, block in enumerate(blocks, 1):
        block = require(block, dict, f"blocks[{number}]")
        name = field(block, "title")
        duration = field(block, "duration")
        if seconds(duration) == 0:
            raise ValueError("duration: длительность должна быть больше нуля")
        beats = strings(block, "beats", minimum=1)
        paragraphs = strings(block, "speech", minimum=1)
        if number == 1:
            paragraphs.insert(1, intro)
        if number == len(blocks):
            paragraphs.extend([outro, telegram_reason])
        loop = field(block, "open_loop")
        transition = field(block, "transition")
        slide = field(block, "slide", dict)
        headline = field(slide, "headline")
        kind, content = slide_content(slide)
        cue = field(slide, "cue")
        next_name = (field(require(blocks[number], dict, "blocks"), "title")
                     if number < len(blocks) else "Конец ролика")

        scenario.append(
            f"## {number}. {name} · {duration}\n\n{bullets(beats)}\n\n"
            f"**Удержание**  {loop}\n\n**Переход**  {transition}"
        )
        speech.extend([f"## {number}. {name}", *paragraphs])
        speech_html = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
        prompter.append(f'<section><h2>{number:02} · {escape(name)}</h2>{speech_html}</section>')
        slides.append(f"""<section class="slide" aria-label="Слайд {number}">
  <div class="stage">
    <div class="stage-inner" data-kind="{kind}">
      <div class="stage-tag">БЛОК {number:02}</div>
      <h2>{escape(headline)}</h2>
      {content}
    </div>
  </div>
  <aside class="cheat" aria-label="Шпаргалка ведущего">
    <header class="cheat-head">{escape(name)} · {escape(duration)}</header>
    <div class="cheat-body">
      <p class="cue">{escape(cue)}</p>{speech_html}
    </div>
    <footer class="cheat-next">→ {escape(next_name)}</footer>
  </aside>
</section>""")
    return {
        "scenario.md": "\n\n".join(scenario),
        "teleprompter.md": "\n\n".join(speech),
        "teleprompter.html": page("teleprompter", title, "\n".join(prompter)),
        "navigator.html": page("navigator", title, "\n".join(slides)),
    }


def publish(source, transcript):
    known = [seconds(stamp) for stamp in re.findall(rf"^\s*\[({TIMESTAMP})\]\s*\S", transcript, re.M)]
    if not known:
        raise ValueError("transcript.txt: нужны строки с таймкодами [00:00]")
    known.append(0)  # The opening chapter may start before the first spoken word.
    chapters = []
    times = []
    for chapter in field(source, "chapters", list):
        chapter = require(chapter, dict, "chapters")
        at = seconds(field(chapter, "at"))
        if at not in known:
            raise ValueError(f"Таймкод {clock(at)} отсутствует в transcript.txt")
        if times and at - times[-1] < 10:
            raise ValueError("Таймкоды должны идти по порядку с интервалом от 10 секунд")
        times.append(at)
        chapters.append(f"{clock(at)} {field(chapter, 'title')}")
    if times and times[0] != 0:
        raise ValueError("Первая глава должна начинаться с 00:00")
    title = field(source, "title")
    alternatives = strings(source, "alternate_titles", minimum=2, maximum=2)
    titles = [title, *alternatives]
    if any(len(item) > 100 or "\n" in item for item in titles):
        raise ValueError("Заголовок должен быть одной строкой до 100 символов")
    if len(set(item.casefold() for item in titles)) != 3:
        raise ValueError("Укажите три разных варианта заголовка")
    description = field(source, "description")
    thumbnail = field(source, "thumbnail")
    tags = strings(source, "tags")
    hashtags = strings(source, "hashtags", minimum=1, maximum=5)
    if any(not re.fullmatch(r"#\w+", item) for item in hashtags):
        raise ValueError("hashtags: укажите хештеги без пробелов, начиная с #")
    links = []
    for item in field(source, "links", list):
        item = require(item, dict, "links")
        url = field(item, "url")
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or any(c.isspace() for c in url):
            raise ValueError("links: укажите действительный HTTP(S) URL")
        links.append(f"{field(item, 'label')} – {url}")
    if len(times) >= 3 and "duration" in source:
        if seconds(field(source, "duration")) - times[-1] < 10:
            raise ValueError("Последняя глава должна длиться не меньше 10 секунд")
    ready_description = "\n\n".join([
        description,
        *(["\n".join(links)] if links else []),
        *(["Таймкоды\n" + "\n".join(chapters)] if len(chapters) >= 3 else []),
        " ".join(hashtags),
    ])
    if len(ready_description) > 5000:
        raise ValueError("Описание для YouTube должно помещаться в 5000 символов")
    text = "\n\n".join([
        f"# {title}",
        f"## Запасные заголовки\n\n{bullets(alternatives)}",
        f"## Описание для YouTube\n\n````text\n{ready_description}\n````",
        *([f"## Ориентиры по записи\n\n{bullets(chapters)}"] if 0 < len(chapters) < 3 else []),
        f"## Текст обложки\n\n{thumbnail}",
        *([f"## Теги для YouTube Studio\n\n{', '.join(tags)}"] if tags else []),
        f"## Закреплённый комментарий\n\n{field(source, 'pinned_comment')}",
    ])
    promises = strings(source, "promises")
    return {
        "youtube.md": text,
        "telegram.md": field(source, "telegram"),
        "handout.md": field(source, "handout"),
        "promises.md": "# Обещания из записи\n\n" + (bullets(promises) or "Явных обещаний в записи нет."),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "publish"])
    parser.add_argument("project", type=Path, help="Папка одного ролика")
    args = parser.parse_args()
    project = args.project
    try:
        if args.stage == "prepare":
            files = prepare(read_json(project / "production.json"))
            output = project
        else:
            transcript = (project / "transcript.txt").read_text(encoding="utf-8")
            files = publish(read_json(project / "publication.json"), transcript)
            output = project / "postproduction"
        output.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            path = output / name
            path.write_text(content.rstrip() + "\n", encoding="utf-8")
            print(path)
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
