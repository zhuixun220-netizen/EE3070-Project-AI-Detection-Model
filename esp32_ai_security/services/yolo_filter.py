import io
import logging
from PIL import Image
from ultralytics import YOLO
from esp32_ai_security import config

logger = logging.getLogger("YOLOFilter")

class YOLOFilter:
    def __init__(self, model_path: str = config.YOLO_MODEL_PATH):
        # 首次加载模型权重
        self.model = YOLO(model_path)

    def detect_person(self, image_bytes_list: list[bytes]) -> bool:
        """
        检查多张图片序列中，是否至少有一张图片包含 Person (conf >= 0.35)
        """
        for idx, img_bytes in enumerate(image_bytes_list):
            try:
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                
                # 【关键修改】：强行指定 device='cpu' 进行推理
                results = self.model.predict(img, device='cpu', verbose=False)

                for r in results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        if cls_id == config.PERSON_CLASS_ID and conf >= config.PERSON_CONF_THRESHOLD:
                            logger.info(f"第 {idx + 1} 张图片匹配成功: Person, 置信度: {conf:.2f}")
                            return True
            except Exception as e:
                logger.error(f"YOLO 解析第 {idx + 1} 张图像失败: {e}")

        return False
