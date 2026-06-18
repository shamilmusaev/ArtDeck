# -*- coding: utf-8 -*-
"""Extract an application icon from a Windows .exe/.dll into a .ico file.

A non-Steam shortcut often has an empty `icon` field (or one pointing at the
.exe itself). Steam shows an icon anyway because it extracts it straight from
the executable's resources. We do the same: read the PE resource directory via
the Win32 API (no extra dependencies) and assemble a standard .ico, which the
window's <img> can render. Results are cached on disk by source path + mtime so
a list render doesn't re-extract per row."""
import ctypes
import hashlib
import os
import struct
import sys
import tempfile

RT_ICON = 3
RT_GROUP_ICON = 14
LOAD_LIBRARY_AS_DATAFILE = 0x00000002

_CACHE_DIR = os.path.join(tempfile.gettempdir(), "artdeck-iconcache")


def _is_int_resource(ptr):
    return (ptr or 0) >> 16 == 0


def _group_icon_to_ico(group, images):
    """Build .ico bytes from a GRPICONDIR blob and its RT_ICON image blobs.

    .ico and the PE group-icon directory share the 6-byte header and the first
    12 bytes of each 14-byte entry; the directory's trailing 2-byte resource id
    becomes a 4-byte file offset in the .ico."""
    _, _, count = struct.unpack("<HHH", group[:6])
    header = struct.pack("<HHH", 0, 1, count)
    entries = bytearray()
    offset = 6 + count * 16
    blobs = []
    for i in range(count):
        base = 6 + i * 14
        width, height, colors, reserved, planes, bits, bytes_in_res, nid = \
            struct.unpack("<BBBBHHIH", group[base:base + 14])
        img = images.get(nid)
        if img is None:
            continue
        entries += struct.pack("<BBBBHHII", width, height, colors, reserved,
                               planes, bits, len(img), offset)
        blobs.append(img)
        offset += len(img)
    if not blobs:
        return None
    return bytes(header) + bytes(entries) + b"".join(blobs)


def _read_pe_icon(path):
    """Return .ico bytes for the first icon group in a PE file, or None."""
    if not (sys.platform == "win32" and path and os.path.isfile(path)):
        return None
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.LoadLibraryExW.restype = ctypes.c_void_p
    k32.LoadLibraryExW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint32]
    k32.FindResourceW.restype = ctypes.c_void_p
    k32.FindResourceW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    k32.LoadResource.restype = ctypes.c_void_p
    k32.LoadResource.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    k32.LockResource.restype = ctypes.c_void_p
    k32.LockResource.argtypes = [ctypes.c_void_p]
    k32.SizeofResource.restype = ctypes.c_uint32
    k32.SizeofResource.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    k32.FreeLibrary.argtypes = [ctypes.c_void_p]
    ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
    k32.EnumResourceNamesW.restype = ctypes.c_int
    k32.EnumResourceNamesW.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                       ENUMPROC, ctypes.c_void_p]

    hmod = k32.LoadLibraryExW(path, None, LOAD_LIBRARY_AS_DATAFILE)
    if not hmod:
        return None
    try:
        # Find the first RT_GROUP_ICON resource name (usually an integer id).
        found = {}

        def _cb(_hm, _type, name, _lp):
            found["name"] = name
            return 0  # stop at the first one

        k32.EnumResourceNamesW(hmod, ctypes.c_void_p(RT_GROUP_ICON), ENUMPROC(_cb), 0)
        name = found.get("name")
        if name is None:
            return None

        def _load(res_type, res_name):
            h = k32.FindResourceW(hmod, res_name, res_type)
            if not h:
                return None
            size = k32.SizeofResource(hmod, h)
            data = k32.LockResource(k32.LoadResource(hmod, h))
            if not data or not size:
                return None
            return ctypes.string_at(data, size)

        group = _load(RT_GROUP_ICON, name)
        if not group:
            return None
        _, _, count = struct.unpack("<HHH", group[:6])
        images = {}
        for i in range(count):
            nid = struct.unpack("<H", group[6 + i * 14 + 12:6 + i * 14 + 14])[0]
            img = _load(RT_ICON, ctypes.c_void_p(nid))
            if img:
                images[nid] = img
        return _group_icon_to_ico(group, images)
    except Exception:
        return None
    finally:
        k32.FreeLibrary(hmod)


def icon_file(exe_path):
    """Path to a cached .ico extracted from exe_path, or None. Cache key is the
    source path + mtime, so a changed executable re-extracts."""
    if not (sys.platform == "win32" and exe_path and os.path.isfile(exe_path)):
        return None
    try:
        mtime = int(os.path.getmtime(exe_path))
    except OSError:
        return None
    key = hashlib.sha1(("%s|%d" % (exe_path.lower(), mtime)).encode("utf-8")).hexdigest()
    dest = os.path.join(_CACHE_DIR, key + ".ico")
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        return dest
    ico = _read_pe_icon(exe_path)
    if not ico:
        return None
    os.makedirs(_CACHE_DIR, exist_ok=True)
    tmp = dest + ".tmp"
    with open(tmp, "wb") as f:
        f.write(ico)
    os.replace(tmp, dest)
    return dest
