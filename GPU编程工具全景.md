# GPU 编程工具全景

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：**任何想进入 GPU 编程世界的程序员**——只要你会 Python / C++ 中任意一门语言，无需任何 CUDA / Triton / AI 框架的先修经验。**这就是你的第一站**。
> **目标**：读完本文，你将拥有一张 GPU 编程工具的**心智地图**——听到 CUDA、Triton、CUTLASS、Thrust、NCCL、Numba、CuPy、TVM、XLA、Warp、Pallas、Mojo、MLIR、FlashAttention 时不再懵，并且知道**自己的场景该从哪份深度指南、哪个工具入手**。
> **本文定位**：**33 份姊妹篇的总入口**。先看全景选路线，再挑一份深度指南精读，比盲目啃某本大部头高效得多。

---

## 目录

- [0. 写在最前：为什么要看"全景"，而不是死磕一个工具？](#0-写在最前为什么要看全景而不是死磕一个工具)
- [0.3 姊妹篇速览：按抽象层与领域的 33 份深度指南（总入口）](#03-姊妹篇速览按抽象层与领域的-33-份深度指南总入口)
- [1. 一张图看懂整个生态：五层抽象金字塔](#1-一张图看懂整个生态五层抽象金字塔)
- [2. L4：Python DSL——与 Triton 同赛道的选手](#2-l4python-dsl与-triton-同赛道的选手)
- [3. L3：C++ 模板库——写更快 kernel 的"零件"](#3-l3c-模板库写更快-kernel-的零件)
- [4. L2：官方封装库——AI 90% 场景其实在用它](#4-l2官方封装库ai-90-场景其实在用它)
- [5. L5：图级编译器——一行加速整张模型](#5-l5图级编译器一行加速整张模型)
- [6. 特殊/跨平台生态：AMD、Intel、图形、仿真](#6-特殊跨平台生态amdintel图形仿真)
- [7. 选型决策树：程序员该选哪个？](#7-选型决策树程序员该选哪个)
- [8. AI 工程师优先级 Top 10](#8-ai-工程师优先级-top-10)
- [9. 学习路线图（渐进式，8~12 周）](#9-学习路线图渐进式812-周)
- [10. 精选资源与官方链接](#10-精选资源与官方链接)

---

## 0. 写在最前：为什么先看"全景"，而不是直接扎进某个工具？

很多程序员一想学 GPU 编程，第一反应就是"买本 CUDA 书从头啃"或"抄一段 Triton 代码跑起来"。**这条路不能说错，但很容易走弯路**。原因有三：

1. **场景不匹配就会做无用功**——花两个月啃 CUDA 却发现自己的活用 `torch.compile` 一行就搞定；用 Triton 手写"矩阵乘"，永远不如直接 `torch.matmul` 调 cuBLAS 快；用 CUDA 写"数据预处理"，代码量是 CuPy 的 10 倍还慢。
2. **看不懂社区讨论**——PyTorch 群里聊 Inductor 后端、CUTLASS 3.x、Pallas、Warp，你会像听天书。
3. **架构决策做不了**——项目要选技术栈时，"用 Triton 还是 TensorRT-LLM？"、"要不要引入 CUTLASS？"这些问题只有懂全景的人才能拍板。

所以本文的策略是：**先花 1~2 小时看完这张地图**，明确"我该从哪一层、哪个工具切入"，再去精读对应的深度指南——效率至少提升 3 倍。

### 0.1 一句话总结整个生态

> **GPU 编程不是一门"技术"，而是一个"栈"**：从 PTX 汇编到 `torch.compile` 一行加速，有 5~6 个抽象层，每层都有明星工具，各司其职。

### 0.2 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **G1 认知** | 听到 CUTLASS / NCCL / CuPy / TVM 知道是干嘛的、在哪一层 |
| **G2 会挑** | 拿到新需求，能在 5 分钟内决定"该用哪个工具"，说得清理由 |
| **G3 会用** | 至少熟练使用 3 个层次的工具（如：`torch.compile` + Triton + CuPy + NCCL）|
| **G4 会评** | 能从性能、可维护性、部署难度多维度对比工具，做架构决策 |


---

## 0.3 姊妹篇速览：按抽象层与领域的 33 份深度指南（总入口）

本文是**全景导览**，配套的**每个工具**都有一份对应的深度学习指南（作者与本文相同、结构完全一致）。以下按**抽象层 + 领域**分组给出**总入口**——你可以从任何一份切入，也可以按学习路线图逐份精读。

### 0.3.1 一张分层地图

```
🎯 应用/框架 & 编译器（Python 层）
├─ Numba / CuPy / Triton / NVIDIA Warp        —— Python DSL 4 大工具
├─ torch.compile / TVM                        —— 编译器 2 兄弟
└─ MLIR                                       —— 编译器底座

🎯 训练与桥接层
├─ PyTorch 自定义 CUDA 算子                    —— Kernel↔Model 桥梁
└─ 大模型训练框架 (Megatron/DeepSpeed/FSDP)    —— 大模型训练三剑客

🔥 关键算子与工具（AI 时代地基）
├─ FlashAttention                             —— 大模型头号算子
├─ CUDA Graphs                                —— 干掉 launch 开销
└─ Nsight 性能分析                            —— GPU 优化 X 光机

🚀 LLM 推理框架（上层服务，开箱即用）
├─ TensorRT-LLM                              —— NVIDIA 官方，性能天花板
├─ vLLM                                       —— 开源事实标准，OpenAI 兼容
├─ SGLang                                     —— DSL + RadixAttention 新贵
└─ llama.cpp                                  —— 任意硬件包括 CPU/Mac/手机

🔷 C++ 高层库
├─ Thrust                                     —— STL-like
└─ cuCollections                              —— GPU 哈希/集合
🔶 C++ 中层原语
├─ CUB
└─ libcu++

🔴 C++ 底层专用
└─ CUTLASS

🟠 NVIDIA 核心运算库（9 份）
├─ cuBLAS / cuBLASLt
├─ cuSPARSE / cuSOLVER
├─ cuDNN / cuFFT / cuRAND
└─ NCCL / NVSHMEM

🌍 基础与全景
├─ 面向 AI 的 CUDA 编程学习指南
└─ GPU 编程工具全景（👈 你正在读）

🔬 贴硬层（看懂编译器、手写关键指令）
└─ PTX 汇编
```
### 0.3.2 33 份指南总表（按学习次序排列，点击直达）

> **排序原则**：从**易到难**、从**上层到底层**、从**"用别人的"到"自己造轮子"**。跟着这个顺序读，就是最平滑的学习曲线。

| # | 阶段 | 分组 | 工具 | 学习指南 | 一句话定位 |
|:--:|:--|:--|:--|:--|:--|
| **1** | **🌍 起点·建立地图** | 全景 | GPU 工具全景 | 本文 | 心智地图 & 选型总入口 |
| **2** | 🌍 起点·打好地基 | 基础 | CUDA | [面向 AI 的 CUDA 编程学习指南](./CUDA-AI编程学习指南.md) | 从零学面向 AI 的 CUDA（**必读**）|
| **3** | **🎯 上手·Python 直译** | Python DSL | CuPy | [CuPy编程学习指南](./CuPy编程学习指南.md) | NumPy 的 GPU 版（**最易入门**）|
| **4** | 🎯 上手·Python 直译 | Python DSL | Numba | [Numba编程学习指南](./Numba编程学习指南.md) | Python `@cuda.jit` 写 kernel |
| **5** | **🎯 上手·AI 主力** | Python DSL | Triton | [Triton编程学习指南](./Triton编程学习指南.md) | AI 融合算子事实标准 ⭐ |
| **6** | 🎯 上手·专用领域 | Python DSL | NVIDIA Warp | [NVIDIA-Warp编程学习指南](./NVIDIA-Warp编程学习指南.md) | 仿真/机器人/可微编程 |
| **7** | **🎯 加速·零门槛** | 编译器 | torch.compile | [torch.compile编程学习指南](./torch.compile编程学习指南.md) | PyTorch 2.x 一行加速 ⭐ |
| **8** | 🎯 加速·跨平台 | 编译器 | TVM (Unity) | [TVM编程学习指南](./TVM编程学习指南.md) | 一份模型跑任意硬件 |
| **9** | **🔗 桥梁·接入模型** | 桥接层 | PyTorch 自定义算子 | [PyTorch自定义CUDA算子学习指南](./PyTorch自定义CUDA算子学习指南.md) | Kernel↔Model 最后一公里 ⭐ |
| **10** | **🔬 优化·必备工具** | 剖析工具 | Nsight | [Nsight性能分析学习指南](./Nsight性能分析学习指南.md) | GPU 优化的 X 光机 ⭐ |
| **11** | **⚡ 加速·干掉 launch** | 性能杀器 | CUDA Graphs | [CUDA-Graphs学习指南](./CUDA-Graphs学习指南.md) | 小 kernel 场景神器 |
| **12** | **🔥 算子·大模型地基** | 关键算子 | FlashAttention | [FlashAttention源码学习指南](./FlashAttention源码学习指南.md) | 大模型时代头号算子 ⭐ |
| **13** | **🚀 应用·一行起服务** | LLM 推理 | vLLM | [vLLM编程学习指南](./vLLM编程学习指南.md) | 开源推理事实标准 ⭐ |
| **14** | 🚀 应用·共享前缀王者 | LLM 推理 | SGLang | [SGLang编程学习指南](./SGLang编程学习指南.md) | DSL + RadixAttention 新贵 || **15** | 🚀 应用·极致性能 | LLM 推理 | TensorRT-LLM | [TensorRT-LLM编程学习指南](./TensorRT-LLM编程学习指南.md) | NVIDIA 推理性能天花板 |
| **16** | 🚀 应用·本地/边缘 | LLM 推理 | llama.cpp | [llama.cpp编程学习指南](./llama.cpp编程学习指南.md) | 任意硬件/本地/离线 |
| **17** | **🏋️ 训练·大模型三剑客** | 训练框架 | Megatron/DeepSpeed/FSDP | [大模型训练框架学习指南](./大模型训练框架学习指南.md) | 训练 7B~千亿必备 ⭐ |
| **18** | **🟠 常用·线代必学** | 运算库 | cuBLAS | [cuBLAS编程学习指南](./cuBLAS编程学习指南.md) | 稠密线性代数（GEMM 入口）|
| **19** | 🟠 常用·融合 & FP8 | 运算库 | cuBLASLt | [cuBLASLt编程学习指南](./cuBLASLt编程学习指南.md) | 融合 epilogue + FP8 |
| **20** | 🟠 常用·DL 必学 | 运算库 | cuDNN | [cuDNN编程学习指南](./cuDNN编程学习指南.md) | 深度学习原语（Conv/Attention）|
| **21** | 🟠 常用·多卡通信 | 运算库 | NCCL | [NCCL编程学习指南](./NCCL编程学习指南.md) | 多卡多机集合通信 |
| **22** | 🟠 细分·随机数 | 运算库 | cuRAND | [cuRAND编程学习指南](./cuRAND编程学习指南.md) | 高性能随机数 |
| **23** | 🟠 细分·FFT | 运算库 | cuFFT | [cuFFT编程学习指南](./cuFFT编程学习指南.md) | 快速傅里叶变换 |
| **24** | 🟠 细分·稀疏矩阵 | 运算库 | cuSPARSE | [cuSPARSE编程学习指南](./cuSPARSE编程学习指南.md) | 稀疏矩阵 |
| **25** | 🟠 细分·数值求解 | 运算库 | cuSOLVER | [cuSOLVER编程学习指南](./cuSOLVER编程学习指南.md) | LU/QR/SVD 求解器 |
| **26** | 🟠 高级·GPU 直通信 | 运算库 | NVSHMEM | [NVSHMEM编程学习指南](./NVSHMEM编程学习指南.md) | GPU 一侧通信 (PGAS) |
| **27** | **🔷 造轮·STL 手感** | C++ 高层 | Thrust | [Thrust编程学习指南](./Thrust编程学习指南.md) | GPU 版 STL |
| **28** | 🔷 造轮·数据结构 | C++ 高层 | cuCollections | [cuCollections编程学习指南](./cuCollections编程学习指南.md) | GPU 哈希表/集合 |
| **29** | **🔶 造轮·并行原语** | C++ 中层 | CUB | [CUB编程学习指南](./CUB编程学习指南.md) | Block/Warp/Device 级原语 |
| **30** | 🔶 造轮·标准库 | C++ 中层 | libcu++ | [libcu++编程学习指南](./libcu++编程学习指南.md) | GPU 版 C++ 标准库 |
| **31** | **🔴 造轮·极致 GEMM** | C++ 底层 | CUTLASS | [CUTLASS编程学习指南](./CUTLASS编程学习指南.md) | GEMM/Conv 模板乐高 |
| **32** | **🧬 底座·下一代编译器** | 编译器底座 | MLIR | [MLIR编译器底座学习指南](./MLIR编译器底座学习指南.md) | Triton/Mojo/IREE 的地基 |
| **33** | **🔬 贴硬·虚拟汇编** | GPU 汇编 | PTX | [PTX 汇编编程学习指南](./PTX%20%E6%B1%87%E7%BC%96%E7%BC%96%E7%A8%8B%E5%AD%A6%E4%B9%A0%E6%8C%87%E5%8D%97.md) | 看懂编译器/CUTLASS/FlashAttention 的只眼 |

**⭐ = 高价值必读（7 份）**：**Triton**（AI 融合算子）、**torch.compile**（一行加速）、**PyTorch 自定义算子**（接入模型）、**Nsight**（性能剖析）、**FlashAttention**（头号算子）、**vLLM**（推理首选）、**大模型训练框架**（训练必备）—— 这 7 份是所有 AI 工程师**投入产出比最高**的核心站点。

**六大阶段的分水岭**：

- **📗 起步（1~2）**：先看懂全景 + 打好 CUDA 心智模型，**不写代码只建认知**；
- **📘 上手（3~8）**：Python DSL + 编译器 —— **90% 的 AI 工程师停在这一层就够用**；
- **🔧 桥接（9~12）**：让 kernel 变成模型一等公民 + 会剖析会调优 + 精通头号算子 —— **AI Kernel 工程师核心竞争力**；
- **📙 应用（13~17）**：LLM 推理框架 + 训练框架 —— **调库/框架工程师的看家本领**；
- **🟠 库·细分（18~26）**：NVIDIA 官方运算库全家桶 —— **按需查阅**；
- **📕 深入（27~33）**：C++ 高/中/底层库 + MLIR + PTX —— **想成为造轮子的芯片/内核/编译器工程师才需要**。

### 0.3.3 推荐 5 条切入路线

- **AI 训练工程师**：CUDA → PyTorch → **torch.compile** → **Triton** → **PyTorch 自定义算子** → **Nsight** → **大模型训练框架**；
- **AI 推理工程师**：**Nsight** → **FlashAttention** → **CUDA Graphs** → **vLLM** → **SGLang** → **TensorRT-LLM** → **llama.cpp**；
- **AI Kernel 工程师**：CUDA → **Triton** → **PyTorch 自定义算子** → **FlashAttention** → CUTLASS → **PTX** → **Nsight**；
- **端侧/跨平台部署**：ONNX → **TVM** → **MLIR** → BYOC 接自研硬件；
- **编译器/芯片工程师**：CUDA → CUTLASS → CUB → libcu++ → **PTX** → **MLIR** → TVM Unity。
> **提示**：本节只是**总入口**，具体每一份指南的选型建议见后续的第 2~8 章。

---

## 1. 一张图看懂整个生态：五层抽象金字塔

### 1.1 全景金字塔

```
                    抽象层级（越高越"傻瓜"，越低越"贴硬件"）
                             ▲
                             │
   ┌─────────────────────────┴─────────────────────────┐
   │  L5: 图级编译器（端到端模型加速，无需写 kernel）        │  torch.compile / TVM / XLA / TensorRT
   ├───────────────────────────────────────────────────┤
   │  L4: Python DSL（用 Python 写单个 kernel）           │  Triton / Numba / CuPy / Warp / Pallas
   ├───────────────────────────────────────────────────┤
   │  L3: C++ 模板库（高性能算子零件）                     │  CUTLASS / Thrust / CUB / libcu++
   ├───────────────────────────────────────────────────┤
   │  L2: 官方封装库（调 API 即可）                        │  cuBLAS / cuDNN / cuSPARSE / NCCL
   ├───────────────────────────────────────────────────┤
   │  L1: CUDA C++（手写 kernel）                        │  原生 CUDA Runtime / Driver API
   ├───────────────────────────────────────────────────┤
   │  L0: PTX / SASS（汇编级）                            │  极致优化才碰
   └───────────────────────────────────────────────────┘
                             │
                             ▼
                          贴近硬件
```

### 1.2 一句话记住每一层的"性格"

| 层 | 性格 | 关键词 | 谁在用 |
|:--|:--|:--|:--|
| **L5** | 懒人福音，一行加速 | 图优化、算子融合、自动生成 | 应用层 AI 工程师 |
| **L4** | Python 党的春天 | JIT、块级编程、生产力 | AI Kernel 工程师 |
| **L3** | 造轮子的零件仓库 | 模板、组合、性能可控 | 底层库作者 |
| **L2** | NVIDIA 官方轮子 | 稳定、极致、闭源 | 所有人（隐式使用）|
| **L1** | 硬核手艺 | 灵活、可控、繁琐 | 硬核工程师 |
| **L0** | 汇编级极限 | 抠周期、抠寄存器 | 极少数专家 |

### 1.3 你现在在哪一层？

- 会用 PyTorch → **默认在 L5**（`torch.matmul` 背后是 cuBLAS，你没意识到）；
- 会写 Triton kernel → **L4**；
- 会写 CUDA C++ + `__shared__` → **L1**；
- 会看 CUTLASS 源码 → **L3**；
- 会调 PTX → **L0**（膜拜）。

**理想的 AI 工程师**：**L1 + L4 + L5 都要会，L2 要熟，L3 能读**。

### 1.4 五层之外的"横切工具"

上面的金字塔是**纵向**的抽象分层，但真实工程里还有一批**横向切一刀**的关键工具，它们不属于某一层，而是**贯穿所有层**：

| 横切维度 | 关键工具 | 定位 | 对应指南 |
|:--|:--|:--|:--|
| **性能剖析** | Nsight Systems / Compute | 从 L5 到 L0 都要用 | [Nsight性能分析学习指南](./Nsight性能分析学习指南.md) |
| **Launch 优化** | CUDA Graphs | 打包多层小 kernel | [CUDA-Graphs学习指南](./CUDA-Graphs学习指南.md) |
| **头号算子** | FlashAttention | L1~L4 都有实现 | [FlashAttention源码学习指南](./FlashAttention源码学习指南.md) |
| **Kernel↔Model 桥梁** | PyTorch 自定义算子 | 把 L1/L4 接入 L5 | [PyTorch自定义CUDA算子学习指南](./PyTorch自定义CUDA算子学习指南.md) |
| **训练框架** | Megatron/DeepSpeed/FSDP | 建立在 L2 (NCCL) + L5 之上 | [大模型训练框架学习指南](./大模型训练框架学习指南.md) |
| **编译器底座** | MLIR | Triton (L4) / TVM (L5) 的地基 | [MLIR编译器底座学习指南](./MLIR编译器底座学习指南.md) |

> **一句话**：**纵轴挑"用哪个抽象层"，横轴挑"哪个环节最需要优化"**——两根轴齐备，才是完整的 GPU 工程师工具箱。

---

## 2. L4：Python DSL——用 Python 写 GPU kernel 的四大门派

这一层是**程序员进入 GPU 世界最友好的入口**——**用 Python 写 GPU kernel**，不用碰 C++、不用管指针。四个工具虽然风格各异，但套路相通：**先学会其中任意一个，其他三个都能分分钟上手**。

### 2.1 五强对比表

| 工具 | 出品方 | 抽象粒度 | 优势 | 劣势 | 定位一句话 |
|:--|:--|:--|:--|:--|:--|
| **Triton** | OpenAI | Block-level | 性能高、生态最大、`torch.compile` 后端 | Windows 支持差、只做 NVIDIA | **AI 算子首选** |
| **Numba** | Anaconda | Thread-level | 语法就是 Python + CUDA 直译，最易入门 | 性能上限低于 Triton | **CUDA 的 Python 翻译** |
| **CuPy** | Preferred Networks | Array-level | API 和 NumPy 100% 兼容，零学习成本 | 只是"调现成 kernel"，写不了融合 | **NumPy 的 GPU 版** |
| **NVIDIA Warp** | NVIDIA | Kernel + 可微 | 支持可微编程、几何/物理原语 | AI 圈用得少 | **仿真/机器人首选** |
| **JAX + Pallas** | Google | Block-level（仿 Triton）| JAX 无缝、TPU/GPU 双支持 | 只在 JAX 圈流行 | **JAX 版 Triton** |
| **Mojo** 🔥 | Modular | 语言级 | Python 超集、性能媲美 C++、支持 MLIR | 生态早期 | **押注下一代 Python** |

### 2.2 什么时候用哪个？

- **写 AI 融合算子** → **Triton**（不用犹豫）；
- **快速做实验/科研原型** → **Numba**（`@cuda.jit` 就是 CUDA 的 Python 翻译）；
- **数据预处理/后处理** → **CuPy**（把 `import numpy as np` 改成 `import cupy as np`）；
- **物理仿真、机器人、可微渲染** → **Warp**；
- **在 JAX 里写自定义 kernel** → **Pallas**；
- **想赌未来 5 年的技术方向** → **Mojo**（谨慎观望）。

### 2.3 Numba 示例（vs Triton 对照）

```python
# Numba：Thread-level（和 CUDA 一样，一个线程处理一个元素）
from numba import cuda

@cuda.jit
def vector_add_numba(a, b, c):
    i = cuda.grid(1)
    if i < a.size:
        c[i] = a[i] + b[i]

# 调用（和 CUDA 一样管 grid/block）
vector_add_numba[(1024,), (256,)](a, b, c)
```

对比 Triton（Block-level）：

```python
# Triton：Block-level（一个 program 处理一块数据）
@triton.jit
def vector_add_triton(a_ptr, b_ptr, c_ptr, N, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    mask = offs < N
    a = tl.load(a_ptr + offs, mask=mask)
    b = tl.load(b_ptr + offs, mask=mask)
    tl.store(c_ptr + offs, a + b, mask=mask)
```

**核心差异**：
- Numba：**一个线程一个元素**（心智模型 = CUDA）；
- Triton：**一个 program 一块数据**（心智模型 = NumPy 向量化）。

### 2.4 CuPy 示例（无脑替换 NumPy）

```python
import cupy as cp   # 唯一改动：import numpy as np → import cupy as cp

x = cp.random.randn(10000, 10000)
y = cp.random.randn(10000, 10000)
z = x @ y                # 底层自动调 cuBLAS
mean = z.mean(axis=0)    # 底层自动生成 kernel
```

**适用**：数据预处理、后处理、非 AI 的科学计算——**不用写任何 kernel**。

---

## 3. L3：C++ 模板库——写更快 kernel 的"零件"

这一层不像 Triton 那样"替代 CUDA"，而是**让你在 CUDA C++ 里少造轮子**。写生产级高性能库（FlashAttention、TensorRT-LLM、vLLM）几乎都要用到。

### 3.1 五大主力

| 工具 | 出品方 | 定位 | 典型用途 |
|:--|:--|:--|:--|
| **CUTLASS** | NVIDIA | 高性能 GEMM/Conv 模板库 | FlashAttention、TensorRT-LLM 内部大量使用 |
| **Thrust** | NVIDIA | GPU 版 STL（`sort` / `reduce` / `scan`）| 数据处理、图算法、非 AI 场景 |
| **CUB** | NVIDIA | Block/Warp/Device 级 primitive | 手写 kernel 时的 reduction/scan 组件 |
| **cuCollections** | NVIDIA | GPU 上的哈希表、集合 | 推荐系统、图计算、去重 |
| **libcu++** | NVIDIA | GPU 版 C++ 标准库 | `cuda::std::atomic`、`cuda::std::chrono` 直接跑 GPU |

### 3.2 CUTLASS 是啥？为什么重要？

**一句话**：**NVIDIA 开源的"GEMM 乐高积木"**——你想写一个 GEMM 变体（如 `fp8 GEMM + gelu + bias`），不用从零手写 tile / async copy / mma 指令，直接用 CUTLASS 模板拼一个。

**为什么重要**：
- FlashAttention v2/v3 的 CUDA 版就是 CUTLASS 写的；
- TensorRT-LLM、cuBLASLt、xFormers 的 dense kernel 底层都是 CUTLASS；
- **想读 SOTA 算子源码，绕不开 CUTLASS**。

**学习曲线**：非常陡（C++ 模板嵌套 5 层是常态），但读懂了收益极大。

### 3.3 Thrust / CUB 示例

```cpp
// Thrust：GPU 版 STL，一行搞定 sort
#include <thrust/device_vector.h>
#include <thrust/sort.h>

thrust::device_vector<int> d(1000000);
thrust::sort(d.begin(), d.end());   // 底层调 CUB 的 radix sort

// CUB：手写 kernel 时用作 reduction 组件
#include <cub/cub.cuh>
__global__ void my_kernel(...) {
    typedef cub::BlockReduce<float, 256> BlockReduce;
    __shared__ typename BlockReduce::TempStorage temp;
    float sum = BlockReduce(temp).Sum(thread_data);
}
```

---

## 4. L2：官方封装库——AI 90% 场景其实在用它

**残酷真相**：作为 AI 工程师，你 90% 的时间根本**不用写 kernel**，直接调这些官方库就够——它们的性能被 NVIDIA 内部团队抠到极致，你手写 99% 追不上。

### 4.1 核心库速查表

| 库 | 用途 | 你什么时候会"隐式"用到？ |
|:--|:--|:--|
| **cuBLAS** | 稠密线性代数（GEMM、GEMV）| `torch.matmul` / `nn.Linear` |
| **cuBLASLt** | cuBLAS 增强版，支持 epilogue 融合 | 现代 PyTorch 的 Linear + bias + gelu 融合 |
| **cuDNN** | 深度学习原语（Conv、RNN、LayerNorm、Attention）| `nn.Conv2d` / `F.scaled_dot_product_attention` |
| **cuSPARSE** | 稀疏矩阵 | 图神经网络、剪枝模型 |
| **cuFFT** | 快速傅里叶变换 | `torch.fft` / 音频/图像处理 |
| **cuRAND** | 高性能随机数 | `torch.randn` 在 GPU 上的实现 |
| **cuSOLVER** | 线性代数求解器（LU、QR、SVD）| `torch.linalg.svd` |
| **NCCL** | 多卡通信（AllReduce、Broadcast）| **DDP / FSDP / DeepSpeed / Megatron 全部依赖** |
| **NVSHMEM** | 一侧通信（GPU 直接读写远端 GPU）| 大模型训练前沿框架 |

### 4.2 什么时候必须直接调它们？

- **训练大模型（多卡/多机）** → **NCCL 必学**（否则你不知道 AllReduce 卡在哪）；
- **自定义融合算子的 Fallback** → 用 cuBLAS/cuDNN 做基线对比；
- **非 AI 场景**（比如金融、CFD）→ 直接 cuBLAS/cuSOLVER 拉满。

### 4.3 NCCL 示例（PyTorch 里的隐式使用）

```python
import torch.distributed as dist
dist.init_process_group(backend='nccl')      # ← 就是这里
model = DDP(model)                            # 底层 AllReduce 走 NCCL
```

**关键概念**：AllReduce、Broadcast、Ring / Tree 拓扑、NVLink vs PCIe——**训大模型必懂**。

---

## 5. L5：图级编译器——一行加速整张模型

不需要你写任何 kernel，**给一个模型、自动全图优化 + 算子融合 + 生成 kernel**。这是"性价比最高"的一层。

### 5.1 四大主力

| 工具 | 出品方 | 定位 | 底层后端 | 一句话 |
|:--|:--|:--|:--|:--|
| **torch.compile** (Inductor) | PyTorch | 一行加速，Python 原生 | **生成 Triton kernel** | 白嫖 Triton 的性能 |
| **TVM** | Apache | 跨硬件（GPU/CPU/NPU）编译器 | 自研 | 学术界宠儿，工业落地重 |
| **XLA** | Google | JAX/TF 的编译器 | 自研（HLO）| Google 全家桶必备 |
| **TensorRT / TensorRT-LLM** | NVIDIA | 推理专用，工业级最快 | 闭源 | NVIDIA 推理事实标准 |

### 5.2 `torch.compile` 是啥"魔法"？

```python
model = MyModel().cuda()
model = torch.compile(model)   # ← 就这一行
```

**背后发生了什么？**
1. **图捕获**：TorchDynamo 把 Python 代码翻成计算图；
2. **算子融合**：Inductor 把连续的 element-wise、reduction 融合成一个 kernel；
3. **代码生成**：Inductor **自动生成 Triton kernel**；
4. **JIT 编译**：Triton 把 Python DSL 编译成 PTX，运行时执行。

**收益**：训练/推理常见 **10%~50% 加速**，大模型场景常见 **2x**。

### 5.3 TensorRT-LLM：LLM 推理事实标准

- 输入 HuggingFace 模型 → 输出高度优化的推理引擎；
- 内置 FlashAttention、Paged KV Cache、Continuous Batching、In-flight Batching；
- 底层大量使用 **CUTLASS**；
- 竞品：**vLLM**（开源、灵活）、**SGLang**（新贵）、**LMDeploy**（中文社区活跃）。

> **深入阅读**：LLM 推理 4 大框架各有专文—— [TensorRT-LLM](./TensorRT-LLM编程学习指南.md) / [vLLM](./vLLM编程学习指南.md) / [SGLang](./SGLang编程学习指南.md) / [llama.cpp](./llama.cpp编程学习指南.md)。

### 5.4 训练框架也是"图级"的思维

和 L5 推理侧对应的**训练侧**，也有一批"图/模型级"的框架——它们不是编译器，但同样**站在整张模型的视角**做优化：

- **DeepSpeed / FSDP**：切参数/梯度/优化器状态（ZeRO 系列），最省显存；
- **Megatron-LM**：切模型本身（Tensor/Pipeline/Sequence Parallel），极致性能；
- 三者常组合使用（Megatron-DeepSpeed 是训练 GPT-3 级别模型的标配）。

> **深入阅读**：[大模型训练框架学习指南](./大模型训练框架学习指南.md) —— DP/TP/PP/ZeRO 全解析。

---

## 6. 特殊/跨平台生态：AMD、Intel、图形、仿真

### 6.1 跨硬件（不绑 NVIDIA）

| 工具 | 出品方 | 定位 | 适用 |
|:--|:--|:--|:--|
| **HIP** | AMD | AMD 版 CUDA，源码级兼容 | 想在 AMD MI300 跑代码 |
| **oneAPI / DPC++** | Intel | Intel 主推的跨硬件方案 | Intel GPU / CPU 混合 |
| **SYCL** | Khronos | 跨平台异构标准 | AMD/Intel/NVIDIA 通吃 |
| **Kokkos / RAJA** | US National Labs | 跨平台并行 C++ 库 | HPC 科学计算圈 |
| **OpenCL** | Khronos | 老牌跨平台 | 移动端/嵌入式（AI 圈已凉）|

### 6.2 图形/仿真/科学计算

| 工具 | 出品方 | 定位 |
|:--|:--|:--|
| **NVIDIA HPC SDK / OpenACC** | NVIDIA | 用 `#pragma` 给 C/C++/Fortran 加 GPU |
| **Halide** | MIT | 图像/张量算子 DSL，图像处理圈老牌 |
| **Taichi** | Taichi Lang | 面向图形/仿真/可微编程的 Python DSL |
| **NVIDIA Warp** | NVIDIA | 面向仿真、机器人、可微渲染 |

---

## 7. 选型决策树：程序员该选哪个？

### 7.1 一分钟决策树

```
你的需求是什么？
    │
    ├─ 已有 PyTorch 模型想变快
    │     └─ torch.compile（一行搞定，先试再说）
    │
    ├─ 写个自定义算子（融合 / 稀疏 / 新颖计算）
    │     ├─ AI 场景 → Triton（首选）
    │     ├─ 只是简单 element-wise → Numba 也够
    │     └─ 要极致性能 / 用 fp8 / TMA → CUDA C++ + CUTLASS
    │
    ├─ 只用 NumPy 语法处理 GPU 数据
    │     └─ CuPy（换个 import 就完事）
    │
    ├─ 多卡 / 多机训练
    │     └─ NCCL（隐式在 DDP/FSDP 里，出问题必查）
    │
    ├─ 部署 LLM 推理
    │     ├─ 追极致 → TensorRT-LLM
    │     ├─ 求灵活 → vLLM / SGLang
    │     └─ 求便宜 → llama.cpp（CPU/低端 GPU）
    │
    ├─ 跨硬件（要跑 AMD/Intel）
    │     └─ SYCL / Kokkos / HIP
    │
    └─ 物理仿真、机器人、可微渲染
          └─ NVIDIA Warp / Taichi
```

### 7.2 三个"反直觉"忠告

1. **别一上来就 Triton**——先试 `torch.compile`，往往免费拿到 30% 加速；
2. **别一上来就手写 CUDA**——先看 cuBLAS/cuDNN/cuSPARSE 有没有现成的；
3. **别忽略 NCCL**——多卡训练卡在通信上的比卡在计算上的多得多。

---

## 8. AI 工程师优先级 Top 10

按**投入产出比**排序，作为程序员切入 AI 加速建议按这个顺序：

| 优先级 | 工具 | 学习时长 | 收益 | 建议路径 |
|:--|:--|:--|:--|:--|
| ⭐⭐⭐⭐⭐ | **torch.compile** | 1 天 | 白嫖性能，几乎零成本 | 官方教程 + 自己模型试 |
| ⭐⭐⭐⭐⭐ | **Nsight 性能分析** | 1~2 周 | 所有 GPU 优化的入口 | [Nsight性能分析学习指南](./Nsight性能分析学习指南.md) |
| ⭐⭐⭐⭐⭐ | **Triton** | 4~6 周 | 写自定义算子事实标准 | [Triton编程学习指南](./Triton编程学习指南.md) |
| ⭐⭐⭐⭐⭐ | **PyTorch 自定义算子** | 1~2 周 | Kernel 接入模型必会 | [PyTorch自定义CUDA算子学习指南](./PyTorch自定义CUDA算子学习指南.md) |
| ⭐⭐⭐⭐⭐ | **FlashAttention** | 3~4 周 | 大模型时代必备内功 | [FlashAttention源码学习指南](./FlashAttention源码学习指南.md) |
| ⭐⭐⭐⭐ | **CUDA C++** | 8~12 周 | 打底功力，能读所有源码 | [面向 AI 的 CUDA 编程学习指南](./CUDA-AI编程学习指南.md) |
| ⭐⭐⭐⭐ | **大模型训练框架** | 4~6 周 | 训练方向必学 | [大模型训练框架学习指南](./大模型训练框架学习指南.md) |
| ⭐⭐⭐⭐ | **CUTLASS** | 4~8 周 | 想读 FlashAttention/TRT-LLM 源码必备 | 官方 examples + 泛读源码 |
| ⭐⭐⭐ | **CUDA Graphs** | 1 周 | LLM 推理优化必备 | [CUDA-Graphs学习指南](./CUDA-Graphs学习指南.md) |
| ⭐⭐⭐ | **MLIR** | 6~8 周 | 想搞自研编译器/DSL 必学 | [MLIR编译器底座学习指南](./MLIR编译器底座学习指南.md) |

### 8.1 建议的"三段式"学习路径

- **第一阶段（1~2 个月）**：`torch.compile` + **Nsight** + Triton + 基础 CUDA → **覆盖 80% 场景 + 学会剖析**；
- **第二阶段（2~4 个月）**：**PyTorch 自定义算子** + **FlashAttention 源码** + CUTLASS + NCCL → **能读懂 SOTA、能接入生产**；
- **第三阶段（长期）**：按需选一条深入——
  - 训练方向：**大模型训练框架**（Megatron/DeepSpeed/FSDP）；
  - 推理方向：**CUDA Graphs** + TensorRT-LLM / vLLM 源码；
  - 编译器方向：**MLIR** + TVM Unity + 自定义后端。

---

## 9. 学习路线图（渐进式，8~12 周）

### Week 1：认知打底
- 通读本文，画出自己的心智地图；
- 用 `torch.compile` 加速一个你手头的模型，测速对比；
- 阅读 [面向 AI 的 CUDA 编程学习指南](./CUDA-AI编程学习指南.md) 第 3 章（三层并行结构）。

### Week 2~5：Triton 主线
- 跟着 [Triton编程学习指南](./Triton编程学习指南.md) 走完前 7 章；
- 手写 vector add / softmax / GEMM，测速对比 PyTorch eager 和 cuBLAS。

### Week 6~8：CUDA 主线（如果还没写过）
- 跟着 [面向 AI 的 CUDA 编程学习指南](./CUDA-AI编程学习指南.md) 走完 CUDA C++ 部分；
- 关键：搞懂 shared memory、bank conflict、warp、occupancy。

### Week 9~10：桥接与调优
- **Nsight**：`nsys` + `ncu` 剖析你在 Week 2~8 写的 kernel，找到瓶颈；
- **PyTorch 自定义算子**：用 `torch.library` 把 Week 2~5 的 Triton kernel 接入 PyTorch，加 autograd；
- **CUDA Graphs**：找一段小 kernel 密集的代码（RL rollout / batch=1 推理），加 graph 提速。

### Week 11~12：深度选一个方向
根据兴趣选一个方向深挖：
- **推理方向** → **FlashAttention 源码** + TensorRT-LLM / vLLM 源码 + 部署一个 LLM；
- **训练方向** → **大模型训练框架**（NCCL + FSDP + Megatron 源码）；
- **底层方向** → CUTLASS 3.x + 读 FlashAttention v3 CUDA 版；
- **编译器方向** → **MLIR** + Triton 编译栈源码 + TVM Unity；
- **前沿方向** → Mojo / Pallas / Warp 三选一。

---

## 10. 精选资源与官方链接

### 10.1 L5：图级编译器
- **torch.compile**：<https://pytorch.org/docs/stable/torch.compiler.html>
- **TVM**：<https://tvm.apache.org/>
- **XLA**：<https://openxla.org/xla>
- **TensorRT**：<https://developer.nvidia.com/tensorrt>
- **TensorRT-LLM**：<https://github.com/NVIDIA/TensorRT-LLM>
- **vLLM**：<https://github.com/vllm-project/vllm>
- **SGLang**：<https://github.com/sgl-project/sglang>

### 10.2 L4：Python DSL
- **Triton**：<https://github.com/triton-lang/triton>
- **Triton 官方教程**：<https://triton-lang.org/main/getting-started/tutorials/index.html>
- **Numba CUDA**：<https://numba.readthedocs.io/en/stable/cuda/index.html>
- **CuPy**：<https://cupy.dev/>
- **NVIDIA Warp**：<https://github.com/NVIDIA/warp>
- **JAX Pallas**：<https://jax.readthedocs.io/en/latest/pallas/index.html>
- **Mojo**：<https://www.modular.com/mojo>
- **Taichi**：<https://github.com/taichi-dev/taichi>

### 10.3 L3：C++ 模板库
- **CUTLASS**：<https://github.com/NVIDIA/cutlass>
- **Thrust**：<https://github.com/NVIDIA/thrust>
- **CUB**：<https://github.com/NVIDIA/cub>
- **cuCollections**：<https://github.com/NVIDIA/cuCollections>
- **libcu++**：<https://github.com/NVIDIA/libcudacxx>

### 10.4 L2：官方封装库
- **cuBLAS / cuDNN 等 CUDA-X**：<https://developer.nvidia.com/gpu-accelerated-libraries>
- **NCCL**：<https://github.com/NVIDIA/nccl>
- **NVSHMEM**：<https://developer.nvidia.com/nvshmem>

### 10.5 L1：CUDA
- **CUDA C++ Programming Guide**：<https://docs.nvidia.com/cuda/cuda-c-programming-guide/>
- **CUDA Best Practices**：<https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/>
- **PTX ISA**：<https://docs.nvidia.com/cuda/parallel-thread-execution/>

### 10.6 跨硬件 / 特殊生态
- **HIP (AMD)**：<https://github.com/ROCm/HIP>
- **oneAPI / DPC++**：<https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html>
- **SYCL**：<https://www.khronos.org/sycl/>
- **Kokkos**：<https://github.com/kokkos/kokkos>
- **Halide**：<https://halide-lang.org/>
- **OpenACC**：<https://www.openacc.org/>

### 10.7 姊妹篇（完整 33 份指南索引，与 0.3.1 分层地图顺序一致）

**🌍 基础与全景**
- [面向 AI 的 CUDA 编程学习指南](./CUDA-AI编程学习指南.md)
- GPU 编程工具全景（本文）

**🎯 Python DSL & 编译器**
- [Numba 编程学习指南](./Numba编程学习指南.md)
- [CuPy 编程学习指南](./CuPy编程学习指南.md)
- [Triton 编程学习指南](./Triton编程学习指南.md)
- [NVIDIA Warp 编程学习指南](./NVIDIA-Warp编程学习指南.md)
- [torch.compile 编程学习指南](./torch.compile编程学习指南.md)
- [TVM 编程学习指南](./TVM编程学习指南.md)

**🔧 桥接与训练**
- [PyTorch 自定义 CUDA 算子学习指南](./PyTorch自定义CUDA算子学习指南.md)
- [大模型训练框架学习指南（Megatron/DeepSpeed/FSDP）](./大模型训练框架学习指南.md)

**🔥 关键算子与优化工具**
- [FlashAttention 源码学习指南](./FlashAttention源码学习指南.md)
- [CUDA Graphs 学习指南](./CUDA-Graphs学习指南.md)
- [Nsight 性能分析学习指南](./Nsight性能分析学习指南.md)

**🚀 LLM 推理框架**
- [vLLM 编程学习指南](./vLLM编程学习指南.md)
- [SGLang 编程学习指南](./SGLang编程学习指南.md)
- [TensorRT-LLM 编程学习指南](./TensorRT-LLM编程学习指南.md)
- [llama.cpp 编程学习指南](./llama.cpp编程学习指南.md)

**� NVIDIA 核心运算库**
- [cuBLAS 编程学习指南](./cuBLAS编程学习指南.md)
- [cuBLASLt 编程学习指南](./cuBLASLt编程学习指南.md)
- [cuDNN 编程学习指南](./cuDNN编程学习指南.md)
- [NCCL 编程学习指南](./NCCL编程学习指南.md)
- [cuRAND 编程学习指南](./cuRAND编程学习指南.md)
- [cuFFT 编程学习指南](./cuFFT编程学习指南.md)
- [cuSPARSE 编程学习指南](./cuSPARSE编程学习指南.md)
- [cuSOLVER 编程学习指南](./cuSOLVER编程学习指南.md)
- [NVSHMEM 编程学习指南](./NVSHMEM编程学习指南.md)

**🔷🔶🔴 C++ 库（高/中/底层）**
- [Thrust 编程学习指南](./Thrust编程学习指南.md)
- [cuCollections 编程学习指南](./cuCollections编程学习指南.md)
- [CUB 编程学习指南](./CUB编程学习指南.md)
- [libcu++ 编程学习指南](./libcu++编程学习指南.md)
- [CUTLASS 编程学习指南](./CUTLASS编程学习指南.md)

**🧬 编译器底座**
- [MLIR 编译器底座学习指南](./MLIR编译器底座学习指南.md)

**🔬 贴硬层（虚拟汇编）**
- [PTX 汇编编程学习指南](./PTX%20%E6%B1%87%E7%BC%96%E7%BC%96%E7%A8%8B%E5%AD%A6%E4%B9%A0%E6%8C%87%E5%8D%97.md)

---

**版权声明**：本文由汪亮（bertonwang）撰写，转载请注明出处。欢迎邮件（<47608843@qq.com>）交流勘误。

**一句话总结全文**：**GPU 编程不是"学 CUDA"或"学 Triton"，而是学会在整个 5 层生态里挑对工具**——`torch.compile` 白嫖性能、Triton 写算子、CUDA + CUTLASS 抠极限、NCCL 搞多卡、CuPy 处理数据。**懂全景的人，才能做架构决策**。
