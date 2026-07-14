# CUDA Graphs 学习指南：干掉 Kernel Launch 开销的性能杀器

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：会训推小模型 / batch=1 大模型推理、发现 GPU 利用率上不去、Nsight timeline 上看到"每个 kernel 之间都有缝"的 AI 工程师。
> **目标**：读完本文，你能用 3 种方式（stream capture / 显式构建 / PyTorch 一键）把上千个小 kernel 打成一个"图"，一次 launch 全跑完，性能提升 20%~2×。

---

## 目录

- [0. 写在最前：为什么小 kernel 场景 CUDA Graphs 是"神器"](#0-写在最前为什么小-kernel-场景-cuda-graphs-是神器)
- [1. 核心概念：图、节点、依赖、实例](#1-核心概念图节点依赖依赖实例)
- [2. 三种构建方式](#2-三种构建方式)
- [3. PyTorch 一键使用](#3-pytorch-一键使用)
- [4. vLLM / TensorRT-LLM 里的 Graphs 实战](#4-vllm--tensorrt-llm-里的-graphs-实战)
- [5. 三大坑：动态 shape / 内存地址 / CPU 侧依赖](#5-三大坑动态-shape--内存地址--cpu-侧依赖)
- [6. Graph 更新（Graph Update）：不重建图改参数](#6-graph-更新graph-update不重建图改参数)
- [7. 什么时候用、什么时候不用](#7-什么时候用什么时候不用)
- [8. 学习路线图（1~2 周）](#8-学习路线图12-周)
- [9. 精选资源与官方链接](#9-精选资源与官方链接)

---

## 0. 写在最前：为什么小 kernel 场景 CUDA Graphs 是"神器"

### 0.1 一个"血泪现场"

你部署了一个 LLM 推理服务，batch=1，Nsight timeline 长这样：

```
GPU:  ▓ ▓  ▓ ▓  ▓ ▓   ▓ ▓   ▓ ▓   ▓ ▓  ...
      ↑ ↑  ↑ ↑
    这些空白就是 kernel 之间的 launch overhead！
```

**每次 `kernel<<<...>>>` 都有 ~5~50 μs 的 CPU → GPU 通信开销**。一个 LLM 一次 forward 有几百个 kernel，光 launch 就吃掉 30%+ 的时间。

### 0.2 CUDA Graphs 的解法

```
传统模式：CPU 一次次告诉 GPU："跑 k1, 跑 k2, 跑 k3, ..."
             ↑ ↑ ↑ 每次都有开销

Graph 模式：CPU 一次性把整张"作业单"交给 GPU：
            "这是 k1→k2→k3→...→kn 的图，你按顺序跑完再叫我"
             ↑ 只有一次 launch 开销
```

**收益**：
- **kernel launch 次数从 N → 1**；
- **timeline 上的空隙消失**；
- **典型收益 20%~50%，某些场景 2×**（如小 batch LLM decode）。

### 0.3 一句话总结

> **CUDA Graphs = 把一堆 GPU 操作打包成一个"批处理任务"**——一次提交、GPU 内部按依赖执行。适用于**重复执行、结构固定**的场景（训练循环、LLM decode、小 batch 推理）。

### 0.4 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **G1 认知** | 说清 launch overhead、graph capture、graph replay |
| **G2 会用** | 用 `torch.cuda.CUDAGraph` 加速一段代码 |
| **G3 会调** | 处理动态 shape、graph update、pool 复用 |
| **G4 会造** | 读懂 vLLM/TRT-LLM 的 graph 分桶策略 |

---

## 1. 核心概念：图、节点、依赖、实例

### 1.1 四个术语

| 术语 | 英文 | 含义 |
|:--|:--|:--|
| **图** | `cudaGraph_t` | 一个"作业模板"，包含节点和依赖关系 |
| **节点** | `cudaGraphNode_t` | 一个操作（kernel、memcpy、memset、host func 等）|
| **依赖** | dependency | 节点间的先后关系（DAG）|
| **图实例** | `cudaGraphExec_t` | 图的"编译后可执行对象"，可以反复 `launch` |

### 1.2 生命周期

```
构建阶段（慢，只做一次）：
    ① 创建 graph (cudaGraphCreate 或 stream capture)
    ② 添加节点（隐式或显式）
    ③ 实例化：cudaGraphInstantiate(graph → graphExec)

执行阶段（快，反复用）：
    while training/inference:
        cudaGraphLaunch(graphExec, stream)   # ← 一次调用跑完整个图
```

### 1.3 支持的节点类型

| 节点类型 | 含义 |
|:--|:--|
| **Kernel** | CUDA kernel（最常见）|
| **Memcpy** | 显存拷贝 |
| **Memset** | 显存置值 |
| **Host** | CPU 回调函数（谨慎用，会拖累性能）|
| **Child Graph** | 嵌套子图 |
| **Empty** | 占位符（用于依赖关系）|
| **Event** | 事件同步 |
| **Semaphore** | 跨 stream 同步 |

---

## 2. 三种构建方式

### 2.1 方式一：Stream Capture（最常用）

**思路**：你把要跑的代码"录一遍"，CUDA 自动生成 graph。

```cpp
cudaStream_t stream;
cudaStreamCreate(&stream);

// ① 开始录制
cudaStreamBeginCapture(stream, cudaStreamCaptureModeGlobal);

// ② 正常写代码（就像 profile 之前一样）
kernel1<<<...,stream>>>(...);
kernel2<<<...,stream>>>(...);
cudaMemcpyAsync(..., stream);
kernel3<<<...,stream>>>(...);

// ③ 结束录制，拿到 graph
cudaGraph_t graph;
cudaStreamEndCapture(stream, &graph);

// ④ 实例化
cudaGraphExec_t graphExec;
cudaGraphInstantiate(&graphExec, graph, nullptr, nullptr, 0);

// ⑤ 反复执行
for (int i = 0; i < 1000; i++) {
    cudaGraphLaunch(graphExec, stream);
}
```

**优点**：无痛，几乎不用改代码。
**缺点**：只能记录"这一次执行"，如果第二次执行 shape 不同，会崩。

### 2.2 方式二：显式构建（灵活但繁琐）

**思路**：手动 `cudaGraphAddKernelNode`、`cudaGraphAddDependency`。

```cpp
cudaGraph_t graph;
cudaGraphCreate(&graph, 0);

// 添加 kernel 节点
cudaGraphNode_t node1, node2;
cudaKernelNodeParams kParams = {...};
cudaGraphAddKernelNode(&node1, graph, nullptr, 0, &kParams);

// 添加依赖：node2 依赖 node1
cudaGraphAddKernelNode(&node2, graph, &node1, 1, &kParams);
```

**适用**：图结构动态变化、需要精细控制依赖。**AI 场景很少直接用**。

### 2.3 方式三：PyTorch 一键（Python 用户首选）

见下一章。

---

## 3. PyTorch 一键使用

### 3.1 最简示例

```python
import torch

# 准备静态输入
x = torch.randn(128, 512, device='cuda')

# 1. Warmup（很重要，让 cuBLAS/cuDNN 选好算法）
for _ in range(3):
    y = model(x)
torch.cuda.synchronize()

# 2. 录制
g = torch.cuda.CUDAGraph()
with torch.cuda.graph(g):
    y = model(x)

# 3. 执行（要复用 x 这个 tensor 的内存，改变 x 的内容即可）
for step in range(1000):
    x.copy_(new_input)   # ← 关键：不新建 tensor，只改内容
    g.replay()
    result = y.clone()   # 输出也是复用的内存
```

### 3.2 make_graphed_callables：最优雅方式

```python
# PyTorch 提供的高层封装
model_graphed = torch.cuda.make_graphed_callables(
    model,
    sample_args=(x,),
)

# 直接调，内部自动 replay
for step in range(1000):
    y = model_graphed(x)
```

**注意**：`sample_args` 的**shape 必须和后续调用完全一致**。

### 3.3 训练循环也能用（含 optimizer）

```python
# 静态输入/输出/梯度
static_input = torch.randn(bsz, dim, device='cuda')
static_target = torch.randn(bsz, dim, device='cuda')

# Warmup
for _ in range(3):
    optimizer.zero_grad()
    loss = loss_fn(model(static_input), static_target)
    loss.backward()
    optimizer.step()

# 捕获整个训练步
g = torch.cuda.CUDAGraph()
optimizer.zero_grad(set_to_none=True)
with torch.cuda.graph(g):
    static_output = model(static_input)
    static_loss = loss_fn(static_output, static_target)
    static_loss.backward()
    optimizer.step()

# Replay
for x, t in data_loader:
    static_input.copy_(x)
    static_target.copy_(t)
    g.replay()
```

---

## 4. vLLM / TensorRT-LLM 里的 Graphs 实战

### 4.1 为什么 LLM decode 阶段特别需要 CUDA Graphs

LLM decode 是**极度小 batch、极度重复**的场景：

- 一次 decode step = 前向一次 = 几百个小 kernel；
- 每 step 只算 1 个 token；
- **kernel launch 开销占比高达 40%~60%**。

CUDA Graphs 是 LLM 推理的**必备优化**。

### 4.2 vLLM 的分桶策略

vLLM 支持不同 batch size，但每个 shape 都要单独一张 graph：

```python
# 简化版 vLLM 逻辑
CAPTURED_BATCH_SIZES = [1, 2, 4, 8, 16, 32, 64, ...]

graphs = {}
for bsz in CAPTURED_BATCH_SIZES:
    static_input = torch.zeros(bsz, ..., device='cuda')
    g = torch.cuda.CUDAGraph()
    with torch.cuda.graph(g):
        model(static_input)
    graphs[bsz] = g

# 运行时：把 batch 补齐（padding）到最近的 captured 大小
def decode(batch):
    bsz = pick_nearest(len(batch), CAPTURED_BATCH_SIZES)
    padded = pad_to(batch, bsz)
    static_inputs[bsz].copy_(padded)
    graphs[bsz].replay()
```

**代价**：一开始要构建 20+ 张 graph（几秒到几分钟）；**收益**：decode 阶段快 30%~2×。

### 4.3 TensorRT-LLM 的 Graph 优化

TensorRT-LLM 更激进：**Enqueue + Graph + In-flight Batching** 三重优化：
- 引擎内部自动打图；
- 支持不同 seq_len 的 graph pool；
- 与 Paged KV Cache 深度集成。

---

## 5. 三大坑：动态 shape / 内存地址 / CPU 侧依赖

### 5.1 坑一：Shape 必须完全一致

```python
g = torch.cuda.CUDAGraph()
with torch.cuda.graph(g):
    y = model(x)   # x.shape = (32, 512)

x_new = torch.randn(64, 512, ...)   # ← shape 变了
# g.replay()  ❌ 崩！或者结果错
```

**解法**：
- Padding 到固定 shape（vLLM 的做法）；
- 每个 shape 一张 graph（Graph pool）。

### 5.2 坑二：Tensor 地址必须固定

```python
# ❌ 错误：每次新建 tensor，地址变了
for i in range(1000):
    x = torch.randn(128, 512, device='cuda')   # ← 新地址
    g.replay()   # 用的是旧地址

# ✅ 正确：复用 tensor
x = torch.randn(128, 512, device='cuda')
for i in range(1000):
    x.copy_(new_input)   # ← 地址不变，只改内容
    g.replay()
```

### 5.3 坑三：Graph 内不能有 CPU 依赖

**图内 kernel 之间不能等 CPU**：

```python
# ❌ 错误：graph 内做 CPU 判断
with torch.cuda.graph(g):
    y = model(x)
    if y.max().item() > 0.5:   # ← 需要 CPU 同步，会破坏 capture
        y = model2(x)
```

**Data-dependent control flow 只能通过 Conditional Graph（CUDA 12.4+）或图外分支解决。**

---

## 6. Graph 更新（Graph Update）：不重建图改参数

**痛点**：模型权重更新了怎么办？重建 graph 太慢！

**解法**：`cudaGraphExecKernelNodeSetParams` —— 只改节点参数，不重建图：

```cpp
// 只改一个 kernel 节点的参数
cudaKernelNodeParams newParams = ...;
cudaGraphExecKernelNodeSetParams(graphExec, node, &newParams);
```

**PyTorch 里的等价**：本质上通过复用 tensor 地址 + 修改数据，达到"图不变但内容变"的效果。

---

## 7. 什么时候用、什么时候不用

### 7.1 决策矩阵

| 场景 | 用不用？ | 理由 |
|:--:|:--:|:--|
| **训练大 batch (bsz≥64) 大模型** | ❌ 不用 | Kernel 本身大，launch 开销占比小 |
| **训练小 batch 小模型（LSTM/RNN 家族）** | ✅ 用 | Kernel 密集且小 |
| **LLM decode (batch=1)** | ✅ 必用 | 完美场景 |
| **LLM prefill / 长序列** | ❌ 不用 | Kernel 大，且 seq_len 变 |
| **强化学习 rollout** | ✅ 用 | 高频小 forward |
| **推理 batch server (动态 shape)** | ✅ 用（分桶）| vLLM 已证明 |
| **首次调试 / 开发** | ❌ 不用 | 排错困难，先跑通再优化 |

### 7.2 三大反直觉

1. **大模型不一定收益大** —— 关键看 kernel 密集度而非模型大小；
2. **Warmup 时间可能吃掉几秒到几分钟** —— 服务启动慢一点是代价；
3. **和 `torch.compile` 可以叠加** —— compile 后再 capture，是 vLLM 的常用组合拳。

---

## 8. 学习路线图（1~2 周）

### Week 1：入门 + 简单场景
- 读 CUDA Graphs 官方文档；
- 用 `torch.cuda.CUDAGraph` 加速一个 MLP 训练循环，测速对比；
- 用 Nsight Systems 看 timeline 前后对比。

### Week 2（可选）：LLM 推理场景
- 读 vLLM 的 `worker/model_runner.py` 里的 graph 逻辑；
- 尝试给自己的 LLM 推理加分桶 graph；
- 用 Nsight 看 decode 阶段的 timeline 优化效果。

---

## 9. 精选资源与官方链接

### 9.1 官方文档
- **CUDA C Programming Guide - Graphs 章节**：<https://docs.nvidia.com/cuda/cuda-c-programming-guide/#cuda-graphs>
- **PyTorch CUDA Graphs Tutorial**：<https://pytorch.org/docs/stable/notes/cuda.html#cuda-graphs>
- **make_graphed_callables API**：<https://pytorch.org/docs/stable/generated/torch.cuda.make_graphed_callables.html>

### 9.2 优秀开源案例
- **vLLM model_runner**：<https://github.com/vllm-project/vllm/blob/main/vllm/worker/model_runner.py>
- **NVIDIA 官方 examples**：<https://github.com/NVIDIA/cuda-samples/tree/master/Samples/3_CUDA_Features/graphs>

### 9.3 姊妹篇
- [面向 AI 的 CUDA 编程学习指南](./CUDA-AI编程学习指南.md)（CUDA 基础）
- [Nsight 性能分析学习指南](./Nsight性能分析学习指南.md)（怎么诊断 launch overhead）
- [vLLM 编程学习指南](./vLLM编程学习指南.md)（Graph 在推理引擎里的实战）
- [TensorRT-LLM 编程学习指南](./TensorRT-LLM编程学习指南.md)

---

**版权声明**：本文由汪亮（bertonwang）撰写，转载请注明出处。欢迎邮件（<47608843@qq.com>）交流勘误。

**一句话总结全文**：**CUDA Graphs = 把一堆小 kernel 打包成一个批处理任务**——重复执行、结构固定的场景（LLM decode、小 batch 推理、RL rollout）能吃到 20%~2× 加速。**vLLM 和 TensorRT-LLM 都靠它压榨最后一滴性能**。
