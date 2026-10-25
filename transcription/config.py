import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = Path(os.getenv("AUDIO_DIR", PROJECT_DIR / "audio_files"))
DATABASE_FILE = Path(os.getenv("DATABASE_FILE", str(PROJECT_DIR / "transcriptions.sqlite3")))

MAX_UPLOAD_MB = 100
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_QUEUED_JOBS = 8
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
