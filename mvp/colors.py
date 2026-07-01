# -*- coding: utf-8 -*-
"""Приблизительные русские названия цветов по HEX (без внешних зависимостей)."""


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hsl(hex_code):
    r, g, b = [c / 255.0 for c in hex_to_rgb(hex_code)]
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    l = (mx + mn) / 2
    if d == 0:
        return 0.0, 0.0, l
    s = d / (1 - abs(2 * l - 1)) if 0 < l < 1 else 0.0
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h * 60, s, l


_HUES = [(15, "красный"), (40, "оранжевый"), (65, "жёлтый"), (160, "зелёный"),
         (200, "бирюзовый"), (255, "синий"), (290, "фиолетовый"),
         (335, "розовый"), (361, "красный")]


def name_ru(hex_code):
    """Возвращает приблизительное название цвета на русском."""
    hue, s, l = _hsl(hex_code)
    if s < 0.12:
        if l > 0.85:
            return "белый"
        if l > 0.6:
            return "светло-серый"
        if l > 0.35:
            return "серый"
        if l > 0.15:
            return "тёмно-серый"
        return "чёрный"
    base = "красный"
    for lim, nm in _HUES:
        if hue < lim:
            base = nm
            break
    if base in ("оранжевый", "жёлтый") and l < 0.45:
        base = "коричневый"
    elif base == "оранжевый" and l > 0.7 and s < 0.55:
        base = "бежевый"
    prefix = ""
    if base not in ("бежевый", "коричневый"):
        if l > 0.78:
            prefix = "светло-"
        elif l < 0.3:
            prefix = "тёмно-"
        if s < 0.35:
            prefix = "приглушённый " + prefix
    return (prefix + base).strip()


# роль цвета в гардеробе по светлоте
def role_ru(hex_code):
    _, s, l = _hsl(hex_code)
    if s < 0.15:
        return "нейтраль (база)"
    if l < 0.35:
        return "тёмная база"
    if s > 0.6:
        return "яркий акцент"
    return "основной цвет"


if __name__ == "__main__":
    for h in ["#C2A878", "#1E2E5A", "#FF1E56", "#FFFFFF", "#8FA89C", "#7A2F4E"]:
        print(h, "->", name_ru(h), "|", role_ru(h))
