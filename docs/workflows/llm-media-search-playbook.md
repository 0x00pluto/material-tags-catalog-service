# LLM Playbook：本服务素材检索（HTTP）

本 **Material Tags Catalog Service** 的 Agent / 大模型检索手册。读完即可用 **curl** 调本实例的 `GET /v1/catalog/search`，按需自拼下载链，并按模板回复用户。

**主路径是本文 HTTP 一二三**（无技能依赖）。本机 Cursor / 互远技能库环境可另装可选技能做渐进披露，见文末 §11。

**用 HTTP 直接读本文**（推荐分享链接；正文里的地址已按本实例渲染）：

```bash
curl -s '{{api_base}}/v1/docs/llm-media-search-playbook'
```

浏览器打开同一地址亦可。仓库模板（含占位符）：`docs/workflows/llm-media-search-playbook.md`。

search 参数与匹配语义以 [serve-catalog-service.md](./serve-catalog-service.md) 与 [material-tags-catalog.md](../contracts/material-tags-catalog.md) 为准。

## 1. 何时用 / 不用

| 场景 | 是否本手册 |
|------|------------|
| 对本 catalog 按关键词找视频/媒体 | **用** |
| 用户提到项目名 / 拍摄目录，要收窄范围 | **用**（加 `path_prefix`） |
| 公网图库 / Unsplash / 商用素材站 | **不用** |
| 对象存储 / CDN 上传 | **不用** |
| 本机磁盘递归扫文件 | **不用** |
| 重建 catalog（`POST /v1/catalog/rebuild`） | **不用**；交运维，Agent **禁止**自行 rebuild |

## 2. 前置

| 变量 | 本实例值 | 说明 |
|------|----------|------|
| `api_base` | `{{api_base}}` | 本 Catalog HTTP 根；**无**尾斜杠（由打开本文的请求地址注入） |
| `file_base` | `{{file_base}}` | 可选下载前缀；来自环境变量 `FILE_BROWSER_BASE`（无尾斜杠）。若为「未配置」则不要拼下载链 |

**索引是什么**：服务把素材盘上 `*.material-tags.json` 合并为 `material-tags-catalog.jsonl`；`GET /v1/catalog/search` **只读**该文件当前行。行字段见 [契约](../contracts/material-tags-catalog.md)。

需要：本机有 `curl`；能访问本实例。若配置了 `file_base`，下载能否打开取决于用户网络与 File Browser 权限——本手册只负责拼 URL，不代登录。

## 3. 推荐顺序（一二三）

```text
用户需求 → ① 先定 path_prefix（若有项目/目录）→ ② 再写短关键词 q → ③ curl search
       → ④（仅当 file_base 已配置）用 media_guess 拼 download_url → ⑤ 按模板回复
```

### ① `path_prefix`（可选）

- 用户提到项目名、拍摄日目录或已知素材文件夹时，抽出相对 `CATALOG_ROOT` 的目录前缀。
- 须与 catalog 行里 `tags_path` **字面一致**（目录边界：等于该前缀，或以 `prefix/` 开头）。
- 可重复多个，语义为 **OR**；最多 20 个。
- 非法：含 `..`、或以 `/` 开头 → API **400**。
- 未提项目则省略，全库检索。

### ② `q`（必填）

- 把自然语言压成**短**关键词；空白或中英文逗号分词；多词 **AND**。
- 过宽（整句长描述）先收窄再搜。
- 可用视频里说过的**口播原话短句**当 `q`（匹配 `title` / `description` / `keywords` / `subtitle`）。`items[]` **不含** `subtitle`：回复只用 `title` / `description`，**禁止**假设 items 有逐字稿或引用口播原文。
- search **不匹配** `stem`：勿用纯镜号如 `C0300` 当唯一关键词。
- 旧索引 JSONL 可能还没有 `subtitle` 键：仅口播词会 0 命中。须运维成功 **rebuild** 后新行才带键；Agent **禁止**自行 rebuild。

### ③ curl

```bash
# 全库
curl -s --get '{{api_base}}/v1/catalog/search' \
  --data-urlencode 'q=女受访者' \
  --data-urlencode 'limit=20' \
  --data-urlencode 'offset=0'

# 单项目
curl -s --get '{{api_base}}/v1/catalog/search' \
  --data-urlencode 'q=玄关' \
  --data-urlencode 'path_prefix=某项目目录名' \
  --data-urlencode 'limit=20'

# 多项目 OR
curl -s --get '{{api_base}}/v1/catalog/search' \
  --data-urlencode 'q=图' \
  --data-urlencode 'path_prefix=项目A' \
  --data-urlencode 'path_prefix=项目B' \
  --data-urlencode 'limit=20'

# 口播原话短句（非访谈长文）；items 仍不含 subtitle
curl -s --get '{{api_base}}/v1/catalog/search' \
  --data-urlencode 'q=跑遍了整个武汉' \
  --data-urlencode 'limit=20'
```

**200 响应要点**：`query`、`tokens`、`total_matched`、`path_prefixes`（未传为 `[]`）、`items[]`（与 catalog 行一致，**仅省略 `subtitle`**）。无命中：`items=[]`，`total_matched=0`，仍 200。若口播词 0 命中而画面词能命中，先换词；确认上游已写出 v4 字幕后交运维 rebuild，不要自行 `POST .../rebuild`。

参数细节（`limit` 钳制、加权排序、casefold 等）见 [serve-catalog-service.md](./serve-catalog-service.md)。

## 4. 下载链接公式（可选）

API **不**返回 `download_url`。仅当 `file_base` 已配置（不是「未配置 FILE_BROWSER_BASE」）且 `media_guess` 非空时再拼：

```text
{file_base}/{segment_encode(media_guess)}
```

规则：

1. 去掉 `file_base` 尾斜杠；去掉 `media_guess` 首部多余 `/`。
2. 按 `/` 分段，对**每一段**做 URL 编码（等价 `encodeURIComponent`），再用 `/` 连接。
3. 拼成 `{file_base}/{encoded}`。

伪代码：

```text
relative = trim(media_guess).lstrip("/")
encoded  = "/".join(encodeURIComponent(seg) for seg in relative.split("/"))
download_url = file_base.rstrip("/") + "/" + encoded
```

短例：`media_guess = "项目A/已处理/镜头.MP4"` →  
`{{file_base}}/%E9%A1%B9%E7%9B%AEA/%E5%B7%B2%E5%A4%84%E7%90%86/%E9%95%9C%E5%A4%B4.MP4`  
（仅非 ASCII 段被编码；ASCII 段如 `clip-day1` 保持原样。）

| 情况 | 处理 |
|------|------|
| `file_base` 未配置 | 不拼链；回复写「下载：暂无」；**禁止编造** |
| `media_guess` 为空 / null | 同上 |
| File Browser 打开 404 | 公式仍可能正确；提示用户确认文件是否仍在网盘，或运维是否需改 `FILE_BROWSER_BASE` |

## 5. 媒体元数据展示

API 返回原始字段；对用户展示时自行格式化（**禁止根据 description 推断**）：

| 对用户标签 | 源字段 | 有值 | 空 / null |
|------------|--------|------|-----------|
| 画幅 | `orientation` | 原文 trim | 未知 |
| 时长 | `duration_s` | `{数字}s`（如 `11.01s`） | 未知 |
| 比例 | `aspect_ratio` | 原文 trim | 未知 |

三行**始终输出**。

## 6. 对用户回复模板（强制）

`description` **全文照抄**，禁止截断、摘要或改写压缩。对用户**不展示** `keywords`。

```markdown
找到 **{本次条数}** 条相关素材（关键词「{q}」，共命中 **{total_matched}**）{可选：路径前缀说明}。

1. **{title}**
   - 描述：{description 全文}
   - 画幅：{orientation 或 未知}
   - 时长：{duration_s 格式化或 未知}
   - 比例：{aspect_ratio 或 未知}
   - 下载：[{title}]({download_url})   ← 无链时写「下载：暂无」
   - 文件：`{stem}`

---
需要下一页可继续翻页，或换关键词 / 路径前缀继续搜。
```

说明：

- `{本次条数}` = 本次 `items.length`（可能小于 `total_matched`）
- `{q}` = 响应里的 `query`
- `path_prefixes` 非空时追加，例如 `，路径前缀：\`某项目目录名\``；多个用顿号或逗号；为空则省略
- 无 `download_url` 时写「下载：暂无」
- 0 命中：只提示换词或放宽路径前缀，不输出空列表伪结果

### 硬约束（违反即不合格）

- 禁止只有「文件名 / 描述」、无下载列的表格（无链时仍保留「下载：暂无」行）
- 禁止只列链接不写描述；禁止对用户列出 keywords
- `description` 必须完整原文
- 画幅 / 时长 / 比例三行始终输出；无值用「未知」——禁止猜测
- 仅当已拼出真实 `download_url` 时使用 Markdown 链接：`[标题](url)`
- 禁止编造不存在的 `download_url`
- 禁止把 search `items` 当成含口播全文；禁止引用或编造逐字稿（`subtitle` 不在响应里）

## 7. 改写 q / path_prefix 与翻页

| 情况 | 建议 |
|------|------|
| `total_matched = 0` | 换更短、更贴近画面/人物/场景的词；或放宽/去掉 `path_prefix`；勿编造链接 |
| 命中过多 | **优先**加 `path_prefix` 限定项目，再加限定词做多词 AND，或降低 `limit` |
| 需要下一页 | 增大 `offset`（如 `offset=20` 且 `limit=20`） |
| HTTP 400 | 检查 `q` 是否为空；`path_prefix` 是否含 `..` 或以 `/` 开头；路径字面是否与 `tags_path` 一致 |
| HTTP 404（catalog 缺失） | **不要**自行 `POST .../rebuild`；告知运维检查服务与索引 |
| 连接失败 / 非 200 | 检查 `api_base`、内网连通 |

## 8. 正例

**用户**：「帮我找素材里宿舍相关镜头」

1. 未提项目 → 不加 `path_prefix`；`q=宿舍`
2. curl：

```bash
curl -s --get '{{api_base}}/v1/catalog/search' \
  --data-urlencode 'q=宿舍' \
  --data-urlencode 'limit=2'
```

3. 按 §6 模板回复；仅当 `file_base` 已配置时拼下载链。

**用户**：「在某某项目目录里找玄关」

1. `path_prefix=` 与盘面一致的相对目录名，`q=玄关`
2. curl：

```bash
curl -s --get '{{api_base}}/v1/catalog/search' \
  --data-urlencode 'q=玄关' \
  --data-urlencode 'path_prefix=某项目目录名' \
  --data-urlencode 'limit=2'
```

3. 回复首行注明路径前缀；再按模板列条目。

### 8.1 演练：样例 search JSON → 合规回复

以下为 **API 真实形状**（无 `download_url` / `*_display`；由调用方按 §4–§5 推导）。描述略作缩短仅便于阅读本文；对用户须全文照抄响应里的 `description`。

```json
{
  "query": "玄关",
  "tokens": ["玄关"],
  "limit": 1,
  "offset": 0,
  "total_matched": 2,
  "path_prefixes": ["某项目目录名"],
  "items": [
    {
      "stem": "C0300_玄关特写",
      "tags_path": "某项目目录名/已处理/C0300_玄关特写.material-tags.json",
      "media_guess": "某项目目录名/已处理/C0300_玄关特写.MP4",
      "schema_version": "2",
      "generated_at": "2026-07-30T11:05:03+08:00",
      "title": "玄关特写",
      "description": "竖屏无人物产品特写，画面居中为玄关衣帽架与鞋凳，室内均匀柔光。",
      "keywords": "玄关, 衣帽架, 竖屏",
      "width": 1080,
      "height": 1920,
      "duration_s": 11.01,
      "aspect_ratio": "9:16",
      "orientation": "竖屏"
    }
  ]
}
```

推导：

1. `orientation` → 画幅「竖屏」；`duration_s` →「11.01s」；`aspect_ratio` →「9:16」。
2. 若 `file_base` 已配置：`download_url` = `{{file_base}}` + `/` + 对 `media_guess` 各段编码；否则「下载：暂无」。
3. **不**把 `keywords` 写进对用户回复。

合规 Markdown 回复（已配置 `file_base` 时）：

```markdown
找到 **1** 条相关素材（关键词「玄关」，共命中 **2**），路径前缀：`某项目目录名`。

1. **玄关特写**
   - 描述：竖屏无人物产品特写，画面居中为玄关衣帽架与鞋凳，室内均匀柔光。
   - 画幅：竖屏
   - 时长：11.01s
   - 比例：9:16
   - 下载：[玄关特写]({{file_base}}/%E6%9F%90%E9%A1%B9%E7%9B%AE%E7%9B%AE%E5%BD%95%E5%90%8D/%E5%B7%B2%E5%A4%84%E7%90%86/C0300_%E7%8E%84%E5%85%B3%E7%89%B9%E5%86%99.MP4)
   - 文件：`C0300_玄关特写`

---
需要下一页可继续翻页，或换关键词 / 路径前缀继续搜。
```

（上例中路径编码仅示意；实际按 §4 对每一段分别编码。）

无元数据时（`orientation` / `duration_s` / `aspect_ratio` 均为 null）：三行均写「未知」，其余结构相同。

## 9. 反例（不应本手册处理）

- 「把这张图传到 CDN」→ 上传流程，非 search
- 「重建 material catalog」→ 运维；不调 rebuild
- 「搜 Unsplash 蓝天」→ 公网图库

## 10. 对用户展示反例（禁止）

- 只有「文件名 / 描述」两列表格、无下载行
- 只有标题超链接、省略或截断 `description`
- 列出 keywords，或根据描述「猜」横竖屏/时长
- 编造不存在的 `download_url`
- 从 search 结果引用或编造口播原文（items 没有 `subtitle`）

## 11. 可选：安装技能（渐进披露）

本文 **不依赖** 外部技能：任意能访问本实例的模型，按 §1–§10 用 curl 即可完成检索与回复。

若本机已接入互远技能库（Cursor / Claude 等），可安装配套技能，由 Agent **按意图触发**再读 `SKILL.md` / 跑 CLI，避免把整份手册常驻塞进上下文：

```bash
huyuan-ai-cli huyuan-skill install huyuan-ai-media-resource-finder-master
```

| 情况 | 怎么做 |
|------|--------|
| 已安装该技能 | 用户说「搜内网素材 / 找拍摄下载链接」等时优先走技能（配置 → `search.mjs` → 模板）；行为应与本文一致（先 `path_prefix` 再 `q`、勿 rebuild、回复模板硬约束） |
| 未安装 / 非本机 / 无 CLI | **继续按本文** HTTP 一二三执行；不要因为缺技能而停住 |
| 技能与本文步骤冲突 | **以本文（本服务 playbook）为准**；技能仅为可选快捷封装 |

首次安装后通常还需初始化本机配置（`api_base` / `file_base`）；以技能包内 `instructions/init.md` 为准。`api_base` 应对准**本实例**（本文注入的值），勿写死过期内网地址。

## 相关文档

| 文档 | 用途 |
|------|------|
| [serve-catalog-service.md](./serve-catalog-service.md) | 常驻服务、search 参数与匹配规则（运维 + API） |
| [material-tags-catalog.md](../contracts/material-tags-catalog.md) | JSONL 行字段契约 |
