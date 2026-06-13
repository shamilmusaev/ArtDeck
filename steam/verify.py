# -*- coding: utf-8 -*-
"""Пост-проверка применённого арта. Steam не сообщает «показал ли он обложку»,
но мы можем поймать реальные причины, по которым она не появляется:
  - файл повреждён/нулевой (битая загрузка),
  - в том же слоте остался файл другого расширения, который не удалось удалить
    (обычно Steam держал его открытым) → Steam покажет старый файл,
  - (для анимации) не записалась регистрация customimage."""
import os

from steam.arts import ART_TYPES, ART_EXTS


def valid_image(path):
    """Файл существует, не пустой и начинается с сигнатуры PNG/JPEG/WEBP/GIF."""
    try:
        if os.path.getsize(path) == 0:
            return False
        with open(path, "rb") as f:
            h = f.read(12)
    except OSError:
        return False
    if h[:4] == b"\x89PNG":
        return True
    if h[:3] == b"\xff\xd8\xff":
        return True
    if h[:4] == b"RIFF" and h[8:12] == b"WEBP":
        return True
    if h[:4] in (b"GIF8",):
        return True
    return False


def competing_files(grid_dir, appid, art_type, applied_path):
    """Файлы того же слота (<appid><suffix>) с другим расширением — их Steam может
    показать вместо только что применённого."""
    suffix = ART_TYPES[art_type]["suffix"]
    applied = os.path.basename(applied_path).lower()
    out = []
    for e in ART_EXTS:
        name = "%d%s%s" % (appid, suffix, e)
        if name.lower() == applied:
            continue
        if os.path.isfile(os.path.join(grid_dir, name)):
            out.append(name)
    return out


def verify_applied(grid_dir, appid, art_type, dest):
    """Проверяет применённый арт. Возвращает {ok, code, files}.
    code: None (всё хорошо) | 'corrupt' (битый файл) | 'competing' (дубль в слоте)."""
    if not dest or not os.path.isfile(dest) or not valid_image(dest):
        return {"ok": False, "code": "corrupt", "files": []}
    comp = competing_files(grid_dir, appid, art_type, dest)
    if comp:
        return {"ok": False, "code": "competing", "files": comp}
    return {"ok": True, "code": None, "files": []}
