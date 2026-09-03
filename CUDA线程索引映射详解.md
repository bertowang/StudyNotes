# CUDA 线程索引映射详解（1D / 2D / 3D 及底层逻辑）

**作者**：汪亮（bertonwang）
**邮箱**：<47608843@qq.com>
**版本**：v1.0 ｜ **最后更新**：2026-09-03

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。


> **本文聚焦**：软件线程坐标（`threadIdx` / `blockIdx`）如何映射到数据全局索引，以及背后的 SIMT / 内存底层逻辑。
> **阅读前提**：了解 `<<<gridSize, blockSize>>>` 的基本写法即可；§8 提供可直接编译运行的完整示例。

---

## 目录

- [一、前置概念：四个内置变量](#sec1)
- [二、1D 映射（一切的基础）](#sec2)
- [三、2D 映射（逐行拆解 + 纠错）](#sec3)
  - [3.1 示例代码逐行解析](#sec3-1)
  - [3.2 常见错误：方阵假设](#sec3-2)
  - [3.3 从 (row, col) 到内存下标](#sec3-3)
- [四、3D 映射（x / y / z 的完整计算）](#sec4)
- [五、通用公式与坐标变换](#sec5)
- [六、底层逻辑：为什么这样设计](#sec6)
  - [6.1 SIMD 与 SIMT：一条指令，两种抽象](#sec6-1)
  - [6.2 warp：SIMT 的物理调度单位](#sec6-2)
  - [6.3 内存合并访问（Coalescing）](#sec6-3)
  - [6.4 从软件坐标到硬件的完整链路](#sec6-4)
  - [6.5 Block 与 Grid 的维度限制](#sec6-5)
- [七、常见陷阱](#sec7)
- [八、完整可运行示例](#sec8)
- [九、小结](#sec9)

---

<a id="sec1"></a>

## 一、前置概念：四个内置变量

CUDA 的线程组织是一个三级层次：**Grid（网格）→ Block（线程块）→ Thread（线程）**。内核启动时 `<<<gridSize, blockSize>>>` 的两个参数，分别定义了 Grid 和 Block 的形状——它们与内核里的 `gridDim`、`blockDim` 是**同一组值的两个视角**：启动时你写的是 `gridSize` / `blockSize`，内核里读到的就是 `gridDim` / `blockDim`。

在内核里，有四个内置变量，它们**都是三维向量**（都含 `.x` / `.y` / `.z` 三个分量）：

| 内置变量 | 类型 | 含义 | 取值范围 / 来源 |
|---------|------|------|------|
| `threadIdx` | `uint3` | 当前线程在**所属 Block 内**的坐标 | `0` ~ `blockDim - 1` |
| `blockDim` | `dim3` | 每个 Block 在**各维度**有多少个线程 | 来自启动参数 `blockSize` |
| `blockIdx` | `uint3` | 当前 Block 在**整个 Grid 中**的坐标 | `0` ~ `gridDim - 1` |
| `gridDim` | `dim3` | Grid 在**各维度**有多少个 Block | 来自启动参数 `gridSize` |

> **一句话区分**：**`Idx` 是"我在哪"（会变的坐标，`uint3`），`Dim` 是"有多大"（固定的尺寸，`dim3`）**。

关键认知：**这四个变量永远是三维的，但你用几个维度就「激活」几个分量。**

未激活的分量按下面规则取值——注意 `Idx` 和 `Dim` **不一样**：

| 场景 | `threadIdx` / `blockIdx` 未用分量 | `blockDim` / `gridDim` 未用分量 |
|------|------|------|
| 1D（只用 `.x`） | `.y = .z = 0` | `.y = .z = 1` |
| 2D（用 `.x`、`.y`） | `.z = 0` | `.z = 1` |
| 3D | 全部使用 | 全部使用 |

> 为什么一个是 0、一个是 1？因为**坐标从 0 开始计数，而尺寸至少是 1**。`dim3 blockSize(16)` 等价于 `dim3(16, 1, 1)`，所以未指定的维度尺寸是 1；而未激活维度上的坐标最大只能到 `blockDim - 1 = 0`。

---

<a id="sec2"></a>

## 二、1D 映射（一切的基础）

一维映射只有一行，后面所有维度都是它的重复：

```cuda
int i = blockIdx.x * blockDim.x + threadIdx.x;   // 全局线性索引
```

拆开看，`blockIdx.x * blockDim.x` 是「当前 Block 之前一共有多少个线程」，`threadIdx.x` 是「当前线程在本 Block 内的偏移」，两者相加就是「当前线程在全局的线性编号」。

> 用一句话记：**全局坐标 = Block 的偏移 + 线程在 Block 内的偏移。**

之所以能直接相加，是因为**线程在 Block 内按 `x` 方向连续排列**：Block 0 排完才轮到 Block 1，中间不留空档。后面会看到，正是这个「连续排列」的规则决定了 warp 由哪些线程构成，进而决定内存访问是否高效（见 §6）。

这个「偏移 + 内偏移」的思想，是 2D 和 3D 映射的共同核心——**每个维度各自做一遍同样的运算，互不干扰**。

---

<a id="sec3"></a>

## 三、2D 映射（逐行拆解 + 纠错）

<a id="sec3-1"></a>

### 3.1 示例代码逐行解析

下面是一段很常见的 2D 配置与索引计算：

```cuda
dim3 blockSize(16, 16); // 16x16 = 256 线程/块
dim3 gridSize((N + blockSize.x - 1) / blockSize.x, (N + blockSize.y - 1) / blockSize.y);
int row = blockIdx.y * blockDim.y + threadIdx.y;
int col = blockIdx.x * blockDim.x + threadIdx.x;
```

**第 1 行**：定义一个 `16×16` 的线程块，共 256 个线程（8 个 warp）。256 是常见起点——它是 warp 大小（**32 线程**）的整数倍，且不超过现代 GPU 每 Block 1024 线程的上限。

**第 2 行**：计算 Grid 需要多少个 Block。`(N + blockSize.x - 1) / blockSize.x` 是「向上取整」的整数除法写法（等价于 `ceil(N / blockSize.x)`），保证当 N 不是 blockSize 的整数倍时，多出的那部分数据也有线程覆盖。

**第 3、4 行**：核心的坐标映射。这里有个**约定俗成但必须点破的对应关系**：

- `.y` 方向（`blockIdx.y`、`blockDim.y`、`threadIdx.y`）→ 对应矩阵的**行**（row）
- `.x` 方向（`blockIdx.x`、`blockDim.x`、`threadIdx.x`）→ 对应矩阵的**列**（col）

⚠️ **但这里其实混着三件不同的事，务必分开看**：

| # | 事实 | 由谁决定 | 内容 |
|:---:|---|---|---|
| ① | 线程编号中 **`threadIdx.x` 变化最快** | **CUDA 规范**（你改不了） | 线性线程 ID = `threadIdx.x + threadIdx.y * blockDim.x` |
| ② | C/C++ 多维数组是 **row-major**，最后一维（列）变化最快 | **语言规则**（你改不了） | `a[row][col]` 的地址 = `base + row * cols + col` |
| ③ | 把 **x 绑定到列**、y 绑定到行 | **你的选择**（可以改） | 让两个"最快维度"互相对齐 |

③ **并不是强制的**——反过来绑定程序照样能跑对。但只有按 ③ 这样绑，才能让「相邻的线程」访问「相邻的地址」，从而命中合并访问。这就是业界几乎约定俗成地采用 `.x` → 列、`.y` → 行的真正原因（性能论证见 §6.3）。

<a id="sec3-2"></a>

### 3.2 常见错误：把方阵假设套用到非方阵

上一段代码里，`gridSize` 的两个分量都用同一个 `N` 来计算。这**只在矩阵是 `N×N` 方阵时成立**。

如果矩阵是 `M×N`（M 行、N 列），正确写法应该是：

```cuda
// M 行 N 列
int rows = M, cols = N;
dim3 blockSize(16, 16);
dim3 gridSize((cols + blockSize.x - 1) / blockSize.x,   // x 方向覆盖「列」
              (rows + blockSize.y - 1) / blockSize.y);  // y 方向覆盖「行」

int row = blockIdx.y * blockDim.y + threadIdx.y;  // 0 ~ M-1
int col = blockIdx.x * blockDim.x + threadIdx.x;  // 0 ~ N-1
```

一句话记住方向对应：**`.x` 对齐「列」/「连续内存」，`.y` 对齐「行」/「变化较慢的维度」。**

<a id="sec3-3"></a>

### 3.3 从 (row, col) 到内存下标

二维数据在 GPU 全局内存里，其实也是**线性存放**的（row-major，行优先）。所以拿到 `(row, col)` 后，还要折算成一个一维下标：

```cuda
int idx = row * cols + col;        // row-major：行号 × 行宽 + 列号
c[row * cols + col] = a[row * cols + col] + b[row * cols + col];
```

其中 `cols` 是「每一行有多少个元素」（行宽 / 矩阵的列数）。这个 `row * width + col` 就是 2D → 1D 的标准线性化公式。

---

<a id="sec4"></a>

## 四、3D 映射（x / y / z 的完整计算）

### 4.1 完整代码

假设一个三维体数据 `volume`，尺寸为 `Dx × Dy × Dz`：

```cuda
dim3 blockSize(8, 8, 8);   // 8×8×8 = 512 线程/块
                           // ⚠️ 这里只为演示三维坐标计算；
                           //    追求性能时应改用 (32,4,4) 等 blockDim.x≥32 的配置，见 §6.5
dim3 gridSize(
    (Dx + blockSize.x - 1) / blockSize.x,
    (Dy + blockSize.y - 1) / blockSize.y,
    (Dz + blockSize.z - 1) / blockSize.z
);

__global__ void kernel3d(const float* in, float* out, int Dx, int Dy, int Dz) {
    int x = blockIdx.x * blockDim.x + threadIdx.x;   // 0 ~ Dx-1
    int y = blockIdx.y * blockDim.y + threadIdx.y;   // 0 ~ Dy-1
    int z = blockIdx.z * blockDim.z + threadIdx.z;   // 0 ~ Dz-1

    if (x < Dx && y < Dy && z < Dz) {                // 边界保护
        int idx = x + y * Dx + z * Dx * Dy;          // 3D → 1D 线性化
        out[idx] = in[idx] + 1.0f;
    }
}
```

### 4.2 逐维度解释

三个维度的计算**结构完全一样**，各自做一遍「Block 偏移 + 线程内偏移」：

| 维度 | 全局坐标 | 含义 |
|------|---------|------|
| x | `blockIdx.x * blockDim.x + threadIdx.x` | 最内层、变化最快的维度 |
| y | `blockIdx.y * blockDim.y + threadIdx.y` | 中间层 |
| z | `blockIdx.z * blockDim.z + threadIdx.z` | 最外层、变化最慢的维度 |

### 4.3 3D → 1D 线性化公式

这是最需要理解清楚的一步。三维数据的线性下标计算：

```cuda
int idx = x + y * Dx + z * Dx * Dy;
```

为什么是这个形式？把它拆成「层级」来看：

- `x`：最内层，`x` 每 +1，地址 +1；
- `y * Dx`：`y` 每 +1，跨过一整行（`Dx` 个元素）；
- `z * Dx * Dy`：`z` 每 +1，跨过一整层（`Dx × Dy` 个元素）。

这正是 row-major（行优先）在三维下的自然推广——**内存地址的变化顺序是 x → y → z，x 最快、z 最慢**。

> 换一种记法：`idx = ((z * Dy) + y) * Dx + x`，本质等价。核心是「最慢的维度乘以最大的跨度」。

### 4.4 维度与「跨度」的对应表

| 维度 | 相邻元素地址差 | 变化速度 |
|------|--------------|---------|
| x | 1 | 最快 |
| y | Dx | 中 |
| z | Dx × Dy | 最慢 |

这个「跨度表」是 3D 映射的灵魂，理解了它，任何维度换算都能推出来。

### 4.5 易错澄清：为什么线性化公式里没有 `Dz`

一个常见的疑问是：`idx = x + y * Dx + z * Dx * Dy` 里，为什么 `z` 那一项乘的是 `Dx * Dy`，而不是「整个立方体大小」`Dx * Dy * Dz`？`Dz` 去哪了？

关键在于区分「**层的大小**」和「**层的数量**」：

| 量 | 含义 | 符号 |
|----|------|------|
| 层的大小（一层有多少元素） | `z` 每 +1 跨过多少个元素 | `Dx × Dy` |
| 层的数量（一共有几层） | `z` 能取多少个值 | `Dz` |

把立方体想成一叠 Dz 片「切片」，每片是 `Dx × Dy` 的平面：

- `z` 每 +1，只跨过**一片切片**（`Dx × Dy` 个元素），不是整叠；
- 只有 `z` 从 0 走到 `Dz`（走出整叠）时，才跨过整叠 = `Dx × Dy × Dz`。

所以 `Dz` 没消失，它只是不参与「跨度」计算，而是用在两处：

1. **边界检查**：`if (z < Dz)` —— 判断 `z` 有没有超出层数；
2. **总元素数**：`Dx × Dy × Dz` —— 计算整个体数据占多少内存。

数值验证（`Dx=4, Dy=3, Dz=2`，总 24 个元素）：

```
z=0 层（idx 0~11）          z=1 层（idx 12~23）
  y=0:  0  1  2  3            y=0: 12 13 14 15
  y=1:  4  5  6  7            y=1: 16 17 18 19
  y=2:  8  9 10 11            y=2: 20 21 22 23
```

取 `(x=2, y=1, z=1)`：`idx = 2 + 1*4 + 1*4*3 = 18` ✓。`z=1` 时 `z*Dx*Dy = 12`，正好跳过 `z=0` 那一整片（12 个元素）。这里乘的是 `Dx*Dy = 12`（一片的大小），而 `Dz=2` 全程没进公式。

> 一句话：**`z` 每 +1 跨过的是「一片」，不是「整叠」。一片 = `Dx × Dy`，整叠 = `Dx × Dy × Dz`。线性化算「跨过几片」只乘 `Dx × Dy`；`Dz` 管「一共几片」，用在边界和总大小上。**

---

<a id="sec5"></a>

## 五、通用公式与坐标变换

把 1D / 2D / 3D 统一起来，其实就是同一件事：**对每一个激活的维度 d，全局坐标 = `blockIdx.d * blockDim.d + threadIdx.d`；然后把多维坐标线性化为一维下标。**

### 通用线性化公式（N 维，row-major）

假设维度尺寸为 `D1, D2, ..., Dn`（其中 `D1` 是变化最快的 x 方向），全局坐标为 `c1, c2, ..., cn`：

```
linear_index = c1
             + c2 * D1
             + c3 * D1 * D2
             + ...
             + cn * D1 * D2 * ... * D(n-1)
```

**符号对应关系**（本文前后用了几套名字，别被绕晕）：

| 通用符号 | 3D 中的名字 | 2D 中的名字 | 变化速度 |
|:---:|:---:|:---:|:---:|
| `D1` / `c1` | `Dx` / `x` | `cols` / `col` | 最快 |
| `D2` / `c2` | `Dy` / `y` | `rows` / `row` | 中 |
| `D3` / `c3` | `Dz` / `z` | — | 最慢 |

代入 3D 即得 `idx = x + y * Dx + z * Dx * Dy`（§4.3），代入 2D 即得 `idx = col + row * cols`，也就是 `row * cols + col`（§3.3）。

### 为什么统一用 row-major？

因为 CUDA 的全局内存本质上是一维的线性地址空间，GPU 硬件按线性地址连续访问时效率最高。`x` 方向（连续线程）对应连续地址，是后面要讲的「内存合并访问」的关键。

---

<a id="sec6"></a>

## 六、底层逻辑：为什么这样设计

前面讲的都是「怎么写」，这一部分回答「为什么这么设计」——这是理解 CUDA 索引映射的根本。

<a id="sec6-1"></a>

### 6.1 SIMD 与 SIMT：一条指令，两种抽象

要真正理解前面讲的「x 最快」「warp」「合并访问」，得先回答一个更根本的问题：**GPU 到底是怎么执行计算的？** 答案就藏在 SIMT 与 SIMD 的关系里。

#### 先看 SIMD：一条指令，一次算多个数据

SIMD（Single Instruction, Multiple Data）是 Flynn 分类法里的经典概念——**用一条指令，同时对多个数据元素做同样的运算**。CPU 上的 SSE / AVX / NEON 都是这个思路：

```cpp
// AVX：一条指令同时加 8 个 float
__m256 va = _mm256_loadu_ps(&a[i]);   // 加载 8 个
__m256 vb = _mm256_loadu_ps(&b[i]);
__m256 vc = _mm256_add_ps(va, vb);    // 一条指令，完成 8 个加法
_mm256_storeu_ps(&c[i], vc);
```

硬件上对应一个 **256 位宽的向量寄存器**和一组 8 通道的运算单元。宽度写死在指令集里：SSE 是 128 位（4 个 float），AVX 是 256 位（8 个），AVX-512 是 512 位（16 个）。

#### SIMD 的三个痛点

SIMD 性能很好，但对程序员很不友好，因为它把**硬件宽度直接暴露给了软件**：

| 痛点 | 具体表现 |
|---|---|
| **宽度绑死，不可移植** | 为 AVX-512 写的代码在只支持 AVX2 的机器上跑不了；换宽度就得改代码、重编译 |
| **分支几乎没法写** | `if-else` 要手工改成「两条路都算 + mask 混合」（`_mm256_blendv_ps`）；遇到 `while`、递归这类每个元素路径不同的代码，基本放弃向量化 |
| **心智负担重** | 要显式管理向量寄存器、考虑内存对齐、处理尾部余数（数组长度不是 8 的倍数时） |

正因如此，CPU 上大量代码其实**没能真正向量化**——要么写 intrinsic 太痛苦，要么依赖编译器自动向量化而它常常静默失败。

#### SIMT 的答案：用「线程的写法」，做「向量的执行」

NVIDIA 提出的 **SIMT（Single Instruction, Multiple Thread）** 正是为了解决这三个痛点。核心思想一句话：

> **让你像写「一个普通标量线程」那样写代码，由硬件负责把这群线程捆成向量来跑。**

同一个向量加法，在 CUDA 里是这样：

```cuda
int i = blockIdx.x * blockDim.x + threadIdx.x;
c[i] = a[i] + b[i];        // 看起来完全是标量代码
```

**注意这行代码和 CPU 上的标量写法一模一样**——没有 `__m256`、没有 `_mm256_add_ps`、没有任何「一次处理 8 个」的痕迹。但硬件执行时，warp 内 32 个线程**共用同一条指令**，由 SM 的执行单元在若干个周期内完成这 32 个加法。

**效果等价于一条「32 车道宽」的 SIMD 指令，而你一个字的向量代码都没写。**

三种写法的对照：

| 写法 | 代码形态 | 并行宽度 | 宽度对谁可见 |
|---|---|:---:|---|
| 标量（SISD） | `c[i] = a[i] + b[i];` 配 for 循环 | 1 | — |
| SIMD（AVX） | `_mm256_add_ps(va, vb);` | 8 | **程序员**（写死在指令里） |
| **SIMT（CUDA）** | `c[i] = a[i] + b[i];` | **32** | **硬件**（程序员看不见） |

#### 关键：SIMT 不是 SIMD 的对立面，而是 SIMD 的「包装」

这是最容易被误解的一点。**SIMT 的底层依然是 SIMD 式的宽向量执行**——32 个 lane 被同一条指令驱动，共享同一套指令译码与发射通路。区别只在于**抽象层次**：

```text
┌──────────────────────────────────────────┐
│  你看到的：32 个独立线程，各算各的        │  ← 编程模型（Thread）
├──────────────────────────────────────────┤
│  实际的：  32 个线程被捆成 warp，          │  ← 执行模型（SIMD 宽向量）
│           一条指令同时驱动 32 个 lane     │
└──────────────────────────────────────────┘
```

| 维度 | SIMD（AVX） | SIMT（CUDA） |
|---|---|---|
| 编程视角 | 操作**向量**（一次 8 个 float） | 操作**标量**（一个线程一个 float） |
| 并行宽度 | 128 / 256 / 512 位，**指令集定死** | warp = 32 线程，**硬件决定** |
| 宽度是否可见 | **可见**，代码里写死了 | **不可见**，代码里没有「32」 |
| 跨代兼容 | 换宽度要改代码 | warp 自 G80 起一直是 32，同一份代码跨代通用 |
| 分支处理 | 程序员手写 mask / blend | **硬件自动**（见下） |
| 随机访问 | gather / scatter，效率较低 | 硬件聚合成内存事务（即合并访问） |

> **一句话**：**SIMT = SIMD 硬件 + 多线程编程抽象。** 名字里的 “Thread” 强调的是**你怎么写**，“Single Instruction” 暴露的是**它怎么跑**。
>
> 顺带一提：SIMT 这个词是 NVIDIA 为自家架构造的，并不在 Flynn 的原始分类里；AMD 的等价概念叫 wavefront（GCN 架构为 64 线程，RDNA 为 32/64）。

#### 分支分歧（Divergence）：SIMT 相对 SIMD 最大的价值

看这段再普通不过的代码：

```cuda
if (threadIdx.x % 2 == 0) {
    y = f(x);      // 偶数线程走这里
} else {
    y = g(x);      // 奇数线程走这里
}
```

在 CPU 上这毫无难度（每个核心独立执行）。在 SIMD 里却很头疼——**你必须把两个分支都算一遍，再用 mask 挑结果**。`while`、递归这类**每个元素执行路径不同**的代码，SIMD 基本无解。

SIMT 把这活儿**交给了硬件**：

1. 硬件为每个 warp 维护一个 **32 位的 active mask**（标记哪些 lane 当前有效；warp 内每个线程称为一个 **lane**）；
2. 遇到分支就**两条路径都执行**：走 `f` 时屏蔽掉奇数 lane，走 `g` 时屏蔽掉偶数 lane；
3. 两路执行完，再让 warp 重新汇合。

结果：

- **正确性没问题**——每个线程走自己的路，你不用写任何 mask；
- **但性能有代价**——耗时 = `T(f) + T(g)`，而不是 `max(T(f), T(g))`。只有当整个 warp 都走同一分支（uniform branch）时才无损失。

> 有意思的是，硬件做的事和 SIMD 程序员手写的事**是同一件**：两边都算，再按 mask 合并。区别只在于**谁来写这段代码**——SIMD 里是你，SIMT 里是硬件。
>
> 所以 **SIMT 并没有消灭 divergence 的开销**，它只是把开销从「程序员根本写不出来」变成了「硬件默默承担」。想写出快的 CUDA 代码，仍然要主动避免 warp 内分支分歧。

（Volta 之后的架构进一步支持**独立线程调度**，warp 内每个线程拥有自己的程序计数器，分叉后可以不再自动汇合，需要时用 `__syncwarp()` 显式同步。）

#### 另一半：用海量 warp 隐藏延迟

SIMD 与 SIMT 还有一个目标层面的根本差异：

| | CPU SIMD | GPU SIMT |
|---|---|---|
| 优化目标 | **降低单次操作延迟**（单核跑得快） | **提高总吞吐**（靠数量取胜） |
| 隐藏延迟的手段 | 大缓存 + 分支预测 + 乱序执行 | **切换 warp**：一个 warp 等内存时立刻换另一个 |
| 硬件资源倾向 | 复杂控制单元 + 大缓存 | 大量运算单元 + **巨大寄存器堆**（驻留几十个 warp 的上下文） |

一个 SM 上会同时驻留几十个 warp。当某个 warp 因访存而停顿时，调度器**几乎零开销地**切到另一个就绪 warp——因为上下文就在寄存器堆里，无需保存与恢复。这就是 GPU 敢用「很慢」的全局内存的原因：**只要 warp 足够多，延迟就被填满的吞吐掩盖了**。

#### 回到本文：这一切与索引映射的关系

现在可以点破 §6.3（合并访问）的物理根源了：

1. SIMT 底层是**宽向量执行**——一个 warp 的指令一次性作用于 32 个 lane；
2. 因此，warp 内 32 个线程发出的 32 次内存访问，会被硬件**压成若干个宽内存事务**；
3. 若这 32 个地址**连续**，就能压成 1 个（或极少数）宽事务 → 带宽吃满；
4. 若地址**散开**，只能拆成多次窄事务，最坏拆成 32 次 → **退回到标量速度**。

**所以「相邻线程要访问相邻地址」不是 CUDA 的教条，而是 SIMT 底下那套 SIMD 执行单元的必然要求。** 而「相邻线程」究竟是哪些线程，完全由 §6.2 讲的线性线程 ID 决定——这就是索引映射之所以重要的全部原因。

<a id="sec6-2"></a>

### 6.2 warp：SIMT 的物理调度单位

CUDA 的编程模型叫 SIMT（Single Instruction, Multiple Threads）。表面上是「每个线程独立跑一段代码」，但硬件上，**线程不是一个个调度的，而是以 32 个为一组（称为 warp）集体调度的**。一个 warp 内的 32 个线程，在同一时刻执行**同一条指令**。

那么，**哪 32 个线程算一个 warp**？答案是：**按「线性线程 ID」连续划分**。Block 内线程的线性 ID 由 CUDA 规定为：

```cuda
tid = threadIdx.x
    + threadIdx.y * blockDim.x
    + threadIdx.z * blockDim.x * blockDim.y;
```

即 **`threadIdx.x` 变化最快，其次是 `y`，`z` 最慢**。线程按 `tid` 从小到大每 32 个一组：tid 0–31 是 warp 0，tid 32–63 是 warp 1，以此类推。

⚠️ **一个高频误解**：很多人以为「一个 warp 就是 `threadIdx.x` 连续的 32 个线程」。**这只在 `blockDim.x ≥ 32` 时成立。**

举个反例——本文 §4 用的 `blockSize(8, 8, 8)`，其中 `blockDim.x = 8`：

| warp | 包含的线程 `(x, y, z)` | 在体数据中的分布 |
|:---:|---|---|
| warp 0 | `(0..7, 0, 0)`、`(0..7, 1, 0)`、`(0..7, 2, 0)`、`(0..7, 3, 0)` | **横跨 4 行 y** |

这 32 个线程的 `tid` 确实连续，但**地址上被切成了 4 段**（每段只有 8 个连续地址），因为每跨一行就要跳过整个 `Dx`。这会直接影响下一节的合并访问。

> **结论**：想让「一个 warp = x 方向连续的 32 个线程」，就要保证 **`blockDim.x` 是 32 的倍数**（32 / 64 / 128 / 256…）。

<a id="sec6-3"></a>

### 6.3 内存合并访问（Coalescing）：性能的分水岭

GPU 访问全局内存时，不是一个个字节读，而是按「内存事务（memory transaction）」成段读取的。当**同一个 warp 的 32 个线程访问 32 个连续地址**时，这些访问可以被硬件合并成一次（或少数几次）事务，吞吐量最高。

于是对应关系就很清晰了：

| 情况 | 条件 | warp 内的地址分布 | 结果 |
|---|---|---|---|
| **理想** | `blockDim.x` 是 32 的倍数，且 x 绑定到最内层数据维度 | 32 个连续地址 | **1 次事务**，快 |
| **踩坑** | `blockDim.x < 32`（如 `(8, 8, 8)`） | 切成 `32 / blockDim.x` 段，段间距为 `Dx` | 事务数成倍增加 |
| **更糟** | 把 x 绑定到了**变化最慢**的数据维度（如让 `threadIdx.x` 表示「第几层 z」） | 相邻线程跨度 `Dx * Dy` | 一个 warp 拆成约 32 次事务，带宽利用率掉到 1/32 量级 |

注意第二、三行的**程序结果仍然正确**，只是慢。这也解释了为什么很多 CUDA 程序「能跑对但慢得离谱」——索引顺序没写对，数据是对的，带宽却浪费了几十倍。

**这就是「x 最快」必须被重视的根本原因：它直接决定内存访问是否 coalesced，是 CUDA 性能的头号因素。**

> 顺带修正一个常见说法：有人讲「要让 `threadIdx.y` 连续」——**线程编号的快慢顺序是 CUDA 规范定死的，改不了**。你真正能选的只有一件事：**把数据的哪个维度绑定到 `threadIdx.x` 上**。选最内层（变化最快）的那个，就赢了。

<a id="sec6-4"></a>

### 6.4 从软件坐标到硬件的完整链路

把整个映射串起来，其实是一次「三步坐标变换」：

```
软件逻辑线程坐标 (blockIdx, threadIdx)
        │  ① 线性化 / 索引计算
        ▼
数据全局索引 (linear index)
        │  ② 硬件自动把 warp 映射到 SM 的调度单元
        ▼
全局内存物理地址 (address)
```

第 ① 步是**你写的代码**（就是本文讲的 `row`、`col`、`idx` 计算）；第 ② 步是**硬件和驱动自动完成**的（warp 调度、地址翻译）。你只需要保证第 ① 步算出的索引能让「相邻线程 → 相邻地址」，第 ② 步就会给你最优的带宽。

<a id="sec6-5"></a>

### 6.5 Block 与 Grid 的维度限制

理解底层，还要知道几个硬约束（来自 CUDA 规范）：

- 每个 Block 最多 **1024** 个线程（`blockDim.x × blockDim.y × blockDim.z ≤ 1024`）；
- 各维度上限：`blockDim.x ≤ 1024`、`blockDim.y ≤ 1024`、`blockDim.z ≤ 64`；
- Grid 各维度上限很大（`gridDim.x` 约 2³¹−1，`gridDim.y / z` 约 65535），通常够用；
- 一个 warp 固定 **32** 个线程。

⚠️ **三维分块要特别小心 `blockDim.x`**：`blockSize(8, 8, 8)` = 512 在三维上很均衡，也确实是 warp 的整数倍（16 个 warp），**但 `blockDim.x = 8 < 32`，按 §6.2 的分析，它反而会削弱合并访问**。

因此处理体数据时，下面这类**保证 `blockDim.x ≥ 32`** 的配置往往比 `(8, 8, 8)` 更快：

| 配置 | 线程数 | `blockDim.x` | 合并访问 |
|---|:---:|:---:|:---:|
| `(8, 8, 8)` | 512 | 8 | 差：一个 warp 切成 4 段 |
| `(32, 4, 4)` | 512 | 32 | 优：一个 warp 恰好一行 |
| `(32, 8, 1)` | 256 | 32 | 优：同上（二维切片常用） |

> 这不是说 `(8, 8, 8)` 是错的——**它结果正确，只是通常不是最快的**。选块形状时，请把「保证 `blockDim.x` 是 32 的倍数」排在「三维均衡」之前。

---

<a id="sec7"></a>

## 七、常见陷阱

1. **方阵假设错误**：`gridSize` 的 x / y 分量都用了同一个 `N`，但矩阵其实是 `M×N`（见 §3.2）。方向对应要牢记：`.x` → 列，`.y` → 行。

2. **漏掉边界保护**：当 `N`（或 `M`、`Dz`）不是 `blockSize` 的整数倍时，Grid 会「多开」一些线程，这些线程算出的 `row`/`col` 会越界，必须加 `if (row < M && col < N)` 判断，否则读写非法地址。

3. **线性化时用错了「行宽」**：`idx = row * cols + col` 里的 `cols` 必须是「矩阵的真实列数（每行元素数）」，而不是 `blockDim.x` 或 `gridDim.x`。这是最高频的错误。

4. **搞反 row-major 与 column-major**：CUDA 的 C/C++ 原生是 row-major；但 **cuBLAS、cuSOLVER 等库沿用 Fortran 的 column-major**，索引方向会反过来，混用时务必单独核对。

5. **`.x` / `.y` 方向与数据方向错位**：把变化最慢的数据维度绑到了 `.x` 上，导致相邻线程地址跨度巨大、性能骤降（见 §6.3）。

6. **`blockDim.x` 不是 32 的倍数**：尤其是三维分块写 `(8, 8, 8)`、`(4, 4, 4)` 时，一个 warp 会横跨多行/多层，合并访问被打断（见 §6.2、§6.5）。**程序结果依然正确，但带宽可能差好几倍**，因此这个坑极难被发现。

7. **warp 内严重分支分歧**：`if (data[tid] > 0)` 这类依赖数据而非线程编号的分支，会让 warp 把两条路径都走一遍，耗时变成两者之和（见 §6.1）。与陷阱 5、6 一样只影响速度，不影响正确性。

8. **忘了 `.x` / `.y` 与「行 / 列」的绑定是自己的选择**：误以为「必须用 x 表示列」，在 column-major 数据（或转置访问）场景下生搬硬套，反而破坏局部性。正确做法是——**永远把「变化最快的线程维度 x」绑定到「变化最快的数据维度」上**。

---

<a id="sec8"></a>

## 八、完整可运行示例

### 2D：矩阵加法（`M×N` 非方阵）

下面这份代码是自包含的，可直接编译运行：

```bash
nvcc -O2 mat_add.cu -o mat_add && ./mat_add
```

```cuda
#include <cstdio>
#include <cstdlib>
#include <cuda_runtime.h>

#define CUDA_CHECK(call)                                                   \
    do {                                                                   \
        cudaError_t err = (call);                                          \
        if (err != cudaSuccess) {                                          \
            fprintf(stderr, "CUDA error %s:%d: %s\n",                      \
                    __FILE__, __LINE__, cudaGetErrorString(err));          \
            exit(EXIT_FAILURE);                                            \
        }                                                                  \
    } while (0)

__global__ void mat_add(const float* a, const float* b, float* c,
                        int rows, int cols) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;   // .y → 行
    int col = blockIdx.x * blockDim.x + threadIdx.x;   // .x → 列

    if (row < rows && col < cols) {                    // 边界保护
        int idx = row * cols + col;                    // row-major 线性化
        c[idx] = a[idx] + b[idx];
    }
}

int main() {
    const int rows = 1000, cols = 800;                 // 非方阵：1000 行 × 800 列
    const size_t n     = (size_t)rows * cols;
    const size_t bytes = n * sizeof(float);

    // —— 主机内存 + 初始化 ——
    float *h_a = (float*)malloc(bytes);
    float *h_b = (float*)malloc(bytes);
    float *h_c = (float*)malloc(bytes);
    for (size_t i = 0; i < n; ++i) { h_a[i] = 1.0f; h_b[i] = 2.0f; }

    // —— 设备内存 ——
    float *d_a, *d_b, *d_c;
    CUDA_CHECK(cudaMalloc(&d_a, bytes));
    CUDA_CHECK(cudaMalloc(&d_b, bytes));
    CUDA_CHECK(cudaMalloc(&d_c, bytes));
    CUDA_CHECK(cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice));

    // —— 启动配置：x 覆盖「列」cols，y 覆盖「行」rows ——
    dim3 blockSize(16, 16);                            // 256 线程（8 warps）
    dim3 gridSize((cols + blockSize.x - 1) / blockSize.x,
                  (rows + blockSize.y - 1) / blockSize.y);

    mat_add<<<gridSize, blockSize>>>(d_a, d_b, d_c, rows, cols);
    CUDA_CHECK(cudaGetLastError());                    // 捕获启动错误
    CUDA_CHECK(cudaDeviceSynchronize());

    // —— 回传 + 校验 ——
    CUDA_CHECK(cudaMemcpy(h_c, d_c, bytes, cudaMemcpyDeviceToHost));
    bool ok = true;
    for (size_t i = 0; i < n; ++i) {
        if (h_c[i] != 3.0f) { ok = false; break; }
    }
    printf("mat_add %s (h_c[0] = %.1f)\n", ok ? "OK" : "FAILED", h_c[0]);

    cudaFree(d_a); cudaFree(d_b); cudaFree(d_c);
    free(h_a); free(h_b); free(h_c);
    return ok ? 0 : 1;
}
```

**注意 `gridSize` 两个分量的顺序**：`dim3` 的构造参数是 `(x, y, z)`，而 x 要覆盖「列」、y 要覆盖「行」，所以这里第一个参数是 `cols`、第二个是 `rows`——**与 `int rows, cols` 的书写顺序正好相反**，这是初学者最容易写反的地方。

### 3D：体数据 +1

```cuda
__global__ void volume_inc(const float* in, float* out, int Dx, int Dy, int Dz) {
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;
    int z = blockIdx.z * blockDim.z + threadIdx.z;

    if (x < Dx && y < Dy && z < Dz) {              // 三维边界保护
        int idx = x + y * Dx + z * Dx * Dy;        // x 最快，z 最慢
        out[idx] = in[idx] + 1.0f;
    }
}

// 启动：注意这里保证 blockDim.x = 32（warp 对齐，见 §6.5）
dim3 blockSize(32, 4, 4);                          // 512 线程
dim3 gridSize((Dx + blockSize.x - 1) / blockSize.x,
              (Dy + blockSize.y - 1) / blockSize.y,
              (Dz + blockSize.z - 1) / blockSize.z);
volume_inc<<<gridSize, blockSize>>>(d_in, d_out, Dx, Dy, Dz);
```

内存分配 / 拷贝 / 校验部分与 2D 示例完全相同，此处省略。

> 想验证 §6.5 的结论，可以把 `blockSize` 改成 `(8, 8, 8)` 再跑一次——**结果一模一样，但用 `nvprof` / Nsight 看全局内存事务数会发现明显变多**。

---

<a id="sec9"></a>

## 九、小结

1. **四个内置变量都是三维的**，用几个维度就激活几个分量；未激活时 `Idx` 为 0、`Dim` 为 1。
2. **每个维度的全局坐标 = `blockIdx.d * blockDim.d + threadIdx.d`**，1D / 2D / 3D 都是同一套逻辑。
3. **SIMT 的本质是「SIMD 硬件 + 多线程抽象」**：你写的是标量线程代码，硬件把 32 个线程捆成 warp、用一条指令驱动（见 §6.1）。这既解放了程序员，也把 SIMD 的约束原封不动地留了下来。
4. **`threadIdx.x` 变化最快**是 CUDA 规范定死的；而「把 x 绑定到最内层数据维度（列）」是你自己的选择——两个「最快维度」对齐才能合并访问。
5. **多维 → 一维线性化**用 row-major：2D 是 `row * cols + col`，3D 是 `x + y*Dx + z*Dx*Dy`，跨度随维度「变慢」而放大。
6. **务必加边界保护**，且线性化时用「真实维度尺寸」而不是 `blockDim` 或 `gridDim`。
7. **`blockDim.x` 尽量取 32 的倍数**——否则一个 warp 会横跨多行/多层，合并访问被打断。
8. **避免 warp 内分支分歧**——依赖数据（而非线程编号）的分支会让两条路径都被执行，耗时变成两者之和。

后三条有个共同点：**它们都不影响正确性，只影响速度**。这正是 CUDA 调优最难的地方——程序跑得对，但可能慢了好几倍，而编译器和运行时都不会给你任何提示。

理解这套映射，本质是理解「软件线程坐标 → 数据索引 → 物理内存地址」这三次坐标变换。只要抓住「x 最快、warp 按线性 ID 划分、row-major 线性化、`blockDim.x` 对齐 32」这四点，任何维度的 CUDA 索引都能自己推出来。
