# cuDNN 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：搞**深度学习推理/训练**、写**C++/CUDA 神经网络推理引擎**（不用 PyTorch 时）、想**在 GPU 上极致优化卷积/RNN/Attention** 的程序员。已经写过基本 CUDA、会用 cuBLAS 更好。
> **目标**：1~2 周内，从"用 cuDNN v8 Graph API 跑第一个 Conv2D"到"能自定义 fused Conv+Bias+ReLU、能用 Frontend API 表达 Attention、能给 3060 打到 cuDNN benchmark 的 90%+"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1** + cuDNN **9.x**（需单独下载）+ C++17。

---

## 目录

- [0. 写在最前：为什么要学 cuDNN？](#0-写在最前为什么要学-cudnn)
- [1. cuDNN 是什么：一句话讲清 vs cuBLAS / vs PyTorch](#1-cudnn-是什么一句话讲清-vs-cublas--vs-pytorch)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. cuDNN 的心智模型：Legacy vs v8 Graph vs Frontend API](#3-cudnn-的心智模型legacy-vs-v8-graph-vs-frontend-api)
- [4. 第一个程序：卷积 Conv2D 完整流程](#4-第一个程序卷积-conv2d-完整流程)
- [5. Fused Conv + Bias + Activation](#5-fused-conv--bias--activation)
- [6. Attention 与 Fused MHA（cuDNN 9.x 亮点）](#6-attention-与-fused-mhacudnn-9x-亮点)
- [7. RNN / LSTM / GRU](#7-rnn--lstm--gru)
- [8. 性能分析与调优](#8-性能分析与调优)
- [9. cuDNN vs cuBLAS / CUTLASS / Triton](#9-cudnn-vs-cublas--cutlass--triton)
- [10. 学习路线图（1~2 周）](#10-学习路线图12-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 cuDNN？

你可能会问：**PyTorch 已经能跑卷积了，为什么还要碰 cuDNN？** 答案是三点：

1. **PyTorch 的 `nn.Conv2d` 底层就是 cuDNN**——学它 = 学 PyTorch 快在哪；
2. **C++ 推理引擎**（TensorRT / ONNX Runtime / TVM）内部大量用 cuDNN；
3. **cuDNN 是 NVIDIA 官方"深度学习原语"的极致优化实现**——手写卷积几乎不可能打赢。

### 0.1 一句话对比

| 场景 | 手写 CUDA 卷积 | **cuDNN** |
|:--|:--|:--|
| 3x3 Conv on 224×224×64 | 上千行 im2col+GEMM | **一次 Graph 调用** |
| 3060 Tensor Core 峰值 | 极难 | **默认打到 85~95%** |
| Fused Conv+Bias+ReLU | 3 个 kernel | **单个 cuDNN Graph** |
| Flash Attention | 学 CUTLASS/Triton | **cuDNN 9 内建支持** |

### 0.2 cuDNN 现在有多重要？

- **PyTorch / TensorFlow / MXNet / TensorRT / ONNX Runtime** 的核心引擎；
- **NVIDIA 每年更新一次大版本**，永远跟上最新硬件（Tensor Core / TMA / FP8）；
- **cuDNN 9.x 新增 Frontend Graph API**，Attention 一等公民；
- **写 C++ 推理引擎**几乎绕不开。

**一句话**：**cuDNN = "GPU 上深度学习原语的官方标准答案"**——学它 = 打开 C++ AI 推理的门。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **D1 入门** | 会用 v8 Legacy API 跑 Conv/Pool/Activation |
| **D2 熟练** | 会用 Graph API 拼 fused Conv+Bias+ReLU |
| **D3 高阶** | 会用 Frontend API 做 Attention / LayerNorm / MHA |
| **D4 专家** | 与 TensorRT/PyTorch 深度对接、benchmark 挑最优算法、跨版本迁移 |

**建议**：**3~5 天到 D1**（能替换 nn.Conv2d 手写）；**1~2 周到 D2/D3**（覆盖 95% 推理场景）。

---

## 1. cuDNN 是什么：一句话讲清 vs cuBLAS / vs PyTorch

### 1.1 cuDNN 的定义

> **cuDNN（CUDA Deep Neural Network library）= NVIDIA 官方的 GPU 深度学习原语库**。它把卷积、池化、归一化、激活、Attention、RNN 等 DL 常用算子做到硬件峰值。

关键三点：

1. **Handle-based**——`cudnnHandle_t`（同 cuBLAS）；
2. **Descriptor-heavy**——Tensor/Filter/Convolution 等各有 descriptor；
3. **算法可选**——同一个卷积可能有 10+ 种实现（IMPLICIT_GEMM / WINOGRAD / FFT），benchmark 挑最快。

### 1.2 cuDNN vs cuBLAS vs PyTorch

| 维度 | cuBLAS | **cuDNN** | PyTorch |
|:--|:--|:--|:--|
| 覆盖 | 线性代数 | **DL 原语** | 全套 DL 框架 |
| 语言 | C API | **C API** | Python + C++ |
| Handle | ✅ | ✅ | 内部封装 |
| 算子融合 | 有限 | **强（Graph API）** | 全 |
| 学习曲线 | 低 | 中 | 低 |
| 目标读者 | 数值计算 | **DL 推理工程师** | AI 应用开发者 |

### 1.3 一张图看清 cuDNN 在栈里的位置

```
┌──────────────────────────────────────────────────────────┐
│  PyTorch / TensorFlow / TensorRT / ONNX Runtime          │
├──────────────────────────────────────────────────────────┤
│  cuDNN（Conv/Pool/Norm/Attention/RNN 全套 DL 原语）        │
├──────────────────────────────────────────────────────────┤
│  cuBLAS / cuBLASLt（GEMM）  ← cuDNN 底下大量调用            │
├──────────────────────────────────────────────────────────┤
│  CUDA Runtime + Driver                                    │
├──────────────────────────────────────────────────────────┤
│  GPU 硬件（3060 / SM86 / Tensor Core）                     │
└──────────────────────────────────────────────────────────┘
```

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 需要单独下载（与 cuBLAS 不同）

cuDNN **不随 CUDA Toolkit 自带**，需单独下载：

1. 登录 <https://developer.nvidia.com/cudnn>（要 NVIDIA 账号，免费）；
2. 下载与 CUDA 12.1 匹配的 cuDNN 9.x；
3. 解压：
   - Linux：把 `include/*.h` 复制到 `/usr/local/cuda/include`，`lib/*.so` 到 `/usr/local/cuda/lib64`；
   - Windows：解压到 `<CUDA>\include`、`\lib\x64`、`\bin`；
4. 验证：`cat /usr/local/cuda/include/cudnn_version.h | grep CUDNN_MAJOR`。

### 2.2 一步验证：hello_cudnn.cu

```cpp
#include <cudnn.h>
#include <cuda_runtime.h>
#include <iostream>

int main() {
    cudnnHandle_t h;
    cudnnCreate(&h);
    std::cout << "cuDNN version: " << CUDNN_VERSION << "\n";
    cudnnDestroy(&h);
}
```

编译：

```bash
nvcc -O3 -std=c++17 -arch=sm_86 hello_cudnn.cu -lcudnn -o hello_cudnn
./hello_cudnn
# cuDNN version: 90xxx
```

### 2.3 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| `undefined reference cudnnCreate` | 忘 `-lcudnn` | 加链接 |
| `libcudnn.so.9 not found` | 库未安装或 PATH 不对 | 装 cuDNN 9.x、`LD_LIBRARY_PATH` 更新 |
| version mismatch | cuDNN 与 CUDA 版本不匹 | 官网选对版本 |
| Windows dll 找不到 | 忘 copy dll | 把 `<CUDA>\bin\cudnn*.dll` 加 PATH |
| Descriptor 泄漏 | 忘 destroy | 每 create 配 destroy |

---

## 3. cuDNN 的心智模型：Legacy vs v8 Graph vs Frontend API

cuDNN 有**三代 API**，理解它们的区别是入门第一步。

### 3.1 三代 API 一览

| API | 版本 | 心智 | 状态 |
|:--|:--|:--|:--|
| **Legacy API** | v1~v7 | 一个算子一个 API（`cudnnConvolutionForward`）| **v8 后不建议新项目用** |
| **v8 Graph API (C)** | v8+ | 用图（node/edge）描述计算 | 稳定，主流 |
| **Frontend API (C++)** | v8+ | C++ header-only，包装 Graph API | **cuDNN 9 主推**，最人性化 |

### 3.2 Legacy API 示例（老代码常见）

```cpp
cudnnConvolutionForward(handle,
    &alpha, xDesc, x,
    wDesc, w,
    convDesc, algo, workspace, ws_size,
    &beta, yDesc, y);
```

**特点**：每个 op 一个 API，无法融合。

### 3.3 v8 Graph 示例（推荐）

```cpp
// 用 Frontend C++ API 拼图
auto op = cudnn_frontend::OperationBuilder(CUDNN_BACKEND_OPERATION_CONVOLUTION_FORWARD_DESCRIPTOR)
              .setxDesc(x).setwDesc(w).setyDesc(y)
              .setcDesc(conv).build();

auto opGraph = cudnn_frontend::OperationGraphBuilder()
                   .setHandle(handle).setOperationGraph(1, &op)
                   .build();

// 拿 execution plan（自动选最优实现）
auto engine_configs = cudnn_frontend::get_heuristics_list<...>(...);
auto plan = cudnn_frontend::ExecutionPlanBuilder()
                .setHandle(handle).setEngineConfig(engine_configs[0])
                .build();

// 跑
cudnnBackendExecute(handle, plan.get_raw_desc(), variantPack);
```

**特点**：能表达 Conv+Bias+ReLU 融合、Attention 融合。

### 3.4 建议：新项目直接用 Frontend API

- 官方推荐（cuDNN 9 更是 Frontend 一等公民）；
- 能融合、能表达 Attention；
- 是 header-only C++ 库，跟着 cuDNN 一起发。

---

## 4. 第一个程序：卷积 Conv2D 完整流程

### 4.1 用 Frontend API 跑一个 3x3 Conv

```cpp
// 概念代码（省略 Frontend include）
int N=1, C=3, H=224, W=224, K=64, R=3, S=3;
// 输入 x [N,C,H,W]、权重 w [K,C,R,S]、输出 y [N,K,H',W']

auto xTensor = cudnn_frontend::TensorBuilder()
    .setDim(4, {N,C,H,W}).setDataType(CUDNN_DATA_HALF)
    .setId('x').build();
auto wTensor = cudnn_frontend::TensorBuilder()
    .setDim(4, {K,C,R,S}).setDataType(CUDNN_DATA_HALF)
    .setId('w').build();
auto yTensor = cudnn_frontend::TensorBuilder()
    .setDim(4, {N,K,H,W}).setDataType(CUDNN_DATA_HALF)
    .setId('y').build();

auto conv = cudnn_frontend::ConvDescBuilder()
    .setStride(2, {1,1}).setPadding(2, {1,1}).setDilation(2, {1,1})
    .build();

auto op = cudnn_frontend::OperationBuilder(CUDNN_BACKEND_OPERATION_CONVOLUTION_FORWARD_DESCRIPTOR)
    .setxDesc(xTensor).setwDesc(wTensor).setyDesc(yTensor)
    .setcDesc(conv).build();

// ... 建 graph -> heuristic -> execute
```

### 4.2 小白版：先用 Legacy API 快速跑通

新手可先用 Legacy API 快速跑通再升级：

```cpp
cudnnTensorDescriptor_t xDesc, yDesc;
cudnnFilterDescriptor_t wDesc;
cudnnConvolutionDescriptor_t convDesc;

cudnnCreateTensorDescriptor(&xDesc);
cudnnSetTensor4dDescriptor(xDesc, CUDNN_TENSOR_NHWC, CUDNN_DATA_HALF, N, C, H, W);
// 同理 y, w
cudnnSetConvolution2dDescriptor(convDesc, /*pad*/1,1, /*stride*/1,1, /*dilation*/1,1,
                                CUDNN_CROSS_CORRELATION, CUDNN_DATA_HALF);
cudnnSetConvolutionMathType(convDesc, CUDNN_TENSOR_OP_MATH);  // ⚡ 走 Tensor Core

// 选 algo
cudnnConvolutionFwdAlgoPerf_t perf[8]; int ret;
cudnnFindConvolutionForwardAlgorithm(h, xDesc, wDesc, convDesc, yDesc,
                                     8, &ret, perf);

// 分配 workspace
size_t ws_size = perf[0].memory;
void* ws; cudaMalloc(&ws, ws_size);

float alpha=1.0f, beta=0.0f;
cudnnConvolutionForward(h, &alpha, xDesc, dx, wDesc, dw,
                        convDesc, perf[0].algo, ws, ws_size,
                        &beta, yDesc, dy);
```

### 4.3 6 个新手常见坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | NCHW vs NHWC 混 | 结果乱或性能差 | Ampere 上 NHWC 更快，一致选一种 |
| 2 | 未开 TENSOR_OP_MATH | 不走 Tensor Core | `cudnnSetConvolutionMathType` |
| 3 | Workspace 不够 | 崩 | 用 `FindAlgorithm` 拿准确大小 |
| 4 | Descriptor 未 destroy | 泄漏 | 全部要 destroy |
| 5 | pad/stride 顺序错 | shape 错 | 严格看文档：pad_h, pad_w, stride_h, stride_w |
| 6 | 版本 API 混用 | 编译错 | 一个项目统一用 Frontend 或 Legacy |

---

## 5. Fused Conv + Bias + Activation

Legacy API 用 `cudnnConvolutionBiasActivationForward`：

```cpp
cudnnConvolutionBiasActivationForward(h,
    &alpha1, xDesc, x, wDesc, w, convDesc, algo, ws, ws_size,
    &alpha2, /*z=*/zDesc, z,     // 可选残差
    biasDesc, bias, activationDesc,
    yDesc, y);
// 一次 kernel 完成 y = Activation(alpha1*Conv(x,w) + alpha2*z + bias)
```

**性能**：比 3 个 kernel 快 30~50%。

Frontend Graph API 更灵活，可以组合任意算子。

---

## 6. Attention 与 Fused MHA（cuDNN 9.x 亮点）

**cuDNN 9 的杀手锏**：官方 fused MHA（multi-head attention），支持 flash attention 风格：

```cpp
// 用 Frontend API 拼 attention graph
// Q, K, V, mask, dropout, causal 都作为节点
// cuDNN 内部自动选 Flash Attention 2 或 3 实现
```

**性能**：3060 上 fused MHA 比 cuBLAS 手工凑快 3~5x，与 xformers/flash-attn 接近。

**PyTorch `F.scaled_dot_product_attention` 现在默认调 cuDNN Attention**（后端之一）。

---

## 7. RNN / LSTM / GRU

cuDNN 提供 `cudnnRNNForward / Backward`，历史悠久：

```cpp
cudnnRNNDescriptor_t rnnDesc;
cudnnSetRNNDescriptor_v8(rnnDesc, algo,
    CUDNN_LSTM, CUDNN_RNN_DOUBLE_BIAS,
    CUDNN_UNIDIRECTIONAL, CUDNN_LINEAR_INPUT,
    dataType, mathPrec, mathType,
    inputSize, hiddenSize, projSize, numLayers,
    dropoutDesc, auxFlags);
```

**注意**：Transformer 兴起后 RNN 不再热，但金融时序、语音识别、老模型迁移仍会用。

---

## 8. 性能分析与调优

### 8.1 三条铁律

1. **用 NHWC layout + FP16 + Tensor Core**——Ampere 组合拳；
2. **用 `FindAlgorithm` 而非 `GetAlgorithm`**：前者真实跑测，后者是启发式估计；
3. **融合能融合的**——Conv+Bias+ReLU 别分三次。

### 8.2 用 Nsight

```bash
ncu --set full ./hello_cudnn
```

看 `sm__inst_executed_pipe_tensor_op` 是否非零；DRAM 是否被融合 kernel 减少。

---

## 9. cuDNN vs cuBLAS / CUTLASS / Triton

| 需求 | cuBLAS | **cuDNN** | CUTLASS | Triton |
|:--|:--|:--|:--|:--|
| 卷积 | ❌（自己 im2col+GEMM）| **✅ 首选** | ✅ 例子 | ✅ 例子 |
| Attention | ❌ | **✅ (v9)** | ✅ | ✅ |
| RNN | ❌ | **✅ 唯一便利** | ❌ | ❌ |
| 自定义算子 | ⚠️ | 有限 | **✅** | **✅** |

---

## 10. 学习路线图（1~2 周）

- **Day 1~3**：装好 cuDNN，Legacy API 跑通 Conv2D；
- **Day 4~6**：用 Frontend API 拼 Conv+Bias+ReLU 融合；
- **Day 7~10**：Fused MHA（cuDNN 9），对比 flash-attn；
- **Day 11~14**：接入 TensorRT 或写自定义 C++ 推理引擎。

---

## 11. 精选资源与踩坑清单

### 11.1 必读

| 资源 | 链接 |
|:--|:--|
| cuDNN 官方文档 | <https://docs.nvidia.com/deeplearning/cudnn/> |
| cudnn-frontend GitHub | <https://github.com/NVIDIA/cudnn-frontend> |
| CUDA Samples: cuDNN | `<CUDA>/samples/4_CUDA_Libraries/` |
| PyTorch cuDNN 后端源码 | pytorch 里搜 `cudnn/Conv` |

### 11.2 踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| Conv 慢 | NCHW + FP32 | 换 NHWC + FP16 |
| 内存爆 | Workspace 巨大 | limit 或换 algo |
| 结果差 | Bias 未加或加错位置 | 用 fused API |
| Attention 版本不支持 | cuDNN < 9 | 升级 |
| Legacy 和 Frontend 混用崩 | 生命周期 | 二选一 |
| Windows 缺 dll | 版本不匹 | 严格匹配 CUDA 12.1 + cuDNN 9.x |

### 11.3 一句话总结

> **cuDNN = "GPU 上深度学习原语的官方标准答案"**。Conv / Attention / RNN 三大件的极致优化实现，PyTorch/TensorFlow 后端。**Frontend API 是未来**，学它 = 打开 C++ AI 推理的门。

---

**祝你写出打到 cuDNN benchmark 的自研推理引擎。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
