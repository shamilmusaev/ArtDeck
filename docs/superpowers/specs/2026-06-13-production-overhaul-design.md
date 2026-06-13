# Steam Art — доведение до production + новые фичи

**Дата:** 2026-06-13
**Ветка:** `feature/production-overhaul`
**Статус:** утверждён, готов к плану реализации

## Цель

Превратить утилиту дозаливки артов для non-Steam игр в полноценное production-приложение:
рефакторинг движка на модули, 7 новых/улучшенных функций, редизайн UI, автотесты,
сборка в .exe и обновлённые доки. Движок остаётся stdlib-only; CLI не ломается.

## Решения по scope (зафиксированы)

- **Охват Steam-игр:** только **установленные** (локально, оффлайн, без Steam Web API-ключа).
- **Структура списка:** **две вкладки** сверху сайдбара — `Non-Steam | Установленные`.
- **Production включает:** сборку в .exe + автотесты + обработку краевых случаев + обновление доков.
- **Подход к коду:** рефакторинг движка на пакет `steam/` (вариант A).
- **i18n:** `web/i18n.js`, словари ru/en, переключатель в шапке, выбор в `localStorage`.

## Архитектура

`steam_art.py` разбивается на пакет `steam/`. Публичные имена сохраняются, CLI и сервер
продолжают работать. `steam_art.py` остаётся тонкой CLI-обёрткой; `steam_art_app.py`
меняет только импорт на `import steam as engine`.

| Модуль | Ответственность |
|---|---|
| `steam/paths.py` | `find_steam_path`, `list_accounts`, `account_paths`, библиотеки (`libraryfolders.vdf`) |
| `steam/users.py` | **NEW** — имена аккаунтов (`loginusers.vdf`) + аватары (`avatarcache/`); маппинг uid↔SteamID64 |
| `steam/vdf.py` | низкоуровневый `parse_binary_vdf` + текстовый VDF-парсер (`.acf`/`loginusers`) |
| `steam/library.py` | `load_shortcuts` (non-Steam) + **NEW** `load_installed` (`appmanifest_*.acf`); единый формат игры |
| `steam/sgdb.py` | `api_get`, `search_games`, `list_arts` (+ фильтр `animated`), `fetch_art_url`, классы ошибок |
| `steam/arts.py` | `apply_art`, `art_status`, `existing_art`, `find_orphans`, `clean_orphans` |
| `steam/__init__.py` | реэкспорт публичного API → `import steam as engine` работает как раньше |

Каждый модуль stdlib-only и тестируется изолированно.

### Единый формат игры

```
{appid, name, kind: "shortcut" | "steam", icon, status}
```

`status` — `{art_type: bool}` по `ART_TYPES`, как сейчас.

## Фичи

### 1. Вкладка «Установленные» (Steam-игры)
`load_installed(steam_path)` читает `libraryfolders.vdf` → все библиотеки →
`steamapps/appmanifest_*.acf` (текстовый VDF: `appid`, `name`, `installdir`). Обе категории
игр приводятся к единому формату. Переключатель вкладок в сайдбаре. Применение арта идентично —
те же `grid/<appid><suffix>`. Очистка осиротевших по-прежнему трогает только appid ≥ `NONSTEAM_MIN`,
официальные арты Steam-игр в безопасности.

### 2. Анимированные обложки
`list_arts` получает параметр `animated`: при фильтре запрашивается `types=animated` (либо
`animated,static`). SGDB отдаёт анимацию для grids/heroes/logos (для icon — нет). На фронте —
чекбокс «Только анимированные» рядом с вкладками типов. Карточки с анимацией помечаются бейджем ▶
и грузятся как `<img>` (animated webp/apng воспроизводится сам). Применение — как у статики;
Steam понимает анимированные обложки.

### 3. Имена и аватары аккаунтов
`steam/users.py`: uid (account ID) → SteamID64 = `uid + 0x110000100000000`. Имя из
`Steam/config/loginusers.vdf` (`PersonaName`), аватар локально из
`Steam/config/avatarcache/<steamid64>.png` (если есть). `/api/state` отдаёт
`[{uid, name, avatar_url}]`; новый эндпоинт `/api/avatar?account=` стримит локальный файл.
В шапке селект аккаунта показывает аватар + имя; fallback на uid.

### 4. Ревью и починка UI (через `/frontend-design`)
На этапе реализации фронтенд прогоняется через скилл frontend-design: чиним сломанные элементы,
аспекты карточек/сетку (грабли из CLAUDE.md), приводим к цельному дизайну с новыми элементами
(вкладки, фильтр анимации, аватары, предпросмотр).

### 5. Английский язык
`web/i18n.js`: словари `ru`/`en`, функция `t(key)`, переключатель RU/EN в шапке, выбор в
`localStorage`. Все строки UI выносятся в словари. Бэкенд языконезависим.

### 6. Иконки игр в списке
- non-Steam: поле `icon` из `shortcuts.vdf` (путь к локальному .ico/.png).
- Steam: `Steam/appcache/librarycache/<appid>_icon.jpg` (или иконка из `steamapps`).

Новый эндпоинт `/api/gameicon?account=&appid=` стримит локальный файл; в списке — миниатюра
слева от названия, fallback на иконку-заглушку. Это самый хрупкий пункт (разные места хранения) —
при отсутствии файла просто показываем заглушку, не падаем.

### 7. Крупный предпросмотр перед установкой
Клик по карточке (или по кнопке-лупе рядом с «Установить») открывает лайтбокс с полноразмерным
артом (`a.url`), размерами/стилем и кнопкой «Установить» внутри. Закрытие по Esc/клику на фон.

## Production

### Автотесты (`tests/`, stdlib `unittest`, оффлайн)
- `test_vdf.py` — бинарный и текстовый VDF на фикстурах (мини `shortcuts.vdf`, `appmanifest`, `loginusers`).
- `test_library.py` — `load_shortcuts` + `load_installed` на временных папках-фикстурах.
- `test_arts.py` — `apply_art`/`existing_art`/`find_orphans` во `tmp`.
- `test_users.py` — uid↔SteamID64, парсинг имени.
- `test_api.py` — `Server` в треде, дёргаем `/api/...` с замоканным движком (monkeypatch SGDB), без сети.

SGDB-сеть мокается — тесты детерминированы и оффлайн.

### Краевые случаи
Нет Steam / нет ключа / нет сети / пустые списки / битый VDF / Steam запущен / нет аватара/иконки —
аккуратные состояния в UI (тосты, заглушки), без падений.

### Сборка в .exe
`build.py` + `run_build.bat`: PyInstaller, один `--onefile --windowed` exe из `steam_art_app.py`.
`web/` в бандле (`--add-data`), путь к ресурсам через `sys._MEIPASS`. Иконка приложения.
`steam_art.key` НЕ бандлится (создаётся рядом с exe при первом вводе ключа). PyInstaller —
dev-зависимость, в движок не тянется.

### Доки
Обновить `README.md` (новые фичи, сборка exe, запуск тестов) и `CLAUDE.md` (модульная структура,
источники данных, i18n-грабли).

## Порядок реализации

1. Рефакторинг движка на пакет `steam/` + тесты (зелёные) — фундамент.
2. Бэкенд: installed games, users/avatars, icons, animated, новые эндпоинты + тесты.
3. Фронтенд: вкладки, фильтр анимации, аватары, иконки, предпросмотр, i18n.
4. Ревью UI через `/frontend-design`, починка.
5. Сборка exe + финальные доки.

## Вне scope (YAGNI)

- Steam Web API / неустановленные купленные игры.
- Запись в `shortcuts.vdf` (только чтение — безопасно при запущенном Steam).
- Кроссплатформенность за пределами Windows (целевая ОС — Windows).
