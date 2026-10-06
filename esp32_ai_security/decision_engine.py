import os
import json
import logging
from datetime import datetime
import config

logger = logging.getLogger("DecisionEngine")

class DecisionEngine:
    def __init__(self):
        os.makedirs(config.STORAGE_DIR, exist_ok=True)

    async def process_decision(self, result: dict, metadata: dict, image_bytes_list: list[bytes]):
        is_suspicious = result.get("is_suspicious", False)
        device_id = metadata.get("device_id", "unknown")

        if is_suspicious:
            await self._trigger_alert(result, metadata, image_bytes_list)
        else:
            await self._archive_event(result, metadata, image_bytes_list)

    async def _trigger_alert(self, result: dict, metadata: dict, image_bytes_list: list[bytes]):
        """结果 1：is_suspicious == true，执行警报推送"""
        logger.warning(
            f"🚨 [高危告警触发] 设备 [{metadata.get('device_id')}]\n"
            f"行为描述: {result.get('behavior_description')}\n"
            f"置信度: {result.get('confidence')}\n"
            f"判定原因: {result.get('reasoning')}"
        )
        # TODO: 此处可对接 MQTT、微信 / 钉钉机器人 API 或 Apple APNs 服务
        self._save_record("ALERT", result, metadata, image_bytes_list)

    async def _archive_event(self, result: dict, metadata: dict, image_bytes_list: list[bytes]):
        """结果 2：is_suspicious == false，正常归档"""
        logger.info(f"🟢 [安全事件归档] 设备 [{metadata.get('device_id')}] 行为正常，已存入日志。")
        self._save_record("NORMAL", result, metadata, image_bytes_list)

    def _save_record(self, level: str, result: dict, metadata: dict, image_bytes_list: list[bytes]):
        record_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_name = f"{level}_{record_time}_{metadata.get('device_id')}"
        record_dir = os.path.join(config.STORAGE_DIR, dir_name)
        os.makedirs(record_dir, exist_ok=True)

        # 1. 保存结构化结果 JSON
        with open(os.path.join(record_dir, "result.json"), "w", encoding="utf-8") as f:
            json.dump({"metadata": metadata, "analysis": result}, f, ensure_ascii=False, indent=2)

        # 2. 异步存储图片
        for idx, img_bytes in enumerate(image_bytes_list):
            with open(os.path.join(record_dir, f"frame_{idx + 1}.jpg"), "wb") as f:
                f.write(img_bytes)