#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CONFIG_DEFAULT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "vk.conf"
)

NEEDED = ["remixsid", "remixsid6k", "p", "remixnttpid", "httoken"]
USEFUL = ["remixlang", "remixdt", "remixstid", "remixstlid", "remixua"]

COOKIE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")
MAX_COOKIE_VALUE_LEN = 4096
MAX_COOKIE_COUNT = 200


def validate_cookie(c):
    name = c.get("name") or ""
    if not COOKIE_NAME_RE.match(name):
        raise ValueError(f"недопустимое имя куки: {name!r}")
    value = c.get("value") or ""
    if len(value) > MAX_COOKIE_VALUE_LEN:
        raise ValueError(f"значение куки {name} слишком длинное ({len(value)} > {MAX_COOKIE_VALUE_LEN})")
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError(f"значение куки {name} содержит запрещённые символы")


def update_config(path, cookies):
    if len(cookies) > MAX_COOKIE_COUNT:
        raise ValueError(f"слишком много кук ({len(cookies)} > {MAX_COOKIE_COUNT})")

    for c in cookies:
        validate_cookie(c)

    picked = []
    for c in cookies:
        host = (c.get("host") or "").lower()
        if not (host.endswith("vk.ru") or host == "vk.ru"):
            continue
        name = c.get("name") or ""
        if name in NEEDED or name in USEFUL:
            picked.append(c)

    picked.sort(
        key=lambda c: (NEEDED + USEFUL).index(c["name"])
        if c["name"] in NEEDED or c["name"] in USEFUL
        else 99
    )

    cookie_str = "; ".join(
        f"{c['name']}={c['value']}" for c in picked if c.get("value")
    )
    if not cookie_str:
        raise ValueError("нет подходящих кук vk.ru (нужны remixsid/p/remixnttpid)")

    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    replaced = False
    out = []
    for line in lines:
        if line.startswith("VK_COOKIE="):
            out.append(f"VK_COOKIE={cookie_str}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"VK_COOKIE={cookie_str}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return len(picked)


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_POST(self):
        if self.path != "/update":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 1024 * 256:
                self.send_error(413)
                return
            raw = self.rfile.read(length) if length else b""
            cookies = json.loads(raw.decode("utf-8"))
            if not isinstance(cookies, list):
                raise ValueError("ожидается JSON-массив")
            n = update_config(self.server.config_path, cookies)
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "cookies": n}).encode())
            print(f"VK_COOKIE обновлён: {n} кук")
        except Exception as e:
            self.send_response(400)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())
            print(f"Ошибка приёма кук: {e}", file=sys.stderr)

    def log_message(self, fmt, *args):
        pass


def main():
    ap = argparse.ArgumentParser(description="Приёмник VK-кук для Raisa")
    ap.add_argument("--config", default=CONFIG_DEFAULT, help="путь к vk.conf")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8002)
    args = ap.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.config_path = args.config
    print(f"Приёмник кук на {args.host}:{args.port}, конфиг: {args.config}")
    server.serve_forever()


if __name__ == "__main__":
    main()
