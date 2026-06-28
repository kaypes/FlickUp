import tempfile
import threading
from gettext import gettext as _
from pathlib import Path

import ffmpeg
from gi.repository import GLib

from . import drive
from .converter import ConversionJob


class Presenter:
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
        threading.Thread(target=self._run, args=(job,), daemon=True).start()

    # ── Private ───────────────────────────────────────────────────────────────

    def _validate(self) -> str | None:
        w = self._window
        if not w.input_file:
            return _("Please select an input file.")
        if not w.output_name:
            return _("Please enter an output filename.")
        return None

    def _build_job(self) -> ConversionJob:
        w = self._window
        if w.send_to_drive:
            output_dir = tempfile.mkdtemp(prefix="noname_")
        else:
            output_dir = w.local_folder
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        output_file = str(Path(output_dir) / (w.output_name + w.selected_format))
        return ConversionJob(
            input_file=w.input_file,
            output_file=output_file,
            send_to_drive=w.send_to_drive,
            drive_folder=w.drive_folder if w.send_to_drive else "",
        )

    def _run(self, job: ConversionJob) -> None:
        try:
            (
                ffmpeg.input(job.input_file)
                .output(
                    job.output_file,
                    map_metadata=-1,
                    map_chapters=-1,
                    c="copy",
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as e:
            error = (
                e.stderr.decode() if e.stderr else _("ffmpeg failed with no output.")
            )
            GLib.idle_add(self._on_done, False, error)
            return

        if job.send_to_drive:
            GLib.idle_add(self._window.set_processing_label, _("Uploading…"))
            try:
                drive.upload_sync(job.output_file, job.drive_folder)
            except Exception as e:
                GLib.idle_add(self._on_done, False, str(e))
                return

        GLib.idle_add(self._on_done, True, None)

    def _on_done(self, success: bool, error: str | None) -> bool:
        self._processing = False
        self._window.end_processing()
        if success:
            self._window.show_toast(_("Conversion complete!"))
        else:
            msg = (error or _("Unknown error"))[:200]
            self._window.show_toast(_("Error: {msg}").format(msg=msg), high=True)
        return False
