# cuBLASLt 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：已经用过 cuBLAS 的程序员，做**深度学习推理**（尤其量化 INT8 / FP8）或**需要 GEMM+epilogue 融合**（bias + activation + scaling）的场景，发现 cuBLAS 传统 API 表达不了，想**用 NVIDIA 官方 "现代版 cuBLAS" 做灵活的 fused GEMM**。
> **目标**：1~2 周内，从"用 `cublasLtMatmul` 跑第一个 fused GEMM"到"能玩 INT8/FP8 量化 GEMM、能用 heuristic 自动选算法、能给 3060 SM86 挑最优 tile"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1**（cuBLASLt 随 CUDA Toolkit 自带）+ C++17。

---

## 目录

- [0. 写在最前：为什么要学 cuBLASLt？](#0-写在最前为什么要学-cublaslt)
- [1. cuBLASLt 是什么：一句话讲清 vs cuBLAS](#1-cublaslt-是什么一句话讲清-vs-cublas)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. cuBLASLt 的心智模型：4 个 Descriptor + Heuristic](#3-cublaslt-的心智模型4-个-descriptor--heuristic)
- [4. 第一个程序：`cublasLtMatmul` 完整流程](#4-第一个程序cublasltmatmul-完整流程)
- [5. Epilogue 融合：Bias / ReLU / GELU / Scaling 一把梭](#5-epilogue-融合bias--relu--gelu--scaling-一把梭)
- [6. INT8 / FP8 量化 GEMM](#6-int8--fp8-量化-gemm)
- [7. Heuristic：自动选最优算法](#7-heuristic自动选最优算法)
- [8. 性能分析与调优](#8-性能分析与调优)
- [9. cuBLASLt vs cuBLAS vs CUTLASS](#9-cublaslt-vs-cublas-vs-cutlass)
- [10. 学习路线图（1~2 周）](#10-学习路线图12-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 cuBLASLt？

用过 cuBLAS 你会发现三个痛点：

1. **参数太死板**——`cublasSgemm` 只有 alpha/beta，想 `Y = ReLU(A*B + bias)` 得起两个额外 kernel；
2. **量化支持一般**——INT8/FP8 GEMM 在 cuBLAS 里勉强能用但不灵活；
3. **算法选择黑盒**——传统 cuBLAS 内部自己选，没法让你干预。

**cuBLASLt（cuBLAS Lightweight，"轻量"其实是"灵活"的意思）就是为解决这三点而生**——**Descriptor-based API + Epilogue 融合 + Heuristic 显式选算法**。

### 0.1 一句话对比

| 场景 | 用 cuBLAS | **用 cuBLASLt** |
|:--|:--|:--|
| 简单 FP32 GEMM | ✅ 一行 | ⚠️ 得建 4 个 descriptor |
| `Y = ReLU(A*B + bias)` | ❌ 需要 3 个 kernel | **✅ 一次调用** |
| INT8 GEMM + 反量化 | ⚠️ 拧巴 | **✅ 官方一等公民** |
| FP8 GEMM (H100)| ❌ | **✅ 官方唯一路径** |
| 想手选算法 | ❌ 黑盒 | **✅ Heuristic 给候选** |

### 0.2 cuBLASLt 现在有多重要？

- **CUDA Toolkit 自带**（10.1 后随 cuBLAS 一起发）；
- **PyTorch 的 `_scaled_mm`（FP8 GEMM）底层**就是 cuBLASLt；
- **TensorRT / Faster Transformer / DeepSpeed** 大量使用；
- **Hopper（H100）FP8 GEMM** 的官方唯一 C++ 接口就是它；
- **大模型推理量化的核心工具**。

**一句话**：**cuBLASLt = "cuBLAS 的现代版本"**——想做量化推理 / fused GEMM，它是官方标准答案。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **Lt1 入门** | 会建 4 个 descriptor 跑通 FP32 GEMM |
| **Lt2 熟练** | 会用 `CUBLASLT_EPILOGUE_RELU_BIAS` 等融合 |
| **Lt3 高阶** | 会 INT8 / FP8 量化 GEMM，会用 heuristic 挑算法 |
| **Lt4 专家** | 与 Graph / stream / workspace 深度整合，与 cuBLAS/CUTLASS 混用 |

**建议**：**3 天到 Lt1**，**1~2 周到 Lt2/Lt3**（覆盖 95% 生产场景）。

---

## 1. cuBLASLt 是什么：一句话讲清 vs cuBLAS

### 1.1 cuBLASLt 的定义

> **cuBLASLt 是 cuBLAS 的"现代版扩展 API"**——用 4 个 Descriptor（Matmul / MatrixLayout × 3）描述一次 GEMM，支持 Epilogue 融合、INT8/FP8/FP16/BF16 全 dtype、Heuristic 自动选算法。它和 cuBLAS **共存于同一个 library**（`libcublas.so`），但 API 完全独立。

关键三点：

1. **Descriptor-based**——用"描述符"表达 GEMM 的所有参数（比 cuBLAS 一堆位置参数灵活得多）；
2. **Epilogue 融合**——一次 kernel 完成 `A*B + bias + activation + scaling`；
3. **Heuristic**——让 cuBLASLt 给你返回 N 个候选算法，你可以 profile 选最快的。

### 1.2 cuBLASLt vs cuBLAS

| 维度 | cuBLAS | **cuBLASLt** |
|:--|:--|:--|
| API 风格 | Fortran BLAS | **Descriptor-based** |
| 学习曲线 | 极低 | **中（要建 4 个 descriptor）** |
| 融合能力 | 有限 | **强（多种 epilogue）** |
| INT8 GEMM | 支持但不便 | **一等公民** |
| FP8 GEMM (SM89+) | ❌ | **唯一路径** |
| Heuristic 选算法 | ❌ | **✅** |
| Layout 灵活性 | 中 | **高**（padded/tiled/vec）|
| 与 stream 集成 | ✅ | ✅ |
| Workspace | 隐式 | **显式**（你控制） |

### 1.3 一张图看清 cuBLASLt 在栈里的位置

```
┌──────────────────────────────────────────────────────────┐
│  PyTorch _scaled_mm / TensorRT / DeepSpeed / FT           │
├──────────────────────────────────────────────────────────┤
│  cuBLASLt（fused GEMM / INT8/FP8 / Heuristic）             │
│  cuBLAS（传统 BLAS API）    ← 二者共库、独立 API             │
├──────────────────────────────────────────────────────────┤
│  CUDA Runtime + Driver                                    │
├──────────────────────────────────────────────────────────┤
│  GPU 硬件（3060 / SM86 / Tensor Core / SM89+ FP8）          │
└──────────────────────────────────────────────────────────┘
```

**核心洞察**：cuBLASLt 是 NVIDIA 为**深度学习推理和量化**量身打造的 GEMM 门面。

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 好消息：cuBLASLt 随 CUDA Toolkit 自带

- 头文件：`<cuda>/include/cublasLt.h`
- 链接：`-lcublasLt`（Windows 上 `cublasLt64_12.dll`）

### 2.2 一步验证：hello_cublaslt.cu（简化版）

```cpp
#include <cublasLt.h>
#include <cuda_runtime.h>
#include <iostream>

int main() {
    int M=1024, N=1024, K=1024;
    float *dA,*dB,*dC;
    cudaMalloc(&dA, M*K*4); cudaMalloc(&dB, K*N*4); cudaMalloc(&dC, M*N*4);
    cudaMemset(dA, 1, M*K*4); cudaMemset(dB, 1, K*N*4);

    cublasLtHandle_t lt; cublasLtCreate(&lt);

    // 1. MatmulDesc（描述"这次 GEMM"）
    cublasLtMatmulDesc_t md;
    cublasLtMatmulDescCreate(&md, CUBLAS_COMPUTE_32F, CUDA_R_32F);
    cublasOperation_t opN = CUBLAS_OP_N;
    cublasLtMatmulDescSetAttribute(md, CUBLASLT_MATMUL_DESC_TRANSA, &opN, sizeof(opN));
    cublasLtMatmulDescSetAttribute(md, CUBLASLT_MATMUL_DESC_TRANSB, &opN, sizeof(opN));

    // 2. 三个 MatrixLayout（A/B/C）
    cublasLtMatrixLayout_t la,lb,lc;
    cublasLtMatrixLayoutCreate(&la, CUDA_R_32F, M, K, M);
    cublasLtMatrixLayoutCreate(&lb, CUDA_R_32F, K, N, K);
    cublasLtMatrixLayoutCreate(&lc, CUDA_R_32F, M, N, M);

    // 3. Workspace
    void* ws; size_t ws_size = 32*1024*1024;
    cudaMalloc(&ws, ws_size);

    float alpha=1.0f, beta=0.0f;
    cublasLtMatmul(lt, md,
        &alpha, dA, la, dB, lb,
        &beta,  dC, lc, dC, lc,
        nullptr,       // algo，null = 库自己选
        ws, ws_size, 0);

    cudaDeviceSynchronize();
    std::cout << "matmul OK\n";

    cublasLtMatmulDescDestroy(md);
    cublasLtMatrixLayoutDestroy(la);
    cublasLtMatrixLayoutDestroy(lb);
    cublasLtMatrixLayoutDestroy(lc);
    cublasLtDestroy(lt);
    cudaFree(dA); cudaFree(dB); cudaFree(dC); cudaFree(ws);
}
```

编译：

```bash
nvcc -O3 -std=c++17 -arch=sm_86 hello_cublaslt.cu -lcublasLt -o hello_cublaslt
./hello_cublaslt
```

### 2.3 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 忘 workspace 报错 | 部分算法要 workspace | 分配 32MB~256MB |
| Descriptor 忘 destroy | 内存泄漏 | 每个 create 对应 destroy |
| INT8 GEMM 结果乱 | scale 没设 | 用 `CUBLASLT_MATMUL_DESC_A_SCALE_POINTER` |
| 找不到 `-lcublasLt` | 拼错 | 是 `cublasLt` 不是 `cublaslt` |
| FP8 报不支持 | 硬件不够 | FP8 需 SM89+（3060 是 SM86，只能 FP16/INT8）|

---

## 3. cuBLASLt 的心智模型：4 个 Descriptor + Heuristic

### 3.1 4 个 Descriptor

一次 `cublasLtMatmul` 调用需要 4 个 descriptor：

| Descriptor | 描述 |
|:--|:--|
| **`cublasLtMatmulDesc_t`** | 这次 matmul 的运算属性（compute type、transpose、epilogue） |
| **`cublasLtMatrixLayout_t`（A）** | A 的 layout（dtype、rows、cols、ld、order） |
| **`cublasLtMatrixLayout_t`（B）** | 同上 |
| **`cublasLtMatrixLayout_t`（C/D）** | 同上 |

**"多写几行换灵活"**：cuBLAS 的 `sgemm` 一行搞定，cuBLASLt 得写 20 行来配 descriptor——**但你能表达的场景多 10 倍**。

### 3.2 Heuristic：让库告诉你候选算法

```cpp
cublasLtMatmulPreference_t pref;
cublasLtMatmulPreferenceCreate(&pref);
size_t ws_size = 32*1024*1024;
cublasLtMatmulPreferenceSetAttribute(pref,
    CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES, &ws_size, sizeof(ws_size));

cublasLtMatmulHeuristicResult_t results[8];
int returned = 0;
cublasLtMatmulAlgoGetHeuristic(lt, md, la, lb, lc, lc,
                               pref, 8, results, &returned);
// results[0..returned-1] 是候选算法，按预估性能排序
// 用 results[0].algo 传给 cublasLtMatmul 就是"库推荐最优"
```

**这就是 cuBLASLt 相对 cuBLAS 的核心价值**——**你可以枚举候选、跑 benchmark、选真正最快的**。

### 3.3 Workspace：显式管理

- 有些算法需要几 MB~几百 MB workspace（用于 split-K、pipeline buffer 等）；
- 你**必须显式分配**——库不会自己 malloc；
- 一次分配可以跨多次 matmul 复用。

---

## 4. 第一个程序：`cublasLtMatmul` 完整流程

见 2.2 节。**小白拆解**：

### 4.1 4 步走

1. **建 MatmulDesc**：`cublasLtMatmulDescCreate` + `SetAttribute(TRANSA/TRANSB/EPILOGUE)`；
2. **建 3 个 MatrixLayout**（A/B/C）：`cublasLtMatrixLayoutCreate(&, dtype, rows, cols, ld)`；
3. **分配 workspace**；
4. **调 `cublasLtMatmul`**（algo 可以传 null 让库自己选）。

### 4.2 6 个新手常见坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | 忘 destroy 每个 descriptor | 泄漏 | 每 create 配 destroy |
| 2 | Layout 参数（rows, cols, ld）搞反 | 结果错 | 严格 column-major，ld=行数 |
| 3 | Compute type 与 dtype 不匹配 | 报错 | FP16 in + FP32 compute 是常见组合 |
| 4 | Workspace 不够 | 报 CUBLAS_STATUS_NOT_SUPPORTED | 加大到 128MB |
| 5 | Epilogue 需要额外 pointer 没传 | 崩 | Bias 需 SetAttribute POINTER |
| 6 | Heuristic 返回 0 候选 | 没有可用算法 | 加大 workspace 或调整 layout |

---

## 5. Epilogue 融合：Bias / ReLU / GELU / Scaling 一把梭

**这是 cuBLASLt 相对 cuBLAS 的最大杀手锏**。

### 5.1 常见 Epilogue 值

| Epilogue | 语义 |
|:--|:--|
| `CUBLASLT_EPILOGUE_DEFAULT` | 纯 GEMM |
| `CUBLASLT_EPILOGUE_BIAS` | `D = A*B + bias` |
| `CUBLASLT_EPILOGUE_RELU` | `D = ReLU(A*B)` |
| `CUBLASLT_EPILOGUE_RELU_BIAS` | `D = ReLU(A*B + bias)` |
| `CUBLASLT_EPILOGUE_GELU` | `D = GELU(A*B)` |
| `CUBLASLT_EPILOGUE_GELU_BIAS` | `D = GELU(A*B + bias)` |
| `CUBLASLT_EPILOGUE_DRELU` | ReLU 的 backward |

### 5.2 用法

```cpp
cublasLtEpilogue_t epi = CUBLASLT_EPILOGUE_RELU_BIAS;
cublasLtMatmulDescSetAttribute(md, CUBLASLT_MATMUL_DESC_EPILOGUE,
                               &epi, sizeof(epi));

void* d_bias;   // 长度 = M（每列一个 bias）
cudaMalloc(&d_bias, M * sizeof(float));
cublasLtMatmulDescSetAttribute(md, CUBLASLT_MATMUL_DESC_BIAS_POINTER,
                               &d_bias, sizeof(d_bias));

cublasLtMatmul(lt, md, &alpha, dA, la, dB, lb, &beta, dC, lc, dC, lc,
               nullptr, ws, ws_size, 0);
// 一次调用完成 D = ReLU(A*B + bias)
```

**性能**：比 3 个 kernel（GEMM → +Bias → ReLU）快 20~40%（省 2 次显存往返）。

---

## 6. INT8 / FP8 量化 GEMM

### 6.1 INT8 GEMM

```cpp
cublasLtMatmulDescCreate(&md, CUBLAS_COMPUTE_32I, CUDA_R_32I);
// A/B: CUDA_R_8I（int8），C: CUDA_R_32I（int32 累加）

// 关键：INT8 需要 scale 反量化
float alpha_scale = ...;   // = scaleA * scaleB
cublasLtMatmul(lt, md, &alpha_scale, dA, la, dB, lb, &beta, dC, lc, dC, lc, ...);
```

**用途**：大模型推理量化——把 FP16 权重量化为 INT8，速度 2x、显存减半。

### 6.2 FP8 GEMM（H100 / SM89+）

3060 不支持 FP8，但了解 API：

```cpp
cublasLtMatmulDescCreate(&md, CUBLAS_COMPUTE_32F, CUDA_R_32F);
// A/B: CUDA_R_8F_E4M3 或 CUDA_R_8F_E5M2

// FP8 用 per-tensor 或 per-channel scale
cublasLtMatmulDescSetAttribute(md, CUBLASLT_MATMUL_DESC_A_SCALE_POINTER, &d_scale_A, ...);
cublasLtMatmulDescSetAttribute(md, CUBLASLT_MATMUL_DESC_B_SCALE_POINTER, &d_scale_B, ...);
```

**PyTorch 的 `torch._scaled_mm` 底层就是这套**。

---

## 7. Heuristic：自动选最优算法

### 7.1 完整流程

```cpp
// 1. 建 preference
cublasLtMatmulPreference_t pref;
cublasLtMatmulPreferenceCreate(&pref);
size_t ws = 128 * 1024 * 1024;
cublasLtMatmulPreferenceSetAttribute(pref,
    CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES, &ws, sizeof(ws));

// 2. 拿候选（最多 16 个）
constexpr int K = 16;
cublasLtMatmulHeuristicResult_t res[K]; int ret = 0;
cublasLtMatmulAlgoGetHeuristic(lt, md, la, lb, lc, lc, pref, K, res, &ret);

// 3. 逐个 benchmark 挑最快的
for (int i = 0; i < ret; ++i) {
    // 用 res[i].algo 跑一次，测时间
}
```

### 7.2 何时该 benchmark

- **形状固定、要跑很多次**（例如 Transformer 层）→ 值得 benchmark 存起来；
- **一次性 GEMM** → 用 `res[0]` 就行。

---

## 8. 性能分析与调优

### 8.1 三条铁律

1. **能融合就融合**——Epilogue 是免费性能；
2. **workspace 给够**——128MB 起步，某些算法要几百 MB；
3. **Heuristic + benchmark**——固定形状不测就是浪费。

### 8.2 Nsight Compute

看 `sm__inst_executed_pipe_tensor_op` 与 `dram__throughput`。融合 kernel 的 DRAM 用量应显著低于分开的三个 kernel。

---

## 9. cuBLASLt vs cuBLAS vs CUTLASS

| 需求 | cuBLAS | **cuBLASLt** | CUTLASS |
|:--|:--|:--|:--|
| 简单 FP32 GEMM | ✅ 一行 | ⚠️ 麻烦 | ⚠️ |
| Fused GEMM+Bias+Act | ❌ | **✅** | ✅ |
| INT8 / FP8 | ⚠️ | **✅ 首选** | ✅ |
| Heuristic 选算法 | ❌ | **✅** | ✅ |
| 完全自定义 epilogue | ❌ | ❌ | **✅** |
| 编写量 | 极少 | 中 | 多 |

**决策**：**首选 cuBLASLt**——除非只是简单 GEMM（用 cuBLAS）或要极致自定义（用 CUTLASS）。

---

## 10. 学习路线图（1~2 周）

- **Day 1~3**：hello_cublaslt，4 个 descriptor 建通 FP32 GEMM；
- **Day 4~5**：Epilogue 融合（Bias/ReLU/GELU）；
- **Day 6~8**：INT8 GEMM + scale 反量化，与 cuBLAS 性能对比；
- **Day 9~10**：Heuristic + benchmark，选最优算法；
- **Day 11~14**：接入 PyTorch `_scaled_mm` 或写自定义融合层。

---

## 11. 精选资源与踩坑清单

### 11.1 必读资源

| 资源 | 链接 |
|:--|:--|
| cuBLASLt 官方文档 | <https://docs.nvidia.com/cuda/cublas/index.html#cublasltmatmul> |
| CUDA Samples: cuBLASLt | `<CUDA>/samples` 里 `LtSgemm`, `LtIgemmTensor` 等 |
| PyTorch `_scaled_mm` 源码 | ATen 里搜 `scaled_mm` |
| TensorRT INT8 GEMM 参考 | TensorRT 官方文档 |

### 11.2 踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| Layout ld 错 | column-major 假设 | ld = rows |
| workspace OOM | 分配太大 | 128MB 起，按需增 |
| Bias 未生效 | 忘 SetAttribute POINTER | 补上 |
| INT8 结果爆炸 | scale 没设 | A/B/D scale 全部要设 |
| Heuristic 返回 0 | 组合不支持 | 换 dtype / layout |
| 反复建 descriptor 慢 | 重用不够 | 描述符复用 |
| Windows 不能调 stream | dll 冲突 | 单一 CUDA 版本 |
| GELU 数值差 | tanh vs erf 版本 | 两种 GELU 都有，看文档 |

### 11.3 一句话总结

> **cuBLASLt = "cuBLAS 的现代版本"**——用 Descriptor 换灵活、用 Epilogue 换融合、用 Heuristic 换性能透明。**FP8/INT8 量化推理的官方标准答案**，学它是从"能用 GEMM" → "会用融合 GEMM"的关键一步。

---

**祝你写出 FP16+Bias+GELU 一把梭的高性能推理内核。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
