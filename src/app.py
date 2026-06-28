import gettext
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import gi

gi.require_version("Adw", "1")

from gi.repository import Adw, Gio

_LOCALE_DIR = Path(__file__).parent.parent / "locale"
gettext.bindtextdomain("noname", _LOCALE_DIR)
gettext.textdomain("noname")

from .window import Window


class Application(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id="io.github.noname.Noname",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app) -> None:
        win = Window(application=self)
        win.present()


def main() -> int:
    app = Application()
    return app.run(sys.argv)
