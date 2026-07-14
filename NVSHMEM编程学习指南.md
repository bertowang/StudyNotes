# NVSHMEM 编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：写**多 GPU HPC / 大模型分布式 kernel** 的 C++/CUDA 程序员，已经用过 NCCL，但发现 NCCL 的"集合通信 + host launch"粒度太粗，想在**kernel 内部**直接读写远端 GPU 显存（细粒度、低延迟、单边通信）——比如做多 GPU FFT、GPU-native 图算法、tensor parallel Attention 融合。
> **目标**：1~2 周内，从"用 nvshmem_put 单边写远端 GPU"到"能用 collective 在 kernel 内部做 AllReduce、能用 nvshmem_barrier 精细同步、能配合 NCCL 混用"。
> **本机环境**：NVIDIA GeForce RTX 3060（单卡）+ CUDA **12.1** + NVSHMEM **3.x**（Linux 强推荐）+ OpenMPI 或 Hydra + C++17。**注意**：单 GPU 环境仅能演示 API 语义，多 GPU 才是本命场景。

---

## 目录

- [0. 写在最前：为什么要学 NVSHMEM？](#0-写在最前为什么要学-nvshmem)
- [1. NVSHMEM 是什么：一句话讲清 vs NCCL / vs MPI](#1-nvshmem-是什么一句话讲清-vs-nccl--vs-mpi)
- [2. 环境搭建（Linux 首选）](#2-环境搭建linux-首选)
- [3. NVSHMEM 的心智模型：PE / Symmetric Heap / One-sided](#3-nvshmem-的心智模型pe--symmetric-heap--one-sided)
- [4. 第一个程序：kernel 内 `nvshmem_put`](#4-第一个程序kernel-内-nvshmem_put)
- [5. Point-to-Point：Put / Get / Signal / Wait](#5-point-to-pointput--get--signal--wait)
- [6. Collective：Barrier / AllReduce / Broadcast（GPU-initiated）](#6-collectivebarrier--allreduce--broadcastgpu-initiated)
- [7. NVSHMEM + NCCL 混用](#7-nvshmem--nccl-混用)
- [8. 性能分析与调优](#8-性能分析与调优)
- [9. NVSHMEM vs NCCL vs MPI：一图看清](#9-nvshmem-vs-nccl-vs-mpi一图看清)
- [10. 学习路线图（1~2 周）](#10-学习路线图12-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 NVSHMEM？

用过 NCCL 你会发现它有两个天花板：

1. **粒度粗**——NCCL 的原语是**整数组**级的 AllReduce/AllGather，没法在 kernel 里做"小消息、细粒度"通信；
2. **Host-initiated**——每次通信要 host 侧调 API，无法在一个 kernel 内既算又通信。

**NVSHMEM 完全不同**：它把**通信原语暴露到 device 侧**，你在 `__global__ void kernel` 内部就能直接 `nvshmem_put(dst_ptr, src_ptr, size, remote_pe)` 写别的 GPU 的显存——**单边、异步、低延迟、可与计算融合**。

### 0.1 一句话对比

| 需求 | NCCL | **NVSHMEM** |
|:--|:--|:--|
| 训练梯度 AllReduce | ✅ 最优 | ⚠️ 可以但不主流 |
| kernel 内小消息细粒度通信 | ❌ | **✅ 唯一选择** |
| 单边 put/get（不用远端配合） | ❌ | **✅ 核心特性** |
| GPU-initiated collective | ❌ | **✅** |
| 与 kernel 计算融合 | ❌（要出 kernel 调 API）| **✅ 融合到一个 kernel** |
| 多 GPU FFT / 图遍历 | 分成多阶段 | **一个 kernel 搞定** |

### 0.2 NVSHMEM 现在有多重要？

- **NVIDIA 官方开源库**，专为多 GPU HPC / 大模型细粒度并行设计；
- **参考 OpenSHMEM 标准**（分布式共享内存），把它做到 GPU；
- **NVIDIA Megatron-LM 的 tensor parallel Attention 融合**用它；
- **多 GPU 求解器 / 图算法（cuGraph 内部）** 大量使用；
- **Hopper（H100） cluster 编程**的官方推荐方式；
- **未来 Blackwell 更强 NVLink 域** 下这类"kernel-initiated 通信"会更重要。

**一句话**：**NVSHMEM = "在 kernel 内部就能直接读写别的 GPU 显存"的官方 API**——多 GPU 融合 kernel 的通信底座。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **NS1 入门** | 会 host 侧初始化，kernel 内用 `nvshmem_put/get` |
| **NS2 熟练** | 会 signal/wait、barrier、point-to-point 异步 |
| **NS3 高阶** | 会 GPU-initiated collective（AllReduce/Broadcast in kernel） |
| **NS4 专家** | 与 NCCL 混合使用，写多 GPU 融合 kernel（Attention/FFT） |

**建议**：**5~7 天到 NS1**，**1~2 周到 NS2/NS3**（覆盖 90% 场景）。

---

## 1. NVSHMEM 是什么：一句话讲清 vs NCCL / vs MPI

### 1.1 NVSHMEM 的定义

> **NVSHMEM = NVIDIA 官方基于 OpenSHMEM 标准的 GPU 分区全局地址空间（PGAS）库**。它让每个 GPU 看到一块**对称堆（symmetric heap）**——所有 PE（Processing Element = 一个 GPU）在这块堆上分配同名对象，任何 PE 都能**用一句 `nvshmem_put` 单边**读写**任何其他 PE 的对应内存**，无需远端 CPU/GPU 参与。

关键三点：

1. **PGAS 模型**——全局地址空间分区到各 PE，编程上像共享内存；
2. **单边通信**——`put/get/signal` 只有发起方参与，远端不需要 recv；
3. **Device-callable**——通信原语可以在 kernel 内直接调用。

### 1.2 NVSHMEM vs NCCL vs MPI

| 维度 | MPI | **NCCL** | **NVSHMEM** |
|:--|:--|:--|:--|
| 通信模型 | 双边 send/recv | 集合通信 | **单边 PGAS** |
| 粒度 | 消息级 | 数组级 | **字节级 / 元素级** |
| 谁 initiate | Host | Host | **Host 或 Device** |
| kernel 内可调 | ❌ | ❌ | **✅** |
| 融合 kernel + comm | ❌ | ❌ | **✅** |
| AI 训练 AllReduce 主力 | ❌ | ✅ | ⚠️ |
| HPC 细粒度 | MPI-RMA | ❌ | **✅ 首选** |
| 学习曲线 | 中 | 低 | **中~陡** |

**记忆口诀**：
- **粗粒度、AI 训练** → **NCCL**；
- **细粒度、kernel 内通信、融合 kernel** → **NVSHMEM**；
- **传统 HPC** → **MPI**；
- **三者可以共存混用**。

### 1.3 一张图看清 NVSHMEM 在栈里的位置

```
┌──────────────────────────────────────────────────────────┐
│  Megatron TP / 多 GPU FFT / cuGraph / 自研融合 kernel      │
├──────────────────────────────────────────────────────────┤
│  NVSHMEM（device-callable put/get/signal/barrier/coll）    │
├──────────────────────────────────────────────────────────┤
│  NCCL（集合通信，host-initiated）                          │
├──────────────────────────────────────────────────────────┤
│  NVLink / NVSwitch / GPUDirect RDMA (IB) / PCIe           │
├──────────────────────────────────────────────────────────┤
│  CUDA Runtime + Driver + UCX/GDR                          │
├──────────────────────────────────────────────────────────┤
│  GPU 硬件（多 GPU / 多节点）                                │
└──────────────────────────────────────────────────────────┘
```

**核心洞察**：NVSHMEM 把 "**GPU-initiated、kernel 内、单边通信**" 这件本来在 CUDA 生态里缺失的能力补齐——这是"融合式多 GPU kernel"的基石。

---

## 2. 环境搭建（Linux 首选）

### 2.1 平台

| 平台 | 支持 | 说明 |
|:--|:--|:--|
| Linux 原生 | ✅ 完整 | **首选** |
| WSL2 | ⚠️ 单机可 | 学习用 |
| Windows 原生 | ❌ | 用 WSL2 或 Linux |

### 2.2 安装

从 <https://developer.nvidia.com/nvshmem> 下载（需 NVIDIA 账号）。或用 conda：

```bash
conda install -c nvidia nvshmem
# 或从源码 tar 解压到 /opt/nvshmem
export NVSHMEM_HOME=/opt/nvshmem
export LD_LIBRARY_PATH=$NVSHMEM_HOME/lib:$LD_LIBRARY_PATH
```

依赖 CUDA + MPI（OpenMPI / MVAPICH）或 Hydra 引导。

### 2.3 一步验证：hello_nvshmem.cu

```cpp
#include <nvshmem.h>
#include <nvshmemx.h>
#include <cuda_runtime.h>
#include <cstdio>

__global__ void kernel(int* dst_on_pe1, int mype, int npes) {
    if (threadIdx.x == 0) {
        int val = 100 + mype;
        // 单边：把 val 写到 PE 1 的 dst_on_pe1
        if (mype == 0 && npes >= 2) {
            nvshmem_int_p(dst_on_pe1, val, /*pe=*/1);
        }
    }
}

int main(int argc, char** argv) {
    nvshmem_init();
    int mype = nvshmem_my_pe();
    int npes = nvshmem_n_pes();
    cudaSetDevice(mype);

    // symmetric heap 分配（所有 PE 都有一份同名对象）
    int* d = (int*)nvshmem_malloc(sizeof(int));
    cudaMemset(d, 0, sizeof(int));

    kernel<<<1, 32>>>(d, mype, npes);
    cudaDeviceSynchronize();
    nvshmem_barrier_all();

    int h = 0;
    cudaMemcpy(&h, d, sizeof(int), cudaMemcpyDeviceToHost);
    printf("PE %d: got %d\n", mype, h);

    nvshmem_free(d);
    nvshmem_finalize();
}
```

编译 & 运行（多 PE 需要 mpirun/nvshmrun）：

```bash
nvcc -O3 -std=c++17 -arch=sm_86 hello_nvshmem.cu \
     -I$NVSHMEM_HOME/include -L$NVSHMEM_HOME/lib -lnvshmem -lcuda \
     -o hello_nvshmem

# 2 PE 运行（有 2 GPU 时）
nvshmrun -n 2 ./hello_nvshmem
# 或者
mpirun -n 2 ./hello_nvshmem
```

期望：PE 1 的输出 `PE 1: got 100`（因为 PE 0 单边写了 100 到 PE 1）。

### 2.4 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| Windows 找不到库 | 不支持 | 用 WSL2 或 Linux |
| 单进程运行没通信 | 只有 1 PE | 用 mpirun / nvshmrun -n N |
| 远端未见更新 | 忘 quiet/fence/barrier | put 后 `nvshmem_quiet()` 或 barrier |
| symmetric heap OOM | 每 PE 都占同大小 | 减小 nvshmem_malloc 大小 |
| kernel 内挂死 | collective 未参与全 PE | 确保所有 PE 都进入同一 collective |

---

## 3. NVSHMEM 的心智模型：PE / Symmetric Heap / One-sided

### 3.1 PE（Processing Element）

- **一个 PE = 一个 GPU**（通常）；
- **PE 编号** 0..N-1，`nvshmem_my_pe()` 取自己，`nvshmem_n_pes()` 取总数；
- PE 与 MPI rank 一一对应（用 MPI 引导时）。

### 3.2 Symmetric Heap（对称堆）

**这是 NVSHMEM 的核心概念**：

```cpp
int* d = (int*)nvshmem_malloc(sizeof(int));
```

- 这一句在**所有 PE**上都会执行；
- **每个 PE 都分配了一块同名对象**（同大小、同虚拟地址意义）；
- 你可以在 PE X 上用 `nvshmem_put(d, val, /*pe=*/Y)`——**PE Y 的 d 就是 PE Y 上那份**；
- **不需要交换指针**，NVSHMEM 内部维护映射。

**类比**：像 MPI 里的 `MPI_Win_allocate_shared`，或 PGAS 语言（UPC/Chapel）里的分布式数组。

### 3.3 One-sided（单边通信）

**双边** vs **单边**：

- MPI 是**双边**：`MPI_Send` 必须配对 `MPI_Recv`，双方都要参与；
- NVSHMEM 是**单边**：`nvshmem_put(dst, src, N, pe)` 只有发起方参与，**目标 PE 不用配合**。

**优势**：
- 不需要接收方"等"，实现真正异步；
- 融合到 kernel 内极方便——你算完一点就 put 一点，不用退出 kernel。

**代价**：需要**同步原语**（barrier、signal、quiet）保证一致性。

---

## 4. 第一个程序：kernel 内 `nvshmem_put`

见 2.3 节代码。**要点**：

- `nvshmem_init/finalize`：与 CUDA 上下文类似，一开一关；
- `nvshmem_malloc`：对称堆分配；
- kernel 内 `nvshmem_int_p(dst_ptr, val, target_pe)`：单边写；
- `nvshmem_barrier_all()`：等所有 PE 到齐，同时刷新未完成的 put。

### 4.1 完整语义（何时能看到远端更新？）

- **put 是异步的**——发起后不保证到达；
- **需要 quiet / fence / barrier** 才能确保远端已经收到：
  - `nvshmem_quiet()`：本 PE 之前所有 put 全部完成；
  - `nvshmem_fence()`：只保证发到同一目标的顺序；
  - `nvshmem_barrier_all()`：全 PE 同步 + quiet 效果。

### 4.2 6 个新手常见坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | 直接读远端 put 结果无 quiet | 拿旧值 | quiet/barrier |
| 2 | symmetric heap OOM | 各 PE 同尺寸 | 减小 |
| 3 | Windows / 单 GPU 玩 | 无意义 | Linux 多 GPU |
| 4 | 未 mpirun 启动 | 只有 1 PE | 用 nvshmrun/mpirun -n N |
| 5 | 混用 cudaMalloc + nvshmem_put | 崩 | 目标必须是 symmetric heap |
| 6 | kernel 内 collective 不全 PE 都到 | 死锁 | 保证全 PE 进入 |

---

## 5. Point-to-Point：Put / Get / Signal / Wait

### 5.1 Put（写远端）

```cpp
nvshmem_int_p(dst, val, target_pe);         // 单元素
nvshmem_int_put(dst, src, N, target_pe);    // 数组
nvshmem_putmem(dst, src, bytes, target_pe); // 字节流
```

### 5.2 Get（读远端）

```cpp
int val = nvshmem_int_g(src, source_pe);
nvshmem_int_get(dst, src, N, source_pe);
```

### 5.3 Signal + Wait（关键的同步原语）

**问题**：我 put 完后怎么让远端知道"我给你数据了"？答：写一个 flag，远端 spin-wait。

```cpp
// PE 0 端 (kernel 内)
nvshmem_int_put(remote_buf, my_data, N, 1);
nvshmem_fence();
nvshmem_int_put(remote_flag, 1, 1);          // 通知
// 或用 put_signal（原子的 put + signal）:
nvshmem_putmem_signal(remote_buf, my_data, N,
                     remote_flag, 1,
                     NVSHMEM_SIGNAL_SET, 1);

// PE 1 端 (kernel 内)
nvshmem_int_wait_until(local_flag, NVSHMEM_CMP_EQ, 1);  // 等标志
// 之后 remote_buf 数据可读
```

**这就是 producer-consumer 的 GPU 版**，全部在 kernel 内完成。

---

## 6. Collective：Barrier / AllReduce / Broadcast（GPU-initiated）

### 6.1 Barrier

```cpp
nvshmem_barrier_all();               // Host 侧
nvshmem_barrier_all_block();          // Device 侧（block 级）
```

### 6.2 GPU-initiated AllReduce（NVSHMEM 独有）

```cpp
__global__ void kernel(float* buf) {
    // ... 每 PE 计算 buf ...
    nvshmemx_float_sum_reduce_block(NVSHMEM_TEAM_WORLD, dst, src, N);
    // ... 用 dst 继续算 ...
}
```

**性能优势**：kernel 不出去，避免 host 侧 launch overhead——**融合 kernel** 的关键。

**对比 NCCL**：NCCL 的 AllReduce 是 host launch 的，NVSHMEM 可以放到 kernel 内。

---

## 7. NVSHMEM + NCCL 混用

**推荐组合**：
- **粗粒度、大数组 AllReduce（DDP 训练）** → NCCL；
- **细粒度、kernel 内通信（融合算子）** → NVSHMEM；
- 二者可以在同一程序共存（分别 init/finalize）。

**Megatron 的 tensor parallel** 就是这么做的：TP 内部的 AllReduce 可以走 NVSHMEM（更 fine-grained），DP 的 AllReduce 走 NCCL。

---

## 8. 性能分析与调优

### 8.1 三条铁律

1. **能融合到 kernel 就融合**——省 host launch overhead；
2. **用 put_signal 而非 put + 单独 signal**——原子性 + 快；
3. **对称堆预分配**——避免多次 alloc/free。

### 8.2 Nsight Systems

看：
- kernel 内 put 与 compute 是否交错；
- NVLink 利用率（`nvidia-smi topo -m` 看拓扑）。

---

## 9. NVSHMEM vs NCCL vs MPI：一图看清

| 维度 | MPI | NCCL | **NVSHMEM** |
|:--|:--|:--|:--|
| 模型 | 双边 send/recv | 集合通信 | **单边 PGAS** |
| GPU 内可调 | ❌ | ❌ | **✅** |
| 融合 kernel + 通信 | ❌ | ❌ | **✅** |
| 大集合 AllReduce | ✅ | ✅ 最佳 | ✅ |
| 细粒度小消息 | ✅（RMA）| ❌ | **✅** |
| 学习曲线 | 中 | 低 | **陡** |
| 主流场景 | HPC | AI 训练 | **HPC + 融合 kernel** |

**选型**：
- **AI 训练 DDP** → NCCL（默认）；
- **多 GPU 融合算子 / kernel 内通信** → NVSHMEM；
- **传统 HPC / CPU 通信** → MPI；
- **常见做法**：MPI 引导 + NCCL 干集合 + NVSHMEM 干融合。

---

## 10. 学习路线图（1~2 周）

- **Day 1~3**：init/finalize、symmetric heap、简单 put/get；
- **Day 4~6**：signal + wait，producer-consumer；
- **Day 7~10**：GPU-initiated collective in kernel；
- **Day 11~14**：与 NCCL/MPI 混用，实战融合 Attention 或多 GPU FFT。

---

## 11. 精选资源与踩坑清单

### 11.1 必读

| 资源 | 链接 |
|:--|:--|
| NVSHMEM 官方页 | <https://developer.nvidia.com/nvshmem> |
| NVSHMEM 文档 | <https://docs.nvidia.com/nvshmem/api/> |
| OpenSHMEM 标准 | <http://www.openshmem.org/> |
| Megatron-LM（NVSHMEM 实战）| <https://github.com/NVIDIA/Megatron-LM> |
| NVSHMEM examples | 官方 tar 里 `perftest/` 目录 |

### 11.2 踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| Windows / 单 GPU 无意义 | 平台 | Linux + 多 GPU |
| 远端读到旧值 | 忘 quiet/barrier | 加同步 |
| kernel 死锁 | collective 未全 PE | 全 PE 进入 |
| 对称堆分配失败 | 太大 | 减小 |
| 未 mpirun / nvshmrun | 单 PE 运行 | 加 -n N |
| put 到非 symmetric heap | 崩 | 目标必须 nvshmem_malloc |
| 与 NCCL 冲突 | 内部资源竞争 | 各自 init/finalize，分 stream |
| MPI 引导错 | 忘 MPI_Init | 先 MPI_Init 再 nvshmem_init_attr |
| Signal 值溢出 | 用了非 64-bit | signal 类型是 uint64_t |
| 慢 | 未走 NVLink | `nvidia-smi topo -m` 检查 |

### 11.3 一句话总结

> **NVSHMEM = "在 kernel 内部就能直接读写别的 GPU 显存"的官方 API**——PGAS 模型的 GPU 版，单边通信 + GPU-initiated collective。**多 GPU 融合 kernel 的通信底座**。学它 = 打开"通信与计算完全融合"的新世界。
>
> **NCCL 解决"训练 AllReduce"，NVSHMEM 解决"kernel 内细粒度通信"**——二者互补，都是大模型 + HPC 分布式的必修。

---

**祝你写出通信与计算完全融合的 GPU-native 多卡 kernel。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
