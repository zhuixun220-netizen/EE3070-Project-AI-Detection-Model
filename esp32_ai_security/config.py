import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resource_path(variable: str, default: str) -> str:
    """Resolve local resources independently of the current directory."""
    path = Path(os.getenv(variable, default)).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path.resolve())

# 1. YOLO 网关配置
YOLO_MODEL_PATH = _resource_path("YOLO_MODEL_PATH", "models/yolov8n.pt")
PERSON_CLASS_ID = 0  # COCO 数据集中 'person' 类别 ID
PERSON_CONF_THRESHOLD = 0.35  # 判断门限：置信度 >= 0.35

# 2. vLLM Qwen2.5-VL 服务配置
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
VLLM_MODEL_NAME = os.getenv("VLLM_MODEL_NAME", "./Qwen2.5-VL-7B-Instruct")

# 3. 日志与存储配置
STORAGE_DIR = _resource_path("STORAGE_DIR", "data/security_logs")
