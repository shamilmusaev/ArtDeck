# -*- coding: utf-8 -*-
"""Парсинг бинарного VDF (shortcuts.vdf) + регистронезависимый доступ к dict."""
import struct


def parse_binary_vdf(data):
    """Разбирает бинарный VDF в dict. Типы: 0x00 map, 0x01 str, 0x02 int32, 0x08 end."""
    pos = 0

    def read_cstring():
        nonlocal pos
        end = data.index(b"\x00", pos)
        s = data[pos:end].decode("utf-8", "replace")
        pos = end + 1
        return s

    def read_map():
        nonlocal pos
        result = {}
        while True:
            t = data[pos]
            pos += 1
            if t == 0x08:
                return result
            key = read_cstring()
            if t == 0x00:
                result[key] = read_map()
            elif t == 0x01:
                result[key] = read_cstring()
            elif t == 0x02:
                result[key] = struct.unpack_from("<i", data, pos)[0]
                pos += 4
            elif t == 0x07:
                result[key] = struct.unpack_from("<q", data, pos)[0]
                pos += 8
            else:
                raise ValueError("Неизвестный тип VDF: 0x%02x на позиции %d" % (t, pos))

    t = data[pos]
    pos += 1
    read_cstring()  # "shortcuts"
    return read_map()


def get_ci(d, key):
    """Достаёт значение из dict без учёта регистра ключа."""
    kl = key.lower()
    for k, v in d.items():
        if k.lower() == kl:
            return v
    return None
