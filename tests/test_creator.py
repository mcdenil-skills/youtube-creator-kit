import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "creator.py"


class CreatorTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name)
        self.production = {
            "title": "Проверка <тема>",
            "audience": "Начинающие",
            "promise": "Готовый результат",
            "facts": ["Сценарий демонстрации"],
            "cta": {
                "intro": "Возьмите шаблон.",
                "outro": "Примените шаблон.",
                "telegram_reason": "В Telegram каждую неделю новое упражнение.",
            },
            "blocks": [{
                "title": "Первый шаг",
                "duration": "0:30",
                "beats": ["Показываем форму"],
                "open_loop": "Дальше проверим результат.",
                "transition": "Откроем форму.",
                "speech": ["<script>alert(1)</script>", "Вторая реплика."],
                "slide": {"headline": "Откройте форму", "points": ["Подсказка"], "cue": "Камера"},
            }],
        }
        self.publication = {
            "title": "Первый шаг",
            "alternate_titles": ["Другой заголовок", "Ещё вариант"],
            "description": "Описание.",
            "chapters": [{"at": "0:00", "title": "Начало"}, {"at": "0:30", "title": "Разбор"}],
            "thumbnail": "Проверка",
            "tags": ["обучение"],
            "hashtags": ["#Обучение", "#Файлы"],
            "links": [{"label": "Шаблон", "url": "https://example.org/template"}],
            "pinned_comment": "Какой шаг попробуете?",
            "telegram": "Пост.",
            "handout": "Методичка.",
            "promises": ["Покажем форму."],
        }

    def write_json(self, name, data):
        (self.project / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def run_creator(self, stage):
        return subprocess.run(
            [sys.executable, str(CLI), stage, str(self.project)],
            capture_output=True, text=True,
        )

    def test_prepare_renders_scenario_prompter_and_escaped_75_25_deck(self):
        self.write_json("production.json", self.production)
        result = self.run_creator("prepare")
        self.assertEqual(result.returncode, 0, result.stderr)
        deck = (self.project / "navigator.html").read_text()
        self.assertIn('class="stage"', deck)
        self.assertIn('class="cheat"', deck)
        self.assertIn("75fr 25fr", deck)
        prompter = (self.project / "teleprompter.html").read_text()
        self.assertIn("&lt;script&gt;", prompter)
        self.assertNotIn("<script>alert(1)", prompter)
        self.assertLess(prompter.index("&lt;script&gt;"), prompter.index("Возьмите шаблон."))
        self.assertLess(prompter.index("Возьмите шаблон."), prompter.index("Вторая реплика."))
        self.assertLess(prompter.index("Вторая реплика."), prompter.index("Примените шаблон."))
        self.assertIn("В Telegram каждую неделю новое упражнение.", prompter)
        self.assertNotIn("Возьмите шаблон.", deck.split('<aside', 1)[0])
        self.assertIn("Возьмите шаблон.", deck)
        self.assertIn("Дальше проверим результат.", (self.project / "scenario.md").read_text())

    def test_prepare_renders_comparison_as_two_cards(self):
        slide = self.production["blocks"][0]["slide"]
        slide.update(kind="compare", points=["До", "После"])
        self.write_json("production.json", self.production)
        result = self.run_creator("prepare")
        self.assertEqual(result.returncode, 0, result.stderr)
        deck = (self.project / "navigator.html").read_text()
        self.assertIn('<ul class="duo"><li>До</li><li>После</li></ul>', deck)

    def test_bad_slide_is_rejected_before_overwriting_output(self):
        self.production["blocks"][0]["slide"]["points"] = [""] * 8
        self.write_json("production.json", self.production)
        (self.project / "navigator.html").write_text("previous deck")
        result = self.run_creator("prepare")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("points", result.stderr)
        self.assertEqual((self.project / "navigator.html").read_text(), "previous deck")

    def test_publish_keeps_only_chapters_supported_by_transcript(self):
        self.write_json("publication.json", self.publication)
        (self.project / "transcript.txt").write_text("[00:00] Вступление\n[00:30] Разбор формы\n")
        result = self.run_creator("publish")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.project / "postproduction"
        youtube = (output / "youtube.md").read_text()
        self.assertIn("00:30 Разбор", youtube)
        self.assertIn("#Обучение #Файлы", youtube)
        self.assertIn("Другой заголовок", youtube)
        self.assertIn("https://example.org/template", youtube)
        self.assertIn("Какой шаг попробуете?", youtube)
        self.assertEqual({p.name for p in output.iterdir()},
                         {"youtube.md", "telegram.md", "handout.md", "promises.md"})

        self.publication["chapters"][1]["at"] = "1:59"
        self.write_json("publication.json", self.publication)
        result = self.run_creator("publish")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("01:59", result.stderr)
        self.assertIn("00:30 Разбор", (output / "youtube.md").read_text())

    def test_publish_accepts_hour_timestamps(self):
        self.publication["chapters"][1]["at"] = "1:00:30"
        self.write_json("publication.json", self.publication)
        (self.project / "transcript.txt").write_text("[00:00] Начало\n[01:00:30] Поздний раздел\n")
        result = self.run_creator("publish")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("01:00:30 Разбор", (self.project / "postproduction/youtube.md").read_text())
