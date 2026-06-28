import shutil
import subprocess
from dataclasses import dataclass
from gettext import gettext as _

from gi.repository import GLib


@dataclass
class ConversionJob:
    input_file: str
    output_file: str
    send_to_drive: bool
    drive_folder: str


def check_tools() -> list[str]:
    missing = []
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    return missing


def run_conversion(job: ConversionJob, on_done) -> None:
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", job.input_file,
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-c", "copy",
        job.output_file,
        "-y",
    ]

    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        error = result.stderr or _("ffmpeg failed with no output.")
        GLib.idle_add(on_done, False, error)
        return

    GLib.idle_add(on_done, True, None)
