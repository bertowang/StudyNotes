# cuRAND 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：搞**蒙特卡洛仿真、量化金融、粒子系统、机器学习数据增强、随机初始化、密码学模拟**的 C++/CUDA 程序员，需要**在 GPU 上高性能生成大批量高质量随机数**（uniform / normal / poisson / lognormal 等）。
> **目标**：3~5 天内，从"用 cuRAND host API 生成 1 亿正态分布随机数"到"能在自己 kernel 里就地 `curand_normal`、能选合适的生成器（XORWOW/MRG32/Philox/Sobol）、能保证可重现性"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1**（cuRAND 随 CUDA Toolkit 自带）+ C++17。

---

## 目录

- [0. 写在最前：为什么要学 cuRAND？](#0-写在最前为什么要学-curand)
- [1. cuRAND 是什么：一句话讲清 vs std::mt19937 / vs numpy.random](#1-curand-是什么一句话讲清-vs-stdmt19937--vs-numpyrandom)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. cuRAND 的心智模型：Host API vs Device API + 5 种生成器](#3-curand-的心智模型host-api-vs-device-api--5-种生成器)
- [4. 第一个程序：Host API 生成 1 亿正态分布](#4-第一个程序host-api-生成-1-亿正态分布)
- [5. Device API：在自己 kernel 里就地生成](#5-device-api在自己-kernel-里就地生成)
- [6. 生成器对比：XORWOW / MRG32k3a / MTGP32 / Philox / Sobol](#6-生成器对比xorwow--mrg32k3a--mtgp32--philox--sobol)
- [7. 分布：Uniform / Normal / LogNormal / Poisson / Discrete](#7-分布uniform--normal--lognormal--poisson--discrete)
- [8. 性能分析与调优](#8-性能分析与调优)
- [9. cuRAND vs 手写 LCG / vs CPU 随机数](#9-curand-vs-手写-lcg--vs-cpu-随机数)
- [10. 学习路线图（5 天）](#10-学习路线图5-天)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 cuRAND？

你可能会问：**我在 CUDA kernel 里手写一个 LCG（`x = a*x + c`）不就能生成随机数了吗？** 答案是：**手写 LCG 快是快，但周期短、相关性差、并行时质量崩塌**——蒙特卡洛结果会有系统性偏差。

**cuRAND = NVIDIA 官方高质量 GPU 随机数库**，是"GPU 版 std::mt19937 + numpy.random"。

### 0.1 一句话对比

| 场景 | 手写 LCG | CPU（std::mt19937）| **cuRAND** |
|:--|:--|:--|:--|
| 生成 1 亿 float | 快但质量差 | ~1 秒 | **~10 ms** |
| 通过 TestU01 严格测试 | ❌ | ✅ | **✅** |
| 并行时无相关性 | ❌（严重）| N/A | **✅（Philox 天生并行）** |
| 反正态分布（金融常用） | 自己写 | 自己写 | **✅ 内置** |
| Sobol 拟随机（低差异） | ❌ | ✅ | **✅** |

### 0.2 cuRAND 现在有多重要？

- **CUDA Toolkit 自带**；
- **PyTorch `torch.randn` / TensorFlow `tf.random`** 底层都是 cuRAND；
- **量化金融的蒙特卡洛期权定价**必需；
- **深度学习初始化 / dropout / data augmentation** 大量使用；
- **粒子系统 / 物理仿真 / 随机图算法** 的基础。

**一句话**：**cuRAND = GPU 上生成高质量随机数的官方标准答案**——蒙特卡洛、AI 数据增强、粒子仿真的必修。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **R1 入门** | 会 Host API 生成 uniform / normal 大批量随机数 |
| **R2 熟练** | 会 Device API 在自己 kernel 里就地生成，理解 state / offset |
| **R3 高阶** | 会选合适生成器（Philox 并行首选、Sobol 拟随机、MTGP 高质量），会 seed 管理保证可复现 |
| **R4 专家** | 混合分布 / 拒绝采样、自定义 sampler、与 cuFFT/cuBLAS pipeline |

**建议**：**2 天到 R1**，**3~5 天到 R2/R3**（覆盖 95% 场景）。

---

## 1. cuRAND 是什么：一句话讲清 vs std::mt19937 / vs numpy.random

### 1.1 cuRAND 的定义

> **cuRAND = NVIDIA 官方 CUDA 版随机数生成库**。提供 **Host API**（host 侧一次生成大批量）+ **Device API**（在你自己 `__global__` kernel 里就地生成）。支持 5 种生成器与 6+ 种分布。

关键三点：

1. **Host API + Device API 双套**——想用哪种看场景；
2. **State-based**——每个 thread 一个 state（对 Device API）；
3. **架构感知**——Philox 对并行最友好，Sobol 拟随机用于金融。

### 1.2 cuRAND vs 竞品

| 维度 | std::mt19937 | numpy.random | **cuRAND** |
|:--|:--|:--|:--|
| 位置 | CPU | CPU (numpy) / GPU (cupy) | **GPU** |
| 并行安全 | ❌（多线程要多 state）| ⚠️ | **✅ Philox 完美并行** |
| 生成速度 | 慢 | 中 | **快 100x** |
| 质量 | 好（MT19937）| 好 | **好（多种可选）** |
| Sobol / 拟随机 | ❌ | ✅ | **✅** |
| 目标读者 | C++ | 科学计算 | **GPU 蒙特卡洛/AI** |

### 1.3 一张图看清 cuRAND 在栈里的位置

```
┌──────────────────────────────────────────────────────────┐
│  PyTorch randn / CuPy random / MATLAB GPU rand           │
├──────────────────────────────────────────────────────────┤
│  cuRAND                                                   │
│  ┌──────────────────────┬─────────────────────────────┐   │
│  │ Host API             │ Device API (kernel 内)      │   │
│  │ curandGenerateNormal │ curand_normal(&state)       │   │
│  └──────────────────────┴─────────────────────────────┘   │
├──────────────────────────────────────────────────────────┤
│  CUDA Runtime + Driver                                    │
├──────────────────────────────────────────────────────────┤
│  GPU 硬件（3060 / SM86）                                    │
└──────────────────────────────────────────────────────────┘
```

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 好消息：cuRAND 随 CUDA Toolkit 自带

- 头文件：`<cuda>/include/curand.h`（Host API）、`curand_kernel.h`（Device API）
- 链接：`-lcurand`

### 2.2 一步验证：hello_curand.cu

```cpp
#include <curand.h>
#include <cuda_runtime.h>
#include <iostream>
#include <vector>

int main() {
    const size_t N = 10'000'000;
    float* d;
    cudaMalloc(&d, N * sizeof(float));

    curandGenerator_t gen;
    curandCreateGenerator(&gen, CURAND_RNG_PSEUDO_PHILOX4_32_10);
    curandSetPseudoRandomGeneratorSeed(gen, 1234ULL);

    // 生成 1000 万正态分布随机数
    curandGenerateNormal(gen, d, N, /*mean=*/0.0f, /*std=*/1.0f);

    std::vector<float> h(10);
    cudaMemcpy(h.data(), d, 10*sizeof(float), cudaMemcpyDeviceToHost);
    for (auto v : h) std::cout << v << " ";
    std::cout << "\n";

    curandDestroyGenerator(gen);
    cudaFree(d);
}
```

编译：

```bash
nvcc -O3 -std=c++17 -arch=sm_86 hello_curand.cu -lcurand -o hello_curand
./hello_curand
# 期望：一串正态分布的浮点数（0 附近，标准差 1）
```

### 2.3 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 每次运行结果不同 | 忘 setSeed 或 seed 变 | 固定 seed |
| `GenerateNormal` 要求偶数 | Box-Muller 成对生成 | N 必须偶数 |
| Device API 用同 seed+offset 不同 thread | 冲突 | 每 thread 用不同 subsequence |
| MTGP32 慢 | 该生成器构造开销大 | 高频用 Philox |
| 忘 destroy generator | 内存泄漏 | 每 Create 配 Destroy |

---

## 3. cuRAND 的心智模型：Host API vs Device API + 5 种生成器

### 3.1 两套 API

| API | 谁调 | 何时用 |
|:--|:--|:--|
| **Host API**（`curandGenerator_t`） | Host 侧调，一次生成大批量 | 预先生成大量随机数存显存 |
| **Device API**（`curandState_t`） | 你 kernel 里就地调 | 蒙特卡洛：每 thread 边算边生成 |

### 3.2 5 种生成器

| Generator | 类型 | 特点 |
|:--|:--|:--|
| `CURAND_RNG_PSEUDO_XORWOW` | 伪随机 | 默认，快，质量一般 |
| `CURAND_RNG_PSEUDO_MRG32K3A` | 伪随机 | 高质量，稍慢 |
| `CURAND_RNG_PSEUDO_MTGP32` | 伪随机 | 长周期，构造慢 |
| `CURAND_RNG_PSEUDO_PHILOX4_32_10` | 计数器型 | **并行首选**，无 state 干扰 |
| `CURAND_RNG_QUASI_SOBOL32/64` | 拟随机 | 低差异序列，蒙特卡洛积分首选 |

**推荐**：**默认用 Philox**——并行完美、速度快、质量好。

### 3.3 Seed & Subsequence

- **Seed**：初始种子（同 seed 结果完全复现）；
- **Subsequence**：每 thread 用不同子序列，避免相关性；
- **Offset**：跳过前 N 个随机数（用于分段生成）。

**并行金律**：**每 thread 用同 seed + 不同 subsequence**（Philox 天然支持）。

---

## 4. 第一个程序：Host API 生成 1 亿正态分布

见 2.2 节代码。**要点**：

- **Philox 生成器**——最适合并行；
- **`GenerateNormal`** 用 Box-Muller，输出成对，**N 必须偶数**；
- 生成 1000 万只需几毫秒，比 CPU 快百倍。

### 4.1 6 个新手常见坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | 每次结果不同 | seed 变了 | 固定 `SetPseudoRandomGeneratorSeed` |
| 2 | Normal 要偶数 | 报错 | N 偶数或用 `Uniform` |
| 3 | 用 XORWOW 多 stream 冲突 | 相关性差 | 换 Philox |
| 4 | Sobol 参数没 setDimensions | 结果错 | Sobol 是多维拟随机，要设维度 |
| 5 | 忘 destroy | 泄漏 | 一定 destroy |
| 6 | Host 生成 vs Device 生成期望不同 | 语义差异 | 二者不能互换验证 |

---

## 5. Device API：在自己 kernel 里就地生成

```cpp
#include <curand_kernel.h>

__global__ void init_states(curandStatePhilox4_32_10_t* states, unsigned long seed) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    curand_init(seed, /*subsequence=*/tid, /*offset=*/0, &states[tid]);
}

__global__ void monte_carlo(curandStatePhilox4_32_10_t* states, int n, int* hits) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    curandStatePhilox4_32_10_t s = states[tid];    // 拷到寄存器（关键）

    int local = 0;
    for (int i = 0; i < 1000; ++i) {
        float x = curand_uniform(&s);
        float y = curand_uniform(&s);
        if (x*x + y*y < 1.0f) local++;
    }
    atomicAdd(hits, local);
    states[tid] = s;   // 写回
}
```

**要点**：
- **每 thread 一个 state**，用 `curand_init(seed, tid, 0, ...)` 初始化；
- **state 拷到寄存器**再用，最后写回——比每次访问全局快得多；
- 支持 `curand_uniform / curand_normal / curand_poisson` 等 device 函数。

**用途**：蒙特卡洛期权定价、粒子仿真、随机图遍历——都是 Device API 的主场。

---

## 6. 生成器对比：XORWOW / MRG32k3a / MTGP32 / Philox / Sobol

| 场景 | 首选 |
|:--|:--|
| 通用 / 深度学习 dropout | **Philox** |
| 蒙特卡洛期权定价 | **Philox 或 Sobol**（Sobol 收敛更快） |
| 数值积分（低差异需求） | **Sobol** |
| 需要极高质量伪随机 | **MRG32k3a** 或 **MTGP32** |
| 快速实验、要求不高 | **XORWOW** |

**Philox 的优势**：是**计数器型**（不需要维护 state 之间的关系），并行时**每 thread 独立**，完美复现，速度也最快之一。

---

## 7. 分布：Uniform / Normal / LogNormal / Poisson / Discrete

### 7.1 Host API

| API | 分布 |
|:--|:--|
| `curandGenerateUniform` | U(0,1) |
| `curandGenerateNormal(mean, std)` | N(mean, std) |
| `curandGenerateLogNormal(mean, std)` | log-normal |
| `curandGeneratePoisson(lambda)` | Poisson |

### 7.2 Device API

- `curand_uniform(&state)`：float in (0,1]；
- `curand_normal(&state)`：std normal；
- `curand_log_normal(&state, m, s)`：log-normal；
- `curand_poisson(&state, lambda)`：Poisson。

**离散分布 / 分类采样**：cuRAND 没有直接 API，可以自己组合 `curand_uniform + 逆 CDF`。

---

## 8. 性能分析与调优

### 8.1 三条铁律

1. **Philox 并行首选**——无 state 依赖；
2. **State 缓存寄存器**——Device API 里每次访问 global state 是浪费；
3. **Batched 生成**——Host API 一次生成 1M+ 数比循环调用快。

### 8.2 Nsight

看 `sm__inst_executed_pipe_alu`——生成随机数主要是整数/浮点运算。DRAM 用量小，属于 compute-bound。

---

## 9. cuRAND vs 手写 LCG / vs CPU 随机数

| 需求 | 手写 LCG | CPU (mt19937) | **cuRAND** |
|:--|:--|:--|:--|
| 速度 | 快 | 慢 | **快** |
| 质量 | 差 | 好 | **好** |
| 并行安全 | ❌ | ⚠️ | **✅** |
| Sobol / 低差异 | ❌ | ✅ | **✅** |
| Poisson / LogNormal | 得手写 | ✅ | **✅** |
| 首选度 | 不推荐 | CPU 场景 | **GPU 首选** |

---

## 10. 学习路线图（5 天）

- **Day 1**：Host API 生成 Uniform/Normal；
- **Day 2**：Device API 蒙特卡洛 π；
- **Day 3**：Sobol 拟随机做数值积分；
- **Day 4**：期权定价（Black-Scholes 蒙特卡洛）；
- **Day 5**：与 cuBLAS/cuFFT pipeline 组合成完整工作流。

---

## 11. 精选资源与踩坑清单

### 11.1 必读

| 资源 | 链接 |
|:--|:--|
| cuRAND 官方文档 | <https://docs.nvidia.com/cuda/curand/> |
| CUDA Samples: MC | `<CUDA>/samples/5_Domain_Specific/MonteCarloMultiGPU` |
| Philox 论文 | Salmon et al. "Parallel Random Numbers: As Easy as 1, 2, 3" (SC'11) |

### 11.2 踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 复现失败 | seed 或 subsequence 变了 | 固定二者 |
| 并行结果相关性强 | 用了 XORWOW 或 seed 相同 | 换 Philox + 不同 subseq |
| MTGP32 慢 | 构造开销 | 用 Philox |
| Sobol 收敛慢 | 未 setDimensions | 明确设置 |
| Normal 数量报错 | N 奇数 | 用偶数 |
| Device state 慢 | 每次读全局 | 拷寄存器再用 |
| 混用 Host + Device 期望冲突 | 语义差异 | 二者独立 |

### 11.3 一句话总结

> **cuRAND = GPU 上生成高质量随机数的官方标准答案**。**蒙特卡洛、深度学习初始化 / dropout、粒子仿真** 必修。**Philox 并行首选、Sobol 拟随机首选、State 缓存寄存器**——三条口诀走遍天下。

---

**祝你写出跑得快又可复现的蒙特卡洛。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
