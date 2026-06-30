# Стилист — MVP

Рабочий движок персонального стилиста: по ответам опросника (и опционально по параметрам фото)
выдаёт **типаж Кибби**, **цветотип (12 сезонов)**, **архетип** и персональные рекомендации.
Подключается к любому чат-боту через HTTP API; в комплекте готовый Telegram-коннектор.

Требуется только **Python 3.9+**. Внешних зависимостей нет.

---

## Структура

```
mvp/
├── kb/                  база знаний (данные отделены от кода)
│   ├── kibbe.json       13 типов Кибби
│   ├── seasons.json     12 цветосезонов с палитрами
│   └── archetypes.json  7 архетипов стиля
├── engine.py            движок анализа + самопроверка
├── api.py               HTTP API (стандартная библиотека)
├── claude_client.py     коннектор Claude API (vision-фото + чат)
├── telegram_bot.py      коннектор Telegram (long polling)
└── README.md
```

---

## 1. Проверить, что всё работает (30 секунд)

```bash
cd mvp
python engine.py --selftest
```

Должно вывести разбор 6 эталонных профилей и строку `ИТОГ: ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ`.
Это подтверждает, что база знаний валидна и движок корректно типирует.

Демо одного профиля в JSON:

```bash
python engine.py
```

---

## 2. Запустить API

```bash
cd mvp
python api.py                # порт 8000 (или PORT=9000 python api.py)
```

Проверка:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/questions

curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"answers":{"q_height":"tall","q_bone":"sharp","q_face":"sharp","q_flesh":"lean","q_fit":"straight","q_proportion":"elongated","q_undertone":"cool","q_value":"deep","q_chroma":"bright","q_contrast":"high","q_arch1":"dramatic","q_arch2":"edgy"}}'
```

Ответ — полный профиль (kibbe / season / archetype / recommendations / summary).

---

## 3. Подключить к Telegram-боту

1. Создайте бота у **@BotFather** и получите токен.
2. (Опционально, для фото и умного чата) получите ключ **Claude API** на console.anthropic.com.
3. Задайте переменные окружения и запустите:

```bash
cd mvp
# обязательно:
export TELEGRAM_TOKEN="123456:ABC..."        # Windows: set TELEGRAM_TOKEN=123456:ABC...
# опционально — включает анализ фото и умный чат:
export ANTHROPIC_API_KEY="sk-ant-..."        # Windows: set ANTHROPIC_API_KEY=sk-ant-...
python telegram_bot.py
```

4. Напишите боту `/start` — он проведёт по опроснику и выдаст профиль.
   Если задан `ANTHROPIC_API_KEY` — можно прислать фото (уточнит цветотип) и задавать
   свободные вопросы (отвечает Claude с учётом профиля).

Бот «тонкий»: вся логика в `engine.py`. Чтобы подключить другой канал (веб-виджет,
WhatsApp, Telegram Mini App) — обращайтесь к тому же API или импортируйте `engine` напрямую.

---

## Где подключается Claude API

Ключ задаётся **один раз** через переменную окружения `ANTHROPIC_API_KEY`, а используется
в модуле **`claude_client.py`** для двух задач:

| Функция | Где вызывается | Что делает |
|---|---|---|
| `analyze_photo(image_bytes)` | бот при получении фото | Claude vision определяет подтон/светлоту/насыщенность/контраст/lean → передаёт в движок как `vision` |
| `consultant_reply(question, profile)` | бот при свободном вопросе | Claude отвечает как стилист, опираясь только на профиль пользователя |

Модель меняется переменной `CLAUDE_MODEL` (по умолчанию `claude-sonnet-4-6`).

**Важно:** Claude — опционален. Без ключа движок, API и опросник в боте работают как есть;
просто отключаются фото-анализ и умный чат (срабатывает запасная логика на правилах).

Быстрая проверка ключа отдельно:

```bash
cd mvp
export ANTHROPIC_API_KEY="sk-ant-..."
python claude_client.py        # выведет тестовый ответ стилиста
```

---

## Анализ фото — уже реализован

Приём фото в боте подключён к Claude vision (`claude_client.analyze_photo`). При наличии
`ANTHROPIC_API_KEY` бот скачивает фото, извлекает параметры и передаёт их в движок как `vision`:
`undertone` (warm/cool/neutral), `value` (light/medium/deep), `chroma` (bright/medium/soft),
`contrast` (high/medium/low), `lean` (−4..+4: + мягче/инь, − острее/ян).

Эти же параметры можно передать в движок напрямую (например, от другой vision-модели):

```python
engine.analyze_profile(answers, vision={"undertone": "cool", "value": "deep",
                                         "chroma": "bright", "contrast": "high"})
```

Параметры `vision` имеют приоритет над ответами опросника по соответствующим осям.

---

## Контракт API

| Метод | Путь | Тело / ответ |
|---|---|---|
| GET | `/health` | `{"status":"ok"}` |
| GET | `/questions` | структура опросника (для любого клиента) |
| POST | `/analyze` | вход `{"answers":{...},"vision":{...}?}` → профиль |

Профиль (`/analyze`):

```json
{
  "kibbe":   {"id","name","family","confidence","line","recommendations","avoid"},
  "season":  {"id","name","undertone","value","chroma","confidence","palette","neutrals","metals","avoid"},
  "archetype":{"primary","secondary","names","description","signature"},
  "recommendations": {"palette","neutrals","silhouettes","fabrics","necklines","accessories","metals","capsule","avoid"},
  "summary": "...",
  "disclaimer": "..."
}
```

---

## Заметки

- База знаний (`kb/*.json`) правится без изменения кода и валидируется при старте движка.
- Результат Кибби и архетип подаются как **гипотеза с уверенностью** — в продукте дайте
  пользователю кнопку «скорректировать».
- В MVP сервер не хранит фото. При подключении реального фото-анализа добавьте согласие,
  шифрование и автоудаление (см. `../План_продукта_Стилист.md`).
- Самопроверка прогонялась построчно по логике; запустите `python engine.py --selftest`
  у себя, чтобы убедиться вживую.
