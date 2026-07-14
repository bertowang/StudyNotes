# SGLang 编程学习指南（Linux + NVIDIA GPU + Python 3.10+）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：已经用过 vLLM 或 HuggingFace，写过 Agent / RAG / 多轮对话应用，希望在**复杂 LLM 程序（分支、工具调用、结构化输出、并行采样）**上追求**极致低延迟与高吞吐**的 AI 工程师、Agent 开发者。
> **目标**：3~5 周内，从"起 SGLang 服务"到"能写 SGLang 前端 DSL、能理解 RadixAttention、能对齐或超越 vLLM 性能"。
> **推荐环境**：NVIDIA A100 / H100 / L40S / RTX 4090（≥ 24GB）+ CUDA 12.1+ + SGLang ≥ 0.3。

---

## 目录

- [0. 写在最前：为什么要学 SGLang？](#0-写在最前为什么要学-sglang)
- [1. SGLang 是什么：一句话讲清 vs vLLM / vs LangChain](#1-sglang-是什么一句话讲清-vs-vllm--vs-langchain)
- [2. 环境搭建（pip / Docker）](#2-环境搭建pip--docker)
- [3. 编程模型：前端 DSL + 后端 Runtime 双层架构](#3-编程模型前端-dsl--后端-runtime-双层架构)
- [4. 第一个例子：起服务 + 用前端 DSL 写多轮对话](#4-第一个例子起服务--用前端-dsl-写多轮对话)
- [5. 核心黑科技：RadixAttention（前缀树 KV 缓存）](#5-核心黑科技radixattention前缀树-kv-缓存)
- [6. 结构化输出：JSON Schema / Regex / 常量约束](#6-结构化输出json-schema--regex--常量约束)
- [7. 并行控制：fork / gen / choices 一次写全](#7-并行控制fork--gen--choices-一次写全)
- [8. 量化 & 分布式：FP8 / AWQ / TP / DP](#8-量化--分布式fp8--awq--tp--dp)
- [9. 性能分析：怎么打到 SGLang 官方基准？](#9-性能分析怎么打到-sglang-官方基准)
- [10. 学习路线图（3~5 周）](#10-学习路线图35-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 SGLang？

**一句话**：SGLang 是 **LLM 推理领域的"新贵"**——2024 年由 UC Berkeley 团队开源（PagedAttention 论文原班人马之一 Lianmin Zheng），主打 **"前端 DSL 表达复杂控制流 + 后端 RadixAttention 做前缀共享"**。在 Agent / RAG / few-shot 类工作负载上**常常超越 vLLM 30~200%**。

### 0.1 一句话对比

| 需求 | vLLM | **SGLang** |
|:--|:--|:--|
| 简单 prompt 单轮 | ★★★★★ | ★★★★★（差不多） |
| **多轮对话（长 system + 短用户）** | ★★★★ | ★★★★★（**明显更快**） |
| **Agent 分支 / 并行采样** | 无原生支持 | ★★★★★（DSL 原生） |
| **JSON / 结构化输出** | 支持 | **首创 xgrammar 引擎，更快** |
| **DeepSeek V3 / R1 特化** | 支持 | **官方推荐后端** |
| 生态成熟度 | 老大哥 | 追赶中，社区活跃 |

### 0.2 SGLang 现在有多重要？

- **DeepSeek 官方推荐推理后端**（V3 / R1 都主推 SGLang）；
- **xAI、Together、Hyperbolic 等**云厂商大量使用；
- **RadixAttention** 是继 PagedAttention 之后 KV Cache 领域最大的创新；
- **前端 DSL** 让 Agent / few-shot / self-consistency 之类的复杂程序**声明式一次写完**。

**一句话**：**如果你的负载有大量共享前缀（system prompt / few-shot / 多轮对话），SGLang 很可能比 vLLM 更快**。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **S1 入门** | 能起 `python -m sglang.launch_server`，用 OpenAI SDK 调用 |
| **S2 熟练** | 能用 `sgl.function` + `fork` + `gen` 写多轮 / 分支程序 |
| **S3 高阶** | 会调 RadixAttention 参数、会用 xgrammar 结构化输出、能量化到 FP8 |
| **S4 专家** | 能读 `python/sglang/srt/managers/scheduler.py`、能写自定义模型 |

---

## 1. SGLang 是什么：一句话讲清 vs vLLM / vs LangChain

### 1.1 定义

> **SGLang = Structured Generation Language**：一门为 LLM 程序（不只是 prompt）设计的 Python DSL + 高性能推理 Runtime，重点解决"**复杂控制流下的 KV Cache 复用**"这个痛点。

三个关键点：

1. **前端 DSL**：`fork` / `gen` / `select` / `choices` 让并行/分支/结构化输出**一等公民**；
2. **RadixAttention**：不是 PagedAttention 的替代，而是**前缀树管理 KV**，把共享前缀的 KV 命中率拉到极致；
3. **xgrammar**：结构化输出的 SOTA 引擎（速度约为 outlines 的 5~10 倍）。

### 1.2 三者定位

```
                LangChain           vLLM              SGLang
              (纯编排, 前端)      (纯 Runtime)     (DSL + Runtime 双栖)
                    │                 │                 │
                    ▼                 ▼                 ▼
              把 LLM 调用像       让 LLM 跑得         让 LLM 程序既
              搭乐高一样拼         最快                 好写又快
```

### 1.3 核心架构一图流

```
用户 SGLang 程序（前端 DSL）
     │
     ▼
Interpreter → 拆成一堆 gen/fork/select 原语
     │
     ▼
HTTP → SGLang Server (Runtime)
              │
              ├─ Scheduler + Router
              ├─ RadixAttention (前缀树)
              ├─ Continuous Batching
              ├─ Constrained Decoding (xgrammar)
              └─ CUDA/Triton Kernel
```

---

## 2. 环境搭建（pip / Docker）

### 2.1 pip

```bash
pip install "sglang[all]"
```

### 2.2 Docker

```bash
docker pull lmsysorg/sglang:latest
docker run --gpus all -p 30000:30000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  lmsysorg/sglang:latest \
  python3 -m sglang.launch_server \
    --model-path meta-llama/Meta-Llama-3-8B-Instruct \
    --port 30000
```

### 2.3 验证

```python
import sglang
print(sglang.__version__)   # 0.3.x
```

---

## 3. 编程模型：前端 DSL + 后端 Runtime 双层架构

### 3.1 三种玩法

| 模式 | 适用 | 代码 |
|:--|:--|:--|
| **OpenAI API** | 兼容旧代码 | `openai.chat.completions.create(...)` |
| **SGLang 前端 DSL** | 复杂 Agent / 并行 / 结构化 | `@sgl.function` + `fork/gen/select` |
| **Native API** | 极简 | `sgl.gen("prompt")` |

### 3.2 后端 Runtime 关键组件

- **RadixAttention**：管理共享前缀的 KV Cache；
- **Scheduler**：请求调度（继承 vLLM 思想）；
- **xgrammar**：结构化输出的正则/CFG 引擎；
- **DP Attention / MLA**：DeepSeek 大模型专属优化。

---

## 4. 第一个例子：起服务 + 用前端 DSL 写多轮对话

### 4.1 起服务

```bash
python -m sglang.launch_server \
  --model-path meta-llama/Meta-Llama-3-8B-Instruct \
  --port 30000
```

### 4.2 用 OpenAI SDK（兼容）

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:30000/v1", api_key="EMPTY")

resp = client.chat.completions.create(
    model="default",
    messages=[{"role": "user", "content": "写一首关于秋天的五言绝句"}],
)
print(resp.choices[0].message.content)
```

### 4.3 用 SGLang 前端 DSL（真正的杀器）

```python
import sglang as sgl

sgl.set_default_backend(sgl.RuntimeEndpoint("http://localhost:30000"))

@sgl.function
def multi_turn_agent(s, question):
    s += sgl.system("You are a helpful math tutor.")
    s += sgl.user(question)
    s += sgl.assistant(sgl.gen("thought", max_tokens=200))
    s += sgl.user("Now show the answer only in JSON: {\"answer\": ...}")
    s += sgl.assistant(sgl.gen(
        "answer",
        max_tokens=50,
        regex=r"\{\"answer\": [0-9\.]+\}"
    ))

state = multi_turn_agent.run(question="What is 12 * 13?")
print("thought:", state["thought"])
print("answer:", state["answer"])
```

**这段代码里 SGLang 做了 3 件普通 API 做不到的事**：
1. `system` + 前几轮的 KV 会被 **RadixAttention 缓存**，后续 turn 免算；
2. `regex="..."` 保证 JSON 100% 合法（走 xgrammar）；
3. 多个字段 `thought` / `answer` 自动分槽，一次调用拿全部结果。

---

## 5. 核心黑科技：RadixAttention（前缀树 KV 缓存）

### 5.1 问题

多轮对话 / few-shot / Agent 场景中：

```
Request 1: [system][few-shot 1][few-shot 2][Q1]
Request 2: [system][few-shot 1][few-shot 2][Q2]
Request 3: [system][few-shot 1][few-shot 2][Q3]
```

前面几千 tokens 一模一样，vLLM 的 Prefix Cache 能命中一部分，但**动态多变的前缀就失效了**。

### 5.2 RadixAttention 的方案

把所有历史 KV 组织成一棵**前缀树（Radix Tree）**：

```
             (root)
                │
        ┌───────┴───────┐
    [system]      [system_short]
        │
    [few-shot1]
        │
    [few-shot2]
       ├── [Q1: KV]
       ├── [Q2: KV]
       └── [Q3: KV]
```

- 新请求 → **走前缀树最长匹配**，命中的 KV 直接 reuse；
- **LRU 淘汰**：显存紧张时按最久未用的分支释放；
- **零拷贝**：命中的 KV **物理上不需要复制**。

### 5.3 收益

- 多轮对话 / Agent 场景，**吞吐比 vLLM 高 30~200%**；
- Prefix Cache 的**"泛化版"**（vLLM 的 Prefix Cache 只能命中静态前缀，SGLang 能命中任意分支）。

---

## 6. 结构化输出：JSON Schema / Regex / 常量约束

### 6.1 三种约束方式

```python
# 1. 正则
sgl.gen("date", regex=r"\d{4}-\d{2}-\d{2}")

# 2. JSON Schema
sgl.gen("data", json_schema={
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age":  {"type": "integer"}
    }
})

# 3. 从常量集合选一个（分类）
sgl.select("mood", choices=["happy", "sad", "neutral"])
```

### 6.2 为什么比 outlines 快

底层用 **xgrammar**（SGLang 团队自研），把 CFG/JSON Schema 预编译成状态机 + mask 缓存，**每步只做 O(1) mask 查询**。

**性能**：结构化输出的开销通常 < 5%，而 outlines 常常 30~50%。

---

## 7. 并行控制：fork / gen / choices 一次写全

### 7.1 fork：并行采样 / self-consistency

```python
@sgl.function
def multi_answer(s, question, n=5):
    s += sgl.user(question)
    forks = s.fork(n)                     # 复制 n 个分支
    for i, f in enumerate(forks):
        f += sgl.assistant(sgl.gen(f"answer_{i}", max_tokens=200))
    forks.join()

    # 多数投票 / 打分选优
    answers = [f["answer_{i}"] for i, f in enumerate(forks)]
```

**关键**：`fork` 后的 n 个分支**共享同一份系统前缀 KV**（RadixAttention 保证），只多算了后半段。

### 7.2 tree-of-thought / chain-of-thought

同样用 `fork` + `select` 组合，能自然表达思维树。

---

## 8. 量化 & 分布式：FP8 / AWQ / TP / DP

### 8.1 FP8（H100 首选）

```bash
python -m sglang.launch_server \
  --model-path meta-llama/Meta-Llama-3-70B-Instruct \
  --quantization fp8 \
  --tp-size 4
```

### 8.2 AWQ

```bash
python -m sglang.launch_server \
  --model-path TheBloke/Llama-2-70B-AWQ \
  --quantization awq
```

### 8.3 DeepSeek V3 / R1（MLA + DP Attention）

```bash
python -m sglang.launch_server \
  --model-path deepseek-ai/DeepSeek-V3 \
  --tp-size 8 --enable-dp-attention
```

**注意**：SGLang 对 DeepSeek 的支持是官方合作，MLA 的实现基本是当前最优。

---

## 9. 性能分析：怎么打到 SGLang 官方基准？

### 9.1 官方 benchmark

```bash
python -m sglang.bench_serving \
  --backend sglang \
  --dataset-name sharegpt --num-prompts 500 \
  --model-path meta-llama/Meta-Llama-3-8B-Instruct
```

### 9.2 调参优先级

1. `--mem-fraction-static`（默认 0.9，与 vLLM `gpu-memory-utilization` 类似）；
2. `--max-running-requests`（并发上限）；
3. `--chunked-prefill-size`（长 context 时降到 4096）；
4. `--enable-torch-compile`（PyTorch 2.4+ 有明显收益）；
5. `--disable-radix-cache`（**只在纯长文本无共享前缀时才关**，否则一定开）。

### 9.3 什么时候 SGLang 比 vLLM 快？

- Agent / RAG / few-shot（**共享前缀多**）→ 快 30~200%；
- 多轮对话（长 system prompt）→ 快 20~80%；
- 结构化输出场景 → 快 10~30%；
- 纯长文本单轮 → 与 vLLM 持平或略优。

---

## 10. 学习路线图（3~5 周）

| 周 | 目标 | 产出 |
|:--|:--|:--|
| Week 1 | 起服务 + OpenAI SDK 打通 | Llama-3-8B / DeepSeek 跑起来 |
| Week 2 | SGLang DSL 上手（`@sgl.function` / `fork` / `gen`）| 一个多轮 Agent |
| Week 3 | RadixAttention 调优 + xgrammar 结构化输出 | 一份对齐 vLLM 的压测 |
| Week 4 | FP8 / AWQ / DeepSeek MLA + 多卡 TP | 70B / DeepSeek 跑起来 |
| Week 5 | 读 `sglang/srt/managers/scheduler.py` + `radix_cache.py` | 能改核心 |

---

## 11. 精选资源与踩坑清单

### 11.1 官方资源
- **GitHub**：<https://github.com/sgl-project/sglang>
- **文档**：<https://docs.sglang.ai/>
- **RadixAttention 论文**：<https://arxiv.org/abs/2312.07104>
- **xgrammar**：<https://github.com/mlc-ai/xgrammar>
- **Discord / Slack**：<https://github.com/sgl-project/sglang#getting-started>

### 11.2 姊妹篇
- [vLLM 编程学习指南](./vLLM编程学习指南.md)
- [TensorRT-LLM 编程学习指南](./TensorRT-LLM编程学习指南.md)
- [llama.cpp 编程学习指南](./llama.cpp编程学习指南.md)
- [Triton 编程学习指南](./Triton编程学习指南.md)
- [GPU 编程工具全景](./GPU编程工具全景.md)

### 11.3 十大踩坑
1. **不写 SGLang DSL 就体验不到 RadixAttention 的全部收益**（OpenAI API 也能享受一部分，但控制不精细）；
2. `regex` / `json_schema` 太复杂会拖慢，先用简单形式测试；
3. `--mem-fraction-static` 太高显存拉爆，多轮对话建议 0.85；
4. **DeepSeek V3 需要 `--enable-dp-attention` + 多卡 TP**，单卡跑不了；
5. `fork` 分支越多，前缀共享收益越大，但显存也涨；
6. FP8 需要 Hopper（H100）；Ada（4090）支持有限；
7. `--enable-torch-compile` 需要 PyTorch 2.4+，太老会退化；
8. RadixAttention 缓存有 LRU 淘汰，冷门前缀命中率低；
9. **SGLang 加载慢**（首次要编 CUDA graph）；
10. 前端 DSL 和 OpenAI API 混用时注意 backend 一致性。

---

**版权声明**：本文由汪亮（bertonwang）撰写，转载请注明出处。欢迎邮件（<47608843@qq.com>）交流勘误。

**一句话总结**：**SGLang = 前端 DSL + RadixAttention 双杀器**——当你的负载**有共享前缀**（Agent / RAG / 多轮 / few-shot / 结构化输出）时，它常常比 vLLM 明显更快，也是 DeepSeek 的官方推荐后端。
