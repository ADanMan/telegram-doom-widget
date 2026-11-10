import os
import time
import zlib
from pathlib import Path

import requests
from game import BUTTONS, Hangar, check_wad

ROOT = Path(__file__).resolve().parent
CONFIG = Path.home() / ".config/doom-message"


def run():
    wad = Path(os.environ.get("DOOM_WAD", CONFIG / "doom1.wad")).resolve()
    check_wad(wad)
    token = os.environ.get("BOT_TOKEN") or (CONFIG / "token").read_text().strip()
    session = requests.Session()

    def api(method, **params):
        response = session.post(f"https://api.telegram.org/bot{token}/{method}",
                                json=params, timeout=45)
        result = response.json()
        if not result.get("ok"):
            raise RuntimeError(result.get("description", "Telegram API error"))
        return result["result"]

    demo = Hangar(wad)
    try:
        html = (ROOT / "widget.html").read_text().replace("FRAME", demo.frame("look"))
    finally:
        demo.game.close()
    assert len(html.encode()) <= 32768 and len(zlib.compress(html.encode(), 9)) <= 4096
    games = {}
    offset = 0
    print("Ready", flush=True)
    while True:
        now = time.monotonic()
        for key, (game, seen) in list(games.items()):
            if now-seen > 600:
                game.game.close()
                del games[key]
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
                    sent = api("sendWidget", chat_id=msg["chat"]["id"], html=html,
                               width=300, allow_queries=True)
                    print("Widget sent", sent["message_id"], flush=True)
                query = update.get("widget_query")
                if not query:
                    continue
                key = (query["from"]["id"], query["chat_instance"], query.get("message_id"))
                action = query["data"]
                result = ""
                if action in (*BUTTONS, "restart"):
                    if key not in games and len(games) < 6:
                        games[key] = (Hangar(wad), now)
                    if key in games:
                        game, _ = games[key]
                        games[key] = (game, time.monotonic())
                        result = game.frame(action)
                    else:
                        result = "busy"
                api("answerWidgetQuery", widget_query_id=query["id"], data=result)
            except RuntimeError as exc:
                print(str(exc)[:180], flush=True)
            except Exception as exc:
                print("Update failed:", type(exc).__name__, flush=True)


if __name__ == "__main__":
    run()
