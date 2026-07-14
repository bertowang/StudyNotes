# 面向 AI 的 CUDA 编程学习指南（Windows + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.1 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
> 
> **面向读者**：有 C/C++ 或 Python 基础、想切入 AI 底层加速（推理引擎、算子开发、模型训练加速）的程序员。
> **目标**：8~12 周内，从"能写第一个 kernel"到"能读懂/修改 PyTorch 自定义算子和 FlashAttention 级别的代码"。
> **本机环境**：Windows + NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1**。
>
> **📍 本文在整个知识体系中的位置**：这是**深度纵向指南**——专注 CUDA C++ 一条主线。如果你还没看过[《GPU 编程工具全景》](./GPU编程工具全景.md)，**强烈建议先花 1~2 小时读完那张地图**，确认 CUDA 是不是你现在最该学的工具；如果你的场景可以用 `torch.compile` / Triton / CuPy 一行解决，就不用啃 CUDA C++。**看完全景再回来精读本文，效率翻倍。**

---

## 目录

- [0. 写在最前：为什么学 CUDA？学到什么程度？](#0-写在最前为什么学-cuda学到什么程度)
- [1. 你的硬件：RTX 3060 + SM 8.6 到底意味着什么](#1-你的硬件rtx-3060--sm-86-到底意味着什么)
- [2. Windows 开发环境搭建（一次性搞定）](#2-windows-开发环境搭建一次性搞定)
- [3. CUDA 编程模型速通（先建立心智模型）](#3-cuda-编程模型速通先建立心智模型)
- [4. 第一个 Kernel：Hello CUDA / 向量加法](#4-第一个-kernelhello-cuda--向量加法)
- [5. 内存层次：CUDA 性能的 80% 都在这里](#5-内存层次cuda-性能的-80-都在这里)
- [6. AI 场景必修的三大 Kernel](#6-ai-场景必修的三大-kernel)
  - [6.1 GEMM（矩阵乘法）——一切的基石](#61-gemm矩阵乘法一切的基石)
  - [6.2 Reduction / Softmax——AI 里最常见的归约](#62-reduction--softmaxai-里最常见的归约)
  - [6.3 Element-wise / Fused 算子](#63-element-wise--fused-算子)
- [7. Tensor Core 与混合精度（AI 加速的核心武器）](#7-tensor-core-与混合精度ai-加速的核心武器)
- [8. 从"手写 Kernel"到"用好轮子"：cuBLAS / cuDNN / CUTLASS / Triton](#8-从手写-kernel到用好轮子cublas--cudnn--cutlass--triton)
- [9. 集成到 AI 框架：写一个 PyTorch 自定义 CUDA 算子](#9-集成到-ai-框架写一个-pytorch-自定义-cuda-算子)
- [10. 性能分析与调优工具链（Nsight 全家桶）](#10-性能分析与调优工具链nsight-全家桶)
- [11. 学习路线图（8~12 周）](#11-学习路线图812-周)
- [12. 精选资源与踩坑清单](#12-精选资源与踩坑清单)
- [📌 姊妹篇总入口：《GPU 编程工具全景》](./GPU编程工具全景.md)

---

## 0. 写在最前：为什么学 CUDA？学到什么程度？

### 0.1 学 CUDA 能解决什么问题？

作为程序员，直接调用 `torch.matmul` 就够了，为什么还要学 CUDA？因为在 AI 领域，**只要你想做以下任何一件事，就绕不开 CUDA**：

| 场景 | 只用 PyTorch/TensorFlow 够吗？ | 需要 CUDA 的原因 |
|:--|:--|:--|
| 训练/微调标准模型 | ✅ 够 | — |
| 实现论文里的**新算子**（例如 FlashAttention、RoPE 融合、MoE 路由） | ❌ 不够 | 框架里没有，或有但太慢 |
| **推理加速**（LLM 部署、TensorRT-LLM、vLLM） | ❌ 不够 | 需要看懂/改 kernel、KV cache、PagedAttention |
| **量化 / 稀疏 / 低比特**（W4A16、FP8、稀疏注意力） | ❌ 不够 | 需要写专用 kernel |
| **算子融合**降 latency（Element-wise + Norm + Activation） | ❌ 不够 | Python 层无法融合 |
| 读懂 **cuBLAS / cuDNN / CUTLASS / Triton / TensorRT** 源码 | ❌ 不够 | 全是 CUDA C++ / PTX |

**一句话**：会用框架 = AI 应用工程师；会写/调 Kernel = AI 基础设施工程师，也是当前市场最稀缺的岗位之一。

### 0.2 学到什么程度算"够用"？

按照难度分级：

| 级别 | 能力标志 | 典型岗位 |
|:--|:--|:--|
| **L1 入门** | 能写向量加、矩阵乘、reduction，理解 grid/block/thread | 应届/转岗准入 |
| **L2 熟练** | 会用 shared memory、warp shuffle，能优化到接近 cuBLAS 的 60~80% | AI 推理工程师 |
| **L3 高阶** | 会用 Tensor Core（WMMA/mma.sync）、CUTLASS，能写 fused kernel | 推理引擎/框架研发 |
| **L4 专家** | 能读改 CUTLASS/FlashAttention，用 PTX/SASS 分析瓶颈 | 编译器/深度优化 |

**建议**：程序员切入 AI 加速，**先冲到 L2，然后按需求推进 L3**。L4 是长期沉淀，不必一步到位。

### 0.3 本文与其他姊妹篇的分工

CUDA C++ 只是 GPU 编程栈里的一层。为避免你走弯路，这里先划清各份指南的边界——**本文只讲 CUDA C++ 核心内核编写**，其他工具都有独立深度指南：

| 你想做的事 | 本文能给你 | 应精读的姊妹篇 |
|:--|:--|:--|
| 手写 GEMM/Reduction/Softmax/LayerNorm | ✅ 第 4~7 章 | — |
| 用 Tensor Core（WMMA） | ✅ 第 7 章入门版 | 深挖 `mma.sync` 看 [PTX 汇编指南](./PTX%20%E6%B1%87%E7%BC%96%E7%BC%96%E7%A8%8B%E5%AD%A6%E4%B9%A0%E6%8C%87%E5%8D%97.md) |
| 用 Python DSL 快速写 kernel | ❌ | [Triton](./Triton编程学习指南.md) / [Numba](./Numba编程学习指南.md) / [CuPy](./CuPy编程学习指南.md) |
| 用高性能库（不重造轮子） | ⚠️ 第 8 章一句话简介 | [cuBLAS](./cuBLAS编程学习指南.md) / [cuDNN](./cuDNN编程学习指南.md) / [CUTLASS](./CUTLASS编程学习指南.md) |
| 集成到 PyTorch | ⚠️ 第 9 章最小例 | [PyTorch 自定义 CUDA 算子指南](./PyTorch自定义CUDA算子编程学习指南.md) |
| 性能分析与调优 | ⚠️ 第 10 章速通 | [Nsight 性能分析指南](./Nsight性能分析编程学习指南.md) |
| 复现 FlashAttention | ⚠️ 只讲背景 | [FlashAttention 源码指南](./FlashAttention源码编程学习指南.md) |
| LLM 推理部署 | ❌ | [vLLM](./vLLM编程学习指南.md) / [TensorRT-LLM](./TensorRT-LLM编程学习指南.md) / [SGLang](./SGLang编程学习指南.md) |
| 分布式训练 | ❌ | [大模型训练框架指南](./大模型训练框架编程学习指南.md) + [NCCL](./NCCL编程学习指南.md) |

> **完整的 33 份姊妹篇索引，请见 [《GPU 编程工具全景》0.3.2 节](./GPU编程工具全景.md#032-33-份指南总表按学习次序排列点击直达)。**

---

## 1. 你的硬件：RTX 3060 + SM 8.6 到底意味着什么

在开始写代码之前，先摸清你手里的这块卡——**它决定了你能用哪些特性**。

### 1.1 RTX 3060 关键规格

| 参数 | 数值 | 对 CUDA 编程的意义 |
|:--|:--|:--|
| 架构 | **Ampere GA106** | 支持第 3 代 Tensor Core、异步拷贝 (`cp.async`) |
| Compute Capability | **8.6** (`sm_86`) | 编译时 `-arch=sm_86`；FP16/BF16/TF32/INT8 Tensor Core 全支持 |
| SM 数量 | 28 个 | 并行度上限的粗略参考 |
| 每 SM 最大线程 | 1536 | 一个 SM 最多同时驻留 1536 个 thread |
| 每 SM 最大 Block | 16 | 一个 SM 最多驻留 16 个 block |
| 每 SM Shared Memory | 100 KB（可配置） | 共享内存优化空间 |
| 每 Block Shared Memory 上限 | 48 KB 默认 / 最高 99 KB（需 opt-in） | 大 tile 时要用 `cudaFuncSetAttribute` 提升 |
| Warp 大小 | **32** | NVIDIA 所有卡都是 32，写代码永远围绕 32 转 |
| 显存 | 12 GB GDDR6 | 训练小模型 / 推理 7B 量化模型完全够 |
| 显存带宽 | ~360 GB/s | 后面判断"访存瓶颈 vs 计算瓶颈"的关键 |
| FP32 峰值 | ~13 TFLOPS | — |
| FP16 Tensor Core 峰值 | ~51 TFLOPS（不含稀疏） | 训练/推理必须用 Tensor Core |

### 1.2 3060 上你能玩什么、玩不了什么

**✅ 完全能玩**：

- 手写所有基础 kernel（vec add、GEMM、reduction、softmax、layernorm、conv）
- 使用 **FP16 / BF16 / TF32 Tensor Core**（WMMA API、CUTLASS）
- 训练 <1B 参数小模型、微调 7B 模型（配 LoRA + 量化）
- 部署 7B~13B 量化 LLM（llama.cpp / vLLM / TensorRT-LLM）
- CUDA Graph、Streams、Multi-stream 并发

**⚠️ 受限**：

- **FP8 Tensor Core**：8.6 不支持（需要 Hopper `sm_90` 或 Ada `sm_89`），学习时用 FP16/BF16 代替
- **Thread Block Cluster / TMA**：这是 Hopper 特性，`sm_86` 没有
- **显存**：12 GB 训练 13B+ 全参数模型不够用

**结论**：3060 是**性价比极高的学习卡**——除了 FP8 和 Hopper 独占特性外，AI CUDA 编程 90% 的知识点都能在上面完整练完。

---

## 2. Windows 开发环境搭建（一次性搞定）

### 2.1 必装组件清单

| 组件 | 版本 | 说明 |
|:--|:--|:--|
| NVIDIA Driver | ≥ 531.xx（配 CUDA 12.1） | 已安装，`nvidia-smi` 能出结果即可 |
| CUDA Toolkit | **12.1**（已装） | 提供 `nvcc`、cuBLAS、cuDNN、Nsight |
| **Visual Studio 2022** | Community 即可 | **必须装 "C++ 桌面开发" workload**，`nvcc` 在 Windows 上依赖 MSVC |
| cuDNN | 匹配 CUDA 12.x | 训练/推理常用，可后装 |
| Python | 3.10 / 3.11 | 配 PyTorch，验证环境 & 写自定义算子 |
| PyTorch | 匹配 CUDA 12.1（`cu121`） | `pip install torch --index-url https://download.pytorch.org/whl/cu121` |
| Nsight Systems | 随 CUDA 附带 | 系统级性能分析 |
| Nsight Compute | 随 CUDA 附带 | Kernel 级性能分析（**最重要**） |
| VS Code + C/C++ 插件 | 最新 | 日常写代码更顺手 |

### 2.2 环境验证脚本

在 PowerShell 中依次运行，确认每一步都 OK：

```powershell
# 1. 驱动 + 显卡识别
nvidia-smi

# 2. CUDA 编译器
nvcc --version

# 3. cuBLAS 头文件是否可见（返回路径即可）
where cublas.h  # 如果没有，去 CUDA_PATH\include 下确认

# 4. Python + PyTorch 能识别 GPU
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0))"
```

**期望输出**：
```
2.x.x+cu121 True NVIDIA GeForce RTX 3060 (8, 6)
```

### 2.3 命令行编译第一个程序（脱离 IDE）

Windows 下 `nvcc` 需要 MSVC 环境变量，最省心的做法是打开 **"x64 Native Tools Command Prompt for VS 2022"**，然后按以下三步走。

#### Step 1：新建 `hello.cu`

在任意目录（例如 `D:\cuda-lab\`）新建文件 `hello.cu`，内容如下——这是能一次跑通、并覆盖 CUDA 最小语法要素（`__global__` kernel、`<<<grid, block>>>` 启动、Host↔Device 同步）的**最短程序**：

```cpp
// hello.cu —— 最小可运行 CUDA 程序
#include <cstdio>
#include <cuda_runtime.h>

// __global__ 表示：Host 调用、Device 执行的 kernel
__global__ void hello_kernel() {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    printf("Hello CUDA from thread %d  (block %d, thread %d)\n",
           tid, blockIdx.x, threadIdx.x);
}

int main() {
    // 打印一下识别到的设备，顺便验证运行时可用
    int dev = 0;
    cudaDeviceProp prop{};
    cudaGetDeviceProperties(&prop, dev);
    printf("Device: %s  (SM %d.%d, %d SMs)\n",
           prop.name, prop.major, prop.minor, prop.multiProcessorCount);

    // 启动配置：2 个 block，每 block 4 个线程 —— 一共 8 个线程会各打印一行
    hello_kernel<<<2, 4>>>();

    // kernel launch 是异步的，必须同步等待 GPU 打印完成
    cudaError_t err = cudaDeviceSynchronize();
    if (err != cudaSuccess) {
        fprintf(stderr, "CUDA error: %s\n", cudaGetErrorString(err));
        return 1;
    }
    return 0;
}
```

#### Step 2：编译

```bat
nvcc -arch=sm_86 -O2 hello.cu -o hello.exe

nvcc -arch=sm_86 -O2   -ccbin "D:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Tools\MSVC\14.41.34120\bin\Hostx64\x64"    hello.cu -o hello.exe

```

**关键参数记住三个**：

- `-arch=sm_86`：为你的 3060 生成原生代码（不加会退回默认，性能可能受损）
- `-O2`：主机代码优化
- `-lineinfo`：调试/分析时加，让 Nsight Compute 显示源代码行号

#### Step 3：运行

```bat
hello.exe
```

**期望输出**（8 行 `Hello CUDA from thread ...` 的顺序**不保证**，这正是 GPU 并行的正常现象）：

```
Device: NVIDIA GeForce RTX 3060  (SM 8.6, 28 SMs)
Hello CUDA from thread 0  (block 0, thread 0)
Hello CUDA from thread 1  (block 0, thread 1)
Hello CUDA from thread 2  (block 0, thread 2)
Hello CUDA from thread 3  (block 0, thread 3)
Hello CUDA from thread 4  (block 1, thread 0)
Hello CUDA from thread 5  (block 1, thread 1)
Hello CUDA from thread 6  (block 1, thread 2)
Hello CUDA from thread 7  (block 1, thread 3)
```

只要看到设备名 + 8 行 Hello，就说明**驱动、CUDA Toolkit、MSVC、显卡**四方全部串通了，可以进入第 3 章。

> 💡 常见报错速查：
> - `nvcc fatal: Cannot find compiler 'cl.exe'` → 没在 **x64 Native Tools Command Prompt** 里跑；
> - kernel 完全没有输出但也没报错 → 忘了 `cudaDeviceSynchronize()`，`printf` 缓冲区还没 flush 主进程就退了；
> - 输出乱序 → **正常**，不同 block/warp 是并行执行的。

### 2.4 深入理解 `hello_kernel<<<2, 4>>>()`：CUDA 的两级并行模型

上面 `hello.cu` 里最诡异的一行是：

```cpp
hello_kernel<<<2, 4>>>();
```

这行代码看起来像 C++ 的模板语法，其实是 **CUDA 独有的"执行配置"(Execution Configuration)** 语法，也是理解 CUDA 编程模型的**第一把钥匙**。下面把它拆到最细。

#### 一句话概括

> 在 GPU 上启动 `hello_kernel` 这个核函数，一共开 **2 个线程块 (Block)**，每块里放 **4 个线程 (Thread)**，因此总共有 **2 × 4 = 8 个线程"同时"并行执行**这段代码。

#### ① 三尖括号 `<<< ... >>>` 的完整语法

`<<< ... >>>` 只能出现在 **`__global__` 核函数**的调用处，完整形式有 4 个参数：

```cpp
kernel<<< gridDim, blockDim, sharedMem, stream >>>(args);
```

| 参数 | 含义 | 本例中的值 |
|:--|:--|:--|
| `gridDim`  | **网格维度**：一个 Grid 里有多少个 Block | `2` → 2 个 Block |
| `blockDim` | **块维度**：一个 Block 里有多少个 Thread | `4` → 每块 4 个 Thread |
| `sharedMem`| 每块动态共享内存字节数（可选） | 省略，默认 `0` |
| `stream`   | 使用哪个 CUDA 流（可选） | 省略，默认 stream `0` |

所以 `<<<2, 4>>>` 就是最简形式：**2 个 block × 4 个 thread/block = 8 个线程**。

#### ② CUDA 的两级并行结构：Grid → Block → Thread

CUDA 把并行线程组织成一个**两级层次结构**：

```
Grid (网格, 一次 kernel 启动 = 一个 Grid)
├── Block 0            <-- 同 Block 内线程可共享 shared memory、可 __syncthreads() 同步
│   ├── Thread 0
│   ├── Thread 1
│   ├── Thread 2
│   └── Thread 3
└── Block 1
    ├── Thread 0
    ├── Thread 1
    ├── Thread 2
    └── Thread 3
```

两个关键事实：

- **同一 Block 内的线程**：跑在**同一个 SM (Streaming Multiprocessor)** 上，可以通过 `__shared__` 内存和 `__syncthreads()` 互相协作。
- **不同 Block 之间**：完全独立，执行顺序不确定，也**不能直接同步**——硬件可以自由地把它们分派到不同的 SM 上并行执行。这正是 CUDA "写一份代码，自动伸缩到不同规模 GPU"的秘诀。

> 更完整的四层结构（Grid → Block → Warp → Thread）留到 [第 3 章](#3-cuda-编程模型速通先建立心智模型) 讨论。Warp 是硬件真正的调度单位，暂时可以先把它理解为"Block 内每 32 个线程为一组"。

#### ③ 核函数内部如何"知道自己是谁"

kernel 里的这一行：

```cpp
int tid = blockIdx.x * blockDim.x + threadIdx.x;
```

用到了 CUDA 提供的 **4 个内置变量**，每个线程各自持有一份属于自己的值：

| 内置变量 | 含义 | 本例中的取值 |
|:--|:--|:--|
| `gridDim.x`  | Grid 里 Block 的数量  | `2` |
| `blockDim.x` | Block 里 Thread 的数量 | `4` |
| `blockIdx.x` | 当前线程所在 Block 的编号 | `0` 或 `1` |
| `threadIdx.x`| 当前线程在自己 Block 内的编号 | `0 ~ 3` |

`tid = blockIdx.x * blockDim.x + threadIdx.x` 就是把 `(块号, 块内号)` 拍平成一个**全局唯一的线程编号**。代入所有可能组合：

| blockIdx.x | threadIdx.x | tid = blockIdx.x × 4 + threadIdx.x |
|:--:|:--:|:--:|
| 0 | 0 | **0** |
| 0 | 1 | **1** |
| 0 | 2 | **2** |
| 0 | 3 | **3** |
| 1 | 0 | **4** |
| 1 | 1 | **5** |
| 1 | 2 | **6** |
| 1 | 3 | **7** |

**这就是 [Step 3](#step-3运行) 里看到 `thread 0 ~ 7` 共 8 行输出的来源。**

> ⚠️ **输出为什么可能乱序？** 8 个线程是**真正并行**执行的，`printf` 缓冲刷回 host 的顺序不保证。同一个 warp 内（32 线程一组）通常有序，但跨 block 一定是乱的——这是 GPU 并行的正常现象，不是 Bug。

#### ④ 为什么必须 `cudaDeviceSynchronize()`？

```cpp
hello_kernel<<<2, 4>>>();          // 【异步】提交给 GPU 后立即返回，CPU 继续往下走
cudaDeviceSynchronize();           // 【阻塞】等 GPU 真的把 kernel 跑完
```

CUDA 的 kernel 启动是**异步**的：CPU 只是把任务塞进 GPU 命令队列就走人。如果不 `cudaDeviceSynchronize()`，`main` 可能直接 `return 0` 把进程干掉，GPU 上的 `printf` 缓冲区还没来得及刷回宿主，你就"什么都看不到"了。**"没输出、没报错"** 的诡异现象几乎都是这个原因。

#### ⑤ `dim3` 三维扩展：为什么可以写成 `<<<grid, block>>>` 也可以写成三维？

`<<<gridDim, blockDim>>>` 里的两个参数其实都是 **`dim3` 类型**（三维向量）。你写的整数 `2` 和 `4` 会被隐式转换成 `dim3(2,1,1)` 和 `dim3(4,1,1)`。完整写法：

```cpp
dim3 grid (2, 1, 1);   // 也可简写为 dim3 grid(2);
dim3 block(4, 1, 1);   // 也可简写为 dim3 block(4);
hello_kernel<<<grid, block>>>();
```

之所以设计成三维，是为了方便处理 **2D 图像 / 3D 体数据**时直接用 `(x, y, z)` 索引像素/体素，避免手动展平。CV / 医学影像 / 物理仿真里非常常见。

#### ⑥ 实战里 `<<<gridDim, blockDim>>>` 怎么选？

`<<<2, 4>>>` 只是 Hello World，8 个线程对 GPU 而言小到可笑。真实项目里的经验法则：

- **`blockDim`（每块线程数）** 通常选 **128 / 256 / 512**，且必须是 **32 (warp 大小) 的整数倍**，否则会浪费执行单元。
- **`gridDim`（块数）** 一般根据数据规模计算，例如处理 `N` 个元素：

  ```cpp
  int threads = 256;
  int blocks  = (N + threads - 1) / threads;   // 向上取整
  kernel<<<blocks, threads>>>(...);
  ```

- 块数**远大于 SM 数量**（3060 有 28 个 SM）可以让硬件调度器隐藏访存延迟，这个指标叫 **Occupancy**，是 [第 5 章](#5-内存层次cuda-性能的-80-都在这里) 和 [第 10 章](#10-性能分析与调优工具链nsight-全家桶) 反复出现的关键词。

这个"如何算 blocks/threads"的模板，会在 [4.2 向量加法](#42-向量加法cuda-的-hello-world) 里再次出现——那是所有 CUDA 程序员都要背下来的 4 行 boilerplate。

---

## 3. CUDA 编程模型速通（先建立心智模型）

在写第一行代码之前，**先把这套心智模型刻进脑子**——CUDA 90% 的坑都源于对模型理解不到位。

### 3.1 四层并行结构：Grid → Block → Warp → Thread

[2.4 节](#24-深入理解-hello_kernel24-cuda-的两级并行模型) 里为讲清 `<<<2, 4>>>` 语法，我们只讲了 **Grid / Block / Thread 两级编程模型**。但硬件真正调度时会**多出一层 Warp**，形成 **"两级编程 + 四级执行"** 的分裂——这就是新手最容易翻车的地方，3.1 节一次讲透。

#### 3.1.0 先破一个误解：一张 GPU 卡上到底有几个 Grid？

> **Grid 数量与 GPU 硬件无关，只取决于你启动了多少次 kernel。** 每一次 `kernel<<<...>>>()` 调用 = 一个新 Grid。

**Grid 是软件逻辑单位，不是硬件槽位**——它更像 C++ 里的"一次函数调用"，本身不占硬件资源；**真正占资源的是它内部的 Block**。

**多个 Grid 可以同时存在**，常见三种场景：

- **多 Stream 并发**：`kernel_A<<<...,0,s1>>>` 和 `kernel_B<<<...,0,s2>>>` 同时在 s1、s2 上跑，只要 SM 资源够，两者的 block 会并发驻留（详见后文 Stream 章节）；
- **多进程共享（MPS / MIG）**：A100/H100 可切成最多 7 个"小 GPU"，各自跑独立 Grid；
- **训练循环**：PyTorch 一个 epoch 底层可能启动几万个 Grid，只是默认串行在一个 stream 里。

**Grid 与硬件资源的关系**：一个 SM 上可以同时驻留**来自不同 Grid 的 block**（只要寄存器/shared memory 够用）；一个 Grid 的 block 也会分布到多个 SM 上——Grid 和 SM 是 **多对多** 关系。

> 类比：C++ 程序视角只有一个 `main()`，但操作系统上同时跑着几百个进程各有自己的 `main()`。**Grid 之于 kernel 启动，就像 main 之于程序**——单次启动看只有一个，整张卡看可以有很多个。

#### 3.1.1 完整层次图

```
                        Grid (一次 kernel 启动 = 一个 Grid)
                       ┌───────────────────────────────────┐
                       │  Block(0,0)  Block(1,0) Block(2,0)│
                       │  Block(0,1)  Block(1,1)  ...      │  ← 数量任意大, 靠硬件调度
                       └───────────────────────────────────┘
                                       │
                       挑一个 Block 放大看内部：
                       ┌───────────────────────────────────┐
                       │  Warp 0  (Thread  0 ~  31)        │
                       │  Warp 1  (Thread 32 ~  63)        │  ← 一个 block 最多 1024
                       │  Warp 2  (Thread 64 ~  95)        │      线程 = 32 个 warp
                       │      ...                          │
                       └───────────────────────────────────┘
                                       │
                       挑一个 Warp 放大看内部：
                       ┌───────────────────────────────────┐
                       │  Thread 0  Thread 1  ...  Thread 31│  ← 32 个线程锁步执行
                       └───────────────────────────────────┘             (SIMT)
```

一句话对比编程模型与硬件模型：

| 视角 | 你在代码里写什么 | 硬件真正做什么 |
|:--|:--|:--|
| **编程模型** | Grid → Block → Thread（2 级，你决定 `<<<grid, block>>>`） | — |
| **硬件模型** | — | Grid → Block → **Warp** → Thread（4 级，Warp 由硬件自动切分） |

**Warp 是硬件自动生成的**：你写 `blockDim = 128`，硬件自动把它切成 `128 / 32 = 4` 个 warp，你不用管，但**必须知道**——因为几乎所有性能优化都围绕 warp 展开。

#### 3.1.2 SM：真正干活的硬件调度中枢

前面反复提到"SM 最多驻留 16 个 block、48 个 warp"这些数字，很多读者会一脸懵：**SM 到底是什么？它长什么样？block 是怎么"住进"SM 的？** 这一小节把 SM 从头到尾讲清楚，也是理解后续 Occupancy、性能调优的必要前提。

**① SM 是什么？——一句话定义**

> **SM (Streaming Multiprocessor，流式多处理器) 是 GPU 里真正执行指令的"硬件工厂"。一张 GPU 卡 = N 个 SM 的物理集合**（3060 有 28 个，A100 有 108 个，H100 有 132 个）。你写的每一个 kernel、每一个 block、每一条指令，最终都会被送到某个 SM 上执行。

**② 用类比一秒理解 SM**

| 类比对象 | 对应关系 |
|:--|:--|
| 🏭 **一张 GPU 卡** | 一座工业园区 |
| 🏗️ **一个 SM** | 园区里的一座**独立工厂**，麻雀虽小五脏俱全 |
| 👷 **一个 Block** | 被安排到某座工厂的**一整个施工队**，进去了就不换厂 |
| 🎽 **一个 Warp** | 施工队里的**一个 32 人班组**，动作永远整齐划一 |
| 💾 **Shared Memory** | 这座工厂**内部的白板**，只有本厂员工能读写 |
| 🌐 **Global Memory** | **园区外的大仓库**，任何工厂都能取，但取一次要坐半天车 |

**记住这个类比**——后面所有关于 SM 的细节都能一一对号入座。

**③ 一个 SM 内部到底有什么？（以 RTX 3060 / Ampere SM 8.6 为例）**

```
┌───────────────────── 一个 SM (Ampere) ─────────────────────┐
│                                                            │
│  ┌─── 4 个 Warp Scheduler ───┐   (每 cycle 从 48 个驻留     │
│  │  SubP0  SubP1 SubP2 SubP3 │    warp 里挑 4 个能跑的发射) │
│  └───────────────────────────┘                             │
│                                                            │
│  ┌─── 计算单元 (共 128 个 CUDA Core) ───┐                  │
│  │  FP32 x 128    INT32 x 64            │                  │
│  │  FP64 x 2      Tensor Core x 4       │  ← 真·搬砖工人   │
│  │  SFU x 4 (特殊函数, sin/exp/rsqrt)   │                  │
│  └──────────────────────────────────────┘                  │
│                                                            │
│  ┌─── 存储资源 ───┐                                        │
│  │ Registers: 65536 x 32-bit = 256 KB   ← 每线程私有       │
│  │ Shared Memory / L1 Cache: 128 KB     ← 全 SM 共享       │
│  │ Constant Cache / Tex Cache: 若干 KB  ← 只读特殊路径     │
│  └──────────────────────────────────────┘                  │
│                                                            │
│  最多驻留：16 个 Block / 48 个 Warp / 1536 个 Thread       │
└────────────────────────────────────────────────────────────┘

RTX 3060 每个 SM 最多可以"同时驻留"（reside）48 个 warp = 1536 个线程。
```

**关键要点**：
- **Warp Scheduler**：SM 的"排班员"，每个 cycle 从当前驻留的 warp 里挑出 ready 的 warp 发射指令。3060 每个 SM 有 **4 个 scheduler**，理论上每 cycle 能同时推进 4 个 warp；
- **CUDA Core**：真正做 FP32/INT32 加乘的执行单元，一个 warp 的 32 lane 在 CUDA Core 上锁步执行；
- **Tensor Core**：Ampere 每 SM 有 **4 个**，专做 4×4×4 或 16×8×16 的矩阵乘加，是深度学习性能的核心引擎（详见后文 [第 6 章](#6-tensor-core--混合精度)）；
- **寄存器堆**：**每个 SM 有 65536 个 32-bit 寄存器**，被驻留在这个 SM 上的**所有线程瓜分**。如果每个线程要 32 个寄存器，那 SM 最多能塞 `65536/32 = 2048` 个线程——但受 warp 上限 48 卡住，实际是 1536。

> ⚠️ **重要澄清："128 CUDA Core" 是"相加"还是"复用"？**
>
> 图里同时列出 `FP32×128 / INT32×64 / FP64×2 / Tensor Core×4 / SFU×4`，很容易误以为总数是 202——**并不是**。真实关系只有三条：
>
> 1. **"128 CUDA Core" = 128 条 FP32 主通道**（Ampere 白皮书的官方口径）。它内部由 **64 条纯 FP32 + 64 条 FP32/INT32 复用通道**拼成。
> 2. **INT32 的 64 = 复用**，不是额外增加。复用通道每 cycle 只能二选一：跑 FP32 或跑 INT32。
> 3. **Tensor Core / FP64 / SFU = 独立专用硬件**，不计入 128，可与 CUDA Core 并行工作。
>
> **性能推论（写 kernel 时会踩到）**：
>
> - kernel 里 FP32 和 INT32 同时大量出现时（例如 `a[i]*b[i]` 里 `i` 的地址算术是 INT32），INT32 会**挤占**复用通道，FP32 实际吞吐从 128 掉到 64——这就是 **"FP32/INT32 争用"**。
> - 缓解手段：**循环 unroll、把 index 编译期常量化**（模板参数 / `constexpr`），把 Datapath 让回给 FP32——这是 CUTLASS / cuBLAS 主循环的常规打法。
> - Tensor Core 与 CUDA Core **不打架**，可同时工作，因此现代 GEMM 会刻意让 Tensor Core 跑主乘、CUDA Core 跑 epilogue（bias/激活）做**双流水**。

**④ Block 是如何"住进"SM 的？——生命周期四步走**

```
     kernel<<<1024, 256>>>()   //  你启动了 1024 个 block
              │
              ▼
     ┌──── GigaThread Engine（全局调度器）────┐
     │  按 SM 空闲度 & 资源余量把 block 分派下去 │
     └───────────────────────────────────────┘
              │
    ┌─────────┼──────────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼          ▼
  SM 0     SM 1        SM 2      ...       SM 27      ← 28 个 SM 同时接活
  ┌─────┐ ┌─────┐    ┌─────┐             ┌─────┐
  │B0,B28│ │B1,B29│  │B2,B30│  ...        │B27,B55│  ← 每 SM 拿到多个 block
  └─────┘ └─────┘    └─────┘             └─────┘
              │
              ▼
     ① 分派：GigaThread 根据 SM 当前**剩余寄存器/Shared Memory/warp 槽位**把 block 塞进 SM
     ② 驻留：block 一旦进入某 SM，**寄存器和 shared memory 立刻被分配**，直到全部线程执行完才释放
     ③ 切换：SM 里的 4 个 Warp Scheduler 在**驻留的所有 warp 之间**来回切换，隐藏访存延迟
     ④ 退休：block 全部线程结束 → 资源归还 → GigaThread 从"待跑队列"再塞一个新 block 进来
```

> 📌 **图中每 SM 画 2 个 block 仅为示意，不是硬性规则**。实际每 SM 能同时驻留的 block 数在 **1 ~ 16** 之间，取决于四个"卡口"的最小值：
>
> - **硬件 Block 上限**：每 SM ≤ **16 个 block**（Ampere 规格死限）；
> - **Warp 上限**：每 SM ≤ **48 warp**——若 `blockDim=256`（8 warp/block，256/32 =8），最多 `48/8 = 6 个 block`；
> - **寄存器**：每 SM 65536 个 32-bit——若每 block 用 32 KB 寄存器，最多 `65536/8192 = 8 个 block`；
> - **Shared Memory**：每 SM ~100 KB——若每 block 申请 16 KB shared，最多 `100/16 ≈ 6 个 block`。
>
> **典型场景速算**（假设 `blockDim=256`）：
>
> | 场景 | 每线程寄存器 | 每 block Shared | 实际驻留 block/SM | Occupancy |
> |:--|:--:|:--:|:--:|:--:|
> | 轻量 kernel（向量加） | 32 | 0 KB | **6** | 100% |
> | 典型 kernel（reduction） | 40 | 16 KB | **6** | 100% |
> | 重量 kernel（GEMM tile） | 128 | 48 KB | **2** | 33% |
>
> 上图画 2 个 block/SM，对应的正是**重量级 kernel** 的常见场景。详细的资源约束推导见下面 ⑤ Occupancy 一节。

**这就是 CUDA 的核心调度模型**：**Block 之间由 GigaThread 全局分派，Block 内部由 SM 的 Warp Scheduler 局部调度**。

**⑤ Occupancy（占用率）：SM 用没用满？**

> **Occupancy = SM 上实际驻留的 warp 数 / SM 支持的最大 warp 数**（3060 是 48）

拉高 Occupancy 的目的：当某个 warp 在等 global memory（~500 cycle），Scheduler 能立刻切到别的 ready warp 继续算。**GPU 靠 warp 切换掩盖访存延迟，CPU 靠 cache/分支预测减少访存等待**——这是两者最本质的区别。

**限制 Occupancy 的三大资源**（调优必看）：**寄存器**（每线程用得多 → 塞不下 1536 线程）、**Shared Memory**（每 block 用得多 → 塞不下 16 block）、**Block 大小**（`blockDim` 太小 → 触到 SM 的 16 block 上限反而线程数上不去）。

> **📐 附录：Occupancy 是如何一步步算出来的？**（对应上方 ④ 的速算表）
>
> **公式定义**：
>
> $$\text{Occupancy} = \frac{\text{SM 实际驻留 warp 数}}{\text{SM 支持的最大 warp 数}} = \frac{\text{active warps}}{48}$$
>
> **关键换算链**（`blockDim=256` 时，每 block = `256/32` = **8 warp**）：
>
> ```text
> 输入：blockDim, 每线程寄存器数, 每 block Shared
>    │
>    ▼
> Step 1: 分别算四个"卡口"的 block/SM 上限
>    ├── A. 硬件 Block 上限（Ampere = 16）
>    ├── B. Warp 上限：48 ÷ (blockDim/32)
>    ├── C. 寄存器：65536 ÷ (blockDim × 每线程寄存器)      ← 向下取整
>    └── D. Shared：~100 KB ÷ 每 block Shared              ← 向下取整
>    │
>    ▼
> Step 2: 取最小值 = 实际 block/SM（短板效应）
>    │
>    ▼
> Step 3: warp/SM = block/SM × (blockDim/32)
>    │
>    ▼
> Step 4: Occupancy = warp/SM ÷ 48
> ```
>
> **三场景逐一推演**（都用 `blockDim=256`，即 8 warp/block）：
>
> **① 轻量 kernel（向量加）**：寄存器=32，Shared=0 KB
>
> | 卡口 | 计算 | 允许 block/SM |
> |:--|:--|:--:|
> | A. Block 上限 | 硬件死限 | 16 |
> | B. Warp 上限 | `48/8` | **6** ⬅ 瓶颈 |
> | C. 寄存器 | `65536/(32×256)` = `65536/8192` | 8 |
> | D. Shared | 0 KB → 无限制 | ∞ |
>
> → `min = 6 block/SM` → `6×8 = 48 warp/SM` → **Occupancy = 48/48 = 100%**
>
> **② 典型 kernel（reduction）**：寄存器=40，Shared=16 KB
>
> | 卡口 | 计算 | 允许 block/SM |
> |:--|:--|:--:|
> | A. Block 上限 | 硬件死限 | 16 |
> | B. Warp 上限 | `48/8` | **6** |
> | C. 寄存器 | `65536/(40×256)` = `65536/10240` ≈ 6.4 → 向下取整 | **6** |
> | D. Shared | `100/16` ≈ 6.25 → 向下取整 | **6** |
>
> → `min = 6 block/SM` → `6×8 = 48 warp/SM` → **Occupancy = 100%**（三个卡口同时打满，配比最优）
>
> **③ 重量 kernel（GEMM tile）**：寄存器=128，Shared=48 KB
>
> | 卡口 | 计算 | 允许 block/SM |
> |:--|:--|:--:|
> | A. Block 上限 | 硬件死限 | 16 |
> | B. Warp 上限 | `48/8` | 6 |
> | C. 寄存器 | `65536/(128×256)` = `65536/32768` | **2** ⬅ 瓶颈 |
> | D. Shared | `100/48` ≈ 2.08 → 向下取整 | **2** ⬅ 瓶颈 |
>
> → `min = 2 block/SM` → `2×8 = 16 warp/SM` → **Occupancy = 16/48 ≈ 33.3%**
>
> **三个必须知道的"陷阱"**：
>
> - **向下取整而非四舍五入**：资源分配是整数，`6.4 个 block` 只能塞 `6 个`，所有除法用 `floor()`；
> - **实际硬件按"块"分配**寄存器（每 256 个一块）和 Shared，上述算法是简化版；**精确值请用官方 CUDA Occupancy Calculator 或 Nsight Compute**；
> - **Occupancy 不是越高越好**：内存密集型（reduction）追求高 Occupancy 掩盖访存延迟；计算密集型（GEMM）反而中低 Occupancy 更优——每线程多占寄存器 → 数据复用更好 → Tensor Core 打满，这就是 CUTLASS 的 "Low Occupancy, High Performance" 哲学。

> **一句话记忆**：**SM = 工厂**，**Block = 施工队**，**Warp = 32 人班组**，**Warp Scheduler = 排班员**，**寄存器/Shared Memory = 配给的工具箱**。kernel 性能好不好 = 工厂利用率高不高、工人闲不闲、工具够不够用。


#### 3.1.3 四层结构逐层拆解（定海神针表）

**为什么是这四层？**——每一层解决一个特定问题，各司其职、缺一不可：

- **Grid**：面向程序员，负责**问题空间切分**（"我要处理多少数据"），屏蔽硬件细节；
- **Block**：负责**局部协作**，独占一套寄存器 + Shared Memory，能内部同步 `__syncthreads()`；如果没有 Block，几万线程全局抢锁会成灾难；
- **Warp**：负责**硬件调度效率**，32 线程锁步 = 1 条指令驱动 32 个 lane，调度开销从 O(N) 降到 O(N/32)；如果没有 Warp，GPU 会退化成 CPU；
- **Thread**：面向代码可读性，程序员按"一个人干一件事"来写，屏蔽了 SIMD 向量化的复杂度。

> **快递类比**：Grid = 全城配送任务；Block = 一个快递站；Warp = 一辆车 + 32 个快递员同时出发；Thread = 单个快递员。

**定海神针表**（建议打印贴屏幕旁，数字以 3060 / SM 8.6 为准）：

| 层级 | 是什么 | 数量上限 | 由谁决定 | 关键资源 | 生命周期 |
|:--|:--|:--|:--|:--|:--|
| **Grid**   | 一次 kernel 启动的**全部线程集合** | 每维 2³¹-1（几乎无上限）  | `gridDim` | — | 一次 kernel 启动 |
| **Block**  | **驻留同一 SM** 的线程组，可共享资源、内部同步 | ≤ **1024** 线程/block；每 SM ≤ **16** block | `blockDim` | Shared Memory / `__syncthreads()` | 所属 block 全部线程执行完 |
| **Warp**   | **硬件调度最小单位**，32 线程锁步执行同一条指令 | 固定 **32**；每 SM ≤ **48** warp（= 1536 线程） | 硬件按 `threadIdx` 自动切 | Warp Shuffle (`__shfl_sync`) | 随所属 block |
| **Thread** | 最小逻辑执行流 | 见 Block 上限 | `threadIdx` | Registers（65536 × 32-bit / SM） | 随所属 block |

> 数字随架构变化（Hopper 每 SM 有 64 warp / 2048 线程），请对照 [1.1 节](#11-rtx-3060-关键规格) 记忆。

#### 3.1.4 Warp 与 SIMT：为什么"32"这么重要？

Warp 的执行模式叫 **SIMT (Single Instruction, Multiple Threads)**——**32 个线程共用一个指令指针，锁步执行同一条指令，但各自持有自己的寄存器和数据**。

用一个类比理解：

> 想象一支 **32 人军乐队**：指挥（Program Counter）喊"抬左脚"，32 个人**同时**抬左脚；喊"抬右脚"就一起抬右脚。每个人有自己的鞋（寄存器），但动作永远一致。

这带来两个至关重要的推论：

**① 为什么 `blockDim` 必须是 32 的倍数？**

如果你写 `blockDim = 100`，硬件仍然要切成 **4 个 warp**（100 / 32 向上取整），但**最后一个 warp 只有 4 个线程有活干，另外 28 个线程被打上"inactive"标记跟着空走**。指令周期一样耗，功耗一样烧，硬生生浪费了 87.5% 的算力。所以：

```cpp
// ❌ 坏：100 % 32 != 0，最后一个 warp 浪费 28 线程
kernel<<<grid, 100>>>(...);

// ✅ 好：128 / 32 = 4 个 warp 全部满员
kernel<<<grid, 128>>>(...);
```

**② 什么是 Warp Divergence（分支发散）？**

如果 warp 里的 32 个线程走入 `if / else` 的**不同分支**，硬件只能**串行执行两条路径**：先让走 `if` 的 4 个线程执行、其余 28 个 masked 掉；再让走 `else` 的 28 个执行、其余 4 个 masked 掉——**warp 内并行度直接砍半甚至更差**。

```cpp
// ⚠️ 分支发散：条件依赖数据，同 warp 内可能一半一半
if (data[tid] > 0) { fast_path(); } else { slow_path(); }

// ✅ 无发散：条件按 tid 划分，同 warp 内 32 个线程走向一致（因为 tid 连续）
if (tid < 512)     { path_A(); }   else { path_B(); }
```

这就是为什么 [3.2 表格](#32-从-cpu-视角到-gpu-视角) 里会说"CPU 分支预测友好，GPU 要避免 warp 内分支发散"——完全是两种不同的性能哲学。

#### 3.1.5 通信与同步能力矩阵

不同层级之间**能不能通信、能不能同步**，是 CUDA 写协作型 kernel（reduction、scan、GEMM tile）的核心考点。一张表说清：

| 谁和谁 | 能通信吗？ | 通信手段 | 能同步吗？ | 同步手段 |
|:--|:--|:--|:--|:--|
| 同 **Warp** 内的线程    | ✅ 最快 | Warp Shuffle：`__shfl_sync`、`__shfl_down_sync` 等（寄存器直连） | ✅ 隐式（SIMT 天然锁步） | `__syncwarp()`（Volta+ 有独立 PC 时需要） |
| 同 **Block** 内、跨 warp | ✅ 快 | Shared Memory (`__shared__`) | ✅ | `__syncthreads()`（block 内屏障） |
| 同 **Grid** 内、跨 block | ⚠️ 慢 | 只能通过 Global Memory + 原子操作 | ❌ **默认不支持** | 只能靠 Cooperative Groups 的 `grid.sync()`，或**结束 kernel 再启动一个新的**做隐式全局屏障 |
| 跨 Grid（跨 kernel launch） | ✅ | Global Memory / Host 中转 | ✅ 天然屏障 | 下一个 kernel 启动前 CUDA runtime 保证前一个完成 |

**记忆口诀**：**越近越快、越远越贵**——寄存器 → shared → global，通信成本大致差 1~2 个数量级。**能在 warp 内解决的绝不上 block，能在 block 内解决的绝不上 grid**，这是所有高性能 kernel 的第一性原则。

#### 3.1.6 Block 为什么必须"完全独立"？——CUDA 的可伸缩性秘诀

新手常问："能不能让 Block 0 等 Block 1 完成？" **答案：不能**（默认无此机制）。这不是硬件做不到，而是 NVIDIA 故意的设计——**Grid 内 block 之间执行顺序不确定，硬件可任意分派到任意 SM**。

**好处**：同一份 kernel 代码**在不同 GPU 上自动伸缩**——`<<<1024, 256>>>` 在 3060（28 SM）、A100（108 SM）、H100（132 SM）上一行不改就能跑，SM 越多跑得越快。这就是 CUDA 能从入门卡一路扩展到 8×H100 集群的根本原因。

**代价**：写算法时必须让 **block 之间无依赖**。真需要跨 block 同步的场景（如全局 reduction 最后一步合并），**标准解法是拆成两个 kernel**——kernel 结束就是天然的全局屏障。

#### 3.1.7 常见误区 FAQ

**Q1：Block 一旦分派到 SM 后能被换出去吗？**  
不能。Block 是 SM 的"驻留居民"——寄存器和 shared memory 直到自己**全部线程执行完**才释放，**不会被抢占迁移**。这就是"每个 block 用的资源越少，SM 能塞的 block 越多"的原因。

**Q2：`threadIdx.x` 最大是多少？**  
单 block ≤ **1024 线程**，故 `threadIdx.x` ≤ 1023；若用 `dim3(x,y,z)`，则 `x*y*z ≤ 1024`。`blockIdx.x` 基本无上限（2³¹-1）。

**Q3：Warp 内 32 个线程一定同步吗？**  
**Volta 之前是**，之后**不一定**。Volta+ 引入 **Independent Thread Scheduling**，warp 内线程可以有独立 PC。所以现代 warp shuffle 都要求传 mask（`__shfl_sync(0xffffffff, val, 0)`），显式声明"这 32 lane 都参与"——这就是 `_sync` 后缀的由来。

**Q4：写代码时该按哪个层级思考？**  
分两步走：
- **写算法时用 thread 视角**："我是一个线程，我处理数据里的哪一份？" 靠 `tid = blockIdx.x * blockDim.x + threadIdx.x` 回答；
- **调性能时用 block / warp 视角**："同 block 能不能 tile 到 shared 复用？同 warp 访存是不是合并的？"

---

### 3.2 从 CPU 视角到 GPU 视角

| CPU 思维 | GPU 思维 |
|:--|:--|
| 一个循环处理 N 个元素 | **启动 N 个线程**，每个线程处理一个元素 |
| 追求单核 IPC 高 | 追求"淹没"式并行，让 SM 永远有 warp 可跑 |
| 分支预测友好 | **避免 warp 内分支发散**（`if (tid < K)` 这种是可以的，`if (data[tid] > 0)` 就要小心） |
| 缓存自动管理 | **手动管理 shared memory / register / L1/L2** |
| 一次 malloc 用到底 | Host / Device 两套内存，`cudaMemcpy` 显式搬运（或用 UM/Pinned） |

### 3.3 一个 kernel 从写到跑的全流程

```
    .cu 源文件
        │
        │ nvcc 分离编译
        ↓
    ┌──────────┐         ┌──────────────┐
    │ Host 代码│         │ Device 代码  │
    │ (给 MSVC)│         │ (给 ptxas)   │
    └────┬─────┘         └──────┬───────┘
         │                      │
         ↓                      ↓
      .obj                    PTX (虚拟汇编)
                                │
                                ↓
                              SASS (真机器码, sm_86 专属)
                                │
         └────────┬─────────────┘
                  ↓
              可执行文件 .exe
                  │
                  ↓
    运行时：cudaMalloc → cudaMemcpy(H→D) → kernel<<<grid, block>>> → cudaMemcpy(D→H) → cudaFree
```

---

## 4. 第一个 Kernel：Hello CUDA / 向量加法

### 4.1 Hello, CUDA

```cpp
// hello.cu
#include <cstdio>

__global__ void hello_kernel() {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    printf("Hello from thread %d (block %d, thread %d)\n",
           tid, blockIdx.x, threadIdx.x);
}

int main() {
    hello_kernel<<<2, 4>>>();      // 2 个 block，每 block 4 线程 = 8 线程
    cudaDeviceSynchronize();       // 等 GPU 打印完
    return 0;
}
```

编译运行：
```bat
nvcc -arch=sm_86 hello.cu -o hello.exe && hello.exe
```

### 4.2 向量加法（CUDA 的 "Hello World"）

```cpp
// vec_add.cu
#include <cstdio>
#include <cuda_runtime.h>

#define CUDA_CHECK(call) do {                                      \
    cudaError_t e = (call);                                        \
    if (e != cudaSuccess) {                                        \
        fprintf(stderr, "CUDA error %s:%d: %s\n",                  \
                __FILE__, __LINE__, cudaGetErrorString(e));        \
        exit(1);                                                   \
    }                                                              \
} while (0)

__global__ void vec_add(const float* a, const float* b, float* c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {                       // 边界保护，避免越界
        c[i] = a[i] + b[i];
    }
}

int main() {
    const int N = 1 << 20;             // 1M 元素
    size_t bytes = N * sizeof(float);

    // 1. Host 内存
    float *h_a = (float*)malloc(bytes);
    float *h_b = (float*)malloc(bytes);
    float *h_c = (float*)malloc(bytes);
    for (int i = 0; i < N; ++i) { h_a[i] = 1.0f; h_b[i] = 2.0f; }

    // 2. Device 内存
    float *d_a, *d_b, *d_c;
    CUDA_CHECK(cudaMalloc(&d_a, bytes));
    CUDA_CHECK(cudaMalloc(&d_b, bytes));
    CUDA_CHECK(cudaMalloc(&d_c, bytes));

    // 3. H2D
    CUDA_CHECK(cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice));

    // 4. Launch：block=256，是常见起点（8 个 warp）
    int block = 256;
    int grid  = (N + block - 1) / block;
    vec_add<<<grid, block>>>(d_a, d_b, d_c, N);
    CUDA_CHECK(cudaGetLastError());              // 检查 launch 错误
    CUDA_CHECK(cudaDeviceSynchronize());         // 等 kernel 完成

    // 5. D2H + 校验
    CUDA_CHECK(cudaMemcpy(h_c, d_c, bytes, cudaMemcpyDeviceToHost));
    printf("h_c[0] = %.1f, h_c[N-1] = %.1f (expect 3.0)\n", h_c[0], h_c[N-1]);

    // 6. 清理
    cudaFree(d_a); cudaFree(d_b); cudaFree(d_c);
    free(h_a); free(h_b); free(h_c);
    return 0;
}
```

### 4.3 从这段代码里能学到的 6 件事

1. **`__global__`** 声明的是从 host 调用、在 device 执行的 kernel。
2. **`<<<grid, block>>>`** 语法是 CUDA C++ 的核心扩展，指定启动配置。
3. **`blockIdx / blockDim / threadIdx`** 三剑客计算全局索引，是所有 kernel 的开头模板。
4. **边界检查** `if (i < n)` 是必备习惯——`grid * block` 通常大于 N。
5. **kernel launch 是异步的**，必须显式 `cudaDeviceSynchronize()` 或 `cudaMemcpy`（同步版）等结果。
6. **错误检查宏是护身符**：CUDA 函数出错不会抛异常，必须自己查返回值。

---

## 5. 内存层次：CUDA 性能的 80% 都在这里

**核心信念**：**GPU 计算力过剩，瓶颈几乎永远是访存。** 学 CUDA 优化 = 学怎么把数据放到"离计算最近"的地方。

### 5.1 内存金字塔（RTX 3060 视角）

```
    ┌──────────────────────────────────────────────────────┐
    │  Registers (每 SM 65536 个 32-bit)   延迟 ~1 cycle  │  ← 最快
    ├──────────────────────────────────────────────────────┤
    │  Shared Memory / L1 (每 SM 128 KB)   延迟 ~20 cycle │  ← 手动管理
    ├──────────────────────────────────────────────────────┤
    │  L2 Cache (整卡 3 MB)                延迟 ~200 cycle│
    ├──────────────────────────────────────────────────────┤
    │  Global Memory / HBM (12 GB)         延迟 ~500 cycle│  ← 最慢
    └──────────────────────────────────────────────────────┘
```

### 5.2 你必须掌握的四种内存

| 内存 | 声明方式 | 作用域 | 生命周期 | 用途 |
|:--|:--|:--|:--|:--|
| Register | 局部变量 | 单线程 | Kernel | 临时计算 |
| **Shared** | `__shared__ float smem[N];` | Block 内共享 | Block | tile、缓存复用数据 |
| Global | `cudaMalloc` 分配 | 整个 grid | 显式 free | 输入/输出数据 |
| Constant | `__constant__` | Grid 只读 | 程序 | 广播式只读参数 |

### 5.3 两条黄金优化法则

#### 法则 1：**Coalesced Access（合并访存）**

一个 warp 的 32 个线程如果连续访问 128 字节对齐的内存 → 硬件合并成 **1 次 transaction**；否则要 32 次。

```cpp
// ✅ 合并：thread i 访问 a[i]
c[i] = a[i] + b[i];

// ❌ 不合并：thread i 访问 a[i * stride]
c[i] = a[i * 32];   // 32 次 transaction，带宽利用率 3%
```

#### 法则 2：**Tiling（分块）+ Shared Memory 复用**

矩阵乘法就是最典型例子：把 A、B 的一小块搬到 shared memory，让 block 内所有线程共享——把访存量从 O(N³) 降到 O(N³/tile)。

**这条法则的威力有多大？** 手写 GEMM 从 Naive → Shared Memory Tiling，性能通常能提升 **5~10 倍**。

### 5.4 Warp 层通信：Shuffle

Ampere 及之后，warp 内 32 个线程可以**不经过 shared memory** 直接交换寄存器：

```cpp
// 每个线程持有 val，把 lane 0 的值广播给整个 warp
float x = __shfl_sync(0xffffffff, val, 0);

// warp 内求和（reduction 常用模板）
for (int offset = 16; offset > 0; offset /= 2)
    val += __shfl_down_sync(0xffffffff, val, offset);
// 现在 lane 0 持有 32 个值的和
```

Shuffle 是写高性能 reduction / softmax 的必备武器。

---

## 6. AI 场景必修的三大 Kernel

学完向量加法只能算入门；AI 场景反复出现的三类 kernel，请**每种都亲手敲一遍并做性能对比**。

### 6.1 GEMM（矩阵乘法）——一切的基石

**为什么最重要？** Transformer 的 90% 计算量、CNN 的 85%，都可以归约成 GEMM。**读懂 GEMM 的优化路线，就读懂了 CUDA 优化的全貌。**

**必走的三级台阶**：

| 版本 | 关键技术 | 3060 上的相对性能（vs cuBLAS） |
|:--|:--|:--|
| v1 Naive | 每线程算 C 的 1 个元素，直接读 global | ~5~10% |
| v2 Shared Memory Tiling | 分块搬到 smem，block 内复用 | ~30~50% |
| v3 Register Tiling | 每线程算 8x8 小块，寄存器复用 | ~60~80% |
| v4 Tensor Core (WMMA) | FP16 输入，用 `wmma::mma_sync` | 接近 cuBLAS |

**v2 关键片段**（shared memory tiling，方形 tile）：

```cpp
#define TS 32   // tile size

__global__ void gemm_smem(const float* A, const float* B, float* C,
                          int M, int N, int K) {
    __shared__ float As[TS][TS];
    __shared__ float Bs[TS][TS];

    int row = blockIdx.y * TS + threadIdx.y;
    int col = blockIdx.x * TS + threadIdx.x;
    float acc = 0.0f;

    for (int t = 0; t < (K + TS - 1) / TS; ++t) {
        // 协作加载一小块到 shared memory
        As[threadIdx.y][threadIdx.x] =
            (row < M && t*TS + threadIdx.x < K) ? A[row*K + t*TS + threadIdx.x] : 0.0f;
        Bs[threadIdx.y][threadIdx.x] =
            (t*TS + threadIdx.y < K && col < N) ? B[(t*TS + threadIdx.y)*N + col] : 0.0f;
        __syncthreads();

        #pragma unroll
        for (int k = 0; k < TS; ++k)
            acc += As[threadIdx.y][k] * Bs[k][threadIdx.x];
        __syncthreads();
    }
    if (row < M && col < N) C[row*N + col] = acc;
}
// launch: dim3 block(TS, TS); dim3 grid((N+TS-1)/TS, (M+TS-1)/TS);
```

**练习目标**：M=N=K=2048 时，写完 v1、v2，用 Nsight Compute 对比"DRAM Throughput"和"Compute Throughput"。你会亲眼看到瓶颈从访存转向计算。

### 6.2 Reduction / Softmax——AI 里最常见的归约

**Softmax = max reduction + exp + sum reduction + 除法**，出现在每个 Attention 里。

**Reduction 的三级优化**：

1. Naive：每 block 内 `__syncthreads()` 一层层折半（会有 warp 内浪费）；
2. Warp Shuffle：warp 内用 `__shfl_down_sync`，跨 warp 用 shared memory；
3. Multi-block + atomic 或第二次 kernel launch。

**warp reduce 模板（背下来）**：

```cpp
__inline__ __device__ float warp_reduce_sum(float val) {
    #pragma unroll
    for (int offset = 16; offset > 0; offset >>= 1)
        val += __shfl_down_sync(0xffffffff, val, offset);
    return val;
}

__inline__ __device__ float block_reduce_sum(float val) {
    __shared__ float smem[32];              // 最多 32 个 warp
    int lane = threadIdx.x & 31;
    int wid  = threadIdx.x >> 5;
    val = warp_reduce_sum(val);             // 每个 warp 内先归约
    if (lane == 0) smem[wid] = val;
    __syncthreads();
    val = (threadIdx.x < (blockDim.x + 31)/32) ? smem[lane] : 0.0f;
    if (wid == 0) val = warp_reduce_sum(val);
    return val;                             // thread 0 持有最终和
}
```

**Softmax 数值稳定版**永远是"减 max 再 exp"，写自定义 kernel 时不要偷懒。

### 6.3 Element-wise / Fused 算子

- **Element-wise**：`y = gelu(x + bias)`——单独看每个都简单，但**融合在一起**能省 2~3 次 global memory 读写。
- **Fused Bias + Activation + Dropout**：LLM 训练/推理里到处都是这类 kernel。
- **LayerNorm / RMSNorm**：本质是 reduction + element-wise 的组合。

**融合原则**：只要两个算子都是**逐元素**或**同一个归约维度**，就融合成一个 kernel——这是 AI 加速最容易拿到的收益。

---

## 7. Tensor Core 与混合精度（AI 加速的核心武器）

### 7.1 什么是 Tensor Core？

Ampere 上一个 Tensor Core 一次可以完成一个 **16×16×16 的 FP16 矩阵乘加**，相当于 CUDA Core 干几百次乘加。**不用 Tensor Core，你的 kernel 上限就是 FP32 的 13 TFLOPS；用了，就是 51 TFLOPS**。AI 加速几乎必须用它。

### 7.2 三种使用方式（从高到低层）

| 层级 | 接口 | 门槛 | 适用场景 |
|:--|:--|:--|:--|
| 高层 | **cuBLAS / cuDNN**（`cublasGemmEx` + `CUBLAS_COMPUTE_16F`） | 低 | 标准 GEMM/Conv |
| 中层 | **CUTLASS** 模板库 | 中 | 自定义 fused GEMM |
| 中层 | **WMMA API**（`nvcuda::wmma`） | 中 | 手写 Tensor Core kernel 学习 |
| 低层 | **`mma.sync` PTX 内联** | 高 | 极致优化，FlashAttention 级别 |

### 7.3 WMMA 最小示例（16×16×16 FP16 GEMM 片段）

```cpp
#include <mma.h>
using namespace nvcuda;

__global__ void wmma_gemm(const half* A, const half* B, float* C,
                          int M, int N, int K) {
    // 每个 warp 计算 C 的一个 16x16 tile
    int warpM = (blockIdx.y * blockDim.y + threadIdx.y);
    int warpN = (blockIdx.x * blockDim.x + threadIdx.x) / 32;

    wmma::fragment<wmma::matrix_a, 16, 16, 16, half, wmma::row_major> a_frag;
    wmma::fragment<wmma::matrix_b, 16, 16, 16, half, wmma::col_major> b_frag;
    wmma::fragment<wmma::accumulator, 16, 16, 16, float>              c_frag;
    wmma::fill_fragment(c_frag, 0.0f);

    for (int k = 0; k < K; k += 16) {
        wmma::load_matrix_sync(a_frag, A + warpM*16*K + k,      K);
        wmma::load_matrix_sync(b_frag, B + k*N + warpN*16,      N);
        wmma::mma_sync(c_frag, a_frag, b_frag, c_frag);         // ← Tensor Core 一次完成
    }
    wmma::store_matrix_sync(C + warpM*16*N + warpN*16, c_frag, N, wmma::mem_row_major);
}
```

**编译加**：`-arch=sm_86`（低于 sm_70 不支持 WMMA）。

### 7.4 精度选择速查（3060 支持的）

| 精度 | 关键字 | 场景 | 3060 支持 |
|:--|:--|:--|:--|
| FP32 | 默认 | 训练 baseline | ✅（不走 TC） |
| **TF32** | `CUBLAS_COMPUTE_32F_FAST_TF32` | 训练默认加速（几乎无精度损失） | ✅ |
| **FP16** | `half` | 训练 AMP、推理 | ✅ |
| **BF16** | `__nv_bfloat16` | LLM 训练首选（动态范围大） | ✅ |
| INT8 | `int8_t` | 推理量化 | ✅ |
| **FP8** | `__nv_fp8_e4m3` | LLM 训练/推理 | ❌（Hopper/Ada 才有） |

---

## 8. 从"手写 Kernel"到"用好轮子"：cuBLAS / cuDNN / CUTLASS / Triton

**认知修正**：你写的 kernel **99% 情况打不过 cuBLAS**——cuBLAS 是 NVIDIA 汇编级手工调优的。学 CUDA 不是为了重新发明轮子，而是为了：**在轮子搞不定的地方（融合、非标准形状、新算子）自己接上**。

本节**只做定位**，帮你在写完手写 kernel 后知道"接下来该跳到哪份姊妹篇精读"，**不重复讲每个库的用法**（那些都有独立指南）。

### 8.1 三秒定位卡片

| 库 | 3 秒定位 | 何时用 | 姊妹篇精读 |
|:--|:--|:--|:--|
| **cuBLAS** | 稠密 GEMM/GEMV 官方库 | 标准形状矩阵乘 | [cuBLAS 指南](./cuBLAS编程学习指南.md) |
| **cuBLASLt** | 带 epilogue 融合的新 GEMM | 推理里 GEMM+bias+GELU | [cuBLASLt 指南](./cuBLASLt编程学习指南.md) |
| **cuDNN** | 卷积/Attention/RNN | CV、传统 DNN 训练 | [cuDNN 指南](./cuDNN编程学习指南.md) |
| **CUTLASS** | GEMM/Conv 开源 C++ 模板 | 定制融合 GEMM、读源码 | [CUTLASS 指南](./CUTLASS编程学习指南.md) |
| **Thrust** | STL 风格 sort/reduce/scan | 数据预处理原型 | [Thrust 指南](./Thrust编程学习指南.md) |
| **CUB** | Block/Warp 级原语 | 自己写高性能 kernel | [CUB 指南](./CUB编程学习指南.md) |
| **Triton** | Python DSL，编译到 PTX | **快速产出融合算子（首推）** | [Triton 指南](./Triton编程学习指南.md) |

### 8.2 从本文出发的推荐路径

- **想立刻见效果**：`torch.matmul`（背后就是 cuBLAS）→ 精读 **cuBLAS 指南**；
- **想快速造新融合算子**：**Triton 指南**（20 行搞定 CUDA 200 行的活）；
- **想深入到极致 GEMM**：**CUTLASS 指南** → **FlashAttention 源码指南** → **PTX 汇编指南**；
- **完整生态选型**：先回 [GPU 编程工具全景](./GPU编程工具全景.md) 挑一条主线，再回本节。

> **⚠️ 一句话规避重复**：本节不再抄写每个库的 API 用法——**每份姊妹篇都有 12 章完整讲解**，重复内容既维护不动也没必要看两遍。

---

## 9. 集成到 AI 框架：写一个 PyTorch 自定义 CUDA 算子

**这是"CUDA 学习"到"能创造价值"的分水岭。** 你可以把手写 kernel 无缝挂进 PyTorch，让 Python 层直接调用。

### 9.1 最小工程结构

```
my_ops/
├── setup.py
├── my_ops.cpp        # C++ 绑定层（pybind11 / TORCH_LIBRARY）
├── my_ops_kernel.cu  # CUDA kernel
└── test.py
```

**`my_ops_kernel.cu`**（还是向量加，但接受 torch::Tensor）：

```cpp
#include <torch/extension.h>

__global__ void add_kernel(const float* a, const float* b, float* c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) c[i] = a[i] + b[i];
}

torch::Tensor my_add_cuda(torch::Tensor a, torch::Tensor b) {
    TORCH_CHECK(a.is_cuda() && b.is_cuda(), "inputs must be CUDA");
    TORCH_CHECK(a.sizes() == b.sizes(), "shape mismatch");
    auto c = torch::empty_like(a);
    int n = a.numel();
    int block = 256, grid = (n + block - 1) / block;
    add_kernel<<<grid, block>>>(a.data_ptr<float>(),
                                b.data_ptr<float>(),
                                c.data_ptr<float>(), n);
    return c;
}
```

**`my_ops.cpp`**：

```cpp
#include <torch/extension.h>
torch::Tensor my_add_cuda(torch::Tensor a, torch::Tensor b);

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("my_add", &my_add_cuda, "custom add (CUDA)");
}
```

**`setup.py`**：

```python
from setuptools import setup
from torch.utils.cpp_extension import BuildExtension, CUDAExtension

setup(
    name='my_ops',
    ext_modules=[CUDAExtension(
        name='my_ops',
        sources=['my_ops.cpp', 'my_ops_kernel.cu'],
        extra_compile_args={'cxx': ['-O2'],
                            'nvcc': ['-O2', '-arch=sm_86']},
    )],
    cmdclass={'build_ext': BuildExtension},
)
```

**编译 + 用**：

```bash
python setup.py install
python -c "import torch, my_ops; a=torch.ones(1024,device='cuda'); b=torch.ones(1024,device='cuda'); print(my_ops.my_add(a,b)[0].item())"
```

### 9.2 进阶方向

- **`torch.compile` + Triton**：Triton 更适合快速验证融合算子；
- **`torch.utils.cpp_extension.load`**：JIT 编译，改代码不用 `python setup.py install`；
- **`torch.autograd.Function`**：定义反向传播，让自定义算子支持训练。

> **📎 精读入口**：本节只给最小可运行例。完整的 `TORCH_LIBRARY` 注册、autograd 反向、多后端派发、CUDA Stream 与 PyTorch 交互、性能陷阱等，见 [《PyTorch 自定义 CUDA 算子编程学习指南》](./PyTorch自定义CUDA算子编程学习指南.md)。

---

## 10. 性能分析与调优工具链（Nsight 全家桶）

> **📎 精读入口**：本节只讲三件事（怎么起 profile、看哪三个指标、迭代闭环）。完整的 Roofline 分析、Warp Stall 分类、SM Occupancy 深挖、Kernel Replay、Compare Baseline 等，见 [《Nsight 性能分析编程学习指南》](./Nsight性能分析编程学习指南.md)。


**没有 Profiler 的 CUDA 调优 = 蒙眼开车。** 3060 上你会用到的两个工具：

### 10.1 Nsight Systems（`nsys`）——系统级时间线

回答的问题："**整个训练/推理过程，时间花在哪？CPU-GPU 有没有等待？stream 有没有并行？**"

```bash
nsys profile -o report python train.py
# 用 Nsight Systems GUI 打开 report.nsys-rep 看时间线
```

### 10.2 Nsight Compute（`ncu`）——单 Kernel 微观分析

回答的问题："**这个 kernel 是访存瓶颈还是计算瓶颈？occupancy 多高？shared memory 冲突了吗？**"

```bash
ncu --set full -o kernel_report .\my_program.exe
# GUI 打开 .ncu-rep，重点看：
#  - GPU Speed Of Light（一眼看瓶颈）
#  - Memory Workload Analysis（合并访存）
#  - Warp State Statistics（stall 原因）
#  - Occupancy（活跃 warp / 上限）
```

**优化闭环 SOP**：

```
    写代码 → nsys 看总体 → 找到最耗时 kernel
              ↓
          ncu 分析该 kernel
              ↓
     ┌────────┴────────┐
     ↓                 ↓
 访存瓶颈           计算瓶颈
  ↓                    ↓
 tiling / 合并访存    Tensor Core / 提高 ILP
  ↓                    ↓
     └────────┬────────┘
              ↓
          再测一遍 → 收敛
```

---

## 11. 学习路线图（8~12 周）

按每周投入 8~12 小时估算，可根据实际进度伸缩：

### 🟢 阶段 1（Week 1-2）：环境 + 心智模型

- ✅ 装好环境，跑通 `hello.cu`、`vec_add.cu`
- ✅ 搞懂 grid/block/thread/warp，能画出内存金字塔
- ✅ 读完 CUDA C++ Programming Guide 前 5 章
- **产出**：向量加、SAXPY、element-wise activation

### 🟢 阶段 2（Week 3-4）：Shared Memory + Reduction

- ✅ 手写 3 个版本 reduction，理解 warp shuffle
- ✅ 手写 GEMM v1（naive）+ v2（shared memory tiling）
- ✅ 用 Nsight Compute 分析瓶颈
- **产出**：能把 2048×2048 GEMM 优化到 cuBLAS 的 30~50%

### 🟡 阶段 3（Week 5-6）：AI 常用 Kernel

- ✅ 写 Softmax、LayerNorm、RMSNorm、GELU
- ✅ 写 fused kernel（bias + activation）
- ✅ 学 cuBLAS 调用方式，做性能对比
- **产出**：一个 element-wise + reduction 的算子小库

### 🟡 阶段 4（Week 7-8）：Tensor Core + 混合精度

- ✅ 写 WMMA 版 GEMM（FP16→FP32）
- ✅ 用 cuBLASLt 做 fused GEMM+bias+GELU
- ✅ 试用 CUTLASS 一个 example
- **产出**：Tensor Core GEMM，性能达 cuBLAS 的 60~80%

### 🔴 阶段 5（Week 9-10）：PyTorch 自定义算子 + Triton

- ✅ 用 CUDAExtension 打包自己的算子
- ✅ 学 Triton，用它复现 fused softmax / layernorm
- ✅ 读 FlashAttention 的 Triton 实现
- **产出**：一个可 pip 安装的自定义算子包

### 🔴 阶段 6（Week 11-12）：真实项目实战

任选 1~2 个：

- 复现 FlashAttention v1 的 forward
- 给 llama.cpp / vLLM 的某个 kernel 提优化 PR
- 用 Triton 写一个量化 GEMM（W4A16）
- 把一个 HuggingFace 模型的推理关键 kernel 手写替换掉

---

## 12. 精选资源与踩坑清单

### 12.1 官方文档（最权威）

- **CUDA C++ Programming Guide**（必读，第 1-6 章、第 B 附录 Cooperative Groups）
- **CUDA C++ Best Practices Guide**（优化必读）
- **PTX ISA**（进阶时查内联汇编）
- **Nsight Compute Kernel Profiling Guide**

### 12.2 书籍

- 《Programming Massively Parallel Processors》4th Ed., Kirk & Hwu —— 最好的 CUDA 教科书
- 《CUDA C 编程权威指南》—— 中文替代品
- 《Professional CUDA C Programming》—— 补充案例

### 12.3 视频/课程

- **UIUC ECE408 / CS483** 公开课录像（对应上面那本教科书）
- **NVIDIA GTC** 每年的 CUTLASS / TensorRT-LLM / CUDA 优化 session
- **Simon Boehm** 博客《How to Optimize a CUDA Matmul Kernel for cuBLAS-like Performance》—— 学 GEMM 的黄金参考

### 12.4 开源项目（读源码）

每个开源项目都对应一份姊妹深度指南，读源码前建议**先看姊妹篇建立心智模型**，再对着源码验证。

| 项目 | 学什么 | 仓库地址 | 姊妹篇 |
|:--|:--|:--|:--|
| **CUTLASS** | 高性能 GEMM 模板设计 | https://github.com/NVIDIA/cutlass | [CUTLASS 指南](./CUTLASS编程学习指南.md) |
| **FlashAttention** | Attention 融合 kernel 的巅峰 | https://github.com/Dao-AILab/flash-attention | [FlashAttention 源码指南](./FlashAttention源码编程学习指南.md) |
| **Triton** | DSL 编译器 + 大量高质量算子 | https://github.com/triton-lang/triton | [Triton 指南](./Triton编程学习指南.md) |
| **llama.cpp / ggml** | 量化推理、CPU/GPU 混合调度 | https://github.com/ggml-org/llama.cpp ｜ https://github.com/ggml-org/ggml | [llama.cpp 指南](./llama.cpp编程学习指南.md) |
| **vLLM** | PagedAttention、continuous batching | https://github.com/vllm-project/vllm | [vLLM 指南](./vLLM编程学习指南.md) |
| **TensorRT-LLM** | 工业级 LLM 推理引擎 | https://github.com/NVIDIA/TensorRT-LLM | [TensorRT-LLM 指南](./TensorRT-LLM编程学习指南.md) |
| **DeepSpeed / Megatron-LM 的 kernel 目录** | 训练侧 kernel | https://github.com/deepspeedai/DeepSpeed ｜ https://github.com/NVIDIA/Megatron-LM | [大模型训练框架指南](./大模型训练框架编程学习指南.md) |

> **📖 阅读建议（按上手难度从低到高）**：
> 1. **llama.cpp** —— 单文件切入、CUDA/Metal/CPU 都有，最容易读懂全局；
> 2. **FlashAttention** —— 单个 kernel 打磨到极致，`csrc/flash_attn/src/` 是核心；
> 3. **vLLM** —— Python 上层 + `csrc/` 下的 PagedAttention kernel，学系统设计；
> 4. **Triton** 官方 tutorials（`python/tutorials/`）—— 用 Python 写 GPU kernel，10 行就能追平 cuBLAS；
> 5. **CUTLASS** —— 模板嵌套深，先看 `examples/` 再进 `include/cutlass/`；
> 6. **TensorRT-LLM / Megatron-LM** —— 工业级复杂度，建议有前 5 项基础后再啃。

### 12.5 Windows + 3060 常见踩坑

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| `nvcc fatal: Cannot find compiler 'cl.exe'` | 没在 VS 命令行环境跑 | 用 "x64 Native Tools Command Prompt" 或在 VS 里编译 |
| Kernel 无输出、无报错 | 没检查 launch 错误、没同步 | 加 `CUDA_CHECK(cudaGetLastError())` + `cudaDeviceSynchronize()` |
| 性能远低于预期 | 没加 `-arch=sm_86`，跑的是 PTX JIT | 显式指定架构 |
| Shared memory 超限 | 单 block 用超 48 KB | `cudaFuncSetAttribute(kernel, cudaFuncAttributeMaxDynamicSharedMemorySize, ...)` |
| WDDM 下长 kernel 触发 TDR（GPU 复位） | Windows 驱动 2 秒超时 | 拆小 kernel，或注册表调 TDR delay |
| 混合精度精度崩了 | 没减 max、accumulator 用了 FP16 | Softmax 数值稳定；累加器用 FP32 |
| PyTorch 扩展编译报错找不到 CUDA | `CUDA_HOME` 没设 | 设环境变量 `CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1` |
| Warp 分支发散严重 | `if` 条件依赖数据 | 尽量按 tid 分支；数据依赖分支考虑 warp vote / 排序后处理 |

### 12.6 心态

1. **别追求一次写对**：CUDA 代码 90% 时间在调 profiler，10% 在写代码——很正常。
2. **cuBLAS/cuDNN 是你的天花板参考**，不是竞争对手。
3. **Triton 是 2024+ 的事实标准**，别跳过它——很多新 idea 用 Triton 20 行就搞定，CUDA C++ 要 200 行。
4. **读源码 > 看教程**。CUTLASS 和 FlashAttention 的每一次通读，都是一次跃迁。

### 12.7 姊妹篇总入口

本文是 **33 份姊妹深度指南**中的 **CUDA C++ 主线篇**。完整分层地图、总表、选型决策树、AI 工程师优先级 Top 10、多路径学习路线，一律见：

📌 **[《GPU 编程工具全景》——33 份深度指南总入口](./GPU编程工具全景.md)**

下一步（按你的目标挑一份精读即可）：

- 想**继续深入 CUDA C++**：[FlashAttention 源码](./FlashAttention源码编程学习指南.md) → [PTX 汇编](./PTX%20%E6%B1%87%E7%BC%96%E7%BC%96%E7%A8%8B%E5%AD%A6%E4%B9%A0%E6%8C%87%E5%8D%97.md) → [Nsight](./Nsight性能分析编程学习指南.md)；
- 想**换到 Python DSL 提效**：[Triton](./Triton编程学习指南.md) → [CuPy](./CuPy编程学习指南.md) → [torch.compile](./torch.compile编程学习指南.md)；
- 想**做 LLM 推理部署**：[vLLM](./vLLM编程学习指南.md) → [TensorRT-LLM](./TensorRT-LLM编程学习指南.md) → [SGLang](./SGLang编程学习指南.md)；
- 想**理解框架内部**：[PyTorch 自定义 CUDA 算子](./PyTorch自定义CUDA算子编程学习指南.md) → [CUDA Graphs](./CUDA-Graphs编程学习指南.md) → [NCCL](./NCCL编程学习指南.md)。

---

**祝你旅途愉快。有一天你回头看 `vec_add.cu`，会觉得那正是所有 AI 加速故事的起点。**
