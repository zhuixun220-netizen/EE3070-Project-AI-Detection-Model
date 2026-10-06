import logging
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
import uvicorn

from esp32_ai_security.services.yolo_filter import YOLOFilter
from esp32_ai_security.services.vllm_client import QwenVLClient
from esp32_ai_security.services.decision_engine import DecisionEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("Gateway")

app = FastAPI(title="ESP32 AI Security Gateway", version="1.0.0")

# 初始化核心对象
yolo_filter = YOLOFilter()
qwen_client = QwenVLClient()
decision_engine = DecisionEngine()

async def async_stage2_pipeline(image_bytes_list: List[bytes], metadata: dict):
    """第二级与第三级异步后台处理管道"""
    try:
        # 第二级：大模型多模态语义推理
        analysis_result = await qwen_client.analyze_security_images(image_bytes_list, metadata)
        # 第三级：规则引擎后处理与分流
        await decision_engine.process_decision(analysis_result, metadata, image_bytes_list)
    except Exception as e:
        logger.error(f"Stage 2 后台处理失败: {e}", exc_info=True)

@app.post("/api/v1/upload")
async def upload_security_frames(
    background_tasks: BackgroundTasks,
    device_id: str = Form(...),
    timestamp: str = Form(None),
    files: List[UploadFile] = File(...)
):
    """
    ESP32-S3 上传接口：接收多张 JPEG 图像 + 设备元数据
    """
    if not files:
        raise HTTPException(status_code=400, detail="未收到图片文件")

    image_bytes_list = []
    for file in files:
        bytes_content = await file.read()
        image_bytes_list.append(bytes_content)

    metadata = {"device_id": device_id, "timestamp": timestamp}

    # 【第一级：轻量级 YOLOv8 过滤网关】
    has_person = yolo_filter.detect_person(image_bytes_list)

    if not has_person:
        logger.info(f"🛑 [分支 A - 流程终止] 设备 [{device_id}] YOLO 未检测到人体 (Count=0)，已安全拦截。")
        return {
            "status": "filtered",
            "message": "No person detected by YOLO filter gateway. Pipeline terminated."
        }

    logger.info(f"⚡ [分支 B - 放行] 设备 [{device_id}] YOLO 检出人体目标，已推入后台异步处理队列。")

    # 在响应返回后执行进程内后台任务，减轻 ESP32 挂起等待压力
    background_tasks.add_task(async_stage2_pipeline, image_bytes_list, metadata)

    return {
        "status": "queued",
        "message": "Person detected. Sent to Qwen2.5-VL for async processing."
    }

def run():
    """Start the gateway from the package or console entry point."""
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    run()
