# cuBLAS 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：已经写过基本 CUDA 或用过 NumPy/PyTorch 的程序员，做**数值计算、深度学习、科学计算**，想**用官方最快的线性代数库把矩阵乘/向量运算打到硬件峰值**，而不是自己手写 kernel。
> **目标**：3~7 天内，从"用 `cublasSgemm` 跑第一个 GEMM"到"能用 stream 并发多路 GEMM、能选对 dtype/layout 打到 3060 FP16 Tensor Core 峰值、能调试常见的 layout/leading-dim 坑"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1**（cuBLAS 随 CUDA Toolkit 自带）+ C++17。

---

## 目录

- [0. 写在最前：为什么要学 cuBLAS？](#0-写在最前为什么要学-cublas)
- [1. cuBLAS 是什么：一句话讲清 vs cuBLASLt / vs CUTLASS](#1-cublas-是什么一句话讲清-vs-cublaslt--vs-cutlass)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. cuBLAS 的心智模型：Handle / Stream / Layout / Level](#3-cublas-的心智模型handle--stream--layout--level)
- [4. 第一个程序：`cublasSgemm` 完整流程](#4-第一个程序cublassgemm-完整流程)
- [5. 三大 Level：Level-1（向量）/ Level-2（矩阵×向量）/ Level-3（矩阵×矩阵）](#5-三大-levellevel-1向量--level-2矩阵向量--level-3矩阵矩阵)
- [6. Tensor Core 加速：`cublasGemmEx` 与 FP16/BF16/TF32](#6-tensor-core-加速cublasgemmex-与-fp16bf16tf32)
- [7. Batch/Strided-Batched GEMM 与 stream 并发](#7-batchstrided-batched-gemm-与-stream-并发)
- [8. 性能分析与调优](#8-性能分析与调优)
- [9. cuBLAS vs 手写 CUDA / CUTLASS / Triton](#9-cublas-vs-手写-cuda--cutlass--triton)
- [10. 学习路线图（1 周）](#10-学习路线图1-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 cuBLAS？

你可能会问：**PyTorch 一句 `A @ B` 就搞定了，为什么还要碰 cuBLAS？** 答案是三点：

1. **PyTorch 的 `A @ B` 底下就是 cuBLAS**——理解它就是理解"为什么快"；
2. **你要写 C++/CUDA 应用**（图形、仿真、机器人）时没有 PyTorch，cuBLAS 是唯一官方选择；
3. **性能上限就是这里**——cuBLAS 是 NVIDIA 官方极致优化的 BLAS 实现，手写 CUDA 很难打赢。

### 0.1 一句话对比

| 场景 | 手写 CUDA GEMM | **cuBLAS** |
|:--|:--|:--|
| M=N=K=4096 FP32 GEMM | 3000+ 行 + 天才级优化 | **1 行 `cublasSgemm`** |
| 打到 3060 FP32 峰值（~13 TFLOPS）| 死磕数月 | **默认打到 80~95%** |
| FP16 Tensor Core（3060 ~51 TFLOPS）| 需 mma.sync + swizzle | **`cublasGemmEx` 一行** |
| 100 个小 GEMM 并发 | 手动 stream + kernel | **`cublasSgemmStridedBatched`** |

### 0.2 cuBLAS 现在有多重要？

- **CUDA Toolkit 自带**，NVIDIA 长期维护，跨 SM 版本自动适配；
- **PyTorch / TensorFlow / JAX / NumPy(cupy) 的 GEMM 引擎**；
- **科学计算、CFD、量化、机器人求解器**的数值内核；
- **cuBLASLt / cuDNN 的基础**——学 cuBLAS 是所有下游库的门票。

**一句话**：**cuBLAS 是 NVIDIA GPU 上"矩阵乘的官方标准答案"**——学不学它决定了你能不能用满 GPU 的算力。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **B1 入门** | 会用 `cublasSgemm` / `cublasSaxpy` / `cublasSdot`，理解 column-major |
| **B2 熟练** | 会用 stream 并发、`cublasGemmEx` 走 Tensor Core、Batched GEMM |
| **B3 高阶** | 会用 `cublasSetMathMode` 精调、TF32/BF16/FP16 混精、算法号选优 |
| **B4 专家** | 与 cuBLASLt / cuDNN / CUTLASS 混用，`heuristic` 选算法，与 stream/Graph 深度集成 |

**建议**：**2~3 天到 B1**（能替换 numpy）；**3~5 天到 B2**（覆盖 90% 生产场景）；**一周基本吃透**。

---

## 1. cuBLAS 是什么：一句话讲清 vs cuBLASLt / vs CUTLASS

### 1.1 cuBLAS 的定义

> **cuBLAS = NVIDIA 官方的 CUDA 版 BLAS（Basic Linear Algebra Subprograms）库**。BLAS 是 1979 年就有的经典数值计算 API 标准（`saxpy / sgemm / dgemv` 等），cuBLAS 就是**这套标准在 GPU 上的官方实现**——C API、Fortran-style column-major、按 Level-1/2/3 分类。

关键三点：

1. **C API，Fortran 惯例**——**默认 column-major**（列主序），这是与 C/C++ 直觉最不同的地方；
2. **Handle-based**——所有调用都要传一个 `cublasHandle_t`（内部有 workspace、算法缓存等）；
3. **stream-aware**——绑上 stream 就能与你的其他 kernel 并发。

### 1.2 cuBLAS vs cuBLASLt vs CUTLASS

| 维度 | **cuBLAS** | cuBLASLt | CUTLASS |
|:--|:--|:--|:--|
| API 风格 | 传统 BLAS（`sgemm`) | Descriptor-based（更灵活）| C++ 模板 |
| 融合支持 | 有限（Bias/ReLU 部分）| **强**（多种 epilogue） | 极强（任意 functor） |
| INT8/FP8 | 支持 | **首选** | 支持 |
| Layout 灵活性 | 中 | **高**（padded/tiled/interleaved）| 极高 |
| 学习曲线 | **低** | 中 | 陡 |
| 目标读者 | 所有 GPU 用户 | AI 推理/量化工程师 | Kernel 工程师 |
| 心智 | "调 API" | "配 Descriptor" | "拼积木" |

**记忆口诀**：
- **传统 BLAS 心智** → **cuBLAS**（入门首选）；
- **想融合 + 量化 + 灵活 layout** → cuBLASLt；
- **想吃透原理 + 自定义 fuse** → CUTLASS。

### 1.3 一张图看清 cuBLAS 在栈里的位置

```
┌──────────────────────────────────────────────────────────┐
│  PyTorch / TensorFlow / NumPy(CuPy) / JAX                 │
├──────────────────────────────────────────────────────────┤
│  cuDNN（卷积/RNN）  ← 内部大量调 cuBLAS/cuBLASLt           │
├──────────────────────────────────────────────────────────┤
│  cuBLAS   |   cuBLASLt   |   CUTLASS  ←  一层三兄弟         │
├──────────────────────────────────────────────────────────┤
│  CUDA Runtime + Driver                                    │
├──────────────────────────────────────────────────────────┤
│  GPU 硬件（3060 / Ampere / SM86 / Tensor Core）             │
└──────────────────────────────────────────────────────────┘
```

**核心洞察**：cuBLAS 是"塔基"，向上被 cuDNN / PyTorch / NumPy 使用；向内它把 Tensor Core、CUDA Graph、多 stream 全都封装好。

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 好消息：cuBLAS 随 CUDA Toolkit 自带

装了 CUDA 12.1 就已经有 cuBLAS 了。**无需额外安装**。

- 头文件：`<cuda>/include/cublas_v2.h`
- 动态库（Linux）：`libcublas.so`
- 动态库（Windows）：`cublas64_12.dll`

### 2.2 一步验证：hello_cublas.cu

```cpp
// hello_cublas.cu
#include <cublas_v2.h>
#include <cuda_runtime.h>
#include <iostream>
#include <vector>

int main() {
    int M=4, N=4, K=4;
    std::vector<float> hA(M*K, 1.0f);
    std::vector<float> hB(K*N, 2.0f);
    std::vector<float> hC(M*N, 0.0f);

    float *dA, *dB, *dC;
    cudaMalloc(&dA, M*K*4); cudaMalloc(&dB, K*N*4); cudaMalloc(&dC, M*N*4);
    cudaMemcpy(dA, hA.data(), M*K*4, cudaMemcpyHostToDevice);
    cudaMemcpy(dB, hB.data(), K*N*4, cudaMemcpyHostToDevice);

    cublasHandle_t h; cublasCreate(&h);

    float alpha=1.0f, beta=0.0f;
    // 注意：cuBLAS 是 column-major，参数顺序看起来"反"
    cublasSgemm(h, CUBLAS_OP_N, CUBLAS_OP_N,
                M, N, K,
                &alpha, dA, M, dB, K,
                &beta,  dC, M);

    cudaMemcpy(hC.data(), dC, M*N*4, cudaMemcpyDeviceToHost);
    std::cout << "C[0]=" << hC[0] << " (expected " << K*2.0f << ")\n";

    cublasDestroy(h);
    cudaFree(dA); cudaFree(dB); cudaFree(dC);
}
```

编译：

```bash
nvcc -O3 -std=c++17 -arch=sm_86 hello_cublas.cu -lcublas -o hello_cublas
./hello_cublas
# C[0]=8 (expected 8)
```

### 2.3 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 结果全错但没报错 | **忘了 column-major**，参数顺序看错 | 见第 3 节详解 |
| `CUBLAS_STATUS_NOT_INITIALIZED` | 忘 `cublasCreate` | 先建 handle |
| 链接错 `undefined cublasSgemm` | 忘 `-lcublas` | 加上 |
| Windows 找不到 dll | 系统没找到 `cublas64_12.dll` | 把 `<CUDA>/bin` 加 PATH |
| 大 GEMM 慢 | 没走 Tensor Core（用了 SP GEMM）| 用 `cublasGemmEx` + FP16 |
| stream 未生效 | 忘 `cublasSetStream` | handle 绑 stream |

---

## 3. cuBLAS 的心智模型：Handle / Stream / Layout / Level

### 3.1 Handle：所有调用的入口

```cpp
cublasHandle_t h;
cublasCreate(&h);          // 一个 handle 就够整个程序用
// ... 用 h 调用一切 cublas 函数 ...
cublasDestroy(h);
```

Handle 内部持有 workspace、算法缓存、当前 stream。**同一 handle 不要跨线程共享**——需要多线程用多个 handle。

### 3.2 Stream：并发的钥匙

```cpp
cudaStream_t s;
cudaStreamCreate(&s);
cublasSetStream(h, s);    // 之后所有 cublas 调用都在这个 stream 上
```

**关键**：不绑 stream 就走默认 stream，会阻塞其他 kernel。**大 GEMM + 小 GEMM 并发** 靠多 stream。

### 3.3 Column-major（**最重要的坑**）

cuBLAS 是 Fortran 传统 → **列主序**。C/C++ 程序员的直觉是行主序，**这里是最容易出结果错但不报错的地方**。

**列主序**：矩阵 `A[m, k]` 存成一维数组 `A_data[i + j*m]`（列先增加）；
**行主序**：`A_data[i*k + j]`（行先增加）。

**参数含义**：
```cpp
cublasSgemm(h, opA, opB, M, N, K, &alpha, A, lda, B, ldb, &beta, C, ldc);
```
- `lda`：A 的 **leading dimension**——列主序下就是 A 的**行数** M；
- `opA=CUBLAS_OP_N`：A 不转置；`OP_T`：转置；
- 计算的是 `C[M×N] = alpha * op(A) * op(B) + beta * C`。

**技巧**：如果你的数据是**行主序**（C/C++ 常态），有两种解法：
1. **swap trick**：调 `sgemm` 时把 A/B 互换 + 传原始行主序作为"列主序的转置"——最常用；
2. 用 `cublasLtMatmul` 显式设置 layout ORDER 参数。

### 3.4 Level 分类

- **Level-1**：向量 op 向量（`saxpy`, `sdot`, `snrm2`）；
- **Level-2**：矩阵 op 向量（`sgemv`, `strmv`）；
- **Level-3**：矩阵 op 矩阵（`sgemm`, `strsm`）—— **占 95% 使用**。

**性能**：Level-3 是**算力密集型**（每字节多个 FLOP），是 GPU 最爱的运算类型；Level-1/2 是**访存密集型**，性能受带宽限制。

---

## 4. 第一个程序：`cublasSgemm` 完整流程

见 2.2 节。这里做**小白级逐段拆解**。

### 4.1 逐行讲透

```cpp
cublasCreate(&h);
```
建 handle，内部会预热 CUDA 上下文（第一次调可能慢几十 ms）。

```cpp
float alpha=1.0f, beta=0.0f;
```
计算 `C = alpha * A*B + beta * C`。alpha=1, beta=0 就是纯 GEMM。

```cpp
cublasSgemm(h, CUBLAS_OP_N, CUBLAS_OP_N,
            M, N, K,
            &alpha, dA, M, dB, K,
            &beta,  dC, M);
```

**参数逐一**：
- `OP_N, OP_N`：A 和 B 都不转置；
- `M, N, K`：结果 C 是 `M×N`，中间维度 K；
- `dA, M`：A 指针 + leading dim（列主序下=行数 M）；
- `dB, K`：B 指针 + leading dim（=行数 K）；
- `dC, M`：C 指针 + leading dim；
- `alpha/beta` 传的是**指针**——因为可以指向 host 或 device 的标量（默认 host）。

### 4.2 6 个新手常见坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | 忘 column-major | 结果全错但不报错 | swap trick 或转置 |
| 2 | leading dim 传错 | 结果部分错 | ldA=M, ldB=K, ldC=M（no-trans 情况） |
| 3 | alpha/beta 传值不是指针 | 编译错或崩 | 用 `&alpha` |
| 4 | alpha/beta 位置错 | 结果错 | 严格照签名 |
| 5 | dtype 混（Sgemm vs Dgemm）| 结果乱 | `S`=float, `D`=double, `H`=half |
| 6 | 未 sync 就读结果 | 拿旧值 | `cudaStreamSynchronize` |

---

## 5. 三大 Level：Level-1（向量）/ Level-2（矩阵×向量）/ Level-3（矩阵×矩阵）

### 5.1 Level-1 常用 API

| API | 作用 |
|:--|:--|
| `cublasSaxpy(h, n, &a, x, 1, y, 1)` | `y = a*x + y` |
| `cublasSdot(h, n, x, 1, y, 1, &r)` | `r = x·y` |
| `cublasSnrm2(h, n, x, 1, &r)` | `r = ||x||₂` |
| `cublasSscal(h, n, &a, x, 1)` | `x = a*x` |
| `cublasIsamax(h, n, x, 1, &i)` | argmax |

### 5.2 Level-2 常用

| API | 作用 |
|:--|:--|
| `cublasSgemv` | `y = alpha*A*x + beta*y` |
| `cublasStrmv` | 三角矩阵×向量 |
| `cublasSger` | rank-1 更新 `A = A + alpha*x*y^T` |

### 5.3 Level-3 常用

| API | 作用 |
|:--|:--|
| `cublasSgemm` | `C = alpha*A*B + beta*C`（主力）|
| `cublasStrsm` | 三角求解 `A*X = B` |
| `cublasSsyrk` | 对称 rank-K 更新 |

---

## 6. Tensor Core 加速：`cublasGemmEx` 与 FP16/BF16/TF32

**cuBLAS 传统的 `Sgemm` 用 CUDA Core（FP32），跑不满 3060 的 Tensor Core**。要走 Tensor Core：

```cpp
cublasGemmEx(h, CUBLAS_OP_N, CUBLAS_OP_N,
             M, N, K,
             &alpha,
             dA, CUDA_R_16F, M,        // A 是 FP16
             dB, CUDA_R_16F, K,
             &beta,
             dC, CUDA_R_32F, M,        // C 是 FP32（累加高精度）
             CUBLAS_COMPUTE_32F,       // 累加 FP32
             CUBLAS_GEMM_DEFAULT_TENSOR_OP);
```

**关键**：
- **A/B: FP16 (`CUDA_R_16F`) / BF16 (`CUDA_R_16BF`)** 走 Tensor Core；
- **C 用 FP32** 累加防溢出；
- **算法号** `CUBLAS_GEMM_DEFAULT_TENSOR_OP` 强制走 Tensor Core。

**性能**：3060 上 FP16 Tensor Core 峰值 ~51 TFLOPS，`cublasGemmEx` 能打到 40+ TFLOPS。

### 6.1 TF32：0 改动升级

Ampere 引入 TF32（`CUBLAS_COMPUTE_32F_FAST_TF32`）——**FP32 精度但走 Tensor Core**，速度几乎翻倍，精度略降但对 DL 训练通常够用。

```cpp
cublasSetMathMode(h, CUBLAS_TF32_TENSOR_OP_MATH);  // 全局开 TF32
cublasSgemm(...);   // 现在自动走 TF32 Tensor Core
```

---

## 7. Batch/Strided-Batched GEMM 与 stream 并发

### 7.1 Batched（一次算 100 个小 GEMM）

```cpp
// 100 个 32×32 GEMM，一次调用完成
cublasSgemmStridedBatched(h, OP_N, OP_N,
    32, 32, 32,
    &alpha,
    dA, 32, 32*32,       // stride between batches
    dB, 32, 32*32,
    &beta,
    dC, 32, 32*32,
    /*batchCount=*/100);
```

**用途**：Transformer 里的 multi-head attention 每 head 一个小 GEMM，batched 一次搞定。

### 7.2 Stream 并发

```cpp
cublasHandle_t h1, h2;   // 或同 handle 换 stream
cudaStream_t s1, s2;
cudaStreamCreate(&s1); cudaStreamCreate(&s2);

cublasSetStream(h1, s1); cublasSgemm(h1, ..., ...);   // GEMM 1 在 s1
cublasSetStream(h1, s2); cublasSgemm(h1, ..., ...);   // GEMM 2 在 s2 并发
```

---

## 8. 性能分析与调优

### 8.1 计算峰值（3060）

- **FP32 (CUDA Core)**：~13 TFLOPS；
- **FP16 (Tensor Core)**：~51 TFLOPS；
- **TF32 (Tensor Core)**：~26 TFLOPS。

### 8.2 三条铁律

1. **能用 FP16 就用 FP16**（Tensor Core 4x 快）；
2. **大 GEMM 走 Level-3**——1000×1000 以上才能打峰值；
3. **多 stream + Batched** 把小 GEMM 打包。

### 8.3 用 Nsight Compute 观察

```bash
ncu --set full ./hello_cublas
```

看 `sm__inst_executed_pipe_tensor_op` 是否非零——如果 0 就是没走 Tensor Core。

---

## 9. cuBLAS vs 手写 CUDA / CUTLASS / Triton

| 需求 | 手写 | cuBLAS | cuBLASLt | CUTLASS | Triton |
|:--|:--|:--|:--|:--|:--|
| 简单 GEMM | 造轮子 | **✅ 首选** | 麻烦 | 陡 | 陡 |
| Fused GEMM+Bias+ReLU | 分 kernel | 有限 | **✅** | ✅ | ✅ |
| INT8/FP8 | 极难 | 有限 | **✅** | ✅ | ⚠️ |
| 自定义 epilogue | 极难 | ❌ | 部分 | **✅** | ✅ |

**决策口诀**：
- **需求简单** → cuBLAS；
- **要融合 + 量化** → cuBLASLt；
- **要极致自定义 kernel** → CUTLASS / Triton。

---

## 10. 学习路线图（1 周）

- **Day 1~2**：hello_cublas + 理解 column-major，替换 numpy 的 matmul；
- **Day 3~4**：`cublasGemmEx` 走 Tensor Core，对比 3060 FP32 vs FP16 性能；
- **Day 5**：Batched GEMM + stream 并发；
- **Day 6~7**：与 PyTorch 集成（`cpp_extension`）、benchmark 与 `torch.matmul` 对比。

---

## 11. 精选资源与踩坑清单

### 11.1 必读资源

| 资源 | 链接 |
|:--|:--|
| cuBLAS 官方文档 | <https://docs.nvidia.com/cuda/cublas/> |
| CUDA Samples: cuBLAS | `<CUDA>/samples/4_CUDA_Libraries/` |
| PyTorch ATen cuBLAS 调用参考 | <https://github.com/pytorch/pytorch/tree/main/aten/src/ATen/cuda> |

### 11.2 踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 结果全错 | column-major 未处理 | swap trick |
| leading dim 传错 | 拷贝了对应的另一维 | 严格按签名 |
| FP16 GEMM 慢 | 走了 CUDA Core | 用 `cublasGemmEx` + TENSOR_OP 算法号 |
| 小 GEMM 慢 | launch overhead 大 | 用 batched |
| 多线程冲突 | 共享 handle | 每线程一个 handle |
| stream 不并发 | 没设 stream | `cublasSetStream` |
| alpha/beta host vs device | pointer mode 不对 | `cublasSetPointerMode` |
| BF16 不支持 | 版本或硬件 | Ampere+ 才有 |

### 11.3 一句话总结

> **cuBLAS = "GPU 上做矩阵/向量运算的官方标准答案"**。学它就是学 NVIDIA 让 PyTorch/NumPy 快起来的秘密。**Column-major 是最大的坑，Tensor Core 是最大的加速**。用好 `cublasGemmEx` + FP16，3060 上能把 GEMM 打到 40+ TFLOPS。

---

**祝你把 GPU 的算力榨到最后一滴。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
