# Numba 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-13

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：会 Python + NumPy，看过 CUDA 教程但**不想学 C++**，想用**纯 Python 语法把热点代码搬到 GPU**的程序员；或者用 Python 做**科学计算 / 数值仿真 / 蒙特卡洛 / 图像处理 / 遗传算法**等，想一键提速 10~100x 的工程师。
> **目标**：3~5 周内，从"写第一个 `@njit` 函数"到"能写 CUDA kernel、能给自己的 Python 项目提速 10x+"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1** + Python 3.10 + Numba ≥ 0.59。

---

## 目录

- [0. 写在最前：为什么要学 Numba？](#0-写在最前为什么要学-numba)
- [1. Numba 是什么：一句话讲清 vs CPython / vs Cython / vs Triton](#1-numba-是什么一句话讲清-vs-cpython--vs-cython--vs-triton)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. Numba CPU 模式：`@njit` 五分钟入门](#3-numba-cpu-模式njit-五分钟入门)
- [4. 第一个 GPU Kernel：向量加法（对照 CUDA C++ 版）](#4-第一个-gpu-kernel向量加法对照-cuda-c-版)
- [5. 三大必修 Kernel：Reduction / Matmul / 图像模糊](#5-三大必修-kernelreduction--matmul--图像模糊)
- [6. 进阶特性：共享内存 / 原子操作 / Stream](#6-进阶特性共享内存--原子操作--stream)
- [7. 集成到 NumPy / PyTorch / CuPy](#7-集成到-numpy--pytorch--cupy)
- [8. 性能分析：怎么知道 Numba 到底跑得多快？](#8-性能分析怎么知道-numba-到底跑得多快)
- [9. Numba vs Triton：何时该用谁？](#9-numba-vs-triton何时该用谁)
- [10. 学习路线图（3~5 周）](#10-学习路线图35-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 Numba？

作为 Python 程序员，你可能已经被 NumPy 惯坏了——直到某天遇到一个**必须写循环**的场景（自定义损失函数、粒子模拟、图像遍历、蒙特卡洛······），发现代码慢了 100 倍。这时你有三条路：

1. **重写成 C++ / Cython** —— 学习成本高，还要编译、绑定；
2. **用 CUDA C++ 写 kernel** —— 更陡的坡，且要 `nvcc`、`pybind11`、`setup.py`；
3. **给函数加一行 `@njit` 或 `@cuda.jit`** —— **这就是 Numba**。

> Numba 是**"Python 加速的性价比之王"**：**只加一个装饰器，代码一行不改，速度提升 10~1000 倍**——这就是它 10 多年来始终在 Python 数值计算圈稳坐王座的原因。

### 0.1 一句话对比

| 需求 | 纯 Python / NumPy | Cython / C++ 扩展 | Numba |
|:--|:--|:--|:--|
| 一个双重循环把数组加起来 | 慢 100~1000 倍 | 需写 .pyx + 编译 | **加 `@njit`，快 100x** |
| 把热点函数搬 GPU | ❌ 做不到 | 需写 CUDA C++ + pybind11 | **加 `@cuda.jit`，几十行** |
| 支持 NumPy 数组 | 天然 | 需手写 buffer | **原生支持** |
| 部署难度 | 零 | 要交叉编译 | **纯 Python 包，pip 装** |
| 调试 | 熟悉 | 麻烦（gdb） | **可关掉 JIT，当普通 Python 调**|

### 0.2 Numba 现在有多重要？

- **SciPy / scikit-learn / scikit-image / librosa** 等主流库内部大量使用 Numba 加速；
- **RAPIDS cuDF / cuML** 允许在 GPU DataFrame 上跑用户自定义 Numba 函数；
- **PyMC / Numba-stats / Hyperopt** 等贝叶斯/优化库靠 Numba 提速；
- **量化交易、CFD、天文、粒子物理** 圈几乎人手一份 Numba；
- Anaconda 官方长期维护，NVIDIA 深度参与 CUDA 后端。

**一句话**：**如果你写 Python 而且关心速度，不会 Numba 就等于放弃 90% 的性能收益**。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **N1 入门** | 会用 `@njit`、`@njit(parallel=True)` 给 CPU 循环提速 |
| **N2 熟练** | 能写 `@cuda.jit` GPU kernel、理解 `cuda.grid` / `cuda.threadIdx` |
| **N3 高阶** | 用 shared memory、atomic、stream；能给 SciPy 级别项目贡献代码 |
| **N4 专家** | 混合调用 Numba + CuPy + PyTorch，能与 Triton 互补选型 |

**建议**：**1 周内到 N1，再花 1~2 周到 N2**，就已经覆盖 80% 场景。到 N3 是"能自己写高性能库"的门槛。

---

## 1. Numba 是什么：一句话讲清 vs CPython / vs Cython / vs Triton

### 1.1 Numba 的定义

> **Numba 是一个 JIT 编译器**：它把带装饰器的 Python 函数（受限子集）在**运行时**翻译成机器码——CPU 上直接是 x86/ARM 汇编，GPU 上是 PTX——性能媲美手写 C。

关键三点：

1. **零语法学习** —— 你写的还是 Python，只是加一个 `@njit` 或 `@cuda.jit`；
2. **两个后端** —— **CPU 后端**（基于 LLVM）+ **CUDA 后端**（基于 NVVM，直接生成 PTX）；
3. **不能加速一切** —— 只支持 NumPy 数值代码 + 简单 Python 结构（循环、if、tuple、简单 class），**pandas / requests / 复杂对象都不行**。

### 1.2 Numba vs CPython vs Cython vs Triton

| 维度 | CPython | Cython | Numba `@njit` | Numba `@cuda.jit` | Triton |
|:--|:--|:--|:--|:--|:--|
| **是否编译** | 解释执行 | AOT 编译 | **JIT 编译** | **JIT 编译** | JIT 编译 |
| **运行位置** | CPU | CPU | CPU | GPU | GPU |
| **抽象层级** | Python | Python + C 混写 | **纯 Python** | **CUDA thread 级** | **Block 级** |
| **改代码量** | / | 大（.pyx）| **1 行装饰器** | **加装饰器 + 写 kernel** | 写 kernel |
| **心智模型** | 逐行执行 | Python + C 类型 | Python + NumPy | **CUDA C++ 直译** | NumPy 向量化 |
| **典型加速** | 1x | 10~100x | 10~200x（CPU）| 50~500x（GPU）| 50~500x（GPU）|
| **调试** | 极易 | 中 | 易（可关 JIT）| 难（GPU 调试）| 中 |

**记忆口诀**：
- 想让 **Python 循环变快**（还在 CPU） → **`@njit`**；
- 想把 **CUDA C++ 翻译成 Python** 语法 → **`@cuda.jit`**；
- 想用 **NumPy 手感写 GPU 融合算子** → **Triton**；
- 想给 **整个 PyTorch 模型加速** → `torch.compile`。

### 1.3 一张图看清 Numba 在栈里的位置

```
┌─────────────────────────────────────────────────┐
│   Python 用户代码（NumPy / SciPy / 你的项目）    │
├─────────────────────────────────────────────────┤
│   @njit / @cuda.jit 装饰器                       │
├──────────────────┬──────────────────────────────┤
│  Numba (CPU)      │  Numba (CUDA)                │
│  Python → LLVM IR │  Python → NVVM IR            │
│  → x86/ARM 汇编    │  → PTX → SASS                │
├──────────────────┴──────────────────────────────┤
│   CPU / GPU 硬件                                 │
└─────────────────────────────────────────────────┘
```

**核心洞察**：Numba 的两个后端**共享同一个前端**（Python 语法解析），所以你学会 `@njit` 后转 `@cuda.jit` 只需要多学"CUDA 心智模型"这一件事。

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 平台选择：三方案对比

**好消息**：与 Triton 不同，**Numba 对 Windows 原生支持一流**！

| 方案 | 难度 | 推荐度 |
|:--|:--|:--|
| **Windows 原生（Anaconda）** | 低 | ⭐⭐⭐⭐⭐ 强烈推荐 |
| **WSL2 + Ubuntu 22.04** | 低 | ⭐⭐⭐⭐ |
| **原生 Linux** | 低 | ⭐⭐⭐⭐ |

以下按 **Windows 原生 + Anaconda** 步骤讲（这也是 Numba 官方最推荐的方式）。

### 2.2 Windows 一次性搭建

```powershell
# 1. 装 Miniconda（如果没有）
#    https://docs.conda.io/projects/miniconda/en/latest/

# 2. 建虚拟环境
conda create -n numba python=3.10 -y
conda activate numba

# 3. 装 Numba + NumPy（conda 源里的 Numba 会带上匹配的 llvmlite）
conda install -c conda-forge numba numpy -y

# 4. 装 CUDA Toolkit（Numba 需要 nvvm.dll）
#    强烈推荐用 conda 装，避免踩 PATH 坑
conda install -c nvidia cuda-toolkit=12.1 -y

# 5.（可选）装 CuPy，方便和 Numba 混用 GPU 数组
conda install -c conda-forge cupy -y
```

> 💡 **CUDA Toolkit 一定要装**——纯 `pip install numba` 只装了 CPU 后端，GPU 需要 `nvvm.dll` 和 `libdevice.bc`，这两个文件在 CUDA Toolkit 里。用 conda 装最省事，环境变量自动配好。

### 2.3 环境验证脚本

```python
# check_numba.py
import numba
from numba import cuda
import numpy as np

print("numba      :", numba.__version__)
print("CUDA avail :", cuda.is_available())

if cuda.is_available():
    print("Device     :", cuda.get_current_device().name.decode())
    print("CC         :", cuda.get_current_device().compute_capability)
    # 跑一个最小 kernel
    @cuda.jit
    def add(a, b, c):
        i = cuda.grid(1)
        if i < a.size:
            c[i] = a[i] + b[i]
    n = 1024
    a = np.arange(n, dtype=np.float32)
    b = np.arange(n, dtype=np.float32)
    c = np.zeros_like(a)
    add[8, 128](a, b, c)   # 8 blocks × 128 threads
    print("kernel ok  :", np.allclose(c, a + b))
```

**期望输出**：

```
numba      : 0.59.x
CUDA avail : True
Device     : NVIDIA GeForce RTX 3060
CC         : (8, 6)
kernel ok  : True
```

看到这 4 行就说明 **Windows 驱动 + CUDA Toolkit + Numba** 全部串通了。

### 2.4 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| `NvvmSupportError: libNVVM cannot be found` | Numba 找不到 `nvvm.dll` | 用 conda 装 `cuda-toolkit`，或设 `NUMBA_CUDA_DRIVER` |
| `CudaAPIError: [100] no CUDA-capable device is detected` | 驱动或 WSL2 GPU 未通 | 更新 NVIDIA 驱动到最新 |
| 第一次 `@njit` 函数卡 3~10 秒 | **首次 JIT 编译**，正常 | 有 `__pycache__/*.nbi` 缓存，第二次就秒开 |
| `TypingError: Cannot determine Numba type of ...` | 用了 Numba 不支持的类型（`str`、`dict`、`pandas`） | 只用 NumPy 数组和 Python 基本类型 |
| `@cuda.jit` 里 print 没输出 | GPU 端 `print` 有缓冲 | Numba 支持 device print，但要用 `cuda.synchronize()` 刷 |

---

## 3. Numba CPU 模式：`@njit` 五分钟入门

**在学 GPU 之前，先花 5 分钟把 CPU 模式吃透——GPU 模式的心智模型就是它 + CUDA thread 概念。**

### 3.1 从"慢死了"到"飞起来"

**场景**：算一个数组每个元素的 sigmoid。

**纯 Python 循环（超慢）**：

```python
def sigmoid_py(x):
    y = np.empty_like(x)
    for i in range(x.shape[0]):
        y[i] = 1.0 / (1.0 + np.exp(-x[i]))
    return y

# 1_000_000 个元素：~1300 ms
```

**加一行装饰器（快 200 倍）**：

```python
from numba import njit

@njit(cache=True)          # 只加这一行
def sigmoid_nb(x):
    y = np.empty_like(x)
    for i in range(x.shape[0]):
        y[i] = 1.0 / (1.0 + np.exp(-x[i]))
    return y

# 1_000_000 个元素：~6 ms（快 ~200x）
```

**并行版（8 核 CPU 再快 4~8 倍）**：

```python
from numba import njit, prange

@njit(parallel=True, cache=True)
def sigmoid_par(x):
    y = np.empty_like(x)
    for i in prange(x.shape[0]):   # prange = 并行 range
        y[i] = 1.0 / (1.0 + np.exp(-x[i]))
    return y

# 1_000_000 个元素：~1 ms
```

### 3.2 三个必知装饰器参数

| 参数 | 作用 | 常用值 |
|:--|:--|:--|
| `cache=True` | 把编译结果存到磁盘，下次启动秒加载 | 生产环境必开 |
| `parallel=True` | 允许 `prange` 自动多核并行 | 大循环必开 |
| `fastmath=True` | 允许浮点重排（牺牲精度换速度） | 数值计算酌情开，AI 里少用 |
| `nogil=True` | 释放 Python GIL，可与线程配合 | 用多线程时开 |

**万能起手式**：

```python
@njit(cache=True, parallel=True, fastmath=True)
def my_hot_func(...): ...
```

### 3.3 Numba 支持哪些 Python？

| ✅ 支持 | ❌ 不支持 |
|:--|:--|
| NumPy 数组、基本数学函数 | pandas DataFrame |
| for / while / if / else / continue / break | 字符串复杂操作 |
| tuple、简单 list | dict（有限支持，慢） |
| 简单 class（`@jitclass`）| 复杂 class、继承、装饰器 |
| math 模块、部分 numpy 函数 | requests / os / 大部分标准库 |

**判定原则**：**你写的代码越像 C，Numba 越快**；越像面向对象 Python，越可能不支持。

---

## 4. 第一个 GPU Kernel：向量加法（对照 CUDA C++ 版）

### 4.1 完整可运行代码

```python
# vec_add_numba.py
import numpy as np
from numba import cuda

@cuda.jit
def add_kernel(a, b, c):
    i = cuda.grid(1)               # 全局 thread 编号，等价于 blockIdx.x * blockDim.x + threadIdx.x
    if i < a.size:
        c[i] = a[i] + b[i]


def add(a, b):
    n = a.size
    threads_per_block = 256
    blocks = (n + threads_per_block - 1) // threads_per_block

    # 把 NumPy 数组拷到 GPU（也可以直接传 NumPy，Numba 自动搬）
    d_a = cuda.to_device(a)
    d_b = cuda.to_device(b)
    d_c = cuda.device_array_like(a)

    add_kernel[blocks, threads_per_block](d_a, d_b, d_c)

    return d_c.copy_to_host()      # 拷回 CPU


if __name__ == "__main__":
    np.random.seed(0)
    a = np.random.randn(1_000_003).astype(np.float32)
    b = np.random.randn(1_000_003).astype(np.float32)

    c_nb  = add(a, b)
    c_ref = a + b

    print("max abs diff:", np.abs(c_nb - c_ref).max())
    assert np.allclose(c_nb, c_ref), "Numba 结果不对"
    print("✅ pass")
```

### 4.2 运行

```bash
python vec_add_numba.py
```

**期望输出**：

```
max abs diff: 0.0
✅ pass
```

（第一次跑因 JIT 编译停顿 3~5 秒，之后毫秒级。）

### 4.3 对照 CUDA C++ 版本，看看少了什么

| CUDA C++ 版要写 | Numba CUDA 版 |
|:--|:--|
| `__global__ void add(float* a, ...)` | `@cuda.jit def add(a, ...)` |
| `int i = blockIdx.x * blockDim.x + threadIdx.x;` | `i = cuda.grid(1)` |
| `cudaMalloc` / `cudaMemcpy` | `cuda.to_device` / `.copy_to_host()` |
| `add<<<blocks, threads>>>(...)` | `add[blocks, threads](...)` |
| `nvcc` 编译 | ❌ 不需要，运行时 JIT |
| `.cu` 文件 + Makefile | 一个 `.py` 文件搞定 |

**代码量**：CUDA C++ 60+ 行 → **Numba 25 行**，性能与手写 CUDA C++ **持平**（因为底层都翻译成 PTX）。

### 4.4 小白也能懂：4.1 代码逐行拆解

如果你是刚入门 GPU 编程的新手，看到 4.1 的 20 多行代码可能有一堆问号：`@cuda.jit` 是什么？`cuda.grid(1)` 里的 1 什么意思？`[blocks, threads_per_block]` 中括号为什么这么写？这一节把每一行讲透。

#### 4.4.1 先看整体结构：一个 Numba CUDA 程序有哪几块？

任何一个 Numba CUDA 程序从上到下都是**固定的三段式**：

```
┌─────────────────────────────────────────────┐
│ ① Kernel 函数（跑在 GPU 上）                 │  ← @cuda.jit 装饰的函数
│    def add_kernel(a, b, c):                 │     "一个 thread 干什么"
│        i = cuda.grid(1)                     │
│        c[i] = a[i] + b[i]                   │
├─────────────────────────────────────────────┤
│ ② Launcher 函数（跑在 CPU 上，负责启动）      │  ← 普通 Python 函数
│    def add(a, b):                           │     "分多少 block × thread 去干"
│        add_kernel[blocks, threads](...)     │
├─────────────────────────────────────────────┤
│ ③ 调用者（if __name__ == '__main__'）        │  ← 准备数据、验证结果
└─────────────────────────────────────────────┘
```

**记住这个结构**：以后写 reduction、matmul、图像卷积，骨架都是这三段。

#### 4.4.2 第 ① 段：Kernel 函数逐行讲

```python
@cuda.jit
def add_kernel(a, b, c):
    i = cuda.grid(1)
    if i < a.size:
        c[i] = a[i] + b[i]
```

**Line 1：`@cuda.jit`**
> **告诉 Numba："这个函数不是普通 Python，请编译成 GPU 代码。"**
> 首次调用时，Numba 会把它翻译成 PTX（GPU 汇编），第二次调用直接用缓存。
> **对照 CUDA C++**：等价于 `__global__` 关键字。

**Line 2：`def add_kernel(a, b, c):`**
> **三个 NumPy 数组，将被 Numba 自动转成 GPU 上的 device array**。
> 注意 kernel 函数**没有返回值**——GPU kernel 的"输出"只能通过写入传入的数组来实现。

**Line 3：`i = cuda.grid(1)`**
> **这是全篇最关键的一行**。它一次性算出"我这个 thread 的全局编号是多少"。
>
> - `cuda.grid(1)` 是 **1 维 grid** 的语法糖，等价于：
>   ```python
>   i = cuda.blockIdx.x * cuda.blockDim.x + cuda.threadIdx.x
>   ```
> - 如果你启动了 **8 个 block × 128 threads**，那么会有 **1024 个 thread** 同时跑这个 kernel，`i` 分别取 `0, 1, 2, ..., 1023`。
> - **每个 thread 靠 `i` 知道自己该处理哪个元素**。
>
> **对照 CUDA C++**：完全等价于 `int i = blockIdx.x * blockDim.x + threadIdx.x;`。
>
> **对照 Triton**：Triton 里没有 thread 级抽象——`tl.program_id(0)` 只到 block 级，block 内部由编译器自动向量化。Numba 保留了 CUDA 的 thread 级视角，**更"原始"，也更容易理解**。

**Line 4~5：`if i < a.size: c[i] = a[i] + b[i]`**
> **边界保护 + 干活**。
> - 因为 `blocks * threads_per_block` 一般会 ≥ `n`（有多余的 thread），必须判断 `i < a.size` 才能安全写入；
> - 每个 thread 只处理**一个元素**——这是 CUDA 的经典心智模型："一个 thread 一个元素"。
>
> **对照 Triton**：Triton 里一个 program 一次处理 `BLOCK` 个元素（向量化），Numba 里一个 thread 只处理 1 个（标量），**Numba 的心智更直白，Triton 的心智更高效**。

**至此 kernel 结束**——**只有 3 行有效代码**，比 CUDA C++ 的等价实现少 90%。

#### 4.4.3 第 ② 段：Launcher 函数逐行讲

```python
def add(a, b):
    n = a.size
    threads_per_block = 256
    blocks = (n + threads_per_block - 1) // threads_per_block

    d_a = cuda.to_device(a)
    d_b = cuda.to_device(b)
    d_c = cuda.device_array_like(a)

    add_kernel[blocks, threads_per_block](d_a, d_b, d_c)

    return d_c.copy_to_host()
```

**Line 3：`threads_per_block = 256`**
> **每个 block 里放多少 thread**。
> - **必须是 32 的倍数**（一个 warp = 32 thread，凑不齐会浪费）；
> - 典型值 128 / 256 / 512；256 是"闭眼选"的默认值。
> **对照 CUDA C++**：等价于 `dim3 block(256);`。

**Line 4：`blocks = (n + threads_per_block - 1) // threads_per_block`**
> **向上取整**计算需要多少个 block。
> - `n = 1_000_003, threads = 256` → `blocks = 3907`；
> - `3907 * 256 = 1_000_192`，比 `n` 略多 189 个，这 189 个 thread 会被 `if i < a.size` 挡掉。
> **对照 CUDA C++**：`dim3 grid((n + 255) / 256);`。

**Line 6~8：`cuda.to_device` / `cuda.device_array_like`**
> **把 NumPy 数组从 CPU 内存搬到 GPU 显存**。
> - `to_device(a)`：把已有数据拷过去；
> - `device_array_like(a)`：在 GPU 上分配**同 shape 同 dtype** 的空数组（不拷贝）。
> - **省事写法**：如果直接把 NumPy 数组传给 kernel，Numba 会自动 to_device + copy_to_host（但每次都拷贝，浪费带宽）；**性能关键路径要显式管理**。
> **对照 CUDA C++**：`cudaMalloc` + `cudaMemcpy`。

**Line 10：`add_kernel[blocks, threads_per_block](d_a, d_b, d_c)`**
> **正式启动 kernel**。这行做了三件事：
> 1. **`add_kernel[blocks, threads_per_block]`** —— Numba 特有的**中括号语法**指定 grid 和 block 大小；
> 2. **传参**：三个 device array 作为参数；
> 3. **异步执行**：这行**立即返回**，kernel 在 GPU 后台跑；当你调 `copy_to_host()` 时会自动等它跑完。
>
> **对照 CUDA C++**：`add<<<blocks, threads_per_block>>>(a, b, c);`。
> **对照 Triton**：`add_kernel[grid](a, b, c, ..., BLOCK_SIZE=1024)`——Triton 中括号里只有 grid，因为 block 内部是 program 级向量化。

**Line 12：`return d_c.copy_to_host()`**
> **把 GPU 上的结果拷回 CPU 内存**，返回 NumPy 数组给用户。
> 如果你后面还要在 GPU 上继续算（比如接下一个 kernel），**不要拷回来**——直接把 `d_c` 传给下一个 kernel 即可。

#### 4.4.4 第 ③ 段：调用者（测试代码）

```python
a = np.random.randn(1_000_003).astype(np.float32)
b = np.random.randn(1_000_003).astype(np.float32)
c_nb  = add(a, b)
c_ref = a + b
assert np.allclose(c_nb, c_ref)
```

**永远先写一个 NumPy 参考实现来验证正确性，再看性能**——这是写任何 GPU kernel 的黄金习惯。

#### 4.4.5 一图串起来：数据流向

```
CPU（Python 进程）                    GPU（3060）
─────────────────────────────────────────────────────────────
a = np.random.randn(1_000_003)
b = np.random.randn(1_000_003)
                                    │
    cuda.to_device(a)         ═══► GPU 显存里存着 4MB float32
    cuda.to_device(b)         ═══► GPU 显存里存着 4MB float32
    device_array_like(a)      ═══► GPU 显存预留 4MB 空间
                                    │
    blocks = 3907
    threads = 256              ─── 告诉 GPU："启动 3907 × 256 = 1_000_192 个 thread"
                                    │
                                    ▼
add_kernel[3907, 256](...)   ═══► GPU 上：
                                    Thread #0    ： c[0]    = a[0]    + b[0]
                                    Thread #1    ： c[1]    = a[1]    + b[1]
                                    ...
                                    Thread #999999：c[999999]= a[999999] + b[999999]
                                    Thread #1000000 ~ #1000191：被 if 挡掉
                                    ↓
                                    1 million 个 thread 并行跑（分成 3907 个 block，每个 block 8 warp）
                                    ↓
                                    d_c 显存里被填好
                                    │
d_c.copy_to_host()         ◄═══     拷回 CPU 内存
```

**理解到这一步，Numba CUDA 的心智模型你就通了**：
- **一个 kernel = 一份"每个 thread 干什么"的说明书**；
- **blocks × threads = "启动多少个 thread"**；
- **`cuda.grid(1)` = "我是第几号 thread"**；
- **`if i < n` = "别越界"**。

#### 4.4.6 新手最容易踩的 5 个坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | 忘了写 `if i < n` | 越界读写，随机崩溃 | 只要 n 不是 threads 整数倍，**必须**加边界检查 |
| 2 | 直接传 NumPy 数组，性能崩了 | 每次调 kernel 都在拷贝 | 用 `cuda.to_device` 显式管理，避免重复拷贝 |
| 3 | `threads_per_block` 不是 32 倍数 | 性能差 20~50% | 用 128 / 256 / 512 |
| 4 | 首次运行卡 3~10 秒 | 以为死机 | 正常，JIT 编译中；用 `cache=True` 或 `@cuda.jit(cache=True)` 缓存 |
| 5 | 忘了 `.astype(np.float32)` | GPU 上 float64 慢 8 倍以上 | 数值计算尽量用 float32 |

**读完 4.4，你应该能自信地说**：4.1 的每一行都懂了、能默写、能仿写一个 `mul_kernel`（`+` → `*` 就是了）。这就是 Numba CUDA "入门"的门槛。

---

## 5. 三大必修 Kernel：Reduction / Matmul / 图像模糊

### 5.1 Reduction（求和）—— CUDA 的教科书案例

**为什么练它**：Reduction 是所有 GPU 编程教材的开篇案例，因为它逼你理解 **shared memory + 树形归约 + warp shuffle**——这三样是所有高性能 kernel 的地基。

**最简版（用 atomic，慢但对）**：

```python
from numba import cuda
import numpy as np

@cuda.jit
def sum_atomic(x, out):
    i = cuda.grid(1)
    if i < x.size:
        cuda.atomic.add(out, 0, x[i])   # 所有 thread 加到同一个位置

x = np.random.randn(1_000_000).astype(np.float32)
d_x = cuda.to_device(x)
d_out = cuda.to_device(np.zeros(1, dtype=np.float32))
sum_atomic[3907, 256](d_x, d_out)
print(d_out.copy_to_host()[0], "vs", x.sum())
```

**优化版（block 内 shared memory 归约）**：

```python
@cuda.jit
def sum_block(x, out):
    TPB = 256
    shared = cuda.shared.array(TPB, dtype=np.float32)   # block 内共享内存

    tid = cuda.threadIdx.x
    i   = cuda.grid(1)

    shared[tid] = x[i] if i < x.size else 0.0
    cuda.syncthreads()

    # 树形归约
    stride = TPB // 2
    while stride > 0:
        if tid < stride:
            shared[tid] += shared[tid + stride]
        cuda.syncthreads()
        stride //= 2

    # 每个 block 的 0 号 thread 把结果加到全局
    if tid == 0:
        cuda.atomic.add(out, 0, shared[0])
```

**关键知识点**：
- **`cuda.shared.array(N, dtype)`**：block 内 N 个元素的共享内存（比 global 显存快 100 倍）；
- **`cuda.syncthreads()`**：同步 block 内所有 thread（不同步会读到未写完的数据）；
- **树形归约**：`log(N)` 步把 N 个数加起来；
- **atomic 用在 block 之间**（每个 block 一次），而不是每个元素——**这是 GPU 性能的关键设计模式**。

### 5.2 Matmul（矩阵乘）—— tile 的经典应用

```python
TPB = 16   # tile per block

@cuda.jit
def matmul_tiled(A, B, C):
    sA = cuda.shared.array((TPB, TPB), dtype=np.float32)
    sB = cuda.shared.array((TPB, TPB), dtype=np.float32)

    row, col = cuda.grid(2)
    tx = cuda.threadIdx.x
    ty = cuda.threadIdx.y

    if row >= C.shape[0] or col >= C.shape[1]:
        return

    tmp = 0.0
    n_tiles = (A.shape[1] + TPB - 1) // TPB
    for t in range(n_tiles):
        # 每个 thread 从 A、B 里协作加载一个元素到 shared memory
        sA[ty, tx] = A[row, t * TPB + tx] if t * TPB + tx < A.shape[1] else 0.0
        sB[ty, tx] = B[t * TPB + ty, col] if t * TPB + ty < B.shape[0] else 0.0
        cuda.syncthreads()

        for k in range(TPB):
            tmp += sA[ty, k] * sB[k, tx]
        cuda.syncthreads()

    C[row, col] = tmp

# 启动
M, N, K = 1024, 1024, 1024
A = np.random.randn(M, K).astype(np.float32)
B = np.random.randn(K, N).astype(np.float32)
C = np.zeros((M, N), dtype=np.float32)

d_A, d_B, d_C = cuda.to_device(A), cuda.to_device(B), cuda.to_device(C)
threads = (TPB, TPB)
blocks  = ((N + TPB - 1) // TPB, (M + TPB - 1) // TPB)
matmul_tiled[blocks, threads](d_A, d_B, d_C)
```

**知识点**：
- **2D grid + 2D block**：`cuda.grid(2)` 返回 `(row, col)`；
- **协作加载**：block 内 `TPB × TPB` 个 thread 各加载一个元素到 shared memory；
- **两次 `syncthreads()`**：加载后、计算后各一次，缺一崩溃。

**性能对比**（RTX 3060，1024×1024 fp32）：

| 方案 | 时间 | 相对 cuBLAS |
|:--|:--|:--|
| NumPy CPU | ~50 ms | 太慢 |
| Numba `@cuda.jit` 朴素版（无 shared） | ~5 ms | ~30% |
| Numba `@cuda.jit` tiled 版 | ~1.5 ms | ~70% |
| Triton 教学版 | ~0.9 ms | ~90% |
| cuBLAS (`np.dot` on CuPy) | ~0.6 ms | 100% |

**结论**：Numba tiled matmul 能到 cuBLAS 的 60~70%，够很多科研/内部工具用；但要打 cuBLAS 90%+ 还是 Triton / CUTLASS 更合适。

### 5.3 图像高斯模糊 —— 最直观的 GPU 应用

思路：每个 thread 处理一个像素，读周围 5×5 邻域加权平均。**代码 ~30 行**，是把 CUDA 心智模型和 shared memory 用起来的绝佳练手项目——2K 图像典型能从 NumPy 的 200 ms 降到 Numba GPU 的 2 ms（**100 倍加速**）。

---

## 6. 进阶特性：共享内存 / 原子操作 / Stream

### 6.1 共享内存（Shared Memory）

**block 内**所有 thread 共享的一小块 SRAM（3060 上每个 SM 有 100KB），**比 global 显存快 100 倍**。

```python
# 静态大小（编译期常量）
shared = cuda.shared.array(shape=(16, 16), dtype=np.float32)

# 动态大小（launch 时指定）
@cuda.jit
def kernel(x):
    dyn_shared = cuda.shared.array(0, dtype=np.float32)   # 大小由启动参数决定
    ...
# 启动时：kernel[grid, block, 0, shared_bytes](x)
```

**使用铁律**：
1. **写完必须 `syncthreads()` 再读**；
2. **别开太大**（每个 SM 最多 ~100KB），否则 occupancy 直接掉；
3. **避免 bank conflict**：同一 warp 里 32 个 thread 访问的地址如果落到同一个 bank 的不同行，性能下降 32 倍。

### 6.2 原子操作（Atomic）

多个 thread 要更新同一个变量时，必须用 atomic：

```python
cuda.atomic.add(arr, index, value)      # arr[index] += value
cuda.atomic.max(arr, index, value)      # 支持 max/min/compare-and-swap
```

**慎用**：atomic 会**串行化**——所有对同一位置的更新会排队。**规则：atomic 只用来聚合 block 级结果，不要在 thread 级用**。

### 6.3 Stream（异步流）

默认所有 kernel 在**同一个 stream** 上按顺序执行。要重叠 kernel 和 memcpy，需要多个 stream：

```python
stream1 = cuda.stream()
stream2 = cuda.stream()

d_a = cuda.to_device(a, stream=stream1)
kernel[grid, block, stream1](d_a, d_b)
d_b.copy_to_host(stream=stream2)      # 与 kernel 并行
cuda.synchronize()                     # 等所有 stream 完成
```

**典型场景**：数据分批 GPU 处理，边算边拷回。

### 6.4 device 函数（`@cuda.jit(device=True)`）

在 kernel 里调用另一个函数，需要标注 `device=True`：

```python
@cuda.jit(device=True, inline=True)
def sigmoid_dev(x):
    return 1.0 / (1.0 + math.exp(-x))

@cuda.jit
def apply_sigmoid(x, y):
    i = cuda.grid(1)
    if i < x.size:
        y[i] = sigmoid_dev(x[i])
```

---

## 7. 集成到 NumPy / PyTorch / CuPy

### 7.1 与 NumPy 无缝

```python
# NumPy 数组直接传给 @cuda.jit，自动 to_device + copy_to_host
my_kernel[grid, block](numpy_array_in, numpy_array_out)
```

**代价**：每次都全量拷贝，热点场景要用 `cuda.to_device` 显式管理。

### 7.2 与 PyTorch 共享显存（零拷贝）

```python
import torch
from numba import cuda

t = torch.randn(1024, device='cuda')
# 关键：PyTorch Tensor 和 Numba device array 共享 CUDA 显存
d_arr = cuda.as_cuda_array(t)      # 零拷贝转换

my_kernel[grid, block](d_arr)      # 直接用
# 修改会反映到 t 上
```

**用途**：PyTorch 模型中间插入一段 Numba 自定义算子，**免拷贝**。

### 7.3 与 CuPy 互通

```python
import cupy as cp
from numba import cuda

x = cp.random.randn(1024)          # CuPy 数组
d_x = cuda.as_cuda_array(x)         # 零拷贝转 Numba

my_kernel[grid, block](d_x)
```

**用途**：CuPy 处理数据 pipeline + Numba 写自定义 kernel，**GPU 端一条龙**。

### 7.4 常见陷阱

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 传 NumPy 数组时性能极差 | 每次调 kernel 都在 host↔device 拷贝 | 用 `cuda.to_device` 显式管理 |
| PyTorch Tensor 传进去报错 | 忘了 `cuda.as_cuda_array` | `d = cuda.as_cuda_array(tensor)` |
| 精度对不上 PyTorch | dtype 是 float64（NumPy 默认） | `.astype(np.float32)` |
| kernel 里 print 没输出 | 没同步 | 加 `cuda.synchronize()` 刷 device print 缓冲 |

---

## 8. 性能分析：怎么知道 Numba 到底跑得多快？

### 8.1 用 `%timeit` / `time.perf_counter`

```python
import time
from numba import cuda

# 预热（避免把 JIT 编译时间算进去）
for _ in range(3):
    my_kernel[grid, block](d_x)
cuda.synchronize()

# 计时
t0 = time.perf_counter()
for _ in range(100):
    my_kernel[grid, block](d_x)
cuda.synchronize()      # ⚠️ kernel 异步，一定要 sync 才是真时间
t1 = time.perf_counter()
print(f"{(t1 - t0) / 100 * 1000:.3f} ms")
```

**关键**：GPU kernel 是异步的，**不 `synchronize` 测出来的时间全是假的**（就是 launch 开销）。

### 8.2 用 CUDA Event（更精确）

```python
start = cuda.event()
end   = cuda.event()

start.record()
my_kernel[grid, block](d_x)
end.record()
end.synchronize()

print(f"{cuda.event_elapsed_time(start, end):.3f} ms")
```

### 8.3 用 Nsight Compute 看 kernel 细节

Numba 生成的 PTX/SASS 可以像 CUDA C++ 一样被 Nsight Compute 分析：

```bash
ncu --set full --target-processes all python bench.py
```

- 关键指标：`dram__throughput`（HBM 带宽利用率）、`smsp__thread_inst_executed_per_inst_executed`（warp 效率）、`sm__warps_active`（occupancy）；
- Numba 生成的 kernel 名字带 `numba_dppy_` 或 `add_kernel$xxx`，别慌，就是 mangling。

### 8.4 三条经验法则

1. **memory-bound** kernel（element-wise）：**看 HBM 带宽**，跑到峰值 70%+ 就算胜利；
2. **compute-bound** kernel（matmul）：Numba 不用 Tensor Core（只支持普通 CUDA core），**上限就是 3060 的 12 TFLOPS fp32**，够不着 Tensor Core 的 51 TFLOPS；
3. **要 Tensor Core** → 换 Triton 或 CuPy 底层的 cuBLAS。

---

## 9. Numba vs Triton：何时该用谁？

**这是所有学完 Numba 的人第一个会问的问题**，简答如下：

### 9.1 一表看清

| 维度 | Numba `@cuda.jit` | Triton `@triton.jit` |
|:--|:--|:--|
| 抽象层级 | **Thread 级**（一 thread 一元素） | **Block 级**（一 program 一块） |
| 心智模型 | CUDA C++ 的 Python 直译 | NumPy 的 GPU 版 |
| Tensor Core | ❌ 不支持 | ✅ `tl.dot` 自动用 |
| Autotune | ❌ 手动 | ✅ `@triton.autotune` |
| Windows 原生 | ✅ 完美 | ⚠️ 差，需 WSL2 |
| 学习曲线 | 平缓（会 CUDA 就会） | 稍陡（要换心智模型） |
| 代码量 | 中（tiled matmul ~50 行） | 短（tiled matmul ~30 行） |
| 性能上限 | cuBLAS 的 60~70% | cuBLAS 的 90~100% |
| 生态定位 | 通用科学计算、遗产 CUDA 迁移 | **AI 融合算子首选** |
| 与 PyTorch | 零拷贝互通 | 原生集成，`torch.compile` 后端 |

### 9.2 选型决策树

```
你的场景是什么？
    │
    ├─ 已经熟 CUDA C++、想搬 Python
    │      → Numba（心智直译，最省事）
    │
    ├─ 科学计算 / 蒙特卡洛 / 图像处理
    │      → Numba（不需要 Tensor Core）
    │
    ├─ AI 算子（Attention、GEMM、Norm）
    │      → Triton（要 Tensor Core + autotune）
    │
    ├─ 要打赢 cuBLAS/cuDNN
    │      → Triton 或 CUTLASS（Numba 够不着）
    │
    ├─ 要跑在 Windows 原生
    │      → Numba（Triton 要 WSL2）
    │
    └─ 快速原型验证
           → Numba（Python 手感最好）
```

### 9.3 一句话总结

> **Numba 是"Python 版 CUDA C++"，Triton 是"GPU 版 NumPy"**。
> 前者适合科学计算和 Python 加速的通用场景，后者是 AI Kernel 的新时代武器。**两者不冲突，很多项目会同时用**（Numba 做数据预处理 + Triton 做模型算子）。

---

## 10. 学习路线图（3~5 周）

### 🟢 阶段 1（Week 1）：CPU `@njit` 入门

- ✅ 装好 Numba + CUDA Toolkit（Windows 原生就行）
- ✅ 用 `@njit` 给至少 3 段自己的 Python 循环提速
- ✅ 用 `@njit(parallel=True)` + `prange` 尝试多核
- ✅ 通读 Numba 官方 5-minute guide

### 🟡 阶段 2（Week 2）：GPU `@cuda.jit` 入门

- ✅ 跑通向量加法、element-wise
- ✅ 理解 `cuda.grid` / `blockIdx` / `threadIdx`
- ✅ 手写 `sigmoid_kernel`、`relu_kernel`
- ✅ 用 `cuda.to_device` 显式管理拷贝

### 🟠 阶段 3（Week 3）：Shared Memory + Reduction

- ✅ 实现 shared memory 版 sum reduction
- ✅ 实现 tiled matmul，跑到 cuBLAS 60%+
- ✅ 理解 `syncthreads` / bank conflict
- ✅ 用 Nsight Compute 看 occupancy

### 🔴 阶段 4（Week 4~5）：进阶 + 集成

- ✅ 使用 stream 实现 kernel + memcpy 重叠
- ✅ 与 PyTorch / CuPy 零拷贝互通
- ✅ 写一个完整应用（如：蒙特卡洛期权定价、图像模糊 pipeline、粒子仿真）
- ✅ 对比 Numba vs CuPy vs PyTorch，理解各自定位

### 🎯 里程碑（做完就是 N3）

- 给自己项目里最慢的一个函数写 GPU 版本，实测 20x+ 加速；
- 用 Numba + shared memory 复现一个经典算法（卷积 / stencil / N-body）；
- 读懂 SciPy / scikit-learn / RAPIDS 里至少一个 Numba 优化过的函数源码。

---

## 11. 精选资源与踩坑清单

### 11.1 必读官方资源

| 资源 | 用途 | 链接 |
|:--|:--|:--|
| Numba 官方文档 | API 参考 + 5-minute guide | <https://numba.readthedocs.io/> |
| Numba CUDA 章节 | GPU 后端专章 | <https://numba.readthedocs.io/en/stable/cuda/index.html> |
| Numba GitHub | 源码、issue | <https://github.com/numba/numba> |
| NVIDIA CUDA Python | 与 Numba 互补的官方项目 | <https://github.com/NVIDIA/cuda-python> |
| RAPIDS 官网 | Numba 在数据科学的最大应用场景 | <https://rapids.ai/> |
| Anaconda Numba Tutorials | 系统教程集合 | <https://github.com/ContinuumIO/gtc2020-numba> |

### 11.2 高质量博客/讲解

- **Numba 官方 GTC 视频**：NVIDIA GTC 每年都有 Numba 专题，讲解最新特性；
- **Anaconda Blog**：Numba 主要维护方，博客有大量案例；
- **Real Python: Numba** —— 面向 Python 老手的入门文章；<https://realpython.com/numba-python/>
- **《High Performance Python》 by Micha Gorelick**：书中 Numba 章节是必读经典。

### 11.3 完整踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 首次运行卡很久 | JIT 编译 | 用 `cache=True` 缓存到磁盘 |
| `TypingError: Cannot determine Numba type` | 传入 Numba 不支持的类型（dict / str / DataFrame） | 拆成 NumPy 数组和基本类型 |
| `NvvmSupportError: libNVVM cannot be found` | 缺 CUDA Toolkit | `conda install -c nvidia cuda-toolkit=12.1` |
| GPU kernel 结果全 0 | 忘了 `copy_to_host()` 或数组是 device_array 但没传对 | 检查数据流向 |
| 性能提升不明显 | 循环体本身就是 NumPy 向量化，Numba 没优化空间 | Numba 擅长"NumPy 做不到的循环"，同类型场景效果有限 |
| `@cuda.jit` 里用了 NumPy 函数报错 | 大部分 NumPy 函数在 device 上不支持 | 用 `math` 模块（`math.exp` 代替 `np.exp`）|
| shared memory 数组报错 | 大小不是编译期常量 | 用 `cuda.shared.array(TPB, ...)`，`TPB` 是全局常量 |
| 结果对但没变快 | 忘了 `synchronize`，测的是 launch 时间 | 计时前后加 `cuda.synchronize()` |
| Occupancy 只有 30% | shared memory 或寄存器用太多 | 缩小 shared array、降低 TPB |
| 与 PyTorch 传数据报错 | 忘了 `cuda.as_cuda_array` | 用它做零拷贝转换 |
| `@njit` 报 `NUMBA_DISABLE_JIT` 相关错 | 环境变量污染 | `unset NUMBA_DISABLE_JIT` |

### 11.4 一句话总结

> **Numba = "Python 加速的性价比之王"**——CPU 上一行装饰器提速 100x，GPU 上让每个 Python 程序员都能写 CUDA。
> **学它的成本极低**（一天入门），**收益却常常巨大**——从科学计算到工程原型，是每个 Python 老手都该掌握的工具。

---

**祝你 Python 越写越快，热点函数一个都不留。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
