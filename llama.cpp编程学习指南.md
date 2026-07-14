# llama.cpp 编程学习指南（Windows/Linux/macOS + CPU / GPU / Apple Silicon）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：想在**消费级硬件（笔记本 / 台式机 / 树莓派 / Mac Mini / 手机）**上跑 LLM 的开发者、独立作者、隐私敏感用户、边缘/离线部署工程师、教育/科研个人。
> **目标**：3~5 周内，从"下载 GGUF 权重跑第一次 chat"到"能编译带 CUDA/Vulkan/Metal 的自定义版本、能量化模型、能挂 HTTP 服务、能读 `ggml` 底层"。
> **推荐环境**：任何有 8GB+ 内存的机器都行。GPU 推荐 RTX 3060 / 4060 及以上；Mac 推荐 M1/M2/M3。

---

## 目录

- [0. 写在最前：为什么要学 llama.cpp？](#0-写在最前为什么要学-llamacpp)
- [1. llama.cpp 是什么：一句话讲清 vs vLLM / vs Ollama](#1-llamacpp-是什么一句话讲清-vs-vllm--vs-ollama)
- [2. 环境搭建（Windows / Linux / macOS）](#2-环境搭建windows--linux--macos)
- [3. 编程模型：GGUF + ggml + backends](#3-编程模型gguf--ggml--backends)
- [4. 第一个例子：在笔记本跑 Llama-3-8B](#4-第一个例子在笔记本跑-llama-3-8b)
- [5. 量化实战：从 F16 到 Q2_K，模型能压多小？](#5-量化实战从-f16-到-q2_k模型能压多小)
- [6. 起 OpenAI 兼容 HTTP 服务](#6-起-openai-兼容-http-服务)
- [7. 后端矩阵：CUDA / Metal / Vulkan / ROCm / OpenBLAS](#7-后端矩阵cuda--metal--vulkan--rocm--openblas)
- [8. 进阶：Speculative / Grammar / Multi-modal](#8-进阶speculative--grammar--multi-modal)
- [9. 性能分析：CPU / GPU 分别跑多快？](#9-性能分析cpu--gpu-分别跑多快)
- [10. 学习路线图（3~5 周）](#10-学习路线图35-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 llama.cpp？

**一句话**：llama.cpp 是 **"让 LLM 跑在任何硬件上"** 的开源奇迹——纯 C/C++ 写成、零 Python 依赖、支持 CPU / CUDA / Metal / Vulkan / ROCm / Intel oneAPI 全部后端，把 8B 模型压到 4GB 塞进树莓派，把 70B 塞进 Mac Studio。它是 Ollama、LM Studio、GPT4All、Jan、KoboldCpp 的**共同底座**。

### 0.1 一句话对比

| 需求 | vLLM / TRT-LLM | **llama.cpp** |
|:--|:--|:--|
| 部署硬件 | NVIDIA 数据中心卡 | **CPU / 消费级 GPU / Mac / 手机 / 树莓派** |
| 部署形态 | Python + Docker | **单个二进制文件** |
| 显存要求（8B） | 16 GB+ | **4~6 GB（Q4）** |
| 首 token 延迟 | 几十 ms | 100~500 ms |
| 吞吐 | ★★★★★ | ★★★ |
| **可移植性** | ★★ | ★★★★★ |
| **隐私 / 离线** | 难 | **完美支持** |

### 0.2 llama.cpp 现在有多重要？

- **GitHub 70k+ star**（截至 2026），LLM 项目里排名第一；
- **Ollama、LM Studio、GPT4All、Jan、KoboldCpp 全都基于它**；
- **GGUF 格式**已成为消费级 LLM 权重的**事实标准**（HuggingFace 上一半模型都有 GGUF 版）；
- **手机端 LLM**（`llama.cpp` iOS/Android 港）几乎唯一选择；
- **零 Python 依赖**，运维极其干净。

**一句话**：**只要目标不是数据中心极致吞吐，llama.cpp 就是首选**——特别是本地/边缘/离线/隐私场景，**没有对手**。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **L1 入门** | 会用 `llama-cli` / `llama-server` 跑 GGUF |
| **L2 熟练** | 会自己编译（带 CUDA/Metal/Vulkan）、会 GGUF 量化 |
| **L3 高阶** | 会挂 HTTP 服务、会调 `n_gpu_layers` / `n_ctx` 榨性能、会用 Speculative / Grammar |
| **L4 专家** | 能读 `ggml.c` / `llama.cpp` 源码、能加新算子、能写自定义 backend |

---

## 1. llama.cpp 是什么：一句话讲清 vs vLLM / vs Ollama

### 1.1 定义

> **llama.cpp = 一份 C/C++ 代码 + 一个 GGUF 权重 → 在任何硬件上跑 LLM**。它包含两个核心组件：
> - **ggml**：底层张量 & kernel 库（作者 Georgi Gerganov 独立开发）；
> - **llama.cpp**：LLM 推理框架（基于 ggml），支持 Llama、Mistral、Qwen、DeepSeek、Gemma、Phi 等 100+ 模型。

三个关键点：

1. **纯 C/C++**：编译后就是**一个二进制文件**，零依赖；
2. **GGUF 格式**：自研的**单文件权重格式**（含 tokenizer、metadata、量化权重）；
3. **后端可插拔**：CPU（SIMD）/ CUDA / Metal / Vulkan / ROCm / SYCL 都能一键切。

### 1.2 三者定位

```
              llama.cpp          Ollama            vLLM / TRT-LLM
                 │                  │                   │
                 ▼                  ▼                   ▼
             底层引擎           llama.cpp 之上         数据中心
             (C/C++)            的 CLI+服务器         Python 服务
             通吃硬件           通吃硬件               NV GPU 极致
             硬核用户           普通用户               生产工程师
```

Ollama = 更友好的 llama.cpp 包装（模型仓库 + CLI + 后台 daemon）。你学会 llama.cpp，用 Ollama 时会知道底层在发生什么。

### 1.3 核心架构一图流

```
      LLM 权重 (.safetensors / .pth)
              │
       [convert-hf-to-gguf.py]
              │
              ▼
        model.gguf  ◄── 单文件（含 tokenizer + 权重 + metadata）
              │
       [llama-quantize]  ◄── 可选：F16 → Q4_K_M / Q5_K_M / ...
              │
              ▼
        model-Q4_K_M.gguf
              │
   ┌──────────┼──────────┬──────────┐
   ▼          ▼          ▼          ▼
llama-cli  llama-server llama-bench llama-perplexity
 (交互式)   (HTTP API)   (基准测试)  (评测)
              │
              ▼
       [ggml backends]
    CPU / CUDA / Metal / Vulkan / ROCm / SYCL
```

---

## 2. 环境搭建（Windows / Linux / macOS）

### 2.1 直接下载预编译版（懒人首选）

<https://github.com/ggerganov/llama.cpp/releases>

选对应平台的 `.zip`（如 `llama-b5000-bin-win-cuda-cu12.4-x64.zip`），解压即用。

### 2.2 从源码编译（推荐，能开更多特性）

```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

# CPU 版
cmake -B build && cmake --build build --config Release -j

# CUDA 版
cmake -B build -DGGML_CUDA=ON && cmake --build build --config Release -j

# Metal 版（Mac 自动开启）
cmake -B build && cmake --build build --config Release -j

# Vulkan 版（AMD / Intel GPU 通用）
cmake -B build -DGGML_VULKAN=ON && cmake --build build --config Release -j
```

### 2.3 下载 GGUF 权重

从 HuggingFace 拉：
- `bartowski/Meta-Llama-3-8B-Instruct-GGUF`
- `TheBloke/Llama-2-13B-chat-GGUF`
- `Qwen/Qwen2.5-7B-Instruct-GGUF`

```bash
huggingface-cli download bartowski/Meta-Llama-3-8B-Instruct-GGUF \
  Meta-Llama-3-8B-Instruct-Q4_K_M.gguf --local-dir ./models
```

---

## 3. 编程模型：GGUF + ggml + backends

### 3.1 GGUF 格式

- **单文件**：权重 + tokenizer + config + 量化元数据全在一个 `.gguf` 里；
- **Memory-map 友好**：加载几乎瞬间（不像 safetensors 要反序列化）；
- **可扩展**：内置 KV metadata，可存 chat template、prompt format。

### 3.2 ggml：底层张量库

llama.cpp 内的 ggml 是**"简化版 PyTorch"**——只支持推理，只关心性能。核心概念：

- `ggml_tensor`：张量对象；
- `ggml_context`：内存池（预分配）；
- `ggml_cgraph`：计算图；
- backends：CPU / CUDA / Metal / Vulkan 都是 backends 的实现。

### 3.3 编程 API 三层

| 层级 | API | 适用 |
|:--|:--|:--|
| **CLI** | `llama-cli` / `llama-server` | 90% 用户 |
| **C API** | `llama.h` | 集成到 C/C++ 应用 |
| **绑定** | `llama-cpp-python`、`node-llama-cpp`、`llama-cpp-rs` | Python / JS / Rust 用户 |

---

## 4. 第一个例子：在笔记本跑 Llama-3-8B

### 4.1 交互式 chat

```bash
./llama-cli \
  -m ./models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf \
  -p "You are a helpful assistant." \
  -cnv \
  -n 200
```

**参数速查**：
- `-m`：模型路径；
- `-p`：system prompt；
- `-cnv`：conversation 模式；
- `-n`：最大生成 token 数；
- `-ngl 32`：offload 32 层到 GPU（有 GPU 时用）；
- `-c 8192`：context 长度。

### 4.2 全 GPU 加载（有 CUDA）

```bash
./llama-cli \
  -m ./models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf \
  -ngl 999 \
  -p "写一首关于秋天的诗" \
  -n 200
```

`-ngl 999` = "所有层都上 GPU"。

### 4.3 Python 绑定（`llama-cpp-python`）

```bash
pip install llama-cpp-python
```

```python
from llama_cpp import Llama

llm = Llama(
    model_path="./models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
    n_gpu_layers=999,
    n_ctx=4096,
)
out = llm("Q: What is FlashAttention?\nA:", max_tokens=200)
print(out["choices"][0]["text"])
```

---

## 5. 量化实战：从 F16 到 Q2_K，模型能压多小？

### 5.1 量化速查表（Llama-3-8B 为例）

| 量化 | 文件大小 | 显存 | 质量（越高越好，F16=100）| 场景 |
|:--|:--|:--|:--|:--|
| F16 | 16 GB | 16 GB | 100 | 基准 |
| Q8_0 | 8.5 GB | 9 GB | 99.9 | 精度敏感 |
| **Q6_K** | 6.6 GB | 7 GB | 99.7 | **质量首选** |
| **Q5_K_M** | 5.7 GB | 6 GB | 99.4 | 平衡 |
| **Q4_K_M** | 4.9 GB | 5.5 GB | 98.5 | **主流推荐** ⭐ |
| Q4_0 | 4.6 GB | 5 GB | 97.5 | 老格式 |
| Q3_K_M | 3.8 GB | 4.5 GB | 95 | 显存紧 |
| Q2_K | 2.9 GB | 3.5 GB | 88 | 极限压缩 |

**推荐**：
- 16 GB 显存 → **Q6_K 或 Q5_K_M**；
- 8 GB 显存 → **Q4_K_M**（默认推荐）；
- 4 GB 显存 → **Q3_K_M**；
- 手机 / 树莓派 → **Q2_K**（勉强能用）。

### 5.2 自己量化

```bash
# Step 1: HF → GGUF (F16)
python convert_hf_to_gguf.py ./Meta-Llama-3-8B-Instruct \
    --outfile llama3-8b-f16.gguf --outtype f16

# Step 2: F16 → Q4_K_M
./llama-quantize llama3-8b-f16.gguf llama3-8b-q4_k_m.gguf Q4_K_M
```

---

## 6. 起 OpenAI 兼容 HTTP 服务

```bash
./llama-server \
  -m ./models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf \
  --host 0.0.0.0 --port 8080 \
  -c 8192 -ngl 999
```

用 OpenAI SDK 打过去：

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8080/v1", api_key="EMPTY")
resp = client.chat.completions.create(
    model="local",
    messages=[{"role": "user", "content": "Hi!"}],
)
print(resp.choices[0].message.content)
```

`llama-server` 内置一个 Web UI，直接访问 `http://localhost:8080` 就能聊天。

---

## 7. 后端矩阵：CUDA / Metal / Vulkan / ROCm / OpenBLAS

| 后端 | 硬件 | 编译宏 | 速度 |
|:--|:--|:--|:--|
| **CPU (AVX2/AVX512)** | 所有 x86 CPU | 默认 | ★★（够用）|
| **CUDA** | NVIDIA GPU | `GGML_CUDA=ON` | ★★★★★ |
| **Metal** | Apple Silicon | 默认（macOS）| ★★★★★（M 系列超强）|
| **Vulkan** | 任何 Vulkan GPU（AMD/Intel/NV）| `GGML_VULKAN=ON` | ★★★★ |
| **ROCm** | AMD GPU (专业)  | `GGML_HIPBLAS=ON` | ★★★★ |
| **SYCL** | Intel GPU | `GGML_SYCL=ON` | ★★★ |
| **CANN** | 华为昇腾 NPU | `GGML_CANN=ON` | ★★★ |

**Mac M 系列的性能真的很惊人**：M3 Max 跑 Llama-3-70B Q4_K_M 大约 8~10 tok/s（对比 RTX 4090 大约 20~25 tok/s）。

---

## 8. 进阶：Speculative / Grammar / Multi-modal

### 8.1 Speculative Decoding

```bash
./llama-cli \
  -m Llama-3-70B-Q4_K_M.gguf \
  -md Llama-3-8B-Q4_K_M.gguf \
  -p "..." -n 200 --draft 4
```

`-md` = draft model，通常选同家族的小号模型。

### 8.2 Grammar（BNF）约束输出

```bash
./llama-cli -m model.gguf \
  --grammar 'root ::= "{" ws "\"answer\":" ws number ws "}"
             number ::= [0-9]+
             ws ::= [ \t\n]*'
```

底层用 GBNF（GGUF 版 BNF），保证输出严格符合语法。

### 8.3 多模态（LLaVA / MiniCPM-V / Qwen-VL）

```bash
./llama-mtmd-cli \
  -m Qwen2-VL-7B-Instruct-Q4_K_M.gguf \
  --mmproj Qwen2-VL-7B-mmproj.gguf \
  --image ./cat.jpg -p "描述这张图"
```

---

## 9. 性能分析：CPU / GPU 分别跑多快？

### 9.1 用 `llama-bench` 跑基准

```bash
./llama-bench -m Meta-Llama-3-8B-Instruct-Q4_K_M.gguf -n 128
```

### 9.2 参考数据（Llama-3-8B Q4_K_M，pp=prompt / tg=generate）

| 硬件 | pp 128 (tok/s) | tg 128 (tok/s) |
|:--|:--|:--|
| RTX 4090 | 5000+ | 130 |
| RTX 3060 | 2500 | 55 |
| M3 Max | 1500 | 85 |
| M2 Pro | 700 | 40 |
| i9-13900K (CPU only) | 100 | 12 |
| Raspberry Pi 5 (CPU only) | 15 | 2 |

### 9.3 调参优先级

1. `-ngl`：offload 到 GPU 的层数（越多越快，但吃显存）；
2. `-c`：context 长度（越大越吃内存/显存）；
3. `-t`：线程数（CPU 场景，一般 = 物理核心数）；
4. `-b` / `-ub`：batch size（长 prompt 时增大）；
5. `--flash-attn`：开 FlashAttention（新版默认开）。

---

## 10. 学习路线图（3~5 周）

| 周 | 目标 | 产出 |
|:--|:--|:--|
| Week 1 | 下预编译版跑起来 + Web UI | Llama-3-8B 在自机 chat |
| Week 2 | 从源码编（带 CUDA/Metal）+ 量化 | 自己出一份 Q4_K_M |
| Week 3 | 挂 `llama-server` + OpenAI SDK 集成 | 一个可上线的本地 API |
| Week 4 | Speculative / Grammar / Multi-modal | 一个多模态 demo |
| Week 5 | 读 `ggml.c` / `llama.cpp` 源码 | 能改核心或加算子 |

---

## 11. 精选资源与踩坑清单

### 11.1 官方资源
- **GitHub**：<https://github.com/ggerganov/llama.cpp>
- **文档 / Wiki**：<https://github.com/ggerganov/llama.cpp/wiki>
- **HuggingFace GGUF 集合**：<https://huggingface.co/models?library=gguf>
- **`llama-cpp-python`**：<https://github.com/abetlen/llama-cpp-python>
- **Ollama（推荐当"上层壳"）**：<https://ollama.com/>

### 11.2 姊妹篇
- [vLLM 编程学习指南](./vLLM编程学习指南.md)
- [TensorRT-LLM 编程学习指南](./TensorRT-LLM编程学习指南.md)
- [SGLang 编程学习指南](./SGLang编程学习指南.md)
- [GPU 编程工具全景](./GPU编程工具全景.md)

### 11.3 十大踩坑
1. **-ngl 忘开**：不加 `-ngl` 就全走 CPU，慢 10x；
2. **量化太狠掉智商**：Q2_K 只在极限场景用；
3. **`n_ctx` 太大 OOM**：不用长上下文就设 4096；
4. **prompt template 不对**：Llama-3 / Qwen / Mistral 的 chat template 各不同，用 `--chat-template` 指定；
5. **Mac 上编译要装 Xcode Command Line Tools**；
6. **Windows 下路径有空格**要加双引号；
7. **Speculative 的 draft 必须和 target 同 tokenizer**；
8. **多模态模型需要额外的 `mmproj` 文件**；
9. **老版 `.bin` 格式已废弃**，一律用 GGUF；
10. **`llama-server` 默认 CORS 关闭**，前端跨域需加 `--api-key` 或反向代理。

---

**版权声明**：本文由汪亮（bertonwang）撰写，转载请注明出处。欢迎邮件（<47608843@qq.com>）交流勘误。

**一句话总结**：**llama.cpp = 让 LLM 跑在任何硬件上的开源奇迹**。单文件二进制 + GGUF 权重 + 全后端支持，是本地 / 边缘 / 隐私 / 消费级硬件部署 LLM 的**唯一正确答案**。
