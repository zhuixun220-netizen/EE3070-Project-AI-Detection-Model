"""Resource paths must work regardless of the launch directory."""

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def read_paths(cwd, **overrides):
    environment = os.environ.copy()
    for key in ("YOLO_MODEL_PATH", "STORAGE_DIR"):
        environment.pop(key, None)
    environment.update(overrides)
    environment["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, "-c", (
            "import json; from esp32_ai_security import config; "
            "print(json.dumps([config.YOLO_MODEL_PATH, config.STORAGE_DIR]))"
        )],
        cwd=cwd, env=environment, check=True, capture_output=True, text=True,
    )
    return [Path(value) for value in json.loads(result.stdout)]


def test_defaults_find_resources_from_another_directory(tmp_path):
    model_path, storage_path = read_paths(tmp_path)
    assert model_path.is_absolute()
    assert model_path.is_file()
    assert storage_path == ROOT / "data" / "security_logs"


def test_relative_resource_overrides_are_project_relative(tmp_path):
    model_path, storage_path = read_paths(
        tmp_path, YOLO_MODEL_PATH="custom/model.pt", STORAGE_DIR="custom/events",
    )

    assert model_path == ROOT / "custom" / "model.pt"
    assert storage_path == ROOT / "custom" / "events"


def test_absolute_resource_overrides_are_preserved(tmp_path):
    model_path, storage_path = read_paths(
        tmp_path, YOLO_MODEL_PATH=str(tmp_path / "camera.pt"),
        STORAGE_DIR=str(tmp_path / "events"),
    )

    assert model_path == tmp_path / "camera.pt"
    assert storage_path == tmp_path / "events"
