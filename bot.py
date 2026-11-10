import os
import time
from pathlib import Path

import requests
from widget_game import DoomWidget

ROOT = Path(__file__).resolve().parent
CONFIG = Path.home() / ".config/doom-message"


def run():
    wad = Path(os.environ.get("DOOM_WAD", CONFIG / "doom1.wad")).resolve()
    token = os.environ.get("BOT_TOKEN") or (CONFIG / "token").read_text().strip()
    session = requests.Session()

    def api(method, **params):
        response = session.post(f"https://api.telegram.org/bot{token}/{method}",
                                json=params, timeout=45)
        result = response.json()
        if not result.get("ok"):
            raise RuntimeError(result.get("description", "Telegram API error"))
        return result["result"]

    widget = DoomWidget(wad)
    offset = 0
    print("Ready", flush=True)
    while True:
        widget.expire()
        try:
            updates = api("getUpdates", offset=offset, timeout=20,
                          allowed_updates=["message", "widget_query"])
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            print("Polling failed:", type(exc).__name__, flush=True)
            time.sleep(3)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            try:
                msg = update.get("message", {})
                if msg.get("chat", {}).get("type") == "private" and msg.get("text", "").split(" ")[0] == "/start":
                    sent = widget.send(api, msg["chat"]["id"])
                    print("Widget sent", sent["message_id"], flush=True)
                query = update.get("widget_query")
                if query:
                    widget.answer(api, query)
            except RuntimeError as exc:
                print(str(exc)[:180], flush=True)
            except Exception as exc:
                print("Update failed:", type(exc).__name__, flush=True)


if __name__ == "__main__":
    run()
