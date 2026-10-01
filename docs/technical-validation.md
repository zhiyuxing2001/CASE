# 技术验证记录（立项阶段）

> 目的：在写正式代码前，**证伪或证实**规划中依赖的关键技术假设。
> 记录时间：立项评审阶段 · 环境：macOS 26.5.2 / Apple Silicon (arm64)

---

## 验证结论速览

| # | 假设 | 结论 | 对规划的影响 |
|---|---|---|---|
| V1 | DeepSeek 支持图片输入，可用于 OCR 精修 | ✅ **成立** | 无需本地训练 OCR，架构大幅简化 |
| V2 | macOS Vision 可从 Python 调用并识别中文 | ✅ **成立** | 双通道方案可行 |
| V3 | SQLite FTS5 能直接支持中文检索 | ⚠️ **部分成立，有坑** | 必须实现查询长度路由，否则静默失效 |

---

## V1 · DeepSeek 视觉能力核实

**方法**：查阅 DeepSeek 官方 API 文档（非二手信息）。

**实测结论**：

| 项 | 事实 |
|---|---|
| 支持视觉的模型 | **`deepseek-flash`**（DeepSeek-V4.1-Flash），上下文 1M，输出上限 384K |
| **不支持**视觉的模型 | `deepseek-v4-pro`（V4-Pro-0813）—— 规划中用于纯文本复杂推理 |
| 旧模型名 `deepseek-v4-flash-vision-exp` | 已下线，请求由最新 Flash 承接，按 Flash 计费 |
| 图片传入方式 | ① base64 data URL ② 外部 http(s) URL ③ Files API `file_id` |
| 支持格式 | JPEG、PNG、GIF、WebP（**按文件内容判断，不看扩展名**） |
| 单图 token 上限 | **1024 tokens**（无论 2000×2000 还是 5000×5000） |
| 单请求图片数上限 | 600 张 |
| 关键限制 | 图片**只能出现在 `user` 消息**中；`system`/`assistant` 带图返回 400 |
| 定价（空闲时段） | 输入缓存命中 **0.02 元/M**，未命中 1 元/M，输出 4 元/M（高峰时段翻倍） |

**推导出的两个规划要点**：

1. **单张处方图成本 ≈ 0.002–0.01 元**，视觉 OCR 的成本可忽略，不需为省钱牺牲准确率（例如不必先做图片压缩）。
2. **缓存命中价差 50 倍**（0.02 vs 1 元）→ 提示词的固定前缀（字典表、字段说明）**必须字节级稳定**，不要插入时间戳、随机 ID、动态排序的字典内容，否则每次都按未命中计费。

> 来源：[图像理解 | DeepSeek API Docs](https://api-docs.deepseek.com/zh-cn/guides/vision/)、[模型 & 价格 | DeepSeek API Docs](https://api-docs.deepseek.com/zh-cn/quick_start/pricing)

---

## V2 · macOS Vision OCR 可用性验证

**动机**：pyobjc（Vision 的 Python 绑定）在系统 Python 和 conda base 中均不存在，需确认可安装且中文可用。

**环境探测**：

```
python3 -c "import Vision"          → ModuleNotFoundError（conda base）
/usr/bin/python3 -c "import Vision" → ModuleNotFoundError
which shortcuts                     → /usr/bin/shortcuts（存在，但建快捷指令需 GUI 操作，不适合自动化）
which tesseract                     → 未安装
```

**方法**：在项目内建独立 venv，安装 `ocrmac`（封装 Vision 的轻量库），用 Pillow 生成一张中文"门诊病历 + 处方"测试图，跑 OCR。

**实测输出**：

```
=== macOS Vision OCR 结果 ===
[1.000] 中医门诊病历
[1.000] 主诉：胃脘胀痛反复发作3月余。
[1.000] 现病史：患者3月前无明显诱因出现胃脘胀痛，餐后加重。
[1.000] 四诊：舌淡红，苔薄白，脉弦细。
[0.500] 中医诊断：胃脘痛（肝胃不和证）
[1.000] 治法：疏肝理气和胃
[0.500] 处方：柴胡10g 白芍15g枳壳10g 甘草6g
[0.500] 香附10g 陈皮10g 茯苓15g白术12g
[1.000] 用法：水煎服，日一剂，分早晚温服。7剂。
```

**关键发现**：

1. ✅ **中文识别可用**，印刷体置信度普遍 1.0，无需任何模型下载，纯本地、离线、毫秒级。
2. ✅ **返回逐行 confidence + bbox 坐标** —— 这是双通道设计成立的基础：
   - 低置信行（上例中的 0.5）可**定向**送 DeepSeek 精修，而非整图重跑；
   - bbox 可用于版面重建（按 y 聚类成行、x 排序）。
3. ⚠️ **药味切分错误**：`白芍15g枳壳10g` 被粘连。Vision 只做"文字识别"，不做"语义切分"。
   → **这恰好证明了通道 B（DeepSeek 精修）不可省略**：必须由 LLM 输出 `[{herb:"白芍",dose:15},{herb:"枳壳",dose:10}]`。
4. 复现脚本：[`tools/ocr_smoke_test.sh`](../tools/ocr_smoke_test.sh) —— 自举创建 venv、生成中文测试图并跑 OCR，一条命令可复现本次验证结果。

**重要限制（必须在规划中正视）**：

> 本次验证用的是**印刷体合成图**，**结论不能推广到手写处方**。手写中医处方笔画潦草、简写与连笔普遍（如"白芍"写作"芍"），是全项目最大不确定项。
> → 因此规划中把 **P-3（采集真实手写评测集）** 列为 **M2 的阻塞前置**，并要求 **M2-A 阶段先跑基线再决定是否继续开发**。

---

## V3 · SQLite 中文全文检索验证

**动机**：SQLite FTS5 默认的 `unicode61` 分词器不切分中文，中文检索通常需要外部分词器（jieba 等）。`trigram` 分词器理论上可绕过，需实测。

**环境**：SQLite 3.51.2（`sqlite3` CLI 与 Python 内置版本一致），FTS5 可用。

**实测 1 —— trigram 对长词有效**：

```sql
CREATE VIRTUAL TABLE t_trigram USING fts5(body, tokenize='trigram');
SELECT body FROM t_trigram WHERE t_trigram MATCH '胃脘胀痛';   -- ✅ 命中
SELECT body FROM t_trigram WHERE t_trigram MATCH '疏肝理气';   -- ✅ 命中
```

**实测 2 —— trigram 对 2 字词静默失效（关键坑）**：

```sql
SELECT body FROM t_trigram WHERE t_trigram MATCH '风热';       -- ❌ 返回空，且不报错
```

**问题定性**：

- `trigram` 分词器按 **3 字符滑窗**建索引，**长度 < 3 的查询词无法匹配**。
- 最危险的是它**静默返回空集，不抛任何错误** —— 用户搜"风热"会以为库里没有相关病案，属于**最难排查的失效模式**。
- 而中医术语中 2 字词极其常见：**风热、气虚、血瘀、肝郁、脾虚、痰湿、阳虚、阴虚**……

**实测 3 —— LIKE 回退有效**：

```sql
SELECT body FROM t WHERE body LIKE '%风热%';   -- ✅ 命中
```

**采用的方案（写入 M1-6 / M1-9）**：

```python
def search(keyword: str, ...):
    if len(keyword) >= 3:
        # FTS5 trigram：有索引、有相关性排序、快
        return fts5_match(keyword)
    else:
        # 2 字及以下：LIKE 回退。单机数据量（万级）性能完全可接受
        return like_fallback(keyword)
```

**强制要求**：M1-9 的回归测试**必须包含 2 字词用例**，防止这个坑在后续重构中复发。

**v1.1 改进方向（F-4）**：用 jieba 预分词，写入空格分隔的 `search_tokens` 列，建 `unicode61` 索引，可统一支持任意长度词检索 —— 但引入分词器与词典维护成本，MVP 不做。

---

## 未验证 / 待验证事项（诚实登记）

| 事项 | 为何未验证 | 计划何时验证 |
|---|---|---|
| **手写处方识别准确率** | 需真实手写素材，且涉及患者隐私 | **M2-A**（阻塞性，不达标则重估产品形态） |
| 真实病历的版面多样性（横排/竖排/表格/盖章遮挡） | 同上 | M2-A |
| DeepSeek JSON Output 对复杂嵌套 schema 的遵循率 | 需真实调用与 quota | M2-10 |
| Word 导出排版在真实打印场景的观感 | 需完整导出链路 | M5-2 |
| 单机 SQLite 在万级病案 + FTS5 下的检索延迟 | 需真实数据量 | M6-2 |

---

## 环境事实存档

| 项 | 值 |
|---|---|
| 操作系统 | macOS 26.5.2 (Build 25F84)，Apple Silicon arm64 |
| Python | 3.13.13（miniconda3，路径 `/Users/zhiyuxing/Documents/miniconda3/bin/python3`） |
| SQLite | 3.51.2（FTS5 可用，trigram 可用） |
| Node.js | v26.7.0（nvm） |
| pnpm | ❌ 未安装（前端用 npm，或先装 pnpm） |
| pyobjc / ocrmac | ❌ 系统与 conda 均无 → 必须装在项目 venv |
| `DEEPSEEK_API_KEY` | ❌ 环境变量中不存在 → 待用户在 P-2 提供 |
| Git remote | `https://github.com/zhiyuxing2001/CASE.git` |
