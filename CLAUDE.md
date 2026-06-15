# CLAUDE.md

Гайд для Claude Code по этому проекту. Кратко: инструмент подтягивает арты (обложки и пр.)
для **non-Steam игр** из **SteamGridDB** и кладёт их в Steam. Нужен потому, что Hydra Launcher
при добавлении игры в Steam передаёт hero/logo/баннер, но НЕ передаёт вертикальную обложку
600×900 (`<appid>p.png`) — в библиотеке остаётся серая заглушка.

## Архитектура

Три слоя, движок переиспользуется и CLI, и GUI:

- **`steam_art.py`** — движок (stdlib-only) + CLI. Здесь вся логика:
  - `find_steam_path`, `load_api_key`, `list_accounts`, `account_paths`, `list_games`
  - `load_shortcuts` / `parse_binary_vdf` — парсинг бинарного `shortcuts.vdf`
  - `search_games` (список кандидатов), `search_game_id` (первый), `list_arts` (список вариантов
    для GUI), `fetch_art_url` (первый — для авто-режима), `apply_art`, `art_status`, `existing_art`
  - `find_orphans` / `clean_orphans` — осиротевшие арты
  - `api_get` — обёртка над SteamGridDB API с ретраями; классы `SGDBError` (некритичная) и
    `SGDBAuthError` (неверный ключ → прерывать)
- **`steam_art_app.py`** — локальный HTTP-сервер (stdlib `http.server`, ThreadingHTTPServer) +
  запуск нативного окна через **pywebview**. Отдаёт `web/` и JSON-API. Бэкенд зовёт движок.
- **`web/`** — фронтенд (vanilla, без сборки): `index.html`, `style.css` (стекло+неон), `app.js`.

CLI: `run_steam_art.bat` → `steam_art.py`. GUI: `run_app.bat` → `steam_art_app.py`.

## Ключевые факты (важно не сломать)

- **Имя файла арта = поле `appid` из `shortcuts.vdf`** (напр. Alien Isolation = `2468090731`),
  НЕ вычисляемый CRC. Если `appid` отсутствует/0 — fallback `compute_legacy_appid`.
- Суффиксы файлов в `ART_TYPES`: cover→`p`, banner→``, hero→`_hero`, logo→`_logo`.
  Steam понимает .png/.jpg/.webp; `apply_art` удаляет дубли другого расширения того же типа.
- **Тип `icon` намеренно НЕ поддерживается** (применение арта-иконки). Иконку non-Steam игры Steam
  берёт из поля `icon` в `shortcuts.vdf` (абсолютный путь), а НЕ из grid, и перечитывает её только из
  своих правок / при перезапуске. Поэтому внешне «вживую» сменить иконку нельзя (без закрытия Steam
  или CEF-инъекции) — тип `icon` убран из `ART_TYPES`, UI и official-арта. Показ значка игры в списке
  (чтение поля через `game_icon_path` / `/api/gameicon`) — это другое, остаётся.
- non-Steam appid всегда `>= NONSTEAM_MIN` (0x80000000). Очистка осиротевших трогает только
  такие файлы — арты обычных Steam-игр (маленький appid) НЕ трогаются.
- Пути: арты в `<Steam>\userdata\<uid>\config\grid\`; читаем `shortcuts.vdf` (не пишем в него →
  безопасно при запущенном Steam). После изменений арта Steam нужно перезапустить.

## API-ключ

SteamGridDB-ключ ищется (в порядке): флаг `--api-key` → env `STEAMGRIDDB_API_KEY` → файл
`steam_art.key` рядом со скриптом. **`steam_art.key` в `.gitignore`** — никогда не коммитить.

## Зависимости

- CLI: только stdlib.
- GUI: **Pillow** (превью), **pywebview** (окно; требует pythonnet/clr для движка Edge WebView2).
  `run_app.bat` доустанавливает Pillow/pywebview при отсутствии.

## Гайдлайны фронтенда (грабли, на которые уже наступали)

- **Кеш WebView2**: статику отдавать с `Cache-Control: no-cache`; в `index.html` ссылки на
  `style.css`/`app.js` версионируются по mtime (`_send_index`). Иначе правки не подхватываются.
- **Аспект карточек**: картинка `position:absolute; inset:0` внутри `.imgwrap` с `aspect-ratio`,
  иначе in-flow `<img>` ломает высоту (схлопывает). Сетка: `grid-auto-rows:max-content` +
  `min-height:0` во flex-цепочке, чтобы строки не сжимались, а список скроллился.
- **Загрузка картинок**: без `loading="lazy"` (иначе нижние «не грузятся»); у каждой карточки
  свой shimmer (класс `loading`), снимается по `load`; при `error` — фолбэк на полный `url`,
  затем значок ⚠. Скелетоны рисуются один раз (guard по `grid.dataset.skel`), чтобы не мигало.
- Сетевые операции бэкенда не должны блокировать UI — длинные операции (авто-дозаливка) идут
  через SSE (`/api/autofill`) с прогрессом.

## Как запускать / проверять

- Запуск GUI: `pythonw steam_art_app.py` (или `run_app.bat`). Окно перезапускать после правок.
- Безопасная проверка бэкенда без окна: поднять `Server` в треде и дёргать эндпоинты через
  `urllib` (см. историю — так тестировали `/api/state|games|search|arts|img|orphans`).
- `apply_art` тестировать во временную папку, чтобы не трогать реальные арты пользователя.
- Перед коммитом: `python -c "import py_compile; py_compile.compile('steam_art.py', doraise=True)"`
  (и для `steam_art_app.py`).

## Стиль кода

- **Комментарии и docstring'и — на английском** (проект open-source). Пользовательские
  строки интерфейса идут через i18n (`web/i18n.js`, RU/EN) — русские значения там это
  локализация, их не трогаем. CLI-вывод — на английском.
- Python — без сторонних зависимостей в движке. Не ломать CLI при доработках GUI (общий движок).
