# -*- coding: utf-8 -*-
"""Генерация PNG-палитры (цветные плашки) чистым Python — только zlib/struct."""

import struct
import zlib

from colors import hex_to_rgb


def _png(width, height, raw_rows):
    def chunk(typ, data):
        body = typ + data
        return (struct.pack(">I", len(data)) + body +
                struct.pack(">I", zlib.crc32(body) & 0xffffffff))
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    idat = zlib.compress(b"".join(raw_rows), 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def make_palette_png(hex_list, width=770, height=150, gap=6):
    """Рисует вертикальные плашки по списку HEX. Возвращает bytes PNG."""
    n = max(1, len(hex_list))
    band = max(1, (width - gap * (n + 1)) // n)
    width = gap * (n + 1) + band * n
    colors = [hex_to_rgb(h) for h in hex_list]
    bg = (14, 15, 19)  # тёмный фон под плашки

    # строим одну строку пикселей (все строки одинаковые, кроме рамок сверху/снизу)
    line = bytearray()
    x = 0
    while x < width:
        # определяем, попадаем ли в плашку или в промежуток
        pos = x
        idx = None
        cx = gap
        for i in range(n):
            if cx <= pos < cx + band:
                idx = i
                break
            cx += band + gap
        r, g, b = colors[idx] if idx is not None else bg
        line += bytes((r, g, b))
        x += 1

    rows = []
    for y in range(height):
        edge = y < gap or y >= height - gap
        if edge:
            rows.append(b"\x00" + bytes(bg * width))
        else:
            rows.append(b"\x00" + bytes(line))
    return _png(width, height, rows)


if __name__ == "__main__":
    png = make_palette_png(["#FF1E56", "#00E0D0", "#1E90FF", "#0A0A0A", "#FFFFFF"])
    with open("palette_demo.png", "wb") as f:
        f.write(png)
    print("Сохранено palette_demo.png,", len(png), "байт")
