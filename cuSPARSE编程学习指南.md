# cuSPARSE 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：写**图算法**（PageRank / BFS / SpMV）、**科学计算**（有限元 / CFD）、**推荐系统**（大规模稀疏 embedding）、**大模型稀疏化**的程序员。**数据大多是"绝大多数为 0"** 的稀疏矩阵/向量，用 dense GEMM 浪费显存和算力。
> **目标**：1~2 周内，从"用 `cusparseSpMV` 一次稀疏矩阵向量乘"到"能用 SpMM 做稀疏矩阵×稠密矩阵、能用 Blocked SpMM 加速、能对接 cuGraph / RAPIDS"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1**（cuSPARSE 随 CUDA Toolkit 自带）+ C++17。

---

## 目录

- [0. 写在最前：为什么要学 cuSPARSE？](#0-写在最前为什么要学-cusparse)
- [1. cuSPARSE 是什么：一句话讲清 vs cuBLAS](#1-cusparse-是什么一句话讲清-vs-cublas)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. 稀疏格式：CSR / CSC / COO / BSR / Blocked-Ellpack](#3-稀疏格式csr--csc--coo--bsr--blocked-ellpack)
- [4. 第一个程序：SpMV（稀疏矩阵 × 稠密向量）](#4-第一个程序spmv稀疏矩阵--稠密向量)
- [5. SpMM：稀疏 × 稠密矩阵](#5-spmm稀疏--稠密矩阵)
- [6. SpGEMM：稀疏 × 稀疏矩阵](#6-spgemm稀疏--稀疏矩阵)
- [7. 转置 / 三角求解 / 预处理器](#7-转置--三角求解--预处理器)
- [8. 性能分析与调优](#8-性能分析与调优)
- [9. cuSPARSE vs cuBLAS / cuSOLVER / cuGraph](#9-cusparse-vs-cublas--cusolver--cugraph)
- [10. 学习路线图（1~2 周）](#10-学习路线图12-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 cuSPARSE？

想象一张 100 万节点的社交网络图，邻接矩阵是 100 万 × 100 万——**用 dense 存要 8 TB**，用稀疏存只要 **几 GB**。稀疏是**大规模真实数据的默认形态**。

**cuSPARSE = NVIDIA 官方的稀疏矩阵/向量运算库**，是稀疏世界的 cuBLAS。

### 0.1 一句话对比

| 场景 | 用 cuBLAS（dense） | **用 cuSPARSE（sparse）** |
|:--|:--|:--|
| 100 万节点图的 PageRank | ❌ OOM | **✅ 秒级** |
| 有限元刚度矩阵求解 | ❌ 存不下 | **✅ 天然稀疏** |
| Embedding lookup（推荐系统） | ⚠️ 慢 | **✅ SpMM 加速** |
| 大模型稀疏权重推理 | 浪费 | **✅ 2:4 稀疏 + Tensor Core** |

### 0.2 cuSPARSE 现在有多重要？

- **CUDA Toolkit 自带**；
- **cuGraph / RAPIDS / DGL / PyG（图学习）** 的引擎；
- **PETSc / Trilinos（HPC 科学计算）** 的 GPU 后端；
- **大模型 2:4 结构化稀疏推理**（A100/H100 Tensor Core 支持）；
- **数据分析、有限元、量化交易**里普遍使用。

**一句话**：**cuSPARSE = GPU 上做大规模稀疏计算的官方标准答案**——图、科学计算、稀疏 AI 三大场景必修。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **S1 入门** | 理解 CSR / COO 格式，会用 `cusparseSpMV` |
| **S2 熟练** | 会 SpMM、格式转换、`cusparseSpMM_bufferSize` 两步调用 |
| **S3 高阶** | 会 SpGEMM、Blocked SpMM、结构化 2:4 稀疏 |
| **S4 专家** | 与 cuGraph / cuSOLVER / cuBLAS 混用，写自定义 SpMV kernel |

**建议**：**3~5 天到 S1**，**1~2 周到 S2/S3**（覆盖 90% 场景）。

---

## 1. cuSPARSE 是什么：一句话讲清 vs cuBLAS

### 1.1 cuSPARSE 的定义

> **cuSPARSE = NVIDIA 官方 CUDA 版稀疏线性代数库**。提供 SpMV / SpMM / SpGEMM / 三角求解 / 转置 / 格式转换等操作，支持 CSR / CSC / COO / BSR / Blocked-Ellpack 等常见稀疏格式。

关键三点：

1. **Descriptor-based 通用 API**（cuSPARSE 12 后统一）；
2. **多种格式**——CSR/COO 最常用，BSR/Blocked-Ellpack 是加速版；
3. **两步调用惯例**——先查 `bufferSize`，再分配 workspace，再跑。

### 1.2 cuSPARSE vs cuBLAS

| 维度 | cuBLAS | **cuSPARSE** |
|:--|:--|:--|
| 数据形态 | Dense 矩阵/向量 | **Sparse 矩阵 + Dense 向量/矩阵** |
| 内存效率 | O(M×N) | **O(nnz)（非零元素数）** |
| 常见运算 | GEMM / GEMV | **SpMV / SpMM / SpGEMM** |
| Tensor Core | ✅ | ⚠️（2:4 structured sparsity 支持） |
| 目标场景 | 数值计算/DL | **图 / HPC / 稀疏 AI** |

### 1.3 一张图看清 cuSPARSE 在栈里的位置

```
┌──────────────────────────────────────────────────────────┐
│  cuGraph / RAPIDS / DGL / PyG / PETSc / Trilinos          │
├──────────────────────────────────────────────────────────┤
│  cuSPARSE（SpMV / SpMM / SpGEMM / Solver）                │
├──────────────────────────────────────────────────────────┤
│  cuSOLVER（稀疏直接/迭代求解） cuBLAS（Dense 部分）         │
├──────────────────────────────────────────────────────────┤
│  CUDA Runtime + Driver                                    │
├──────────────────────────────────────────────────────────┤
│  GPU 硬件（3060 / SM86）                                    │
└──────────────────────────────────────────────────────────┘
```

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 好消息：cuSPARSE 随 CUDA Toolkit 自带

- 头文件：`<cuda>/include/cusparse.h`
- 链接：`-lcusparse`

### 2.2 一步验证：hello_cusparse.cu

```cpp
#include <cusparse.h>
#include <cuda_runtime.h>
#include <iostream>

int main() {
    cusparseHandle_t h;
    cusparseCreate(&h);
    int ver;
    cusparseGetVersion(h, &ver);
    std::cout << "cuSPARSE version: " << ver << "\n";
    cusparseDestroy(h);
}
```

编译：

```bash
nvcc -O3 -std=c++17 -arch=sm_86 hello_cusparse.cu -lcusparse -o hello_cusparse
./hello_cusparse
```

### 2.3 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 找不到 `-lcusparse` | 拼错 | 是 `cusparse` |
| API deprecated 警告 | 用了 legacy API | 换 generic API（12.x 首选）|
| SpMV 结果错 | Index base 混（0-based / 1-based） | `CUSPARSE_INDEX_BASE_ZERO` |
| Buffer 不足崩 | 忘先查 bufferSize | 两步调用 |
| Descriptor 泄漏 | 忘 destroy | 每 create 配 destroy |

---

## 3. 稀疏格式：CSR / CSC / COO / BSR / Blocked-Ellpack

### 3.1 CSR（Compressed Sparse Row）—— 最常用

存 3 个数组：
- `values[nnz]`：所有非零元素；
- `col_indices[nnz]`：每个非零元素的列号；
- `row_ptr[M+1]`：第 i 行的非零元素在 values 里的起止位置。

**示例**：矩阵 `[[1,0,2],[0,3,0],[4,5,0]]`
```
values      = [1, 2, 3, 4, 5]
col_indices = [0, 2, 1, 0, 1]
row_ptr     = [0, 2, 3, 5]     // 行 0: [0,2), 行 1: [2,3), 行 2: [3,5)
```

**优势**：按行访问快，SpMV 内存友好，是 GPU 稀疏的标配。

### 3.2 COO（Coordinate）—— 最简单

`(row, col, val)` 三元组数组。**易于构造、易于并行填充**，但 SpMV 需要归约到同一行。

### 3.3 CSC —— CSR 的转置

按列存。做 `A^T * x` 或 `x^T * A` 时快。

### 3.4 BSR（Blocked Sparse Row）

CSR 的分块版本：非零"块"（比如 4×4）而非单元素。**大规模有限元刚度矩阵、图形学**首选。

### 3.5 Blocked-Ellpack

CSR + 定长 + 分块 —— Ampere Sparse Tensor Core（2:4 稀疏）的专属格式。

---

## 4. 第一个程序：SpMV（稀疏矩阵 × 稠密向量）

### 4.1 完整代码

```cpp
#include <cusparse.h>
#include <cuda_runtime.h>
#include <iostream>

int main() {
    // A（3×3, CSR）：
    //   [[1, 0, 2],
    //    [0, 3, 0],
    //    [4, 5, 0]]
    int M=3, N=3, nnz=5;
    int   h_rowptr[]  = {0, 2, 3, 5};
    int   h_col[]     = {0, 2, 1, 0, 1};
    float h_vals[]    = {1, 2, 3, 4, 5};
    float h_x[]       = {1, 2, 3};    // 向量
    float h_y[3]      = {0};

    int   *dRP, *dCol;
    float *dVals, *dX, *dY;
    cudaMalloc(&dRP,  4*sizeof(int));    cudaMemcpy(dRP,  h_rowptr, 4*sizeof(int), cudaMemcpyHostToDevice);
    cudaMalloc(&dCol, 5*sizeof(int));    cudaMemcpy(dCol, h_col,    5*sizeof(int), cudaMemcpyHostToDevice);
    cudaMalloc(&dVals,5*sizeof(float));  cudaMemcpy(dVals,h_vals,   5*sizeof(float), cudaMemcpyHostToDevice);
    cudaMalloc(&dX,   3*sizeof(float));  cudaMemcpy(dX,   h_x,      3*sizeof(float), cudaMemcpyHostToDevice);
    cudaMalloc(&dY,   3*sizeof(float));

    cusparseHandle_t h; cusparseCreate(&h);

    // 建 SpMat（generic API，推荐）
    cusparseSpMatDescr_t matA;
    cusparseCreateCsr(&matA, M, N, nnz, dRP, dCol, dVals,
                      CUSPARSE_INDEX_32I, CUSPARSE_INDEX_32I,
                      CUSPARSE_INDEX_BASE_ZERO, CUDA_R_32F);

    cusparseDnVecDescr_t vecX, vecY;
    cusparseCreateDnVec(&vecX, N, dX, CUDA_R_32F);
    cusparseCreateDnVec(&vecY, M, dY, CUDA_R_32F);

    float alpha=1.0f, beta=0.0f;
    size_t bufSize = 0;
    cusparseSpMV_bufferSize(h, CUSPARSE_OPERATION_NON_TRANSPOSE,
        &alpha, matA, vecX, &beta, vecY, CUDA_R_32F,
        CUSPARSE_SPMV_ALG_DEFAULT, &bufSize);

    void* buf; cudaMalloc(&buf, bufSize);
    cusparseSpMV(h, CUSPARSE_OPERATION_NON_TRANSPOSE,
        &alpha, matA, vecX, &beta, vecY, CUDA_R_32F,
        CUSPARSE_SPMV_ALG_DEFAULT, buf);

    cudaMemcpy(h_y, dY, 3*sizeof(float), cudaMemcpyDeviceToHost);
    for (auto v : h_y) std::cout << v << " ";   // 期望：7 6 14
    std::cout << "\n";
}
```

### 4.2 逐段小白拆解

- **CSR 三数组**表示稀疏矩阵 A；
- **SpMat 描述符** 包装 A 的所有信息；
- **DnVec 描述符** 包装稠密向量；
- **两步 API**：先查 bufferSize，再分配 workspace，再跑；
- 计算 `y = alpha * A*x + beta * y`（同 GEMM 结构，但 A 是 sparse）。

### 4.3 6 个新手常见坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | Index base 混 | 结果错 | 统一 0-based |
| 2 | row_ptr 长度错 | 崩 | 长度 M+1 |
| 3 | 忘 bufferSize | 崩 | 两步调用 |
| 4 | dtype/index-type 不匹配 | 报错 | 严格对齐 API 签名 |
| 5 | 未 destroy descriptor | 泄漏 | 每 create 配 destroy |
| 6 | SpMV 慢在小矩阵 | GPU 优势看规模 | ≥ 10K×10K 才明显 |

---

## 5. SpMM：稀疏 × 稠密矩阵

```cpp
cusparseSpMM_bufferSize(...);
cusparseSpMM(h, opA, opB,
    &alpha, matA, matB, &beta, matC, CUDA_R_32F,
    CUSPARSE_SPMM_ALG_DEFAULT, buf);
// C[M×N] = A[M×K, sparse] * B[K×N, dense]
```

**场景**：GNN 消息传递（邻接矩阵 × 节点特征）、稀疏 Attention。

---

## 6. SpGEMM：稀疏 × 稀疏矩阵

**最难的一个**——输出规模未知，得两阶段：

```cpp
// 阶段 1：计算 nnz
cusparseSpGEMM_workEstimation(...);
// 阶段 2：真正计算
cusparseSpGEMM_compute(...);
```

**场景**：图算法里的 A²（两跳邻居）、代数多重网格法。

---

## 7. 转置 / 三角求解 / 预处理器

- `cusparseCsr2cscEx2`：CSR ↔ CSC；
- `cusparseSpSV / cusparseSpSM`：三角求解 `L*x = b`；
- `cusparseCreateCsrilu02Info` / `cusparseCreateCsric02Info`：不完全 LU / Cholesky 预处理（迭代法的加速器）。

---

## 8. 性能分析与调优

### 8.1 三条铁律

1. **CSR 是通用首选**，除非结构规整（BSR/Blocked-Ellpack 更快）；
2. **算法号别用 default 就完事**——固定形状挑最优（如 `CUSPARSE_SPMV_ALG_MERGE_PATH` 对不规则稀疏更好）；
3. **matrix sort 决定性能**——同行内 col 无序会拖慢。

### 8.2 Nsight

看 DRAM 带宽——SpMV 是访存 bound，能达 60%+ 峰值就算优秀。

---

## 9. cuSPARSE vs cuBLAS / cuSOLVER / cuGraph

| 需求 | cuBLAS | **cuSPARSE** | cuSOLVER | cuGraph |
|:--|:--|:--|:--|:--|
| Dense GEMM | ✅ | ❌ | 部分 | ❌ |
| Sparse MV/MM | ❌ | **✅** | 部分 | 内部用 |
| Sparse LU/Cholesky | ❌ | ⚠️ | **✅** | 内部用 |
| 图算法（PageRank）| ❌ | ⚠️（底层）| ❌ | **✅ 上层** |

---

## 10. 学习路线图（1~2 周）

- **Day 1~2**：CSR / COO 掌握，跑通 SpMV；
- **Day 3~5**：SpMM + 格式转换 + 排序；
- **Day 6~8**：SpGEMM + 三角求解；
- **Day 9~14**：接入图算法（PageRank）或有限元。

---

## 11. 精选资源与踩坑清单

### 11.1 必读

| 资源 | 链接 |
|:--|:--|
| cuSPARSE 官方文档 | <https://docs.nvidia.com/cuda/cusparse/> |
| CUDA Samples: cuSPARSE | `<CUDA>/samples/4_CUDA_Libraries/` |
| SuiteSparse Matrix Collection | <https://sparse.tamu.edu/>（真实稀疏矩阵测试集）|

### 11.2 踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 结果错 | Index base | 0-based 统一 |
| 慢 | col 未排序 | 用 `cusparseXcsrsort` |
| workspace 不够 | 忘查 | 两步调用 |
| SpGEMM 挂 | 忘 workEstimation | 两阶段严格执行 |
| 与 cuBLAS/cuSOLVER 混淆 | Descriptor 类型 | 严格区分 |
| Legacy API 弃用警告 | 老代码 | 迁到 generic API |

### 11.3 一句话总结

> **cuSPARSE = "GPU 上做大规模稀疏计算的官方标准答案"**——图、科学计算、稀疏 AI 三大场景必修。学它就是打开图算法 + HPC + 稀疏推理的门。

---

**祝你写出百万边规模的图算法。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
