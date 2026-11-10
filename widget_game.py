"""Host the Hangar widget inside a Telegram bot's polling loop."""
import time
from pathlib import Path

from game import BUTTONS, Hangar, check_wad


class DoomWidget:
    def __init__(self, wad):
        self.wad = Path(wad)
        check_wad(self.wad)
        demo = Hangar(self.wad)
        try:
            template = Path(__file__).with_name("widget.html").read_text()
            self.html = template.replace("FRAME", demo.frame("look"))
        finally:
            demo.game.close()
        self.games = {}

    def send(self, api, chat_id):
        return api("sendWidget", chat_id=chat_id, html=self.html, width=300, allow_queries=True)

    def expire(self):
        now = time.monotonic()
        for key, (game, seen) in list(self.games.items()):
            if now - seen >= 600:
                game.game.close()
                del self.games[key]

    def answer(self, api, query):
        self.expire()
        key = (query["from"]["id"], query["chat_instance"], query.get("message_id"))
        action = query["data"]
        result = ""
        if action in (*BUTTONS, "restart"):
            if key not in self.games and len(self.games) < 6:
                self.games[key] = Hangar(self.wad), time.monotonic()
            if key in self.games:
                game, _ = self.games[key]
                self.games[key] = game, time.monotonic()
                result = game.frame(action)
            else:
                result = "busy"
        api("answerWidgetQuery", widget_query_id=query["id"], data=result)
