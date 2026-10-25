import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

temporary_folder = tempfile.TemporaryDirectory()
os.environ["AUDIO_DIR"] = str(Path(temporary_folder.name) / "audio")
os.environ["DATABASE_FILE"] = str(Path(temporary_folder.name) / "test.sqlite3")

# Config is imported when the application modules load, so set the environment first.
from fastapi.testclient import TestClient
from transcription import api


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(api.app)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_rejects_unsupported_format(self):
        response = self.client.post(
            "/transcriptions",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        self.assertEqual(response.status_code, 415)

    def test_rejects_empty_upload(self):
        response = self.client.post(
            "/transcriptions",
            files={"file": ("empty.wav", b"", "audio/wav")},
        )
        self.assertEqual(response.status_code, 400)

    def test_accepts_wav_and_returns_job_id(self):
        # Mock scheduling so this test checks the API, not speech recognition.
        with patch.object(api.worker_pool, "submit") as submit:
            response = self.client.post(
                "/transcriptions",
                files={"file": ("sample.wav", b"sample-data", "audio/wav")},
            )

        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.json()["job_id"])
        submit.assert_called_once()

        # The mock doesn't execute the worker, so release the queue slot here.
        api.available_slots.release()

    def test_unknown_job_is_not_found(self):
        response = self.client.get("/transcriptions/not-found")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
