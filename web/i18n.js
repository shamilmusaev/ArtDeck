"use strict";
/* ArtDeck localization dictionaries (RU/EN) plus a tiny t() engine.
   Language is stored in localStorage("artdeck.lang"); default is EN. */

const I18N = {
  ru: {
    account: "Аккаунт",
    key_need: "Вставьте API-ключ",
    key_btn: "API-ключ",
    autofill: "Дозалить недостающее",
    clean: "Удалить лишние",
    tip_autofill: "Скачать и поставить все недостающие арты для игр этого аккаунта. Существующее не трогается.",
    tip_clean: "Удалить осиротевшие арт-файлы: обложки игр, которых больше нет в Steam.",
    tip_sidebar_hide: "Скрыть сайдбар",
    tip_sidebar_show: "Показать сайдбар",
    sidebar_collapse: "Свернуть",
    lang_name: "RU",

    tab_nonsteam: "Non-Steam",
    tab_installed: "Steam",
    games_section: "Игры",

    filter_games: "Поиск игры…",
    search_sgdb: "Найти другую игру на SteamGridDB…",
    search_error: "Ошибка поиска: ",
    nothing_found: "Ничего не найдено",

    t_cover: "Обложка",
    t_banner: "Баннер",
    t_hero: "Hero",
    t_logo: "Logo",

    only_animated: "Только анимированные",
    current: "Текущая",
    current_hint: "Текущая обложка в Steam, нажми чтобы рассмотреть",
    apply: "Установить",
    preview: "Просмотр",
    none_short: "нет",
    no_variants: "Нет вариантов в базе для этого типа",
    pick_to_see: "Выбери игру, чтобы увидеть варианты обложек ✨",
    load_variants_err: "Не загрузить варианты: ",

    applied: (f) => `Установлено: ${f}`,
    warn_competing: "Применено, но в этом слоте остался старый файл, Steam может показать его. Закрой Steam и повтори.",
    warn_corrupt: "Файл скачался повреждённым, попробуй другой вариант.",
    revert: "Вернуть оригинал",
    revert_hint: "Убрать наш арт и вернуть оригинал Steam",
    reverted: "Возвращён оригинал Steam · перезапусти Steam",
    nothing_to_revert: "Нашего арта тут нет",
    apply_err: "Ошибка применения: ",
    games_err: "Не загрузить игры: ",
    refresh: "Обновить список (пере-сканировать)",
    refreshed: "Список игр обновлён",
    scanning: "Сканируем библиотеку…",
    lang_title: "Язык интерфейса",
    steam_not_found: "Steam не найден",
    no_key_hint: "Нужен API-ключ SteamGridDB: нажмите «Вставьте API-ключ» вверху справа",
    need_key_title: "Нужен API-ключ SteamGridDB",
    need_key_body: "Без ключа ArtDeck не может загрузить варианты артов. Ключ бесплатный и берётся за минуту.",
    key_steps: "1. Войди на SteamGridDB.  2. Открой Preferences → API.  3. Нажми «Generate API Key».  4. Скопируй ключ и вставь сюда.",
    key_get: "Получить ключ на SteamGridDB",
    error: "Ошибка: ",

    autofill_title: "Авто-дозаливка недостающего",
    autofill_body: "Скачать все недостающие арты и заполнить пробелы? Существующее не трогается.",
    autofill_all: "Все аккаунты (иначе только текущий)",
    cancel: "Отмена",
    run: "Запустить",
    prepare: "Подготовка…",
    to_process: n => `Игр к обработке: ${n}`,
    autofill_done: (ok, skip, fail) => `Дозаливка: +${ok}, пропущено ${skip}, ошибок ${fail}`,
    conn_lost: "Соединение прервано",

    clean_title: n => `Очистка осиротевших (${n})`,
    no_orphans: "Осиротевших артов нет",
    delete_chosen: "Удалить выбранное",
    account_label: "аккаунт ",
    removed_n: n => `Удалено файлов: ${n}`,

    key_title: "API-ключ SteamGridDB",
    key_placeholder: "Вставь ключ…",
    save: "Сохранить",
    key_saved: "Ключ сохранён",
    key_cleared: "Ключ очищен",

    disclaimer: "ArtDeck не аффилирован с Valve или SteamGridDB.",
    animated_badge: "ANIM",

    mode_covers: "Оформление",
    mode_import: "Импорт игр",
    import_launchers_section: "Лаунчеры",
    import_no_launchers: "Сторонние лаунчеры не найдены",
    import_no_games: "Нет новых игр для импорта",
    import_download_art: "Скачать арты",
    import_add_btn: "Добавить %d в Steam",
    import_close_steam: "Steam запущен. Закрыть его и продолжить?",
    import_close_confirm: "Закрыть и продолжить",
    import_done: "Добавлено: %d — они в твоей библиотеке Steam",
    import_refresh: "Пересканировать лаунчеры",
    import_view_grid: "Сетка",
    import_view_list: "Список",
    import_refreshed: "Лаунчеры пересканированы",
    imported_badge: "В Steam",
    import_hint: "Установите игры в %s — и они появятся здесь",
    customize: "Оформить",
  },

  en: {
    account: "Account",
    key_need: "Add API key",
    key_btn: "API key",
    autofill: "Fill missing art",
    clean: "Remove extras",
    tip_autofill: "Download & set all missing art for this account's games. Existing art is kept.",
    tip_clean: "Delete orphaned art files: covers of games no longer in Steam.",
    tip_sidebar_hide: "Hide sidebar",
    tip_sidebar_show: "Show sidebar",
    sidebar_collapse: "Minimize",
    lang_name: "EN",

    tab_nonsteam: "Non-Steam",
    tab_installed: "Steam",
    games_section: "Games",

    filter_games: "Search game…",
    search_sgdb: "Find another game on SteamGridDB…",
    search_error: "Search error: ",
    nothing_found: "Nothing found",

    t_cover: "Cover",
    t_banner: "Banner",
    t_hero: "Hero",
    t_logo: "Logo",

    only_animated: "Animated only",
    current: "Current",
    current_hint: "Current art in Steam, click to view",
    apply: "Apply",
    preview: "Preview",
    none_short: "none",
    no_variants: "No variants in the database for this type",
    pick_to_see: "Pick a game to see cover options ✨",
    load_variants_err: "Couldn't load variants: ",

    applied: (f) => `Applied: ${f}`,
    warn_competing: "Applied, but an old file remains in this slot, Steam may show it. Close Steam and retry.",
    warn_corrupt: "The file downloaded corrupted, try another variant.",
    revert: "Restore original",
    revert_hint: "Remove our art and restore Steam's original",
    reverted: "Restored Steam's original · restart Steam",
    nothing_to_revert: "No custom art here",
    apply_err: "Apply error: ",
    games_err: "Couldn't load games: ",
    refresh: "Refresh list (rescan)",
    refreshed: "Game list refreshed",
    scanning: "Scanning library…",
    lang_title: "Interface language",
    steam_not_found: "Steam not found",
    no_key_hint: "No API key: click “Add API key” at the top-right",
    need_key_title: "SteamGridDB API key needed",
    need_key_body: "Without a key ArtDeck can't load art variants. It's free and takes a minute.",
    key_steps: "1. Sign in to SteamGridDB.  2. Open Preferences → API.  3. Click “Generate API Key”.  4. Copy the key and paste it here.",
    key_get: "Get a key on SteamGridDB",
    error: "Error: ",

    autofill_title: "Auto-fill missing art",
    autofill_body: "Download all missing art and fill the gaps? Existing art is left untouched.",
    autofill_all: "All accounts (otherwise current only)",
    cancel: "Cancel",
    run: "Run",
    prepare: "Preparing…",
    to_process: n => `Games to process: ${n}`,
    autofill_done: (ok, skip, fail) => `Auto-fill: +${ok}, skipped ${skip}, errors ${fail}`,
    conn_lost: "Connection lost",

    clean_title: n => `Clean orphans (${n})`,
    no_orphans: "No orphaned art",
    delete_chosen: "Delete selected",
    account_label: "account ",
    removed_n: n => `Files removed: ${n}`,

    key_title: "SteamGridDB API key",
    key_placeholder: "Paste your key…",
    save: "Save",
    key_saved: "Key saved",
    key_cleared: "Key cleared",

    disclaimer: "ArtDeck is not affiliated with Valve or SteamGridDB.",
    animated_badge: "ANIM",

    mode_covers: "Artwork",
    mode_import: "Import games",
    import_launchers_section: "Launchers",
    import_no_launchers: "No third-party launchers found",
    import_no_games: "No new games to import",
    import_download_art: "Download art",
    import_add_btn: "Add %d to Steam",
    import_close_steam: "Steam is running. Close it and continue?",
    import_close_confirm: "Close & continue",
    import_done: "Added %d — they're in your Steam library",
    import_refresh: "Rescan launchers",
    import_view_grid: "Grid view",
    import_view_list: "List view",
    import_refreshed: "Launchers rescanned",
    imported_badge: "In Steam",
    import_hint: "Install games in %s and they'll appear here",
    customize: "Customize",
  },
};

let LANG = localStorage.getItem("artdeck.lang") || "en";

function t(key, ...args) {
  const dict = I18N[LANG] || I18N.en;
  const v = dict[key];
  if (typeof v === "function") return v(...args);
  return v != null ? v : key;
}

function setLang(lang) {
  LANG = I18N[lang] ? lang : "en";
  localStorage.setItem("artdeck.lang", LANG);
}

function nextLang() {
  return LANG === "ru" ? "en" : "ru";
}
