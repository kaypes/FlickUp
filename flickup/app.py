import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio

from .window import FlickUpWindow


class FlickUpApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id="io.github.flickup.FlickUp",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app) -> None:
        win = FlickUpWindow(application=self)
        win.present()


def main() -> int:
    app = FlickUpApplication()
    return app.run(sys.argv)
