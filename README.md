# ESP32 AI Security Gateway

用于接收 ESP32-S3 摄像头图片的 Python 安防网关。网关先使用 YOLOv8 检测人体，再将通过筛选的图片交给独立运行的 Qwen2.5-VL / vLLM 服务分析，最后保存分析结果和原始图片。

本仓库包含网关、YOLO 权重和上传示例，不包含 ESP32 固件、前端或 Qwen 模型权重。

## 目录结构

```text
.
├── esp32_ai_security/          # 可导入的 Python 应用包
│   ├── __init__.py
│   ├── __main__.py             # python -m esp32_ai_security 启动入口
│   ├── main.py                 # FastAPI 应用与上传接口
│   ├── config.py               # 环境变量与项目路径配置
│   └── services/
│       ├── __init__.py
│       ├── yolo_filter.py      # 人体检测
│       ├── vllm_client.py      # 多模态模型调用
│       └── decision_engine.py  # 结果分流与事件存储
├── models/
│   └── yolov8n.pt              # YOLOv8n 权重
├── scripts/
│   └── upload_sample.py       # 模拟设备上传图片
├── tests/
│   ├── test_config.py          # 跨目录资源路径检查
│   ├── test_gateway.py         # 上传、过滤和事件落盘检查
│   ├── test_upload_sample.py   # 上传脚本检查
│   └── fixtures/images/       # test.jpg、test_nature.jpg、test_thief.jpg
├── data/security_logs/        # 运行时生成的事件记录，忽略版本控制
├── archive/
│   └── project_py.zip         # 原始项目归档，不作为运行入口
├── .env.example               # 可选的环境变量配置示例
├── .gitignore
├── pyproject.toml             # 项目元数据、依赖与测试配置
└── README.md
```

## 安装与启动

要求 Python 3.10 或更高版本。以下命令在仓库根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

`dev` 额外依赖用于运行测试；仅运行网关可使用 `python -m pip install -e .`。

推荐保留源码目录并使用上述可编辑安装。模型、样例图片和历史归档不打入 Python 包；
如果使用普通安装或单独分发 wheel，需要另行准备模型，并用绝对路径设置
`YOLO_MODEL_PATH` 和可写的 `STORAGE_DIR`，不能依赖源码布局下的默认资源位置。

如需覆盖默认配置，可复制并修改环境变量示例：

```bash
cp .env.example .env
# 编辑 .env 后，将变量导出到当前 shell
set -a
. ./.env
set +a
```

应用不会自动读取 `.env`；也可以直接通过 shell 的 `export` 设置变量。

启动网关：

```bash
python -m esp32_ai_security
```

或直接使用 Uvicorn：

```bash
uvicorn esp32_ai_security.main:app --host 0.0.0.0 --port 8080
```

默认监听 `http://localhost:8080`，接口文档位于 `http://localhost:8080/docs`。检出人体后的分析需要可访问的、提供 OpenAI 兼容接口的多模态模型服务；该服务需要另行部署，并与以下模型配置匹配。

## 配置

| 环境变量 | 默认值 | 含义 |
| --- | --- | --- |
| `YOLO_MODEL_PATH` | 项目根目录下的 `models/yolov8n.pt` | YOLO 权重文件路径 |
| `STORAGE_DIR` | 项目根目录下的 `data/security_logs` | 事件记录存储目录 |
| `VLLM_BASE_URL` | `http://localhost:8000/v1` | 多模态模型服务的 API 地址 |
| `VLLM_MODEL_NAME` | `./Qwen2.5-VL-7B-Instruct` | 模型服务所接受的模型标识 |

`YOLO_MODEL_PATH` 和 `STORAGE_DIR` 支持绝对路径；设置为相对路径时，以项目根目录为基准解析，与启动命令所在的工作目录无关。默认配置也使用项目根目录下的绝对路径。

`VLLM_MODEL_NAME` 会原样发送给模型服务。它是服务端的模型标识，即使看起来像路径，也不会转换为本地文件路径。

人体检测保持使用 COCO 的 `person` 类别（ID 为 `0`）、置信度阈值 `0.35`，并在 CPU 上运行。

## 上传图片

网关启动后，在另一个终端激活相同的虚拟环境并从仓库根目录运行：

```bash
# 默认上传 tests/fixtures/images/test_thief.jpg
python scripts/upload_sample.py

# 上传多张图片，并指定设备信息与目标网关
python scripts/upload_sample.py \
  tests/fixtures/images/test.jpg \
  tests/fixtures/images/test_thief.jpg \
  --url http://localhost:8080/api/v1/upload \
  --device-id esp32_cam_entrance_01 \
  --timestamp 2026-10-06T12:00:00Z

python scripts/upload_sample.py --help
```

脚本的默认图片按项目位置查找；通过位置参数传入的相对图片路径则按当前工作目录解析。

设备也可以直接发送 `POST /api/v1/upload`，使用 `multipart/form-data`：

| 字段 | 要求 | 说明 |
| --- | --- | --- |
| `device_id` | 必填 | 设备标识 |
| `timestamp` | 可选 | 设备提供的时间戳字符串 |
| `files` | 必填 | 一张或多张 JPEG 图片；多张图片重复使用此字段 |

未检出人体时，响应的 `status` 为 `filtered`，处理结束。检出人体时，响应的 `status` 为 `queued`，随后通过 FastAPI `BackgroundTasks` 在当前进程中调用模型并保存结果。`queued` 表示已安排后台处理，不代表模型分析或保存已经成功；处理失败会记录在服务日志中。

## 事件记录与能力边界

正常事件和可疑事件分别保存在 `NORMAL_<时间>_<设备ID>` 和 `ALERT_<时间>_<设备ID>` 目录中，每个目录包含 `result.json` 和 `frame_1.jpg` 等原始图片。默认位置为 `data/security_logs/`。

当前告警行为是输出日志并保存文件，尚未接入 MQTT、消息机器人或推送服务。后台处理使用进程内任务，不是持久化任务队列，进程退出可能导致尚未完成的任务丢失。

## 开发检查

安装开发依赖后，在仓库根目录运行：

```bash
python -m pytest
```

自动化测试不能替代真实模型服务联调。此次目录整理未运行真实 Qwen 服务的端到端验证；完整验证还需要部署模型服务、上传含人体的图片，并检查服务日志和事件文件。

## 从旧目录迁移

旧启动方式 `cd esp32_ai_security && python main.py` 改为在仓库根目录执行 `python -m esp32_ai_security`。上传示例由 `esp32_ai_security/test_upload.py` 移至 `scripts/upload_sample.py`，示例图片移至 `tests/fixtures/images/`，YOLO 权重移至 `models/`。

默认事件存储位置从旧工作目录下的 `security_logs/` 改为项目根目录下的 `data/security_logs/`。已有事件记录不会自动迁移；如果有旧的 `esp32_ai_security/security_logs/`，请手动移动至新目录，或将 `STORAGE_DIR` 指向旧目录，例如 `STORAGE_DIR=esp32_ai_security/security_logs`。
