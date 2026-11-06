# YouTube Creator Kit

Локальный рабочий стол для длинных YouTube-роликов. Откройте папку в Codex или Claude Code. Агент проведёт от темы или референса до сценария, суфлёра, презентации, анимации и документа для YouTube Studio.

## Первый ролик

На GitHub нажмите **Code → Download ZIP**, распакуйте архив и откройте папку проекта. Если пользуетесь Git, выполните:

```bash
git clone https://github.com/mcdenil-skills/youtube-creator-kit.git
cd youtube-creator-kit
```

1. Скопируйте `templates/author.example.md` в `author.md`. Укажите свою аудиторию, голос, ссылку входа в воронку и причину подписки на свой Telegram.
2. Откройте эту папку как проект в агенте и напишите: «Подготовь ролик про … для … на … минут. Начни со сценария и сделай презентацию с суфлёром». Можно дать расшифровку референса.
3. Перед съёмкой откройте `navigator.html`. Стрелки листают слайды, `F` включает полный экран. Слева 75% для зрителя, справа 25% для ведущего. Для отдельного окна откройте `teleprompter.html` и настройте прокрутку.
4. После съёмки дайте агенту финальный файл или расшифровку и попросите: «Подготовь документ для YouTube Studio, пост в Telegram и методичку по этой записи».

Встроенные навыки [Сценарий](.agents/skills/youtube-scenario/SKILL.md), [Презентация](.agents/skills/youtube-slides/SKILL.md), [Публикация](.agents/skills/youtube-publication/SKILL.md) подхватываются по правилам проекта. Короткий вход в воронку после хука, финальный призыв и причина подписки на Telegram попадают в сценарий и суфлёр.

## Воспроизвести пример

Нужны Python 3.11+ и браузер. Для анимации нужны Node.js 22+ и npm. Первый рендер может скачать браузер Remotion. Синтетические входные файлы уже лежат в `examples/demo/`.

```bash
python3 creator.py prepare examples/demo
python3 creator.py publish examples/demo
npm ci --prefix tools/slide-animator
node tools/slide-animator/render.mjs examples/demo/navigator.html
```

Откройте `examples/demo/navigator.html` и `teleprompter.html` в браузере. В `animation/` лежат MP4, постеры и прозрачные слои. В `postproduction/youtube.md` лежат три варианта заголовка, описание с главами и хештегами, текст обложки, теги и закреплённый комментарий. Пост, методичка и список обещаний лежат рядом. Файлы генерируются локально и исключены из Git. [Схема входов и выходов](knowledge/inputs.md)

## Запись и тренды

- **Есть текст с таймкодами.** Сохраните его как `transcript.txt` в папку ролика. Можно сразу готовить публикацию.
- **Нужно распознать запись локально.** Установите `python3 -m pip install -r requirements-local.txt` в виртуальном окружении. Запустите `python3 tools/transcribe.py video.mp4 --language ru -o scripts/my-video/transcript.txt`. Модель скачивается при первом запуске, если её ещё нет. Чтобы использовать имеющуюся модель, передайте её путь через `--model`.
- **Нужны Deepgram или YouTube Data API.** Установите `requirements-services.txt`, скопируйте `.env.example` в `.env` и добавьте только свой нужный ключ. Для Deepgram также нужен FFmpeg. Добавьте `--engine deepgram` к команде расшифровки. Для трендов запустите `python3 tools/trends.py --search "моя тема" --exclude-shorts`. Фильтр длинных видео приблизительный и использует длительность. [Deepgram](https://developers.deepgram.com/docs/pre-recorded-audio) · [YouTube Data API](https://developers.google.com/youtube/data)
- **Свои ролики.** Папки в `scripts/`, личный профиль `author.md`, дневник `memory/` и `.env` остаются локально. Готовые HTML-файлы открываются самостоятельно. [Дополнительные навыки](knowledge/skills.md)

## Проверки

```bash
python3 -m unittest discover -s tests -v
npm run --prefix tools/slide-animator check
npx --prefix tools/slide-animator playwright-core install chromium
node tools/slide-animator/check-html.mjs examples/demo
```

Чтобы проверить браузером уже установленный Chrome, задайте `CHROME_PATH` с путём к бинарнику. Для Remotion аналогичная переменная называется `REMOTION_BROWSER_EXECUTABLE`. Синтетическую запись примера на Mac можно пересобрать после рендера командой `python3 examples/demo/record-macos.py`. Нужны голос Milena и FFmpeg. Запись появится в `.local/demo/test-video.mp4`. Это демонстрация процесса подготовки, запись и публикация реального ролика остаются у автора.
