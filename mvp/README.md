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
2. Запустите:

```bash
cd mvp
export TELEGRAM_TOKEN="123456:ABC..."   # Windows: set TELEGRAM_TOKEN=123456:ABC...
python telegram_bot.py
```

3. Напишите боту `/start` — он проведёт по опроснику и выдаст профиль.

Бот «тонкий»: вся логика в `engine.py`. Чтобы подключить другой канал (веб-виджет,
WhatsApp, Telegram Mini App) — обращайтесь к тому же API или импортируйте `engine` напрямую.

---

## Как подключить анализ фото (следующий шаг)

Сейчас точка приёма фото в боте — заглушка. Чтобы включить:

1. Отправляйте фото во внешнюю **vision-модель** и извлекайте параметры:
   `undertone` (warm/cool/neutral), `value` (light/medium/deep),
   `chroma` (bright/medium/soft), `contrast` (high/medium/low),
   и опционально `lean` (число: + мягче/инь, − острее/ян).
2. Передавайте их в движок как `vision`:

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
