import shutil
from dataclasses import dataclass
from gettext import gettext as _


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
