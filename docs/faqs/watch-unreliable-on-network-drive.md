# 网络盘上 watchdog 不可靠

SMB / 网络盘上文件监听常漏事件。对策：保持 `SCHEDULE_ENABLED=true`，用定时全量 rebuild 兜底；watch 仅作加速。
