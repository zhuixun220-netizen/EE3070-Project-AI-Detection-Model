import base64
import json
import logging
from openai import AsyncOpenAI
import config

logger = logging.getLogger("VLLMClient")

class QwenVLClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key="EMPTY",
            base_url=config.VLLM_BASE_URL,
        )

    async def analyze_security_images(self, image_bytes_list: list[bytes], metadata: dict) -> dict:
        """
        组装多模态 Prompt 并请求 Qwen2.5-VL
        """
        system_prompt = (
            "你是一个专业的智能安防监控分析大脑。"
            "请分析接收到的连续监控图片序列，严格按照指定的 JSON 格式返回分析结果，不要包含任何 markdown 标签或多余解释。\n"
            "输出 JSON 格式要求：\n"
            "{\n"
            '  "is_suspicious": true / false,\n'
            '  "confidence": 0.0 ~ 1.0,\n'
            '  "behavior_description": "一句话客观描述画面中的人物动作与状态",\n'
            '  "reasoning": "判定是否可疑的逻辑原因"\n'
            "}\n"
            f"设备元信息: 设备ID={metadata.get('device_id')}, 时间戳={metadata.get('timestamp')}"
        )

        content = [{"type": "text", "text": system_prompt}]

        # 编码图片序列存入 Payload
        for img_bytes in image_bytes_list:
            b64_str = base64.b64encode(img_bytes).decode('utf-8')
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64_str}"}
            })

        response = await self.client.chat.completions.create(
            model=config.VLLM_MODEL_NAME,
            messages=[{"role": "user", "content": content}],
            max_tokens=300,
            temperature=0.1
        )

        raw_text = response.choices[0].message.content.strip()
        return self._parse_json_response(raw_text)

    def _parse_json_response(self, raw_text: str) -> dict:
        """解析并格式化大模型返回的 JSON"""
        text = raw_text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(text)
        except Exception as e:
            logger.error(f"解析 JSON 响应异常: {e}, 原始输出: {raw_text}")
            return {
                "is_suspicious": False,
                "confidence": 0.0,
                "behavior_description": "大模型返回格式解析异常",
                "reasoning": raw_text
            }