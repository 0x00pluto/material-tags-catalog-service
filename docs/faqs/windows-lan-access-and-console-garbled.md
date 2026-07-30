# Windows：局域网访问不了 / 控制台「乱码」

## 局域网只能本机 `127.0.0.1` 访问

默认 `HOST=127.0.0.1`，进程只监听本机回环，其它机器用局域网 IP 连不上是预期行为。

1. 在运行目录 `.env` 中设置：

```text
HOST=0.0.0.0
```

也可启动时传 `--host 0.0.0.0`（覆盖 `.env`）。

2. 重启服务。日志应出现 `serving host=0.0.0.0`（若仍是 `127.0.0.1`，说明配置未生效）。
3. 在另一台机器浏览器打开 `http://<服务器局域网IP>:8787/health`。
4. 仍不通时：在 Windows「防火墙」中放行入站 TCP `8787`（或你改过的 `PORT`）。

仅本机调试可继续用默认 `127.0.0.1`。

## 浏览器一直转圈，按一下 Ctrl+C 才突然通了

多半是 **Windows CMD「快速编辑模式」**：用鼠标点选黑窗口会进入选中态，**整个控制台进程（含 HTTP）被暂停**；按 Esc / Ctrl+C 往往只是退出选中并解冻，并不是服务真挂了。

便携包 `start.bat` 启动时会尝试关闭**本窗口**的快速编辑；服务进程内也会再关一次。启动日志应出现 `console quick-edit disabled`。

即使用 `start.bat` 仍假死时：

1. 看日志有没有 `console quick-edit disabled`；若是 WARNING「not disabled」或完全没有该行，请换新便携包 / 确认部署目录里的 `start.bat` 已更新
2. 不要用鼠标去点/拖选正在跑服务的 CMD 黑窗
3. 或改用 Windows Terminal / PowerShell
4. 仍可手动：CMD 标题栏右键 → 属性 → 选项 → 取消「快速编辑模式」（可勾「设为默认值」）

## 控制台出现 `[32m` / `□[0m` 一类字符

那是 **ANSI 颜色转义码**，老版 Windows CMD 不渲染，看起来像乱码；中文路径本身通常正常。

服务端已关闭 Uvicorn 彩色输出（`use_colors=False`）。升级/换新便携包后重启即可；临时也可改用 Windows Terminal / PowerShell。
另外新版 `start.bat` 启动时会自动执行 `chcp 65001` 切到 UTF-8 代码页，减少首屏中文提示乱码概率。
