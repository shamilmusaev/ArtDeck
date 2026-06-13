# -*- coding: utf-8 -*-
"""Парсинг бинарного VDF (shortcuts.vdf) + регистронезависимый доступ к dict."""
import struct


def parse_binary_vdf(data):
    """Разбирает бинарный VDF в dict. Типы: 0x00 map, 0x01 str, 0x02 int32, 0x07 int64, 0x08 end."""
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


_VDF_ESCAPES = {"n": "\n", "t": "\t"}


def _tokenize_text_vdf(text):
    """Токенайзер текстового VDF: кавыченные строки, { и }, // комментарии."""
    tokens = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j == -1 else j + 1
        elif c == "{" or c == "}":
            tokens.append(c)
            i += 1
        elif c == '"':
            i += 1
            buf = []
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n:
                    nxt = text[i + 1]
                    buf.append(_VDF_ESCAPES.get(nxt, nxt))
                    i += 2
                else:
                    buf.append(text[i])
                    i += 1
            tokens.append("".join(buf))
            i += 1  # закрывающая кавычка
        else:
            # неэкранированный токен (редко в Steam-файлах)
            j = i
            while j < n and text[j] not in ' \t\r\n"{}':
                j += 1
            tokens.append(text[i:j])
            i = j
    return tokens


def parse_text_vdf(text):
    """Разбирает текстовый VDF (.acf, libraryfolders.vdf, loginusers.vdf) в dict."""
    tokens = _tokenize_text_vdf(text)
    pos = 0

    def parse_obj():
        nonlocal pos
        obj = {}
        while pos < len(tokens):
            tok = tokens[pos]
            if tok == "}":
                pos += 1
                return obj
            pos += 1
            key = tok
            if pos < len(tokens) and tokens[pos] == "{":
                pos += 1
                obj[key] = parse_obj()
            elif pos < len(tokens) and tokens[pos] != "}":
                obj[key] = tokens[pos]
                pos += 1
            else:
                obj[key] = ""  # ключ без значения — не «съедаем» закрывающую }
        return obj

    return parse_obj()
