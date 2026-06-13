"use strict";
/* ArtDeck — словари локализации (RU/EN) + крошечный движок t().
   Язык хранится в localStorage("artdeck.lang"). По умолчанию — RU. */

const I18N = {
  ru: {
    tagline: "обложки для твоей библиотеки",
    account: "Аккаунт",
    key_ok: "Ключ: OK",
    key_none: "Ключ: нет",
    key_btn: "Ключ",
    autofill: "Авто-дозаливка",
    clean: "Очистка",
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
    apply: "Установить",
    preview: "Просмотр",
    none_short: "нет",
    no_variants: "Нет вариантов в базе для этого типа",
    pick_to_see: "Выбери игру, чтобы увидеть варианты обложек ✨",
    load_variants_err: "Не загрузить варианты: ",

    applied: (f) => `Установлено: ${f} · перезапусти Steam`,
    apply_err: "Ошибка применения: ",
    games_err: "Не загрузить игры: ",
    steam_not_found: "Steam не найден",
    no_key_hint: "Нет API-ключа — нажми «Ключ»",
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
  },

  en: {
    tagline: "cover art for your library",
    account: "Account",
    key_ok: "Key: OK",
    key_none: "Key: none",
    key_btn: "Key",
    autofill: "Auto-fill",
    clean: "Cleanup",
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
    apply: "Apply",
    preview: "Preview",
    none_short: "none",
    no_variants: "No variants in the database for this type",
    pick_to_see: "Pick a game to see cover options ✨",
    load_variants_err: "Couldn't load variants: ",

    applied: (f) => `Applied: ${f} · restart Steam`,
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
  },
};

let LANG = localStorage.getItem("artdeck.lang") || "ru";

function t(key, ...args) {
  const dict = I18N[LANG] || I18N.ru;
  const v = dict[key];
  if (typeof v === "function") return v(...args);
  return v != null ? v : key;
}

function setLang(lang) {
  LANG = I18N[lang] ? lang : "ru";
  localStorage.setItem("artdeck.lang", LANG);
}

function nextLang() {
  return LANG === "ru" ? "en" : "ru";
}
