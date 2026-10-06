import os

# 1. YOLO 网关配置
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")  # 可替换为微调好的 IR 权重路径
PERSON_CLASS_ID = 0  # COCO 数据集中 'person' 类别 ID
PERSON_CONF_THRESHOLD = 0.35  # 判断门限：置信度 >= 0.35

# 2. vLLM Qwen2.5-VL 服务配置
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
VLLM_MODEL_NAME = os.getenv("VLLM_MODEL_NAME", "./Qwen2.5-VL-7B-Instruct")

# 3. 日志与存储配置
STORAGE_DIR = "security_logs"