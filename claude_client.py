# -*- coding: utf-8 -*-
"""
Стилист — коннектор к Claude API (vision-анализ фото + чат-консультант).
Только стандартная библиотека (urllib). Python 3.9+.

КУДА ПОДКЛЮЧАЕТСЯ КЛЮЧ:
    переменная окружения ANTHROPIC_API_KEY = "sk-ant-..."
    (опционально CLAUDE_MODEL, по умолчанию claude-sonnet-4-6)

Если ключ не задан — функции возвращают None / запасной текст,
и движок продолжает работать на одном опроснике (без фото и без умного чата).
"""

import base64
import json
import os
import urllib.request
import urllib.error

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6").strip()
URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def enabled():
    """True, если ключ задан и Claude можно вызывать."""
    return bool(API_KEY)


def _call(messages, system=None, max_tokens=700):
    if not API_KEY:
        return None
    body = {"model": MODEL, "max_tokens": max_tokens, "messages": messages}
    if system:
        body["system"] = system
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(URL, data=data, headers={
        "x-api-key": API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("Claude HTTP", e.code, e.read().decode("utf-8", "ignore")[:300])
        return None
    except Exception as e:  # noqa
        print("Claude ошибка:", e)
        return None
    parts = [b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text"]
    return "".join(parts).strip()


def _extract_json(text):
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    a, b = t.find("{"), t.rfind("}")
    if a != -1 and b != -1:
        t = t[a:b + 1]
    try:
        return json.loads(t)
    except Exception:  # noqa
        return None


# ---------------------------------------------------------------- VISION: фото
PHOTO_SYSTEM = (
    "Ты — эксперт по сезонному цветотипу и типажу Кибби. "
    "Анализируешь фото человека и оцениваешь объективные признаки. "
    "Отвечай СТРОГО одним JSON-объектом без пояснений."
)

PHOTO_PROMPT = (
    "Оцени по фото и верни JSON с ключами:\n"
    '  "undertone": "warm" | "cool" | "neutral"  (подтон кожи)\n'
    '  "value": "light" | "medium" | "deep"      (общая светлота внешности)\n'
    '  "chroma": "bright" | "medium" | "soft"     (яркость/приглушённость)\n'
    '  "contrast": "high" | "medium" | "low"      (контраст волос/кожи/глаз)\n'
    '  "lean": число от -4 до 4 (-4 = острый ян, +4 = мягкий инь)\n'
    '  "notes": краткий комментарий (1 предложение)\n'
    "Только JSON, без markdown."
)


def analyze_photo(image_bytes, media_type="image/jpeg"):
    """Возвращает dict с параметрами для engine.analyze_profile(vision=...) или None."""
    if not API_KEY:
        return None
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    messages = [{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64",
                                     "media_type": media_type, "data": b64}},
        {"type": "text", "text": PHOTO_PROMPT},
    ]}]
    txt = _call(messages, system=PHOTO_SYSTEM, max_tokens=400)
    data = _extract_json(txt)
    if not data:
        return None
    # нормализация
    out = {}
    for k in ("undertone", "value", "chroma", "contrast"):
        if data.get(k):
            out[k] = str(data[k]).lower()
    if isinstance(data.get("lean"), (int, float)):
        out["lean"] = max(-4, min(4, data["lean"]))
    if data.get("notes"):
        out["notes"] = data["notes"]
    return out or None


# ---------------------------------------------------------------- ЧАТ-консультант
def consultant_reply(question, profile):
    """Умный ответ стилиста на свободный вопрос. None -> используйте запасную логику."""
    if not API_KEY:
        return None
    ctx = {
        "kibbe": profile["kibbe"]["name"],
        "kibbe_line": profile["kibbe"]["line"],
        "season": profile["season"]["name"],
        "palette": profile["season"]["palette"],
        "metals": profile["season"].get("metals", []),
        "archetype": profile["archetype"]["names"],
        "silhouettes": profile["recommendations"]["silhouettes"],
        "fabrics": profile["recommendations"]["fabrics"],
        "accessories": profile["recommendations"]["accessories"],
        "avoid": profile["recommendations"]["avoid"],
    }
    system = (
        "Ты — тёплый, профессиональный личный стилист. Отвечай кратко (2–4 предложения), "
        "по-русски, поддерживающе и без оценочных суждений о теле. Опирайся ТОЛЬКО на профиль "
        "пользователя ниже. Если просят конкретные вещи — давай примеры в рамках его палитры и типажа.\n\n"
        "ПРОФИЛЬ: " + json.dumps(ctx, ensure_ascii=False)
    )
    messages = [{"role": "user", "content": question}]
    return _call(messages, system=system, max_tokens=500)


# ---------------------------------------------------------------- быстрый тест
if __name__ == "__main__":
    if not enabled():
        print("ANTHROPIC_API_KEY не задан — Claude отключён. "
              "Установите ключ, чтобы протестировать vision и чат.")
    else:
        print("Ключ найден. Модель:", MODEL)
        demo_profile = {
            "kibbe": {"name": "Dramatic", "line": "Чистый ян."},
            "season": {"name": "Bright Winter", "palette": ["#FF1E56", "#1E90FF"], "metals": ["серебро"]},
            "archetype": {"names": ["Драматический"]},
            "recommendations": {"silhouettes": ["Длинные вертикали"], "fabrics": ["Плотные ткани"],
                                "accessories": ["Крупная геометрия"], "avoid": ["Рюши"]},
        }
        print("Тест чата:")
        print(consultant_reply("Что надеть на деловую встречу?", demo_profile))
