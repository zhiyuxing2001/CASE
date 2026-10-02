# CASE 模型接入层设计（API 为主，预留自托管）

> 阶段二 · B5（AI 辅助）的前置设计
> CASE — Clinical Archives for Student Encounters

| 项 | 内容 |
|---|---|
| 版本 | v1.0 |
| 状态 | **接口契约设计，尚未实现** |
| 决策 | **以 DeepSeek API 调用为主**；自托管（自有 H20 服务器）**延后**，现在只预留接口 |
| 影响范围 | `backend/app/llm/`（新增模块）、`.env` 配置、一次待执行的数据库迁移 |

> **本文只定义接口契约与配置形态，不含任何实现代码。** 数据库与现有代码均未改动。

---

## 一、为什么这个"预留"几乎是免费的

三个既有选择让自托管的接入成本降到接近零：

| 既有选择 | 带来的好处 |
|---|---|
| 后端用 `openai` SDK（而非 DeepSeek 私有 SDK） | 请求/响应结构已与 OpenAI 协议对齐 |
| 模型能力已区分（`deepseek-flash` 支持视觉、`deepseek-v4-pro` 不支持） | 已经需要"按能力选模型"，路由抽象本来就要做 |
| vLLM / SGLang 都暴露 OpenAI 兼容接口 | **自托管与 API 可以共用同一个 Provider 类**，只是 `base_url` 不同 |

结论：**预留的真正内容不是"再写一套自托管客户端"，而是"把模型名从业务代码里去掉"。**
只要业务代码说的是"我要做视觉结构化"而不是"我要用 deepseek-flash"，将来加自托管端点就只是配置问题。

---

## 二、模块划分（预留）

```
backend/app/llm/
├── __init__.py
├── types.py           # Capability / ChatRequest / ChatResponse / Usage
├── base.py            # LlmProvider 协议（本文的核心契约）
├── openai_compat.py   # 唯一需要的实现：同时覆盖 API 与自托管
├── router.py          # 按能力路由 + 回退链（端点数 > 1 时才真正起作用）
└── registry.py        # 从 .env 构建端点与路由
```

**关键设计**：`openai_compat.py` 一个类覆盖两种部署形态。
自托管落地时不新增 Provider，只新增一条端点配置。

---

## 三、接口契约

### 3.1 能力枚举

业务代码只声明**能力需求**，永不声明模型名。

```python
class Capability(StrEnum):
    VISION       = "vision"        # 接受图片输入
    JSON_MODE    = "json_mode"     # 受约束的结构化输出
    TOOL_CALLS   = "tool_calls"    # 工具调用
    LONG_CONTEXT = "long_context"  # 超长上下文（≥200K）
    STREAMING    = "streaming"     # 流式输出
```

### 3.2 Provider 协议——**这是预留的核心**

```python
class LlmProvider(Protocol):
    """模型提供方。API 与自托管共用此契约。"""

    name: str
    kind: ProviderKind                      # API | SELF_HOSTED
    capabilities: frozenset[Capability]

    def supports(self, required: Iterable[Capability]) -> bool: ...

    def chat(self, request: ChatRequest) -> ChatResponse: ...

    def stream(self, request: ChatRequest) -> Iterator[ChatChunk]: ...

    def health(self) -> ProviderHealth: ...   # 供熔断器使用
```

```python
class ProviderKind(StrEnum):
    API         = "api"           # 第三方 API（当前唯一在用）
    SELF_HOSTED = "self_hosted"   # 自建推理服务（已预留，未启用）
```

> `ProviderKind` 是留给自托管的**唯一显式标记**。路由策略、用量归集、隐私提示都读它。

### 3.3 请求与响应

```python
@dataclass(frozen=True)
class ChatRequest:
    task: Task                       # 业务任务，非模型名
    messages: Sequence[Message]
    images: Sequence[ImageInput] = ()
    json_schema: Mapping | None = None
    temperature: float = 0.2
    max_tokens: int | None = None
    timeout_s: float = 60.0

@dataclass(frozen=True)
class ChatResponse:
    text: str
    structured: Mapping | None       # JSON 模式下的解析结果
    provider: str                    # 端点名，用于溯源
    model: str
    usage: Usage
    latency_ms: int
    degraded: bool                   # 是否走了回退链

@dataclass(frozen=True)
class Usage:
    tokens_in: int
    tokens_cached: int
    tokens_out: int
    cost_yuan: float                 # 自托管端点为 0
```

**`provider` 字段是溯源的关键**：将来的 `ocr_job.provider` 与 `ai_conversations.provider` 取自这里。

### 3.4 任务枚举与能力映射

业务代码只认任务名。**这是把模型名从业务层剥离的机制。**

```python
class Task(StrEnum):
    OCR_STRUCTURING = "ocr_structuring"   # 处方图 → 结构化字段
    CASE_QA         = "case_qa"           # 病案库问答（带出处）
    NOTE_DRAFT      = "note_draft"        # 心得初稿
    NOTE_POLISH     = "note_polish"       # 润色 / 学术化
    TERM_NORMALIZE  = "term_normalize"    # 术语归一建议
```

映射写在配置里（可改而不动代码）：

| 任务 | 能力需求 | 当前走哪个端点 |
|---|---|---|
| `OCR_STRUCTURING` | `VISION`, `JSON_MODE` | DeepSeek API（`deepseek-flash`） |
| `CASE_QA` | `JSON_MODE`, `STREAMING` | DeepSeek API |
| `NOTE_DRAFT` | `STREAMING` | DeepSeek API |
| `NOTE_POLISH` | `STREAMING` | DeepSeek API |
| `TERM_NORMALIZE` | `JSON_MODE` | **本地字典优先**，未命中才调模型 |

> `TERM_NORMALIZE` 目前基本不走模型：药名归一与形近字纠错已由本地字典 + 相似度匹配解决（见 `backend/app/dictionary.py`）。保留该任务是为了将来处理字典未覆盖的情况。

---

## 四、端点配置

### 4.1 端点定义

```python
@dataclass(frozen=True)
class LlmEndpoint:
    name: str                        # 端点标识，写入溯源字段
    kind: ProviderKind
    base_url: str
    api_key: str
    model: str
    capabilities: frozenset[Capability]
    context_window: int
    priority: int = 100              # 越小越优先
    price_input_cached: float = 0.0  # 元/百万 tokens
    price_input: float = 0.0
    price_output: float = 0.0
```

`price_*` 让设置页能显示"本机 API 花了多少钱"；自托管端点填 0。

### 4.2 `.env` 形态（当前）

```bash
# ── 端点注册表（逗号分隔）─────────────────────────────
LLM_ENDPOINTS=deepseek-api

# ── deepseek-api ──────────────────────────────────────
LLM_DEEPSEEK_API_KIND=api
LLM_DEEPSEEK_API_BASE_URL=https://api.deepseek.com
LLM_DEEPSEEK_API_KEY=                # 留空则 AI 功能优雅降级
LLM_DEEPSEEK_API_MODEL=deepseek-flash
LLM_DEEPSEEK_API_CAPABILITIES=vision,json_mode,tool_calls,long_context,streaming
LLM_DEEPSEEK_API_CONTEXT=1000000

# ── 路由偏好：api | selfhosted | auto ─────────────────
LLM_PREFER=api

# ── 任务 → 能力需求 ───────────────────────────────────
LLM_TASK_OCR_STRUCTURING=vision,json_mode
LLM_TASK_CASE_QA=json_mode,streaming
LLM_TASK_NOTE_DRAFT=streaming
LLM_TASK_NOTE_POLISH=streaming
LLM_TASK_TERM_NORMALIZE=json_mode
```

### 4.3 `.env.example` 中预留的自托管段（注释状态）

```bash
# ══════════════════════════════════════════════════════
#  自托管推理服务（预留，未启用）
#  服务器需提供 OpenAI 兼容接口（vLLM / SGLang 均可）
# ══════════════════════════════════════════════════════
# LLM_ENDPOINTS=deepseek-api,selfhosted
#
# LLM_SELFHOSTED_KIND=self_hosted
# LLM_SELFHOSTED_BASE_URL=https://gpu.example.com/v1
# LLM_SELFHOSTED_API_KEY=            # 必须设置，不要裸奔在公网
# LLM_SELFHOSTED_MODEL=deepseek-r1-distill-qwen-32b
# LLM_SELFHOSTED_CAPABILITIES=json_mode,streaming
# LLM_SELFHOSTED_CONTEXT=131072
#
# 文本任务走自托管，视觉任务因自托管未声明 vision 而自动回落 API：
# LLM_PREFER=auto
```

> 注意 `LLM_SELFHOSTED_CAPABILITIES` **不含 `vision`**。这是有意的：视觉任务会自动落到 API，
> 无需在业务代码里写"如果自托管则……"。

---

## 五、路由与回退（预留）

```
resolve(task) →
  1. 取该任务的能力需求
  2. 过滤：supports(all required)
  3. 过滤：熔断器判定为健康的端点
  4. 排序：按 priority；LLM_PREFER=selfhosted 时 SELF_HOSTED 优先
  5. 返回 [首选, 回退链…]
```

**当前端点数 = 1，路由退化为直通**——但契约已就位，加第二个端点无需改调用方。

`LLM_PREFER` 的语义：

| 取值 | 行为 |
|---|---|
| `api` | 全部走 API（**当前设定**） |
| `selfhosted` | 优先自托管；能力不足时自动回落 API |
| `auto` | 自托管健康且能力满足时用自托管，否则 API |

### 降级阶梯

```
双通道（本地 Vision + 模型结构化）
   │ 端点不可用 / 无网络
   ▼
仅本地 Vision（文本入库，结构化字段留空待人工）
   │ API Key 未配置
   ▼
纯手工录入（AI 入口显示"未配置 Key"，其余功能完全正常）
```

**核心功能（录入、检索、本地 OCR、导出）零依赖模型**——这条自始未变。

---

## 六、数据模型影响（登记，**现在不执行**）

接入第二个端点后，`model` 一个字段不足以回答"这条记录是哪个端点产生的"，用量与费用也无法分摊。

| 表 | 待新增 | 说明 |
|---|---|---|
| `ocr_job` | `provider TEXT DEFAULT ''` | 端点名，如 `deepseek-api` |
| `ai_conversations` | `provider TEXT DEFAULT ''` | 同上 |

**现在不加列**，理由：功能尚未存在，为它改 schema 属于推测性设计；且我们已确认单机库的迁移成本很低（`alembic upgrade head` 一条命令）。

迁移落地时应同时回填历史数据：`UPDATE ocr_job SET provider='deepseek-api' WHERE provider=''`。

> 这条登记在本文，避免将来接入自托管时漏掉溯源与费用归属。

---

## 七、现在实现什么 / 预留什么

| 项 | B5 实现 | 预留（自托管落地时） |
|---|---|---|
| `LlmProvider` 协议 | ✅ 定稿并按此实现 | — |
| `OpenAiCompatibleProvider` | ✅ 一个类 | 复用同一类，不新增代码 |
| 端点注册表（`registry.py`） | ✅ 支持多端点，实际配 1 个 | 加一条配置 |
| `LlmRouter` | ✅ 契约完整，单端点退化 | 多端点排序与熔断真正生效 |
| 熔断器 / 健康探测 | ⛔ 不做（单端点无意义） | 引入 |
| `provider` 列 | ⛔ 不加 | 迁移 + 回填 |
| 自托管端点配置 | ⛔ 不配 | 取消 `.env` 中注释 |
| 隐私提示（数据流向） | ✅ 显示"数据将发送至 DeepSeek API" | 增加"发送至自建服务器"选项 |

**净增量成本：约 0.3 人日**（主要是把契约写进代码结构，而非额外功能）。
自托管真正落地时，预估 2 人日（多端点路由 + 熔断 + 迁移 + 观测）。

---

## 八、未决事项

| # | 事项 | 何时决定 |
|---|---|---|
| Q1 | 自托管端点是否声明 `VISION`（即是否用它做 OCR） | B3 评测基线跑完后，用真实处方实测再定 |
| Q2 | 自托管接入方式：SSH 隧道还是 TLS 反代 | 自托管落地前 |
| Q3 | 是否需要「按任务强制指定端点」的调试开关 | 端点数 > 1 时 |
| Q4 | 隐私提示的粒度（是否逐字段展示发送内容） | B5 设计时 |

---

## 附：相关文档

| 文档 | 内容 |
|---|---|
| [`project-plan.md`](./project-plan.md) | §4.2 DeepSeek 模型能力与路由 |
| [`phase-2-software-development.md`](./phase-2-software-development.md) | B5 AI 辅助模块设计 |
| [`technical-validation.md`](./technical-validation.md) | DeepSeek 视觉能力与缓存价差的实测依据 |
