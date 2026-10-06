"""The standalone upload utility must find its default sample from any cwd."""

from pathlib import Path
import runpy
import subprocess
import sys
from types import SimpleNamespace

import requests


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "upload_sample.py"


def test_help_runs_from_another_directory(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "--device-id" in result.stdout


def test_missing_image_has_a_clear_error_without_sending_request(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "missing.jpg"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "missing.jpg" in result.stderr
    assert "Traceback" not in result.stderr


def test_default_upload_finds_sample_from_another_directory(monkeypatch, tmp_path):
    namespace = runpy.run_path(str(SCRIPT), run_name="upload_sample")
    uploaded = {}

    def post(url, *, data, files, timeout):
        uploaded["url"] = url
        uploaded["data"] = data
        uploaded["images"] = [(key, item[1].read()) for key, item in files]
        return SimpleNamespace(
            status_code=200, ok=True, json=lambda: {"status": "queued"}
        )

    monkeypatch.setattr(requests, "post", post)
    monkeypatch.chdir(tmp_path)
    assert namespace["main"](["--device-id", "sample-camera"]) == 0
    assert uploaded["url"] == "http://localhost:8080/api/v1/upload"
    assert uploaded["data"]["device_id"] == "sample-camera"
    expected = (ROOT / "tests" / "fixtures" / "images" / "test_thief.jpg").read_bytes()
    assert uploaded["images"] == [("files", expected)]
