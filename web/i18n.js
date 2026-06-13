"use strict";
/* ArtDeck — словари локализации (RU/EN) + крошечный движок t().
   Язык хранится в localStorage("artdeck.lang"). По умолчанию — RU. */

const I18N = {
  ru: {
    tagline: "обложки для твоей библиотеки",
    account: "Аккаунт",
    key_ok: "API-ключ: OK",
    key_none: "Ключ: нет",
    key_need: "Вставьте API-ключ",
    key_btn: "API-ключ",
    autofill: "Дозалить недостающее",
    clean: "Удалить лишние",
    lang_name: "RU",

    tab_nonsteam: "Non-Steam",
    tab_installed: "Установленные",

    filter_games: "Поиск игры…",
    search_sgdb: "Найти другую игру на SteamGridDB…",
    pick_game: "Выбери игру слева",
    searching: "Поиск совпадения на SteamGridDB…",
    not_found_manual: "Не найдено — попробуй ручной поиск",
    search_error: "Ошибка поиска: ",
    found_n: n => `Найдено: ${n}`,
    nothing_found: "Ничего не найдено",

    t_cover: "Обложка",
    t_banner: "Баннер",
    t_hero: "Hero",
    t_logo: "Logo",
    t_icon: "Icon",

    only_animated: "Только анимированные",
    current: "Текущая",
    current_cap: "Стоит в Steam",
    current_hint: "Текущая обложка в Steam — нажми, чтобы рассмотреть",
    apply: "Установить",
    preview: "Просмотр",
    none_short: "нет",
    no_variants: "Нет вариантов в базе для этого типа",
    pick_to_see: "Выбери игру, чтобы увидеть варианты обложек ✨",
    load_variants_err: "Не загрузить варианты: ",

    applied: (f) => `Установлено: ${f} · перезапусти Steam`,
    warn_competing: "Применено, но в этом слоте остался старый файл — Steam может показать его. Закрой Steam и повтори.",
    warn_corrupt: "Файл скачался повреждённым — попробуй другой вариант.",
    revert: "Вернуть оригинал",
    revert_hint: "Убрать наш арт и вернуть оригинал Steam",
    reverted: "Возвращён оригинал Steam · перезапусти Steam",
    nothing_to_revert: "Нашего арта тут нет",
    apply_err: "Ошибка применения: ",
    games_err: "Не загрузить игры: ",
    steam_not_found: "Steam не найден",
    no_key_hint: "Нужен API-ключ SteamGridDB — нажмите «Вставьте API-ключ» вверху справа",
    error: "Ошибка: ",

    autofill_title: "Авто-дозаливка недостающего",
    autofill_body: "Скачать все недостающие арты и заполнить пробелы? Существующее не трогается.",
    autofill_all: "Все аккаунты (иначе только текущий)",
    cancel: "Отмена",
    run: "Запустить",
    prepare: "Подготовка…",
    to_process: n => `Игр к обработке: ${n}`,
    autofill_done: (ok, skip, fail) => `Дозаливка: +${ok}, пропущено ${skip}, ошибок ${fail} · перезапусти Steam`,
    conn_lost: "Соединение прервано",

    clean_title: n => `Очистка осиротевших (${n})`,
    no_orphans: "Осиротевших артов нет",
    delete_chosen: "Удалить выбранное",
    account_label: "аккаунт ",
    removed_n: n => `Удалено файлов: ${n}`,

    key_title: "API-ключ SteamGridDB",
    key_hint: "steamgriddb.com → Preferences → API",
    key_placeholder: "Вставь ключ…",
    save: "Сохранить",
    key_saved: "Ключ сохранён",
    key_cleared: "Ключ очищен",

    disclaimer: "ArtDeck не аффилирован с Valve или SteamGridDB.",
    animated_badge: "ANIM",

    cov_have: "Обложка есть",
    cov_need: "Нужна обложка",
    cov_full: "Все арты на месте",
    cov_count: n => `${n}/5 артов`,
    cov_missing: "не хватает",
  },

  en: {
    tagline: "cover art for your library",
    account: "Account",
    key_ok: "API key: OK",
    key_none: "Key: none",
    key_need: "Add API key",
    key_btn: "API key",
    autofill: "Fill missing art",
    clean: "Remove extras",
    lang_name: "EN",

    tab_nonsteam: "Non-Steam",
    tab_installed: "Installed",

    filter_games: "Search game…",
    search_sgdb: "Find another game on SteamGridDB…",
    pick_game: "Pick a game on the left",
    searching: "Matching on SteamGridDB…",
    not_found_manual: "Not found — try a manual search",
    search_error: "Search error: ",
    found_n: n => `Found: ${n}`,
    nothing_found: "Nothing found",

    t_cover: "Cover",
    t_banner: "Banner",
    t_hero: "Hero",
    t_logo: "Logo",
    t_icon: "Icon",

    only_animated: "Animated only",
    current: "Current",
    current_cap: "Set in Steam",
    current_hint: "Current art in Steam — click to view",
    apply: "Apply",
    preview: "Preview",
    none_short: "none",
    no_variants: "No variants in the database for this type",
    pick_to_see: "Pick a game to see cover options ✨",
    load_variants_err: "Couldn't load variants: ",

    applied: (f) => `Applied: ${f} · restart Steam`,
    warn_competing: "Applied, but an old file remains in this slot — Steam may show it. Close Steam and retry.",
    warn_corrupt: "The file downloaded corrupted — try another variant.",
    revert: "Restore original",
    revert_hint: "Remove our art and restore Steam's original",
    reverted: "Restored Steam's original · restart Steam",
    nothing_to_revert: "No custom art here",
    apply_err: "Apply error: ",
    games_err: "Couldn't load games: ",
    steam_not_found: "Steam not found",
    no_key_hint: "No API key — click “Key”",
    error: "Error: ",

    autofill_title: "Auto-fill missing art",
    autofill_body: "Download all missing art and fill the gaps? Existing art is left untouched.",
    autofill_all: "All accounts (otherwise current only)",
    cancel: "Cancel",
    run: "Run",
    prepare: "Preparing…",
    to_process: n => `Games to process: ${n}`,
    autofill_done: (ok, skip, fail) => `Auto-fill: +${ok}, skipped ${skip}, errors ${fail} · restart Steam`,
    conn_lost: "Connection lost",

    clean_title: n => `Clean orphans (${n})`,
    no_orphans: "No orphaned art",
    delete_chosen: "Delete selected",
    account_label: "account ",
    removed_n: n => `Files removed: ${n}`,

    key_title: "SteamGridDB API key",
    key_hint: "steamgriddb.com → Preferences → API",
    key_placeholder: "Paste your key…",
    save: "Save",
    key_saved: "Key saved",
    key_cleared: "Key cleared",

    disclaimer: "ArtDeck is not affiliated with Valve or SteamGridDB.",
    animated_badge: "ANIM",

    cov_have: "Cover ready",
    cov_need: "Needs cover",
    cov_full: "All art present",
    cov_count: n => `${n}/5 art`,
    cov_missing: "missing",
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
