"""Exercise the HTTP-to-disk pipeline without downloading or calling models."""

import io
import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture
def gateway(monkeypatch, tmp_path):
    import esp32_ai_security
    from esp32_ai_security import config
    from esp32_ai_security import services

    monkeypatch.setattr(config, "STORAGE_DIR", str(tmp_path / "events"))

    # Import fresh app modules for this fixture, then restore any prior imports.
    modules = [
        (esp32_ai_security, "main"),
        (services, "yolo_filter"),
        (services, "vllm_client"),
        (services, "decision_engine"),
    ]
    for parent, name in modules:
        monkeypatch.delitem(sys.modules, f"{parent.__name__}.{name}", raising=False)
        monkeypatch.delattr(parent, name, raising=False)

    # YOLO inference is the expensive boundary; keep real decoding and filtering.
    predictions = []

    class FakeYOLO:
        def __init__(self, model_path):
            pass

        def predict(self, image, device, verbose):
            return [SimpleNamespace(boxes=predictions)]

    ultralytics = ModuleType("ultralytics")
    ultralytics.YOLO = FakeYOLO
    monkeypatch.setitem(sys.modules, "ultralytics", ultralytics)

    try:
        from esp32_ai_security import main

        analysis = {
            "is_suspicious": False,
            "confidence": 0.9,
            "behavior_description": "正常经过",
            "reasoning": "未发现异常行为",
        }
        analyze = AsyncMock(return_value=analysis)
        monkeypatch.setattr(main.qwen_client, "analyze_security_images", analyze)

        buffer = io.BytesIO()
        Image.new("RGB", (8, 8), color="white").save(buffer, format="JPEG")
        with TestClient(main.app) as client:
            yield SimpleNamespace(
                client=client,
                predictions=predictions,
                analysis=analysis,
                analyze=analyze,
                image=buffer.getvalue(),
                records=tmp_path / "events",
            )
    finally:
        for parent, name in modules:
            sys.modules.pop(f"{parent.__name__}.{name}", None)
            vars(parent).pop(name, None)


def test_no_person_is_filtered_without_model_request_or_record(gateway):
    response = gateway.client.post(
        "/api/v1/upload",
        data={"device_id": "test-camera"},
        files=[("files", ("frame.jpg", gateway.image, "image/jpeg"))],
    )

    assert response.status_code == 200
    assert response.json()["status"] == "filtered"
    gateway.analyze.assert_not_awaited()
    assert list(gateway.records.iterdir()) == []


@pytest.mark.parametrize("suspicious, prefix", [(False, "NORMAL_"), (True, "ALERT_")])
def test_person_analysis_persists_metadata_and_all_frames(gateway, suspicious, prefix):
    gateway.predictions.append(SimpleNamespace(cls=[0], conf=[0.9]))
    gateway.analysis["is_suspicious"] = suspicious
    response = gateway.client.post(
        "/api/v1/upload",
        data={"device_id": "test-camera", "timestamp": "2026-10-06T00:00:00Z"},
        files=[
            ("files", ("first.jpg", gateway.image, "image/jpeg")),
            ("files", ("second.jpg", gateway.image, "image/jpeg")),
        ],
    )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    records = list(gateway.records.iterdir())
    assert len(records) == 1
    assert records[0].name.startswith(prefix)
    result = json.loads((records[0] / "result.json").read_text(encoding="utf-8"))
    assert result["metadata"] == {
        "device_id": "test-camera", "timestamp": "2026-10-06T00:00:00Z"
    }
    assert result["analysis"] == gateway.analysis
    assert (records[0] / "frame_1.jpg").read_bytes() == gateway.image
    assert (records[0] / "frame_2.jpg").read_bytes() == gateway.image
