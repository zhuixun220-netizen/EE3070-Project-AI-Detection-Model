import os
import requests

# 1. 网关接口地址与图片路径
url = "http://localhost:8080/api/v1/upload"
image_path = "test_thief.jpg"

# 2. 检查图片文件是否存在
if not os.path.exists(image_path):
    print(f"❌ 错误：在当前目录下找不到 {image_path}，请先确认图片已上传！")
    exit(1)

# 3. 模拟 ESP32-S3 上传的元数据
data = {
    "device_id": "esp32_cam_entrance_01",
    "timestamp": "2026-09-30T21:00:00Z"
}

# 4. 读取 test.jpg 并发送 POST 请求
print(f"正在读取 {image_path} 并发送至网关...")

with open(image_path, "rb") as f:
    files = [
        ("files", (image_path, f, "image/jpeg"))
    ]
    response = requests.post(url, data=data, files=files)

# 5. 打印测试结果
print("\n--- 网关响应 ---")
print(f"HTTP 状态码: {response.status_code}")
try:
    print("返回内容:", response.json())
except Exception:
    print("返回内容:", response.text)