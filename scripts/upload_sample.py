"""Upload sample frames: python scripts/upload_sample.py --help."""

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import sys

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE = PROJECT_ROOT / "tests" / "fixtures" / "images" / "test_thief.jpg"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="上传 JPEG 图片到 ESP32 安防网关")
    parser.add_argument("images", nargs="*", type=Path, help="图片路径，可指定多张")
    parser.add_argument("--url", default="http://localhost:8080/api/v1/upload")
    parser.add_argument("--device-id", default="esp32_cam_entrance_01")
    parser.add_argument("--timestamp", help="设备时间戳，默认使用当前 UTC 时间")
    args = parser.parse_args(argv)
    images = args.images or [DEFAULT_IMAGE]

    for path in images:
        if not path.is_file():
            parser.error(f"找不到图片文件: {path}")

    data = {
        "device_id": args.device_id,
        "timestamp": args.timestamp or datetime.now(timezone.utc).isoformat(),
    }
    print(f"正在上传 {len(images)} 张图片至 {args.url}...")
    try:
        with ExitStack() as stack:
            files = [
                ("files", (path.name, stack.enter_context(path.open("rb")), "image/jpeg"))
                for path in images
            ]
            response = requests.post(args.url, data=data, files=files, timeout=30)
    except (OSError, requests.RequestException) as exc:
        print(f"上传失败: {exc}", file=sys.stderr)
        return 1

    print(f"HTTP 状态码: {response.status_code}")
    try:
        print("返回内容:", response.json())
    except ValueError:
        print("返回内容:", response.text)
    return 0 if response.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
