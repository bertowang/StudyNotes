# CUTLASS 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：已经写过基本 CUDA C++、理解 grid/block/thread/warp 心智模型，想**吃透 GPU 上矩阵乘（GEMM）与卷积到底怎样打到峰值算力**、想读懂 cuBLAS/cuDNN 底层"到底做了什么"的 C++/CUDA 程序员。
> **目标**：4~6 周内，从"用 CUTLASS 跑第一个 GEMM"到"能自己组一个含 epilogue 融合的 fused GEMM、能读懂 CUTLASS 3.x 的 CuTe 抽象、能给 SM86/SM90 分别搭 kernel"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1** + CUTLASS **3.5+**（含 CuTe）+ CMake ≥ 3.19。

---

## 目录

- [0. 写在最前：为什么要学 CUTLASS？](#0-写在最前为什么要学-cutlass)
- [1. CUTLASS 是什么：一句话讲清 vs cuBLAS / vs Triton](#1-cutlass-是什么一句话讲清-vs-cublas--vs-triton)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. CUTLASS 的心智模型：分层 GEMM（Device→Kernel→Threadblock→Warp→Thread）](#3-cutlass-的心智模型分层-gemmdevice→kernel→threadblock→warp→thread)
- [4. 第一个 GEMM：`device::Gemm` 五分钟跑起来](#4-第一个-gemmdevicegemm-五分钟跑起来)
- [5. Epilogue 融合：GEMM + bias + ReLU 一把梭](#5-epilogue-融合gemm--bias--relu-一把梭)
- [6. CUTLASS 3.x 新范式：CuTe + CollectiveMainloop](#6-cutlass-3x-新范式cute--collectivemainloop)
- [7. Profiler 工具：一条命令测遍所有 kernel](#7-profiler-工具一条命令测遍所有-kernel)
- [8. 集成到 PyTorch / 自定义算子](#8-集成到-pytorch--自定义算子)
- [9. 性能分析：怎么知道 CUTLASS 到底跑得多快？](#9-性能分析怎么知道-cutlass-到底跑得多快)
- [10. 学习路线图（4~6 周）](#10-学习路线图46-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 CUTLASS？

作为已经写过 CUDA 的程序员，你可能会问：**cuBLAS 已经很快了，Triton 也能写 GEMM 了，为什么还要碰 CUTLASS？** 答案是三点：

1. **cuBLAS 是黑盒**——你没法在 GEMM 内部塞任何自定义融合（比如你想 `GEMM(A,B) + softmax + top-k` 在一个 kernel 里做完，cuBLAS 帮不了你）；
2. **Triton 抽象层太高**——你想控制 async copy、Tensor Core 的具体指令、CTA 之间的 barrier，Triton 就到头了；
3. **CUTLASS 才是 NVIDIA 官方"教你怎么写 GEMM"的答案**——cuBLAS/cuDNN 的很多算子内部就是 CUTLASS 或类 CUTLASS。

### 0.1 一句话对比

| 需求 | 用手写 CUDA | 用 cuBLAS | 用 Triton | **用 CUTLASS** |
|:--|:--|:--|:--|:--|
| 打到 A100/H100 峰值的 GEMM | 3000+ 行、天才级工程 | ✅ 一行 | ✅ 100 行 | **✅ 500 行模板拼装** |
| GEMM + bias + activation 融合 | 得自己写 | ❌ 黑盒 | ⚠️ 部分支持 | **✅ 官方 Epilogue** |
| 特定 layout（interleaved / groupwise） | 死磕 | ❌ | ⚠️ | **✅ Layout tag 组合** |
| 支持 FP8 / 稀疏 / Grouped GEMM | 自己写 | 部分支持 | 部分 | **✅ 官方一等公民** |
| 想学"GEMM 到底怎么写" | 无从下手 | 看不到 | 看不到 | **✅ 官方教材** |

### 0.2 CUTLASS 现在有多重要？

- **cuBLAS / cuDNN 的许多 kernel** 就是 CUTLASS 生成或 CUTLASS 家族的产物；
- **FlashAttention 3、Grouped GEMM、FP8 GEMM** 的 SOTA 参考实现都是 CUTLASS；
- **PyTorch 的 `_scaled_mm`（FP8 矩阵乘）、Triton 的部分 tile-level 原语**背后都借鉴或直接用了 CUTLASS/CuTe；
- **Hopper（H100）与 Blackwell（B200）的新特性**（TMA、WGMMA、cluster launch、DSMEM）——CUTLASS 是**唯一给出完整开源示例**的库。

**一句话**：**要想真正理解"GPU 上矩阵乘为什么这样写"，绕不开 CUTLASS**；要想在 SM90+ 用满 WGMMA/TMA，CUTLASS 3.x + CuTe 目前是 C++ 世界的唯一答案。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **CT1 入门** | 会用 `cutlass::gemm::device::Gemm` 跑一个 FP16 GEMM，会改 tile size |
| **CT2 熟练** | 会写 Epilogue 融合（bias + activation + scaling），会用 profiler 找最优配置 |
| **CT3 高阶** | 会用 CUTLASS 3.x 的 CuTe / CollectiveMainloop，能针对 SM86 / SM90 分开配 |
| **CT4 专家** | 能读改 GEMM Kernel 内部（Mainloop、pipeline、predication），能给 CUTLASS 提 PR |

**建议**：**1~2 周到 CT1**（能跑各种 dtype 的 GEMM）；**3~4 周到 CT2**（能写融合 Epilogue）；**CT3 已能干实际工程**。

---

## 1. CUTLASS 是什么：一句话讲清 vs cuBLAS / vs Triton

### 1.1 CUTLASS 的定义

> **CUTLASS（CUDA Templates for Linear Algebra Subroutines）是 NVIDIA 官方开源的 C++ 模板库**，把 GPU 上 GEMM/卷积从 "device → kernel → threadblock → warp → thread" 五个层级抽象成可组合的 C++ 模板。你不是"写一个 GEMM"，而是"从模板货架上挑组件拼一个 GEMM"。

关键三点：

1. **C++ 模板库** —— 全 header-only（3.x 部分带编译组件），编译时决定所有 tile size / dtype / layout；
2. **分层抽象** —— 每一层都对应硬件的一个层级（SM → warp → mma 指令），与 GPU 硬件一一映射；
3. **NVIDIA 官方样例** —— 100+ examples，从最简 GEMM 到 FP8 / 稀疏 / grouped / FlashAttention 都有。

### 1.2 CUTLASS vs cuBLAS vs Triton

| 维度 | cuBLAS | Triton | **CUTLASS** |
|:--|:--|:--|:--|
| 抽象层级 | 库 API | Block-level DSL | **五层模板（device → thread）** |
| 语言 | C API | Python DSL | **C++ 模板** |
| 开放性 | 黑盒 | 开源 | **开源，可魔改** |
| Epilogue 融合 | 有限（bias/relu）| 一定程度 | **强项：任意组合** |
| SM90 新特性（TMA/WGMMA）| ✅ | 逐步支持 | **✅ 一等公民** |
| Windows 支持 | ✅ | ⚠️ | **✅ 完美** |
| 学习曲线 | 极低 | 中 | **陡** |
| 目标读者 | 用户 | AI 算法工程师 | **kernel 工程师 / 编译器开发者** |
| 生态定位 | 拿来用 | 写融合算子 | **搞懂 GPU 计算的底盘** |

**记忆口诀**：
- **只想跑 GEMM** → cuBLAS 一行；
- **想写 AI 融合算子** → Triton；
- **想吃透 GEMM 原理 + SM90 新特性 + 极致自定义** → CUTLASS。

### 1.3 一张图看清 CUTLASS 在栈里的位置

```
┌──────────────────────────────────────────────────────────┐
│  PyTorch / TensorFlow / JAX                              │
├──────────────────────────────────────────────────────────┤
│  cuBLAS / cuDNN / cuSPARSE  ← 内部大量使用 CUTLASS         │
├──────────────────────────────────────────────────────────┤
│  Triton / TVM / XLA          ← tile 抽象借鉴自 CUTLASS/CuTe│
├──────────────────────────────────────────────────────────┤
│  CUTLASS 3.x                                             │
│  ────────────────────────────────────────────────────    │
│  device::Gemm / kernel::GemmUniversal                    │
│  CollectiveMainloop + CollectiveEpilogue（3.x 新范式）    │
│  CuTe（Layout / Tensor / MMA / Copy Atoms）              │
├──────────────────────────────────────────────────────────┤
│  CUDA Runtime + PTX (mma.sync / wgmma / cp.async / TMA)  │
├──────────────────────────────────────────────────────────┤
│  GPU 硬件（Ampere SM86 / Hopper SM90 / Blackwell）        │
└──────────────────────────────────────────────────────────┘
```

**核心洞察**：CUTLASS 不是 "另一个 BLAS 库"，而是 **"教你怎么用模板从积木拼出峰值 GEMM 的样板工程"**。

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 平台选择

| 方案 | 难度 | 推荐度 |
|:--|:--|:--|
| **Linux 原生（推荐）** | 低 | ⭐⭐⭐⭐⭐ 首选 |
| **Windows + MSVC + CUDA** | 中 | ⭐⭐⭐⭐ |
| **WSL2** | 低 | ⭐⭐⭐⭐ |

CUTLASS 是 header-only 为主，跨平台良好，Windows 原生 MSVC 也能编，但 examples 的 CMake 在 Linux 上最顺。

### 2.2 一步获取

```bash
git clone --depth 1 https://github.com/NVIDIA/cutlass.git
cd cutlass
mkdir build && cd build

# 关键：CUTLASS_NVCC_ARCHS 要覆盖你的 SM
cmake .. -DCUTLASS_NVCC_ARCHS="86"          \
         -DCUTLASS_ENABLE_TESTS=OFF        \
         -DCUTLASS_ENABLE_PROFILER=ON      \
         -DCUTLASS_LIBRARY_KERNELS=all

make -j 8 cutlass_profiler
```

**参数说明**：
- `CUTLASS_NVCC_ARCHS="86"`：只编 Ampere 的（3060）；如果你有多张卡写 `"86;90"`；
- `CUTLASS_LIBRARY_KERNELS=all` 会编上千个 kernel，**编译时间可能超过 1 小时**——第一次试用建议限制成 `--kernels="sgemm_*"` 之类；
- Windows：换成 `cmake -G "Visual Studio 17 2022" -A x64 -T v143,cuda=12.1 ...` 然后用 MSBuild。

### 2.3 环境验证：跑官方 `basic_gemm` example

```bash
# 从 CUTLASS repo 根目录
cd examples/00_basic_gemm
mkdir build && cd build
cmake .. -DCUTLASS_NVCC_ARCHS="86"
make -j 8
./00_basic_gemm
```

期望输出（示意）：

```
Running basic GEMM: 5120 x 4096 x 4096
Runtime: 3.21 ms  Performance: 26.7 TFLOP/s
Passed
```

看到 `Passed` 就说明**驱动 + CUDA + CUTLASS + MSVC/GCC** 全部就位。

### 2.4 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| `nvcc fatal: Unsupported gpu architecture 'compute_86'` | CUDA 版本太老 | 升级到 CUDA 11.4+ |
| 编译爆内存（16GB 也不够） | 一次编太多 kernel | `-DCUTLASS_LIBRARY_KERNELS="sgemm_*"` 限制范围 |
| Windows MSVC 报模板深度超限 | MSVC 默认深度小 | 加 `/Zc:__cplusplus /std:c++17 /permissive-` |
| `undefined reference to cutlass::...` | 试图 lib 化 header-only 库 | CUTLASS 主体 header-only，直接 include |
| SM86 用了 SM90-only 的 API | 拿了 3.x 的 Hopper example | 换 `examples/00_basic_gemm` 这种通用样例 |

---

## 3. CUTLASS 的心智模型：分层 GEMM（Device→Kernel→Threadblock→Warp→Thread）

这是 CUTLASS **最核心的抽象**，理解了它就理解了一切。

### 3.1 五层结构

```
┌──────────────────────────────────────────────────────────┐
│ Device 层：整个 GPU 上的 GEMM 调用（host 侧）              │
│           cutlass::gemm::device::Gemm<...>                │
├──────────────────────────────────────────────────────────┤
│ Kernel 层：一次 kernel launch 内的调度、swizzle、K-loop    │
│           cutlass::gemm::kernel::GemmUniversal            │
├──────────────────────────────────────────────────────────┤
│ Threadblock 层：一个 CTA 处理的 tile（e.g. 128x128x32）    │
│           ThreadblockShape + Mma 主循环                   │
├──────────────────────────────────────────────────────────┤
│ Warp 层：一个 warp（32 thread）处理的 tile（e.g. 64x64x16）│
│           WarpShape + mma.sync 指令 tile                  │
├──────────────────────────────────────────────────────────┤
│ Thread / Instruction 层：单条 MMA 指令（e.g. 16x8x16 HMMA）│
│           InstructionShape                                │
└──────────────────────────────────────────────────────────┘
```

### 3.2 每一层做什么

| 层级 | 谁在跑 | 关键"形状" | 关键抽象 |
|:--|:--|:--|:--|
| Device | Host（1 次）| 全 GEMM shape (M,N,K) | `device::Gemm<>` |
| Kernel | 整张 GPU（1 次 launch）| Grid tile 分割 | `kernel::GemmUniversal` |
| Threadblock (CTA) | 1 个 CTA | `ThreadblockShape=<128,128,32>` | `Mma`（主循环）|
| Warp | 1 个 warp | `WarpShape=<64,64,16>` | Tensor Core 指令 tile |
| Instruction | 1 个 warp 的一条指令 | `InstructionShape=<16,8,16>` | `mma.sync`（Ampere HMMA）|

**乘法关系**（Ampere FP16 常用配置）：

```
ThreadblockShape = <128, 128, 32>
    ├─ 拆成 4 个 warp（2x2）
    │   WarpShape = <64, 64, 32>
    │       ├─ 每 warp 用多条 mma.sync
    │       │   InstructionShape = <16, 8, 16>   （Ampere HMMA.16816）
```

**理解要点**：**你选的每一层形状必须能被下一层整除**——这就是 CUTLASS 的"契约"。

### 3.3 为什么要五层？

- **Device**：让 host 侧一句话调用；
- **Kernel**：负责 CTA 的 swizzle（比如 threadblock 之间的 L2-friendly 排布）；
- **Threadblock**：**决定 shared memory 用多少**（比如 tile 128x128 就要 32KB shared）；
- **Warp**：**决定 register 用多少 + 走什么 Tensor Core 指令**；
- **Instruction**：直接映射硬件 MMA 指令，不同 SM 上不同（SM75 是 16x8x8, SM80 是 16x8x16, SM90 是 wgmma 64x256xk）。

**层数看似繁琐，但每层都对应硬件真实存在的东西**——这是 CUTLASS 相对 cuBLAS 的核心价值：**每一层都可以被你替换/魔改**。

---

## 4. 第一个 GEMM：`device::Gemm` 五分钟跑起来

### 4.1 完整可运行代码

```cpp
// basic_gemm.cu
#include <cutlass/gemm/device/gemm.h>
#include <cutlass/util/host_tensor.h>
#include <iostream>

using ElementA      = cutlass::half_t;   // FP16 输入
using ElementB      = cutlass::half_t;
using ElementC      = float;             // FP32 输出（累加）
using LayoutA       = cutlass::layout::RowMajor;
using LayoutB       = cutlass::layout::ColumnMajor;
using LayoutC       = cutlass::layout::RowMajor;

// 关键：五层形状全部显式指定
using Gemm = cutlass::gemm::device::Gemm<
    ElementA, LayoutA,
    ElementB, LayoutB,
    ElementC, LayoutC,
    float,                                          // Accumulator
    cutlass::arch::OpClassTensorOp,                 // 用 Tensor Core
    cutlass::arch::Sm80,                            // Ampere
    cutlass::gemm::GemmShape<128, 128, 32>,         // ThreadblockShape
    cutlass::gemm::GemmShape<64,  64,  32>,         // WarpShape
    cutlass::gemm::GemmShape<16,  8,  16>           // InstructionShape (HMMA.16816)
>;

int main() {
    int M = 5120, N = 4096, K = 4096;

    cutlass::HostTensor<ElementA, LayoutA> A({M, K});
    cutlass::HostTensor<ElementB, LayoutB> B({K, N});
    cutlass::HostTensor<ElementC, LayoutC> C({M, N});

    A.sync_device();
    B.sync_device();
    C.sync_device();

    Gemm gemm_op;
    Gemm::Arguments args({M, N, K},
        {A.device_data(), K},
        {B.device_data(), K},
        {C.device_data(), N},
        {C.device_data(), N},
        {1.0f, 0.0f});                              // alpha, beta

    cutlass::Status status = gemm_op(args);
    if (status != cutlass::Status::kSuccess) {
        std::cerr << "GEMM failed\n"; return 1;
    }
    cudaDeviceSynchronize();
    std::cout << "GEMM OK\n";
}
```

### 4.2 对照手写 CUDA 版，CUTLASS 省了什么

| 手写 CUDA 得做 | CUTLASS 版 |
|:--|:--|
| 自己分 tile / 算 threadblock/warp id | 模板参数指定形状后自动 |
| 手动 `cp.async` + double buffering | Mainloop 内建 pipeline |
| 手动 `mma.sync` PTX 或 wmma | InstructionShape 自动选 |
| 手写 shared memory swizzle 避 bank conflict | Layout tag + Iterator 自动 |
| 手写 epilogue（写回 + bias + relu）| `LinearCombination` 组件 |
| 处理边界 mask | Predicated Iterator 自动 |

**结论**：一个能打到 cuBLAS 80~95% 的 GEMM，CUTLASS 只要**几十行模板参数**。

### 4.3 编译命令（关键：`-arch=sm_86`）

```bash
nvcc -O3 -std=c++17 -arch=sm_86 \
     -I/path/to/cutlass/include \
     -I/path/to/cutlass/tools/util/include \
     basic_gemm.cu -o basic_gemm
./basic_gemm
```

### 4.4 小白也能懂：GEMM 代码逐段拆解

如果你只写过普通 CUDA vec add，第一次看 `device::Gemm<...>` 一堆模板会晕。这一节把每一处讲透。

#### 4.4.1 先看整体结构

```
┌───────────────────────────────────┐
│ ① 选类型 + 布局                    │  ElementA/B/C + LayoutA/B/C
├───────────────────────────────────┤
│ ② 用模板"拼"出一个 GEMM 类型        │  using Gemm = device::Gemm<...>
├───────────────────────────────────┤
│ ③ 准备 host/device 数据            │  HostTensor
├───────────────────────────────────┤
│ ④ 构造 Arguments 并调 gemm_op()    │
└───────────────────────────────────┘
```

#### 4.4.2 类型 + 布局：GEMM 就是 C = alpha*A*B + beta*C

- `ElementA/B/C`：分别是 A、B、C 的元素类型（FP16 输入、FP32 输出是深度学习最常见）；
- `LayoutA=RowMajor`、`LayoutB=ColumnMajor`：**行主 × 列主**在 CUTLASS 里是最常用组合（能让 B 的访存自然连续）；
- `Accumulator=float`：Tensor Core 内部累加用 FP32，避免精度损失。

#### 4.4.3 五层形状：GEMM 的灵魂

```cpp
GemmShape<128, 128, 32>   // ThreadblockShape：一个 CTA 算 128×128 的 C tile，每次沿 K 前进 32
GemmShape<64,  64,  32>   // WarpShape：一个 warp 算 64×64
GemmShape<16,  8,  16>    // InstructionShape：HMMA.16816（Ampere Tensor Core 原生指令）
```

- 一个 CTA 里正好 (128/64)×(128/64)=**4 个 warp** 干活；
- shared memory 需求 ≈ (128+128)×32×2B ≈ 16 KB（够用）；
- **改数字就能改配置**：想让每 CTA 4 个 warp 变 8 个？把 ThreadblockShape 变 `<256,128,32>`（前提是 shared memory 够、register 够）。

#### 4.4.4 `Arguments` 构造：喂数据 + 步长

```cpp
Gemm::Arguments args(
    {M, N, K},                        // 问题规模
    {A.device_data(), K},             // A 指针 + leading dim
    {B.device_data(), K},             // B 指针 + leading dim
    {C.device_data(), N},             // 输入 C（beta 用）
    {C.device_data(), N},             // 输出 D（这里 D=C，就地写）
    {1.0f, 0.0f}                      // alpha, beta：D = 1.0*A*B + 0.0*C
);
```

**要点**：CUTLASS 的 GEMM 一般写成 **D = α·A·B + β·C**，比 BLAS 通用。

#### 4.4.5 `gemm_op(args)`：底下发生了什么？

1. `gemm_op.can_implement(args)`：**编译期已保证形状能整除**，运行期只查 M/N/K 是否合规；
2. 计算 grid size = `(ceil(M/128), ceil(N/128), 1)`；
3. `cudaLaunchKernel(GemmKernel)`；
4. GPU 上：
   - CTA 从 GMEM 用 `cp.async` 把 A/B tile 搬到 shared memory；
   - 每 warp 用 `mma.sync.aligned.m16n8k16` 循环累加到 register；
   - Epilogue：把 register 里的 C tile 写回 GMEM。

#### 4.4.6 6 个新手常见坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | ThreadblockShape 除不尽 WarpShape | 编译期 static_assert 失败 | 保证整除关系 |
| 2 | InstructionShape 与 arch 不匹配 | 报 `unsupported mma instruction` | SM80 用 16x8x16，SM75 用 16x8x8 |
| 3 | LayoutA/B 反了 | 结果全错 | RowMajor 的 stride=cols，ColumnMajor 的 stride=rows |
| 4 | 忘 `sync_device()` | 结果是老 CPU 值 | 每次改 host 数据后同步 |
| 5 | 编译爆内存 | 模板实例化太多 | 单文件编 1 个 kernel，别一次编全套 |
| 6 | 3060 上跑 SM90 example | 报 `unsupported architecture` | 换 SM80 版 example |

---

## 5. Epilogue 融合：GEMM + bias + ReLU 一把梭

这是 CUTLASS **相对 cuBLAS 的最大杀手锏**——**在 GEMM 结果写回显存前，直接在 register 里做后处理**。

### 5.1 场景

深度学习里非常常见：`Y = ReLU(A * B + bias)`。cuBLAS 你得先 GEMM 出 `A*B`，再启一个 kernel 做 `+bias`，再启一个做 `ReLU`——**三次显存往返**。CUTLASS 一把梭：**GEMM 结果不出 register 就完成 bias + activation**。

### 5.2 用 `LinearCombinationRelu`

```cpp
#include <cutlass/epilogue/thread/linear_combination_relu.h>

using Epilogue = cutlass::epilogue::thread::LinearCombinationRelu<
    ElementC,                       // 输出类型
    128 / cutlass::sizeof_bits<ElementC>::value,   // 向量化写回宽度
    float,                          // 累加器类型
    float                           // 计算类型
>;

using Gemm = cutlass::gemm::device::Gemm<
    ElementA, LayoutA,
    ElementB, LayoutB,
    ElementC, LayoutC,
    float,
    cutlass::arch::OpClassTensorOp,
    cutlass::arch::Sm80,
    cutlass::gemm::GemmShape<128, 128, 32>,
    cutlass::gemm::GemmShape<64,  64,  32>,
    cutlass::gemm::GemmShape<16,  8,  16>,
    Epilogue                        // ← 关键：塞进来
>;
```

### 5.3 CUTLASS 自带的常用 Epilogue

| Epilogue | 作用 |
|:--|:--|
| `LinearCombination` | `D = α*C + β*Bias` |
| `LinearCombinationRelu` | 上面 + `ReLU` |
| `LinearCombinationGelu` | + `GELU` |
| `LinearCombinationClamp` | + `clamp(min,max)`（int8 量化必备）|
| `LinearCombinationDequant` | int8 反量化到 FP |
| Custom Epilogue | 你自己写一个 functor |

### 5.4 自定义 Epilogue（简版模板）

```cpp
template <typename T>
struct MyEpilogue {
    CUTLASS_HOST_DEVICE
    T operator()(T accum, T bias) const {
        T x = accum + bias;
        return x * (T)(x > (T)0);      // ReLU
    }
};
```

**只要能表达成"逐元素 functor"，就能塞进 Epilogue**——这一点直接让 CUTLASS 打赢了 cuBLAS 的组合场景。

---

## 6. CUTLASS 3.x 新范式：CuTe + CollectiveMainloop

**这是 CUTLASS 未来 5 年的方向**（Hopper 后主推）。

### 6.1 CuTe 是什么

> CuTe（**Cu**da **Te**nsors and Layouts）是 CUTLASS 3.x 的底层核心库，用**统一的 Layout 抽象**表达数据在 GMEM/SMEM/RMEM 中的排布。

**关键抽象**：

- `Layout`：由 **shape + stride** 描述一个多维索引空间；
- `Tensor`：数据指针 + Layout；
- `Copy Atom`：一次拷贝的"原子"（cp.async / TMA / ldmatrix）；
- `MMA Atom`：一条 MMA 指令（mma.sync / wgmma）。

**为什么要引入 CuTe？**：Ampere 之前的 CUTLASS 2.x 用 `Iterator + Fragment` 表达，写自定义 kernel 极其痛苦；CuTe 用**统一的 Layout 代数**（`composition`, `tiled_divide`, `logical_divide`）让 shape 变换像玩乐高。

### 6.2 CollectiveMainloop（3.x 的主循环抽象）

```cpp
using CollectiveMainloop = cutlass::gemm::collective::CollectiveMma<
    cutlass::gemm::MainloopSm80CpAsyncMultistage<3>,   // 3-stage pipeline
    TileShape,
    ElementA, StrideA,
    ElementB, StrideB,
    TiledMma,                       // CuTe 定义的 MMA tiling
    GmemTiledCopyA,                 // GMEM → SMEM 拷贝原子
    SmemLayoutAtomA,                // SMEM layout
    SmemCopyAtomA,                  // SMEM → RMEM 拷贝
    cute::identity                  // 变换
>;
```

**心智模型**：把"GEMM 主循环"抽象成**四个可替换组件**：MMA、GMEM 拷贝、SMEM 布局、pipeline 阶段数。想在 SM90 上换 TMA + WGMMA？只需要**换其中两个原子**。

### 6.3 什么时候用 3.x（CuTe），什么时候用 2.x

| 场景 | 用 |
|:--|:--|
| SM75~SM86（Turing / Ampere）| **2.x 就够了**，成熟稳定 |
| SM90 (H100) TMA / WGMMA / cluster | **必须 3.x（CuTe）** |
| SM100 (Blackwell) | **只有 3.x** |
| 学习/入门 | 从 2.x 起手，理解五层再上 3.x |

**建议**：**入门先啃 2.x**（`examples/00~15`），能编译能改 tile size 就 OK；**要玩 H100 或想深度改 mainloop，再上 3.x**（`examples/48+`）。

---

## 7. Profiler 工具：一条命令测遍所有 kernel

CUTLASS 自带一个"神器"：**cutlass_profiler**，能一条命令跑遍所有形状 × 所有 tile 组合，找到最快的那个。

### 7.1 常用命令

```bash
# 找 M=N=K=4096 FP16 GEMM 最快的配置
./tools/profiler/cutlass_profiler \
    --operation=Gemm --m=4096 --n=4096 --k=4096 \
    --A=f16:row --B=f16:col --C=f32:row \
    --accumulator-type=f32

# 输出：所有能跑的 kernel + 各自耗时 + GFLOPS + 最佳配置
```

### 7.2 输出示例

```
Kernel                                           Runtime  GFLOPS
------                                           -------  ------
cutlass_tensorop_h1688gemm_128x128_32x2_nn         3.21ms   26.7T
cutlass_tensorop_h1688gemm_128x256_32x2_nn         3.85ms   22.2T
cutlass_tensorop_h1688gemm_256x128_32x2_nn         3.42ms   25.0T
...
Best: cutlass_tensorop_h1688gemm_128x128_32x2_nn   3.21ms
```

**这个工具救过多少人的命**：不用你手动改 tile size 逐个编译测试，一条命令直接告诉你 3060 上 FP16 4096 GEMM 最佳 tile 是 `128×128×32`。

### 7.3 与 cuBLAS 对比

```bash
./cutlass_profiler --operation=Gemm ... --reference-check=on --providers=cutlass,cublas
```

会同时跑 CUTLASS 和 cuBLAS，一目了然差距。**目标**：把 CUTLASS 打到 cuBLAS 的 85%+ 就算优秀，95%+ 就是极致。

---

## 8. 集成到 PyTorch / 自定义算子

### 8.1 通过 `torch.utils.cpp_extension`

```python
from torch.utils.cpp_extension import load_inline

cutlass_gemm = load_inline(
    name="my_cutlass_gemm",
    cpp_sources="""
        torch::Tensor gemm(torch::Tensor A, torch::Tensor B);
    """,
    cuda_sources=open("my_gemm.cu").read(),
    extra_include_paths=["/path/to/cutlass/include",
                         "/path/to/cutlass/tools/util/include"],
    extra_cuda_cflags=["-O3", "-arch=sm_86", "-std=c++17"],
    verbose=True
)

C = cutlass_gemm.gemm(A, B)
```

### 8.2 `_scaled_mm` 与 CUTLASS 的关系

PyTorch 2.x 的 FP8 GEMM（`torch._scaled_mm`）内部就是 CUTLASS 3.x 的 kernel。你如果要写自己的 FP8 融合，最正确的路径就是**照抄 CUTLASS FP8 example → 加 Epilogue → 编成 PyTorch 扩展**。

### 8.3 一句话建议

> 如果只想在 PyTorch 里用，先看看 `torch._scaled_mm` / `torch._int_mm` 够不够；不够再写 CUTLASS 扩展。**别一上来就手撸——生态里可能已经有现成的**（xformers、flash-attn、cutlass-fpA-intB 都是 CUTLASS 的封装）。

---

## 9. 性能分析：怎么知道 CUTLASS 到底跑得多快？

### 9.1 计算峰值算力（3060）

RTX 3060 (Ampere GA106)：
- FP16 Tensor Core：**约 51 TFLOPS**（sparsity off）；
- 你的 CUTLASS GEMM 目标：**跑到 40~45 TFLOPS 就是优秀**（80~90% 峰值）。

### 9.2 计算你的 GEMM FLOPs

```
FLOPs = 2 * M * N * K
GFLOPS = FLOPs / (runtime_ms * 1e6)
```

**示例**：M=N=K=4096, runtime=3.21ms  
→ FLOPs = 2×4096³ ≈ 137.4 GFLOP  
→ GFLOPS ≈ 42.8 TFLOP/s → **对 3060 FP16 是 84% 峰值，非常健康**。

### 9.3 与 Nsight Compute 配合

```bash
ncu --set full --target-processes all ./basic_gemm
```

关注三个指标：
- **SM Busy %**：应该 > 90%（计算真的在跑）；
- **Tensor Core Utilization**：> 70% 才算用起来了；
- **DRAM Throughput %**：GEMM 大多是 compute-bound，这个不该顶到 90%（顶到就说明 tile 太小）。

### 9.4 三条经验

1. **先跑 profiler 找最佳 tile，别自己瞎猜**；
2. **对比 cuBLAS 是最诚实的基准**——差距超过 20% 说明配置错了；
3. **每换一个形状（M/N/K 或 dtype）重新跑 profiler**——最佳 tile 是随形状变的。

---

## 10. 学习路线图（4~6 周）

### 🟢 阶段 1（Week 1）：入门

- ✅ 装好 CUTLASS，编过 `examples/00_basic_gemm`；
- ✅ 理解**五层分层结构**（Device→Kernel→Threadblock→Warp→Instruction）；
- ✅ 会改 `ThreadblockShape / WarpShape / InstructionShape`；
- ✅ 会跑 `cutlass_profiler`，读懂输出。

### 🟡 阶段 2（Week 2~3）：Epilogue & 常见变体

- ✅ 会用 `LinearCombinationRelu / Gelu / Clamp`；
- ✅ 写一个自定义 Epilogue functor；
- ✅ 用 profiler 把 3060 FP16 GEMM 打到 cuBLAS 80%+；
- ✅ 跑通 `examples/13_two_tensor_op_fusion`（GEMM + GEMM 融合）。

### 🟠 阶段 3（Week 4~5）：3.x + CuTe

- ✅ 读 `examples/48_hopper_warp_specialized_gemm`（Hopper 起点）；
- ✅ 理解 CuTe 的 `Layout` / `Tensor` / `Copy Atom` / `MMA Atom`；
- ✅ 会用 `CollectiveMainloop` 拼一个 SM80 的 GEMM；
- ✅ 尝试 Grouped GEMM（`examples/24_gemm_grouped`）。

### 🔴 阶段 4（Week 6+）：实战 & 前沿

- ✅ 读改 FlashAttention CUTLASS 参考实现（含 Hopper 版）；
- ✅ 把 CUTLASS 集成到 PyTorch，写一个 fused Linear+GELU；
- ✅ 尝试 FP8 GEMM（SM90）或 int4 GEMM（`examples/55`）；
- ✅ 给 CUTLASS 提一个 issue 或 PR。

---

## 11. 精选资源与踩坑清单

### 11.1 必读官方资源

| 资源 | 用途 | 链接 |
|:--|:--|:--|
| CUTLASS GitHub | 源码 + 100+ examples | <https://github.com/NVIDIA/cutlass> |
| CUTLASS docs | 官方文档站 | <https://nvidia.github.io/cutlass/> |
| CuTe docs | CuTe 概念详解 | <https://github.com/NVIDIA/cutlass/tree/main/media/docs/cute> |
| NVIDIA GTC talks | 每年 GTC 都有 CUTLASS 专场 | 搜 "GTC CUTLASS" |
| CUTLASS 论文 | 分层抽象的动机 | 搜 "CUTLASS: Fast Linear Algebra in CUDA C++" |

### 11.2 高质量博客

- **NVIDIA Developer Blog：CUTLASS 系列**：<https://developer.nvidia.com/blog/tag/cutlass/>；
- **《Making GEMM Fast》系列**（Simon Boehm）：<https://siboehm.com/articles/22/CUDA-MMM>——虽然是手写 CUDA 但心智模型跟 CUTLASS 一模一样；
- **《Deep Dive into CUTLASS》**（Colfax Research）：<https://research.colfax-intl.com/>。

### 11.3 完整踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 编译时间 30 分钟以上 | 一次编上千个 kernel | `-DCUTLASS_LIBRARY_KERNELS="sgemm_*"` 限制范围 |
| `static_assert failed: shape` | ThreadblockShape/WarpShape 不整除 | 保证 128/64=2 这种整数关系 |
| 结果全 NaN | Layout tag 反了 | 检查 RowMajor/ColumnMajor 是否与实际内存一致 |
| 打不过 cuBLAS 60% | tile 选错了 | 跑 profiler 拿最佳配置 |
| SM90 example 编译错 | 3060 是 SM86 | 换 SM80 example |
| register pressure 高、spill 严重 | tile 太大 | 缩小 WarpShape 或降 pipeline stage |
| shared memory 超 48KB | tile+pipeline 太大 | 缩小 tile 或用 dynamic shared |
| PyTorch 集成后 Cache 报错 | 模板实例化路径 hash 变了 | 清 `~/.cache/torch_extensions` |
| Windows 上 MSVC 死循环 | 模板深度不足 | `/Zc:__cplusplus /permissive-` |

### 11.4 一句话总结

> **CUTLASS = "NVIDIA 官方公开的 GEMM 写法教科书 + 生产级模板库"**。它把 GPU 上矩阵乘拆成五层可组合的积木，让你既能像用库一样一行调用，也能像玩乐高一样重组底层。**cuBLAS 是产品，CUTLASS 是产品的源代码给你看**。
>
> **学它的收益**：真正吃透 GPU 计算的"下限"和"上限"——**上限**就是打到硬件峰值的 GEMM；**下限**就是理解为什么 cuBLAS 快、为什么 Tensor Core 要这样用。想搞 kernel 工程师、编译器（TVM/Triton/XLA）、AI 底层加速的同学，CUTLASS 是绕不过去的一站。

---

**祝你写出接近峰值算力的 kernel。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
