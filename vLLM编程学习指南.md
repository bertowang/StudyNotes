# vLLM 编程学习指南（Linux + NVIDIA/AMD GPU + Python 3.10+）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：会用 PyTorch/HuggingFace，能跑 `AutoModelForCausalLM.generate()`，想**几行代码就把 LLM 变成高吞吐 OpenAI 兼容 API 服务**的 AI 工程师、后端工程师、创业者。
> **目标**：3~5 周内，从"pip install vllm 起服务"到"能改调度器、能写自定义模型、能跑多机张量并行、能对齐 TensorRT-LLM 80%~90% 性能"。
> **推荐环境**：NVIDIA A100 / H100 / L40S / RTX 4090 / RTX 3090（≥ 24GB 显存）+ CUDA 12.1+ + vLLM ≥ 0.6。

---

## 目录

- [0. 写在最前：为什么要学 vLLM？](#0-写在最前为什么要学-vllm)
- [1. vLLM 是什么：一句话讲清 vs TensorRT-LLM / vs HF](#1-vllm-是什么一句话讲清-vs-tensorrt-llm--vs-hf)
- [2. 环境搭建（pip / uv / Docker 三选一）](#2-环境搭建pip--uv--docker-三选一)
- [3. 编程模型：Offline / Online / API 三种玩法](#3-编程模型offline--online--api-三种玩法)
- [4. 第一个例子：一行起 OpenAI 兼容服务](#4-第一个例子一行起-openai-兼容服务)
- [5. 核心黑科技：PagedAttention + Continuous Batching](#5-核心黑科技pagedattention--continuous-batching)
- [6. 量化：AWQ / GPTQ / FP8 / INT8 一网打尽](#6-量化awq--gptq--fp8--int8-一网打尽)
- [7. 分布式：TP / PP / EP 与多机部署](#7-分布式tp--pp--ep-与多机部署)
- [8. 进阶：Speculative / LoRA / Prefix Cache / 结构化输出](#8-进阶speculative--lora--prefix-cache--结构化输出)
- [9. 性能分析：怎么把吞吐拉到极限？](#9-性能分析怎么把吞吐拉到极限)
- [10. 学习路线图（3~5 周）](#10-学习路线图35-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 vLLM？

一句话：**vLLM 是开源 LLM 推理的事实标准**，2023 年问世后迅速成为绝大多数创业公司、云厂商推理服务的默认后端。它把 PagedAttention 论文的思想变成了工业级实现，几乎重新定义了"LLM 推理"这件事。

### 0.1 一句话对比

| 需求 | HuggingFace `.generate()` | **vLLM** | TensorRT-LLM |
|:--|:--|:--|:--|
| 起服务代码量 | 30~50 行 FastAPI | **1 行 CLI** | 3 步编译 + 起 Triton |
| 吞吐（Llama-3-8B, H100） | ~30 tok/s | ~220 tok/s | ~300 tok/s |
| 加载速度 | ~30s | ~30s | 秒开（已编 engine）|
| 支持新模型 | 出模型当天 | 出后 1~3 天 | 官方支持后（数周）|
| 部署难度 | 简单 | **极简** | 复杂 |
| 开源可控 | ✅ | ✅ | 部分闭源 |

### 0.2 vLLM 有多重要？

- **GitHub 30k+ star**（截至 2026），LLM 推理项目里独一档；
- **OpenAI 兼容 API**：客户端零改动切走 OpenAI；
- **广泛集成**：LangChain、LlamaIndex、Ray Serve、OpenLLM、BentoML 都以 vLLM 为默认后端；
- **PagedAttention 论文**（SOSP'23）—— 已被 TensorRT-LLM、SGLang、TGI 全部借鉴。

**一句话**：**如果你只学一个开源推理框架，就是 vLLM**。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **V1 入门** | 能用 `vllm serve` 起服务、能调 `LLM(...)` offline batch |
| **V2 熟练** | 会调 `--tensor-parallel-size` / `--max-num-seqs` / `--gpu-memory-utilization` |
| **V3 高阶** | 会用 AWQ/FP8 量化、Speculative、LoRA、Prefix Cache，能压测调参 |
| **V4 专家** | 能读 `vllm/attention` `vllm/engine` `vllm/worker` 源码、能提 PR、能写自定义模型 |

---

## 1. vLLM 是什么：一句话讲清 vs TensorRT-LLM / vs HF

### 1.1 定义

> **vLLM 是一个基于 PagedAttention 的高吞吐 LLM 推理和服务引擎**：Python 主导、CUDA 内核在关键路径手写，聚焦"OpenAI 兼容 + 极简部署 + 高吞吐"。

三个关键点：

1. **PagedAttention**：把 KV Cache 分块管理（类似 OS 分页），显存利用率飙升；
2. **Continuous Batching**：请求随到随入，GPU 永远不空闲；
3. **OpenAI 兼容 API**：一行起服务，客户端 100% 复用 OpenAI SDK。

### 1.2 三者对比

```
                     HF Transformers          vLLM                TensorRT-LLM
  ┌───────────────┬────────────────────┬────────────────────┬───────────────────┐
  定位            │ 训练 & 研究首选     │ 推理开源事实标准    │ NV GPU 性能王者    │
  编译方式        │ 无（PyTorch eager）│ 部分 JIT（Triton） │ AOT（TRT engine）│
  API 兼容        │ 无                │ OpenAI API         │ 需自建             │
  跨硬件          │ 全                │ NV + AMD + TPU     │ 只 NVIDIA         │
  上手时间        │ 半天              │ 半小时             │ 1~2 天           │
  生产吞吐        │ ★                │ ★★★★            │ ★★★★★         │
```

### 1.3 核心概念一图流

```
Client (OpenAI SDK / curl)
       │
       ▼
 ┌─────────────────────────────┐
 │  vLLM Async Engine          │  ←── FastAPI + async
 │  ┌─────────────────────┐   │
 │  │ Scheduler           │   │  ←── Continuous Batching
 │  │  ├─ waiting queue   │   │
 │  │  ├─ running queue   │   │
 │  │  └─ swap queue      │   │
 │  └──────────┬──────────┘   │
 │             ▼               │
 │  ┌─────────────────────┐   │
 │  │ Model Executor       │   │  ←── 每张卡一个 Worker
 │  │  ├─ Worker 0 (GPU 0)│   │
 │  │  └─ Worker 1 (GPU 1)│   │
 │  └──────────┬──────────┘   │
 │             ▼               │
 │  ┌─────────────────────┐   │
 │  │ PagedAttention Kernel│  │  ←── CUDA/Triton 手写
 │  └─────────────────────┘   │
 └─────────────────────────────┘
```

---

## 2. 环境搭建（pip / uv / Docker 三选一）

### 2.1 pip（最简单）

```bash
pip install vllm
```

**注意**：默认装的是 CUDA 12.1 版；CUDA 11.8 需要 `pip install vllm[cu118]`。

### 2.2 uv（推荐，快且稳）

```bash
uv pip install vllm
```

### 2.3 Docker（推荐生产）

```bash
docker pull vllm/vllm-openai:latest
docker run --gpus all -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model meta-llama/Meta-Llama-3-8B-Instruct
```

### 2.4 验证

```python
import vllm
print(vllm.__version__)  # 0.6.x
```

---

## 3. 编程模型：Offline / Online / API 三种玩法

| 模式 | 代码 | 适用 |
|:--|:--|:--|
| **Offline batch** | `LLM(...).generate([...])` | 批量离线推理、评测、数据生成 |
| **Online async** | `AsyncLLMEngine` | 自建服务、复杂调度 |
| **OpenAI API** | `vllm serve ...` | **90% 生产场景直接用它** |

---

## 4. 第一个例子：一行起 OpenAI 兼容服务

### 4.1 起服务

```bash
vllm serve meta-llama/Meta-Llama-3-8B-Instruct \
  --dtype auto \
  --tensor-parallel-size 1 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.9 \
  --port 8000
```

### 4.2 用 OpenAI SDK 调用

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

resp = client.chat.completions.create(
    model="meta-llama/Meta-Llama-3-8B-Instruct",
    messages=[{"role": "user", "content": "写一首关于秋天的五言绝句"}],
    max_tokens=100,
)
print(resp.choices[0].message.content)
```

### 4.3 Offline batch 模式（评测友好）

```python
from vllm import LLM, SamplingParams

llm = LLM(model="meta-llama/Meta-Llama-3-8B-Instruct")
prompts = ["Hello!", "What is AI?", "Explain FlashAttention."]
outputs = llm.generate(prompts, SamplingParams(temperature=0.8, max_tokens=100))

for o in outputs:
    print(o.prompt, "->", o.outputs[0].text)
```

**关键点**：`LLM(...)` 内部**自动开启 PagedAttention + Continuous Batching**，你只管扔 prompts，vLLM 帮你把 GPU 榨干。

---

## 5. 核心黑科技：PagedAttention + Continuous Batching

### 5.1 PagedAttention（vLLM 的灵魂）

**问题**：不同请求的序列长度不一，传统 KV Cache 要按最大长度预分配，浪费高达 60~80% 显存。

**方案**：
- 把 KV Cache 切成固定大小的 **block**（默认 16 tokens）；
- 用一张 **block table** 把逻辑连续的序列映射到物理散布的 block；
- 完全类比 OS 的**虚拟内存 + 页表**。

**收益**：
- 显存利用率 40% → **90%+**；
- 一张 H100 从并发 50 到 **并发 200**；
- **零拷贝共享**：Prefix Cache / Beam Search 直接复用 block。

### 5.2 Continuous Batching（俗称 IFB）

**传统 static batching**（HF `.generate()`）：
```
Batch = [A, B, C, D]
A 30 tokens 就结束了，B/C/D 还有 200 tokens
→ A 的槽位空转 170 步 ❌
```

**Continuous Batching**（vLLM）：
```
A 结束 → 立即从等待队列取 E 塞进来
→ GPU 从不空闲 ✅
```

**收益**：吞吐相比 static batching **2~5x**。

### 5.3 一张图对比

```
        static batching:            continuous batching:
        ┌───────────┐               ┌───────────┐
step 0  │ A B C D   │               │ A B C D   │
step 1  │ A B C D   │               │ A B C D   │
step 2  │ A B C D   │               │ A B C D   │
step 3  │ _ B C D   │  ← A 结束      │ E B C D   │  ← E 立即上位
step 4  │ _ B C D   │               │ E B C D   │
step 5  │ _ _ C D   │  ← B 结束      │ E F C D   │  ← F 立即上位
        └───────────┘               └───────────┘
```

---

## 6. 量化：AWQ / GPTQ / FP8 / INT8 一网打尽

### 6.1 支持矩阵

| 量化 | 命令 | GPU 要求 | 加速比 |
|:--|:--|:--|:--|
| FP16 | 默认 | 全部 | 1x |
| **AWQ (W4A16)** | `--quantization awq` | ≥ SM70 | ~1.5x（长上下文更好）|
| **GPTQ (W4A16)** | `--quantization gptq` | ≥ SM70 | ~1.5x |
| **FP8** | `--quantization fp8` | Ada / Hopper | ~1.8x |
| INT8 (W8A8) | `--quantization compressed-tensors` | ≥ SM75 | ~1.5x |

### 6.2 用 AWQ 起服务

```bash
vllm serve TheBloke/Llama-2-13B-chat-AWQ \
  --quantization awq --dtype half
```

### 6.3 FP8 KV Cache（H100 独享）

```bash
vllm serve meta-llama/Meta-Llama-3-8B \
  --kv-cache-dtype fp8_e5m2 --dtype half
```

**收益**：KV Cache 显存减半，同一张卡并发翻倍。

---

## 7. 分布式：TP / PP / EP 与多机部署

### 7.1 单机多卡（Tensor Parallel）

```bash
vllm serve meta-llama/Meta-Llama-3-70B-Instruct \
  --tensor-parallel-size 4
```

### 7.2 多机多卡（Ray 集群）

```bash
# Head node
ray start --head --port=6379
# Worker node
ray start --address=<HEAD_IP>:6379
# vLLM
vllm serve meta-llama/Meta-Llama-3-405B \
  --tensor-parallel-size 8 \
  --pipeline-parallel-size 2
```

### 7.3 Expert Parallel（MoE）

Mixtral / DeepSeek-MoE 类模型：`--enable-expert-parallel`。

---

## 8. 进阶：Speculative / LoRA / Prefix Cache / 结构化输出

### 8.1 Speculative Decoding

```bash
vllm serve meta-llama/Meta-Llama-3-70B-Instruct \
  --speculative-model meta-llama/Meta-Llama-3-8B-Instruct \
  --num-speculative-tokens 5
```

### 8.2 LoRA 热切换

```bash
vllm serve meta-llama/Meta-Llama-3-8B \
  --enable-lora --lora-modules sql-lora=/path/to/lora
```

调用时 `model="sql-lora"` 即可切换。

### 8.3 Prefix Cache（长 system prompt 神器）

```bash
vllm serve ... --enable-prefix-caching
```

同一个 system prompt 只需算一次 KV，后续请求命中直接跳过。

### 8.4 结构化输出（JSON / Regex）

```python
resp = client.chat.completions.create(
    model="...",
    messages=[...],
    extra_body={"guided_json": {"type": "object", "properties": {...}}}
)
```

底层用 outlines / lm-format-enforcer，**保证 100% 合法 JSON**。

---

## 9. 性能分析：怎么把吞吐拉到极限？

### 9.1 官方 benchmark

```bash
python benchmarks/benchmark_serving.py \
  --backend vllm --model meta-llama/Meta-Llama-3-8B \
  --dataset-name sharegpt --num-prompts 1000
```

### 9.2 调参优先级

1. `--gpu-memory-utilization`（默认 0.9，可以往 0.95 推）；
2. `--max-num-seqs`（默认 256，长上下文降到 64）；
3. `--max-model-len`（越小并发越高）；
4. `--enable-prefix-caching`（system prompt 长的话开启）；
5. 量化（AWQ / FP8）。

### 9.3 关键指标

| 指标 | 目标 |
|:--|:--|
| TTFT (P50/P99) | 越低越好 |
| TPOT | 稳定在 30~50ms |
| Throughput (tok/s) | 越高越好 |
| GPU Util | 应 > 85% |

---

## 10. 学习路线图（3~5 周）

| 周 | 目标 | 产出 |
|:--|:--|:--|
| Week 1 | 起服务 + OpenAI SDK 打通 | Llama-3-8B 在自机跑起来 |
| Week 2 | Offline batch + AWQ + Prefix Cache | 吞吐 200+ tok/s |
| Week 3 | 多卡 TP + LoRA + Speculative | 70B 模型跑起来 |
| Week 4 | 压测调参 + 观测 Nsight/Prometheus | 一份性能报告 |
| Week 5 | 读 `vllm/core/scheduler.py` + `vllm/attention/` 源码 | 能改调度器 |

---

## 11. 精选资源与踩坑清单

### 11.1 官方资源
- **GitHub**：<https://github.com/vllm-project/vllm>
- **文档**：<https://docs.vllm.ai/>
- **PagedAttention 论文**：<https://arxiv.org/abs/2309.06180>
- **Blog**：<https://blog.vllm.ai/>
- **Discord**：<https://discord.gg/jz7wjKhh6g>

### 11.2 姊妹篇
- [TensorRT-LLM 编程学习指南](./TensorRT-LLM编程学习指南.md)
- [SGLang 编程学习指南](./SGLang编程学习指南.md)
- [llama.cpp 编程学习指南](./llama.cpp编程学习指南.md)
- [Triton 编程学习指南](./Triton编程学习指南.md)
- [GPU 编程工具全景](./GPU编程工具全景.md)

### 11.3 十大踩坑
1. **`gpu-memory-utilization` 太高**会 OOM，太低浪费显存，一般 0.9；
2. **`max-model-len` 定死之后运行时超限直接报错**，要预留 buffer；
3. **AWQ / GPTQ 权重需要单独下载**，不是所有 HF 模型都有；
4. **多卡 TP 时 world_size 必须能被注意力头数整除**；
5. **首 token 慢**：Prefix Cache 冷启动 + 图捕获，第二次请求会快很多；
6. **Prefix Cache 只对相同前缀有效**，动态 few-shot 不生效；
7. **Speculative 的 draft 与 target 必须同 tokenizer**；
8. **CUDA graph 与 eager 切换**：`--enforce-eager` 关掉 CUDA graph 便于 debug；
9. **`vllm serve` 默认无鉴权**，生产要挂网关或加 `--api-key`；
10. **升级 vLLM 版本时** 老 checkpoint / KV Cache dtype 可能不兼容，看 CHANGELOG。

---

**版权声明**：本文由汪亮（bertonwang）撰写，转载请注明出处。欢迎邮件（<47608843@qq.com>）交流勘误。

**一句话总结**：**vLLM = 开源 LLM 推理事实标准**，一行 `vllm serve` 起 OpenAI 兼容服务，PagedAttention + Continuous Batching 双杀器，是所有想快速上线 LLM 服务的第一站。
