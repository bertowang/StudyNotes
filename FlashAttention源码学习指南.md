# FlashAttention 源码学习指南：大模型时代的地基算子

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：会用 `F.scaled_dot_product_attention`、读过 Triton 或 CUDA 一些例子，但对 FlashAttention v1/v2/v3 的 online softmax、tile 分块、warp specialization 一知半解的 AI 工程师。
> **目标**：读完本文，你不仅能说清 FlashAttention 为什么快 5~10 倍，还能自己用 Triton 写一版 forward，看得懂 CUTLASS 的 v3 源码。

---

## 目录

- [0. 写在最前：为什么 FlashAttention 必须精读](#0-写在最前为什么-flashattention-必须精读)
- [1. 标准 Attention 慢在哪？](#1-标准-attention-慢在哪)
- [2. FlashAttention v1：Tiling + Online Softmax](#2-flashattention-v1tiling--online-softmax)
- [3. FlashAttention v2：调整并行 + 重排循环](#3-flashattention-v2调整并行--重排循环)
- [4. FlashAttention v3：Hopper 专属（TMA + WGMMA + Warp Specialization）](#4-flashattention-v3hopper-专属tma--wgmma--warp-specialization)
- [5. Triton 版最小实现（80 行）](#5-triton-版最小实现80-行)
- [6. 变体家族：Paged / MQA / GQA / Sliding Window](#6-变体家族paged--mqa--gqa--sliding-window)
- [7. 工程实践：什么时候该自己写、什么时候调库](#7-工程实践什么时候该自己写什么时候调库)
- [8. 学习路线图（4~6 周）](#8-学习路线图46-周)
- [9. 精选资源与官方链接](#9-精选资源与官方链接)

---

## 0. 写在最前：为什么 FlashAttention 必须精读

**一个残酷事实**：整个大模型时代，性能优化的**头号技术突破**就是 FlashAttention（Tri Dao, 2022）。它做到了三件"看似不可能"的事：

1. **数学上等价** —— 输出和标准 Attention **一模一样**（不是近似）；
2. **速度快 2~10 倍** —— 尤其在长序列上；
3. **显存从 O(N²) 降到 O(N)** —— 让 100K+ 长上下文成为可能。

**为什么你必须精读**：
- vLLM、TensorRT-LLM、SGLang **全部依赖它**；
- Triton 官方教程的 crown jewel 就是它；
- CUTLASS 3.x 的最佳实践案例就是它；
- **面试大模型 infra，几乎必问**。

**懂 FlashAttention = 懂了当代 GPU 性能优化的所有精髓**：tiling、online softmax、operator fusion、warp specialization、async copy……

### 0.1 一句话总结

> **FlashAttention 就是把 `softmax(QK^T)V` 从"O(N²) 显存的 3 次遍历"变成"O(N) 显存的 1 次融合遍历"**——秘诀是 **tiling（分块计算）+ online softmax（增量归一）**。

### 0.2 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **G1 认知** | 说清 v1/v2/v3 每一代解决了什么问题 |
| **G2 会读** | 能看懂官方 Triton 版 forward 代码 |
| **G3 会写** | 能自己用 Triton 从零实现 forward + backward |
| **G4 会造** | 能改造 FlashAttention 支持自定义 mask / 位置编码 / 稀疏模式 |

**建议**：本文带你到 **G2**，配合手写 Triton 一遍冲到 **G3**。

---

## 1. 标准 Attention 慢在哪？

### 1.1 数学公式回顾

$$
\text{Attention}(Q, K, V) = \text{softmax}\!\left(\frac{QK^T}{\sqrt{d}}\right) V
$$

其中 $Q, K, V \in \mathbb{R}^{N \times d}$，$N$ 是序列长度，$d$ 是 head_dim。

### 1.2 朴素实现的三大罪

```python
# 朴素实现（PyTorch 一行流）
S = Q @ K.T / sqrt(d)     # ① 生成 N×N 矩阵
P = softmax(S, dim=-1)     # ② 又是 N×N
O = P @ V                  # ③ 最后才用 V
```

**三个致命问题**：

| 问题 | 后果 |
|:--|:--|
| **中间矩阵 S、P 都是 N×N** | N=8K 时，一份 fp16 矩阵占 128 MB；一层就爆显存 |
| **要遍历 HBM 3 次** | 读 QK、写 S、读 S、写 P、读 P 和 V、写 O —— IO 至少 4×N² |
| **完全无法融合** | softmax 需要全局最大值 → 必须 materialize S → 无法 tile |

### 1.3 关键洞察：GPU 快在算力，慢在访存

A100 的算力/带宽比 = **312 TFLOPS / 1.5 TB/s ≈ 200 FLOPs/Byte**。

**结论**：只要能减少访存，即使多算几遍也是赚的。这就是 FlashAttention 的核心思想 —— **用重计算换 HBM 访存**。

---

## 2. FlashAttention v1：Tiling + Online Softmax

### 2.1 核心思想（图示）

```
标准 Attention：
    ┌─────────────────┐
    │      S = QK^T   │  ← 完整 N×N，写回 HBM
    └─────────────────┘
           ↓
    ┌─────────────────┐
    │  P = softmax(S) │  ← 再读一遍，写一遍
    └─────────────────┘
           ↓
    ┌─────────────────┐
    │       O = PV    │
    └─────────────────┘

FlashAttention：
    for i in range(N / Br):      # 外循环：Q 的分块
        for j in range(N / Bc):  # 内循环：K, V 的分块
            # 全在 SRAM 里完成，S 从未写回 HBM
            load Q_i, K_j, V_j to SRAM
            S_ij = Q_i @ K_j^T
            update running max, sum
            O_i += (softmax 增量) @ V_j
```

**S 从来没有完整存在于 HBM**——只有一小块 S_ij 存在于 SRAM。

### 2.2 Online Softmax：算法核心

**问题**：softmax 的分母是**所有元素**的 exp 之和，必须遍历一遍才能算——这不就还是要 materialize S 吗？

**解法**：**online softmax**（Milakov & Gimelshein, 2018）。它把"两遍扫描"变成"一遍扫描 + 增量更新"：

```python
# 传统 softmax（两遍）
m = max(x)             # 遍历 1
p = exp(x - m).sum()   # 遍历 2
softmax = exp(x - m) / p

# Online softmax（一遍）
m = -inf; p = 0; o = 0
for x_i in x:
    m_new = max(m, x_i)
    p = p * exp(m - m_new) + exp(x_i - m_new)  # 用差值校正
    o = o * exp(m - m_new) + exp(x_i - m_new) * v_i
    m = m_new
```

**关键**：每来一个新块，用 `exp(m_old - m_new)` **校正之前的累加值**——保证数学等价。

### 2.3 v1 Forward 伪代码（论文原版）

```python
# 初始化
O = zeros(N, d)      # 输出
l = zeros(N)         # softmax 分母
m = fill(N, -inf)    # 每行最大值

# 外循环：K, V 的分块
for j in range(N / Bc):
    K_j = load K[j*Bc : (j+1)*Bc]
    V_j = load V[j*Bc : (j+1)*Bc]

    # 内循环：Q 的分块
    for i in range(N / Br):
        Q_i = load Q[i*Br : (i+1)*Br]
        O_i, l_i, m_i = load O, l, m 的对应块

        # 计算这一块的 attention
        S_ij = Q_i @ K_j.T                    # [Br, Bc]
        m_ij = max(S_ij, axis=-1)             # 局部 max
        P_ij = exp(S_ij - m_ij)               # 局部 softmax
        l_ij = sum(P_ij, axis=-1)             # 局部分母

        # 关键：合并新旧
        m_new = max(m_i, m_ij)
        l_new = exp(m_i - m_new) * l_i + exp(m_ij - m_new) * l_ij
        O_new = (l_i * exp(m_i - m_new) * O_i +
                 exp(m_ij - m_new) * P_ij @ V_j) / l_new

        store O_new, l_new, m_new
```

**性能收益**（N=8K, d=64, A100）：
- 显存：128 MB → 0.1 MB（**降 1000×**）；
- 速度：**2.4× 更快**（论文数据）；
- HBM IO：4N²d → 4N²d/M×d（M 是 SRAM 容量，**降 M/d 倍**）。

---

## 3. FlashAttention v2：调整并行 + 重排循环

### 3.1 v1 的两大遗憾

1. **外循环是 K/V，内循环是 Q** —— 意味着**每个 Q 块要重复加载**，串行度不高；
2. **每次迭代都要重算 O_new** —— 涉及除法，浮点开销大。

### 3.2 v2 的三大优化

| 优化 | 做法 | 收益 |
|:--|:--|:--|
| **循环顺序反转** | 外循环 Q，内循环 K/V | Q 块只加载一次；**每个 Q 块可并行** |
| **延迟归一** | 循环里只累加，**最后除一次** l | 减少除法 |
| **序列维度并行** | 除了 batch/head，**seq_len 也并行** | 长序列 SM 利用率翻倍 |

### 3.3 v2 Forward 伪代码

```python
# 每个 CUDA block 处理一个 Q 块（Br 行）
for i in range(N / Br):  # ← 并行（每个 block）
    Q_i = load Q[i*Br : (i+1)*Br]
    O_i = zeros(Br, d)
    l_i = zeros(Br)
    m_i = fill(Br, -inf)

    for j in range(N / Bc):  # ← 串行
        K_j = load K[j*Bc : (j+1)*Bc]
        V_j = load V[j*Bc : (j+1)*Bc]

        S_ij = Q_i @ K_j.T
        m_new = max(m_i, max(S_ij, axis=-1))
        P_ij = exp(S_ij - m_new)
        l_i = exp(m_i - m_new) * l_i + sum(P_ij, axis=-1)
        O_i = exp(m_i - m_new) * O_i + P_ij @ V_j   # ← 不再除 l
        m_i = m_new

    O_i = O_i / l_i  # ← 最后一次除
    store O_i
```

**v2 vs v1**：吞吐提升 **~2×**（A100 上从 25% 上升到 50%+ 硬件峰值利用率）。

---

## 4. FlashAttention v3：Hopper 专属（TMA + WGMMA + Warp Specialization）

### 4.1 v3 为什么必须专门写

Hopper (H100/H200) 有三大新硬件：

| 特性 | 干啥用 |
|:--|:--|
| **TMA (Tensor Memory Accelerator)** | 异步 tile 拷贝，DMA 引擎，不占计算 warp |
| **WGMMA** | Warp-group MMA，一次 128×256×16 矩阵乘 |
| **Async Barrier + Cluster** | 支持 SM 间同步 |

**FA v2 用不上这些新特性**——所以 v3 是**为 Hopper 重写**。

### 4.2 核心技术：Warp Specialization

**传统 v2**：所有 warp 干同样的活（load + compute + store）。

**v3**：把 warp 分工：

```
一个 CTA（thread block）里的 warp 分两组：
├─ Producer warps：只负责 TMA 异步加载（1~2 个 warp）
└─ Consumer warps：只负责 WGMMA 计算（4~8 个 warp）

两组通过 async barrier 同步，形成"生产-消费"流水线：
    Load block 0  →  Load block 1  →  Load block 2 ...
                     Compute  0    →  Compute 1  ...
```

**收益**：H100 上从 v2 的 35% 峰值 → v3 的 **75% 峰值利用率**（FP16）。

### 4.3 v3 关键优化清单

| 优化 | 描述 |
|:--|:--|
| **TMA 异步加载** | Producer warp 用 TMA 加载 Q/K/V tile，不占算力 |
| **WGMMA** | 128×256×16 tile 一次 MMA |
| **FP8 支持** | 精度可切 FP8，H100 上算力翻倍 |
| **Ping-pong 调度** | 两组 consumer warp 交替计算，隐藏 softmax 延迟 |
| **Overlap softmax & GEMM** | softmax 和下一轮 QK^T 计算重叠 |

---

## 5. Triton 版最小实现（80 行）

**下面是简化版 forward，方便理解**（真实版还要 mask、backward）：

```python
import triton
import triton.language as tl

@triton.jit
def flash_attn_fwd(
    Q, K, V, O,
    stride_qb, stride_qh, stride_qm, stride_qk,
    stride_kb, stride_kh, stride_kn, stride_kk,
    stride_vb, stride_vh, stride_vn, stride_vk,
    stride_ob, stride_oh, stride_om, stride_ok,
    N_CTX: tl.constexpr,
    HEAD_DIM: tl.constexpr,
    BLOCK_M: tl.constexpr,   # Br，Q 分块大小
    BLOCK_N: tl.constexpr,   # Bc，K/V 分块大小
):
    # 每个 program 处理 (batch, head, Q_block) 三元组
    start_m = tl.program_id(0)
    off_bh = tl.program_id(1)
    off_b = off_bh // NUM_HEADS
    off_h = off_bh % NUM_HEADS

    # Q 分块指针
    Q_block_ptr = tl.make_block_ptr(
        base=Q + off_b*stride_qb + off_h*stride_qh,
        shape=(N_CTX, HEAD_DIM),
        strides=(stride_qm, stride_qk),
        offsets=(start_m*BLOCK_M, 0),
        block_shape=(BLOCK_M, HEAD_DIM),
        order=(1, 0),
    )
    # K, V 分块指针（略）...

    # 载入 Q_i（一次，一直放 SRAM）
    q = tl.load(Q_block_ptr)

    # 初始化累加器
    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    o = tl.zeros([BLOCK_M, HEAD_DIM], dtype=tl.float32)

    # 内循环：遍历 K, V 的分块
    for start_n in range(0, N_CTX, BLOCK_N):
        k = tl.load(K_block_ptr)
        v = tl.load(V_block_ptr)

        # 1. S_ij = Q_i @ K_j^T
        s = tl.dot(q, tl.trans(k))
        s = s * (1.0 / tl.sqrt(HEAD_DIM))

        # 2. Online softmax
        m_ij = tl.max(s, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)      # 旧值校正因子
        p = tl.exp(s - m_new[:, None])

        # 3. 累加
        l_i = l_i * alpha + tl.sum(p, axis=1)
        o = o * alpha[:, None] + tl.dot(p.to(v.dtype), v)
        m_i = m_new

        # 前进 K, V 指针
        K_block_ptr = tl.advance(K_block_ptr, (BLOCK_N, 0))
        V_block_ptr = tl.advance(V_block_ptr, (BLOCK_N, 0))

    # 最后一次归一
    o = o / l_i[:, None]

    # 写回
    tl.store(O_block_ptr, o.to(O.dtype.element_ty))
```

**上手建议**：拿 Triton 官方 `06-fused-attention.py` 直接跑，对比上面的伪代码，一行一行看。

---

## 6. 变体家族：Paged / MQA / GQA / Sliding Window

FlashAttention 火了以后衍生出无数变体，都是**基础算法 + 特殊场景**：

| 变体 | 场景 | 核心改动 |
|:--|:--|:--|
| **FlashAttention-2** | 常规训练/推理 | 循环反转 + 序列并行 |
| **FlashAttention-3** | H100 训练/推理 | TMA + WGMMA + Warp Specialization |
| **FlashDecoding** | 长序列推理（batch=1）| 沿 seqlen 切分并行 |
| **FlashDecoding++** | 极长序列（>32K）| 异步 softmax rescaling |
| **PagedAttention** | vLLM 引擎 | KV Cache 分页管理，非连续访问 |
| **MQA / GQA** | Llama 2/3 | Multi/Grouped Query，KV head 更少 |
| **Sliding Window** | Mistral | 只算最近 W 个 token |
| **Sparse Attention** | 超长上下文 | 稀疏 mask（如 Longformer, BigBird）|

---

## 7. 工程实践：什么时候该自己写、什么时候调库

### 7.1 决策树

```
你要用 Attention？
    │
    ├─ 常规 GPT/BERT 场景
    │     └─ 直接调 F.scaled_dot_product_attention (SDPA)
    │             ↑ PyTorch 内部自动选 FA/mem-efficient
    │
    ├─ LLM 推理
    │     ├─ vLLM 部署 → 已内置 FlashAttention + PagedAttention
    │     ├─ TensorRT-LLM → 也已内置
    │     └─ 自己搭 → 调 flash-attn 库
    │
    ├─ 新颖的 attention 变体（自研）
    │     ├─ 只想快点跑 → 用 Triton 版改
    │     └─ 极致性能 → 用 CUTLASS 3.x + Hopper 特性
    │
    └─ 研究/教学
          └─ 用 Triton 版从头实现，最快理解原理
```

### 7.2 三个"反直觉"忠告

1. **99% 场景直接用 SDPA** —— PyTorch 会自动选最快的实现，别自己造轮子；
2. **自己写 CUDA 版几乎不可能超越 flash-attn 官方** —— 除非你是 Tri Dao 的水平；
3. **优先尝试 Triton 版** —— 改起来是 CUDA 版的 1/10 工作量，性能只差 5~10%。

---

## 8. 学习路线图（4~6 周）

### Week 1：理解算法
- 读论文：FlashAttention v1（NeurIPS 2022）；
- 手推 online softmax 公式，理解 3 个校正因子；
- 读 v2 论文的循环调整部分。

### Week 2~3：Triton 实现
- 跑通 Triton 官方 `06-fused-attention.py`；
- 逐行注释，画出 SRAM 里的数据流；
- 修改：加 causal mask、支持不同 head_dim。

### Week 4：性能剖析
- 用 Nsight Compute 看你的 Triton 版和官方 `flash-attn` 差距；
- 关注 SM active、DRAM throughput、Tensor Core 使用率。

### Week 5~6：CUTLASS / v3 深入（可选）
- 读 CUTLASS `examples/49_hopper_fmha`；
- 理解 warp specialization、TMA、WGMMA；
- 尝试改造：新 mask、位置编码、稀疏模式。

---

## 9. 精选资源与官方链接

### 9.1 论文
- **FlashAttention v1**：<https://arxiv.org/abs/2205.14135>
- **FlashAttention v2**：<https://arxiv.org/abs/2307.08691>
- **FlashAttention v3**：<https://arxiv.org/abs/2407.08608>
- **Online Softmax**：<https://arxiv.org/abs/1805.02867>

### 9.2 代码
- **官方仓库**（Tri Dao）：<https://github.com/Dao-AILab/flash-attention>
- **Triton 官方 tutorial**：<https://triton-lang.org/main/getting-started/tutorials/06-fused-attention.html>
- **CUTLASS Hopper FMHA**：<https://github.com/NVIDIA/cutlass/tree/main/examples/48_hopper_warp_specialized_gemm>
- **vLLM PagedAttention**：<https://github.com/vllm-project/vllm/tree/main/vllm/attention>

### 9.3 姊妹篇
- [Triton 编程学习指南](./Triton编程学习指南.md)（Triton 是 FA 的推荐学习入口）
- [CUTLASS 编程学习指南](./CUTLASS编程学习指南.md)（v3 的底层）
- [Nsight 性能分析学习指南](./Nsight性能分析学习指南.md)（怎么剖析 FA kernel）
- [vLLM 编程学习指南](./vLLM编程学习指南.md)（PagedAttention 变体）

---

**版权声明**：本文由汪亮（bertonwang）撰写，转载请注明出处。欢迎邮件（<47608843@qq.com>）交流勘误。

**一句话总结全文**：**FlashAttention = tiling + online softmax + 硬件极致利用**——v1 让长序列训练成为可能、v2 让 GPU 跑满、v3 让 H100 起飞。**懂了它，你就懂了当代 GPU 性能优化的所有精髓**。
