# -*- coding: utf-8 -*-
"""
Стилист — HTTP API (MVP). Только стандартная библиотека.

Запуск:   python api.py            (по умолчанию порт 8000)
          PORT=9000 python api.py

Эндпоинты:
    GET  /health      -> {"status":"ok"}
    GET  /questions   -> структура опросника
    POST /analyze     -> тело {"answers":{...}, "vision":{...}?} -> профиль
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import engine

PORT = int(os.environ.get("PORT", "8000"))


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, {})

    def do_GET(self):
        if self.path.rstrip("/") == "/health":
            self._send(200, {"status": "ok", "service": "stylist-mvp"})
        elif self.path.rstrip("/") == "/questions":
            self._send(200, {"questions": engine.QUESTIONS})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path.rstrip("/") != "/analyze":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
        except Exception as e:  # noqa
            self._send(400, {"error": "bad json: %s" % e})
            return
        answers = data.get("answers", {})
        vision = data.get("vision")
        try:
            profile = engine.analyze_profile(answers, vision)
            self._send(200, profile)
        except Exception as e:  # noqa
            self._send(500, {"error": "engine error: %s" % e})

    def log_message(self, *args):  # тише в консоли
        pass


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("Стилист API запущен на http://localhost:%d" % PORT)
    print("  GET  /health")
    print("  GET  /questions")
    print("  POST /analyze")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено.")
        server.shutdown()


if __name__ == "__main__":
    main()
