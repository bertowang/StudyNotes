# Thrust 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：C++ 程序员，会用 STL（`std::vector` / `std::sort` / `std::transform`），想**用几乎相同的心智把并行算法搬到 GPU 上**，同时**不想被 CUDA 的 grid/block/thread 细节淹没**。
> **目标**：1~2 周内，从"用 `thrust::sort` 排 1 亿个数"到"能自定义 functor 组合 `transform+reduce`、能与手写 CUDA kernel 混用、能针对 3060 调优内存分配"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1**（Thrust 随 CUDA Toolkit 自带）+ C++17。

---

## 目录

- [0. 写在最前：为什么要学 Thrust？](#0-写在最前为什么要学-thrust)
- [1. Thrust 是什么：一句话讲清 vs STL / vs CUB](#1-thrust-是什么一句话讲清-vs-stl--vs-cub)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. Thrust 核心：Container / Iterator / Algorithm / Execution Policy](#3-thrust-核心container--iterator--algorithm--execution-policy)
- [4. 第一个程序：CPU 版 vs GPU 版一字之差](#4-第一个程序cpu-版-vs-gpu-版一字之差)
- [5. 三大常用套路：Sort / Reduce / Scan](#5-三大常用套路sort--reduce--scan)
- [6. Fancy Iterator：Thrust 的杀手锏](#6-fancy-iteratorthrust-的杀手锏)
- [7. 与手写 CUDA kernel 混用](#7-与手写-cuda-kernel-混用)
- [8. 性能分析与调优](#8-性能分析与调优)
- [9. Thrust vs CUB：什么时候该"下沉"](#9-thrust-vs-cub什么时候该下沉)
- [10. 学习路线图（1~2 周）](#10-学习路线图12-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 Thrust？

作为 C++ 程序员你可能会问：**都在用 `std::sort / std::reduce` 了，为什么要额外学一个 Thrust？** 答案是：**Thrust 让你用同样的 STL 心智，把 `sort` 从 CPU 搬到 GPU 上跑，速度直接快 10~50 倍**——而你写的代码只多改了 2 个字符。

### 0.1 一句话对比

| 场景 | 用 STL | 用 Thrust |
|:--|:--|:--|
| 排 1 亿个 int | `std::sort` ~ 5 秒 | `thrust::sort` ~ **80 ms** |
| 求和 1 亿个 float | `std::reduce` ~ 100 ms | `thrust::reduce` ~ **2 ms** |
| 前缀和 (scan) | `std::inclusive_scan` ~ 200 ms | `thrust::inclusive_scan` ~ **4 ms** |
| 需要写多少 GPU 代码 | 全 CPU | **改容器 + 加 `thrust::` 前缀** |
| 学习成本 | 你已经会 | **~ 1 天** |

### 0.2 Thrust 现在有多重要？

- **CUDA Toolkit 官方组件**（不用额外装），NVIDIA 长期维护；
- **STL 的 GPU 版本**：几乎所有 STL 里的并行算法都有对应实现；
- **RAPIDS（cuDF / cuML）、cuGraph** 内部大量使用；
- **CCCL（CUDA C++ Core Libraries）**：2024 年后 Thrust + CUB + libcu++ 合并为 CCCL 项目，统一维护；
- **写"胶水代码"的效率王**：数据前后处理、host↔device 拷贝、临时排序去重，Thrust 一行搞定。

**一句话**：**如果你写 C++ 想快速把已有算法 GPU 化，Thrust 是投入产出比最高的选择**——比手写 CUDA 快 100 倍上手时间，比 cuBLAS/cuDNN 灵活得多。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **Th1 入门** | 会用 `device_vector`、`host_vector`、`thrust::sort/reduce/copy` |
| **Th2 熟练** | 会写自定义 functor，会组合 `transform+reduce`、`sort_by_key` |
| **Th3 高阶** | 会用 fancy iterator（zip/counting/permutation/transform）、CUDA stream 混用 |
| **Th4 专家** | 会 Thrust ↔ CUB 互转、custom execution policy、自定义分配器优化 |

**建议**：**3 天到 Th1**（能替换掉 CPU 版），**1~2 周到 Th2/Th3**（覆盖 95% 生产场景）。

---

## 1. Thrust 是什么：一句话讲清 vs STL / vs CUB

### 1.1 Thrust 的定义

> **Thrust 是一个 C++ 模板库**（header-only），提供**与 STL 高度对齐的 API**，但底层可以在 CUDA、OpenMP、TBB、CPP（单线程）等多种执行后端上运行。你写的是 `thrust::sort(policy, begin, end)`，Thrust 挑合适的后端把它跑起来。

关键三点：

1. **STL-like API**——`thrust::sort / reduce / transform / scan / copy / unique` 全套；
2. **多后端**——同一份代码能跑 GPU（CUDA）、多核 CPU（OpenMP/TBB）、单线程 CPU；
3. **Container + Algorithm + Iterator** 三件套完全对标 STL。

### 1.2 Thrust vs STL vs CUB

| 维度 | STL | **Thrust** | CUB |
|:--|:--|:--|:--|
| 抽象层级 | 算法级 | **算法级** | Warp / Block / Device 级原语 |
| 语言 | C++ | **C++ 模板** | C++ 模板 |
| 后端 | CPU 单线程 | **CUDA / OpenMP / TBB / CPU** | CUDA only |
| 心智模型 | STL | **STL** | CUDA-native |
| 学习曲线 | 已会 | **1 天** | 1 周 |
| 定制性 | 一般 | 中 | **极高** |
| 目标读者 | 所有 C++ | **想 GPU 化的 C++** | GPU kernel 工程师 |

**记忆口诀**：
- **"STL 上加个 `thrust::`"** → Thrust（快速 GPU 化）；
- **"想自己写 kernel 但要复用 warp/block 原语"** → CUB；
- **"只想跑 CPU"** → STL。

### 1.3 一张图看清 Thrust 在栈里的位置

```
┌──────────────────────────────────────────────────────────┐
│  你的 C++ 应用（数据处理 / 数值计算 / 图算法 / 前后处理）    │
├──────────────────────────────────────────────────────────┤
│  Thrust（STL-like API：sort/reduce/scan/transform/copy）  │
├──────────────────────────────────────────────────────────┤
│  CUB（warp/block/device 级原语）  ← Thrust 内部大量调用    │
├──────────────────────────────────────────────────────────┤
│  libcu++（std:: 的 CUDA 版：atomic/tuple/optional/...）    │
├──────────────────────────────────────────────────────────┤
│  CUDA Runtime + PTX                                       │
├──────────────────────────────────────────────────────────┤
│  GPU 硬件（3060 / Ampere / SM86）                          │
└──────────────────────────────────────────────────────────┘
```

**核心洞察**：Thrust 是"高层 STL 门面"，CUB 是"底层实现引擎"，libcu++ 是"std:: 在 device 侧的落地"。**三者现在统一叫 CCCL（CUDA C++ Core Libraries）**。

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 好消息：Thrust 随 CUDA Toolkit 自带

装了 CUDA 12.1 你就已经有 Thrust 了——**无需额外安装**。头文件在：

- Linux：`/usr/local/cuda/include/thrust/`
- Windows：`C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\include\thrust\`

### 2.2 一步验证：hello_thrust.cu

```cpp
// hello_thrust.cu
#include <thrust/device_vector.h>
#include <thrust/sort.h>
#include <thrust/generate.h>
#include <cstdlib>
#include <iostream>

int main() {
    // Host 侧生成 1M 个随机数
    thrust::host_vector<int> h(1'000'000);
    thrust::generate(h.begin(), h.end(), std::rand);

    // 一行拷到 GPU
    thrust::device_vector<int> d = h;

    // 一行 GPU 排序
    thrust::sort(d.begin(), d.end());

    // 一行拷回 CPU
    h = d;

    std::cout << "First: " << h.front()
              << "  Last: " << h.back() << "\n";
    std::cout << "Sorted? "
              << std::is_sorted(h.begin(), h.end()) << "\n";
}
```

编译：

```bash
nvcc -O3 -std=c++17 -arch=sm_86 hello_thrust.cu -o hello_thrust
./hello_thrust
```

期望输出：

```
First: 0  Last: 2147483591
Sorted? 1
```

### 2.3 想用最新的 Thrust？装 CCCL

CUDA 12.1 自带的 Thrust 是 2.x；想要最新特性（比如更好的 SM90 支持）可以装独立版：

```bash
git clone --depth 1 https://github.com/NVIDIA/cccl.git
# 编译时用 -I/path/to/cccl/thrust -I/path/to/cccl/cub -I/path/to/cccl/libcudacxx/include
```

**大部分人不需要**，随 Toolkit 版本足够用。

### 2.4 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| `undefined reference to thrust::...` | 忘记用 nvcc 编 | Thrust 只能 nvcc/clang-cuda 编 |
| 编译很慢 | 模板膨胀 | 一个 TU 少放几个 Thrust 算法调用 |
| `device_vector` 用起来奇慢 | 每次 push_back 重新分配 | 先 `resize` 或 `reserve` |
| `thrust::for_each` 在 host 上跑 | 用 `host_vector` 迭代器触发了 host policy | 显式加 `thrust::device` policy |
| lambda 报 "extended lambda 需 experimental" | nvcc 需要开关 | `--extended-lambda` |
| MSVC 死不了 | Windows 上模板问题 | 用 `/Zc:__cplusplus /permissive-` |

---

## 3. Thrust 核心：Container / Iterator / Algorithm / Execution Policy

Thrust 的四大支柱，完全对标 STL：

### 3.1 Container

| Thrust | STL 对应 | 说明 |
|:--|:--|:--|
| `thrust::host_vector<T>` | `std::vector<T>` | 就是 std::vector 的别名（几乎） |
| `thrust::device_vector<T>` | 无 | **在 GPU 显存里的 vector**（关键）|

**赋值即拷贝**：`d = h` 就是 `cudaMemcpy(host→device)`，非常直观。

### 3.2 Iterator

- `.begin() / .end()`：像 STL 一样；
- **Fancy Iterator**（Thrust 独有）：`counting_iterator / constant_iterator / zip_iterator / permutation_iterator / transform_iterator`——第 6 节详讲。

### 3.3 Algorithm

Thrust 提供了 100+ 算法，最常用的：

| 类别 | Thrust API | 对应 STL |
|:--|:--|:--|
| 变换 | `thrust::transform` | `std::transform` |
| 归约 | `thrust::reduce` | `std::reduce` |
| 扫描（前缀和）| `thrust::inclusive_scan / exclusive_scan` | C++17 有 |
| 排序 | `thrust::sort / sort_by_key / stable_sort` | `std::sort` |
| 拷贝 | `thrust::copy / copy_if` | `std::copy` |
| 去重 | `thrust::unique` | `std::unique` |
| 集合 | `thrust::set_intersection` | `std::set_intersection` |
| 计数 | `thrust::count_if` | `std::count_if` |
| 归并 | `thrust::merge` | `std::merge` |
| 生成 | `thrust::generate / fill / sequence` | `std::generate` |

### 3.4 Execution Policy（关键）

**这是 Thrust 独有的最关键概念**：告诉算法"在哪儿跑"。

```cpp
#include <thrust/execution_policy.h>

thrust::sort(thrust::device, d_vec.begin(), d_vec.end());   // GPU
thrust::sort(thrust::host,   h_vec.begin(), h_vec.end());   // CPU 单线程
thrust::sort(thrust::omp::par, h_vec.begin(), h_vec.end()); // OpenMP（要开启后端）
thrust::sort(thrust::tbb::par, h_vec.begin(), h_vec.end()); // TBB
```

**不显式给 policy 时**，Thrust 会**从迭代器类型推断**（`device_vector::iterator` → `device`）。

**进阶用法：绑定 CUDA stream**：

```cpp
cudaStream_t stream;
cudaStreamCreate(&stream);
thrust::sort(thrust::cuda::par.on(stream), d.begin(), d.end());
```

**这就是 Thrust 与手写 CUDA 混用的关键钩子**——把 Thrust 塞进你现有的 stream 流水线。

---

## 4. 第一个程序：CPU 版 vs GPU 版一字之差

### 4.1 CPU 版

```cpp
#include <vector>
#include <algorithm>
#include <numeric>

std::vector<int> v(1'000'000);
std::iota(v.begin(), v.end(), 0);
std::sort(v.begin(), v.end());
int sum = std::reduce(v.begin(), v.end(), 0);
```

### 4.2 GPU 版（Thrust）

```cpp
#include <thrust/device_vector.h>
#include <thrust/sequence.h>
#include <thrust/sort.h>
#include <thrust/reduce.h>

thrust::device_vector<int> v(1'000'000);
thrust::sequence(v.begin(), v.end());     // 0,1,2,...
thrust::sort(v.begin(), v.end());
int sum = thrust::reduce(v.begin(), v.end(), 0);
```

**差异**：
- `std::vector` → `thrust::device_vector`；
- `std::` → `thrust::`；
- `std::iota` → `thrust::sequence`（名字略不同）；
- **就这些**。整个语义、类型、心智模型一样。

### 4.3 小白也能懂：GPU 版每一行发生了什么？

#### 4.3.1 `thrust::device_vector<int> v(1'000'000);`

- 相当于 `int* p; cudaMalloc(&p, sizeof(int)*1000000)`；
- 但类型系统会记住"这块内存在 GPU 上"，防止你混用；
- 析构时自动 `cudaFree`（RAII）。

#### 4.3.2 `thrust::sequence(v.begin(), v.end());`

- Thrust 内部生成一个 CUDA kernel，让 100 万个 thread 分别写入 0,1,2,...；
- 你**看不到 kernel 代码**，Thrust 帮你写了；
- 但**是**在 GPU 上跑的。

#### 4.3.3 `thrust::sort(v.begin(), v.end());`

- 这一行内部调用的是 **CUB 的 device-wide radix sort**（对整数）或 merge sort（对 float）；
- 用了几十 KB 临时空间（Thrust 内部自动申请自动释放）；
- 3060 上排 1 亿个 int 约 80 ms——比 `std::sort` 快 60 倍。

#### 4.3.4 `thrust::reduce(v.begin(), v.end(), 0);`

- 内部 CUB device reduce，两阶段树形归约；
- 返回值 `sum` 是 host 侧 int——**Thrust 帮你做了 device→host 的隐式拷贝**；
- ⚠️ 这一步会**同步阻塞**（因为要拿回值），高频循环里注意。

#### 4.3.5 关键洞察

> **Thrust 让你写 CPU 心智的代码，Thrust 帮你写 CUDA kernel**。代价：**看不到 kernel、调不了 tile、控不了 stream（除非显式 policy）**——这就是它简单的原因，也是它的局限。

#### 4.3.6 6 个新手常见坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | 用了 `host_vector` 却期望 GPU 加速 | 慢得像 std | 换 `device_vector` |
| 2 | `device_vector<T>` 里放非 POD 类型 | 编译报错或崩溃 | T 必须是可 memcpy 的 |
| 3 | 循环里频繁 `device_vector<int> v(n)` | 每次都 cudaMalloc 巨慢 | 提前建好一次复用 |
| 4 | `thrust::reduce` 每次都同步 | 高频调用性能崩 | 用 `thrust::async::reduce`（异步）|
| 5 | 从 `device_vector` 逐个下标访问 | 每次触发 device→host 拷贝 | 一次性 `.copy_to_host()` 或用迭代器 |
| 6 | functor 里用了 `std::sin` | 编译错，host 函数不能在 device 用 | 换成 `sin` 或 `__device__` 标注 |

---

## 5. 三大常用套路：Sort / Reduce / Scan

### 5.1 Sort by Key（最常用）

**场景**：给一堆 `(key, value)`，按 key 排序，value 跟着走。深度学习里 top-k、图算法里边排序都用它。

```cpp
thrust::device_vector<int>   keys   = {5, 3, 1, 4, 2};
thrust::device_vector<float> values = {50, 30, 10, 40, 20};

thrust::sort_by_key(keys.begin(), keys.end(), values.begin());

// keys   = {1, 2, 3, 4, 5}
// values = {10, 20, 30, 40, 50}
```

### 5.2 Segmented Reduce（分段归约）

**场景**：按 key 分组求和（GroupBy Sum，SQL 里最常见的聚合）。

```cpp
thrust::device_vector<int>   keys   = {1,1,1,2,2,3,3,3,3};
thrust::device_vector<float> values = {1,2,3,4,5,6,7,8,9};

thrust::device_vector<int>   out_keys(3);
thrust::device_vector<float> out_sums(3);

thrust::reduce_by_key(keys.begin(), keys.end(),
                      values.begin(),
                      out_keys.begin(), out_sums.begin());

// out_keys = {1, 2, 3},  out_sums = {6, 9, 30}
```

**这一个 API 就等于 SQL 的 `SELECT SUM(v) FROM t GROUP BY k`，在 GPU 上跑**。

### 5.3 Inclusive/Exclusive Scan（前缀和）

**场景**：数组去空、稀疏索引压缩、并行分配 ID。**GPU 编程的隐形基石**。

```cpp
thrust::device_vector<int> v = {1, 2, 3, 4, 5};
thrust::device_vector<int> s(5);

thrust::inclusive_scan(v.begin(), v.end(), s.begin());
// s = {1, 3, 6, 10, 15}

thrust::exclusive_scan(v.begin(), v.end(), s.begin());
// s = {0, 1, 3, 6, 10}
```

**经典用法：流式压缩（stream compaction）**：

```cpp
// 从 arr 里挑出 > 0 的元素，紧凑排到 out
thrust::copy_if(arr.begin(), arr.end(), out.begin(),
                [] __device__ (int x) { return x > 0; });
```

（背后就是 scan）

---

## 6. Fancy Iterator：Thrust 的杀手锏

**这是 Thrust 相对手写 CUDA 最优雅的地方**——**用"虚拟迭代器"避免中间数组**，节省显存、节省访存带宽。

### 6.1 `counting_iterator`：无中生有的 0..N

```cpp
thrust::counting_iterator<int> begin(0);
thrust::counting_iterator<int> end(1'000'000);

// 相当于一个虚拟的 [0, 1, 2, ..., 999999]，但不占内存
int sum = thrust::reduce(begin, end, 0);   // = 499999500000
```

### 6.2 `zip_iterator`：多个数组一次遍历

```cpp
auto z = thrust::make_zip_iterator(
    thrust::make_tuple(a.begin(), b.begin(), c.begin()));

thrust::for_each(z, z + n, [] __device__ (auto t) {
    thrust::get<2>(t) = thrust::get<0>(t) + thrust::get<1>(t);
});
```

**优势**：**一次 kernel launch 处理三条流**，比先 `transform(a,b,c)` 再 `transform(c,x,y)` 快，减少访存。

### 6.3 `transform_iterator`：读的时候顺手变换

```cpp
auto squared = thrust::make_transform_iterator(
    v.begin(), [] __device__ (int x) { return x * x; });

int sum_sq = thrust::reduce(squared, squared + n, 0);
// 完全不生成中间的 "平方数组"
```

**这就是 GPU 版的"惰性计算"**——省一次显存往返。

### 6.4 `permutation_iterator`：按索引重排（不真的排）

```cpp
// values[indices[i]] 的视图，不真的拷贝
auto pit = thrust::make_permutation_iterator(values.begin(), indices.begin());
```

### 6.5 组合能力（最强）

```cpp
// 对 a[i]*b[i] 求和，中间不生成任何数组
auto zip = thrust::make_zip_iterator(thrust::make_tuple(a.begin(), b.begin()));
auto tit = thrust::make_transform_iterator(zip,
    [] __device__ (auto t) { return thrust::get<0>(t) * thrust::get<1>(t); });

float dot = thrust::reduce(tit, tit + n, 0.0f);
```

**这就是 GPU 版的"one-liner 点积"，比手写 kernel 还短**。

---

## 7. 与手写 CUDA kernel 混用

### 7.1 从 device_vector 拿裸指针

```cpp
thrust::device_vector<float> v(n);
float* raw_ptr = thrust::raw_pointer_cast(v.data());

my_kernel<<<blocks, threads>>>(raw_ptr, n);
```

反过来包装裸指针：

```cpp
float* d_ptr;    // 你自己 cudaMalloc 出来的
thrust::device_ptr<float> dev_ptr(d_ptr);
thrust::sort(dev_ptr, dev_ptr + n);
```

### 7.2 stream 混用

```cpp
cudaStream_t stream;
cudaStreamCreate(&stream);

my_kernel<<<b, t, 0, stream>>>(...);
thrust::sort(thrust::cuda::par.on(stream), d.begin(), d.end());
another_kernel<<<b, t, 0, stream>>>(...);
```

**Thrust 完美融入 CUDA stream 流水线**。

### 7.3 与 cuBLAS / cuDNN 一起用

```cpp
cublasHandle_t h;
cublasCreate(&h);
thrust::device_vector<float> x(n), y(n);
float alpha = 2.0f;

cublasSaxpy(h, n, &alpha,
    thrust::raw_pointer_cast(x.data()), 1,
    thrust::raw_pointer_cast(y.data()), 1);
```

**结论**：Thrust 的 `device_vector` 是 GPU 内存管理的通用底座——所有 CUDA 库都能直接用它。

---

## 8. 性能分析与调优

### 8.1 计时的正确姿势

```cpp
cudaDeviceSynchronize();
auto t0 = std::chrono::high_resolution_clock::now();

thrust::sort(d.begin(), d.end());
cudaDeviceSynchronize();          // ⚠️ 关键

auto t1 = std::chrono::high_resolution_clock::now();
double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
```

**警告**：`thrust::reduce` 返回值时会**隐式同步**，但 `thrust::sort` 是异步的，测速一定要显式 sync。

### 8.2 三条铁律

1. **减少 device_vector 分配次数**——预先建好复用；
2. **少同步**——尽量用 iterator 组合避免中间 host↔device 往返；
3. **fancy iterator 是免费午餐**——能用就用。

### 8.3 自定义内存池（进阶）

高频分配释放场景（比如每帧都 `device_vector<int> tmp(n)`）会拖慢：

```cpp
#include <thrust/system/cuda/experimental/pinned_allocator.h>
#include <thrust/system/cuda/vector.h>

// 或者用 CUB 的 CachingDeviceAllocator 做自定义 allocator
```

**建议**：先跑 profiler，看是不是 malloc/free 占大头，再考虑。

### 8.4 与 Nsight Systems 配合

```bash
nsys profile --stats=true ./hello_thrust
```

Thrust 的 kernel 名字带 `thrust::cuda_cub::...`，一眼能认出来。

---

## 9. Thrust vs CUB：什么时候该"下沉"

Thrust 好用但抽象层高，有时你需要"下沉"到 CUB 拿更细粒度控制。**判断标准**：

| 场景 | 用 Thrust | **下沉到 CUB** |
|:--|:--|:--|
| 想快速原型 | ✅ | ❌ |
| 数据结构就是数组 | ✅ | ⚠️ |
| 需要"我自己的 kernel 里"复用 block-level 归约 | ❌ | ✅ |
| 想精确控制临时空间（自定义分配器）| ⚠️ | ✅ |
| 需要 warp-level 原语（scan/reduce/shuffle）| ❌ | ✅ |
| 想避免 Thrust 的模板膨胀 | ⚠️ | ✅ |
| 追求极致性能（打赢 Thrust 20~30%）| ❌ | ✅ |

**结论**：**先写 Thrust 版本跑通，测出瓶颈再考虑 CUB**。90% 的场景 Thrust 就够。

---

## 10. 学习路线图（1~2 周）

### 🟢 阶段 1（Day 1~2）：入门

- ✅ 跑通 `hello_thrust.cu`；
- ✅ 会用 `host_vector`、`device_vector`、`sort / reduce / copy`；
- ✅ 理解 Execution Policy（`thrust::device` / `thrust::cuda::par.on(stream)`）。

### 🟡 阶段 2（Day 3~5）：常用算法 + 自定义 functor

- ✅ 写 `transform` + lambda（记得开 `--extended-lambda`）；
- ✅ 用 `sort_by_key / reduce_by_key`；
- ✅ 用 `copy_if / partition`（stream compaction）；
- ✅ 掌握 `inclusive_scan / exclusive_scan`。

### 🟠 阶段 3（Day 6~10）：Fancy Iterator + 与 CUDA 混用

- ✅ 会用 `counting/zip/transform/permutation_iterator`；
- ✅ 会 `raw_pointer_cast` 与手写 kernel 混用；
- ✅ 绑定 CUDA stream；
- ✅ 用 fancy iterator 消掉中间数组。

### 🔴 阶段 4（Day 11~14）：进阶

- ✅ 自定义 allocator / 内存池；
- ✅ 读 Thrust 内部（`thrust/system/cuda/detail/`）看它如何调 CUB；
- ✅ 理解什么时候该下沉到 CUB；
- ✅ 完成一个"CSV → GPU 排序 → 聚合"完整 pipeline。

---

## 11. 精选资源与踩坑清单

### 11.1 必读官方资源

| 资源 | 用途 | 链接 |
|:--|:--|:--|
| Thrust GitHub | 源码 + examples（现属 CCCL）| <https://github.com/NVIDIA/cccl/tree/main/thrust> |
| Thrust 官方文档 | API reference | <https://nvidia.github.io/cccl/thrust/> |
| Thrust Tutorial | 官方入门 | <https://github.com/NVIDIA/cccl/blob/main/thrust/README.md> |
| CCCL 主页 | Thrust + CUB + libcu++ 合并 | <https://nvidia.github.io/cccl/> |
| Thrust examples | 40+ 官方例子 | <https://github.com/NVIDIA/cccl/tree/main/thrust/examples> |

### 11.2 高质量博客

- **NVIDIA Developer Blog：Thrust 系列**：搜 "Thrust site:developer.nvidia.com"；
- **"Expressive Algorithmic Programming with Thrust"**（Bell & Hoberock）：Thrust 设计者原始论文；
- **RAPIDS cuDF**：<https://github.com/rapidsai/cudf>——Thrust 大型生产项目的最好参考。

### 11.3 完整踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| lambda 报错 | 未开 extended lambda | 加 `--extended-lambda` |
| functor 里调用 `std::` 函数报错 | host-only | 换 `::sin` / `__device__` 版本 |
| `device_vector` 每帧新建慢 | cudaMalloc 昂贵 | 复用 + `.resize` |
| `thrust::reduce` 阻塞主线程 | 隐式同步 | 用 `thrust::async::reduce` |
| MSVC 死循环 | 模板深度 | `/Zc:__cplusplus /permissive-` |
| 大整数排序慢 | 用了 stable_sort | 换 `thrust::sort`（不稳定但快）|
| 结果不确定 | 用了 non-associative reduce | float 求和顺序不同结果略异，正常 |
| device_vector<struct> 崩 | struct 非 POD | 用 `__align__` + trivially copyable |
| `thrust::copy` 慢 | 走了 pageable memory | 用 `pinned_allocator` 的 host_vector |
| 编译时间爆炸 | 一个 .cu 塞了 10 个 Thrust 算法 | 拆多个 .cu，减少模板实例化 |

### 11.4 一句话总结

> **Thrust = "STL 的 GPU 版本"**。它让你**用 C++ 标准库的心智**，把并行算法搬到 GPU 上跑，代码几乎不变，速度快 10~100 倍。缺点是抽象层高、看不到 kernel 内部——**这既是它的优点（省心），也是它的天花板**。
>
> **学它的收益**：**投入产出比最高的 CUDA 加速方案**。已有 C++ 代码想 GPU 化？先套 Thrust 跑通，再看瓶颈在哪儿，再决定是否下沉到 CUB 或手写 kernel。

---

**祝你写出优雅的 GPU C++ 代码。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
