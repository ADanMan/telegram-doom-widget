"""Host the Hangar widget inside a Telegram bot's polling loop."""
import time
from pathlib import Path
from string import Template

from game import BUTTONS, Hangar, check_wad


LABELS = {
    "forward_label": ("Forward", "Вперёд"),
    "back_label": ("Back", "Назад"),
    "use_label": ("Use", "Дверь"),
    "fire_label": ("Fire", "Огонь"),
    "end_status": ("Game over · tap Restart", "Игра окончена · нажми «Заново»"),
    "restart_label": ("Restart", "Заново"),
    "idle_status": ("Tap a button to take a turn", "Нажми кнопку для хода"),
    "move_status": ("Moving…", "Ход…"),
    "busy_status": ("All sessions are busy. Try again later.", "Все слоты заняты. Попробуй позже."),
    "empty_status": ("No frame received", "Ход не получен"),
    "next_status": ("E1M1 · your turn", "E1M1 · следующий ход"),
    "error_status": ("No response · try again", "Нет ответа · попробуй ещё раз"),
}


class DoomWidget:
    def __init__(self, wad):
        self.wad = Path(wad)
        check_wad(self.wad)
        demo = Hangar(self.wad)
        try:
            template = Path(__file__).with_name("widget.html").read_text()
            template = Template(template.replace("FRAME", demo.frame("look")))
            self.html = {lang: template.substitute({key: pair[i] for key, pair in LABELS.items()})
                         for i, lang in enumerate(("en", "ru"))}
        finally:
            demo.game.close()
        self.games = {}

    def send(self, api, chat_id, reply_markup=None, language_code=None):
        options = {"reply_markup": reply_markup} if reply_markup else {}
        return api("sendWidget", chat_id=chat_id, html=self.html["ru" if (language_code or "").lower().split("-")[0] == "ru" else "en"], width=300, allow_queries=True, **options)

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
