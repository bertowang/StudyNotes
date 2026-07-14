# cuCollections 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：C++/CUDA 程序员，熟悉 STL 的 `std::unordered_map / std::unordered_set`，正在处理**大规模键值查询、去重、连接（join）、图数据结构**类问题，苦于"CPU 侧哈希表在 GPU 上完全没法用"，想在 GPU 上拥有**真正并发安全、能被数百万 thread 同时插入/查找**的哈希容器。
> **目标**：1~2 周内，从"用 `cuco::static_map` 存 1 亿 KV 对"到"能在自己的 kernel 里就地 `insert/find`、能做 GPU 版 hash join、能针对 3060 调 load factor"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1** + cuCollections（`cuco`）≥ 0.0.1（header-only）+ CCCL（Thrust/CUB/libcu++）+ C++17。

---

## 目录

- [0. 写在最前：为什么要学 cuCollections？](#0-写在最前为什么要学-cucollections)
- [1. cuCollections 是什么：一句话讲清 vs `std::unordered_map`](#1-cucollections-是什么一句话讲清-vs-stdunordered_map)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. 核心概念：Sentinel / Load Factor / Bulk API / Device API](#3-核心概念sentinel--load-factor--bulk-api--device-api)
- [4. 第一个程序：`static_map` 存 1 亿 KV 对](#4-第一个程序static_map-存-1-亿-kv-对)
- [5. 在你自己 kernel 里就地 `insert/find`](#5-在你自己-kernel-里就地-insertfind)
- [6. 常用容器：`static_map` / `static_set` / `dynamic_map` / `distinct_count_estimator`](#6-常用容器static_map--static_set--dynamic_map--distinct_count_estimator)
- [7. 实战：GPU 版 hash join](#7-实战gpu-版-hash-join)
- [8. 性能分析与调优](#8-性能分析与调优)
- [9. cuCollections vs Thrust/CUB 排序去重](#9-cucollections-vs-thrustcub-排序去重)
- [10. 学习路线图（1~2 周）](#10-学习路线图12-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 cuCollections？

你可能会问：**用 `thrust::sort + thrust::unique` 或 `thrust::reduce_by_key` 不就能做去重、聚合、join 了吗？为什么还要哈希？** 答案是三点：

1. **哈希是 O(N)，排序是 O(N log N)**——1 亿 KV 上 join，哈希方案能快 3~10 倍；
2. **哈希天然支持"点查询"**——给定 100 万个 key 找它们的 value，排序方案要做二分或另一次排序；
3. **cuCollections 是 RAPIDS / cuDF 的底座**——SQL 引擎 join、去重、group by 内部用的就是它。

### 0.1 一句话对比

| 场景 | 用 STL | 用 Thrust sort+unique | **用 cuCollections** |
|:--|:--|:--|:--|
| 1 亿 key 去重 | `std::unordered_set` 卡爆 CPU | ~120 ms（GPU）| **~40 ms（GPU）** |
| 1 亿 key 点查询 100 万 key | 极慢 | 需两次排序 | **~10 ms（GPU）** |
| 千万 hash join | Pandas 分钟级 | 秒级 | **~50 ms** |
| 并发线程安全 | ❌ | 排序无所谓 | **✅ 无锁 CAS** |

### 0.2 cuCollections 现在有多重要？

- **NVIDIA 官方开源库**，Apache 2.0；
- **RAPIDS cuDF 的核心组件**：SQL join / group-by / distinct 全靠它；
- **cuGraph 的底座**：图算法里 vertex/edge 去重、邻接表构建；
- **CCCL 生态成员**：与 Thrust / CUB / libcu++ 无缝互操作；
- **无锁设计**：数百万 thread 同时插入不会死锁不会崩。

**一句话**：**如果你在做 GPU 上的大规模键值查询、SQL 数据处理、图数据结构，cuCollections 是绕不开的一站**。手写 GPU 哈希表极容易死锁或性能爆炸，用官方轮子就对了。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **CC1 入门** | 会用 `cuco::static_map` 构造、`insert / find` bulk API |
| **CC2 熟练** | 会在自己 kernel 里用 device view 就地 insert/find |
| **CC3 高阶** | 会调 load factor、hash function、probe scheme，做 hash join |
| **CC4 专家** | 会用 `distinct_count_estimator (HyperLogLog)`、cooperative groups 加速、读源码 |

**建议**：**2~3 天到 CC1**，**1 周到 CC2/CC3**（覆盖 90% 生产场景）。

---

## 1. cuCollections 是什么：一句话讲清 vs `std::unordered_map`

### 1.1 cuCollections 的定义

> **cuCollections（cuco）是 NVIDIA 官方开源的 GPU 并发数据结构库**（header-only），提供 **GPU 上无锁的哈希表 / 哈希集合 / bloom filter / HyperLogLog** 等常用容器。它是 **`std::unordered_map` 的 GPU 版**，但为并发和 GPU 内存层次做了完全重设计。

关键三点：

1. **无锁**：所有操作用 CAS（`atomicCAS`）实现，无 mutex、无 barrier；
2. **开放寻址**：不是拉链法（GPU 上链表极慢），而是线性/双哈希探测；
3. **Bulk + Device 两套 API**：Host 侧一次调 1 亿 key 的 bulk 版；kernel 内一个一个 key 的 device view 版。

### 1.2 cuCollections vs `std::unordered_map` vs Thrust sort

| 维度 | `std::unordered_map` | Thrust sort+unique | **cuCollections** |
|:--|:--|:--|:--|
| 位置 | CPU 内存 | GPU 显存 | **GPU 显存** |
| 复杂度 | O(1) 均摊 | O(N log N) | **O(1) 均摊** |
| 并发安全 | ❌ | 排序方案不需要 | **✅ 无锁** |
| 支持点查询 | ✅ | ❌ 需再排序 | **✅** |
| 支持 kernel 内插入 | ❌ | ❌ | **✅（Device view）** |
| 内存开销 | 高（链表）| 无（数组）| **1 / load_factor**（一般 1.5x）|
| 目标读者 | CPU 程序员 | 数据处理 | **GPU 数据/图工程师** |

**记忆口诀**：
- **数据不动、只想去重/reduce** → Thrust sort+unique；
- **要频繁点查询 / 高并发插入 / GPU join** → cuCollections。

### 1.3 一张图看清 cuCollections 在栈里的位置

```
┌──────────────────────────────────────────────────────────┐
│  RAPIDS cuDF（SQL join / group-by / distinct）            │
│  cuGraph（BFS / PageRank / 邻接表构建）                    │
├──────────────────────────────────────────────────────────┤
│  cuCollections                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │ static_map / static_set / dynamic_map              │   │
│  │ bloom_filter / distinct_count_estimator (HLL)      │   │
│  │ hash_functions (MurmurHash / xxHash / FNV)         │   │
│  │ probing schemes (linear / double-hashing)          │   │
│  └────────────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────────┤
│  CCCL：Thrust + CUB + libcu++ (atomic, CAS)              │
├──────────────────────────────────────────────────────────┤
│  CUDA Runtime + PTX (atomicCAS.acq_rel)                  │
├──────────────────────────────────────────────────────────┤
│  GPU 硬件（3060 / Ampere / SM86）                          │
└──────────────────────────────────────────────────────────┘
```

**核心洞察**：cuCollections 是**"GPU 上的 std::unordered_map 家族"**，用无锁 CAS + 开放寻址实现，是 RAPIDS 数据处理的骨架。

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 获取

cuCollections 是 **header-only**，无需编译成库：

```bash
git clone --depth 1 https://github.com/NVIDIA/cuCollections.git
```

或用 CMake FetchContent：

```cmake
include(FetchContent)
FetchContent_Declare(cuco GIT_REPOSITORY https://github.com/NVIDIA/cuCollections.git)
FetchContent_MakeAvailable(cuco)
target_link_libraries(my_app PRIVATE cuco::cuco)
```

**依赖**：CUDA Toolkit 12.x + CCCL（Thrust/CUB/libcu++，随 CUDA 自带）+ C++17。

### 2.2 一步验证：hello_cuco.cu

```cpp
// hello_cuco.cu
#include <cuco/static_map.cuh>
#include <thrust/device_vector.h>
#include <thrust/sequence.h>
#include <iostream>

int main() {
    using Key = int;
    using Val = int;

    // 1. 构造：容量 2M（够存 1M 元素，load factor 0.5）
    Key empty_key = -1;   // sentinel（用于标记"空槽"）
    Val empty_val = -1;
    cuco::static_map<Key, Val> map{2'000'000,
                                    cuco::empty_key{empty_key},
                                    cuco::empty_value{empty_val}};

    // 2. 准备 1M KV 对
    int N = 1'000'000;
    thrust::device_vector<Key> keys(N);
    thrust::device_vector<Val> vals(N);
    thrust::sequence(keys.begin(), keys.end(), 0);   // 0..N-1
    thrust::sequence(vals.begin(), vals.end(), 100); // 100..N+99

    // 3. Bulk insert：一次全部插入
    auto zip = thrust::make_zip_iterator(
                   thrust::make_tuple(keys.begin(), vals.begin()));
    map.insert(zip, zip + N);

    // 4. Bulk find：查 3 个 key
    thrust::device_vector<Key> qk = {42, 100, 999999};
    thrust::device_vector<Val> qv(3);
    map.find(qk.begin(), qk.end(), qv.begin());

    for (int i = 0; i < 3; ++i)
        std::cout << "key=" << qk[i] << " val=" << qv[i] << "\n";

    std::cout << "size = " << map.size() << "\n";
}
```

编译：

```bash
nvcc -O3 -std=c++17 -arch=sm_86 -I /path/to/cuCollections/include \
     hello_cuco.cu -o hello_cuco
./hello_cuco
```

期望输出：

```
key=42 val=142
key=100 val=200
key=999999 val=1000099
size = 1000000
```

### 2.3 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 编译报模板深度不足 | cuco 模板深 | `-ftemplate-depth=1024` |
| 结果全是 sentinel | key 里有等于 sentinel 的值 | 换 sentinel，避开真实值域 |
| 容量不够崩溃 | load factor 太高 | 容量 = 元素数 × 1.5 起 |
| 编译很慢 | header-only 模板 | 减少一个 TU 里的 map 类型数 |
| SM86 上 CAS 慢 | 无 acq_rel 版 | 用新 CUDA + libcu++ |

---

## 3. 核心概念：Sentinel / Load Factor / Bulk API / Device API

### 3.1 Sentinel（哨兵值）

**因为无锁 + 开放寻址，需要用特殊值标记"空槽"**。你必须选一个**永远不会出现在真实数据里**的值作为 sentinel：

```cpp
cuco::empty_key{-1}   // key 值永远不会是 -1
cuco::empty_value{-1}
```

**常见 sentinel 选法**：
- key 是正整数？→ `-1` 或 `INT_MIN`；
- key 是 uint64？→ `UINT64_MAX`；
- key 是浮点？→ NaN（但要小心 NaN 比较）；
- key 是字符串？→ 空指针或长度为 0；

**⚠️ 大坑**：如果真实数据里出现 sentinel，容器行为**未定义**（可能永远查不到那个 key）。

### 3.2 Load Factor（负载因子）

**容量 vs 实际存储**的比例：

```
load_factor = size / capacity
```

- Load factor 越高，内存越省，但**探测链越长，插入/查询越慢**；
- cuCollections 默认建议 **load factor ≤ 0.7**（即 `capacity ≥ 1.5 * N`）；
- 极致速度：load factor 0.3~0.5；
- 极致省内存：0.7~0.85（性能会显著下降）。

**建议**：容量取 **元素数 × 2**，简单粗暴。

### 3.3 Bulk API（Host 侧一次全量）

```cpp
map.insert(keys_begin, keys_end);
map.find(query_begin, query_end, output_begin);
map.contains(query_begin, query_end, bool_out);
map.size();
map.erase(keys_begin, keys_end);   // 部分容器支持
```

**特点**：
- host 侧一次调用完成整批操作；
- 内部启动 CUDA kernel，thread 数 ≈ 元素数；
- 对典型 1M~100M 元素规模最快。

### 3.4 Device API（Kernel 内一个一个）

```cpp
auto view = map.get_device_mutable_view();

__global__ void my_kernel(decltype(view) view, ...) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    view.insert(cuco::pair{key, value});
    // 或
    auto found = view.find(key);
    if (found != view.end()) { auto v = found->second; }
}
```

**特点**：
- 在**你自己**的 kernel 里就地用；
- 与你的其他计算融合，避免额外一次 kernel launch；
- 用 `cooperative_groups` 或 `cuco::experimental::CG` 可以让多个 thread 协作探测一个 key，加速哈希冲突场景。

---

## 4. 第一个程序：`static_map` 存 1 亿 KV 对

见 2.2 节完整代码。这一节做**小白逐行拆解**。

### 4.1 小白也能懂：hello_cuco 每一行发生了什么？

#### 4.1.1 `cuco::static_map<Key, Val> map{2'000'000, ...};`

- 分配了 2M × (sizeof(K)+sizeof(V)) 的 GPU 内存作为哈希表槽位；
- 所有槽位初始化为 `(sentinel_key, sentinel_val)`；
- 内部选定 hash function（默认 MurmurHash3）+ probing scheme（默认双哈希）；
- **构造后不能改容量**——这就是 `static_map` 名字的由来。

#### 4.1.2 `map.insert(zip, zip + N);`

- 内部启动一个 CUDA kernel，`N` 个 thread 并发；
- 每个 thread 干这样一件事：
  ```
  slot = hash(key) % capacity
  while (真的循环) {
      old = atomicCAS(&table[slot].key, sentinel, key);
      if (old == sentinel) { table[slot].val = val; break; }        // 抢到空槽
      if (old == key)      { break; }                                // 已有相同 key（去重语义）
      slot = probe(slot);                                            // 冲突，探测下一个
  }
  ```
- **无锁**：靠 `atomicCAS` 保证并发安全；
- **速度**：3060 上 1M 插入 ~10 ms；1 亿 ~1 秒。

#### 4.1.3 `map.find(qk.begin(), qk.end(), qv.begin());`

- 类似，`N` 个 thread 并发查询；
- 每 thread：
  ```
  slot = hash(key) % capacity
  while (true) {
      k = table[slot].key
      if (k == key)      { return table[slot].val; }
      if (k == sentinel) { return sentinel_val; }    // 到空槽还没找到 → 不存在
      slot = probe(slot);
  }
  ```

#### 4.1.4 关键洞察

> **你写的是 STL 心智，cuCollections 帮你写并发 CAS 的 GPU kernel**。代价：**必须显式给 sentinel，必须提前定容量**——这就是它的两个使用约束。

#### 4.1.5 6 个新手常见坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | sentinel 与真实数据冲突 | 少数 key 查不到 | 换 sentinel |
| 2 | 容量 = 元素数 | load factor=1，卡死或极慢 | 容量 ≥ 2×元素数 |
| 3 | insert 后立刻 CPU 读，忘同步 | 拿到旧值 | `cudaDeviceSynchronize()` |
| 4 | 相同 key 插两次 val 不同 | 语义"先到者赢"，第二次静默丢 | 想要覆盖用 `insert_or_assign`（部分版本）|
| 5 | Device view 里 `insert` 后 `find` 未见结果 | 需要 `__threadfence()` 或 memory_order | 用 `cuda::memory_order_release/acquire` 变体 |
| 6 | 结果里出现 sentinel_val | 说明 key 不存在 | 用 sentinel_val 做"未找到"判断 |

---

## 5. 在你自己 kernel 里就地 `insert/find`

**这是 cuCollections 相对 Thrust 的核心价值**——**融合到你的计算 kernel 里**，避免额外一次 launch。

### 5.1 获取 Device View

```cpp
auto mv = map.get_device_mutable_view();   // 可读可写
auto rv = map.get_device_view();           // 只读（更省寄存器）
```

### 5.2 一个融合示例：一次 kernel 内完成"计数 + 查表 + 累加"

```cpp
__global__ void fused_kernel(int* data, int n,
                             decltype(map.get_device_mutable_view()) view,
                             int* out_sum) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= n) return;

    int key = data[tid];

    // 1. 查表
    auto it = view.find(key);
    int val = (it != view.end()) ? it->second : 0;

    // 2. 累加到全局输出
    atomicAdd(out_sum, val);

    // 3. 顺手把 key -> val*2 更新到 map（如果不存在则插）
    view.insert_or_assign(cuco::pair{key, val * 2});
}
```

**优势**：查表 + 累加 + 更新一次搞定，**只需 1 次 kernel launch**（用 Thrust 的话至少 3 次）。

### 5.3 Cooperative Group 加速（进阶）

**冲突严重时**，多个 thread 协作探测一个 key 比一个 thread 单打独斗快：

```cpp
namespace cg = cooperative_groups;
auto tile = cg::tiled_partition<8>(cg::this_thread_block());   // 8 个 thread 一组

auto found = view.find(tile, key);   // 8 个 thread 协作查一个 key
```

**性能**：负载因子 0.7+ 时能提速 20~40%；负载因子低时反而慢一点（协作开销）。

---

## 6. 常用容器：`static_map` / `static_set` / `dynamic_map` / `distinct_count_estimator`

### 6.1 `static_map<K,V>`

**核心容器**，固定容量、KV 对。最常用。

### 6.2 `static_set<K>`

**只有 key 没有 value**，用于去重、集合运算。内存开销减半：

```cpp
cuco::static_set<int> s{2'000'000, cuco::empty_key{-1}};
s.insert(keys.begin(), keys.end());
size_t distinct_count = s.size();
```

### 6.3 `dynamic_map<K,V>`

**容量可增长**——当 load factor 达到阈值时自动 rehash：

```cpp
cuco::dynamic_map<int, int> m{1'000'000,
                              cuco::empty_key{-1},
                              cuco::empty_value{-1}};
m.insert(kv.begin(), kv.end());   // 会自动扩容
```

**代价**：rehash 时性能抖动，且比 static_map 慢 10~20%。**未知规模时用它，已知规模用 static**。

### 6.4 `distinct_count_estimator`（HyperLogLog）

**估算基数**，误差 ~1% 但内存 O(1)：

```cpp
cuco::distinct_count_estimator<int> hll{cuco::standard_deviation{0.01}};
hll.add_async(keys.begin(), keys.end(), stream);
auto est = hll.estimate(stream);   // 估算 distinct 数量
```

**用途**：SQL `COUNT(DISTINCT ...)`、去重规模估计、cardinality-based query planning。

### 6.5 `bloom_filter`（部分版本已有）

**成员查询**，误报率可控，无假阴：

```cpp
cuco::bloom_filter<int> bf{num_expected, 0.01};   // 1% 误报率
bf.add(keys.begin(), keys.end());
bf.contains(query.begin(), query.end(), result.begin());
```

**用途**：join 前预过滤、缓存查询、图遍历去重。

---

## 7. 实战：GPU 版 hash join

### 7.1 场景

两张表 `L(key, val_L)` 和 `R(key, val_R)`，做 inner join：`SELECT L.key, val_L, val_R WHERE L.key = R.key`。

### 7.2 GPU Hash Join 算法

```
Build phase：把小表 L 建成 static_map<key, val_L>
Probe phase：对大表 R 的每个 key，在 map 里 find，找到就输出 (key, val_L, val_R)
```

### 7.3 代码

```cpp
// Build
cuco::static_map<int, int> map{L_size * 2,
                                cuco::empty_key{-1},
                                cuco::empty_value{-1}};
auto zL = thrust::make_zip_iterator(
              thrust::make_tuple(L_keys.begin(), L_vals.begin()));
map.insert(zL, zL + L_size);

// Probe
thrust::device_vector<int> matched_L(R_size);
map.find(R_keys.begin(), R_keys.end(), matched_L.begin());

// 输出：过滤掉未匹配（matched_L == sentinel）
auto is_matched = [] __device__ (int v) { return v != -1; };
auto num_hits = thrust::count_if(matched_L.begin(), matched_L.end(), is_matched);
// ... 用 thrust::copy_if / stream compaction 输出结果 ...
```

### 7.4 性能

3060 上 1M × 10M 的 int join：
- CPU pandas merge：~5 秒；
- Thrust sort-merge join：~500 ms；
- **cuCollections hash join：~50 ms**。

**这就是 cuDF 内部 `merge()` 快的核心原因**。

---

## 8. 性能分析与调优

### 8.1 三条铁律

1. **Load factor 决定一切**：0.5 是甜蜜点；超过 0.7 性能悬崖跌落；
2. **hash function 选对**：整数用 MurmurHash3 就够好；字符串用 xxHash；
3. **cooperative group 用在冲突严重时**：低 load factor 时反而慢。

### 8.2 与 Nsight Compute 联用

```bash
ncu --set full ./hello_cuco
```

看关键指标：
- **atomic CAS 吞吐**：应该 > 100 GB/s（Ampere 峰值）；
- **DRAM 利用率**：hash 查询是访存 bound，应该 > 60%；
- **Warp Execution Efficiency**：< 50% 说明冲突严重，考虑降 load factor。

### 8.3 调优 checklist

- ✅ 容量 = 元素数 × 2；
- ✅ 用整数 key 而非字符串（能哈希前预转换）；
- ✅ static_map 优先于 dynamic_map；
- ✅ 高冲突时用 cooperative group probing；
- ✅ hash 函数与 key 分布匹配（顺序 key 用双哈希，随机 key 用线性也行）。

---

## 9. cuCollections vs Thrust/CUB 排序去重

| 场景 | Thrust sort+unique | **cuCollections** |
|:--|:--|:--|
| 单次去重（无后续查询）| ✅ 排序 O(N logN) 也快 | ⚠️ 内存多 |
| 频繁点查询 | ❌ | ✅ O(1) |
| Join | ⚠️ sort-merge O(N logN) | ✅ hash O(N) |
| Group-by aggregation | ✅ `reduce_by_key` | ✅ hash 版本更快（cuDF 用后者）|
| 内存紧张 | ✅ 原地 | ❌ 需 1.5~2x |
| 需要顺序保序 | ✅ | ❌ 哈希无序 |

**决策**：
- 只求 distinct 数量 → **HLL estimator**（内存最省）；
- 只做单次去重后不再查 → **Thrust sort+unique**（简单）；
- 频繁查询 / join / dynamic 更新 → **cuCollections**。

---

## 10. 学习路线图（1~2 周）

### 🟢 阶段 1（Day 1~2）：入门

- ✅ 装好 cuCollections，跑通 `hello_cuco`；
- ✅ 会用 `static_map` bulk insert/find；
- ✅ 理解 sentinel 和 load factor。

### 🟡 阶段 2（Day 3~7）：容器熟练

- ✅ 用 `static_set` 做 1 亿 key 去重；
- ✅ 用 `dynamic_map` 处理未知规模；
- ✅ 用 `distinct_count_estimator` 做基数估计；
- ✅ 装 device view，在 kernel 里就地 insert/find。

### 🟠 阶段 3（Day 8~14）：实战

- ✅ 写一个 GPU hash join（Build+Probe）；
- ✅ 用 cooperative group 加速高冲突场景；
- ✅ 用 Nsight Compute 调优 load factor；
- ✅ 读 cuDF 内部 join 实现（`cpp/src/join/`）。

---

## 11. 精选资源与踩坑清单

### 11.1 必读官方资源

| 资源 | 用途 | 链接 |
|:--|:--|:--|
| cuCollections GitHub | 源码 + examples | <https://github.com/NVIDIA/cuCollections> |
| 官方文档 | API 详解 | <https://nvidia.github.io/cuCollections/> |
| cuDF | 生产级用户 | <https://github.com/rapidsai/cudf> |
| cuGraph | 图应用参考 | <https://github.com/rapidsai/cugraph> |
| GTC 讲座 | 官方设计动机 | 搜 "GTC cuCollections" |

### 11.2 高质量博客

- **NVIDIA Blog：cuCollections 系列**：<https://developer.nvidia.com/blog/tag/cucollections/>；
- **《Building a High-Performance GPU Hash Table》**（Junchao Gu 等）：cuco 的设计论文；
- **RAPIDS cuDF 源码**：`cpp/src/hash/` 与 `cpp/src/join/` —— 最好的实战代码。

### 11.3 完整踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| Sentinel 与真实数据冲突 | key 值域覆盖了 sentinel | 换 sentinel |
| 容量爆炸崩溃 | load factor > 1 | 容量 ≥ 2×N |
| CPU 侧读结果不对 | 忘同步 | `cudaDeviceSynchronize()` |
| Device view 更新后未见 | memory_order 问题 | 用 `cuda::memory_order_release/acquire` |
| bulk insert 慢 | key 分布集中导致冲突 | 换 hash 函数或先 shuffle |
| dynamic_map rehash 抖动 | 初始 capacity 太小 | 初始给一个合理估计 |
| 模板深度不足 | cuco 深模板 | `-ftemplate-depth=1024` |
| Windows 编译慢 | 模板膨胀 | 减少一个 TU 内实例化种类 |
| kernel 内 insert 后同 kernel find 拿不到 | 需要 fence | `__threadfence()` 或用 release/acquire |
| HLL 估算误差大 | stddev 设太松 | 调 `standard_deviation{0.005}` |
| join 结果丢部分行 | sentinel 与真实 key 撞了 | 换 sentinel |

### 11.4 一句话总结

> **cuCollections = "GPU 上真正能用的 std::unordered_map 家族"**。它把哈希表 / 集合 / bloom filter / HLL 用无锁 CAS + 开放寻址实现到 GPU 上，让**大规模键值查询、去重、join、图数据结构**变得像 STL 一样简单，比 Thrust 排序方案快 3~10 倍。
>
> **学它的收益**：**从"只会用 sort+unique 硬凑 join 的 GPU 数据工程师" → "会用官方无锁哈希容器做真 SQL 引擎级操作的数据/图工程师"**。想搞 cuDF / cuGraph、写数据库 GPU 后端、做大规模图算法，cuCollections 是必修课。

---

**祝你写出百万级 QPS 的 GPU 查询代码。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
