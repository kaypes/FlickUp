import tempfile
import threading
from gettext import gettext as _
from pathlib import Path

from .converter import ConversionJob, run_conversion


class FlickUpPresenter:
    def __init__(self, window) -> None:
        self._window = window
        self._processing = False

    # ── Public ────────────────────────────────────────────────────────────────

    def on_convert_clicked(self) -> None:
        if self._processing:
            return

        error = self._validate()
        if error:
            self._window.show_toast(error)
            return

        job = self._build_job()
        self._processing = True
        self._window.begin_processing()
        threading.Thread(
            target=run_conversion,
            args=(job, self._on_done),
            daemon=True,
        ).start()

    # ── Private ───────────────────────────────────────────────────────────────

    def _validate(self) -> str | None:
        w = self._window
        if not w.input_file:
            return _("Please select an input file.")
        if not w.output_name:
            return _("Please enter an output filename.")
        if w.send_to_drive:
            if not w.rclone_path:
                return _("Please enter a Drive destination path.")
            if ":" not in w.rclone_path:
                return _("Drive destination path is invalid.")
        return None

    def _build_job(self) -> ConversionJob:
        w = self._window
        if w.send_to_drive:
            output_dir = tempfile.mkdtemp(prefix="flickup_")
        else:
            output_dir = w.local_folder
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        output_file = str(Path(output_dir) / (w.output_name + w.selected_format))
        return ConversionJob(
            input_file=w.input_file,
            output_file=output_file,
            send_to_drive=w.send_to_drive,
            rclone_path=w.rclone_path if w.send_to_drive else "",
        )

    def _on_done(self, success: bool, error: str | None) -> bool:
        self._processing = False
        self._window.end_processing()
        if success:
            self._window.show_toast(_("Conversion complete!"))
        else:
            msg = (error or _("Unknown error"))[:200]
            self._window.show_toast(_("Error: {msg}").format(msg=msg), high=True)
        return False
