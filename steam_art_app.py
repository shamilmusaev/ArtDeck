#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
steam_art_app.py
================
Современный интерфейс (стекло + неон) для steam_art в нативном окне (pywebview).
Локальный HTTP-сервер на stdlib отдаёт фронтенд (web/) и JSON-API, бэкенд — движок
steam_art.py.

Запуск:  run_app.bat   (или:  python steam_art_app.py)
Зависимости: pywebview (нативное окно). Без него откроется в браузере.
"""

import http.server
import socketserver
import socket
import json
import os
import sys
import threading
import urllib.parse
import mimetypes

SCRIPTDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTDIR)

import steam as engine

# В собранном exe (PyInstaller --onefile) ресурсы web/ распакованы в sys._MEIPASS.
WEBDIR = os.path.join(getattr(sys, "_MEIPASS", SCRIPTDIR), "web")
STEAM = engine.find_steam_path(None)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    # ---- helpers ----
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _err(self, msg, code=400):
        self._json({"error": str(msg)}, code)

    def _read_json(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw or b"{}")
        except Exception:
            return {}

    def _send_file(self, path, cache=True):
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "max-age=86400" if cache else "no-cache")
        self.end_headers()
        self.wfile.write(data)

    # ---- GET ----
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        path = u.path
        try:
            if path in ("/", ""):
                return self._send_index()
            if path == "/img":
                return self._serve_current(q)
            if path == "/api/avatar":
                return self._serve_avatar(q)
            if path == "/api/gameicon":
                return self._serve_gameicon(q)
            if path.startswith("/api/"):
                return self._api_get(path, q)
            # Static files from web/. Resolve the request against WEBDIR and require
            # the result to stay inside it — a bare lstrip lets a Windows drive-letter
            # or backslash path (/C:/.., /\..\..) escape and read arbitrary files.
            full = os.path.normpath(os.path.join(WEBDIR, path.lstrip("/")))
            root = os.path.normpath(WEBDIR)
            try:
                inside = os.path.commonpath((full, root)) == root
            except ValueError:
                inside = False
            if not inside:
                return self._err("forbidden", 403)
            if os.path.isfile(full):
                return self._send_file(full, cache=False)
            return self._err("not found", 404)
        except BrokenPipeError:
            pass
        except Exception as e:
            try:
                self._err(e, 500)
            except Exception:
                pass

    def _api_get(self, path, q):
        key = engine.load_api_key(None)
        if path == "/api/state":
            accounts = engine.list_accounts(STEAM) if STEAM else []
            return self._json({
                "steam_path": STEAM,
                "accounts": engine.account_infos(STEAM, accounts) if STEAM else [],
                "key_ok": bool(key),
                "key": key or "",
            })
        if path == "/api/games":
            acc = q.get("account", [None])[0]
            source = q.get("source", ["shortcut"])[0]
            if acc and STEAM:
                games = (engine.installed_games(STEAM, acc) if source == "installed"
                         else engine.list_games(STEAM, acc))
            else:
                games = []
            is_installed = source == "installed"
            out = [{
                "appid": g["appid"],
                "name": engine.clean_name(g["name"]),
                "kind": g.get("kind", "shortcut"),
                # status[t] = НАШ кастомный арт; official[t] = официальный арт Steam (установленные)
                "status": {t: bool(g["status"][t]) for t in engine.ART_TYPES},
                "official": ({t: engine.official_art(STEAM, g["appid"], t) is not None
                              for t in engine.ART_TYPES}
                             if is_installed else {t: False for t in engine.ART_TYPES}),
            } for g in games]
            out.sort(key=lambda g: g["name"].lower())
            return self._json({"games": out, "source": source})
        if path == "/api/search":
            if not key:
                return self._err("no-key", 400)
            term = q.get("q", [""])[0]
            return self._json({"results": engine.search_games(term, key)})
        if path == "/api/arts":
            if not key:
                return self._err("no-key", 400)
            try:
                gid = int(q.get("game_id", [0])[0])
            except ValueError:
                return self._err("bad id", 400)
            t = q.get("type", ["cover"])[0]
            animated = q.get("animated", ["0"])[0] in ("1", "true", "yes")
            try:
                return self._json({"arts": engine.list_arts(gid, t, key, animated=animated)})
            except engine.SGDBError as e:
                return self._err(e, 502)
        if path == "/api/orphans":
            items = []
            for uid in (engine.list_accounts(STEAM) if STEAM else []):
                vdf, _ = engine.account_paths(STEAM, uid)
                _, orph = engine.find_orphans(vdf)
                for fn in orph:
                    items.append({"account": uid, "file": fn})
            return self._json({"items": items})
        if path == "/api/autofill":
            return self._autofill_sse(q, key)
        if path == "/api/open":
            u2 = q.get("url", [""])[0]
            # Match the host exactly — a startswith check accepts
            # steamgriddb.com.evil.com and steamgriddb.com@evil.com.
            host = urllib.parse.urlparse(u2).hostname or ""
            if u2.startswith("https://") and host in ("steamgriddb.com", "www.steamgriddb.com"):
                import webbrowser
                webbrowser.open(u2)
                return self._json({"ok": True})
            return self._err("bad-url", 400)
        return self._err("unknown", 404)

    def _send_index(self):
        p = os.path.join(WEBDIR, "index.html")
        with open(p, encoding="utf-8") as f:
            html = f.read()
        try:
            ver = str(int(max(os.path.getmtime(os.path.join(WEBDIR, x))
                              for x in ("style.css", "app.js", "i18n.js"))))
        except OSError:
            ver = "0"
        html = (html.replace('href="style.css"', 'href="style.css?v=%s"' % ver)
                    .replace('src="i18n.js"', 'src="i18n.js?v=%s"' % ver)
                    .replace('src="app.js"', 'src="app.js?v=%s"' % ver))
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def _serve_current(self, q):
        uid = q.get("account", [None])[0]
        t = q.get("type", ["cover"])[0]
        try:
            appid = int(q.get("appid", [None])[0])
        except (TypeError, ValueError):
            return self._err("bad id", 400)
        if not (uid and STEAM) or t not in engine.ART_TYPES:
            return self._err("bad", 400)
        _, grid = engine.account_paths(STEAM, uid)
        p = engine.existing_art(grid, appid, engine.ART_TYPES[t]["suffix"])
        if not p or not os.path.isfile(p):
            p = engine.official_art(STEAM, appid, t)  # fall back to Steam's own art (installed games)
        if not p or not os.path.isfile(p):
            return self._err("none", 404)
        self._send_file(p, cache=False)

    def _serve_avatar(self, q):
        uid = q.get("account", [None])[0]
        if not (uid and STEAM):
            return self._err("bad", 400)
        p = engine.account_avatar_path(STEAM, uid)
        if not p:
            return self._err("none", 404)
        self._send_file(p, cache=False)

    def _game_icon_file(self, uid, appid):
        """Путь к иконке игры: сперва ищем среди non-Steam ярлыков аккаунта,
        иначе считаем Steam-игрой и берём из librarycache."""
        vdf, _ = engine.account_paths(STEAM, uid)
        for g in engine.load_shortcuts(vdf):
            if g["appid"] == appid:
                return engine.game_icon_path(STEAM, g)
        return engine.steam_game_image(STEAM, appid)

    def _serve_gameicon(self, q):
        uid = q.get("account", [None])[0]
        try:
            appid = int(q.get("appid", [0])[0])
        except ValueError:
            return self._err("bad id", 400)
        if not (uid and STEAM):
            return self._err("bad", 400)
        p = self._game_icon_file(uid, appid)
        if not p or not os.path.isfile(p):
            return self._err("none", 404)
        self._send_file(p, cache=False)

    def _autofill_sse(self, q, key):
        if not key:
            return self._err("no-key", 400)
        acc = q.get("accounts", ["all"])[0]
        if not STEAM:
            accts = []
        elif acc == "all":
            accts = engine.list_accounts(STEAM)
        else:
            accts = [acc]

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def send(ev):
            try:
                self.wfile.write(("data: " + json.dumps(ev, ensure_ascii=False) + "\n\n").encode("utf-8"))
                self.wfile.flush()
                return True
            except (BrokenPipeError, ConnectionError, OSError):
                return False

        work = []
        for uid in accts:
            vdf, grid = engine.account_paths(STEAM, uid)
            if not os.path.isfile(vdf):
                continue
            for g in engine.load_shortcuts(vdf):
                status = engine.art_status(grid, g["appid"])
                missing = [t for t in engine.ART_TYPES if not status[t]]
                if missing:
                    work.append((uid, grid, g, missing))

        total = len(work)
        ok = fail = skip = 0
        if not send({"type": "start", "total": total}):
            return
        for i, (uid, grid, g, missing) in enumerate(work):
            if not send({"type": "progress", "i": i + 1, "total": total,
                         "game": engine.clean_name(g["name"])}):
                return
            try:
                gid, _ = engine.search_game_id(g["name"], key)
            except engine.SGDBAuthError as e:
                send({"type": "error", "message": str(e)})
                return
            except engine.SGDBError:
                fail += len(missing)
                continue
            if not gid:
                skip += len(missing)
                continue
            for t in missing:
                try:
                    url = engine.fetch_art_url(gid, engine.ART_TYPES[t], key)
                    if url:
                        engine.apply_art(grid, g["appid"], t, url)
                        try:
                            engine.register_custom_image(STEAM, uid, g["appid"])
                        except Exception:
                            pass
                        ok += 1
                    else:
                        skip += 1
                except engine.SGDBAuthError as e:
                    send({"type": "error", "message": str(e)})
                    return
                except engine.SGDBError:
                    fail += 1
        send({"type": "done", "ok": ok, "fail": fail, "skip": skip})

    # ---- POST ----
    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        data = self._read_json()
        try:
            if u.path == "/api/apply":
                uid = data["account"]
                appid = int(data["appid"])
                t = data["type"]
                url = data["url"]
                _, grid = engine.account_paths(STEAM, uid)
                dest = engine.apply_art(grid, appid, t, url)
                # регистрируем в кэше нового клиента Steam (иначе анимация не играет)
                try:
                    engine.register_custom_image(STEAM, uid, appid)
                except Exception:
                    pass
                # пост-проверка: битый файл / конкурент в слоте → предупреждаем UI
                warn = None
                try:
                    v = engine.verify_applied(grid, appid, t, dest)
                    if not v["ok"]:
                        warn = v["code"]
                except Exception:
                    pass
                return self._json({"ok": True, "dest": os.path.basename(dest), "warn": warn})
            if u.path == "/api/revert":
                uid = data["account"]
                appid = int(data["appid"])
                t = data["type"]
                _, grid = engine.account_paths(STEAM, uid)
                removed = engine.revert_art(grid, appid, t)
                return self._json({"ok": True, "removed": removed})
            if u.path == "/api/clean":
                # Recompute the real orphan set per account and only delete files in
                # it — never os.remove a client-supplied path (traversal / arbitrary
                # delete, and find_orphans enforces the non-Steam appid guard).
                removed = 0
                allow = {}
                for it in data.get("items", []):
                    acc = it.get("account")
                    if acc not in allow:
                        vdf, _ = engine.account_paths(STEAM, acc) if STEAM else (None, None)
                        allow[acc] = engine.find_orphans(vdf) if vdf else (None, [])
                    grid, orphans = allow[acc]
                    if not grid or it.get("file") not in orphans:
                        continue
                    try:
                        os.remove(os.path.join(grid, it["file"]))
                        removed += 1
                    except OSError:
                        pass
                return self._json({"removed": removed})
            if u.path == "/api/key":
                val = (data.get("key") or "").strip()
                engine.save_api_key(val)
                return self._json({"ok": True, "key_ok": bool(val), "key": val})
            return self._err("unknown", 404)
        except Exception as e:
            return self._err(e, 500)


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def main():
    port = free_port()
    srv = Server(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d/" % port
    print("ArtDeck UI:", url)
    try:
        import webview
        webview.create_window("ArtDeck", url, width=1280, height=820,
                              min_size=(1024, 640), background_color="#0a0b10")
        webview.start()
    except Exception as e:
        print("pywebview недоступен (%s), открываю в браузере…" % e)
        import webbrowser
        webbrowser.open(url)
        threading.Event().wait()


if __name__ == "__main__":
    main()
