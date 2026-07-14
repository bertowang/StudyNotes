# TVM 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：写**跨平台 AI 推理引擎**（云 GPU / 手机 / 端侧 NPU / 树莓派 / MCU）、做**编译器 / AutoML for kernels**、想理解**AI 模型 → 硬件可执行代码"的完整编译栈**的程序员。已经用过 PyTorch/ONNX，最好熟悉编译原理基础（IR、Pass、Schedule）。
> **目标**：2~4 周内，从"用 Relax 前端 import 一个 ONNX 模型跑通推理"到"能自定义算子、能用 MetaSchedule 自动调优、能用 TVM Unity 编译大模型到 CUDA / Vulkan / Metal"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1** + Python **3.10+** + TVM **0.17+ (Unity 版本)**。**Linux 首选**；Windows 支持源码编译，WSL2 是最舒服的方式。

---

## 目录

- [0. 写在最前：为什么要学 TVM？](#0-写在最前为什么要学-tvm)
- [1. TVM 是什么：一句话讲清 vs ONNX Runtime / vs TensorRT / vs torch.compile](#1-tvm-是什么一句话讲清-vs-onnx-runtime--vs-tensorrt--vs-torchcompile)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. TVM Unity 的心智模型：Relax / TIR / MetaSchedule / Target](#3-tvm-unity-的心智模型relax--tir--metaschedule--target)
- [4. 第一个程序：ONNX 模型 → Relax → GPU](#4-第一个程序onnx-模型--relax--gpu)
- [5. TIR：底层张量循环 IR，逐段拆解](#5-tir底层张量循环-ir逐段拆解)
- [6. Schedule：把一个矩阵乘变快 100 倍](#6-schedule把一个矩阵乘变快-100-倍)
- [7. MetaSchedule：AutoTune 自动搜最优](#7-metaschedule-autotune-自动搜最优)
- [8. 部署：一个模型跑 GPU / CPU / Android / iOS / WebGPU](#8-部署一个模型跑-gpu--cpu--android--ios--webgpu)
- [9. 高阶：BYOC / 自定义 op / 与 MLC-LLM 集成](#9-高阶byoc--自定义-op--与-mlc-llm-集成)
- [10. 性能分析与调优](#10-性能分析与调优)
- [11. TVM vs torch.compile / TensorRT / ONNX Runtime / XLA](#11-tvm-vs-torchcompile--tensorrt--onnx-runtime--xla)
- [12. 学习路线图（3 周）](#12-学习路线图3-周)
- [13. 精选资源与踩坑清单](#13-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 TVM？

你可能会问：**PyTorch 有 torch.compile、推理有 TensorRT/ONNX Runtime，为什么还要学 TVM？** 答案是四点：

1. **TVM 覆盖硬件最广**——GPU / CPU / ARM / Vulkan / Metal / WebGPU / RISC-V / DSP / NPU；
2. **TVM 有编译器教科书级别的分层设计**——学它 = 学一整套 AI 编译器；
3. **MLC-LLM（陈天奇团队）** 让 Llama-7B 在**手机、浏览器、Mac、树莓派**跑起来的核心引擎；
4. **AutoTune（MetaSchedule）** —— 让机器自动写出比人类专家更快的 kernel。

### 0.1 一句话对比

| 场景 | ONNX Runtime | TensorRT | torch.compile | **TVM** |
|:--|:--|:--|:--|:--|
| NVIDIA GPU 极致推理 | ✅ | **✅ 最强** | ✅ | ✅ |
| AMD GPU / Intel GPU | ⚠️ | ❌ | ⚠️ | **✅** |
| 手机（Android/iOS） | ⚠️ | ❌ | ❌ | **✅** |
| 浏览器 (WebGPU) | ⚠️ | ❌ | ❌ | **✅** |
| RISC-V / MCU | ❌ | ❌ | ❌ | **✅** |
| 自动调优出新 kernel | ❌ | ⚠️ | ⚠️ | **✅ 顶级** |

### 0.2 TVM 现在有多重要？

- **MLC-LLM / Web-LLM** —— 大模型跑在浏览器/手机的官方方案；
- **陈天奇 & OctoAI**（后被 NVIDIA 收购）—— 编译器工业化标杆；
- **Amazon SageMaker Neo** 的核心；
- **国产 AI 芯片厂商** 大量基于 TVM 定制后端；
- **AI 编译器教育** —— 陈天奇 CMU 编译器课程指定使用。

**一句话**：**TVM = 唯一一个"一份模型，任意硬件"的开源 AI 编译栈**——想让模型跑在任何地方，学它。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **T1 入门** | 会 import ONNX / PyTorch 到 Relax、能编译到 CUDA 跑通 |
| **T2 熟练** | 会写 TIR、会用 tir.Schedule 手动优化 GEMM |
| **T3 高阶** | 会 MetaSchedule autotune、能自定义 relax pattern |
| **T4 专家** | 会写 BYOC 接入自家硬件、能读懂 MLC-LLM / Unity 内部实现 |

**建议**：**3~5 天到 T1**，**2 周到 T2**，**3~4 周到 T3**。

---

## 1. TVM 是什么：一句话讲清 vs ONNX Runtime / vs TensorRT / vs torch.compile

### 1.1 TVM 的定义

> **Apache TVM 是端到端开源的 AI 编译栈**——把 PyTorch / TensorFlow / ONNX 等前端模型，通过多层 IR（**Relax**：图级；**TIR**：循环级）编译到任意后端（CUDA / LLVM / Vulkan / Metal / WebGPU / OpenCL / C 源码 / …）。核心特色是**Schedule 分离**（算法与优化分开写）与 **MetaSchedule 自动搜索**。

关键三点：

1. **多前端**——ONNX / PyTorch / TF / JAX 都能进；
2. **多后端**——一份 IR，编译到任意硬件；
3. **Schedule 心智**——你先写"要算什么"（compute），再写"怎么算"（schedule），机器还能帮你搜最优 schedule。

### 1.2 TVM Unity 是什么？

**TVM 0.15+ 引入的新一代架构**，把老 Relay/TE 升级为 **Relax + TIR** 二层设计：
- **Relax**：图级 IR（原 Relay 的接班），一等公民支持动态 shape、control flow、symbolic 表达；
- **TIR**：底层张量 IR，循环级表达；
- **两层可自由互调用** —— 大模型很多**"图"和"循环"混合**优化都能干。

**MLC-LLM 就是构建在 TVM Unity 之上**。

### 1.3 TVM vs 竞品

| 维度 | ONNX Runtime | TensorRT | torch.compile | XLA | **TVM (Unity)** |
|:--|:--|:--|:--|:--|:--|
| 前端 | ONNX | ONNX / Torch | PyTorch | JAX / TF | **多前端** |
| 后端 | CPU/GPU | NVIDIA GPU only | CUDA / CPU | TPU / GPU / CPU | **万能** |
| 手机 / 浏览器 | ⚠️ | ❌ | ❌ | ❌ | **✅** |
| Autotune | ❌ | 部分 | ⚠️ | ❌ | **✅ 最强** |
| 学习曲线 | 中 | 中 | 极低 | 中 | **陡** |
| 目标读者 | 部署工程师 | 部署工程师 | AI 工程师 | Google 生态 | **编译器 / 端侧 / 芯片工程师** |

### 1.4 一张图看清 TVM 在栈里的位置

```
┌──────────────────────────────────────────────────────────┐
│  PyTorch / ONNX / TensorFlow / JAX 模型                    │
├──────────────────────────────────────────────────────────┤
│  Relax（图 IR：动态 shape、control flow）                  │
├──────────────────────────────────────────────────────────┤
│  TIR（循环 IR：block、loop、schedule）                     │
├──────────────────────────────────────────────────────────┤
│  MetaSchedule（自动 tuning，从 schedule 空间搜最优）        │
├──────────────────────────────────────────────────────────┤
│  Codegen：CUDA / LLVM / Vulkan / Metal / WebGPU / C       │
├──────────────────────────────────────────────────────────┤
│  Runtime：TVM Runtime（PackedFunc + Module）              │
├──────────────────────────────────────────────────────────┤
│  硬件：NVIDIA / AMD / ARM / x86 / iOS / Android / Web / …   │
└──────────────────────────────────────────────────────────┘
```

**核心洞察**：TVM 把"AI 模型 → 硬件代码"变成一个**教科书级分层编译流水线** —— 每一层都可插拔、可定制。

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 平台

| 平台 | 支持 | 说明 |
|:--|:--|:--|
| Linux 原生 | ✅ 最好 | **首选** |
| WSL2 | ✅ 好 | Windows 学 TVM 的最佳方式 |
| Windows 原生 | ⚠️ 源码可编 | 环境配置繁琐 |
| macOS | ✅ | Metal 后端一等公民 |

### 2.2 安装（用 nightly 预编译）

```bash
# 官方推荐：从 mlc.ai 拉最新 nightly
python -m pip install --pre --force-reinstall \
    -f https://mlc.ai/wheels mlc-ai-nightly-cu121
# 会附带 tvm（Unity）
```

或**源码编译**（长期玩必需）：

```bash
git clone --recursive https://github.com/apache/tvm.git
cd tvm && mkdir build && cd build
cmake -DUSE_CUDA=ON -DUSE_LLVM=ON -DUSE_CUBLAS=ON -DUSE_CUDNN=ON ..
make -j$(nproc)
export TVM_HOME=$PWD/..
export PYTHONPATH=$TVM_HOME/python
```

### 2.3 一步验证：hello_tvm.py

```python
import tvm
from tvm import relax
import numpy as np

# 1. 用 Relax script 写一个模型
from tvm.script import relax as R, tir as T
from tvm.script import ir as I

@I.ir_module
class MyModule:
    @R.function
    def main(x: R.Tensor((4, 4), "float32")) -> R.Tensor((4, 4), "float32"):
        with R.dataflow():
            y = R.nn.relu(x + R.const(1.0, "float32"))
            R.output(y)
        return y

# 2. 编译到 GPU
target = tvm.target.Target("cuda -arch=sm_86")
ex = tvm.compile(MyModule, target)

# 3. 运行
dev = tvm.cuda(0)
vm  = relax.VirtualMachine(ex, dev)
x_np = np.random.randn(4, 4).astype("float32") - 2.0
x_tvm = tvm.nd.array(x_np, dev)
y_tvm = vm["main"](x_tvm)
print("input:\n", x_np)
print("relu(x+1):\n", y_tvm.numpy())
```

期望：负输入被 relu 变 0；`(x+1)` 后仍为负的位置变 0。

### 2.4 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| `import tvm` 报 CUDA 未编 | 装了 CPU-only wheel | 装 `mlc-ai-nightly-cu121` |
| 找不到 nvcc | PATH 缺 | 加 `<CUDA>/bin` |
| Windows 编译失败 | 依赖太多 | 用 WSL2 |
| Relay 教程和当前 API 不一致 | 老教程用 Relay，新 API 是 Relax | 认准 "Unity" / "Relax" 关键字 |
| `tvm.compile` 找不到 | 老版本用 `relax.build` | 用 Unity 新 API |
| autotune 慢 | 是正常 | 用小 trials 试水 |

---

## 3. TVM Unity 的心智模型：Relax / TIR / MetaSchedule / Target

### 3.1 四层核心概念

```
Relax (Graph IR)  ─── 图级：动态 shape、控制流、大 op（如 attention）
    │
    ▼ Lower（部分下降到 TIR）
    │
TIR (Tensor IR)   ─── 循环级：block/loop/schedule
    │
    ▼ Codegen
    │
Target Code       ─── CUDA / LLVM / Vulkan / Metal / …
```

### 3.2 Relax：图级 IR

- **一等公民支持动态 shape**（用符号 `n`, `m` 表达）；
- 支持控制流（if / while）；
- 有 `dataflow block` 概念——纯函数式子图，能被大力优化；
- 用 **TVMScript** 用 Python 语法写。

### 3.3 TIR：底层张量 IR

- **循环级**：显式写 for 循环、buffer、block；
- 每个"计算"是一个 `T.block`——**优化的最小单元**；
- Schedule 就是**改变 block 上的循环组织**（tile / split / fuse / reorder / bind）。

### 3.4 Target：编译目标

```python
tvm.target.Target("cuda -arch=sm_86")             # 3060
tvm.target.Target("llvm -mcpu=skylake-avx512")    # x86
tvm.target.Target("nvidia/nvidia-a100")           # A100
tvm.target.Target("vulkan")                       # 移动 GPU
tvm.target.Target("metal")                        # Apple GPU
tvm.target.Target("webgpu")                       # 浏览器
```

### 3.5 MetaSchedule：AutoTune 引擎

- 给一个 TIR 函数 + Target；
- MetaSchedule 生成一个**候选 schedule 空间**（tile 大小、循环顺序、绑定线程等组合）；
- 在真机上跑候选，用 cost model + 进化算法搜最优；
- 通常 1000~10000 trials 能超越人工编写的 schedule。

---

## 4. 第一个程序：ONNX 模型 → Relax → GPU

### 4.1 完整代码

```python
import numpy as np
import onnx
import tvm
from tvm import relax
from tvm.relax.frontend.onnx import from_onnx

# 1. 加载 ONNX 模型
onnx_model = onnx.load("resnet50.onnx")

# 2. import 到 Relax
mod = from_onnx(onnx_model, keep_params_in_input=True)
mod, params = relax.frontend.detach_params(mod)

# 3. 应用优化 pass
mod = relax.get_pipeline("zero")(mod)   # 基础 pipeline

# 4. 编译到 CUDA
target = tvm.target.Target("cuda -arch=sm_86", host="llvm")
ex = tvm.compile(mod, target)

# 5. 运行
dev = tvm.cuda(0)
vm  = relax.VirtualMachine(ex, dev)

x_np = np.random.randn(1, 3, 224, 224).astype("float32")
x_tvm = tvm.nd.array(x_np, dev)
params_tvm = [tvm.nd.array(p, dev) for p in params["main"]]

out = vm["main"](x_tvm, *params_tvm)
print("output shape:", out.shape)
```

### 4.2 小白级拆解

- **`from_onnx`** 把 ONNX 图转成 Relax IRModule；
- **`get_pipeline("zero")`** 应用基础优化（常量折叠、DCE、算子融合）；
- **`tvm.compile`** 走 Relax→TIR→CUDA 全流程；
- **`VirtualMachine`** 是运行时，负责调度算子。

### 4.3 6 个新手常见坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | 老教程用 Relay | API 不匹配 | 认准 Relax / Unity |
| 2 | ONNX opset 不支持 | 转换报错 | 用 onnxsim 简化 / 降 opset |
| 3 | 忘 host="llvm" | 编译崩 | 显式指定 host |
| 4 | dtype 混 | 结果错 | 前后端 dtype 一致 |
| 5 | 未调优就跑 | 慢 | 加 MetaSchedule tune |
| 6 | 显存爆 | Params 都塞 GPU | 用 `bundle_constants` |

---

## 5. TIR：底层张量循环 IR，逐段拆解

### 5.1 一个 GEMM 的 TIR 写法

```python
from tvm.script import tir as T

@T.prim_func
def gemm(A: T.Buffer((1024, 1024), "float32"),
         B: T.Buffer((1024, 1024), "float32"),
         C: T.Buffer((1024, 1024), "float32")):
    for i, j, k in T.grid(1024, 1024, 1024):
        with T.block("gemm"):
            vi, vj, vk = T.axis.remap("SSR", [i, j, k])   # S=Spatial, R=Reduce
            with T.init():
                C[vi, vj] = 0.0
            C[vi, vj] = C[vi, vj] + A[vi, vk] * B[vk, vj]
```

**关键概念**：
- **`T.Buffer`**：多维数组；
- **`T.block`**：优化的最小单元，声明轴的类型（S 空间/R 归约）；
- **`T.init`**：这个 block 的初始化语句；
- **`T.axis.remap("SSR", ...)`**：把外层 for 循环变量映射到 block 内轴。

### 5.2 为什么 block 这么设计？

因为 block 是**优化不变量**——不管你怎么 tile / reorder / bind，block 的语义永远是"用这些 axis 计算这一小块"。这让 Schedule 变换**永远数学正确**。

---

## 6. Schedule：把一个矩阵乘变快 100 倍

Schedule 就是**保持语义不变，改变循环组织**。

### 6.1 手动 schedule GEMM

```python
from tvm import tir

sch = tir.Schedule(gemm)
block_C = sch.get_block("gemm")
i, j, k = sch.get_loops(block_C)

# 1. Tile
i0, i1 = sch.split(i, [None, 32])
j0, j1 = sch.split(j, [None, 32])
k0, k1 = sch.split(k, [None, 8])

# 2. Reorder
sch.reorder(i0, j0, k0, k1, i1, j1)

# 3. 绑到 GPU 线程
sch.bind(i0, "blockIdx.y")
sch.bind(j0, "blockIdx.x")
sch.bind(i1, "threadIdx.y")
sch.bind(j1, "threadIdx.x")

# 4. Cache 到 shared memory
A_shared = sch.cache_read(block_C, 0, "shared")
B_shared = sch.cache_read(block_C, 1, "shared")

print(sch.mod.script())     # 看变换后的 TIR
```

**一步步做下来，一个 1024×1024 GEMM 从几百 ms 降到几 ms**——这就是 TVM 的"schedule 心智"。

### 6.2 关键 Schedule 原语

| 原语 | 作用 |
|:--|:--|
| `split` | 拆循环 |
| `fuse` | 合循环 |
| `reorder` | 换循环顺序 |
| `bind` | 绑到 GPU 线程 (blockIdx/threadIdx) |
| `tile` | split + reorder 组合 |
| `cache_read/write` | 引入 shared/local buffer |
| `compute_at` | 循环嵌套融合 |
| `vectorize` | SIMD 向量化 |
| `unroll` | 循环展开 |
| `parallel` | CPU 并行 |
| `pipeline` | 软件流水 |
| `tensorize` | 用硬件 intrinsic（Tensor Core！）|

---

## 7. MetaSchedule：AutoTune 自动搜最优

### 7.1 一键 tune

```python
from tvm import meta_schedule as ms

target = tvm.target.Target("cuda -arch=sm_86")
database = ms.tune_tir(
    mod=gemm,
    target=target,
    max_trials_global=1000,
    num_trials_per_iter=64,
    work_dir="./tune_work",
)

# 拿到最优 schedule
sch = ms.tir_integration.compile_tir(database, gemm, target)
```

### 7.2 关键参数

| 参数 | 含义 |
|:--|:--|
| `max_trials_global` | 总尝试数（1000 ~ 20000） |
| `num_trials_per_iter` | 每轮候选数 |
| `work_dir` | 中间结果 & 数据库 |

**建议**：**先跑 1000 trials 快速试水，效果好再加到 10000+**。

### 7.3 Tune 一个完整模型

```python
mod = from_onnx(...)                    # 拿 IRModule
database = ms.tune_relax(mod, target, max_trials_global=20000)
mod = ms.relax_integration.compile_relax(database, mod, target)
```

---

## 8. 部署：一个模型跑 GPU / CPU / Android / iOS / WebGPU

### 8.1 CUDA GPU

```python
ex = tvm.compile(mod, tvm.target.Target("cuda -arch=sm_86"))
ex.export_library("model_cuda.so")
```

### 8.2 x86 CPU

```python
tvm.target.Target("llvm -mcpu=native")
```

### 8.3 Android (ARM64 + Vulkan)

```python
tvm.target.Target("vulkan -device=adreno",
                  host="llvm -mtriple=aarch64-linux-android")
```

### 8.4 iOS (Metal)

```python
tvm.target.Target("metal", host="llvm -mtriple=arm64-apple-darwin")
```

### 8.5 WebGPU (浏览器)

```python
tvm.target.Target("webgpu", host="llvm -mtriple=wasm32-unknown-unknown-wasm")
```

**这就是 MLC-LLM 让 Llama 跑在 iPhone / MacBook / Chrome 的秘密**。

---

## 9. 高阶：BYOC / 自定义 op / 与 MLC-LLM 集成

### 9.1 BYOC（Bring Your Own Codegen）

**让 TVM 把某些子图交给你的编译器/库**：
- 例如"所有 Conv2D 交给 cuDNN、所有 GEMM 交给 cuBLAS"；
- 或"某些子图交给我自研加速卡 SDK"。

TVM 提供 `partition_for_cutlass` / `partition_for_cudnn` 等现成 partitioner。

### 9.2 自定义 op

- 在 Python 里用 `T.prim_func` 写 TIR；
- 在 Relax 里用 `R.call_tir` 挂进去；
- MetaSchedule 就能自动 tune 它。

### 9.3 MLC-LLM

**MLC-LLM = TVM Unity + 大模型部署栈**。它做了三件事：
1. 把 Llama / Qwen / GPT-2 等模型转 Relax；
2. 大量高质量 schedule + tune；
3. 打包成 iOS / Android / Web / Mac / Linux 的 App 或库。

**学 TVM Unity 后，MLC-LLM 就是"熟练读源码 + 应用场景"**。

---

## 10. 性能分析与调优

### 10.1 三条铁律

1. **一切从 schedule 开始**——没 schedule 的 TIR = 无优化 = 慢；
2. **优先 MetaSchedule**——机器搜比人写快；
3. **BYOC 关键算子**——GEMM / Conv 直调 cuBLAS / cuDNN，剩下的自 tune。

### 10.2 Profile 内建工具

```python
from tvm import runtime
prof = runtime.profiler_vm.ProfilerVM(ex, dev)
prof.set_input("main", x_tvm, *params_tvm)
report = prof.profile()
print(report)
```

### 10.3 与 Nsight 结合

TVM 生成的 CUDA 代码可以用 Nsight Compute 直接分析——`ex.export_library` 后就是普通 .so，profile 与手写 kernel 一样。

---

## 11. TVM vs torch.compile / TensorRT / ONNX Runtime / XLA

| 需求 | ONNX Runtime | TensorRT | torch.compile | XLA | **TVM** |
|:--|:--|:--|:--|:--|:--|
| NVIDIA GPU 极致推理 | ✅ | **✅** | ✅ | ✅ | ✅ |
| 手机 / 端侧 | ⚠️ | ❌ | ❌ | ❌ | **✅** |
| 浏览器 (WebGPU) | ⚠️ | ❌ | ❌ | ❌ | **✅** |
| 训练加速 | ❌ | ❌ | **✅** | ✅ | ⚠️ |
| Autotune 强度 | ❌ | ⚠️ | ⚠️ | ❌ | **✅ 最强** |
| 学习曲线 | 中 | 中 | **极低** | 中 | **陡** |
| 主要读者 | 部署工程师 | 部署工程师 | AI 工程师 | Google 生态 | **编译器 / 端侧 / 芯片工程师** |

**决策口诀**：
- **只跑 NVIDIA GPU、不折腾** → TensorRT / torch.compile；
- **跨平台部署（手机/浏览器）** → **TVM (MLC-LLM)**；
- **搞编译器 / 芯片后端** → **TVM**；
- **训练加速** → torch.compile。

---

## 12. 学习路线图（3 周）

| 周 | 目标 | 关键产出 |
|:--|:--|:--|
| **Week 1** | ONNX → Relax → CUDA 跑通、Relax/TIR 基本语法 | ResNet-50 推理 |
| **Week 2** | 手写 GEMM Schedule，理解 tile/bind/cache | GEMM 从 100ms 到 5ms |
| **Week 3** | MetaSchedule autotune、部署到 Vulkan / WebGPU | 一份 TIR，三个平台 |

### 12.1 详细每日建议

- **Day 1~2**：装环境、跑 Relax hello、看 Unity 教程；
- **Day 3~4**：TIR 语法、写第一个 vector add；
- **Day 5~7**：GEMM schedule 逐步优化，读 TVMScript 变换过程；
- **Day 8~10**：MetaSchedule tune GEMM / Conv2D；
- **Day 11~14**：ONNX 端到端模型 tune；
- **Day 15~21**：BYOC、部署 Android/WebGPU、看 MLC-LLM 源码。

---

## 13. 精选资源与踩坑清单

### 13.1 必读资源

| 资源 | 链接 |
|:--|:--|
| TVM 官网 | <https://tvm.apache.org/> |
| TVM Unity 文档 | <https://tvm.apache.org/docs/> |
| MLC 课程（陈天奇 CMU） | <https://mlc.ai/> |
| MLC-LLM | <https://github.com/mlc-ai/mlc-llm> |
| TVM GitHub | <https://github.com/apache/tvm> |
| TVM Discuss 论坛 | <https://discuss.tvm.apache.org/> |
| MetaSchedule 论文 | Shao et al. "Tensor Program Optimization with Probabilistic Programs" (NeurIPS 2022) |

### 13.2 完整踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 老教程 API 全失效 | Relay 已过时 | 用 Relax / Unity |
| Windows 编译难 | 依赖多 | WSL2 或 Docker |
| ONNX 转换报错 | opset 不支持 | onnxsim + 降 opset |
| 不 tune 就跑慢 | 无 schedule | MetaSchedule 或手动 schedule |
| MetaSchedule 内存爆 | trials 太多 | 减 trials，分批 tune |
| Autotune 结果不稳定 | 硬件抖动 | 多次取中位数 |
| Codegen 出错 | 某 op 后端不支持 | BYOC 或 fallback |
| CUDA arch 传错 | 用了错架构 | 3060 用 sm_86 |
| dtype 全流程不一致 | 混 FP16/FP32 | 明确 policy |
| 大模型编译 OOM | 图太大 | Relax pipeline 拆分 |
| WebGPU 不识别 | 浏览器版本 | Chrome 113+ |
| 移动端 crash | Vulkan 驱动 bug | 换 host GPU 或 OpenCL |

### 13.3 一句话总结

> **TVM = 唯一一个"一份模型，任意硬件"的开源 AI 编译栈**。**Relax（图 IR）+ TIR（循环 IR）+ MetaSchedule（自动 tune）+ 万能后端** 四件套，学它就是学一整套现代 AI 编译器技术，也是通往 MLC-LLM / 手机大模型 / WebGPU 部署 / 自研加速卡的核心工具。**学习曲线陡，但对编译器工程师和端侧部署工程师是必修**。

---

**祝你把大模型带到每一块硬件上。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
