import base64
import hashlib
import io
from pathlib import Path

from PIL import Image
import vizdoom as doom

BUTTONS = {
    "forward": doom.Button.MOVE_FORWARD,
    "back": doom.Button.MOVE_BACKWARD,
    "left": doom.Button.TURN_LEFT,
    "right": doom.Button.TURN_RIGHT,
    "fire": doom.Button.ATTACK,
    "use": doom.Button.USE,
}


def check_wad(path):
    digest = hashlib.md5(Path(path).read_bytes()).hexdigest()
    if digest != "f0cefca49926d00903cf57551d901abe":
        raise ValueError("Expected original Doom shareware 1.9 DOOM1.WAD")


class Hangar:
    def __init__(self, wad):
        self.game = doom.DoomGame()
        self.game.set_doom_game_path(str(wad))
        self.game.set_doom_map("E1M1")
        self.game.set_window_visible(False)
        self.game.set_sound_enabled(False)
        self.game.set_screen_format(doom.ScreenFormat.RGB24)
        self.game.set_screen_resolution(doom.ScreenResolution.RES_320X200)
        self.game.set_render_hud(True)
        self.game.set_available_buttons(list(BUTTONS.values()))
        self.game.init()
        self.game.new_episode()

    def frame(self, action):
        if action == "restart":
            self.game.new_episode()
        elif action in BUTTONS and not self.game.is_episode_finished():
            self.game.make_action([int(key == action) for key in BUTTONS], 5)
        if self.game.is_episode_finished():
            return "end"
        image = Image.fromarray(self.game.get_state().screen_buffer)
        for width in (120, 96, 80, 64, 48, 32):
            buf = io.BytesIO()
            image.resize((width, width*5//8), Image.Resampling.LANCZOS).save(
                buf, "WEBP", quality=25, method=3
            )
            data = base64.b64encode(buf.getvalue()).decode("ascii")
            if len(data) <= 1024:
                return data
        raise ValueError("Frame exceeds widget answer limit")
