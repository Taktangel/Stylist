# -*- coding: utf-8 -*-
"""
Стилист — Telegram-коннектор (MVP). Только стандартная библиотека (long polling).

Запуск:
    export TELEGRAM_TOKEN="123456:ABC..."   (Windows: set TELEGRAM_TOKEN=...)
    python telegram_bot.py

Бот ведёт опросник кнопками и в конце выдаёт стилевой профиль из движка.
Логика анализа полностью в engine.py — бот лишь тонкий канал.
"""

import json
import os
import time
import urllib.request
import urllib.error

import engine
import claude_client

TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
API = "https://api.telegram.org/bot%s/" % TOKEN
FILE_API = "https://api.telegram.org/file/bot%s/" % TOKEN

# Состояние диалога по chat_id: {"i": индекс_вопроса, "answers": {...}, "done": bool}
STATE = {}


# ---------------------------------------------------------------- Telegram API
def call(method, params):
    data = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(API + method, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode("utf-8", "ignore"))
    except Exception as e:  # noqa
        print("Ошибка запроса:", e)
    return None


def send(chat_id, text, keyboard=None):
    params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        params["reply_markup"] = {"inline_keyboard": keyboard}
    return call("sendMessage", params)


def kb_for(question):
    rows = []
    for opt in question["options"]:
        rows.append([{"text": opt["label"],
                      "callback_data": "%s|%s" % (question["id"], opt["id"])}])
    return rows


def download_file(file_id):
    """Скачивает файл из Telegram по file_id -> bytes или None."""
    info = call("getFile", {"file_id": file_id})
    if not info or not info.get("ok"):
        return None
    path = info["result"]["file_path"]
    try:
        with urllib.request.urlopen(FILE_API + path, timeout=60) as r:
            return r.read()
    except Exception as e:  # noqa
        print("Не удалось скачать фото:", e)
        return None


# ---------------------------------------------------------------- сценарий
def start(chat_id):
    STATE[chat_id] = {"i": 0, "answers": {}, "vision": None, "done": False}
    send(chat_id,
         "Привет! Я помогу определить ваш <b>типаж по Кибби</b>, <b>цветотип</b> и "
         "<b>стиль</b>, и дам персональные советы ✨\n\nОтветьте на несколько вопросов.")
    ask(chat_id)


def ask(chat_id):
    st = STATE[chat_id]
    if st["i"] >= len(engine.QUESTIONS):
        finish(chat_id)
        return
    q = engine.QUESTIONS[st["i"]]
    send(chat_id, "<b>%d/%d.</b> %s" % (st["i"] + 1, len(engine.QUESTIONS), q["text"]),
         kb_for(q))


def on_answer(chat_id, qid, oid):
    st = STATE.get(chat_id)
    if not st or st["done"]:
        start(chat_id)
        return
    st["answers"][qid] = oid
    st["i"] += 1
    ask(chat_id)


def finish(chat_id):
    st = STATE[chat_id]
    st["done"] = True
    p = engine.analyze_profile(st["answers"], st.get("vision"))
    send(chat_id, format_profile(p))
    tail = ("💬 Теперь можете спросить меня про аксессуары, капсулу или конкретную вещь — "
            "отвечу с учётом вашего профиля.\n")
    if claude_client.enabled():
        tail += "📷 Или пришлите фото при дневном свете — уточню цветотип по нему.\n"
    tail += "\nЧтобы пройти заново — /start"
    send(chat_id, tail)


def format_profile(p):
    k, s, a = p["kibbe"], p["season"], p["archetype"]
    rec = p["recommendations"]
    palette = "  ".join(s["palette"])
    lines = [
        "🎯 <b>Ваш профиль</b>",
        "",
        "<b>Типаж (Кибби):</b> %s" % k["name"],
        "<i>%s</i>" % k["line"],
        "Уверенность: %d%%" % int(k["confidence"] * 100),
        "",
        "<b>Цветотип:</b> %s (%d%%)" % (s["name"], int(s["confidence"] * 100)),
        "Палитра: %s" % palette,
        "Металл: %s" % ", ".join(s.get("metals", [])),
        "",
        "<b>Стиль:</b> %s" % " + ".join(a["names"]),
        "",
        "<b>✓ Силуэты:</b> %s" % "; ".join(rec["silhouettes"][:3]),
        "<b>✓ Ткани:</b> %s" % "; ".join(rec["fabrics"][:3]),
        "<b>✓ Аксессуары:</b> %s" % "; ".join(rec["accessories"][:3]),
        "<b>✕ Избегать:</b> %s" % "; ".join(rec["avoid"][:3]),
        "",
        "ℹ️ %s" % p["disclaimer"],
    ]
    return "\n".join(lines)


def on_photo(chat_id, msg):
    st = STATE.get(chat_id)
    if not st:
        start(chat_id)
        return
    if not claude_client.enabled():
        send(chat_id, "📷 Фото получено, но анализ фото выключен (нет ключа Claude). "
                      "Профиль строится по опроснику. Чтобы включить — задайте ANTHROPIC_API_KEY.")
        return
    send(chat_id, "🔍 Анализирую фото…")
    # берём самое крупное фото
    file_id = msg["photo"][-1]["file_id"]
    img = download_file(file_id)
    if not img:
        send(chat_id, "Не получилось загрузить фото, попробуйте ещё раз.")
        return
    vision = claude_client.analyze_photo(img)
    if not vision:
        send(chat_id, "Не удалось распознать параметры по фото. Профиль по опроснику остаётся в силе.")
        return
    st["vision"] = vision
    if st.get("done"):
        p = engine.analyze_profile(st["answers"], vision)
        send(chat_id, "✨ Уточнил по фото:\n\n" + format_profile(p))
    else:
        send(chat_id, "✅ Фото учтено. Допройдите опросник — и я соберу профиль с поправкой по фото.")


def on_text(chat_id, text):
    st = STATE.get(chat_id)
    if not st or not st.get("done"):
        start(chat_id)
        return
    p = engine.analyze_profile(st["answers"], st.get("vision"))

    # умный консультант через Claude (если есть ключ)
    smart = claude_client.consultant_reply(text, p)
    if smart:
        send(chat_id, smart)
        return

    # запасная логика без Claude
    k = p["kibbe"]
    low = text.lower()
    rec = p["recommendations"]
    if any(w in low for w in ("аксессуар", "украшен", "сумк", "серьг")):
        ans = "Аксессуары для вашего типажа: %s." % "; ".join(rec["accessories"][:3])
    elif any(w in low for w in ("цвет", "палитр", "оттен")):
        ans = "Ваша палитра: %s. Металл: %s." % (
            "  ".join(p["season"]["palette"]), ", ".join(p["season"].get("metals", [])))
    elif any(w in low for w in ("капсул", "гардероб", "база")):
        ans = "Базовая капсула: %s." % "; ".join(rec["capsule"])
    else:
        ans = "С учётом вашего типажа %s советую: %s." % (
            k["name"], (rec["silhouettes"] or ["—"])[0].lower())
    send(chat_id, ans)


# ---------------------------------------------------------------- цикл бота
def loop():
    if not TOKEN:
        raise SystemExit("Не задан TELEGRAM_TOKEN. Установите переменную окружения и перезапустите.")
    print("Стилист-бот запущен. Ожидаю сообщения…")
    offset = None
    while True:
        params = {"timeout": 30, "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            params["offset"] = offset
        res = call("getUpdates", params)
        if not res or not res.get("ok"):
            time.sleep(2)
            continue
        for upd in res["result"]:
            offset = upd["update_id"] + 1
            try:
                handle(upd)
            except Exception as e:  # noqa
                print("Ошибка обработки:", e)


def handle(upd):
    if "callback_query" in upd:
        cq = upd["callback_query"]
        call("answerCallbackQuery", {"callback_query_id": cq["id"]})
        chat_id = cq["message"]["chat"]["id"]
        qid, _, oid = cq["data"].partition("|")
        on_answer(chat_id, qid, oid)
        return
    if "message" in upd:
        msg = upd["message"]
        chat_id = msg["chat"]["id"]
        if "photo" in msg:
            on_photo(chat_id, msg)
            return
        text = msg.get("text", "")
        if text.startswith("/start"):
            start(chat_id)
        else:
            on_text(chat_id, text)


if __name__ == "__main__":
    loop()
