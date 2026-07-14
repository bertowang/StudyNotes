# Nsight 性能分析学习指南：GPU 优化的"X 光机"

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：会写 CUDA/Triton kernel、但优化时只会 `time.time()` 打时间戳、看不懂 timeline 与 occupancy 的 AI 工程师。
> **目标**：读完本文，你能用 Nsight Systems 找到"整个程序"的瓶颈，用 Nsight Compute 找到"单个 kernel"的瓶颈，说清 SM 利用率、DRAM 带宽、Roofline 三大关键指标。

---

## 目录

- [0. 写在最前：为什么 Nsight 是所有 GPU 工程师的必修课](#0-写在最前为什么-nsight-是所有-gpu-工程师的必修课)
- [1. 全家桶：Nsight Systems vs Nsight Compute vs 老 nvprof](#1-全家桶nsight-systems-vs-nsight-compute-vs-老-nvprof)
- [2. Nsight Systems：程序级 timeline 分析](#2-nsight-systems程序级-timeline-分析)
- [3. Nsight Compute：kernel 级深度剖析](#3-nsight-computekernel-级深度剖析)
- [4. 三大核心指标：SM 利用率 / DRAM 带宽 / Roofline](#4-三大核心指标sm-利用率--dram-带宽--roofline)
- [5. PyTorch / Triton 工程实践](#5-pytorch--triton-工程实践)
- [6. 十大常见瓶颈模式与识别方法](#6-十大常见瓶颈模式与识别方法)
- [7. 学习路线图（2~3 周）](#7-学习路线图23-周)
- [8. 精选资源与官方链接](#8-精选资源与官方链接)

---

## 0. 写在最前：为什么 Nsight 是所有 GPU 工程师的必修课

**残酷真相**：99% 的初学者优化 GPU 代码，都在**盲人摸象**——改一改代码、跑一跑 `time.time()`、觉得快了就发版。这样的优化 **90% 是玄学**。

**Nsight 就是 GPU 的 X 光机**：

- 你的 kernel 是**计算瓶颈**还是**内存瓶颈**？→ Nsight Compute 一目了然；
- 你的训练循环是**卡在 kernel**还是**卡在 CPU/数据加载/通信**？→ Nsight Systems 的 timeline 直接告诉你；
- 你的 SM 是**跑满了**还是**在打瞌睡**？→ Occupancy / SM Active 指标秒懂。

**没有 Nsight 的 GPU 优化 = 没有 profiler 的性能工程 = 蒙眼开车**。

### 0.1 一句话总结

> **Nsight Systems 看"哪里慢"，Nsight Compute 看"为什么慢"**。前者是**望远镜**（全局 timeline），后者是**显微镜**（单个 kernel 微指标）。

### 0.2 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **G1 认知** | 能区分 Systems 与 Compute 的用途，看得懂 timeline |
| **G2 会用** | 能定位 CPU/GPU 空闲、H2D/D2H 拷贝、NCCL 通信瓶颈 |
| **G3 会读** | 能读懂 SM 利用率、Memory Throughput、Warp Stall 原因 |
| **G4 会优** | 根据 Nsight 结果做出正确优化决策，反复迭代提速 10 倍 |

**建议**：读完本文你到 **G2**，配合实操 1~2 个项目冲到 **G3**。

---

## 1. 全家桶：Nsight Systems vs Nsight Compute vs 老 nvprof

### 1.1 三大工具速查表

| 工具 | 定位 | 输入 | 输出 | 适用场景 |
|:--|:--|:--|:--|:--|
| **Nsight Systems** (`nsys`) | 系统级 timeline | 整个程序 | 时间线（CPU/GPU/NCCL/CUDA API）| **先用它**：找宏观瓶颈 |
| **Nsight Compute** (`ncu`) | Kernel 级微指标 | 单个 kernel | 数百项 metric + Roofline | **再用它**：优化单个 kernel |
| **nvprof / nvvp** | 老工具（已废弃）| CUDA 9 之前 | Timeline + metric | ⚠️ 不再更新，用 nsys/ncu 替代 |

### 1.2 什么时候用哪个？

```
优化 GPU 程序的正确姿势：
    │
    1️⃣ nsys profile python train.py   # 先看整体：CPU 卡？GPU 卡？通信卡？
    │
    ├─ 发现 GPU 空闲多 → 检查数据加载 / CPU 逻辑
    ├─ 发现 NCCL 时间长 → 检查通信拓扑 / 梯度桶
    └─ 发现某几个 kernel 占大头 → 进入 2️⃣
    │
    2️⃣ ncu --set full python train.py  # 深挖 kernel：为什么慢？
    │
    ├─ Compute Throughput 高 → 计算瓶颈，考虑降精度/融合
    ├─ Memory Throughput 高 → 访存瓶颈，考虑合并访问/共享内存
    └─ 都不高 → Latency 瓶颈，考虑增加 occupancy
```

---

## 2. Nsight Systems：程序级 timeline 分析

### 2.1 最小上手示例

```bash
# 1. 采集
nsys profile -o report -t cuda,nvtx,cudnn,cublas,nccl python train.py

# 2. 查看：GUI 打开 report.nsys-rep（推荐）或转 SQLite
nsys stats report.nsys-rep
```

打开 GUI 后你能看到 **6 大信息通道**：

| 通道 | 内容 |
|:--|:--|
| **CPU threads** | 每个 CPU 线程的执行时间 |
| **CUDA API** | `cudaMemcpyAsync` / `cudaLaunchKernel` 调用时间 |
| **CUDA HW** | GPU 上真正执行的 kernel + memcpy |
| **NVTX** | 你自己插入的标签（下面会讲）|
| **NCCL** | 集合通信操作 |
| **cuDNN / cuBLAS** | 官方库调用 |

### 2.2 NVTX：给自己的代码打标签

**痛点**：默认 timeline 只有 `elementwise_kernel_23`，你根本不知道是哪一层。

**方案**：用 NVTX 打标签：

```python
import torch.cuda.nvtx as nvtx

for step, batch in enumerate(loader):
    nvtx.range_push(f"step_{step}")

    nvtx.range_push("forward")
    out = model(batch)
    nvtx.range_pop()

    nvtx.range_push("backward")
    loss.backward()
    nvtx.range_pop()

    nvtx.range_push("optimizer")
    opt.step()
    nvtx.range_pop()

    nvtx.range_pop()
```

这样 timeline 会**分层显示**，你能一眼看到 forward/backward/optimizer 各占多少。

### 2.3 六大 timeline 常见"病症"

| 症状 | 长啥样 | 诊断 |
|:--|:--|:--|
| **GPU 空闲多** | GPU 通道大量空白 | 数据加载慢 / CPU 前处理重 |
| **kernel 之间有缝** | 每个 kernel 间隔 5~50 μs | Launch overhead 太多，考虑 CUDA Graphs |
| **H2D/D2H 拷贝频繁** | Memcpy 占 30%+ | 数据 pinned 了吗？异步了吗？ |
| **NCCL 前有等待** | AllReduce 前 GPU 空闲 | 梯度累积不同步 / 拓扑不对 |
| **单个 kernel 巨长** | 一个 kernel 占 60%+ | 用 ncu 深挖它 |
| **Python 侧 CPU 100%** | CPU 通道满 | GIL 争用 / DataLoader worker 少 |

---

## 3. Nsight Compute：kernel 级深度剖析

### 3.1 最小上手示例

```bash
# 采集全部指标（慢，但信息完整）
ncu --set full -o kernel_report python train.py

# 只采集第 100~110 个 kernel（快）
ncu --set full --launch-skip 100 --launch-count 10 python train.py

# 只采集名字包含 "gemm" 的 kernel
ncu --set full --kernel-name regex:.*gemm.* python train.py
```

**⚠️ 重要**：`ncu` 会让 kernel **慢 10~100 倍**（要重放采集不同 metric），只用于诊断，不用于生产。

### 3.2 GUI 打开后看什么？

Nsight Compute UI 分几个关键面板：

| 面板 | 关键信息 |
|:--|:--|
| **GPU Speed Of Light** | SM % / Memory % 双柱图 —— **第一眼看这个** |
| **Compute Workload Analysis** | FMA/ALU/Tensor Core 利用率 |
| **Memory Workload Analysis** | L1/L2/DRAM 各层带宽 & 命中率 |
| **Scheduler Statistics** | Warp 调度效率、Stall 原因 |
| **Occupancy** | 理论/实际 occupancy + 限制因子（reg/shmem/block）|
| **Source Counters** | 每一行 SASS 汇编的开销 |

### 3.3 五大 Warp Stall 原因（面试高频）

`ncu` 会告诉你每个 warp 在**因为什么原因等待**：

| Stall Reason | 含义 | 常见修法 |
|:--|:--|:--|
| **Long Scoreboard** | 等 DRAM 数据 | 用 shared memory / 增加 occupancy |
| **Short Scoreboard** | 等 shared memory | 减少 bank conflict |
| **Wait** | 等待固定周期指令 | 增加 ILP / 更多 warp |
| **Not Selected** | 有别的 warp 在跑 | 正常，说明 occupancy 够 |
| **Barrier** | 等 `__syncthreads()` | 减少同步点 |

---

## 4. 三大核心指标：SM 利用率 / DRAM 带宽 / Roofline

### 4.1 SM Active vs SM Busy vs SM Occupancy

**三个术语很容易搞混**：

| 指标 | 含义 | 理想值 |
|:--|:--|:--|
| **SM Active %** | 有多少 SM 在跑（对全局）| **>90%**（否则 grid 太小）|
| **SM Busy %** | SM 里的 warp scheduler 有多忙 | **>60%** |
| **Occupancy** | 实际活跃 warp / 理论最大 warp | **>50%**（不是越高越好）|

### 4.2 DRAM Throughput：内存带宽用了多少？

```
DRAM Throughput = 实际 DRAM 带宽 / 硬件峰值带宽

例如 A100 峰值 1555 GB/s，你的 kernel 达到 1200 GB/s → 77%（很好）
                                        400 GB/s → 26%（有优化空间）
```

**关键判断**：

- 如果 DRAM% **接近 100%** → **访存瓶颈**（memory-bound），优化方向：融合算子、减少访存；
- 如果 SM% **接近 100%** → **计算瓶颈**（compute-bound），优化方向：降精度（FP16/BF16/FP8）、用 Tensor Core；
- 如果**都不高** → **Latency 瓶颈**，优化方向：提高 occupancy、增大 batch。

### 4.3 Roofline 模型：一图看懂瓶颈

```
                     性能 (GFLOPS)
                        ▲
       峰值算力  ───────┼───────────────  <── Compute Bound
                        │            /
                        │          /
                        │        / <── 你的 kernel 在这条斜线上 = Memory Bound
                        │      /
                        │    /  斜率 = DRAM 带宽
                        │  /
                        │/
                        └───────────────────► 算术强度 (FLOPs / Byte)
```

**算术强度**：每字节访存能做多少浮点运算。

- **Element-wise（如 add、relu）**：≈ 0.25 → **必然 memory-bound**；
- **GEMM (大矩阵)**：≈ 100+ → **可能 compute-bound**；
- **Attention (FlashAttention 优化后)**：≈ 20~50 → 中间地带。

**Nsight Compute 直接画 Roofline 图**，你的 kernel 是一个点，告诉你离屋顶还有多远。

---

## 5. PyTorch / Triton 工程实践

### 5.1 只 profile 第 N 步（跳过 warmup）

```python
import torch

for step in range(200):
    if step == 100:
        torch.cuda.cudart().cudaProfilerStart()

    train_one_step(...)

    if step == 110:
        torch.cuda.cudart().cudaProfilerStop()
```

配合命令：

```bash
nsys profile --capture-range=cudaProfilerApi python train.py
```

### 5.2 torch.profiler 一体化方案（推荐）

```python
from torch.profiler import profile, ProfilerActivity, schedule

with profile(
    activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
    schedule=schedule(wait=10, warmup=10, active=5, repeat=1),
    on_trace_ready=torch.profiler.tensorboard_trace_handler('./log'),
    record_shapes=True,
    with_stack=True,
) as prof:
    for step, batch in enumerate(loader):
        train_step(batch)
        prof.step()
```

产出的 trace 可以：
- 用 **TensorBoard** 直接查看；
- 转 `chrome://tracing` 打开；
- 或用 **Perfetto**（<https://ui.perfetto.dev/>）。

### 5.3 Triton kernel 的 profile

```python
import triton

# 方式 1：Triton 内置 benchmark
@triton.testing.perf_report(...)
def bench_softmax(...): ...

# 方式 2：直接 ncu
# ncu --kernel-name softmax_kernel python test_softmax.py
```

**看 Triton kernel 的 PTX / SASS**：

```python
kernel = softmax_kernel.warmup(...)
print(kernel.asm['ptx'])    # PTX 汇编
print(kernel.asm['sass'])   # SASS 汇编（GPU 真实指令）
```

---

## 6. 十大常见瓶颈模式与识别方法

| # | 瓶颈 | Nsight 里的表现 | 优化方向 |
|:--:|:--|:--|:--|
| **1** | 数据加载慢 | Systems: GPU 空闲、CPU 满 | 增 DataLoader worker / pinned memory |
| **2** | 小 kernel 太多 | Systems: 密密麻麻的小 kernel | 算子融合 / CUDA Graphs |
| **3** | Bank conflict | Compute: Shared Memory 带宽低 | 加 padding / swizzle |
| **4** | 非合并访存 | Compute: L1 命中率低 + DRAM 高 | 调整内存布局 (AoS→SoA) |
| **5** | Occupancy 低（寄存器爆）| Compute: Occupancy 30% + Reg 高 | 减小 block size / 用 `__launch_bounds__` |
| **6** | Warp 分歧 | Compute: Divergent Branches 高 | 消除 `if` / 数据重排 |
| **7** | Tensor Core 没用上 | Compute: Tensor Active 0% | 用 FP16/BF16 + 对齐维度 |
| **8** | NCCL 通信慢 | Systems: NCCL 占 30%+ | 梯度桶 / 拓扑 / NVLink |
| **9** | H2D 频繁 | Systems: Memcpy 通道满 | Pinned / 异步 / prefetch |
| **10** | Python 侧 GIL | Systems: 单核 100% | 用 C++ 扩展 / TorchScript |

---

## 7. 学习路线图（2~3 周）

### Week 1：Nsight Systems 上手
- 装好 `nsys`（NVIDIA HPC SDK 自带）；
- 跑一次自己的 PyTorch 训练，采集 timeline；
- 加 NVTX 标签，分层看 forward / backward / optim；
- 定位一个宏观瓶颈（数据加载 / kernel / 通信）。

### Week 2：Nsight Compute 进阶
- 用 `ncu` 对上周最慢的 kernel 做 `--set full`；
- 学会看 GPU Speed of Light、Occupancy、Memory Workload；
- 尝试识别 memory-bound / compute-bound；
- 读 Roofline 图，找到自己 kernel 的位置。

### Week 3：实战优化
- 挑一个自己的 Triton / CUDA kernel，先测基线；
- 用 Nsight 找瓶颈 → 修改 → 再测 → 迭代 3~5 轮；
- 目标：性能提升 2 倍以上，说得清每一步为什么快了。

---

## 8. 精选资源与官方链接

### 8.1 官方文档
- **Nsight Systems**：<https://developer.nvidia.com/nsight-systems>
- **Nsight Compute**：<https://developer.nvidia.com/nsight-compute>
- **Nsight Compute Kernel Profiling Guide**：<https://docs.nvidia.com/nsight-compute/ProfilingGuide/>
- **NVTX**：<https://nvidia.github.io/NVTX/>

### 8.2 教程 / 视频
- **GTC "Optimizing CUDA Applications with Nsight"** 系列（每年更新）；
- **PyTorch Profiler 教程**：<https://pytorch.org/tutorials/recipes/recipes/profiler_recipe.html>
- **Perfetto UI**：<https://ui.perfetto.dev/>

### 8.3 姊妹篇
- [面向 AI 的 CUDA 编程学习指南](./CUDA-AI编程学习指南.md)（先学 CUDA 心智模型）
- [Triton 编程学习指南](./Triton编程学习指南.md)（Nsight 常用来优化 Triton kernel）
- [GPU 编程工具全景](./GPU编程工具全景.md)（工具生态总入口）

---

**版权声明**：本文由汪亮（bertonwang）撰写，转载请注明出处。欢迎邮件（<47608843@qq.com>）交流勘误。

**一句话总结全文**：**没有 Nsight 的 GPU 优化就是玄学**——`nsys` 找宏观瓶颈、`ncu` 挖单 kernel、看懂 SM% / DRAM% / Roofline 三大指标，你就从"改代码碰运气"升级到"数据驱动优化"。
