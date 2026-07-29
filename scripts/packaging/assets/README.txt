素材标签索引服务 — 便携包（三步）

1. 复制 .env.example 为 .env（若已有可跳过）
2. 用记事本/文本编辑打开 .env，把 CATALOG_ROOT 改成你的素材盘路径
   Windows 示例：CATALOG_ROOT=D:\media
   macOS 示例：CATALOG_ROOT=/Volumes/media
3. 双击 start.bat（Windows）或 start.command（macOS）启动

验活：浏览器打开 http://127.0.0.1:8787/health（JSON 里有 version）
文档界面：http://127.0.0.1:8787/docs
查看版本：catalog-service\catalog-service.exe --version（Windows）
           ./catalog-service/catalog-service --version（macOS）

原地升级：
- 先停掉正在运行的服务，再把新版 zip「合并解压」到当前部署目录（不要先删整个文件夹）。
- 发布包不含 .env，合并解压会保留现场 .env；.env.example 被新版本覆盖无妨。
- 启动后核对 /health 的 version 与 zip 文件名中的版本一致。

说明：
- 无需安装 Python。
- 主程序在 catalog-service/ 目录；一次性工具在 build-catalog/。
- macOS 若提示无法打开：选中文件 → 右键 → 打开。
- 网络盘监听可能漏事件，服务内定时重建会兜底。
- 端口默认 8787，可在 .env 改 PORT。
