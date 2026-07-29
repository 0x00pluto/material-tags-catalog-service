# 便携包覆盖升级会不会丢掉 `.env`？

**结论**：按官方 SOP **合并解压**到现有部署目录时，现场 `.env` **会保留**。发布 zip **永不包含** `.env`（只有 `.env.example`），解压不会用包内文件覆盖你的配置。推荐优先用包内 **一键升级脚本**（`upgrade.bat` / `upgrade.command`）：同样合并进当前目录，且**明确跳过**已有 `.env`，升级前还会备份为 `.env.bak.upgrade`。

## 会保留的情况

1. 运行 `upgrade.bat` / `upgrade.command`（或手动：先停掉正在跑的 `catalog-service`）。
2. 把新版 zip **合并解压**进当前正在用的部署目录（同名文件被新包覆盖；zip 里没有的文件保留）。
3. 确认包根仍有原来的 `.env`，再双击 `start.bat` / `start.command`。
4. 打开 `/health`，核对 `version` 与下载文件名中的版本一致。

`.env.example` 可能被新版本覆盖，这是预期行为；不要把真实配置只写在 `.env.example` 里。

## 会丢掉的情况（禁止作为升级路径）

- 先**删除整个部署目录**再解压。
- 解压工具「**清空目标目录**再解压」。
- 解压到全新目录却**忘记**从旧目录拷贝 `.env`。

这些操作会让现场 `CATALOG_ROOT` / `HOST` / `PORT` 等配置丢失。若无备份且记不清素材盘路径，只能重新配置。

## 建议

优先用一键升级脚本；也可升级前手动复制一份 `.env`。完整步骤见 [portable-dist-ci](../workflows/portable-dist-ci.md) 的「一键升级」与「原地升级」。
