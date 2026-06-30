# Образ для запуска Telegram-бота «Стилист».
# Зависимостей нет — нужен только Python.
FROM python:3.11-slim

WORKDIR /app
COPY mvp/ ./mvp/

WORKDIR /app/mvp

# Токены передаются как переменные окружения / секреты хостинга:
#   TELEGRAM_TOKEN      (обязательно)
#   ANTHROPIC_API_KEY   (опционально — фото и умный чат)
CMD ["python", "telegram_bot.py"]
