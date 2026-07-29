# 端口已被占用

默认 `PORT=8787`。若启动失败报 address already in use：

1. 改 `.env` 中 `PORT`，或 `serve.py --port <其它>`。
2. macOS 查占用：`lsof -i :8787`
3. 确认没有第二个 `serve` 进程。
