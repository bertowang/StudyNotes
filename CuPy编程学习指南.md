# CuPy 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：已经会用 **NumPy**，做**数据处理 / 科学计算 / 图像/信号处理 / 数值仿真**，想**几乎零学习成本**地把代码搬到 GPU、拿 10~100x 加速的 Python 程序员；也适合搞 AI 的同学做 **PyTorch 之外的数据 pipeline 提速**。
> **目标**：2~4 周内，从"把 `import numpy as np` 改成 `import cupy as cp`"到"能写融合算子、能与 PyTorch/Numba 混用、能上生产环境"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1** + Python 3.10 + CuPy ≥ 13.0。

---

## 目录

- [0. 写在最前：为什么要学 CuPy？](#0-写在最前为什么要学-cupy)
- [1. CuPy 是什么：一句话讲清 vs NumPy / vs PyTorch / vs Numba](#1-cupy-是什么一句话讲清-vs-numpy--vs-pytorch--vs-numba)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. 五分钟入门：把 NumPy 代码搬 GPU](#3-五分钟入门把-numpy-代码搬-gpu)
- [4. 第一个自定义 Kernel：ElementwiseKernel（对照 CUDA 版）](#4-第一个自定义-kernelelementwisekernel对照-cuda-版)
- [5. 三大必修 Kernel：Reduction / Raw / Fusion](#5-三大必修-kernelreduction--raw--fusion)
- [6. 与 PyTorch / Numba / Triton 互通（零拷贝）](#6-与-pytorch--numba--triton-互通零拷贝)
- [7. 内存管理与流：CuPy 的性能杀手锏](#7-内存管理与流cupy-的性能杀手锏)
- [8. 性能分析：怎么知道 CuPy 到底跑得多快？](#8-性能分析怎么知道-cupy-到底跑得多快)
- [9. CuPy vs Numba vs Triton：何时该用谁？](#9-cupy-vs-numba-vs-triton何时该用谁)
- [10. 学习路线图（2~4 周）](#10-学习路线图24-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 CuPy？

作为一个已经会 NumPy 的程序员，你一定遇到过这种痛点：**代码逻辑没错，就是太慢**——一个 4K 图像 FFT 要 2 秒、一个百万级矩阵求逆要 5 秒、蒙特卡洛跑一晚上没结束。传统解决方案要么写 CUDA C++（学习曲线陡），要么用 Numba（要重写循环），要么直接放弃精度用采样。

CuPy 给了第四条路——**几乎零改动**：

```python
# 只需改这一行
# import numpy as np
import cupy as cp

# 剩下所有 NumPy 代码原样跑，自动在 GPU 上执行
x = cp.random.randn(10000, 10000)
y = cp.linalg.inv(x @ x.T + cp.eye(10000))
```

**收益**：常见 NumPy 场景 **10~200x 加速**，代码几乎不改。

### 0.1 一句话对比

| 需求 | NumPy | Numba `@cuda.jit` | CuPy |
|:--|:--|:--|:--|
| 100 行 NumPy 数值计算搬 GPU | ❌ | 改 100 行成 kernel | **改 1 行 import** |
| 一个 FFT + 矩阵求逆 pipeline | 慢 | 得手写 kernel | **cp.fft + cp.linalg 直接调** |
| 图像 5×5 卷积 | 用 scipy 慢 | 写 kernel ~30 行 | **cupyx.scipy.ndimage 直接调** |
| 自定义融合算子 | ❌ | ~30 行 | **`ElementwiseKernel` ~5 行** |
| 与 PyTorch/Numba 互通 | / | 零拷贝 | **零拷贝，DLPack 无缝** |

### 0.2 CuPy 现在有多重要？

- **RAPIDS 生态基石**：cuDF / cuML / cuGraph / cuSignal 全部构建在 CuPy 之上；
- **SciPy 的 GPU 版**：`cupyx.scipy` 覆盖 `ndimage / signal / sparse / linalg / stats` 等大部分子模块；
- **PyTorch 数据 pipeline 加速主力**：预处理/后处理走 CuPy，模型走 PyTorch，中间零拷贝；
- **NumPy API 100% 兼容**：这是它区别于所有其他 GPU 库的最大杀手锏；
- **由 Preferred Networks 主导，NVIDIA 深度支持**：稳定、成熟、生产级。

**一句话**：**如果你的代码是 NumPy 或 SciPy 风格，CuPy 是投入产出比最高的 GPU 加速方案，没有之一**。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **C1 入门** | 会把 `numpy` 替换成 `cupy`，能用 `cp.asarray` / `cp.asnumpy` 搬数据 |
| **C2 熟练** | 会用 `ElementwiseKernel` / `ReductionKernel` 写自定义融合算子，会控制 Stream |
| **C3 高阶** | 会用 `RawKernel` 塞原生 CUDA C++，会做内存池调优，能与 PyTorch/Numba 混合使用 |
| **C4 专家** | 能读 CuPy 源码、给 RAPIDS 提 PR、能处理多 GPU 场景 |

**建议**：**1 周内到 C1**（把手头一段 NumPy 代码搬 GPU），**2~3 周内到 C2**（能写自定义算子），已覆盖 90% 生产场景。

---

## 1. CuPy 是什么：一句话讲清 vs NumPy / vs PyTorch / vs Numba

### 1.1 CuPy 的定义

> **CuPy 是 NumPy/SciPy 的 GPU 版本**：**API 100% 兼容**，底层调用 cuBLAS / cuDNN / cuFFT / cuSPARSE / cuSOLVER 等 NVIDIA 官方库，同时提供 `ElementwiseKernel` / `RawKernel` 让你写自定义 GPU 算子。

关键三点：

1. **NumPy 兼容** —— 你写的还是 NumPy 语法，`cp.array` / `cp.mean` / `cp.linalg.svd` 都能用；
2. **背后是官方 CUDA 库** —— `cp.matmul` 调 cuBLAS，`cp.fft.fft` 调 cuFFT，性能已经是极限；
3. **可扩展** —— 官方库覆盖不到的场景，用 `ElementwiseKernel`（简单）/ `RawKernel`（终极）自定义 kernel。

### 1.2 CuPy vs NumPy vs PyTorch vs Numba

| 维度 | NumPy | PyTorch | Numba `@cuda.jit` | **CuPy** |
|:--|:--|:--|:--|:--|
| **运行位置** | CPU | GPU（+ CPU） | GPU | **GPU** |
| **API 风格** | NumPy | PyTorch 自成一派 | Python + CUDA thread | **NumPy 100% 兼容** |
| **心智模型** | 数组运算 | 计算图 + 自动微分 | 一 thread 一元素 | **数组运算（同 NumPy）** |
| **自动微分** | ❌ | ✅ | ❌ | ❌ |
| **写自定义 kernel** | ❌ | 得写 C++ ext | 直接 Python | **`ElementwiseKernel` 5 行** |
| **改代码量（NumPy→GPU）**| / | 大（换成 tensor API） | 大（改成 kernel） | **1 行 import** |
| **典型加速（vs NumPy）** | 1x | 10~100x | 10~200x | **10~200x** |
| **典型场景** | 通用 | AI 训练/推理 | 循环密集科学计算 | **数据处理 / 科学计算 / SciPy 迁移** |

**记忆口诀**：
- **NumPy 代码原样搬 GPU** → **CuPy**（无脑替换）；
- **需要自动微分 / 训模型** → **PyTorch**；
- **要写 CUDA-thread 级 kernel** → **Numba**；
- **要写 AI 融合算子（GEMM/Attn）** → **Triton**。

### 1.3 一张图看清 CuPy 在栈里的位置

```
┌───────────────────────────────────────────────────────┐
│  你的 Python 代码（NumPy / SciPy 风格）                │
├───────────────────────────────────────────────────────┤
│  CuPy API（cp.array / cp.linalg / cupyx.scipy...）    │
├──────────────────┬────────────────────────────────────┤
│  高层：官方封装    │  底层：cuBLAS / cuDNN / cuFFT /    │
│  ElementwiseKernel│         cuSPARSE / cuSOLVER / NCCL │
│  ReductionKernel  │  自定义：RawKernel（原生 CUDA C++） │
│  RawKernel        │                                    │
├──────────────────┴────────────────────────────────────┤
│  CUDA Runtime + Driver                                │
├───────────────────────────────────────────────────────┤
│  GPU 硬件（RTX 3060 / Ampere / SM 8.6）                │
└───────────────────────────────────────────────────────┘
```

**核心洞察**：CuPy 是**"NumPy 的语法层"**贴到**"NVIDIA 官方 CUDA 库"**上的一个"桥梁"。它不发明新算子，只是让你用 NumPy 的手感调用世界上最快的 GPU 库。

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 平台选择：三方案对比

**好消息**：与 Triton 不同，**CuPy 对 Windows 原生支持一流**，甚至比 Numba 更省事（不需要额外的 nvvm.dll 配置）。

| 方案 | 难度 | 推荐度 |
|:--|:--|:--|
| **Windows 原生（conda）** | 极低 | ⭐⭐⭐⭐⭐ 首选 |
| **Windows 原生（pip）** | 低 | ⭐⭐⭐⭐ |
| **WSL2 / Linux** | 极低 | ⭐⭐⭐⭐ |

### 2.2 Windows 一次性搭建

**方案 A：conda（推荐，一步到位）**

```powershell
conda create -n cupy python=3.10 -y
conda activate cupy

# 一步装 CuPy + CUDA runtime（版本自动匹配）
conda install -c conda-forge cupy cuda-version=12.1 -y
```

**方案 B：pip（更常用）**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 根据本机 CUDA 版本选包名：cupy-cuda12x / cupy-cuda11x
pip install cupy-cuda12x
```

> 💡 **CuPy 的包名带 CUDA 版本**：`cupy-cuda12x` 对应 CUDA 12.x，`cupy-cuda11x` 对应 CUDA 11.x。**装错版本会加载失败**，务必对齐本机 `nvidia-smi` 里的 CUDA 大版本。

### 2.3 环境验证脚本

```python
# check_cupy.py
import cupy as cp
import numpy as np

print("CuPy version    :", cp.__version__)
print("CUDA runtime    :", cp.cuda.runtime.runtimeGetVersion())
print("Device          :", cp.cuda.Device(0).attributes)
print("Device name     :", cp.cuda.runtime.getDeviceProperties(0)['name'].decode())

# 跑一个最小示例
x = cp.random.randn(1000, 1000, dtype=cp.float32)
y = cp.random.randn(1000, 1000, dtype=cp.float32)
z = x @ y                # 底层调 cuBLAS
print("matmul shape    :", z.shape, "dtype:", z.dtype)

# 拷回 CPU 验证
z_cpu = cp.asnumpy(z)
print("copy back ok    :", z_cpu.shape)
```

**期望输出**：

```
CuPy version    : 13.x.x
CUDA runtime    : 12010
Device name     : NVIDIA GeForce RTX 3060
matmul shape    : (1000, 1000) dtype: float32
copy back ok    : (1000, 1000)
```

看到这几行就说明 **驱动 + CUDA runtime + CuPy** 全部串通了。

### 2.4 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| `ImportError: DLL load failed`（Windows） | pip 装的包与本机 CUDA 版本不匹配 | 对齐 `nvidia-smi` 的 CUDA 大版本，重装对应 `cupy-cudaXXx` |
| `CUDARuntimeError: cudaErrorInsufficientDriver` | 驱动过旧 | 升级 NVIDIA 驱动 |
| 首次 kernel 启动慢 | JIT 编译内置 kernel | 正常，`~/.cupy/kernel_cache/` 会缓存，第二次秒开 |
| 内存爆掉 / `OutOfMemoryError` | CuPy 默认用内存池，缓存不释放 | `cp.get_default_memory_pool().free_all_blocks()` |
| `cupyx.scipy.xxx` 找不到 | 部分功能需 CUDA-toolkit 里的 `.dll`（cuFFT 等） | conda 装 `cuda-toolkit` 补齐 |

---

## 3. 五分钟入门：把 NumPy 代码搬 GPU

### 3.1 一行 import 走天下

```python
import numpy as np
import cupy  as cp

# CPU
x_cpu = np.random.randn(10000, 10000).astype(np.float32)
y_cpu = np.linalg.inv(x_cpu @ x_cpu.T + np.eye(10000, dtype=np.float32))

# GPU：一模一样的代码，只是 np → cp
x_gpu = cp.random.randn(10000, 10000, dtype=cp.float32)
y_gpu = cp.linalg.inv(x_gpu @ x_gpu.T + cp.eye(10000, dtype=cp.float32))
```

在 RTX 3060 上前者要 **十几秒**，后者不到 **1 秒**。

### 3.2 三个必知函数：数据搬运

| 场景 | 函数 | 说明 |
|:--|:--|:--|
| NumPy → GPU | `cp.asarray(np_arr)` | 拷贝上 GPU，返回 `cupy.ndarray` |
| GPU → NumPy | `cp.asnumpy(cp_arr)` / `.get()` | 拷回 CPU |
| GPU 内新建 | `cp.zeros / cp.ones / cp.random.xxx` | 直接在 GPU 分配 |
| 类型/数据一致 | `cp.array_equal(a, b)` | 支持跨设备比较 |

**铁律**：**尽量避免频繁 host↔device 拷贝**。CPU-GPU 之间的 PCIe 带宽（3060 是 PCIe 4.0 x16 ≈ 32 GB/s）比 GPU 内部 HBM 带宽（~360 GB/s）**慢 10 倍**——**能一直在 GPU 就别拷回来**。

### 3.3 "无脑替换"的边界：CuPy 不支持什么？

CuPy 覆盖了 NumPy **>90%** 的 API，但仍有边角：

| ✅ 支持 | ❌ 不支持 / 有限支持 |
|:--|:--|
| 全部基本算术 / 广播 / 索引 | `np.vectorize`（改用 `ElementwiseKernel`）|
| `linalg`（SVD / eig / inv / solve） | `object` dtype / 变长字符串 |
| `fft`（1D/2D/3D）| Python 层复杂对象 |
| `random`（全部分布） | 少量 `np.polynomial` 边角函数 |
| 大部分 `cupyx.scipy.*` | pandas（换用 cuDF）|

**判定原则**：**能纯 NumPy 数值化描述的代码，几乎 100% 能搬**；一旦涉及 pandas、字符串、Python 对象，就要考虑 cuDF 或换设计。

### 3.4 一段完整的"搬迁"示例

**场景**：图像做归一化 + 3x3 均值滤波 + 阈值二值化。

```python
import cupy as cp
from cupyx.scipy.ndimage import uniform_filter

def process_gpu(img_uint8):
    x = cp.asarray(img_uint8).astype(cp.float32) / 255.0   # 上 GPU + 归一化
    x = uniform_filter(x, size=3)                          # GPU 上均值滤波
    x = (x > 0.5).astype(cp.uint8) * 255                   # 阈值
    return cp.asnumpy(x)                                   # 回 CPU
```

**对照 NumPy 版**：**代码基本一样**，`np` 换 `cp`、`scipy` 换 `cupyx.scipy`。这就是 CuPy 的杀手锏。

---

## 4. 第一个自定义 Kernel：ElementwiseKernel（对照 CUDA 版）

**问题**：内置 API 不够时怎么办？例如你想写一个"融合的 sigmoid + scale + bias"，用 CuPy 内置 API 得 3 步（3 次显存往返），能不能一次搞定？

**答案**：`ElementwiseKernel` —— **写一段 CUDA C++ 表达式，CuPy 自动生成 kernel + 编译 + 缓存**。

### 4.1 完整可运行代码

```python
# fused_sigmoid.py
import cupy as cp
import numpy as np

fused_sigmoid = cp.ElementwiseKernel(
    in_params  = 'T x, T scale, T bias',              # 输入
    out_params = 'T y',                               # 输出
    operation  = 'y = 1 / (1 + exp(-(x * scale + bias)))',  # 每元素表达式（CUDA C++）
    name       = 'fused_sigmoid'
)

# 使用
x = cp.random.randn(1_000_003, dtype=cp.float32)
y = fused_sigmoid(x, cp.float32(2.0), cp.float32(0.5))

# 验证
ref = 1 / (1 + cp.exp(-(x * 2.0 + 0.5)))
print("max abs diff:", float(cp.abs(y - ref).max()))
assert cp.allclose(y, ref)
print("✅ pass")
```

### 4.2 对照 CUDA C++ 版本，看看少了什么

| CUDA C++ 版要写 | CuPy `ElementwiseKernel` 版 |
|:--|:--|
| `__global__ void fused(...)` | 无（自动生成） |
| `int i = blockIdx.x * blockDim.x + threadIdx.x;` | 无（自动，用 `i` 就行） |
| `if (i < n)` | 无（自动） |
| 手写 `cudaMalloc / cudaMemcpy` | 无（自动） |
| `nvcc` 编译 + 链接 | 无（自动 JIT + 缓存） |
| launch config `<<<blocks, threads>>>` | 无（自动最优）|

**代码量**：CUDA C++ 60+ 行 → CuPy **5 行有效代码**，性能几乎持平（都会调 CUDA JIT 编译成 PTX）。

### 4.3 参数速查

| 参数 | 说明 | 典型值 |
|:--|:--|:--|
| `in_params` | 输入变量声明（`T` 是泛型，`float32`/`float64` 自动特化）| `'T x, T y'` |
| `out_params`| 输出变量声明 | `'T z'` |
| `operation` | 每个元素的表达式，**CUDA C++ 语法**（不是 Python！） | `'z = x * y + 1'` |
| `name`      | kernel 名（缓存文件名依赖它，**必须唯一**）| 见名知意 |
| `reduce_dims` | 是否合并可合并的维度加速 | 默认 `True` |

### 4.4 小白也能懂：4.1 代码逐行拆解

如果你是刚接触 CuPy 自定义 kernel 的新手，看到 `ElementwiseKernel` 的 5 行代码可能会有一堆问号：为什么参数是字符串？`T` 是什么？`operation` 里的语法是 Python 还是 C++？这一节把每一处讲透。

#### 4.4.1 先看整体结构：一个 CuPy 自定义 kernel 有几块？

CuPy 自定义 kernel 是**声明式的**——你告诉 CuPy "输入是什么、输出是什么、每个元素怎么算"，剩下的它全包了：

```
┌─────────────────────────────────────────────┐
│ ① 定义 kernel（一次性做）                    │
│    fused_sigmoid = cp.ElementwiseKernel(   │
│        in_params  = 'T x, T scale, T bias',│  ← 输入声明
│        out_params = 'T y',                 │  ← 输出声明
│        operation  = 'y = ...',             │  ← CUDA C++ 表达式
│        name       = 'fused_sigmoid')       │  ← 缓存标识
├─────────────────────────────────────────────┤
│ ② 使用 kernel（跟调 NumPy 函数一样）          │
│    y = fused_sigmoid(x, 2.0, 0.5)          │
└─────────────────────────────────────────────┘
```

**对比 Numba**：Numba 得自己算 `cuda.grid(1)` 和边界；CuPy **完全隐藏**了这些，专注表达式本身。

#### 4.4.2 逐行拆解 kernel 定义

```python
fused_sigmoid = cp.ElementwiseKernel(
    in_params  = 'T x, T scale, T bias',
    out_params = 'T y',
    operation  = 'y = 1 / (1 + exp(-(x * scale + bias)))',
    name       = 'fused_sigmoid'
)
```

**Line 1：`cp.ElementwiseKernel(...)`**
> **告诉 CuPy："我要定义一个逐元素算子。"**
> - "逐元素"意思是：**每个输出元素只依赖对应位置的输入元素**（不看邻居、不做归约）；
> - 典型：sigmoid、relu、加/减/乘/除、比较、bit 操作等；
> - 不适用：conv、matmul、sum、sort（这些用别的 kernel 类型）。

**Line 2：`in_params = 'T x, T scale, T bias'`**
> **输入声明字符串**——写法像 C++ 函数签名，但简化了。
> - `T` 是**泛型类型占位符**：你传 `float32` 就用 `float32`，传 `float64` 就用 `float64`，CuPy 自动为每种 dtype 生成一份特化的 kernel（首次调用触发编译）；
> - `x`、`scale`、`bias`：三个输入变量名，在 `operation` 里能直接引用；
> - 也可以指定具体类型：`'float32 x, int32 n'`，就不再是泛型；
> - **广播自动处理**：`x` 是 `(1000,)`，`scale` 是标量 `float32(2.0)`，会自动广播。

**Line 3：`out_params = 'T y'`**
> **输出声明**——CuPy 会**自动分配输出数组**，shape 由输入广播规则决定。
> - 如果你想复用一块显存（避免频繁分配），可以传 `out=` 参数：`fused_sigmoid(x, 2.0, 0.5, out=y_buf)`。

**Line 4：`operation = 'y = 1 / (1 + exp(-(x * scale + bias)))'`**
> **这一整个字符串是 CUDA C++ 代码**！不是 Python 代码。
> - 每个 thread 只跑这**一行表达式**，处理**一个元素**；
> - `exp` 是 CUDA math 库函数（`__expf`、`exp` 都行）；
> - **不要在这里写 Python 的 `**`**（幂）——用 `pow(x, 2)` 或直接 `x * x`；
> - **不要写 `if x > 0`**（会串行化 warp）——用三元运算符：`y = x > 0 ? x : 0`；
> - **不能写 `for` 循环**吗？可以，但表达式里的循环也是 C++ 语法；一般不这么用，逐元素本身就是并行。

**Line 5：`name = 'fused_sigmoid'`**
> **kernel 名字，很重要**。CuPy 把 JIT 编译结果按 `name + 参数类型` 存到磁盘缓存（默认 `~/.cupy/kernel_cache/`）。
> - **必须唯一**，不然会读到别人的缓存导致行为错乱；
> - 起名习惯：`模块_功能_版本`，如 `myops_fused_sigmoid_v1`。

#### 4.4.3 使用 kernel

```python
x = cp.random.randn(1_000_003, dtype=cp.float32)
y = fused_sigmoid(x, cp.float32(2.0), cp.float32(0.5))
```

**跟调普通 Python 函数一样简单**：
- **首次调用**：CuPy 检查参数类型 → 生成 CUDA C++ 源码 → 调 NVRTC 编译成 PTX → 缓存到磁盘（约 200~500ms 停顿）；
- **后续调用**：秒调（读缓存）；
- **shape 由 CuPy 自动推断**（此处 `y.shape == x.shape`）；
- **kernel 内部的 launch config（block/thread）** 由 CuPy 自动选一个较优值，你完全不用管。

#### 4.4.4 一图串起来：ElementwiseKernel 背后发生了什么

```
你写的 Python                          CuPy 内部（首次调用触发）             GPU
─────────────────────────────────────────────────────────────────────────────
                                       ┌─────────────────────────┐
fused_sigmoid = cp.ElementwiseKernel  →│ 保存元信息（尚未编译）    │
    (..., 'y = 1/(1+exp(...))')       └─────────────────────────┘

x = cp.random.randn(..., cp.float32)  → 已在 GPU 显存里
                                       ┌─────────────────────────┐
y = fused_sigmoid(x, 2.0, 0.5)        →│ 1. 看到 x 是 float32     │
                                       │ 2. 把 T 替换成 float32    │
                                       │ 3. 生成完整 .cu 源码：    │
                                       │    __global__ void ...(  │
                                       │      const float* x, ...) │
                                       │    { int i = blockIdx.x   │
                                       │        * blockDim.x       │
                                       │        + threadIdx.x;     │
                                       │      if (i < n) y[i] = ...│
                                       │    }                      │
                                       │ 4. NVRTC 编译成 PTX       │
                                       │ 5. 缓存到 ~/.cupy/...     │
                                       │ 6. 选定 launch config     │
                                       │    (blocks=3907, tpb=256) │
                                       └─────────────────────────┘
                                                                    ┌─────────────┐
                                                                  → │ 1M threads  │
                                                                    │ 并行跑一个   │
                                                                    │ 表达式       │
                                                                    └─────────────┘
                                       ┌─────────────────────────┐
                                     ← │ 返回 cp.ndarray y        │
                                       └─────────────────────────┘
```

**理解到这里，`ElementwiseKernel` 的心智模型就通了**：
- 你写的是**"每个元素的公式"**，CuPy 帮你写外壳（thread 索引、边界、launch）；
- **首次慢**（几百 ms 编译），**后续快**（微秒级 launch）；
- 数据只在 GPU 上流动，**不涉及 CPU-GPU 拷贝**。

#### 4.4.5 新手最容易踩的 5 个坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | 在 `operation` 里写 Python 语法 | 编译报错 `error: expected ';'` | 记住：**operation 是 CUDA C++**，用 `?:` 代替 `if`，`x*x` 代替 `x**2` |
| 2 | 输入 dtype 不一致 | 泛型 `T` 匹配失败或悄悄升 double 变慢 | 显式 `cp.float32(2.0)` 传标量，避免 Python `2.0`（会当 float64）|
| 3 | 忘了 `name` 或名字重复 | 缓存冲突、行为诡异 | 每个 kernel 起独一无二的名字 |
| 4 | 传 `numpy.ndarray` 进去 | 报错 `expected cupy.ndarray` | 先 `cp.asarray(np_arr)` |
| 5 | 结果不对但没报错 | operation 里用了未声明的变量名 | 声明的变量名要严格匹配 in/out_params |

**读完 4.4，你应该能自信地说**：`ElementwiseKernel` 的每一行都懂了、能默写、能仿写一个 `fused_gelu` 或 `fused_swish`——这就是 CuPy 自定义算子的入门门槛。

---

## 5. 三大必修 Kernel：Reduction / Raw / Fusion

### 5.1 ReductionKernel：写归约（sum / max / L2 norm）

**逐元素**只能表达 map，**不能表达归约**（因为归约要跨元素累加）。CuPy 为此提供 `ReductionKernel`。

**示例：计算每行的 L2 范数**

```python
l2_row = cp.ReductionKernel(
    in_params  = 'T x',
    out_params = 'T y',
    map_expr   = 'x * x',           # 先做啥（逐元素）
    reduce_expr= 'a + b',            # 怎么合（结合律运算）
    post_map_expr = 'y = sqrt(a)',   # 归约完再做啥
    identity   = '0',                # 归约初值
    name = 'l2_row_norm'
)

x = cp.random.randn(1024, 4096, dtype=cp.float32)
y = l2_row(x, axis=1)                # 沿列归约，输出 shape=(1024,)
```

**四段式记忆**：
- `map_expr`：**元素预处理**（`x*x`）；
- `reduce_expr`：**如何合并两个部分和**（`a + b`）；
- `post_map_expr`：**归约完再套一层**（开方）；
- `identity`：**归约的"零元"**（求和是 0，求积是 1，求 max 是 `-INFINITY`）。

**性能**：接近 cuBLAS 的手写 reduction，够绝大多数科学计算用。

### 5.2 RawKernel：写原生 CUDA C++

需要用到 **shared memory、warp shuffle、Tensor Core、原子操作、复杂 kernel 结构** 时，`ElementwiseKernel` 和 `ReductionKernel` 就不够了。**这时用 `RawKernel` 塞原生 CUDA C++**——CuPy 只负责编译和 launch，你写完整的 `.cu` 代码。

```python
saxpy_src = r'''
extern "C" __global__
void saxpy(const float* x, const float* y, float* out, float a, int n) {
    int i = blockDim.x * blockIdx.x + threadIdx.x;
    if (i < n) out[i] = a * x[i] + y[i];
}
'''

saxpy = cp.RawKernel(saxpy_src, 'saxpy')

n = 1_000_000
x = cp.random.randn(n, dtype=cp.float32)
y = cp.random.randn(n, dtype=cp.float32)
out = cp.empty_like(x)

threads = 256
blocks  = (n + threads - 1) // threads
saxpy((blocks,), (threads,), (x, y, out, cp.float32(2.0), n))
```

**用途**：把 CUDA 教程里的 `.cu` kernel **原样贴进 Python**——CUDA 老手迁移代码最爽的方式。

**姐妹类**：`cp.RawModule` 允许在同一段代码里放**多个 kernel**、共享 `__device__` 函数、包含 header。

### 5.3 `cp.fuse`：自动融合表达式

**痛点**：`y = cp.sin(x) + cp.cos(x)` 会产生 3 个 kernel（sin、cos、加），3 次显存读写。**`@cp.fuse` 让 CuPy 自动融合成一个 kernel**：

```python
@cp.fuse()
def sin_plus_cos(x):
    return cp.sin(x) + cp.cos(x)

y = sin_plus_cos(x)      # 融合成单个 kernel
```

**收益**：显存访问减半到三分之一，element-wise 场景常见 **2~3x 加速**。

**限制**：只支持 element-wise + 简单 reduction；有条件分支或复杂控制流会失败。**能用就用**，是 CuPy 里"免费的加速午餐"。

---

## 6. 与 PyTorch / Numba / Triton 互通（零拷贝）

**CuPy 最大魅力之一：与 PyTorch / Numba / Triton 之间可以做到显存零拷贝共享**——数据一直在 GPU，来回穿梭只是"改指针视角"。

### 6.1 CuPy ↔ PyTorch（DLPack 或 `__cuda_array_interface__`）

```python
import cupy as cp
import torch

# CuPy → PyTorch
x_cp = cp.random.randn(1024, dtype=cp.float32)
x_pt = torch.as_tensor(x_cp, device='cuda')     # 零拷贝（共享显存）

# PyTorch → CuPy
y_pt = torch.randn(1024, device='cuda')
y_cp = cp.from_dlpack(y_pt)                     # 零拷贝
# 或（老 API）：y_cp = cp.asarray(y_pt)
```

**典型场景**：PyTorch 训模型 + CuPy 做数据增强 / 后处理，中间无拷贝。

### 6.2 CuPy ↔ Numba

```python
from numba import cuda

x_cp = cp.random.randn(1024, dtype=cp.float32)
d_x  = cuda.as_cuda_array(x_cp)                 # Numba device array，零拷贝

@cuda.jit
def scale(x, s):
    i = cuda.grid(1)
    if i < x.size:
        x[i] *= s

scale[8, 128](d_x, 2.0)
# x_cp 已被修改（共享同一块显存）
```

**典型场景**：数据 pipeline 走 CuPy，热点循环用 Numba 手写 kernel。

### 6.3 CuPy ↔ Triton

Triton kernel 直接接受 CuPy 数组（都实现了 `__cuda_array_interface__`）：

```python
import triton
import triton.language as tl

@triton.jit
def add_kernel(x_ptr, y_ptr, out_ptr, N, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    mask = offs < N
    a = tl.load(x_ptr + offs, mask=mask)
    b = tl.load(y_ptr + offs, mask=mask)
    tl.store(out_ptr + offs, a + b, mask=mask)

x = cp.random.randn(1_000_000, dtype=cp.float32)
y = cp.random.randn(1_000_000, dtype=cp.float32)
out = cp.empty_like(x)
grid = ((x.size + 1023) // 1024,)
add_kernel[grid](x, y, out, x.size, BLOCK=1024)
```

### 6.4 常见陷阱

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| PyTorch 修改 tensor 后 CuPy 看不到 | 用了 `.clone()` 破坏共享 | 用 `torch.as_tensor` 而不是 `torch.tensor` |
| Numba 修改数组后 CuPy 看不到 | 传的是 host copy | 用 `cuda.as_cuda_array`，别用 `to_device` |
| dtype 不匹配 | CuPy 默认 float64，PyTorch 默认 float32 | 显式指定 `dtype=cp.float32` |
| 内存被提前释放 | 生命周期被 Python GC 抢走 | 保留 CuPy 数组的引用直到用完 |

---

## 7. 内存管理与流：CuPy 的性能杀手锏

### 7.1 内存池（默认开启，不懂会踩坑）

CuPy 默认用**内存池**——`cudaMalloc` / `cudaFree` 太慢，CuPy 缓存已释放的显存块以便复用。

```python
mempool = cp.get_default_memory_pool()
print("已用       :", mempool.used_bytes() / 1e6, "MB")
print("池内已分配 :", mempool.total_bytes() / 1e6, "MB")

# 显式释放（长跑任务定期调，避免看起来"内存泄漏"）
mempool.free_all_blocks()
```

**坑**：`nvidia-smi` 看到 CuPy 进程占用 8GB 显存不下降，**多半是内存池在缓存**。真出问题时调 `free_all_blocks()`。

### 7.2 Stream：kernel 与拷贝并行

```python
stream1 = cp.cuda.Stream(non_blocking=True)
stream2 = cp.cuda.Stream(non_blocking=True)

with stream1:
    a = cp.random.randn(10_000_000, dtype=cp.float32)
    b = a * 2 + 1

with stream2:
    c = cp.random.randn(10_000_000, dtype=cp.float32)
    d = cp.sin(c)

cp.cuda.Stream.null.synchronize()   # 等所有流
```

**典型收益**：CPU 侧 batch 上传 + GPU 端 kernel + 结果拷回三段流水，能榨出**再多 30~50%** 的性能。

### 7.3 固定内存（Pinned Memory）

CPU-GPU 拷贝走**普通内存**时会经过一次 host 拷贝到"锁页缓冲区"再 DMA；用**固定内存**能省掉这一次：

```python
pinned = cp.cuda.alloc_pinned_memory(4 * 1024 * 1024 * 1024)  # 4GB
x_np   = np.frombuffer(pinned, dtype=np.float32).reshape(...)
# x_np 现在是固定内存，与 GPU 传输快 1.5~2x
```

**用途**：需要频繁大批量 CPU↔GPU 拷贝（如视频解码 → GPU 推理）。

### 7.4 多 GPU

```python
with cp.cuda.Device(0):
    a = cp.random.randn(1000)
with cp.cuda.Device(1):
    b = cp.random.randn(1000)
    # b 在 GPU 1 上
```

配合 NCCL（CuPy 自带 `cupyx.distributed`）可做多卡数据并行。

---

## 8. 性能分析：怎么知道 CuPy 到底跑得多快？

### 8.1 用 `time.perf_counter` + `cp.cuda.Stream.null.synchronize()`

```python
import time

# 预热
for _ in range(3):
    y = fused_sigmoid(x, 2.0, 0.5)
cp.cuda.Stream.null.synchronize()

# 计时
t0 = time.perf_counter()
for _ in range(100):
    y = fused_sigmoid(x, 2.0, 0.5)
cp.cuda.Stream.null.synchronize()   # ⚠️ 一定要同步
t1 = time.perf_counter()
print(f"{(t1 - t0) / 100 * 1000:.3f} ms")
```

**关键**：GPU 是异步的，**不同步测出来的是 launch 时间，全是假的**。

### 8.2 CuPy 内置 benchmark

```python
from cupyx.profiler import benchmark

def run():
    return fused_sigmoid(x, cp.float32(2.0), cp.float32(0.5))

print(benchmark(run, n_repeat=100, n_warmup=3))
# 会同时输出 CPU 时间、GPU 时间
```

**优点**：帮你处理好同步、预热、统计；生产环境首选。

### 8.3 用 Nsight Systems / Compute

```bash
nsys profile --stats=true python bench.py
ncu  --set full --target-processes all python bench.py
```

CuPy 自动生成的 kernel 名字带 `cupy_` 前缀，很好定位。

### 8.4 三条经验法则

1. **内置 API 已经很快**（cuBLAS/cuFFT 是 NVIDIA 极限），别造轮子；
2. **`@cp.fuse` 是免费加速**（element-wise 场景），先用了再说；
3. **写自定义算子前先看能不能用 `ElementwiseKernel`**，写 `RawKernel` 是最后手段。

---

## 9. CuPy vs Numba vs Triton：何时该用谁？

**这是学完 CuPy 后必然要面对的选型问题**，一图讲清。

### 9.1 一表看清

| 维度 | **CuPy** | Numba `@cuda.jit` | Triton `@triton.jit` |
|:--|:--|:--|:--|
| 抽象层级 | **Array 级（NumPy）** | Thread 级 | Block 级 |
| 心智模型 | **NumPy 数组运算** | CUDA thread 直译 | GPU 版 NumPy |
| API 兼容 | **NumPy 100%** | Python 子集 + CUDA | Triton DSL |
| 内置算子 | **cuBLAS/cuFFT 等一大堆** | ❌（要自己写）| ❌（要自己写）|
| 自定义 kernel | ElementwiseKernel / RawKernel | 全自己写 | 全自己写 |
| Tensor Core | ✅（通过 cuBLAS）| ❌ | ✅（`tl.dot`）|
| Autotune | ❌ | ❌ | ✅ |
| Windows 原生 | ✅ 完美 | ✅ 完美 | ⚠️ 差 |
| 学习曲线 | **极平缓** | 平缓 | 稍陡 |
| 典型场景 | **科学计算 / 数据 pipeline / SciPy 迁移** | 循环密集 / CUDA 老手 | **AI 融合算子** |
| 性能上限 | cuBLAS 极限 | cuBLAS ~60~70% | cuBLAS 90~100% |

### 9.2 选型决策树

```
你的场景是什么？
    │
    ├─ 已有 NumPy / SciPy 代码，想搬 GPU
    │      → CuPy（一行 import）
    │
    ├─ 需要调 cuBLAS / cuFFT / cuSPARSE 等官方库
    │      → CuPy（就是它的门面）
    │
    ├─ 数据 pipeline（预处理 + 推理 + 后处理）
    │      → CuPy 主线，配合 PyTorch/Numba/Triton
    │
    ├─ 手上有 CUDA .cu 代码，只想 Python 侧调
    │      → CuPy 的 RawKernel（原样贴进来）
    │
    ├─ 要写 CUDA-thread 级复杂 kernel
    │      → Numba 或 CuPy RawKernel
    │
    ├─ 要写 AI 融合算子（Attention/GEMM/Norm）
    │      → Triton
    │
    └─ 快速原型 + NumPy 兼容 + 免维护
           → CuPy（首选）
```

### 9.3 一句话总结

> **CuPy 是"NumPy 的 GPU 版本"，Numba 是"CUDA 的 Python 直译版"，Triton 是"NumPy 手感的 GPU DSL"**。
> - **CuPy 用来"搬"**（把 NumPy 代码搬 GPU）；
> - **Numba 用来"写"**（写自己的 CUDA thread 级 kernel）；
> - **Triton 用来"打"**（打 AI 里的性能极限战）。
>
> 三者**不冲突，最佳实践是混用**：CuPy 做骨架 + 自定义 kernel 用 Numba/Triton 补齐 + PyTorch 训模型。

---

## 10. 学习路线图（2~4 周）

### 🟢 阶段 1（Week 1）：无脑搬迁

- ✅ 装好 CuPy（pip 或 conda）
- ✅ 挑一段自己的 NumPy 代码，把 `np` 全换成 `cp`，跑通并对比速度
- ✅ 熟练用 `cp.asarray` / `cp.asnumpy` / `.get()`
- ✅ 了解 `cupyx.scipy` 覆盖了哪些 SciPy 子模块
- ✅ 通读 CuPy 官方 quickstart

### 🟡 阶段 2（Week 2）：自定义算子

- ✅ 写 3 个 `ElementwiseKernel`（sigmoid、gelu、fused_add_mul）
- ✅ 写 1 个 `ReductionKernel`（L2 norm、softmax 归一化因子）
- ✅ 学会 `@cp.fuse`，跑对比看融合前后加速比
- ✅ 用 `cupyx.profiler.benchmark` 测速

### 🟠 阶段 3（Week 3）：进阶 & 集成

- ✅ 写一个 `RawKernel`（贴一段 CUDA C++ 进来）
- ✅ 与 PyTorch 做零拷贝互通（DLPack）
- ✅ 与 Numba 做零拷贝互通（`cuda.as_cuda_array`）
- ✅ 玩 Stream，实现 kernel + memcpy 并行
- ✅ 学会内存池管理，避免 OOM 假象

### 🔴 阶段 4（Week 4）：实战项目

- ✅ 做一个**完整应用**：例如"视频帧 → GPU 解码 → CuPy 图像滤波 → PyTorch 推理 → 后处理写回"，全程零拷贝
- ✅ 对比 CuPy vs NumPy vs Numba vs Triton，同一 kernel 四种写法测速
- ✅ 读一段 RAPIDS（cuML / cuSignal）源码，看官方怎么用 CuPy

### 🎯 里程碑（做完就是 C3）

- 给自己项目里最慢的一个 NumPy 函数写 CuPy 版本，实测 20x+ 加速；
- 用 `ElementwiseKernel` + `ReductionKernel` 复现一个 Softmax，测速接近 PyTorch；
- 写一个完整的 CuPy + PyTorch 数据 pipeline，跑通训练。

---

## 11. 精选资源与踩坑清单

### 11.1 必读官方资源

| 资源 | 用途 | 链接 |
|:--|:--|:--|
| CuPy 官方文档 | API 手册 + tutorial | <https://docs.cupy.dev/> |
| CuPy GitHub | 源码 + issue | <https://github.com/cupy/cupy> |
| cupyx.scipy 参考 | SciPy 迁移查询 | <https://docs.cupy.dev/en/stable/reference/scipy.html> |
| RAPIDS 官网 | CuPy 的最大用户 / 集成案例 | <https://rapids.ai/> |
| NumPy 到 CuPy 对照 | 已支持/未支持 API 速查 | <https://docs.cupy.dev/en/stable/reference/comparison.html> |
| DLPack 规范 | 零拷贝互通原理 | <https://dmlc.github.io/dlpack/latest/> |

### 11.2 高质量博客/讲解

- **Preferred Networks 官方博客**：CuPy 的主要维护方；<https://tech.preferred.jp/en/>
- **NVIDIA Developer Blog: CuPy 系列**：<https://developer.nvidia.com/blog/tag/cupy/>
- **《High Performance Python》**（Micha Gorelick 等）：CuPy 与 Numba 章节值得反复看；
- **RAPIDS Notebooks**：<https://github.com/rapidsai/notebooks>——大量 CuPy 实战。

### 11.3 完整踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| `ImportError: DLL load failed` | pip 包 CUDA 版本与本机不符 | 对齐 `nvidia-smi`，重装 `cupy-cudaXXx` |
| 首次 kernel 停顿 200~500ms | JIT 编译 | 正常，`~/.cupy/kernel_cache/` 缓存 |
| `nvidia-smi` 显存不释放 | 内存池未清 | `cp.get_default_memory_pool().free_all_blocks()` |
| 结果对但比 NumPy 慢 | 数据太小，Kernel launch 开销占主导 | 攒大 batch 再做，或 `@cp.fuse` |
| 数值精度对不上 NumPy | 默认 float64 被隐式转 float32 | 显式指定 dtype，或对比时也用 float64 |
| 传 numpy 数组给 Kernel 报错 | 需要 CuPy 数组 | `cp.asarray(np_arr)` |
| `operation` 里报编译错 | 写成了 Python 语法 | `operation` 是 CUDA C++；用 `?:` 代替 `if`|
| 与 PyTorch 共享 tensor 后被"覆盖" | 用了 `torch.tensor(...)` 触发拷贝 | 用 `torch.as_tensor` 或 `from_dlpack` |
| kernel 名冲突结果错乱 | 两个 `ElementwiseKernel` 用了相同 `name` | 保证 `name` 唯一 |
| 计时太乐观 | 忘了 `synchronize` | 用 `cp.cuda.Stream.null.synchronize()` 或 `benchmark` |
| `float64` 慢得离谱 | 3060 是消费卡，fp64 阉割严重 | 全程 float32，除非必须 |
| 多 GPU 时数据在错误设备 | 忘了 `with cp.cuda.Device(i):` | 显式切换设备上下文 |

### 11.4 一句话总结

> **CuPy = "NumPy 的 GPU 版本"**——一行 import 拿到 10~200x 加速；调 cuBLAS/cuFFT 是它的默认技能；写自定义算子只要 5 行 `ElementwiseKernel`；与 PyTorch/Numba/Triton 零拷贝互通。
> **学它的成本极低**（一天入门），**收益却常常巨大**——从科学计算到工程原型，是每个 Python 数值计算工程师都该掌握的第一把 GPU 武器。

---

**祝你 NumPy 越写越快，热点函数一个都不留。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
