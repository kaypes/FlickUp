import shutil
import subprocess
from dataclasses import dataclass

from gi.repository import GLib


@dataclass
class ConversionJob:
    input_file: str
    output_file: str
    send_to_drive: bool
    rclone_path: str


def check_tools(send_to_drive: bool) -> list[str]:
    missing = []
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    if send_to_drive and not shutil.which("rclone"):
        missing.append("rclone")
    return missing


def run_conversion(job: ConversionJob, on_progress, on_done) -> None:
    ffmpeg_cmd = [
        "ffmpeg",
        "-i",
        job.input_file,
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-c",
        "copy",
        job.output_file,
        "-y",
    ]

    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        error = result.stderr or "ffmpeg falhou sem mensagem de erro."
        GLib.idle_add(on_done, False, error)
        return

    GLib.idle_add(on_progress)

    if job.send_to_drive:
        if not shutil.which("rclone"):
            GLib.idle_add(on_done, False, "rclone não está instalado.")
            return

        rclone_cmd = ["rclone", "copy", job.output_file, job.rclone_path]
        result = subprocess.run(rclone_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            error = result.stderr or "rclone falhou sem mensagem de erro."
            GLib.idle_add(on_done, False, error)
            return

    GLib.idle_add(on_done, True, None)
