# CUB 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：写过基本 CUDA C++ kernel、理解 warp/block 心智模型，正在**手写 kernel** 但发现"reduce / scan / sort / histogram 这些原语每次都要重新造轮子"，想**在自己的 kernel 里就地复用高性能原语**的程序员。
> **目标**：2~3 周内，从"用 `cub::DeviceReduce` 一行归约 1 亿元素"到"能在自己 kernel 里嵌 `BlockScan / WarpReduce`、能读懂 Thrust 内部是怎么调 CUB 的、能针对 3060 调 items-per-thread"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1**（CUB 随 CUDA Toolkit 自带）+ C++17。

---

## 目录

- [0. 写在最前：为什么要学 CUB？](#0-写在最前为什么要学-cub)
- [1. CUB 是什么：一句话讲清 vs Thrust](#1-cub-是什么一句话讲清-vs-thrust)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. CUB 的三层设计：Device / Block / Warp](#3-cub-的三层设计device--block--warp)
- [4. 第一个程序：`cub::DeviceReduce::Sum` 完整流程](#4-第一个程序cubdevicereducesum-完整流程)
- [5. 在你自己 kernel 里嵌 CUB：`BlockScan` / `WarpReduce`](#5-在你自己-kernel-里嵌-cubblockscan--warpreduce)
- [6. 三大杀手锏 API：DeviceRadixSort / DeviceScan / DeviceHistogram](#6-三大杀手锏-apidevicearadixsort--devicescan--devicehistogram)
- [7. Tuning：ITEMS_PER_THREAD 与 BLOCK_THREADS](#7-tuningitems_per_thread-与-block_threads)
- [8. 性能分析与调优](#8-性能分析与调优)
- [9. CUB vs Thrust：怎么选](#9-cub-vs-thrust怎么选)
- [10. 学习路线图（2~3 周）](#10-学习路线图23-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 CUB？

你已经会写 CUDA kernel 了，可能会问：**Thrust 已经能一行 `thrust::sort` 了，为什么还要碰 CUB？** 答案是三点：

1. **Thrust 只能"整个算法在 GPU 上跑"**——你没法在自己的 kernel *内部* 复用 Thrust 的 reduce/scan；
2. **CUB 提供 warp/block 级原语**——可以直接嵌到你现有的 `__global__ void my_kernel(...)` 里；
3. **CUB 是 Thrust 的底层引擎**——`thrust::sort` 内部就是 `cub::DeviceRadixSort`，学 CUB 就是学"Thrust 为什么快"。

### 0.1 一句话对比

| 场景 | 用 Thrust | **用 CUB** |
|:--|:--|:--|
| 排 1 亿个 int | `thrust::sort` 一行 | `cub::DeviceRadixSort::SortKeys` |
| 我自己的 kernel 里做归约 | ❌ 用不了 | **✅ `cub::BlockReduce`** |
| warp 内归约 | 手写 `__shfl_down_sync` | **✅ `cub::WarpReduce`** |
| 复用 Thrust 但要自定义临时空间 | 打不了补丁 | **✅ 显式 temp_storage** |
| 想读懂 Thrust 内部实现 | 看不见 | **✅ CUB 就是实现** |

### 0.2 CUB 现在有多重要？

- **CUDA Toolkit 官方组件**（随 CUDA 自带）；
- **Thrust 的底层引擎**：所有 device-wide 算法背后都是 CUB；
- **cuDF / RAPIDS / cuGraph / FAISS-GPU 的骨架**；
- **CCCL（CUDA C++ Core Libraries）三大件之一**：CUB + Thrust + libcu++；
- **NVIDIA 官方"高性能原语"参考实现**：SM75~SM90 每一代都专门优化。

**一句话**：**如果你在手写 CUDA kernel，CUB 就是"你不用再造的轮子"**——归约、扫描、排序、直方图、去重、runlength encode、select_if 全套，个个打到硬件峰值。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **CUB1 入门** | 会用 `DeviceReduce / DeviceScan / DeviceRadixSort` 一系列 device API |
| **CUB2 熟练** | 会在自己 kernel 里嵌 `BlockScan / BlockReduce / BlockRadixSort` |
| **CUB3 高阶** | 会用 `WarpReduce / WarpScan`、`CacheModifiedInputIterator`、tune `ITEMS_PER_THREAD` |
| **CUB4 专家** | 会看 CUB 源码、写自定义 policy、给 SM86/90 分别调 |

**建议**：**3 天到 CUB1**（能替换掉 Thrust 的调用），**1~2 周到 CUB2**（能给自己 kernel 提速 30~50%），**2~3 周到 CUB3**（覆盖 95% 生产场景）。

---

## 1. CUB 是什么：一句话讲清 vs Thrust

### 1.1 CUB 的定义

> **CUB（CUDA UnBound）是 NVIDIA 官方的 C++ 模板库**，提供 **warp / block / device 三个层级**的高性能 CUDA 原语（reduce、scan、sort、histogram、select、run-length encode 等）。它是 header-only，性能对齐 NVIDIA 内部实验室级 kernel。

关键三点：

1. **三层原语**：**Warp-level（32 thread）**、**Block-level（一个 CTA）**、**Device-level（整张 GPU）**；
2. **可组合**：block-level 原语可以嵌进你的 `__global__` kernel，与你的自定义逻辑无缝混合；
3. **架构感知**：CUB 内部对 SM75/80/86/90 分别选最优实现，你只 include 头文件就自动享受。

### 1.2 CUB vs Thrust

| 维度 | Thrust | **CUB** |
|:--|:--|:--|
| 抽象层级 | 算法级（整个算法） | **原语级（warp / block / device）** |
| 心智 | STL-like | **CUDA-native** |
| 能嵌进自己 kernel | ❌ | **✅ 核心价值** |
| 显式临时空间 | 隐式管理 | **✅ 显式 temp_storage** |
| 定制性 | 中 | **极高** |
| 学习曲线 | 1 天 | **1~2 周** |
| 性能上限 | 高 | **极高（Thrust 的引擎）** |
| 目标读者 | C++ 程序员 | **CUDA kernel 工程师** |

**记忆口诀**：
- **想 GPU 化算法** → Thrust（一行搞定）；
- **想在自己 kernel 里复用高性能原语** → CUB；
- **想吃透 Thrust 为什么快** → 读 CUB 源码。

### 1.3 一张图看清 CUB 在栈里的位置

```
┌──────────────────────────────────────────────────────────┐
│  你的 C++ 应用                                            │
├──────────────────────────────────────────────────────────┤
│  Thrust（STL-like，整算法）                                │
├──────────────────────────────────────────────────────────┤
│  你的手写 CUDA kernel（__global__）    ← CUB 嵌进这里！    │
├──────────────────────────────────────────────────────────┤
│  CUB                                                      │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Device-level：DeviceReduce/Scan/RadixSort/...      │   │
│  │ Block-level ：BlockReduce/BlockScan/BlockRadixSort │   │
│  │ Warp-level  ：WarpReduce/WarpScan/WarpExchange     │   │
│  └────────────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────────┤
│  CUDA Runtime + PTX（shfl / cp.async / ldmatrix）        │
├──────────────────────────────────────────────────────────┤
│  GPU 硬件（3060 / Ampere / SM86）                          │
└──────────────────────────────────────────────────────────┘
```

**核心洞察**：**Thrust 是外壳，CUB 是引擎**。CUB 的三层原语对应 GPU 硬件真实的三层组织（warp、CTA、grid）。

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 好消息：CUB 随 CUDA Toolkit 自带

装了 CUDA 12.1 就已经有 CUB 了，头文件在 `<cuda>/include/cub/`。**无需额外安装**。

### 2.2 一步验证：hello_cub.cu

```cpp
// hello_cub.cu
#include <cub/cub.cuh>
#include <cuda_runtime.h>
#include <iostream>
#include <vector>

int main() {
    int n = 1'000'000;
    std::vector<int> h(n, 1);            // 全 1

    int *d_in, *d_out;
    cudaMalloc(&d_in,  n * sizeof(int));
    cudaMalloc(&d_out, sizeof(int));
    cudaMemcpy(d_in, h.data(), n * sizeof(int), cudaMemcpyHostToDevice);

    // 1. 查询需要多少 temp_storage
    void*  d_temp = nullptr;
    size_t temp_bytes = 0;
    cub::DeviceReduce::Sum(d_temp, temp_bytes, d_in, d_out, n);

    // 2. 分配 temp
    cudaMalloc(&d_temp, temp_bytes);

    // 3. 真跑
    cub::DeviceReduce::Sum(d_temp, temp_bytes, d_in, d_out, n);

    // 4. 取回
    int sum;
    cudaMemcpy(&sum, d_out, sizeof(int), cudaMemcpyDeviceToHost);
    std::cout << "Sum = " << sum << " (expected " << n << ")\n";

    cudaFree(d_in); cudaFree(d_out); cudaFree(d_temp);
}
```

编译：

```bash
nvcc -O3 -std=c++17 -arch=sm_86 hello_cub.cu -o hello_cub
./hello_cub
# Sum = 1000000 (expected 1000000)
```

### 2.3 CUB API 的"两步调用"惯例

**每个 device-level API 都要调两次**——第一次查临时空间大小，第二次真跑。这是 CUB 的核心设计选择：**显式暴露临时空间**，让用户控制 malloc 时机。

```cpp
// 通用模式
size_t temp_bytes = 0;
cub::DeviceXxx::Yyy(nullptr,  temp_bytes, ...);  // 查
void* d_temp;
cudaMalloc(&d_temp, temp_bytes);
cub::DeviceXxx::Yyy(d_temp,   temp_bytes, ...);  // 跑
```

**这一点比 Thrust 麻烦，但也是 CUB 性能上限更高的原因**——你可以复用一块 temp、可以用自定义分配器、可以 pipeline 起来。

### 2.4 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 编译报"cub 未找到" | include 路径不对 | `#include <cub/cub.cuh>` 且 -arch 已设 |
| 结果错乱 | 忘了第一步的 temp 查询 | 严格两步调用 |
| Windows MSVC 死循环 | 模板深度 | `/Zc:__cplusplus /permissive-` |
| kernel 内嵌 BlockReduce 崩 | 忘声明 shared temp | `__shared__ typename BlockReduce::TempStorage tmp;` |
| SM86 用了 SM90 tune 参数 | 用了 -arch=sm_90 tune | 用默认或 `-arch=sm_86` |

---

## 3. CUB 的三层设计：Device / Block / Warp

**这是 CUB 最核心的抽象**——**API 层级 = 硬件层级**。

### 3.1 三层原语一览

| 层级 | 谁在跑 | 典型 API | 使用位置 |
|:--|:--|:--|:--|
| **Device** | 整张 GPU | `cub::DeviceReduce/Scan/RadixSort/Histogram/...` | Host 侧调用 |
| **Block** | 1 个 CTA（256~1024 thread）| `cub::BlockReduce/BlockScan/BlockRadixSort/BlockLoad/BlockStore` | 你的 `__global__` kernel 内 |
| **Warp** | 1 个 warp（32 thread）| `cub::WarpReduce/WarpScan/WarpExchange` | 你的 `__global__` kernel 内 |

### 3.2 什么时候用哪个？

```
你要归约一个数组吗？
    │
    ├─ 全数组 device-wide reduce？
    │      → cub::DeviceReduce::Sum（host 侧一行）
    │
    ├─ 我 kernel 里每个 CTA 要归约自己那块 tile？
    │      → cub::BlockReduce（kernel 内嵌）
    │
    └─ 我 kernel 里每个 warp 要各自归约？
           → cub::WarpReduce（kernel 内嵌）
```

### 3.3 三个层级的性能差异（3060 上归约 100M float）

| 方式 | 耗时 | 备注 |
|:--|:--|:--|
| `cub::DeviceReduce` | ~2 ms | 大数组最优 |
| 手写两阶段 reduce（用 `BlockReduce`）| ~2.1 ms | 与官方几乎相同，因为 DeviceReduce 就是这样实现的 |
| 手写 `__shfl_down_sync` 自撸 | ~3.5 ms | 除非你是天才，很难打赢 CUB |
| `thrust::reduce` | ~2 ms | 底下就是 CUB |

**结论**：**CUB 是 NVIDIA 的"极限参考实现"，很难打赢**。你的时间应该花在"怎么用它组合出更快的融合 kernel"上，而不是"想打败它"。

---

## 4. 第一个程序：`cub::DeviceReduce::Sum` 完整流程

### 4.1 完整代码 + 逐行讲解

见 2.2 节。这里补充讲解 4 个要点。

### 4.2 小白也能懂：逐段拆解

#### 4.2.1 为什么要两步调用？

```cpp
cub::DeviceReduce::Sum(nullptr, temp_bytes, d_in, d_out, n);   // ① 查
cudaMalloc(&d_temp, temp_bytes);                                // ② 你自己分配
cub::DeviceReduce::Sum(d_temp, temp_bytes, d_in, d_out, n);    // ③ 跑
```

**动机**：CUB 内部的树形 reduce 需要一块中间缓冲（大小 ≈ log(n) 数量级）。CUB **不主动 malloc**（因为 malloc 慢，且用户可能想复用/用池），而是**告诉你需要多大，让你自己管**。

**好处**：
- 一个 temp 可以喂多次 `Sum` 调用（复用）；
- 可以用 `cudaMallocAsync`、内存池、Thrust 分配器；
- 可以避免高频调用里的 malloc 抖动。

#### 4.2.2 参数类型

- `d_in / d_out`：**必须是 device 指针**——CUB 不做 host 拷贝，纯 GPU 端；
- `n`：元素数量；
- 返回值是 `cudaError_t`：非 0 表示出错（一般是 temp 大小不够或指针无效）。

#### 4.2.3 支持自定义归约算子

```cpp
struct Max { __device__ int operator()(int a, int b) const { return a > b ? a : b; } };
Max op;
cub::DeviceReduce::Reduce(d_temp, temp_bytes,
                          d_in, d_out, n,
                          op, /*init=*/INT_MIN);
```

**任何满足结合律 + 有单位元的二元操作都能用**（max/min/product/bitwise）。

#### 4.2.4 常用 device API 一览

| API | 作用 |
|:--|:--|
| `DeviceReduce::Sum / Min / Max / ArgMax / ArgMin` | 归约 |
| `DeviceScan::InclusiveSum / ExclusiveSum / ...` | 前缀和 |
| `DeviceRadixSort::SortKeys / SortPairs` | 排序（integer/float 都行）|
| `DeviceHistogram::HistogramEven / HistogramRange` | 直方图 |
| `DeviceSelect::If / Flagged / Unique` | 流式压缩 |
| `DeviceRunLengthEncode::Encode` | 游程编码 |
| `DevicePartition::If` | 按谓词分区 |
| `DeviceSpmv::CsrMV` | 稀疏矩阵向量乘 |
| `DeviceSegmentedReduce/Sort/Scan` | 分段版本（多组）|

**这就是 CUB 的"武器库"**——每个 API 都是 NVIDIA 官方极限性能实现。

#### 4.2.5 6 个新手常见坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | 忘第一步查 temp | 崩溃或结果乱 | 严格两步调用 |
| 2 | temp_bytes 传 int 不是 size_t | 溢出 | 用 `size_t` |
| 3 | 归约算子非结合 | 结果不确定 | float 求和天然不精确，别慌 |
| 4 | d_out 只分配了 1 元素但 `ArgMax` 要 2 | 越界 | 看 API 签名，ArgMax 输出是 KeyValuePair |
| 5 | 在 stream 上跑但没同步就读结果 | 拿到旧值 | 加 stream 参数 + 显式同步 |
| 6 | 同一 temp buffer 供不同 API 用大小不够 | 崩 | 取多个 API 的 max 大小 |

---

## 5. 在你自己 kernel 里嵌 CUB：`BlockScan` / `WarpReduce`

**这是 CUB 相对 Thrust 的核心价值**。

### 5.1 `BlockReduce`：CTA 内归约

```cpp
#include <cub/block/block_reduce.cuh>

template <int BLOCK_THREADS>
__global__ void my_reduce_kernel(int* in, int* out, int n) {
    using BlockReduce = cub::BlockReduce<int, BLOCK_THREADS>;
    __shared__ typename BlockReduce::TempStorage temp;

    // 每 thread 加载一个元素
    int tid = blockIdx.x * BLOCK_THREADS + threadIdx.x;
    int val = (tid < n) ? in[tid] : 0;

    // 一行 CTA 内归约
    int block_sum = BlockReduce(temp).Sum(val);

    if (threadIdx.x == 0) atomicAdd(out, block_sum);
}

// launch
my_reduce_kernel<256><<<blocks, 256>>>(d_in, d_out, n);
```

**要点**：
- `BlockReduce::TempStorage` 必须放 `__shared__`；
- 一次 `.Sum(val)` 就把 256 个 thread 的值归约成一个；
- 只有 `threadIdx.x==0` 有归约结果，其他 thread 的返回值是未定义的。

### 5.2 `BlockScan`：CTA 内前缀和

```cpp
#include <cub/block/block_scan.cuh>

template <int BLOCK_THREADS>
__global__ void my_scan(int* in, int* out) {
    using BlockScan = cub::BlockScan<int, BLOCK_THREADS>;
    __shared__ typename BlockScan::TempStorage temp;

    int tid = blockIdx.x * BLOCK_THREADS + threadIdx.x;
    int val = in[tid];
    int prefix;
    BlockScan(temp).InclusiveSum(val, prefix);
    out[tid] = prefix;
}
```

**用途**：stream compaction、稀疏矩阵构建、动态并行分配槽位——GPU 编程的基本功。

### 5.3 `WarpReduce`：warp 内归约

```cpp
#include <cub/warp/warp_reduce.cuh>

__global__ void my_kernel(...) {
    using WarpReduce = cub::WarpReduce<int>;
    __shared__ typename WarpReduce::TempStorage temp[8];  // 每 warp 一份

    int lane = threadIdx.x % 32;
    int warp_id = threadIdx.x / 32;

    int val = ...;
    int wsum = WarpReduce(temp[warp_id]).Sum(val);

    if (lane == 0) {
        // 每 warp 的 lane 0 拿到 warp 内 32 值之和
    }
}
```

**性能**：CUB 的 WarpReduce 用 `__shfl_down_sync` 硬件指令，**5 条指令搞定 32 值归约**——你手写多半慢 10~20%。

### 5.4 `BlockRadixSort`：CTA 内排序

```cpp
using BlockRadixSort = cub::BlockRadixSort<int, BLOCK_THREADS, ITEMS_PER_THREAD>;
__shared__ typename BlockRadixSort::TempStorage temp;

int items[ITEMS_PER_THREAD];  // 每 thread 拿多个
// ... 加载到 items ...
BlockRadixSort(temp).Sort(items);
// 现在 items 在 CTA 内全局有序（thread 0 拿最小的 K 个，thread N-1 拿最大的）
```

**用途**：局部排序、top-k、直方图桶分配——**这是"GPU kernel 内部小规模排序"的标准答案**。

### 5.5 `BlockLoad / BlockStore`：向量化加载

```cpp
using BlockLoad = cub::BlockLoad<int, BLOCK_THREADS, ITEMS_PER_THREAD,
                                 cub::BLOCK_LOAD_VECTORIZE>;
__shared__ typename BlockLoad::TempStorage temp;

int items[ITEMS_PER_THREAD];
BlockLoad(temp).Load(in + blockIdx.x * TILE_SIZE, items);
```

**价值**：**自动向量化访存**（int4 / float4），把访存效率打到峰值，比你手写 `reinterpret_cast<int4*>` 干净得多。

---

## 6. 三大杀手锏 API：DeviceRadixSort / DeviceScan / DeviceHistogram

### 6.1 `DeviceRadixSort`

**性能之王**。100M 个 32-bit int 排序：

| 方法 | 耗时 |
|:--|:--|
| `std::sort` (CPU) | ~5 s |
| `thrust::sort` | ~80 ms |
| **`cub::DeviceRadixSort`** | **~75 ms**（Thrust 底下就是它）|

支持 `SortKeys / SortPairs`（键值对同排）、`SortKeysDescending / SortPairsDescending`。

### 6.2 `DeviceScan::ExclusiveSum`

**stream compaction 三件套之一**：

```cpp
// 步骤 1：给每个元素打标（1 = 保留，0 = 丢弃）
// 步骤 2：exclusive scan 得到"如果保留应该放哪个 index"
// 步骤 3：scatter
```

CUB 提供 `DeviceSelect::If / Flagged / Unique` 直接把三步合成一个 API。

### 6.3 `DeviceHistogram`

```cpp
cub::DeviceHistogram::HistogramEven(
    d_temp, temp_bytes,
    d_samples, d_histogram,
    /*num_levels=*/257,           // 256 bins + 1 boundary
    /*lower=*/0, /*upper=*/256,
    /*num_samples=*/n);
```

**图像处理 / 数据分析里最快的 GPU 直方图**——一亿像素几毫秒。

---

## 7. Tuning：ITEMS_PER_THREAD 与 BLOCK_THREADS

CUB 的 block-level 原语大都有两个模板参数：

- `BLOCK_THREADS`：一个 CTA 有多少 thread（一般 128/256/512）；
- `ITEMS_PER_THREAD`：每个 thread 处理多少元素（一般 4/8/16）；

**Tile size = BLOCK_THREADS × ITEMS_PER_THREAD**。

### 7.1 怎么选？

| 硬件目标 | BLOCK_THREADS | ITEMS_PER_THREAD |
|:--|:--|:--|
| SM75/80/86（3060）compute-bound | 128~256 | 8~16 |
| SM75/80/86 memory-bound | 128 | 4~8 |
| SM90（H100）| 256~512 | 8~16 |

### 7.2 经验法则

- **register pressure 越高，ITEMS_PER_THREAD 要越小**；
- **shared memory 用得多，BLOCK_THREADS 要减**；
- **访存 bandwidth-bound**：`ITEMS_PER_THREAD` 大有助于向量化；
- **compute-bound**：反过来。

**建议**：**用 CUB 官方 tune 值** —— CUB 内部对 SM75~SM90 都有默认 policy，你不写就用它的最优默认。**除非你在极端场景**（比如 tile 特别小/特别大），否则别瞎调。

---

## 8. 性能分析与调优

### 8.1 计时正确姿势

```cpp
cudaDeviceSynchronize();
auto t0 = std::chrono::high_resolution_clock::now();

for (int i = 0; i < 100; ++i)
    cub::DeviceReduce::Sum(d_temp, temp_bytes, d_in, d_out, n);
cudaDeviceSynchronize();

auto t1 = std::chrono::high_resolution_clock::now();
double ms = std::chrono::duration<double, std::milli>(t1-t0).count() / 100.0;
```

### 8.2 与 Nsight Compute 联用

```bash
ncu --set full ./hello_cub
```

看 CUB kernel 的三个关键指标：
- **DRAM Throughput %**：sort/reduce/scan 大都 memory-bound，应该 > 70%；
- **SM Busy %**：> 80% 才算跑满；
- **Achieved Occupancy**：> 50%。

### 8.3 三条经验

1. **复用 temp_storage**：高频调用时一次分配足够大的 temp，多次复用；
2. **用 stream 版 API**：`cub::DeviceReduce::Sum(..., stream)` 与你的其他 kernel 重叠；
3. **不要嵌套 kernel**：CUB 的 device API 是"host 侧一整个算法"，不要在你的 `__global__` 里调 `DeviceReduce`（那要开 dynamic parallelism，很慢）。

---

## 9. CUB vs Thrust：怎么选

| 场景 | 用 Thrust | **用 CUB** |
|:--|:--|:--|
| 快速原型 | ✅ | ⚠️ |
| 我在写 `__global__` kernel | ❌ 不能嵌 | ✅ 核心用途 |
| 需要复用 temp buffer | ❌ | ✅ |
| 想控制 stream/pipeline | ⚠️（可 policy）| ✅ 更细 |
| 想减小编译时间 | ✅（模板浅）| ⚠️（也不深）|
| 需要 warp 级原语 | ❌ | ✅ 唯一选择 |
| 需要 fancy iterator | ✅ | 部分支持 |

**决策树**：
- 只用 GPU 跑现成算法 → **Thrust**；
- 手写 kernel 且要复用高性能原语 → **CUB**；
- 两者混用 → 常见做法，用 `raw_pointer_cast` 打通。

---

## 10. 学习路线图（2~3 周）

### 🟢 阶段 1（Day 1~3）：入门

- ✅ 跑通 `hello_cub`；
- ✅ 掌握"两步调用"惯例；
- ✅ 会用 `DeviceReduce / DeviceScan / DeviceRadixSort` 三大 device API；
- ✅ 理解三层设计（Device/Block/Warp）。

### 🟡 阶段 2（Day 4~10）：嵌入自己 kernel

- ✅ 写一个含 `BlockReduce` 的两阶段归约 kernel；
- ✅ 写一个含 `BlockScan` 的 stream compaction；
- ✅ 用 `BlockLoad + BlockStore` 向量化访存；
- ✅ 用 `WarpReduce` 做 warp 内聚合。

### 🟠 阶段 3（Day 11~14）：进阶

- ✅ 用 `BlockRadixSort` 做 CTA 内小规模排序（top-k）；
- ✅ 掌握 `ITEMS_PER_THREAD` 调优；
- ✅ 用 `DeviceHistogram / DeviceSelect / DeviceRunLengthEncode`；
- ✅ 用 stream 让 CUB API 与其他 kernel 并发。

### 🔴 阶段 4（Day 15~21）：源码级

- ✅ 读 CUB 源码：看 `DeviceRadixSort` 内部怎么调 `BlockRadixSort`；
- ✅ 写一个"我自己的 kernel + CUB block 原语"融合示例（如 fused softmax）；
- ✅ 用 Nsight Compute 对比手写 vs CUB。

---

## 11. 精选资源与踩坑清单

### 11.1 必读官方资源

| 资源 | 用途 | 链接 |
|:--|:--|:--|
| CUB GitHub（现属 CCCL）| 源码 + 文档 | <https://github.com/NVIDIA/cccl/tree/main/cub> |
| CUB 官方文档 | API 详解 | <https://nvidia.github.io/cccl/cub/> |
| CCCL 主页 | Thrust+CUB+libcu++ | <https://nvidia.github.io/cccl/> |
| CUB examples | 40+ 例子 | <https://github.com/NVIDIA/cccl/tree/main/cub/examples> |
| GTC "Beyond Thrust" | 官方讲座 | 搜 "GTC CUB Duane Merrill" |

### 11.2 高质量博客

- **NVIDIA Blog：CUB 系列**：<https://developer.nvidia.com/blog/tag/cub/>；
- **Duane Merrill 的博客**（CUB 主设计者）：讲 back-scan / radix sort 内部；
- **《High-Performance and Scalable GPU Graph Traversal》**：CUB 的诞生场景。

### 11.3 完整踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| kernel 内 BlockReduce 崩 | TempStorage 没 `__shared__` | `__shared__ typename BR::TempStorage tmp;` |
| 结果只有 thread 0 对 | BlockReduce 只保证 lane 0 有值 | 用 `.Sum(v)` 返回值 |
| radix sort float 负数错 | float 用 int reinterpret 前需 flip | CUB 自动处理，用 `float` 别自己 reinterpret |
| DeviceScan 结果差 1 位 | inclusive vs exclusive | 看清 API 名字 |
| 两次调用 temp 大小变 | 输入 n 变了 | 用最大 n 的 size 做 temp |
| 在 stream 上 API 结果空 | 没同步就读 | `cudaStreamSynchronize(stream)` |
| 模板膨胀编译慢 | 多种 BLOCK_THREADS 组合 | 别一次实例化太多 |
| ITEMS_PER_THREAD 太大 spill | register 不够 | 减小 items 或 block |
| DeviceHistogram 结果错 | num_levels = bins+1 | 记住 `num_levels = num_bins + 1` |
| Thrust 与 CUB 混用报错 | 头文件冲突（旧版本）| 用同一版本 CCCL |

### 11.4 一句话总结

> **CUB = "NVIDIA 官方的 CUDA 原语武器库"**。它把 warp/block/device 三层原语打磨到硬件峰值，让你**在自己的 kernel 里以近似 STL 的心智复用高性能归约、扫描、排序**。**Thrust 是你上层做业务的胶水，CUB 是你 kernel 里的钢筋**。
>
> **学它的收益**：**从"手撸 shared memory 归约的 CUDA 老兵" → "5 行代码嵌入官方极限性能原语的现代 CUDA 工程师"**。想深入 kernel 性能优化、想读 Thrust/RAPIDS 底层、想为 SM90 写融合算子，CUB 是必修课。

---

**祝你写出接近硬件峰值的 kernel。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
