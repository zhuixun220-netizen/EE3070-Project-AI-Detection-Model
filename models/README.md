# 模型资源

`yolov8n.pt` 是网关本地运行的人体检测权重。默认使用 CPU。

通过 `YOLO_MODEL_PATH` 指定其他权重；相对路径以项目根目录为基准。
Qwen 模型由独立 API 服务加载，不放在此目录。通过 `VLLM_BASE_URL` 和
`VLLM_MODEL_NAME` 配置该服务的地址和模型标识。
