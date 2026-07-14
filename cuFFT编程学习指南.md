# cuFFT 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：搞**信号处理、图像处理、CFD/物理仿真、雷达/通信、量化交易、音频/视频**的 C++/CUDA 程序员，用过 FFTW（CPU 版）或 NumPy `np.fft`，想在 GPU 上把 FFT 打到硬件峰值。
> **目标**：3~7 天内，从"用 `cufftExecR2C` 跑第一个 1D 实数 FFT"到"能做 2D/3D FFT、Batched FFT、In-place FFT、能与自定义 kernel pipeline"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1**（cuFFT 随 CUDA Toolkit 自带）+ C++17。

---

## 目录

- [0. 写在最前：为什么要学 cuFFT？](#0-写在最前为什么要学-cufft)
- [1. cuFFT 是什么：一句话讲清 vs FFTW / vs NumPy fft](#1-cufft-是什么一句话讲清-vs-fftw--vs-numpy-fft)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. cuFFT 的心智模型：Plan / Type / Direction / Batch](#3-cufft-的心智模型plan--type--direction--batch)
- [4. 第一个程序：1D R2C FFT 完整流程](#4-第一个程序1d-r2c-fft-完整流程)
- [5. 常用变体：C2C / R2C / C2R / 2D / 3D / Batched](#5-常用变体c2c--r2c--c2r--2d--3d--batched)
- [6. Callback：在 FFT 前后融合自己 kernel](#6-callback在-fft-前后融合自己-kernel)
- [7. cufftXt：多 GPU 与 Half FFT](#7-cufftxt多-gpu-与-half-fft)
- [8. 性能分析与调优](#8-性能分析与调优)
- [9. cuFFT vs FFTW / VkFFT / 手写](#9-cufft-vs-fftw--vkfft--手写)
- [10. 学习路线图（1 周）](#10-学习路线图1-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 cuFFT？

FFT（快速傅里叶变换）是数字信号处理的顶梁柱，也是许多算法的基石（卷积可以化为 FFT，PDE 求解可用谱方法，雷达匹配滤波，音频分析……）。**大规模 FFT 是访存密集型 + 计算密集型混合**，GPU 上跑比 CPU 快 10~100 倍。

**cuFFT = FFTW 的 GPU 版**——API 极其相似，学习曲线平缓。

### 0.1 一句话对比

| 场景 | FFTW（CPU） | **cuFFT（GPU）** |
|:--|:--|:--|
| 1M 点 1D FFT | ~10 ms | **~0.3 ms** |
| 4096² 2D FFT | ~500 ms | **~5 ms** |
| 100 个 4K FFT 并发（Batched）| 挨个跑 | **一次调用** |
| 与自定义 kernel 融合 | 独立进程 | **Callback 内嵌** |

### 0.2 cuFFT 现在有多重要？

- **CUDA Toolkit 自带**；
- **PyTorch `torch.fft` / NumPy(CuPy) `cupy.fft`** 底层就是 cuFFT；
- **雷达/通信/图像/音频/CFD/量化** 领域普遍使用；
- **深度学习的 spectral method / FNO** 靠它；
- **多 GPU 大规模 FFT**（cufftXt）是 HPC 唯一路径。

**一句话**：**cuFFT = GPU 上做 FFT 的官方标准答案**——信号处理、科学计算的通用工具。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **F1 入门** | 会 1D R2C / C2R FFT，会 in-place / out-of-place |
| **F2 熟练** | 会 2D/3D FFT、Batched FFT、绑 stream |
| **F3 高阶** | 会 Callback 融合自定义 kernel、half FFT、多 GPU |
| **F4 专家** | 与 cuBLAS/cuDNN pipeline、benchmark 优化、非 2 幂大小的 tuning |

**建议**：**2~3 天到 F1**，**1 周到 F2/F3**（覆盖 95% 场景）。

---

## 1. cuFFT 是什么：一句话讲清 vs FFTW / vs NumPy fft

### 1.1 cuFFT 的定义

> **cuFFT（CUDA Fast Fourier Transform）= NVIDIA 官方 GPU 版 FFT 库**。API 风格模仿 FFTW，用 **Plan** 描述一次 FFT 的全部参数（大小、类型、Batch、方向），plan 复用性极高。

关键三点：

1. **Plan-based**——同一 shape 的 FFT 建一个 plan 反复用；
2. **In-place / Out-of-place**——一样 API 都支持；
3. **R2C / C2C / C2R**——实数/复数变换分类清晰。

### 1.2 cuFFT vs FFTW vs NumPy fft

| 维度 | FFTW | NumPy(np.fft) | **cuFFT** |
|:--|:--|:--|:--|
| 位置 | CPU | CPU (numpy) / GPU (cupy) | **GPU** |
| API 心智 | Plan-based | 一句话 | **Plan-based（同 FFTW）** |
| 性能 | 单机 CPU 极致 | 一般 | **10~100× FFTW** |
| Callback 融合 | ❌ | ❌ | **✅** |
| 多 GPU | ❌ | ❌ | **✅ cufftXt** |
| 学习曲线 | 已会等于会 cuFFT | 极低 | **低** |

### 1.3 一张图看清 cuFFT 在栈里的位置

```
┌──────────────────────────────────────────────────────────┐
│  PyTorch fft / CuPy fft / MATLAB GPU / TensorFlow signal  │
├──────────────────────────────────────────────────────────┤
│  cuFFT / cufftXt (multi-GPU)                              │
├──────────────────────────────────────────────────────────┤
│  CUDA Runtime + Driver                                    │
├──────────────────────────────────────────────────────────┤
│  GPU 硬件（3060 / SM86）                                    │
└──────────────────────────────────────────────────────────┘
```

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 好消息：cuFFT 随 CUDA Toolkit 自带

- 头文件：`<cuda>/include/cufft.h`, `cufftXt.h`
- 链接：`-lcufft`（Callback 需要 static `-lcufft_static -lculibos`）

### 2.2 一步验证：hello_cufft.cu

```cpp
#include <cufft.h>
#include <cuda_runtime.h>
#include <iostream>
#include <vector>
#include <cmath>

int main() {
    const int N = 1024;
    std::vector<float> h(N);
    for (int i = 0; i < N; ++i)
        h[i] = std::sin(2 * M_PI * 3.0 * i / N);   // 3 Hz sine

    float* d_in;
    cufftComplex* d_out;
    cudaMalloc(&d_in,  N * sizeof(float));
    cudaMalloc(&d_out, (N/2+1) * sizeof(cufftComplex));
    cudaMemcpy(d_in, h.data(), N*4, cudaMemcpyHostToDevice);

    cufftHandle plan;
    cufftPlan1d(&plan, N, CUFFT_R2C, /*batch=*/1);
    cufftExecR2C(plan, d_in, d_out);

    std::vector<cufftComplex> hr(N/2+1);
    cudaMemcpy(hr.data(), d_out, (N/2+1)*sizeof(cufftComplex), cudaMemcpyDeviceToHost);

    // 期望：bin 3 处幅度最大
    for (int i = 0; i < 10; ++i)
        std::cout << "bin " << i << ": |X|=" << std::hypot(hr[i].x, hr[i].y) << "\n";

    cufftDestroy(plan);
    cudaFree(d_in); cudaFree(d_out);
}
```

编译：

```bash
nvcc -O3 -std=c++17 -arch=sm_86 hello_cufft.cu -lcufft -o hello_cufft
./hello_cufft
```

期望：`bin 3: |X|=512`（其他 bin 接近 0）。

### 2.3 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| R2C 输出大小算错 | R2C 结果只有 N/2+1 复数 | 按 `N/2+1` 分配 |
| Plan 忘 destroy | 显存泄漏 | `cufftDestroy` |
| 非 2 幂性能差 | cuFFT 对 2/3/5/7 幂最快 | 尽量选 2 幂 |
| Callback 链接失败 | 需 static lib | `-lcufft_static -lculibos` |
| stream 未生效 | 忘 `cufftSetStream` | plan 绑 stream |
| 幅度差 N 倍 | 未归一化 | 除以 N |

---

## 3. cuFFT 的心智模型：Plan / Type / Direction / Batch

### 3.1 Plan：一切的入口

```cpp
cufftHandle plan;
cufftPlan1d(&plan, N, CUFFT_R2C, batch);
// or cufftPlan2d, cufftPlan3d, cufftPlanMany（最灵活）
```

Plan 内部预计算了：**FFT 分解方案（Cooley-Tukey 蝶形）、workspace、算法号**。**同一 shape 的 FFT 建一个 plan 反复用**，别每次都建。

### 3.2 Type：R2C / C2C / C2R

| Type | 输入 | 输出 | 场景 |
|:--|:--|:--|:--|
| **R2C** | 实数 | 复数（N/2+1）| 实信号 FFT 首选，省一半算力 |
| **C2C** | 复数 | 复数 | 通用 |
| **C2R** | 复数（N/2+1）| 实数 | R2C 的逆变换 |

**Hermitian 对称性**：实数信号的 FFT 天然对称，所以 R2C 只输出 N/2+1 个复数即可完整。

### 3.3 Direction

C2C 时需要方向：
- `CUFFT_FORWARD = -1`；
- `CUFFT_INVERSE = +1`。

R2C 只有 forward，C2R 只有 inverse。

### 3.4 Batch：一次跑多个 FFT

```cpp
cufftPlan1d(&plan, N, CUFFT_R2C, 100);   // 100 个独立的 N 点 FFT
```

**用途**：多通道音频、雷达多脉冲、Batched 频谱分析——比循环调用快很多。

---

## 4. 第一个程序：1D R2C FFT 完整流程

见 2.2 节代码。**小白拆解**：

### 4.1 五步走

1. **生成信号**：3 Hz 正弦；
2. **cudaMalloc**：实数输入 N，复数输出 N/2+1；
3. **`cufftPlan1d(N, R2C, batch=1)`**：建 plan；
4. **`cufftExecR2C(plan, in, out)`**：执行；
5. **验证**：bin 3 处应有大幅值，其他 bin 为 0。

### 4.2 6 个新手常见坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | R2C 输出大小算错 | 越界 | 分配 `N/2+1` 个 `cufftComplex` |
| 2 | 忘归一化 | 幅度差 N | inverse 后除 N |
| 3 | Plan 未 destroy | 显存泄漏 | `cufftDestroy` |
| 4 | 非 2 幂性能差 | 例如 N=1000 | 补零到 1024 |
| 5 | in-place 内存不够 | 崩 | in-place R2C 需 `2*(N/2+1)` |
| 6 | stream 未生效 | 阻塞 | `cufftSetStream(plan, s)` |

---

## 5. 常用变体：C2C / R2C / C2R / 2D / 3D / Batched

### 5.1 2D FFT

```cpp
cufftPlan2d(&plan, Nx, Ny, CUFFT_C2C);
cufftExecC2C(plan, dIn, dOut, CUFFT_FORWARD);
// 用途：图像卷积（FFT 卷积）、CFD 谱方法
```

### 5.2 3D FFT

```cpp
cufftPlan3d(&plan, Nx, Ny, Nz, CUFFT_C2C);
// 用途：CFD、量子化学、气象模拟
```

### 5.3 PlanMany（最灵活）

```cpp
int n[1] = {N};
int inembed[1] = {N};
int onembed[1] = {N/2+1};
cufftPlanMany(&plan, /*rank=*/1, n,
              inembed, /*istride=*/1, /*idist=*/N,
              onembed, /*ostride=*/1, /*odist=*/N/2+1,
              CUFFT_R2C, /*batch=*/100);
```

**用途**：数据不是紧凑排列（stride/dist 可自定义）。

---

## 6. Callback：在 FFT 前后融合自己 kernel

**cuFFT 的杀手锏**——**允许你在 FFT 加载/存储数据时插入自定义函数**，融合到 FFT kernel 里，省一次显存往返：

```cpp
// Callback 函数（device 端）
__device__ cufftComplex myLoadCB(void* dataIn, size_t offset, void* cb_info, void* sharedPtr) {
    float raw = ((float*)dataIn)[offset];
    return { raw * 2.0f, 0.0f };   // 加载时乘 2
}
__device__ cufftCallbackLoadC d_loadCB = myLoadCB;

// 注册
cufftCallbackLoadC h_loadCB;
cudaMemcpyFromSymbol(&h_loadCB, d_loadCB, sizeof(h_loadCB));
cufftXtSetCallback(plan, (void**)&h_loadCB, CUFFT_CB_LD_COMPLEX, nullptr);
```

**要求**：必须用**静态链接**（`-lcufft_static -lculibos`）。

**性能**：融合可以省一次显存读/写，对访存 bound 的 FFT 很关键。

---

## 7. cufftXt：多 GPU 与 Half FFT

- **`cufftXtSetGPUs`**：把一个大 FFT 切分到多 GPU；
- **`CUFFT_C2C_HALF`**（Ampere+）：FP16 FFT，性能 2x（精度受限）；
- **`cufftXtExec`**：多 GPU 执行。

**用途**：单 GPU 显存装不下的 8K³ 3D FFT。

---

## 8. 性能分析与调优

### 8.1 三条铁律

1. **N 选 2/3/5/7 幂**——cuFFT 对这些 radix 最快，其他数会慢 2~5x；
2. **Batched 优先**——多个小 FFT 一次跑，充分打满 GPU；
3. **R2C 优于 C2C**——实信号别用 C2C 浪费一半算力。

### 8.2 Nsight

FFT 是**混合型**（compute + memory）。看 SM 与 DRAM 双指标，都应 > 60%。

---

## 9. cuFFT vs FFTW / VkFFT / 手写

| 需求 | FFTW | VkFFT | **cuFFT** | 手写 |
|:--|:--|:--|:--|:--|
| 位置 | CPU | Vulkan GPU | **CUDA GPU** | CUDA |
| 通用性 | 强 | 强 | **强** | 差 |
| 官方支持 | ✅ | 开源 | **✅** | ❌ |
| 性能 | 最好 CPU | 有时打赢 cuFFT | **NVIDIA 极致** | 极难打赢 |
| 学习曲线 | 中 | 中 | **低** | 陡 |

**决策**：NVIDIA GPU 上首选 cuFFT，除非有特殊需求（非 2 幂大小、VkFFT 有时更快）。

---

## 10. 学习路线图（1 周）

- **Day 1~2**：1D R2C FFT + 频谱分析；
- **Day 3~4**：2D FFT + 图像卷积应用；
- **Day 5**：Batched FFT + stream；
- **Day 6~7**：Callback 融合 + 与 cuBLAS pipeline。

---

## 11. 精选资源与踩坑清单

### 11.1 必读

| 资源 | 链接 |
|:--|:--|
| cuFFT 官方文档 | <https://docs.nvidia.com/cuda/cufft/> |
| CUDA Samples: cuFFT | `<CUDA>/samples/4_CUDA_Libraries/` |
| VkFFT（对比参考）| <https://github.com/DTolm/VkFFT> |

### 11.2 踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| N=1000 特慢 | 非光滑数 | 补零到 1024 |
| in-place OOM | R2C 需 padded | 分配 `2*(N/2+1)` 大小 |
| 幅度差 N | 未归一 | 除 N |
| Callback 链接失败 | 用了 shared lib | 换 `-lcufft_static` |
| 多 GPU FFT 慢 | 未装 NVLink | 单机多卡才有意义 |
| FP16 精度差 | 累积误差 | 大 N 用 FP32 |

### 11.3 一句话总结

> **cuFFT = "GPU 上做 FFT 的官方标准答案"**——信号处理、科学计算、量化、CFD 的通用工具。学它 = 打开 GPU 数字信号处理的大门。**R2C + Batched + 2 幂 = 打到硬件峰值三件套**。

---

**祝你写出打到 GPU 峰值的 FFT。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
