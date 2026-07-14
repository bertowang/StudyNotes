# cuSOLVER 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：搞**科学计算、有限元、CFD、优化求解器、机器人 IK、SLAM、量化金融**的 C++/CUDA 程序员，用过 LAPACK / Eigen，需要**在 GPU 上做线性方程求解、特征值、SVD、Cholesky/LU/QR 分解**。
> **目标**：1~2 周内，从"用 cuSOLVER dense API 解 `Ax=b`"到"能做 SVD/特征值分解、能用 cusolverSp 求解稀疏线性系统、能对接 Eigen / PETSc"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1**（cuSOLVER 随 CUDA Toolkit 自带）+ C++17。

---

## 目录

- [0. 写在最前：为什么要学 cuSOLVER？](#0-写在最前为什么要学-cusolver)
- [1. cuSOLVER 是什么：一句话讲清 vs LAPACK / vs Eigen](#1-cusolver-是什么一句话讲清-vs-lapack--vs-eigen)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. cuSOLVER 三大子库：Dense / Sparse / Refactor](#3-cusolver-三大子库dense--sparse--refactor)
- [4. 第一个程序：`cusolverDnSgesv` 解 Ax=b](#4-第一个程序cusolverdnsgesv-解-axb)
- [5. LU / Cholesky / QR 分解](#5-lu--cholesky--qr-分解)
- [6. SVD / 特征值 / 特征向量](#6-svd--特征值--特征向量)
- [7. Sparse Solver：稀疏线性系统直接/迭代求解](#7-sparse-solver稀疏线性系统直接迭代求解)
- [8. 性能分析与调优](#8-性能分析与调优)
- [9. cuSOLVER vs LAPACK / vs Eigen / vs PETSc](#9-cusolver-vs-lapack--vs-eigen--vs-petsc)
- [10. 学习路线图（1~2 周）](#10-学习路线图12-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 cuSOLVER？

**LAPACK** 是数值线性代数世界的标准（1992 年出，至今没被替代），但它是 CPU 库。GPU 上求解 `Ax=b` / SVD / eig 是 HPC 与 AI 的基础运算，**cuSOLVER = NVIDIA 官方 GPU 版 LAPACK + 稀疏求解器**。

### 0.1 一句话对比

| 场景 | LAPACK/Eigen (CPU) | **cuSOLVER (GPU)** |
|:--|:--|:--|
| 5000×5000 dense LU | ~5 秒 | **~200 ms** |
| 10⁶×10⁶ 稀疏 Ax=b | 分钟级 | **秒级** |
| 大矩阵 SVD | 极慢 | **数秒** |
| 与 cuBLAS/cuSPARSE 集成 | 需拷贝回 CPU | **同 GPU 显存** |

### 0.2 cuSOLVER 现在有多重要？

- **CUDA Toolkit 自带**；
- **CFD / FEM / 有限元 / 优化 / Kalman 滤波 / 机器人 IK** 的核心；
- **PyTorch `torch.linalg.solve/svd/eig`** 底层用它；
- **量化金融的协方差分解、期权定价**；
- **推荐系统的矩阵分解 / PCA**；
- **稀疏部分**与 cuSPARSE 强强联合，PETSc / Trilinos 用它做 GPU 后端。

**一句话**：**cuSOLVER = GPU 上做线性代数求解的官方标准答案**——HPC / 数值仿真 / AI 底层都用。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **So1 入门** | 会 `cusolverDnSgesv / getrf / geqrf` 解一般方程 |
| **So2 熟练** | 会 SVD / eig / Cholesky，会 workspace 两步查询 |
| **So3 高阶** | 会 sparse solver，会 refactor（多次求解同结构不同数值） |
| **So4 专家** | 与 cuBLAS/cuSPARSE 混用，写自定义预条件，多 GPU 求解 |

**建议**：**3~5 天到 So1**，**1~2 周到 So2/So3**（覆盖 90% 生产场景）。

---

## 1. cuSOLVER 是什么：一句话讲清 vs LAPACK / vs Eigen

### 1.1 cuSOLVER 的定义

> **cuSOLVER = NVIDIA 官方 CUDA 版 LAPACK + 稀疏求解器套件**。三个子库：**cusolverDn**（Dense）、**cusolverSp**（Sparse）、**cusolverRf**（Refactor，重复分解加速）。API 命名基本对齐 LAPACK（`getrf`, `potrf`, `geqrf`, `gesvd`, `syevd` 等）。

关键三点：

1. **三子库**——按数据形态分：dense / sparse / refactor；
2. **Handle-based**——`cusolverDnHandle_t` / `cusolverSpHandle_t`；
3. **Workspace 两步查询**——先算需要多少 workspace，再分配再跑（同 cuBLASLt / cuSPARSE 惯例）。

### 1.2 cuSOLVER vs LAPACK vs Eigen vs PETSc

| 维度 | LAPACK | Eigen | PETSc | **cuSOLVER** |
|:--|:--|:--|:--|:--|
| 位置 | CPU | CPU (header-only) | CPU + GPU | **GPU** |
| Dense | ✅ | ✅ | 部分 | **✅ (Dn)** |
| Sparse | ⚠️（LAPACK 无）| ⚠️ | ✅ | **✅ (Sp)** |
| API 心智 | Fortran BLAS | STL-like | 面向对象 | **LAPACK-like** |
| 与 cuBLAS 无缝 | ❌ | ❌ | 部分 | **✅** |

### 1.3 一张图看清 cuSOLVER 在栈里的位置

```
┌──────────────────────────────────────────────────────────┐
│  PyTorch linalg / MATLAB GPU / SciPy(via CuPy)            │
│  PETSc GPU / Trilinos-GPU / 有限元求解器                    │
├──────────────────────────────────────────────────────────┤
│  cuSOLVER                                                 │
│  ┌────────────┬───────────────┬──────────────────────┐    │
│  │ cusolverDn │ cusolverSp    │ cusolverRf           │    │
│  │ (Dense)    │ (Sparse)      │ (Refactor)           │    │
│  └────────────┴───────────────┴──────────────────────┘    │
├──────────────────────────────────────────────────────────┤
│  cuBLAS / cuSPARSE ← cuSOLVER 底下大量调用                 │
├──────────────────────────────────────────────────────────┤
│  CUDA Runtime + Driver                                    │
├──────────────────────────────────────────────────────────┤
│  GPU 硬件（3060 / SM86）                                    │
└──────────────────────────────────────────────────────────┘
```

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 好消息：cuSOLVER 随 CUDA Toolkit 自带

- 头文件：`<cuda>/include/cusolverDn.h`, `cusolverSp.h`, `cusolverRf.h`
- 链接：`-lcusolver`（还会隐式依赖 `-lcublas -lcusparse`）

### 2.2 一步验证：hello_cusolver.cu

```cpp
#include <cusolverDn.h>
#include <cuda_runtime.h>
#include <iostream>

int main() {
    cusolverDnHandle_t h;
    cusolverDnCreate(&h);
    int ver;
    cusolverGetVersion(&ver);
    std::cout << "cuSOLVER version: " << ver << "\n";
    cusolverDnDestroy(h);
}
```

编译：

```bash
nvcc -O3 -std=c++17 -arch=sm_86 hello_cusolver.cu -lcusolver -lcublas -lcusparse -o hello_cusolver
./hello_cusolver
```

### 2.3 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 找不到 `-lcusolver` | 拼错 | 是 `cusolver` |
| workspace 不足崩 | 忘查询 bufferSize | 两步调用 |
| Column-major 混淆 | LAPACK 遗产 | 记住 column-major |
| SVD 特别慢 | 大矩阵慢是正常 | 用 `gesvdj`(Jacobi) 或 `gesvda` (approx) |
| Sparse solver 结果错 | Index base 不一致 | 统一 0-based / 1-based |
| Ordering 差性能悬崖 | 稀疏矩阵未 reorder | 用 `cusolverSpXcsrsymamdHost` reorder |

---

## 3. cuSOLVER 三大子库：Dense / Sparse / Refactor

### 3.1 cusolverDn（Dense）

对**中小规模稠密矩阵**（几百到几万维）的经典分解与求解：

| API | 作用 | LAPACK 对应 |
|:--|:--|:--|
| `cusolverDnSgetrf / getrs` | LU 分解 + 求解 | `sgetrf/sgetrs` |
| `cusolverDnSpotrf / potrs` | Cholesky | `spotrf/spotrs` |
| `cusolverDnSgeqrf` | QR | `sgeqrf` |
| `cusolverDnSgesvd` | SVD（标准）| `sgesvd` |
| `cusolverDnSgesvdj` | SVD（Jacobi，大矩阵更快）| — |
| `cusolverDnSsyevd` | 对称特征值 | `ssyevd` |
| `cusolverDnSgesv` | 直接解 Ax=b（新 API 一步到位）| — |

### 3.2 cusolverSp（Sparse）

对**大规模稀疏矩阵**：

| API | 作用 |
|:--|:--|
| `cusolverSpScsrlsvchol` | Cholesky 直接求解 |
| `cusolverSpScsrlsvqr` | QR 直接求解 |
| `cusolverSpScsrlsvlu` | LU（部分稀疏结构）|
| Preconditioned CG (through cuSPARSE + cuSOLVER combo) | 迭代求解 |

### 3.3 cusolverRf（Refactor）

**同一稀疏结构、不同数值反复求解** 的加速：

- 第一次做符号 + 数值分解；
- 之后每次只做数值 refactor + 求解，速度快 10x+。

**场景**：牛顿法迭代里每步 Jacobian 结构不变、CFD 时间推进。

---

## 4. 第一个程序：`cusolverDnSgesv` 解 Ax=b

### 4.1 简化版代码

```cpp
#include <cusolverDn.h>
#include <cuda_runtime.h>
#include <iostream>

int main() {
    // 3×3 方程 A*x = b：
    //   [2 1 1] [x1]   [4]
    //   [1 3 2]*[x2] = [7]
    //   [1 0 0] [x3]   [1]
    const int N = 3;
    float h_A[9] = {2,1,1, 1,3,0, 1,2,0};   // column-major!
    float h_b[3] = {4, 7, 1};

    float *dA, *dB;
    int   *dIpiv, *dInfo;
    cudaMalloc(&dA, N*N*sizeof(float));
    cudaMalloc(&dB, N*sizeof(float));
    cudaMalloc(&dIpiv, N*sizeof(int));
    cudaMalloc(&dInfo, sizeof(int));
    cudaMemcpy(dA, h_A, N*N*sizeof(float), cudaMemcpyHostToDevice);
    cudaMemcpy(dB, h_b, N*sizeof(float),   cudaMemcpyHostToDevice);

    cusolverDnHandle_t h; cusolverDnCreate(&h);

    // 查 workspace
    int lwork = 0;
    cusolverDnSgetrf_bufferSize(h, N, N, dA, N, &lwork);
    float* dWork; cudaMalloc(&dWork, lwork*sizeof(float));

    // LU 分解
    cusolverDnSgetrf(h, N, N, dA, N, dWork, dIpiv, dInfo);
    // 求解
    cusolverDnSgetrs(h, CUBLAS_OP_N, N, 1, dA, N, dIpiv, dB, N, dInfo);

    float h_x[3];
    cudaMemcpy(h_x, dB, N*sizeof(float), cudaMemcpyDeviceToHost);
    std::cout << "x = " << h_x[0] << " " << h_x[1] << " " << h_x[2] << "\n";
}
```

**别忘了 column-major**（LAPACK 遗产，同 cuBLAS）。

### 4.2 6 个新手常见坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | column-major 处理错 | 结果错 | 严格 CM |
| 2 | 忘 buffer size 查询 | 崩 | 两步调用 |
| 3 | Info 未查 | 分解失败没发现 | `cudaMemcpy(&info, dInfo, ...)` |
| 4 | Ipiv 长度错 | 崩 | 长度 = min(M,N) |
| 5 | Sparse Solver Index base 错 | 结果乱 | 与 cuSPARSE 一致 |
| 6 | 小矩阵 GPU 比 CPU 慢 | GPU 优势看规模 | ≥ 1000×1000 才明显 |

---

## 5. LU / Cholesky / QR 分解

- **LU**：`getrf + getrs`——通用，稳；
- **Cholesky**：`potrf + potrs`——**对称正定专用，速度 2x LU**；
- **QR**：`geqrf`——用于最小二乘、无条件数问题。

**决策**：
- **对称正定**（协方差矩阵、Laplacian）→ Cholesky；
- **一般方阵** → LU；
- **矩形/最小二乘** → QR。

---

## 6. SVD / 特征值 / 特征向量

### 6.1 SVD

```cpp
cusolverDnSgesvdj(...);   // Jacobi 版，大矩阵快
```

**用途**：PCA / 推荐系统低秩分解 / 相机标定。

### 6.2 特征值

```cpp
cusolverDnSsyevd(...);    // 对称
```

**用途**：主成分分析、量子力学 Hamiltonian、结构模态分析。

---

## 7. Sparse Solver：稀疏线性系统直接/迭代求解

### 7.1 cusolverSp 直接求解

```cpp
cusolverSpScsrlsvchol(h, N, nnz, descrA,
    csrVals, csrRowPtr, csrColInd,
    b, /*tol=*/1e-6, /*reorder=*/1,
    x, &singularity);
```

**注意**：稀疏直接法只对**有限元规模**（≤ 百万维）可行；更大规模用**迭代法**（CG/GMRES）。

### 7.2 迭代法（自己拼）

cuSOLVER 没有开箱即用的 CG/GMRES，但**用 cuBLAS + cuSPARSE 组合**几十行就能写：

```
r = b - Ax
p = r
while (未收敛):
    Ap = A * p              (cusparseSpMV)
    alpha = (r,r) / (p, Ap) (cublasSdot)
    x = x + alpha * p        (cublasSaxpy)
    r_new = r - alpha * Ap
    beta = (r_new, r_new) / (r, r)
    p = r_new + beta * p
    r = r_new
```

---

## 8. 性能分析与调优

### 8.1 三条铁律

1. **Column-major 是遗产坑，一开始就习惯**；
2. **稀疏矩阵先 reorder**（AMD/METIS）能提速 5~10x；
3. **迭代法配预条件器**——不加 preconditioner 的 CG 收敛慢是常态。

### 8.2 Nsight

大 GEMM 组件通常 compute-bound（Tensor Core），稀疏部分 memory-bound。

---

## 9. cuSOLVER vs LAPACK / vs Eigen / vs PETSc

| 需求 | LAPACK | Eigen | PETSc | **cuSOLVER** |
|:--|:--|:--|:--|:--|
| 位置 | CPU | CPU | CPU + GPU | **GPU** |
| API 熟悉度 | 老 Fortran | C++ 优雅 | 面向对象 | LAPACK-like |
| 大规模稀疏 | ❌ | ⚠️ | ✅ | ✅ |
| GPU 加速 | ❌ | ❌ | 部分 | **✅** |

---

## 10. 学习路线图（1~2 周）

- **Day 1~3**：LU / Cholesky 解 Ax=b；
- **Day 4~6**：SVD + PCA 应用；
- **Day 7~9**：稀疏 solver + reorder；
- **Day 10~14**：CG/GMRES + preconditioner，实战 CFD 或 FEM。

---

## 11. 精选资源与踩坑清单

### 11.1 必读

| 资源 | 链接 |
|:--|:--|
| cuSOLVER 官方文档 | <https://docs.nvidia.com/cuda/cusolver/> |
| CUDA Samples | `<CUDA>/samples/4_CUDA_Libraries/` |
| SuiteSparse Matrix Collection | <https://sparse.tamu.edu/> |
| MAGMA（对比参考）| <https://icl.utk.edu/magma/> |

### 11.2 踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 结果错 | Column-major | 严格 CM |
| Info 非 0 未检查 | 分解失败没发现 | 每次拷回检查 |
| SVD 极慢 | 用标准 gesvd | 换 gesvdj |
| 稀疏解慢 | 未 reorder | AMD 排序 |
| 迭代不收敛 | 无 preconditioner | 加 ILU/IC |
| 与 cuBLAS 冲突 | Handle 混 | 明确各自 handle |

### 11.3 一句话总结

> **cuSOLVER = GPU 上做线性代数求解的官方标准答案**——LAPACK-like API，覆盖 dense + sparse。**HPC / CFD / 有限元 / 优化 / SLAM** 的必修课。

---

**祝你解好百万维稀疏线性系统。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
