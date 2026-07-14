# TensorRT-LLM 编程学习指南（Linux + Ada/Ampere/Hopper + CUDA 12.x）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：会用 PyTorch/HuggingFace，跑过 `AutoModelForCausalLM.generate()`，想把手头的 LLM 部署到**生产环境、追求极致延迟与吞吐**的 AI 工程师、推理架构师、平台开发者。
> **目标**：4~6 周内，从"第一次编译 Llama-3 引擎"到"能改插件、能量化到 FP8、能上 In-flight Batching、能读源码定位性能瓶颈"。
> **推荐环境**：NVIDIA H100 / A100 / L40S / RTX 4090（Compute Capability ≥ 8.0）+ CUDA 12.4+ + Docker + TensorRT-LLM 0.14+。

---

## 目录

- [0. 写在最前：为什么要学 TensorRT-LLM？](#0-写在最前为什么要学-tensorrt-llm)
- [1. TensorRT-LLM 是什么：一句话讲清 vs vLLM / vs TensorRT](#1-tensorrt-llm-是什么一句话讲清-vs-vllm--vs-tensorrt)
- [2. 环境搭建（Docker 强烈推荐）](#2-环境搭建docker-强烈推荐)
- [3. 编程模型：从 HF 模型到 Engine 的三步走](#3-编程模型从-hf-模型到-engine-的三步走)
- [4. 第一个例子：部署 Llama-3-8B（对照 vLLM 版）](#4-第一个例子部署-llama-3-8b对照-vllm-版)
- [5. 四大杀器：Paged KV / In-flight Batching / FP8 / Speculative](#5-四大杀器paged-kv--in-flight-batching--fp8--speculative)
- [6. 量化实战：FP8 / INT8 SmoothQuant / AWQ / GPTQ](#6-量化实战fp8--int8-smoothquant--awq--gptq)
- [7. Triton Inference Server + TensorRT-LLM 上线](#7-triton-inference-server--tensorrt-llm-上线)
- [8. 性能分析：怎么知道跑得多快？](#8-性能分析怎么知道跑得多快)
- [9. 进阶：写一个自定义 Plugin（PTQ + FlashAttention 变体）](#9-进阶写一个自定义-plugin)
- [10. 学习路线图（4~6 周）](#10-学习路线图46-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 TensorRT-LLM？

一句话：**在 NVIDIA GPU 上部署 LLM，TensorRT-LLM 就是"性能天花板"**。它不是学术玩具，而是 NVIDIA 官方投入最重的推理框架，Meta、Microsoft、Databricks 生产 LLM 服务几乎都基于它或它的思想。

### 0.1 一句话对比

| 需求 | HuggingFace 原生 | vLLM | **TensorRT-LLM** |
|:--|:--|:--|:--|
| Llama-3-8B 单卡吞吐 (H100) | ~30 tok/s | ~150 tok/s | **~300+ tok/s** |
| FP8 支持 | ❌ | 部分 | **✅ 原生 Hopper FP8** |
| Speculative Decoding | 手写 | ✅ | **✅ + Medusa/EAGLE** |
| 多卡张量并行 | 复杂 | ✅ | **✅ + Pipeline 并行** |
| 部署形态 | Python 服务 | Python 服务 | **Engine + Triton Server** |

### 0.2 TensorRT-LLM 现在有多重要？

- **NVIDIA 官方主推**：`NIM`（NVIDIA Inference Microservices）背后就是它；
- **底层用 CUTLASS 3.x + FlashAttention v2/v3 + FP8 tensor core**——你享受 NVIDIA 全部软硬件加速红利；
- **In-flight Batching (IFB)** 是它率先大规模落地的关键优化，vLLM 的 Continuous Batching 是同一思想；
- **超长上下文 / MoE / 多模态**：Nemotron、Mixtral 8x22B、LLaVA 都有官方支持。

**一句话**：**如果目标是"在 NVIDIA GPU 上给用户最低延迟、最高吞吐"，TensorRT-LLM 就是首选**；如果目标是"快速迭代、跨硬件、开源可控"，那才轮到 vLLM / SGLang。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **T1 入门** | 能用官方脚本编 Llama-3 引擎、能跑 `run.py` 单 batch 推理 |
| **T2 熟练** | 会用 `trtllm-build` + Python API，能开 Paged KV / IFB / FP16 |
| **T3 高阶** | 会做 FP8 / SmoothQuant 量化、能配 TP+PP、能挂 Triton Server 上线 |
| **T4 专家** | 能写 Plugin、能读 `cpp/tensorrt_llm` 源码、能针对特定模型手调 GEMM tactic |

---

## 1. TensorRT-LLM 是什么：一句话讲清 vs vLLM / vs TensorRT

### 1.1 定义

> **TensorRT-LLM 是 NVIDIA 基于 TensorRT 打造的 LLM 专用推理框架**：给你一个 HuggingFace 权重，它编出一个高度优化的 `engine` 文件，运行时用 C++ Runtime + IFB 调度器提供服务。

三个关键点：

1. **AOT 编译**（Ahead-of-Time）——不是 JIT，需要先花几分钟"编"出 engine，之后每次启动都秒开；
2. **LLM 专用**——内置 Attention、RoPE、GQA、Paged KV、Speculative 等 LLM 专属图与调度；
3. **闭源核心 + 开源前端**——C++ Runtime 部分闭源，但模型定义、Python API、大部分 Plugin 全开源。

### 1.2 三者对比

```
                   TensorRT              TensorRT-LLM          vLLM
  ┌─────────────────────────────┬────────────────────────┬──────────────────┐
定位│ 通用推理编译器（CV/NLP 都行） │ LLM 专用（衍生自 TRT）  │ 开源 LLM 推理引擎  │
编译│ AOT，engine 一次生成         │ AOT，engine + IFB       │ JIT，Python 加载  │
调度│ 静态 batch                  │ In-flight Batching     │ Continuous Batch │
生态│ CV/NLP 广                    │ 只做 LLM               │ LLM，社区最活跃    │
量化│ FP16/INT8                   │ FP16/FP8/INT8/AWQ/GPTQ  │ FP16/AWQ/GPTQ    │
```

### 1.3 核心概念一图流

```
HF 权重 ─┐
         ├─► [Convert] ──► TRT-LLM 模型定义 (Python API)
Config ──┘                            │
                                       ▼
                             [trtllm-build]
                                       │
                                       ▼
                              engine.plan  ◄── 可分享 / 版本化
                                       │
                     ┌─────────────────┴──────────────────┐
                     ▼                                    ▼
               Python Runtime                   C++ Runtime + IFB
                (跑离线测试)                     (生产 / Triton Server)
```

---

## 2. 环境搭建（Docker 强烈推荐）

### 2.1 官方推荐姿势：直接拉镜像

```bash
docker pull nvcr.io/nvidia/tensorrt-llm/release:0.14.0
docker run --gpus all -it --rm \
  -v $(pwd):/workspace \
  nvcr.io/nvidia/tensorrt-llm/release:0.14.0 bash
```

**为什么必须 Docker**：TRT-LLM 依赖 TensorRT 特定版本 + `mpi4py` + `polygraphy` + NCCL + FlashAttention 编译好的二进制，本地编译至少 40 分钟且极易失败。

### 2.2 硬件要求

| GPU | 支持特性 |
|:--|:--|
| **H100 / H200** | 全功能（FP8、TMA、fused MoE） |
| A100 / A800 | FP16 / INT8 / SmoothQuant（无 FP8） |
| L40S / RTX 4090 | 单卡推理，FP8 支持 |
| RTX 3060 / T4 | **仅支持 FP16**，不推荐生产 |

### 2.3 验证安装

```python
import tensorrt_llm
print(tensorrt_llm.__version__)   # 0.14.0
```

---

## 3. 编程模型：从 HF 模型到 Engine 的三步走

### 3.1 三步走全景图

```
Step 1: Convert    HF 权重 → TRT-LLM checkpoint (含量化)
    │
    ▼
Step 2: Build      checkpoint → engine.plan (含 kernel 选优)
    │
    ▼
Step 3: Run        engine + tokenizer → 推理服务
```

### 3.2 三个 API 层级

| 层级 | API | 适用 |
|:--|:--|:--|
| **高阶** | `LLM` class (Python) | 快速 demo、Notebook |
| **中阶** | `trtllm-build` CLI | 生产脚本、CI |
| **低阶** | Python 模型 API + C++ Runtime | 自定义模型 / Plugin |

---

## 4. 第一个例子：部署 Llama-3-8B（对照 vLLM 版）

### 4.1 TensorRT-LLM 版（3 步）

```bash
# Step 1: 转 checkpoint（FP16）
python examples/llama/convert_checkpoint.py \
    --model_dir ./Meta-Llama-3-8B-Instruct \
    --output_dir ./tllm_ckpt/llama3-8b-fp16 \
    --dtype float16

# Step 2: 编 engine
trtllm-build \
    --checkpoint_dir ./tllm_ckpt/llama3-8b-fp16 \
    --output_dir ./engines/llama3-8b-fp16 \
    --gemm_plugin float16 \
    --max_input_len 4096 --max_output_len 1024 \
    --paged_kv_cache enable \
    --use_inflight_batching

# Step 3: 跑
python examples/run.py \
    --engine_dir ./engines/llama3-8b-fp16 \
    --tokenizer_dir ./Meta-Llama-3-8B-Instruct \
    --max_output_len 200 \
    --input_text "Explain FlashAttention in 3 sentences."
```

### 4.2 对照 vLLM 版（1 步）

```python
from vllm import LLM
llm = LLM("meta-llama/Meta-Llama-3-8B-Instruct")
print(llm.generate("Explain FlashAttention in 3 sentences.")[0].outputs[0].text)
```

**对比**：
- vLLM 一行、TRT-LLM 三步 —— **代价**换来 **1.5x~2x 吞吐 + 更低 P99 延迟**；
- vLLM 加载慢（每次都重新分析图），TRT-LLM engine 秒开；
- vLLM 加新模型分钟级，TRT-LLM 加新模型架构可能得写模型定义。

### 4.3 高阶 Python API（0.13+ 提供的 `LLM` class）

```python
from tensorrt_llm import LLM, SamplingParams

llm = LLM(model="meta-llama/Meta-Llama-3-8B-Instruct")
outputs = llm.generate(
    ["Hello, how are you?"],
    SamplingParams(temperature=0.8, max_tokens=100),
)
print(outputs[0].outputs[0].text)
```

**这一层 API 就是为了追平 vLLM 的开发体验**，内部自动做 Convert + Build + Cache。

---

## 5. 四大杀器：Paged KV / In-flight Batching / FP8 / Speculative

### 5.1 Paged KV Cache

- **问题**：LLM 每个 token 都要缓存 K/V（KV Cache），序列长度不一时显存碎片严重；
- **方案**：像 OS 虚拟内存那样，KV Cache 按 **块（block）** 分配（默认 128 tokens/block），逻辑连续、物理散布；
- **收益**：显存利用率从 ~40% 到 ~90%，同一张 H100 能装下 3~5 倍并发。

### 5.2 In-flight Batching (IFB)

- 也叫 Continuous Batching（vLLM 里的叫法）；
- **传统 static batching**：一批 32 个请求，最长那个不完成，其他都空转；
- **IFB**：任何一个请求结束就腾出槽位，立即把等待队列里的新请求塞进来，**GPU 利用率 90%+**。

### 5.3 FP8（Hopper 独享）

- H100 的 Tensor Core 原生支持 FP8（E4M3 / E5M2）；
- 相比 FP16 **吞吐翻倍、显存减半**，精度损失 < 1%（用 SmoothQuant 校准后）；
- 命令：`trtllm-build --gemm_plugin fp8 --use_fp8_context_fmha`。

### 5.4 Speculative Decoding

- **原理**：小模型（draft）快速生成 N 个候选 token，大模型（target）一次性并行验证；
- 常见方案：Medusa（多头预测）、EAGLE（隐状态预测）、Lookahead Decoding；
- 端到端加速通常 **2~3x**，几乎无精度损失。

---

## 6. 量化实战：FP8 / INT8 SmoothQuant / AWQ / GPTQ

| 量化 | 精度 | 速度 | 门槛 | 场景 |
|:--|:--|:--|:--|:--|
| FP16 | 100% | 1x | 无 | 基线 |
| **FP8** | ~99% | ~2x | Hopper | 生产首选（H100） |
| INT8 SmoothQuant | ~98% | ~1.7x | 需校准数据 | A100/L40S |
| **AWQ (W4A16)** | ~97% | ~2.5x（内存受限场景）| 需 AWQ 权重 | 消费级 GPU / 显存紧 |
| GPTQ (W4A16) | ~97% | ~2.5x | 需 GPTQ 权重 | 同上，社区多 |

**推荐路线**：
- H100 → **FP8**；
- A100 → **SmoothQuant INT8**；
- RTX 4090 / L40S → **AWQ**（同时兼顾速度和显存）。

---

## 7. Triton Inference Server + TensorRT-LLM 上线

生产部署几乎都是这个组合：

```
Client (HTTP/gRPC)
     │
     ▼
Triton Inference Server
     │
     ├── model.json (config)
     └── tensorrt_llm backend
              │
              ▼
        engine.plan (你编译出的)
```

好处：
- 多模型热切换、动态 batching、metrics 全套；
- 一个端口挂多个引擎（FP8 大模型 + INT8 小模型）；
- HTTP / gRPC / KServe 三种协议全支持。

---

## 8. 性能分析：怎么知道跑得多快？

### 8.1 官方 benchmark 脚本

```bash
python benchmarks/python/benchmark.py \
    -m llama_7b \
    --mode plugin \
    --batch_size "1;8;32" \
    --input_output_len "128,128;512,512"
```

### 8.2 关键指标

| 指标 | 含义 | 追求 |
|:--|:--|:--|
| **TTFT** | Time-to-First-Token | 越低越好（用户感知） |
| **TPOT** | Time-per-Output-Token | 越低越好（吞吐） |
| **Throughput** | tokens/s | 越高越好 |
| **QPS** | queries/s | 服务化关心 |
| **P99 Latency** | 99 分位延迟 | SLA 保底 |

### 8.3 Nsight Systems 抓 kernel

```bash
nsys profile -t cuda,nvtx --gpu-metrics-device=0 \
    python run.py --engine_dir ./engines/...
```

---

## 9. 进阶：写一个自定义 Plugin

Plugin 是 TRT/TRT-LLM 的插件式扩展机制，用来塞入 TRT 不支持或需要极致优化的算子。

### 9.1 Plugin 结构（简化）

```cpp
class MyFusedRMSNormPlugin : public IPluginV2DynamicExt {
    int enqueue(const PluginTensorDesc* inputDesc, ...) override {
        // 调用你的 CUDA / CUTLASS kernel
        launch_my_fused_rmsnorm(inputs, outputs, stream);
        return 0;
    }
    // ... (getSerializationSize / serialize / clone ...)
};
```

### 9.2 什么时候需要写 Plugin？

- 新算子（如 MoE 的 top-k routing 变体）；
- 想融合 4~5 个连续 op；
- 需要用 CUTLASS/FlashAttention 变体的地方。

---

## 10. 学习路线图（4~6 周）

| 周 | 目标 | 产出 |
|:--|:--|:--|
| Week 1 | 环境 + 编第一个 engine | 跑通 Llama-3-8B FP16 |
| Week 2 | Paged KV + IFB + 多 batch | 吞吐从 100 → 250 tok/s |
| Week 3 | FP8 或 SmoothQuant 量化 | 吞吐再 +50% |
| Week 4 | 挂 Triton Server + benchmark | 一个可上线的服务 |
| Week 5 | Speculative / MoE / 多卡 TP | 覆盖真实生产场景 |
| Week 6 | 读 `cpp/tensorrt_llm` 源码 + 尝试写 Plugin | 能改核心 |

---

## 11. 精选资源与踩坑清单

### 11.1 官方资源
- **GitHub**：<https://github.com/NVIDIA/TensorRT-LLM>
- **文档**：<https://nvidia.github.io/TensorRT-LLM/>
- **examples 目录**：<https://github.com/NVIDIA/TensorRT-LLM/tree/main/examples>
- **性能报告**：<https://github.com/NVIDIA/TensorRT-LLM/blob/main/docs/source/performance/perf-overview.md>
- **Triton Server backend**：<https://github.com/triton-inference-server/tensorrtllm_backend>

### 11.2 姊妹篇
- [vLLM 编程学习指南](./vLLM编程学习指南.md)
- [SGLang 编程学习指南](./SGLang编程学习指南.md)
- [llama.cpp 编程学习指南](./llama.cpp编程学习指南.md)
- [GPU 编程工具全景](./GPU编程工具全景.md)
- [CUTLASS 编程学习指南](./CUTLASS编程学习指南.md)

### 11.3 十大踩坑
1. **必须用官方 Docker**，本地编译几乎无法成功；
2. `max_input_len` + `max_output_len` 编译时定死，运行时超出会截断；
3. FP8 需要 Compute Capability ≥ 9.0（H100），Ada（4090）只有部分支持；
4. Paged KV 的 block size 影响很大，默认 128 一般够，长上下文可调到 64；
5. `--gemm_plugin` 一定要开，否则性能腰斩；
6. 多卡 TP 时 `--tp_size` 必须能被 num_heads 整除；
7. 量化校准数据要覆盖真实分布，否则精度掉点严重；
8. Speculative 的 draft 模型要和 target 同 tokenizer；
9. Triton Server 版本要和 TRT-LLM 版本严格匹配；
10. `engine.plan` **不跨 GPU 架构**，H100 编的不能拿到 A100 跑。

---

**版权声明**：本文由汪亮（bertonwang）撰写，转载请注明出处。欢迎邮件（<47608843@qq.com>）交流勘误。

**一句话总结**：**TensorRT-LLM = NVIDIA GPU 上 LLM 推理的性能天花板**，Convert→Build→Run 三步，杀器四件套（Paged KV / IFB / FP8 / Speculative），生产上线首选。
