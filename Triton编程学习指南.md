# Triton 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-10

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：已经会用 PyTorch，读过《面向 AI 的 CUDA 编程学习指南》或至少理解 grid/block/thread 心智模型，想用**更少的代码写出接近手写 CUDA 性能**的算子的程序员。
> **目标**：4~6 周内，从"写第一个 Triton kernel"到"能读改 FlashAttention 的 Triton 实现、能给 PyTorch 写融合算子"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1** + PyTorch 2.x + Triton ≥ 3.0。

---

## 目录

- [0. 写在最前：为什么要学 Triton？](#0-写在最前为什么要学-triton)
- [1. Triton 是什么：一句话讲清 vs CUDA / vs torch.compile](#1-triton-是什么一句话讲清-vs-cuda--vs-torchcompile)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. Triton 编程模型：Block-level 编程范式](#3-triton-编程模型block-level-编程范式)
- [4. 第一个 Kernel：向量加法（对照 CUDA 版）](#4-第一个-kernel向量加法对照-cuda-版)
- [5. 三大必修 Kernel：Softmax / GEMM / LayerNorm](#5-三大必修-kernelsoftmax--gemm--layernorm)
- [6. 自动调优（`@triton.autotune`）：Triton 的杀手锏](#6-自动调优tritonautotunetriton-的杀手锏)
- [7. 集成到 PyTorch：写一个自定义融合算子](#7-集成到-pytorch写一个自定义融合算子)
- [8. 性能分析：怎么知道 Triton 到底跑得多快？](#8-性能分析怎么知道-triton-到底跑得多快)
- [9. 进阶：读懂 FlashAttention 的 Triton 实现](#9-进阶读懂-flashattention-的-triton-实现)
- [10. 学习路线图（4~6 周）](#10-学习路线图46-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 Triton？

作为已经会写 CUDA 或至少读过 CUDA 的程序员，可能会问：**都能写 CUDA 了，为什么还要学 Triton？** 答案是 **"20 行 Python 追平 200 行 CUDA C++"**——Triton 让你把精力从 index 计算、shared memory 手动搬运、bank conflict 里解放出来，专注于算法本身。

### 0.1 一句话对比

| 需求 | 用 CUDA C++ | 用 Triton |
|:--|:--|:--|
| 写一个 fused softmax | 100~150 行，手动管 shared memory | **~30 行 Python** |
| 写一个 GEMM 打到 cuBLAS 80% | 300+ 行 + 手写 tile / async copy | **~50 行 + `@autotune`** |
| 支持多种 dtype / shape | 大量模板特化 | 参数化 + JIT 编译 |
| 修改 tile 大小 / warp 数 | 改代码重编 | 改一个数字 |
| 集成到 PyTorch | 需要 `setup.py` + `pybind11` | **直接 `import triton`** |

### 0.2 Triton 现在有多重要？

- **FlashAttention 系列**（v1/v2/v3 的公版参考实现）就是 Triton 写的；
- **PyTorch 2.x 的 `torch.compile`（Inductor 后端）** 生成的 GPU 代码 = **Triton**；
- **vLLM / Unsloth / Liger-Kernel / xFormers** 里越来越多的算子在从 CUDA C++ 迁移到 Triton；
- OpenAI、Meta、NVIDIA 都在深度使用/贡献 Triton。

**一句话**：**2024 年之后，AI Kernel 领域的新算子首选就是 Triton**，CUDA C++ 只在需要抠到极致（PTX/SASS 手调）或访问 Triton 没暴露的硬件特性（如 TMA、cluster）时才用。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **T1 入门** | 能写 vector add、element-wise、reduction，理解 `program_id` / `tl.load` / `tl.store` |
| **T2 熟练** | 会用 block-level 编程 + `mask`，能写 fused softmax / layernorm 打赢 PyTorch eager |
| **T3 高阶** | 会用 `@autotune`、能写 GEMM 打到 cuBLAS 80%+、能读 FlashAttention 源码 |
| **T4 专家** | 能给 Triton 提 PR、能用 `tl.inline_asm` 塞 PTX、能针对 SM86/90 分别调优 |

**建议**：直接冲到 **T2**（1~2 周），然后 **T3**（3~4 周），就能覆盖 90% 生产场景。

---

## 1. Triton 是什么：一句话讲清 vs CUDA / vs torch.compile

### 1.1 Triton 的定义

> **Triton 是一个 Python DSL + 编译器**：你用受限的 Python 语法写 kernel（长得像 NumPy 但作用在 GPU 一块数据上），Triton 把它编译成 PTX，最终在 GPU 上跑。

关键三点：

1. **Python 语法** —— 不用写 C++，不用管头文件、CMake、pybind11；
2. **Block-level 编程** —— 你写的是"一个 program 处理一块数据"，而不是"一个 thread 处理一个元素"（CUDA 是后者）；
3. **编译器帮你搞定**：shared memory 分配、bank conflict 规避、寄存器分配、warp 调度、访存合并。

### 1.2 Triton vs CUDA vs `torch.compile`

| 维度 | CUDA C++ | Triton | `torch.compile`（Inductor） |
|:--|:--|:--|:--|
| **谁写 kernel** | 你 | 你 | 编译器自动生成 |
| **抽象层级** | Thread 级 | **Block 级** | 图级（自动融合） |
| **门槛** | 高（要懂 shared memory / warp / bank conflict） | 中（会 NumPy 就行） | 低（`torch.compile(model)` 一行） |
| **性能上限** | 最高（可手抠 SASS） | 90~100% cuBLAS/cuDNN | 通常 80~95% |
| **灵活性** | 最高 | 高（能改 tile） | 低（黑盒） |
| **典型用途** | 极致优化 / 硬件独占特性 | 新算子快速产出 | 现有模型端到端加速 |

**记忆口诀**：
- 想让**整个模型变快** → `torch.compile`；
- 想为**某个算子写个自定义加速版** → **Triton**；
- 想榨干**每一个 cycle** → CUDA C++ + PTX。

### 1.3 一张图看清 Triton 在栈里的位置

```
┌────────────────────────────────────────────┐
│   Python / PyTorch 用户代码                 │
├────────────────────────────────────────────┤
│   torch.compile (Inductor) ──┐             │
│   xFormers / vLLM / FA       │             │
├────────────────────────────┐ │             │
│   @triton.jit 用户 kernel   │◄┘             │
├────────────────────────────┴──────────────┤
│   Triton 编译器：Triton IR → LLVM IR → PTX │
├────────────────────────────────────────────┤
│   NVIDIA Driver + PTX JIT / SASS           │
├────────────────────────────────────────────┤
│   GPU (SM / Tensor Core / HBM)             │
└────────────────────────────────────────────┘
```

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 平台选择：⚠️ 优先 Linux / WSL2

**Triton 对 Windows 原生支持很差**（截至 v3.x 仍无官方 Windows wheel）。三种可行方案：

| 方案 | 难度 | 推荐度 |
|:--|:--|:--|
| **WSL2 + Ubuntu 22.04** | 低 | ⭐⭐⭐⭐⭐ 强烈推荐 |
| **原生 Linux（双系统）** | 中 | ⭐⭐⭐⭐ |
| Windows 原生（第三方非官方 wheel） | 高，坑多 | ⭐ 不推荐 |

以下按 **WSL2 + Ubuntu 22.04** 步骤讲。

### 2.2 WSL2 一次性搭建

```powershell
# Windows PowerShell（管理员）
wsl --install -d Ubuntu-22.04
# 重启后进入 Ubuntu，创建用户名密码
```

进入 WSL2 Ubuntu：

```bash
# 1. 更新
sudo apt update && sudo apt upgrade -y

# 2. Python 3.10（Ubuntu 22.04 自带）
python3 --version   # 应该 >= 3.10

# 3. 装 pip、venv
sudo apt install -y python3-pip python3-venv build-essential

# 4. 建虚拟环境
python3 -m venv ~/venv-triton
source ~/venv-triton/bin/activate

# 5. 装 PyTorch (CUDA 12.1) + Triton
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install triton    # 从 PyTorch 2.1 起，triton 会作为依赖一起装
```

> 💡 WSL2 无需在里面单独装 CUDA Toolkit 和驱动——**驱动走 Windows 主机**，WSL2 内的 PyTorch 直接调用主机 GPU。装 `nvidia-cuda-toolkit` 反而会踩版本冲突坑。

### 2.3 环境验证脚本

```python
# check_triton.py
import torch, triton, triton.language as tl

print("torch      :", torch.__version__)
print("triton     :", triton.__version__)
print("CUDA avail :", torch.cuda.is_available())
print("Device     :", torch.cuda.get_device_name(0))
print("CC         :", torch.cuda.get_device_capability(0))
```

**期望输出**：

```
torch      : 2.x.x+cu121
triton     : 3.x.x
CUDA avail : True
Device     : NVIDIA GeForce RTX 3060
CC         : (8, 6)
```

看到这 5 行就说明 **Windows 驱动 + WSL2 + PyTorch + Triton** 全部串通了。

### 2.4 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| `RuntimeError: Triton Error [CUDA]: no kernel image is available` | Triton 编译目标架构错了 | 升级 Triton；或 `export TRITON_PTXAS_PATH=$(which ptxas)` |
| `libcuda.so.1: cannot open shared object file` | WSL2 里找不到 GPU 驱动 | 别在 WSL2 里装 CUDA 驱动，重装 Windows 驱动到最新 |
| 第一次运行 kernel 卡 30~60 秒 | Triton **首次 JIT 编译**，正常现象 | 有 `~/.triton/cache` 缓存，第二次就快了 |
| `AttributeError: module 'triton.language' has no attribute 'xxx'` | Triton 版本太老 | `pip install -U triton` |

---

## 3. Triton 编程模型：Block-level 编程范式

### 3.1 CUDA 心智 vs Triton 心智

**这是学 Triton 最重要的一节，理解了就通了一大半。**

CUDA 里你写的是**一个 thread 的行为**：

```cpp
// CUDA：一个 thread 加一个元素
__global__ void add(float* a, float* b, float* c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) c[i] = a[i] + b[i];   // 每个 thread 处理 1 个元素
}
```

Triton 里你写的是**一个 program（≈ CUDA block）对一整块数据的行为**：

```python
# Triton：一个 program 加一个 BLOCK 大小的数据块
@triton.jit
def add_kernel(a_ptr, b_ptr, c_ptr, n, BLOCK: tl.constexpr):
    pid  = tl.program_id(0)                    # 当前是第几个 block
    offs = pid * BLOCK + tl.arange(0, BLOCK)    # 这块要处理的 BLOCK 个下标
    mask = offs < n
    a = tl.load(a_ptr + offs, mask=mask)        # 一次 load BLOCK 个元素
    b = tl.load(b_ptr + offs, mask=mask)
    tl.store(c_ptr + offs, a + b, mask=mask)    # 一次 store BLOCK 个元素
```

**核心差异**：

| 维度 | CUDA | Triton |
|:--|:--|:--|
| 抽象单位 | 单个 thread | **单个 program（≈ block）** |
| 循环 32 个元素 | 32 个 thread 并行 | **1 行 `tl.arange(0, 32)`** |
| Shared memory | 你手动 `__shared__` 声明 | **编译器自动分配** |
| Warp 数量 / bank conflict | 你负责 | **编译器负责** |
| Mask 边界 | `if (i < n)` | `mask=offs<n`（向量化 mask）|

### 3.2 三个必知概念

**① `tl.program_id(axis)`** —— 对应 CUDA 的 `blockIdx.axis`。Triton 里没有 `threadIdx`，因为你根本不关心"哪个 thread"，只关心"这一整块数据的下标"。

**② `tl.arange(0, BLOCK)`** —— 生成一个 `[0,1,2,...,BLOCK-1]` 的向量。所有 Triton 运算都是**向量化的**，天然并行。

**③ `mask`** —— 用来处理"数据量不是 BLOCK 整数倍"的尾部。`tl.load(ptr, mask=..., other=0.0)` 会在 mask=False 处返回 `other`。

### 3.3 program / block / warp 三级映射

```
Triton 概念        对应 CUDA 概念       你要不要管
─────────────────────────────────────────────────
grid（1D/2D/3D）   grid                  ✅ 你决定（launch grid）
program            block                 ✅ 你决定（BLOCK 大小 = 一个 program 处理多少数据）
（隐藏）           warp                  ❌ 编译器管（可通过 num_warps 提示）
（隐藏）           thread                ❌ 完全不用管
```

**这就是 Triton 的"魔力"**：把最痛苦的**线程级并行细节**藏起来，让你像写 NumPy 一样写 GPU 代码。

---

## 4. 第一个 Kernel：向量加法（对照 CUDA 版）

### 4.1 完整可运行代码

```python
# vec_add_triton.py
import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(
    a_ptr, b_ptr, c_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,   # constexpr = 编译期常量
):
    pid  = tl.program_id(axis=0)
    offs = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offs < n_elements
    a = tl.load(a_ptr + offs, mask=mask)
    b = tl.load(b_ptr + offs, mask=mask)
    tl.store(c_ptr + offs, a + b, mask=mask)


def add(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    c = torch.empty_like(a)
    n = a.numel()
    # grid = 需要多少个 program 才能覆盖 n 个元素
    grid = lambda meta: (triton.cdiv(n, meta['BLOCK_SIZE']),)
    add_kernel[grid](a, b, c, n, BLOCK_SIZE=1024)
    return c


if __name__ == "__main__":
    torch.manual_seed(0)
    a = torch.randn(1_000_003, device='cuda', dtype=torch.float32)
    b = torch.randn_like(a)

    c_triton = add(a, b)
    c_torch  = a + b

    print("max abs diff:", (c_triton - c_torch).abs().max().item())
    assert torch.allclose(c_triton, c_torch), "Triton 结果不对"
    print("✅ pass")
```

### 4.2 运行

```bash
python vec_add_triton.py
```

**期望输出**：

```
max abs diff: 0.0
✅ pass
```

（第一次跑会因为 JIT 编译停顿几秒，第二次以后毫秒级启动。）

### 4.3 对照 CUDA 版本，看看少了什么

| CUDA 版本要写 | Triton 版本 |
|:--|:--|
| `cudaMalloc` / `cudaMemcpy` | ❌ 不需要，直接传 `torch.Tensor` |
| `__global__` / `blockIdx` / `threadIdx` | 换成 `@triton.jit` / `program_id` |
| `<<<grid, block>>>` 启动配置 | `add_kernel[grid](...)` |
| CMake / nvcc / MSVC 环境 | ❌ 不需要，纯 Python |
| 边界检查 `if (i < n)` | 向量化 `mask = offs < n` |

**代码量**：CUDA 60+ 行 → **Triton 25 行**，性能几乎一样。

### 4.4 小白也能懂：4.1 代码逐行拆解

如果你是刚入门 AI Kernel 的新手，看到 4.1 里的 20 多行代码可能会有一堆问号：`@triton.jit` 是什么？`tl.constexpr` 干嘛的？`pid * BLOCK_SIZE + tl.arange(...)` 为什么长这样？这一节就把每一行讲透。

#### 4.4.1 先看整体结构：一个 Triton 程序有哪几块？

任何一个 Triton kernel 从上到下都是**固定的三段式**，4.1 的代码也不例外：

```
┌─────────────────────────────────────────────┐
│ ① Kernel 函数（跑在 GPU 上）                 │  ← @triton.jit 装饰的函数
│    def add_kernel(...):                     │     "一个 program 干什么"
│        pid = tl.program_id(0)               │
│        ...                                  │
├─────────────────────────────────────────────┤
│ ② Launcher 函数（跑在 CPU 上，负责启动）      │  ← 普通 Python 函数
│    def add(a, b):                           │     "分多少个 program 去干"
│        add_kernel[grid](a, b, c, ...)       │
├─────────────────────────────────────────────┤
│ ③ 调用者（if __name__ == '__main__'）        │  ← 准备数据、验证结果
└─────────────────────────────────────────────┘
```

**记住这个结构**：以后不管你写 softmax、GEMM 还是 attention，代码骨架都是这三段。

#### 4.4.2 第 ① 段：Kernel 函数逐行讲

先把代码贴回来，方便对照：

```python
@triton.jit
def add_kernel(
    a_ptr, b_ptr, c_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    pid  = tl.program_id(axis=0)
    offs = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offs < n_elements
    a = tl.load(a_ptr + offs, mask=mask)
    b = tl.load(b_ptr + offs, mask=mask)
    tl.store(c_ptr + offs, a + b, mask=mask)
```

**逐行拆解**：

**Line 1：`@triton.jit`**
> **告诉 Triton："这个函数不是普通 Python 函数，请把它编译成 GPU 代码。"**
> `jit` = Just-In-Time，"即时编译"。首次调用时，Triton 会把这个函数翻译成 GPU 汇编（PTX），第二次调用就直接用缓存了。
> **对照 CUDA**：类似 `__global__` 关键字。

**Line 3：`a_ptr, b_ptr, c_ptr`**
> **三个"指针"，分别指向 A、B、C 三个 Tensor 在 GPU 显存里的首地址。**
> 你在 Launcher 里传的是 `torch.Tensor`，Triton 会自动帮你抽出 `.data_ptr()`。**理解成"C 语言里数组的首地址"就对了**。

**Line 4：`n_elements`**
> **告诉 kernel"总共有多少个元素要加"**。因为 GPU 上没有 `len()` 这种东西，长度必须显式传进来。

**Line 5：`BLOCK_SIZE: tl.constexpr`**
> **`constexpr` = "编译期常量"**——它的值在 kernel **编译时就要确定**，不能运行时才知道。
> 为什么必须是编译期常量？因为 Triton 编译器要靠它决定"每个 program 处理多大一块"、"用几个寄存器"、"要不要展开循环"。你在 4.1 里传的是 `BLOCK_SIZE=1024`，这个 1024 是编译到 GPU 代码里的常数。
> **对照 CUDA**：类似 C++ 模板参数 `template<int BLOCK_SIZE>`。

**Line 7：`pid = tl.program_id(axis=0)`**
> **"我是第几个 program？"**
> 假设你启动了 1000 个 program，那么 1000 个 program 会同时跑同一份 kernel 代码，只是 `pid` 分别是 `0, 1, 2, ..., 999`。**这是唯一区分它们的东西**——每个 program 靠 `pid` 知道自己该处理数据的哪一段。
> **对照 CUDA**：完全等价于 `blockIdx.x`。

**Line 8：`offs = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)`**
> **这是全篇最关键的一行**。它一次性算出"这个 program 要处理的 `BLOCK_SIZE` 个下标"。
>
> 假设 `BLOCK_SIZE=1024`，展开一下：
> - `pid=0` 时：`offs = 0 * 1024 + [0,1,2,...,1023] = [0,1,2,...,1023]`
> - `pid=1` 时：`offs = 1 * 1024 + [0,1,2,...,1023] = [1024,1025,...,2047]`
> - `pid=2` 时：`offs = 2 * 1024 + [0,1,2,...,1023] = [2048,2049,...,3071]`
> - ......
>
> **每个 program 各自负责一段连续的下标**，拼起来就覆盖了全部数据。
>
> 注意：`tl.arange(0, BLOCK_SIZE)` **不是 Python 的 `range()`**，它返回一个"**向量**"（可以理解为一个长度为 1024 的数组），后面所有 `tl.load / tl.store` 都直接对整个向量操作——这就是 Triton 的"**Block-level 编程**"精髓：**你不需要写 for 循环遍历 1024 个元素，一行搞定**。
>
> **对照 CUDA**：CUDA 里你要写 `int i = blockIdx.x * blockDim.x + threadIdx.x;`（每个 thread 一个 i）。Triton 里没有 threadIdx，`offs` 本身就是一个"下标向量"，一个 program 直接拿到 1024 个下标。

**Line 9：`mask = offs < n_elements`**
> **边界保护**。数据长度不一定正好是 `BLOCK_SIZE` 的整数倍——比如 4.1 里的 `n = 1_000_003`，`1_000_003 / 1024 ≈ 977.5`，也就是要 **978 个 program**，最后一个 program 的下标会超出 `n_elements`。
>
> `mask` 是一个和 `offs` 一样长的**布尔向量**，标记"哪些下标是合法的"：
> - 前面 977 个 program：mask 全 True，1024 个位置全都读写；
> - 第 978 个 program：只有前面几个位置 True，超出 1_000_003 的位置 False，跳过不读不写。
>
> **对照 CUDA**：等价于 `if (i < n) { ... }`，只是 Triton 是**向量化 mask**，一次判断 1024 个位置。

**Line 10~11：`tl.load(a_ptr + offs, mask=mask)`**
> **从显存里加载 1024 个 float**，一次搞定。
> - `a_ptr + offs`：**"指针 + 下标向量" = 1024 个地址**（每个下标对应一个地址）；
> - `mask=mask`：mask 为 False 的位置**跳过不读**（不会越界崩溃）；
> - 返回值 `a` 是一个长度 1024 的向量。
>
> **对照 CUDA**：等价于每个 thread 各 `float x = a[i]`——但 Triton 把 1024 个 thread 的 load 打包成一次调用，编译器自动帮你做**访存合并 (coalesced access)**。

**Line 12：`tl.store(c_ptr + offs, a + b, mask=mask)`**
> **把结果一次性写回显存**。
> - `a + b`：向量相加，1024 个位置一起加；
> - `tl.store`：把结果向量写回 `c` 的对应位置；
> - mask 为 False 的位置**跳过不写**（保护越界）。

**至此 kernel 结束**——你会发现整个函数**没有一个 for 循环**，因为 1024 个元素的加法被 `tl.load / +/ tl.store` 三行"一次性"表达了。

#### 4.4.3 第 ② 段：Launcher 函数逐行讲

```python
def add(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    c = torch.empty_like(a)
    n = a.numel()
    grid = lambda meta: (triton.cdiv(n, meta['BLOCK_SIZE']),)
    add_kernel[grid](a, b, c, n, BLOCK_SIZE=1024)
    return c
```

**Line 2：`c = torch.empty_like(a)`**
> **提前分配输出 Tensor**。GPU 上的 kernel 不能自己分配显存（那是 CPU 端的事），必须先由 PyTorch 分配好，再把指针传进去。
> `empty_like` 只分配不初始化，比 `zeros_like` 快，因为反正马上要被覆盖。

**Line 3：`n = a.numel()`**
> **拿到元素总数**。`numel()` = number of elements。

**Line 4：`grid = lambda meta: (triton.cdiv(n, meta['BLOCK_SIZE']),)`**
> **计算"要启动多少个 program"**——这是最容易劝退新手的一行。拆开看：
>
> - `triton.cdiv(n, BLOCK_SIZE)` = **向上取整除法** = `ceil(n / BLOCK_SIZE)`。
>   例：`n=1_000_003, BLOCK_SIZE=1024` → `cdiv = 978`，也就是要 978 个 program 才能覆盖所有元素。
> - `(..., )` **元组**：Triton 要求 grid 是元组，即使只有一维也要写成 `(978,)`，**逗号不能少**（少写就变成普通整数，报错）。
> - `lambda meta: ...`：为什么要用 lambda？因为 `BLOCK_SIZE` 可能会被 `@autotune` 动态换（第 6 节讲），所以 grid 得**根据当前用的 BLOCK_SIZE 现算**。`meta` 是 Triton 传进来的字典，里面有当前的 constexpr 值。
>
> **对照 CUDA**：等价于 `dim3 grid((n + 1023) / 1024);`。

**Line 5：`add_kernel[grid](a, b, c, n, BLOCK_SIZE=1024)`**
> **正式启动 kernel**。这行做了三件事：
> 1. **`add_kernel[grid]`** 中括号语法 = 指定 grid 大小（多少个 program）——**这是 Triton 特有的启动语法，看着奇怪但记住就行**；
> 2. **传参**：`a, b, c` 会被自动转成指针，`n` 是普通整数，`BLOCK_SIZE=1024` 是编译期常量；
> 3. **异步执行**：这行会**立即返回**，kernel 在 GPU 上后台跑；当你后面对 `c` 做操作时（比如打印、`.cpu()`），PyTorch 会自动等它跑完。
>
> **对照 CUDA**：等价于 `add_kernel<<<grid, block>>>(a, b, c, n);`。

#### 4.4.4 第 ③ 段：调用者（测试代码）

```python
a = torch.randn(1_000_003, device='cuda', dtype=torch.float32)
b = torch.randn_like(a)
c_triton = add(a, b)
c_torch  = a + b
assert torch.allclose(c_triton, c_torch)
```

这段没什么好讲的，就是**造两个随机数组 → 分别用 Triton 和 PyTorch 各算一遍 → 对比结果**。它是**写 kernel 的黄金习惯**：**永远先写一个 PyTorch 参考实现来验证正确性，再看性能**。

#### 4.4.5 一图串起来：数据流向

```
CPU 端                          GPU 端
─────────────────────────────────────────────────────────────
a = torch.randn(1_000_003)  →  显存里存着 4MB 的 float32
b = torch.randn(1_000_003)  →  显存里存着 4MB 的 float32
c = empty_like(a)           →  显存里预留 4MB 空间
n = 1_000_003
grid = (978,)               →  告诉 GPU："启动 978 个 program"
                                    │
                                    ▼
add_kernel[grid](...)      ═══► GPU 上：
                                    Program #0：处理 offs=[0..1023]
                                    Program #1：处理 offs=[1024..2047]
                                    ...
                                    Program #977：处理 offs=[1000448..1000003]
                                                 （最后一个 mask 掉尾部）
                                    ↓
                                    978 个 program 并行跑，
                                    每个内部 1024 个"格子"也在并行加
                                    ↓
                                    c 显存里被填好
                                    │
return c ← ─────────────────────────┘
```

**理解到这一步，Triton 的心智模型你就通了**：
- **一个 kernel = 一份"每个 program 干什么"的说明书**；
- **grid = "复印这份说明书发给多少个 program"**；
- **BLOCK_SIZE = "每个 program 一次能处理多大一块数据"**；
- **mask = "别越界"**。

后面写 softmax、GEMM、attention，无非就是把"这个 program 干什么"从"加一段数据"换成"算一行 softmax"、"算一块 C 的 tile"，骨架完全不变。

#### 4.4.6 新手最容易踩的 5 个坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | grid 忘了写成元组 | `TypeError: 'int' object is not subscriptable` | `(978,)` 逗号不能少 |
| 2 | `BLOCK_SIZE` 不是 2 的幂 | 性能差、编译警告 | 用 32/64/128/256/512/1024 |
| 3 | 忘了传 `mask` | 尾部越界，结果错乱甚至 CUDA error | 只要 n 不是 BLOCK_SIZE 整数倍，**必须**加 mask |
| 4 | 输入 Tensor 不在 GPU 上 | `RuntimeError: Expected all tensors to be on the same device` | `x.cuda()` 或建 Tensor 时 `device='cuda'` |
| 5 | 第一次运行卡 3~5 秒 | 以为死机了 | 正常，JIT 编译中；第二次毫秒级 |

**读完 4.4，你应该能自信地说**：4.1 的每一行都懂了、能默写、能仿写一个 `mul_kernel`（把 `a + b` 改成 `a * b` 就是了）。这就是 Triton "入门"的门槛，剩下 90% 的复杂 kernel 都是在这个骨架上堆花样。

---

## 5. 三大必修 Kernel：Softmax / GEMM / LayerNorm

### 5.1 Fused Softmax（Triton 官方经典入门）

**为什么练它**：Softmax 是 AI 里最常见的归约操作，且能一次跑完（不需要中间显存），是**融合算子的教科书案例**。PyTorch eager 里 softmax 会启动多个 kernel（`exp`, `sum`, `div`），Triton 一个 kernel 搞定。

```python
# fused_softmax.py（简化版，只处理 row-wise，且假设 n_cols <= BLOCK）
import torch, triton, triton.language as tl

@triton.jit
def softmax_kernel(
    out_ptr, in_ptr,
    in_row_stride, out_row_stride,
    n_cols,
    BLOCK: tl.constexpr,
):
    row = tl.program_id(0)
    in_row_ptr  = in_ptr  + row * in_row_stride
    out_row_ptr = out_ptr + row * out_row_stride

    cols = tl.arange(0, BLOCK)
    mask = cols < n_cols

    x = tl.load(in_row_ptr + cols, mask=mask, other=-float('inf'))
    x = x - tl.max(x, axis=0)              # 数值稳定：减 max
    num = tl.exp(x)
    den = tl.sum(num, axis=0)
    y   = num / den
    tl.store(out_row_ptr + cols, y, mask=mask)


def softmax(x: torch.Tensor) -> torch.Tensor:
    assert x.ndim == 2
    n_rows, n_cols = x.shape
    BLOCK = triton.next_power_of_2(n_cols)
    y = torch.empty_like(x)
    softmax_kernel[(n_rows,)](
        y, x,
        x.stride(0), y.stride(0),
        n_cols,
        BLOCK=BLOCK,
        num_warps=4,
    )
    return y


if __name__ == "__main__":
    x = torch.randn(1823, 781, device='cuda')
    y_t = softmax(x)
    y_ref = torch.softmax(x, dim=-1)
    print("max diff:", (y_t - y_ref).abs().max().item())
```

**关键 tricks**：

- `tl.max` / `tl.sum` 是 Triton 内置 reduction，编译器自动生成 warp shuffle；
- `other=-float('inf')` 让 mask 掉的位置在减 max 时无影响；
- `num_warps=4` 提示编译器用 4 个 warp（128 threads）跑一个 program，可以调 1/2/4/8。

### 5.2 GEMM（矩阵乘）—— Triton 秀肌肉

**GEMM 是 Triton 最能秀性能的场景**。下面是**教学简化版**（真正的高性能版见 Triton 官方 `03-matrix-multiplication.py`）：

```python
@triton.jit
def matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    # 每个 program 计算 C 的一个 [BLOCK_M, BLOCK_N] 块
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k in range(0, K, BLOCK_K):
        a = tl.load(a_ptrs, mask=(offs_k[None, :] + k) < K, other=0.0)
        b = tl.load(b_ptrs, mask=(offs_k[:, None] + k) < K, other=0.0)
        acc += tl.dot(a, b)                  # 🔥 tl.dot 自动用 Tensor Core
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)
```

**必看知识点**：
- `tl.dot(a, b)` —— **一句话调用 Tensor Core**（FP16/BF16/TF32 自动选择）；
- 三层 tile：`BLOCK_M / BLOCK_N / BLOCK_K` 决定单个 program 的算力/访存平衡；
- 二维 grid：`(cdiv(M, BM), cdiv(N, BN))`，每个 program 独立算一小块。

**典型 tile 选择**（RTX 3060 上跑 FP16 矩阵乘的经验起点）：

| M, N, K | BLOCK_M | BLOCK_N | BLOCK_K | num_warps |
|:--|:--|:--|:--|:--|
| 512+ | 128 | 128 | 32 | 4 |
| 中等（256~512） | 64 | 64 | 32 | 2 |
| 小（<256） | 32 | 32 | 32 | 2 |

具体值应交给 **`@autotune`** 决定，见第 6 节。

### 5.3 LayerNorm（练手好目标）

思路：每个 program 处理一行（或一小段），行内做两次 reduction（`mean`、`var`），然后归一化 + affine。**代码量 ~40 行**，是把 softmax 学扎实后的绝佳练手项目——`torch.nn.LayerNorm` 是 3 次 kernel 启动，Triton 版是 1 次，实测能省 30~40% latency。

---

## 6. 自动调优（`@triton.autotune`）：Triton 的杀手锏

**手写 CUDA 想换 tile 大小要重编、要改代码**；Triton 让你**列出候选配置，让编译器自动挑最快的**。

```python
@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N':  64, 'BLOCK_K': 32}, num_warps=4),
        triton.Config({'BLOCK_M':  64, 'BLOCK_N':  64, 'BLOCK_K': 32}, num_warps=2),
        triton.Config({'BLOCK_M':  32, 'BLOCK_N':  32, 'BLOCK_K': 32}, num_warps=2),
    ],
    key=['M', 'N', 'K'],   # (M,N,K) 变化时才重新调优
)
@triton.jit
def matmul_kernel(...):
    ...
```

**执行逻辑**：
1. 第一次调用某个 `(M,N,K)` shape 时，Triton **依次跑一遍每个 config**，选出最快的；
2. 结果被缓存到 `~/.triton/autotune/`；
3. 后续同 shape 直接用最快的那个 config。

**踩坑**：
- `key` 一定要选**真正影响性能的维度**（一般就是 M/N/K），否则会频繁重调；
- 首次调优会**慢 1~5 秒**，别怀疑是 bug；
- 调优时如果某个 config OOM 或用超 shared memory，会自动跳过，不会 crash。

---

## 7. 集成到 PyTorch：写一个自定义融合算子

### 7.1 最简洁的封装（`torch.autograd.Function`）

```python
import torch, triton, triton.language as tl

class TritonSoftmax(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x):
        y = softmax(x)                # 复用第 5.1 节的 softmax
        ctx.save_for_backward(y)
        return y

    @staticmethod
    def backward(ctx, grad_out):
        (y,) = ctx.saved_tensors
        # softmax 的反向：dL/dx = y * (grad_out - (grad_out * y).sum(-1, keepdim=True))
        s = (grad_out * y).sum(dim=-1, keepdim=True)
        return y * (grad_out - s)     # 反向用 PyTorch 表达式即可，也可以再写 Triton kernel

triton_softmax = TritonSoftmax.apply

# 用法完全和 nn.functional.softmax 一样
y = triton_softmax(x)
loss = y.sum()
loss.backward()
```

### 7.2 与 `torch.compile` 协作

Triton 写的算子可以**直接被 `torch.compile` 识别**并塞进它生成的融合图里——这也是 PyTorch 2.x 官方推荐的自定义算子写法。

### 7.3 常见陷阱

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| `IndexError: tuple index out of range` | grid 元组少写了逗号 `(N,)` → `(N)` | 加逗号 |
| 结果对但慢 | Triton 首次 JIT 编译 | 预热 3~5 次再测 |
| 精度对不上 | Reduce 累加用了 fp16 | 累加器改 `tl.float32`，最后再 cast |
| Kernel 里 `print` 没输出 | Triton **不支持 device 端 print** | 用 `TRITON_INTERPRET=1` 环境变量，把 kernel 当 Python 跑（**神器**） |

---

## 8. 性能分析：怎么知道 Triton 到底跑得多快？

### 8.1 用 Triton 官方 `do_bench`

```python
import torch, triton

def torch_softmax(x): return torch.softmax(x, dim=-1)
def our_softmax(x):   return softmax(x)   # 第 5.1 节的实现

x = torch.randn(4096, 4096, device='cuda')
ms_torch = triton.testing.do_bench(lambda: torch_softmax(x))
ms_ours  = triton.testing.do_bench(lambda: our_softmax(x))
print(f"torch: {ms_torch:.3f} ms | triton: {ms_ours:.3f} ms | speedup: {ms_torch/ms_ours:.2f}x")
```

`do_bench` 会自动**预热 + 多次取中位数**，比手写 `time.time()` 靠谱得多。

### 8.2 用 Nsight Compute 看 kernel 细节

Triton 生成的 PTX/SASS 可以像 CUDA C++ 一样被 Nsight Compute 分析：

```bash
ncu --set full --target-processes all python bench_softmax.py
```

- 关注指标：`sm__pipe_tensor_op_hmma_cycles_active` （Tensor Core 是否吃满）、`dram__throughput`（HBM 带宽利用率）、`smsp__thread_inst_executed_per_inst_executed` （warp 效率）。
- Triton 生成的 kernel 名字形如 `add_kernel_0d1d2d3de` —— 那串后缀是 constexpr 参数编码，别慌。

### 8.3 三条经验法则

1. **memory-bound** kernel（element-wise、reduction）：**看 HBM 带宽**，跑到峰值 80%+ 就算胜利；
2. **compute-bound** kernel（GEMM、attention）：**看 Tensor Core 利用率**，60%+ 是好起点；
3. Triton 一般能拿到 **90%+ cuBLAS/cuDNN 性能**，如果差得多，先怀疑 tile 大小 → `num_warps` → 是否用了 `tl.dot` 而非手写 loop。

---

## 9. 进阶：读懂 FlashAttention 的 Triton 实现

学完前 8 章后，直接去读官方参考实现：

- 仓库：<https://github.com/Dao-AILab/flash-attention>
- Triton 版路径：`flash_attn/flash_attn_triton.py`（历史版本）或参考 `triton` 官方 tutorial `06-fused-attention.py`

**阅读顺序建议**：

1. 先看 Triton 官方 `python/tutorials/06-fused-attention.py`（~200 行，纯教学）；
2. 理解**online softmax**（分块算 softmax 而不需要看到整行数据）；
3. 理解**两次循环结构**：外层遍历 Q 的行块，内层遍历 K/V 的列块；
4. 再去看 FA 官方 Triton 实现，抓 causal mask、变长序列、GQA 等工程细节。

**FlashAttention 用到的 Triton 关键特性**：
- `tl.dot` × 多次累加（Tensor Core 循环）；
- 在线归约（`m_i`, `l_i` 两个 running 值）；
- 精妙的 mask 处理（causal / padding / sliding window）。

**看懂 FA 的 Triton 版，基本就到 T3 水平**。

---

## 10. 学习路线图（4~6 周）

### 🟢 阶段 1（Week 1）：环境 + 心智模型

- ✅ WSL2 装好 Triton + PyTorch
- ✅ 跑通向量加、element-wise
- ✅ 理解 program / block / mask
- ✅ 通读 Triton 官方 tutorial 01/02

### 🟡 阶段 2（Week 2）：Reduction 家族

- ✅ 手写 fused softmax，跑赢 `torch.softmax`
- ✅ 手写 LayerNorm，跑赢 `nn.LayerNorm`
- ✅ 熟悉 `tl.max` / `tl.sum` / `mask` / `other`

### 🟠 阶段 3（Week 3~4）：GEMM + Autotune

- ✅ 写出 matmul，跑到 cuBLAS 70%+
- ✅ 加 `@autotune`，尝试不同 tile
- ✅ 理解 `tl.dot` 底层是 Tensor Core
- ✅ 用 Nsight Compute 看利用率

### 🔴 阶段 4（Week 5~6）：Attention + PyTorch 集成

- ✅ 复现 fused attention（无 causal）
- ✅ 加 causal mask
- ✅ 封装成 `torch.autograd.Function`
- ✅ 用 `torch.compile` + 你的 Triton 算子跑 mini-GPT

### 🎯 里程碑（做完就是 T3）

- 写一个 **fused RMSNorm + SiLU + 矩阵乘** 的融合算子给自己项目提速；
- 用 Triton 复现 **W4A16 量化 GEMM**（LLM 推理核心）；
- 读懂并小改 **FlashAttention v2** 的 Triton 版。

---

## 11. 精选资源与踩坑清单

### 11.1 必读官方资源

| 资源 | 用途 | 链接 |
|:--|:--|:--|
| Triton 官方文档 | API 参考 | <https://triton-lang.org/main/> |
| Triton 官方 tutorials | 从 vec_add 到 fused attention | <https://github.com/triton-lang/triton/tree/main/python/tutorials> |
| PyTorch × Triton 集成 | `torch.compile` 生成 Triton | <https://pytorch.org/docs/stable/torch.compiler.html> |
| FlashAttention 论文 & 代码 | 生产级 Triton 案例 | <https://github.com/Dao-AILab/flash-attention> |
| Liger-Kernel | 一堆高质量 LLM Triton 算子 | <https://github.com/linkedin/Liger-Kernel> |
| Unsloth | LoRA 训练加速用大量 Triton | <https://github.com/unslothai/unsloth> |

### 11.2 高质量博客/讲解

- **Sasha Rush**（HuggingFace）：*GPU Puzzles* + Triton Puzzles，做题式学习；<https://github.com/srush/Triton-Puzzles>
- **Simon Boehm**：《How to Optimize a CUDA Matmul Kernel》—— 虽然是 CUDA，但对理解 Triton 里 GEMM 优化直接受用；
- **Philippe Tillet**（Triton 作者）：OpenAI 官方博客有一篇《Introducing Triton》，看 Triton 设计哲学。

### 11.3 完整踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 首次运行卡很久 | JIT 编译 + autotune | 正常，第二次快；`~/.triton/cache` 缓存 |
| `Cannot find libcuda` | WSL2 下 Triton 找不到驱动 | 更新 Windows NVIDIA 驱动到最新（≥ 531） |
| `tl.dot` 报 shape 错 | 两个操作数必须都是 2D 且形状匹配 | `a: (M,K)`, `b: (K,N)`；用 `[:, None]` 升维 |
| 精度差 1e-2 | Reduce 用 fp16 累加 | 累加器 `tl.zeros(..., dtype=tl.float32)` |
| 大 shape 崩溃 / OOM | BLOCK 太大，shared memory 超限 | 缩小 BLOCK，或加 `num_stages=2` |
| Kernel 里 print 没输出 | Triton 不支持 device print | `TRITON_INTERPRET=1 python xxx.py`，当 Python 跑并可 print |
| Autotune 结果每次不一样 | GPU 抖动（低负载时 clock 不稳） | 用 `nvidia-smi -lgc <freq>` 锁频后再调优 |
| 结果对，性能远低于预期 | 忘了 `num_warps` 提示 / tile 不对 | 加 `@autotune` 让编译器挑 |
| `RuntimeError: PassManager::run failed` | 用了当前版本不支持的 API | 升级 Triton；查 changelog |

### 11.4 一句话总结

> **Triton = "用 NumPy 的手感写出 CUDA 的性能"。**
> 学它的成本远小于 CUDA，收益却常常一样大——**新时代 AI Kernel 工程师的必备工具**。

---

**祝你 Kernel 越写越快，模型越跑越猛。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
