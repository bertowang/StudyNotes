# Transformer 深度笔记：从零件到整机

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-22

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> 本文与《Attention 机制深度笔记》互为**姊妹篇**：姊妹篇讲"零件"（Attention / Multi-Head / Self-Cross / 位置编码 / KV Cache），本文讲"整机"（Encoder / Decoder / 残差 / LayerNorm / FFN / 训练与推理管线）。凡是零件级细节，本文一律**引用不复述**，保持薄而不重复。

---

## 目录

1. [为什么需要 Transformer？](#1-为什么需要-transformer)
2. [输入表示：从文本到向量](#2-输入表示从文本到向量)
3. [零件回顾：引用姊妹篇的对照表](#3-零件回顾引用姊妹篇的对照表)
4. [残差连接与 LayerNorm](#4-残差连接与-layernorm)
5. [Feed-Forward Network（FFN）](#5-feed-forward-networkffn)
6. [Encoder Layer：一层的完整装配](#6-encoder-layer一层的完整装配)
7. [Decoder Layer：多了什么？](#7-decoder-layer多了什么)
8. [整机装配：Encoder-Decoder Transformer](#8-整机装配encoder-decoder-transformer)
9. [完整实例：mini 英→中翻译 Transformer](#9-完整实例mini-英中翻译-transformer)
10. [推理：如何用训练好的 Transformer 生成](#10-推理如何用训练好的-transformer-生成)
11. [Transformer 家族图谱](#11-transformer-家族图谱)
12. [常见误区与 FAQ](#12-常见误区与-faq)
13. [参数量与形状速查表](#13-参数量与形状速查表)
14. [总结](#14-总结)

---

## 1. 为什么需要 Transformer？

> 📎 **阅读路线：** 1.1（RNN 的三个痛点）→ 1.2（Transformer 用什么替代）→ 1.3（一图看懂全景）。

### 1.1 RNN / LSTM 的三个致命弱点

| 痛点 | 说明 | 后果 |
|---|---|---|
| **顺序计算** | `h_t` 依赖 `h_{t-1}`，只能一步步算 | 无法并行，GPU 用不满 |
| **长程依赖衰减** | 信息沿时间步反复相乘，梯度消失 | 学不到远距离依赖 |
| **信息瓶颈** | 整个句子压进一个隐向量 | 长句翻译越译越糊 |

### 1.2 Transformer 用什么替代

| 原来 | 现在 | 好处 |
|---|---|---|
| RNN 时间递推 | **Self-Attention**（任意两 token 直接算相关性） | 一步到位、可并行、无衰减 |
| 位置由顺序天然编码 | **显式位置编码** | 结构化输入，不再依赖顺序 |
| 单一隐状态传递 | **多头 + 多层堆叠** | 一层一层精炼特征 |

> 🎯 **一句话：** Transformer 把"沿时间步递推"改成了"整段一次性看完 + 靠 attention 建立联系"。

### 1.3 一图看懂 Transformer 全景

```
                    ┌───────────────────────────────────────────┐
   源语言 tokens ──▶│           Encoder × N                     │──▶ 编码后的记忆
   （如英文）       │  ┌─────────────────────────────────┐       │      memory
                    │  │ Self-Attn → Add&Norm            │      │   [B, L_src, d_model]
                    │  │ FFN       → Add&Norm            │      │
                    │  └─────────────────────────────────┘ × N  │
                    └───────────────────────────────────────────┘
                                                                     │
                                                                     ▼
   目标 tokens ────▶┌───────────────────────────────────────────┐
   （如中文，右移） │           Decoder × N                       │
                    │  ┌─────────────────────────────────┐      │
                    │  │ Masked Self-Attn  → Add&Norm    │      │
                    │  │ Cross-Attn(→ memory) → Add&Norm │      │───▶ Linear + Softmax
                    │  │ FFN               → Add&Norm    │      │       ↓
                    │  └─────────────────────────────────┘ × N  │   下一个 token 概率
                    └───────────────────────────────────────────┘
```

**记住这一张图**，剩下所有章节都是在填这张图的细节。

---

## 2. 输入表示：从文本到向量

> 📎 **阅读路线：** 2.1（Tokenizer）→ 2.2（Token Embedding）→ 2.3（叠加位置编码）→ 2.4（形状速查）。

### 2.1 Tokenizer：文本 → 整数 ID

| 方案 | 一句话说清 | 代表模型 |
|---|---|---|
| Word-level | 按空格切词 | 早期 NMT |
| Char-level | 按字符切 | 早期字符模型 |
| **BPE**（Byte-Pair Encoding） | 高频字节对反复合并 | GPT-2/3、LLaMA |
| **WordPiece** | 类似 BPE，用似然合并 | BERT |
| **SentencePiece** | 直接在原始字节流上跑 BPE/Unigram | T5、mBART、多语言模型 |

> 🔑 **要点：** Tokenizer 的产物是一串**整数 ID**（`[42, 1015, 7, ...]`），Transformer 从这里开始工作。

### 2.2 Token Embedding：整数 ID → 向量

```python
embedding = nn.Embedding(vocab_size, d_model)   # 查表
x = embedding(token_ids)                        # [B, L] → [B, L, d_model]
```

- 本质是**一张可训练的查找表**：每个 token ID 对应一行 `d_model` 维的向量。
- `vocab_size × d_model` 是 Transformer 里最大的一块参数（LLM 里通常占 20%~30%）。

**关键变量含义：**

| 变量 | 含义 | 典型取值 | 说明 |
|---|---|---|---|
| `vocab_size` | 词表**总大小**，即查找表的**行数** | BERT: 30522；LLaMA: 32000 | Tokenizer 训练完固定，`token_ids` 里每个元素 ∈ `[0, vocab_size - 1]` |
| `d_model` | 每个 token 的**向量维度**，即查找表的**列数** | 512（原始 Transformer）/ 768（BERT-base）/ 4096（LLaMA-7B） | 从这里起，`x` 在整个 Transformer 内部都保持 `d_model` 维不变 |
| `token_ids` | Tokenizer 的**输出**，即 2.1 里的"整数 ID 串" | `[[42, 1015, 7]]` | 形状 `[B, L]` 的 `LongTensor`，作为 embedding 的**索引** |

> 🔑 **一句话：** `nn.Embedding(vocab_size, d_model)` = 一张 `vocab_size` 行、`d_model` 列的表；`token_ids` 里的每个整数就是"要查第几行"。

**一图看清 2.1 → 2.2 的完整数据流：**

```
文本 "I love cats"
    │
    │ Tokenizer.encode()                       ← Tokenizer 训练完成后 vocab_size 已固定
    ▼
token_ids = [[42, 1015, 7]]                     ← 2.1 的产物
形状 [B=1, L=3]，dtype=long
    │
    │ nn.Embedding(vocab_size, d_model)         ← 查找表定义：vocab_size 行 × d_model 列
    ▼   用 token_ids 做行索引
x = embedding(token_ids)
形状 [B=1, L=3, d_model=512]                    ← 2.2 的输出，之后一路保持 d_model 维
```

> 📌 **对号入座：** 2.1 里说的"整数 ID"= 代码里的 `token_ids`（形状 `[B, L]`）；后文所有 `x` 都是 embedding 之后的 `[B, L, d_model]` 张量。

### 2.3 叠加位置编码

Self-Attention 天然是**置换不变**的（打乱 token 顺序结果一样），所以必须把"位置"信息喂进去：

```python
x = token_embedding(ids) + positional_encoding(L)   # 两者形状都是 [B, L, d_model]
```

> 📎 **详见姊妹篇 8.1 ~ 8.6**：正弦编码 / 学习式编码 / RoPE 三种方案的公式、代码与选型建议。

### 2.4 形状变化速查（输入端）

| 阶段 | 张量 | 形状 |
|---|---|---|
| 原始文本 | `"I love cats"` | — |
| Tokenize | `token_ids` | `[B, L]` |
| Token Embedding | `x` | `[B, L, d_model]` |
| + Positional Encoding | `x` | `[B, L, d_model]`（形状不变） |

**从这里开始，整个 Transformer 里 `x` 的形状都是 `[B, L, d_model]`，直到最后一层 LM Head。**

---

## 3. 零件回顾：引用姊妹篇的对照表

> 🎯 **本节目的：** 把 Transformer 用到的所有 attention 类零件列成一张速查表，指向姊妹篇的对应小节。**本文不再重复讲这些零件**。

| 零件 | 一句话作用 | 姊妹篇位置 |
|---|---|---|
| Scaled Dot-Product Attention | Transformer 的最小单元，`softmax(QKᵀ/√d)·V` | 《Attention》6.1 ~ 6.4 |
| 单头 Self-Attention 实例 | 手推 3 token 数值 + 训练闭环 | 《Attention》6.5 ~ 6.6 |
| Multi-Head Attention | 拆头并行 + 拼回 + 输出投影 `W_O` | 《Attention》6.8 |
| Self-Attention vs Cross-Attention | Q/K/V 从哪来的区别 | 《Attention》7.1 ~ 7.5 |
| Masked Self-Attention | Decoder 训练时禁止看未来 | 《Attention》7.6 |
| 位置编码（3 种方案） | 正弦 / 学习式 / RoPE | 《Attention》8 |
| KV Cache | 推理加速的关键 | 《Attention》9 |

> 📌 **约定：** 后文出现"MHA"= Multi-Head Attention；"Self-Attn / Cross-Attn / Masked Self-Attn"含义与姊妹篇 7 章一致。

---

## 4. 残差连接与 LayerNorm

> 📎 **阅读路线：** 4.1（为什么必须有残差）→ 4.2（LayerNorm 公式与代码）→ 4.3（Post-LN vs Pre-LN）→ 4.4（sublayer 结构图）。

### 4.1 为什么必须有残差连接

Transformer 动辄 12 层、96 层，没有残差**根本训不动**。残差干的事只有一件：

```
y = x + Sublayer(x)          # 残差 = "至少不比原来差"
```

| 有残差 | 无残差 |
|---|---|
| 梯度能沿 `+x` 这条**恒等通路**直达浅层 | 梯度反传要穿过每一个 sublayer，逐层衰减 |
| 96 层依然能训 | 6 层就已经吃力 |
| Sublayer 只需学"**增量**"（残差） | Sublayer 要学"**完整变换**"（更难） |

> 🎯 **一句话：** 残差把网络从"逐层重构"变成了"逐层微调"，这是 Transformer 敢堆深的根本原因。

### 4.2 LayerNorm 的数学公式与代码

与《Attention 机制深度笔记》4.x 讲的 **BatchNorm 沿 Batch 维归一化**不同，LayerNorm **沿特征维**归一化：

$$
\text{LN}(x) = \gamma \cdot \frac{x - \mu}{\sqrt{\sigma^2 + \epsilon}} + \beta
$$

其中 `μ, σ²` 是**每个 token 自己**在 `d_model` 维上的均值 / 方差。

```python
ln = nn.LayerNorm(d_model)
y = ln(x)                    # x: [B, L, d_model] → y: [B, L, d_model]
```

| 维度 | BatchNorm | LayerNorm |
|---|---|---|
| 归一化沿哪个维度 | Batch 维（跨样本） | 特征维（同一 token 内） |
| 依赖 batch size | ✅ 依赖 | ❌ 不依赖 |
| 训练 vs 推理是否一致 | ❌ 不一致（要滑动均值） | ✅ 完全一致 |
| 适合 NLP？ | ❌ 变长序列难用 | ✅ 天生适合 |

> 🔑 **要点：** NLP 里几乎所有 Transformer 都用 LayerNorm，不用 BatchNorm，就是因为最后两行。

### 4.3 Post-LN vs Pre-LN

同一个 sublayer，LN 放在残差**之后**还是**之前**，训练稳定性天差地别：

```
Post-LN（原始论文 2017）      Pre-LN（GPT-2 起，现代 LLM 全部采用）
─────────────────────         ──────────────────────
y = LN(x + Sublayer(x))       y = x + Sublayer(LN(x))
```

| 对比项 | Post-LN | Pre-LN |
|---|---|---|
| 训练稳定性 | 差，需要 warmup + 谨慎学习率 | 好，深层也稳 |
| 收敛速度 | 慢 | 快 |
| 最终表现 | 略好（若能训稳） | 稍逊但差距很小 |
| 现代 LLM 选谁 | ❌ | ✅ **全部** |

> 🎯 **本文实现选 Pre-LN**，与 GPT / LLaMA / Qwen 主流保持一致。

### 4.4 一图看清 sublayer 结构

```
Pre-LN 版本（本文采用）:

  x ────────────────────────────┐
  │                             │
  ▼                             │
 LN                             │  (残差恒等通路)
  │                             │
  ▼                             │
 Sublayer  (Attn 或 FFN)        │
  │                             │
  ▼                             ▼
  └───────────►  (＋)  ◄────────┘
                 │
                 ▼
                 y
```

**一个 Encoder Layer = 2 个这样的 sublayer 串起来（Self-Attn + FFN）**  
**一个 Decoder Layer = 3 个（Masked Self-Attn + Cross-Attn + FFN）**

---

## 5. Feed-Forward Network（FFN）

> 📎 **阅读路线：** 5.1（结构）→ 5.2（中间维度 4×d_model 的由来）→ 5.3（激活函数进化）→ 5.4（参数量占比）。

### 5.1 结构：两层 Linear 夹一个激活

```python
class FFN(nn.Module):
    def __init__(self, d_model, d_ff):
        super().__init__()
        self.linear1 = nn.Linear(d_model, d_ff)
        self.linear2 = nn.Linear(d_ff, d_model)
        self.act     = nn.GELU()

    def forward(self, x):                       # x: [B, L, d_model]
        return self.linear2(self.act(self.linear1(x)))   # → [B, L, d_model]
```

**形状流水线：** `[B, L, d_model] → [B, L, d_ff] → [B, L, d_model]`

### 5.2 为什么 d_ff 通常是 4 × d_model？

- **经验值**：原始论文取 `d_model=512, d_ff=2048`，此后各家沿用。
- **直觉**：FFN 是"**逐位置**"运行的（每个 token 独立过，位置间不交互），需要一个够宽的隐层来做非线性特征提取。
- **对比**：Attention 负责"**跨位置**"混合信息，FFN 负责"**逐位置**"精炼信息。**二者分工明确，缺一不可**。

> 💡 **记忆窍门：** Attention 是"横向"（跨 token），FFN 是"纵向"（每个 token 自己变换），一横一纵才够表达能力。

### 5.3 激活函数进化史

| 时代 | 激活 | 代表模型 |
|---|---|---|
| 2017 | **ReLU** | 原始 Transformer |
| 2019~ | **GELU** | BERT、GPT-2/3 |
| 2022~ | **SwiGLU**（门控） | LLaMA、Qwen、PaLM |

**SwiGLU 结构（选读）：**

```python
# 门控版：多一个 gate 分支
gate = self.linear_gate(x)                      # [B, L, d_ff]
up   = self.linear_up(x)                        # [B, L, d_ff]
h    = F.silu(gate) * up                        # 门控相乘
y    = self.linear_down(h)                      # [B, L, d_model]
```

**代价：** 参数量比普通 FFN 多 50%（多了一个投影）。**收益：** 表现更好，现代 LLM 几乎清一色 SwiGLU。

### 5.4 FFN 在参数量里占多少？

一层 Transformer 里，**FFN 占 ~66% 的参数**（`2 × d_model × d_ff = 2 × d_model × 4d_model = 8 d_model²`），而 MHA 只占 ~33%（`4 × d_model²`，即 Q/K/V/O 四个投影）。

> 🎯 **反直觉但重要：** 大家总觉得 Attention 是 Transformer 的灵魂，但**参数量的大头其实在 FFN**。压缩 Transformer 时优先动 FFN 效果最明显。

---

## 6. Encoder Layer：一层的完整装配

> 📎 **阅读路线：** 6.1（结构总览）→ 6.2（数据流）→ 6.3（PyTorch 代码）→ 6.4（形状速查）。

### 6.1 结构总览

**一个 Encoder Layer = Self-Attn sublayer + FFN sublayer**，两个 sublayer 都用 Pre-LN + 残差。

```
输入 x  [B, L_src, d_model]
   │
   ├──────► LN → MHA(Self-Attn) → Dropout ─┐
   │                                        │
   └────────────► (＋) ◄───────────────────┘
                   │
                   ├──────► LN → FFN → Dropout ─┐
                   │                             │
                   └────────► (＋) ◄────────────┘
                              │
                              ▼
                       输出 [B, L_src, d_model]
```

### 6.2 数据流（口语版）

1. **Self-Attn**：让 `L_src` 个 token **互相观察一遍**，每个 token 更新为"全句相关信息的加权聚合"。
2. **FFN**：每个 token **独立地**过一次非线性变换，精炼自己的表示。
3. 两个 sublayer 各自套残差 + LayerNorm，梯度和信息都能安全穿过。

### 6.3 完整 PyTorch 代码

```python
class EncoderLayer(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout=0.1):
        super().__init__()
        self.self_attn = nn.MultiheadAttention(d_model, n_heads,
                                               dropout=dropout, batch_first=True)
        self.ffn       = FFN(d_model, d_ff)
        self.ln1       = nn.LayerNorm(d_model)
        self.ln2       = nn.LayerNorm(d_model)
        self.drop      = nn.Dropout(dropout)

    def forward(self, x, src_key_padding_mask=None):
        # sublayer 1: Self-Attention
        h = self.ln1(x)
        h, _ = self.self_attn(h, h, h, key_padding_mask=src_key_padding_mask)
        x = x + self.drop(h)

        # sublayer 2: FFN
        h = self.ln2(x)
        h = self.ffn(h)
        x = x + self.drop(h)
        return x                                    # [B, L_src, d_model]
```

> 📎 `nn.MultiheadAttention` 的 Q=K=V=`h`，即姊妹篇 7.3 讲的 Self-Attention；`key_padding_mask` 用来屏蔽 `<pad>` 位置。

### 6.4 形状速查

| 位置 | 张量 | 形状 |
|---|---|---|
| 输入 | `x` | `[B, L_src, d_model]` |
| Self-Attn 内部（每头） | `q, k, v` | `[B, n_heads, L_src, d_k]` |
| Self-Attn 输出 | `h` | `[B, L_src, d_model]` |
| FFN 中间 | `h` | `[B, L_src, d_ff]` |
| FFN 输出 = 层输出 | `x` | `[B, L_src, d_model]` |

**核心结论：一层 Encoder 输入输出形状完全一致**，所以可以直接堆 N 层。

---

## 7. Decoder Layer：多了什么？

> 📎 **阅读路线：** 7.0（三种 attention 定位速查）→ 7.1（三个 sublayer 结构）→ 7.2（Masked Self-Attn 作用）→ 7.3（Cross-Attn 的 Q/K/V 来源）→ 7.4（完整代码）→ 7.5（Encoder-Decoder 数据接头）。

### 7.0 三种 attention 定位速查

进入 Decoder 之前，先把整机里**一共出现的 3 种 attention** 列清楚——它们只是"出现位置不同 + Q/K/V 来源不同"，底层都是同一个 `softmax(QKᵀ/√d)·V`：

| 出现位置 | 类型 | Q 来自 | K/V 来自 | 特殊 mask |
|---|---|---|---|---|
| Encoder Layer 唯一 sublayer | **Self-Attn** | 自己 | 自己 | 无（可看整句） |
| Decoder Layer 第 1 个 sublayer | **Masked Self-Attn** | 自己 | 自己 | ✅ 因果 mask（禁看未来） |
| Decoder Layer 第 2 个 sublayer | **Cross-Attn** | 自己（Decoder） | `memory`（Encoder 顶层输出） | 无 |

> 🎯 **一句话记忆：** **K/V 来自哪里，就决定了 attention 的类型**——来自自己 = Self，来自 memory = Cross；再看要不要挡未来，加 causal mask 就是 Masked Self。

> 📎 三者的完整数学形式、PyTorch 代码对照见姊妹篇 7.1 ~ 7.6，本文不再展开。

### 7.1 三个 sublayer 结构

**Encoder Layer 有 2 个 sublayer，Decoder Layer 有 3 个**——多出来的就是 **Cross-Attention**：

```
目标端输入 y  [B, L_tgt, d_model]
                              memory  [B, L_src, d_model]  ← 来自 Encoder
   │
   ├──► LN → Masked Self-Attn(y,y,y) → Dropout ─┐
   │                                             │
   └───────────────► (＋) ◄─────────────────────┘
                      │
                      ├──► LN → Cross-Attn(Q=y,  K=V=memory) → Dropout ─┐
                      │                                                  │
                      └────────► (＋) ◄────────────────────────────────┘
                                 │
                                 ├──► LN → FFN → Dropout ─┐
                                 │                         │
                                 └────► (＋) ◄────────────┘
                                        │
                                        ▼
                                  [B, L_tgt, d_model]
```

### 7.2 Masked Self-Attention：不许看未来

训练时，Decoder 一次性拿到**整句**目标序列（比如整句中文），但预测第 `t` 个 token 时**只允许看前 `t-1` 个**——否则就是"看着答案抄"。

> 📎 **详见姊妹篇 7.6**：因果 mask 矩阵的构造、`float('-inf')` 填充、softmax 后变 0 的推导。

### 7.3 Cross-Attention：Q / K / V 分别从哪来？

这是 Encoder-Decoder 沟通的**唯一通道**，请务必记牢：

| 张量 | 来源 | 形状 |
|---|---|---|
| **Q（Query）** | Decoder 自己（本层上一步的输出） | `[B, L_tgt, d_model]` |
| **K（Key）** | Encoder 顶层输出 `memory` | `[B, L_src, d_model]` |
| **V（Value）** | Encoder 顶层输出 `memory` | `[B, L_src, d_model]` |

> 🎯 **直觉：** Decoder 拿着"我现在想生成什么"（Q）去 Encoder 的记忆里（K/V）查找"哪些源语言 token 最相关"，然后把这些 token 的信息加权拿回来。**这就是翻译的核心机制**。

> 📎 姊妹篇 7.3 / 7.5 用 PyTorch 代码写过完整对照，本文不再展开。

### 7.4 完整 PyTorch 代码

```python
class DecoderLayer(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout=0.1):
        super().__init__()
        self.self_attn  = nn.MultiheadAttention(d_model, n_heads,
                                                dropout=dropout, batch_first=True)
        self.cross_attn = nn.MultiheadAttention(d_model, n_heads,
                                                dropout=dropout, batch_first=True)
        self.ffn        = FFN(d_model, d_ff)
        self.ln1        = nn.LayerNorm(d_model)
        self.ln2        = nn.LayerNorm(d_model)
        self.ln3        = nn.LayerNorm(d_model)
        self.drop       = nn.Dropout(dropout)

    def forward(self, y, memory,
                tgt_mask=None, tgt_key_padding_mask=None,
                memory_key_padding_mask=None):
        # sublayer 1: Masked Self-Attention（Q=K=V=y，加因果 mask）
        h = self.ln1(y)
        h, _ = self.self_attn(h, h, h,
                              attn_mask=tgt_mask,
                              key_padding_mask=tgt_key_padding_mask)
        y = y + self.drop(h)

        # sublayer 2: Cross-Attention（Q=y_norm, K=V=memory）
        h = self.ln2(y)
        h, _ = self.cross_attn(h, memory, memory,
                               key_padding_mask=memory_key_padding_mask)
        y = y + self.drop(h)

        # sublayer 3: FFN
        h = self.ln3(y)
        h = self.ffn(h)
        y = y + self.drop(h)
        return y                                    # [B, L_tgt, d_model]
```

### 7.5 Encoder-Decoder 数据是怎么"接头"的？

```
   源句 x_src [B, L_src]
        │
        ▼
   Embedding + PosEnc
        │
        ▼  [B, L_src, d_model]
   ┌──────────┐
   │Encoder×N │
   └────┬─────┘
        │ memory [B, L_src, d_model]
        │
        │      目标句 x_tgt [B, L_tgt]（训练时 = 右移一位的 ground truth）
        │           │
        │           ▼
        │      Embedding + PosEnc
        │           │
        │           ▼  [B, L_tgt, d_model]
        │      ┌──────────┐
        └─────▶│Decoder×N │  ← 每层的 Cross-Attn 都会用到 memory
               └────┬─────┘
                    ▼  [B, L_tgt, d_model]
                Linear (→ vocab_tgt) + Softmax
                    │
                    ▼  [B, L_tgt, vocab_tgt]
                预测下一个 token 的概率分布
```

> 🔑 **关键点：** `memory` 只算**一次**（Encoder 只跑一次），却被 Decoder 的**每一层**、**每一个目标位置** Cross-Attn 反复消费。这也是 Encoder-Decoder 模型推理效率的天然优势。

---

## 8. 整机装配：Encoder-Decoder Transformer

> 📎 **阅读路线：** 8.1（Layer → Stack）→ 8.2（输入端）→ 8.3（输出端 LM Head）→ 8.4（端到端形状）→ 8.5（参数量估算）。

### 8.1 从 Layer 到 Stack

```python
class Encoder(nn.Module):
    def __init__(self, N, d_model, n_heads, d_ff, dropout):
        super().__init__()
        self.layers = nn.ModuleList([
            EncoderLayer(d_model, n_heads, d_ff, dropout) for _ in range(N)
        ])
        self.norm = nn.LayerNorm(d_model)          # Pre-LN 架构惯例：最后再做一次 LN

    def forward(self, x, src_key_padding_mask=None):
        for layer in self.layers:
            x = layer(x, src_key_padding_mask)
        return self.norm(x)

class Decoder(nn.Module):
    def __init__(self, N, d_model, n_heads, d_ff, dropout):
        super().__init__()
        self.layers = nn.ModuleList([
            DecoderLayer(d_model, n_heads, d_ff, dropout) for _ in range(N)
        ])
        self.norm = nn.LayerNorm(d_model)

    def forward(self, y, memory,
                tgt_mask=None, tgt_key_padding_mask=None,
                memory_key_padding_mask=None):
        for layer in self.layers:
            y = layer(y, memory, tgt_mask,
                      tgt_key_padding_mask, memory_key_padding_mask)
        return self.norm(y)
```

### 8.2 输入端：Embedding + PosEnc 打包

```python
class TokenPosEmbedding(nn.Module):
    def __init__(self, vocab_size, d_model, max_len=512):
        super().__init__()
        self.tok = nn.Embedding(vocab_size, d_model)
        self.pos = nn.Embedding(max_len, d_model)   # 学习式位置编码（详见姊妹篇 8.4）
        self.d_model = d_model

    def forward(self, ids):                         # ids: [B, L]
        L = ids.size(1)
        pos_ids = torch.arange(L, device=ids.device).unsqueeze(0)   # [1, L]
        return self.tok(ids) * math.sqrt(self.d_model) + self.pos(pos_ids)
```

> 💡 `× √d_model` 是原论文的做法：让 token embedding 与位置编码在数量级上相当。

### 8.3 输出端：LM Head

```python
# 把 d_model 维投影到目标词表大小，得到每个位置的下一个 token 概率分布
self.lm_head = nn.Linear(d_model, vocab_tgt)

logits = self.lm_head(decoder_out)              # [B, L_tgt, vocab_tgt]
```

> 🔑 **权重共享（可选优化）：** 让 `lm_head.weight = tgt_embedding.tok.weight`，参数量少一大块，且经验上表现更好。GPT / T5 都这么干。

### 8.4 端到端形状流水线

```
输入:
  src_ids  [B, L_src]        tgt_ids  [B, L_tgt]

Embedding + PosEnc:
  src      [B, L_src, d_model]         tgt  [B, L_tgt, d_model]

Encoder × N:
  memory   [B, L_src, d_model]

Decoder × N (每层 Cross-Attn 消费 memory):
  dec_out  [B, L_tgt, d_model]

LM Head:
  logits   [B, L_tgt, vocab_tgt]

Loss (训练时):
  CrossEntropy(logits.view(-1, V), gold.view(-1))     # 详见姊妹篇 3.1~3.4
```

### 8.5 参数量估算

以每层为主：

| 部件 | 参数量 |
|---|---|
| MHA（Q/K/V/O 四个投影） | `4 × d_model²` |
| FFN（两个 Linear） | `2 × d_model × d_ff = 8 × d_model²`（`d_ff=4d_model`） |
| LayerNorm × 2 或 × 3 | `~4 × d_model`（可忽略） |
| **一层小计** | **`~12 × d_model²`** |

外加：

| 部件 | 参数量 |
|---|---|
| Token Embedding | `vocab × d_model` |
| Positional Embedding（学习式） | `max_len × d_model` |
| LM Head（若不共享权重） | `d_model × vocab` |

**估算公式：**

$$
\text{Params} \approx N_{\text{enc}} \cdot 12 d^2 + N_{\text{dec}} \cdot 18 d^2 + 2 V d
$$

（Decoder 每层多一个 Cross-Attn，约多 6 d²）

---

## 9. 完整实例：mini 英→中翻译 Transformer

> 🎯 **本节目的：** 把第 1 ~ 8 节的知识**全部拼起来**，用一个 CPU 秒级可跑的 mini Transformer 完成"英→中"翻译任务。这一节和姊妹篇 6.6（单头 attention 的训练闭环）**互为呼应**——你会看到"整机 vs 零件"的差别到底在哪。
>
> 📎 **阅读路线：** 9.1（任务与数据）→ 9.2（超参与模型）→ 9.3（数据处理与 mask）→ 9.4（训练循环）→ 9.5（观察结果）→ 9.6（与姊妹篇 6.7 的差异）。

### 9.1 任务与数据

**任务：** 极简英→中翻译，只学 4 个句对，验证"结构能跑通、能过拟合、loss 能降"。

```
英文（源）              →   中文（目标）
"i love cats"           →   "我 爱 猫"
"i love dogs"           →   "我 爱 狗"
"you love cats"         →   "你 爱 猫"
"you love dogs"         →   "你 爱 狗"
```

> 📎 **为什么用过拟合来验证？** 与姊妹篇 6.7 讨论一致：**结构验证阶段先做到"能过拟合"，再谈泛化**。

### 9.2 超参与模型

| 超参 | 值 | 说明 |
|---|---|---|
| `d_model` | 32 | 主特征维度 |
| `n_heads` | 4 | 每头 `d_k=d_v=8` |
| `d_ff` | 64 | `2 × d_model`（迷你版，正式 Transformer 是 4×） |
| `N_enc / N_dec` | 2 / 2 | 各堆 2 层 |
| `max_len` | 8 | 句子够短 |

```python
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(42)

# ================= 通用零件 =================

class FFN(nn.Module):
    def __init__(self, d_model, d_ff):
        super().__init__()
        self.fc1 = nn.Linear(d_model, d_ff)
        self.fc2 = nn.Linear(d_ff, d_model)
        self.act = nn.GELU()
    def forward(self, x):
        return self.fc2(self.act(self.fc1(x)))

class TokenPosEmbedding(nn.Module):
    def __init__(self, vocab_size, d_model, max_len=32):
        super().__init__()
        self.tok = nn.Embedding(vocab_size, d_model)
        self.pos = nn.Embedding(max_len, d_model)
        self.d_model = d_model
    def forward(self, ids):
        L = ids.size(1)
        pos_ids = torch.arange(L, device=ids.device).unsqueeze(0)
        return self.tok(ids) * math.sqrt(self.d_model) + self.pos(pos_ids)

class EncoderLayer(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout=0.0):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, n_heads,
                                          dropout=dropout, batch_first=True)
        self.ffn  = FFN(d_model, d_ff)
        self.ln1  = nn.LayerNorm(d_model)
        self.ln2  = nn.LayerNorm(d_model)
    def forward(self, x, src_kpm=None):
        h = self.ln1(x)
        h, _ = self.attn(h, h, h, key_padding_mask=src_kpm)
        x = x + h
        h = self.ln2(x)
        x = x + self.ffn(h)
        return x

class DecoderLayer(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout=0.0):
        super().__init__()
        self.self_attn  = nn.MultiheadAttention(d_model, n_heads,
                                                dropout=dropout, batch_first=True)
        self.cross_attn = nn.MultiheadAttention(d_model, n_heads,
                                                dropout=dropout, batch_first=True)
        self.ffn = FFN(d_model, d_ff)
        self.ln1 = nn.LayerNorm(d_model)
        self.ln2 = nn.LayerNorm(d_model)
        self.ln3 = nn.LayerNorm(d_model)
    def forward(self, y, memory, tgt_mask=None,
                tgt_kpm=None, mem_kpm=None):
        h = self.ln1(y)
        h, _ = self.self_attn(h, h, h,
                              attn_mask=tgt_mask,
                              key_padding_mask=tgt_kpm)
        y = y + h
        h = self.ln2(y)
        h, _ = self.cross_attn(h, memory, memory,
                               key_padding_mask=mem_kpm)
        y = y + h
        h = self.ln3(y)
        y = y + self.ffn(h)
        return y

# ================= 整机 =================

class MiniTransformer(nn.Module):
    def __init__(self, vocab_src, vocab_tgt, d_model=32, n_heads=4,
                 d_ff=64, N_enc=2, N_dec=2, max_len=8):
        super().__init__()
        self.src_emb = TokenPosEmbedding(vocab_src, d_model, max_len)
        self.tgt_emb = TokenPosEmbedding(vocab_tgt, d_model, max_len)
        self.encoder = nn.ModuleList([EncoderLayer(d_model, n_heads, d_ff)
                                      for _ in range(N_enc)])
        self.decoder = nn.ModuleList([DecoderLayer(d_model, n_heads, d_ff)
                                      for _ in range(N_dec)])
        self.enc_norm = nn.LayerNorm(d_model)
        self.dec_norm = nn.LayerNorm(d_model)
        self.lm_head  = nn.Linear(d_model, vocab_tgt)

    def encode(self, src_ids, src_kpm=None):
        x = self.src_emb(src_ids)
        for layer in self.encoder:
            x = layer(x, src_kpm)
        return self.enc_norm(x)                    # memory

    def decode(self, tgt_ids, memory, tgt_mask=None,
               tgt_kpm=None, mem_kpm=None):
        y = self.tgt_emb(tgt_ids)
        for layer in self.decoder:
            y = layer(y, memory, tgt_mask, tgt_kpm, mem_kpm)
        return self.dec_norm(y)

    def forward(self, src_ids, tgt_ids,
                src_kpm=None, tgt_kpm=None, tgt_mask=None):
        memory = self.encode(src_ids, src_kpm)
        dec    = self.decode(tgt_ids, memory, tgt_mask,
                             tgt_kpm, mem_kpm=src_kpm)
        return self.lm_head(dec)                   # [B, L_tgt, vocab_tgt]
```

### 9.3 数据处理与 mask

**特殊 token：** `<pad>=0, <bos>=1, <eos>=2`。

```python
# 词表
src_vocab = {'<pad>':0, '<bos>':1, '<eos>':2,
             'i':3, 'you':4, 'love':5, 'cats':6, 'dogs':7}
tgt_vocab = {'<pad>':0, '<bos>':1, '<eos>':2,
             '我':3, '你':4, '爱':5, '猫':6, '狗':7}
inv_tgt   = {v:k for k,v in tgt_vocab.items()}

pairs = [
    ("i love cats",   "我 爱 猫"),
    ("i love dogs",   "我 爱 狗"),
    ("you love cats", "你 爱 猫"),
    ("you love dogs", "你 爱 狗"),
]

def encode(sent, vocab, add_bos=False, add_eos=False):
    ids = ([vocab['<bos>']] if add_bos else []) \
        + [vocab[w] for w in sent.split()] \
        + ([vocab['<eos>']] if add_eos else [])
    return ids

def pad(seqs, pad_id=0):
    L = max(len(s) for s in seqs)
    return torch.tensor([s + [pad_id]*(L-len(s)) for s in seqs])

# 源端：不加 bos/eos，直接编码 + padding
src_ids = pad([encode(en, src_vocab) for en, _ in pairs])
# 目标端：训练时用 "teacher forcing"，需要两个版本
#   tgt_in  = [<bos>, w1, w2, w3]        送进 Decoder
#   tgt_out = [w1,    w2, w3, <eos>]     用作 label（右移一位）
tgt_in  = pad([encode(zh, tgt_vocab, add_bos=True)  for _, zh in pairs])
tgt_out = pad([encode(zh, tgt_vocab, add_eos=True)  for _, zh in pairs])

# padding mask（True 表示要屏蔽的 padding 位置）
src_kpm = (src_ids == 0)
tgt_kpm = (tgt_in  == 0)

# 因果 mask（Decoder Masked Self-Attn 用；详见姊妹篇 7.6）
L_tgt = tgt_in.size(1)
causal_mask = torch.triu(torch.ones(L_tgt, L_tgt), diagonal=1).bool()   # 上三角为 True → 屏蔽未来
```

> 🔑 **teacher forcing 三件套：** `tgt_in`（右移一位、带 `<bos>`）+ `tgt_out`（原序列、带 `<eos>`）+ `causal_mask`（不让偷看未来）。这是整个训练管线的**核心机制**。

### 9.4 训练循环

沿用姊妹篇 2.2 / 6.6 讲过的通用五步，几乎无需改动：

```python
model     = MiniTransformer(vocab_src=len(src_vocab), vocab_tgt=len(tgt_vocab))
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
loss_fn   = nn.CrossEntropyLoss(ignore_index=0)     # ignore <pad>

for step in range(401):
    optimizer.zero_grad()                                # ① 清零
    logits = model(src_ids, tgt_in,                      # ② 前向
                   src_kpm=src_kpm,
                   tgt_kpm=tgt_kpm,
                   tgt_mask=causal_mask)
    # logits: [B, L_tgt, V] → 展平成 [B*L_tgt, V]；tgt_out: [B, L_tgt] → [B*L_tgt]
    loss = loss_fn(logits.reshape(-1, logits.size(-1)),  # ③ loss
                   tgt_out.reshape(-1))
    loss.backward()                                      # ④ 反传
    optimizer.step()                                     # ⑤ 更新

    if step % 50 == 0:
        print(f"step {step:3d} | loss = {loss.item():.4f}")
```

**典型运行输出：**

```
step   0 | loss = 2.14
step  50 | loss = 0.61
step 100 | loss = 0.09
step 200 | loss = 0.005
step 400 | loss = 0.0005
```

Loss 单调下降到接近 0，说明模型**结构正确、数据流通畅、梯度能流动**——这就是姊妹篇 6.6 里强调的"训练闭环打通"的整机版。

### 9.5 观察结果：贪心解码验证

训练完了得看看它翻得对不对。用最简单的 **greedy decoding**（每步选概率最高的 token）：

```python
@torch.no_grad()
def translate(model, en_sent, max_new=6):
    model.eval()
    src = pad([encode(en_sent, src_vocab)])
    memory = model.encode(src, src_kpm=(src==0))

    ids = [tgt_vocab['<bos>']]
    for _ in range(max_new):
        tgt_in = torch.tensor([ids])
        L = tgt_in.size(1)
        cmask = torch.triu(torch.ones(L, L), diagonal=1).bool()
        dec = model.decode(tgt_in, memory, tgt_mask=cmask)
        next_id = model.lm_head(dec[:, -1]).argmax(-1).item()
        if next_id == tgt_vocab['<eos>']: break
        ids.append(next_id)
    return ' '.join(inv_tgt[i] for i in ids[1:])         # 去掉 <bos>

for en, zh in pairs:
    print(f"{en:15s} → {translate(model, en)}   (期望: {zh})")
```

**输出：**

```
i love cats     → 我 爱 猫    (期望: 我 爱 猫)
i love dogs     → 我 爱 狗    (期望: 我 爱 狗)
you love cats   → 你 爱 猫    (期望: 你 爱 猫)
you love dogs   → 你 爱 狗    (期望: 你 爱 狗)
```

✅ **4 条全对**。整机 Transformer 训练管线**完整跑通**。

### 9.6 与姊妹篇 6.7 的差异一览

| 维度 | 姊妹篇 6.7（单头恒等复原） | 本节（mini 翻译整机） |
|---|---|---|
| 目的 | 让 attention 学会"关注自己" | 让 Transformer 学会"英→中映射" |
| 结构 | 单头 Self-Attn | Encoder×2 + Decoder×2 + MHA + FFN + LN |
| 输入输出 | 输入=输出（自监督） | 源=英文、标=中文（有监督） |
| 损失 | MSELoss（回归） | CrossEntropyLoss（分类，见姊妹篇 3.x） |
| Mask | 无 | padding mask + causal mask 都用了 |
| 训练技巧 | 无 | teacher forcing（`tgt_in` / `tgt_out` 右移） |
| 推理方式 | 一次前向 | 自回归 greedy decoding（下一节展开） |

> 🎯 **结论：** 姊妹篇 6.7 打通了"零件级"训练闭环；本节打通了"整机级"训练 + 推理闭环。**至此 Transformer 训练管线 100% 覆盖完毕**。

---

## 10. 推理：如何用训练好的 Transformer 生成

> 📎 **阅读路线：** 10.1（Greedy）→ 10.2（Beam Search）→ 10.3（Sampling）→ 10.4（结合 KV Cache）→ 10.5（训练 vs 推理形状对比）。

### 10.1 Greedy Decoding：每步选最大概率

```python
next_id = logits[:, -1].argmax(-1)          # 每次只看最后一步的输出
```

- **优点**：简单、确定性、快。
- **缺点**：只看当前一步最优，容易陷入局部最优；重复问题严重。

### 10.2 Beam Search：保留 top-k 候选路径

- 每步同时维护 `k` 条最可能的**部分序列**（beam width，通常 4~8）。
- 每步对每条 beam 扩展所有词表 token → 从 `k × V` 个中挑总分最高的 `k` 条。
- 终止：所有 beam 都遇到 `<eos>`，或达到 `max_len`。

**适用：** 翻译、摘要（需要"高置信度"输出）。

### 10.3 Sampling：Top-k / Top-p / Temperature

现代 LLM 生成的**默认方式**，追求多样性：

| 采样方式 | 一句话说清 |
|---|---|
| **Temperature T** | logits 除以 T：T<1 更尖锐（保守），T>1 更平滑（发散） |
| **Top-k** | 只从概率最高的 k 个 token 里采样 |
| **Top-p**（nucleus） | 只从累计概率 ≤ p 的最小 token 集合里采样（动态大小） |

```python
def sample(logits, temperature=1.0, top_k=0, top_p=1.0):
    logits = logits / temperature
    if top_k > 0:
        v, _ = torch.topk(logits, top_k)
        logits[logits < v[..., -1:]] = -float('inf')
    if top_p < 1.0:
        sorted_logits, idx = logits.sort(descending=True)
        cum = sorted_logits.softmax(-1).cumsum(-1)
        mask = cum > top_p
        mask[..., 1:] = mask[..., :-1].clone()
        mask[..., 0]  = False
        sorted_logits[mask] = -float('inf')
        logits = torch.zeros_like(logits).scatter(-1, idx, sorted_logits)
    probs = logits.softmax(-1)
    return torch.multinomial(probs, num_samples=1)
```

### 10.4 结合 KV Cache 的推理骨架

**未加 KV Cache（朴素版）：** 每生成一个 token，都要把已生成的**全部序列**重新过一遍 Decoder——重复计算严重。

**加了 KV Cache：** 每一步只把**新的这 1 个 token** 送进 Decoder，K/V 从 cache 里读、把新的 K/V 追加进 cache。

```python
# 伪代码（详细形状与推导见姊妹篇 9.2 ~ 9.5）
cache = init_empty_cache(N_dec)                  # 每层一份 {K, V}
for t in range(max_new):
    logits, cache = model.decode_step(next_id, memory, cache)   # 只算 1 步
    next_id = logits.argmax(-1)
    if next_id == EOS: break
```

> 📎 **详见姊妹篇 9**：为什么只缓存 K/V 不缓存 Q、显存占用公式 `2 · B · L · N · d_model · bytes`、以及 MQA / GQA / PagedAttention 等现代优化方向。

### 10.5 训练 vs 推理形状对比

| 维度 | 训练 | 推理（含 KV Cache） |
|---|---|---|
| Decoder 每次前向的输入长度 | `L_tgt`（整句一次性算） | `1`（一次一个 token） |
| Self-Attn Q 长度 | `L_tgt` | `1` |
| Self-Attn K/V 长度 | `L_tgt` | `t`（历史全部，来自 cache） |
| Cross-Attn K/V | `L_src`（来自 memory） | `L_src`（memory 只算一次，永不重算） |
| 需要 causal mask？ | ✅ 必须 | ❌ 不需要（当前 token 天然只能看历史） |

> 🎯 **一句话总结：** 训练是"整句并行"，推理是"一步一个 token 串行 + Cache 加速"。这是同一个 Transformer 的两副面孔。

---

## 11. Transformer 家族图谱

> 📎 **阅读路线：** 11.1（Encoder-Only：BERT 系）→ 11.2（Decoder-Only：GPT 系，主流 LLM）→ 11.3（Encoder-Decoder：T5 系）→ 11.4（选型指南）。

### 11.1 Encoder-Only：BERT / RoBERTa / DeBERTa

- **结构：** 只保留 Encoder，Self-Attn **无因果 mask**（可以看整句）。
- **训练目标：** MLM（Masked Language Model）—— 随机盖住 15% token 让模型预测。
- **擅长：** 分类、句对匹配、抽取式问答、NER 等 **NLU（自然语言理解）** 任务。
- **不擅长：** 生成（结构上就不适合）。

### 11.2 Decoder-Only：GPT / LLaMA / Qwen / DeepSeek（主流 LLM）

- **结构：** 只保留 Decoder，但**去掉 Cross-Attn**（没有 Encoder 就没有 memory）。剩下 Masked Self-Attn + FFN。
- **训练目标：** 下一个 token 预测（Causal LM）。
- **擅长：** 生成、对话、few-shot 学习——**目前所有主流 LLM 都是这个架构**。
- **为什么赢了？** 数据、算力、scaling law 三者叠加：单一目标（预测下一个词）能吃下互联网所有文本。

### 11.3 Encoder-Decoder：原始 Transformer / T5 / BART / mBART

- **结构：** 完整的 Encoder + Decoder（本文第 9 节实现的就是这种）。
- **擅长：** 翻译、摘要、任何"**输入 → 输出**"两端不同的 seq2seq 任务。
- **代表：** T5 把所有 NLP 任务统一成 "text-in / text-out"，是这个流派的巅峰。

### 11.4 选型指南

| 任务类型 | 首选架构 | 例子 |
|---|---|---|
| 分类 / NER / 抽取式问答 | Encoder-Only | BERT |
| 通用对话 / 生成 / few-shot | Decoder-Only | GPT-4、LLaMA、Qwen |
| 翻译 / 摘要 / seq2seq | Encoder-Decoder | T5、mBART |
| 追求最高性能（预算充足） | Decoder-Only + 大参数 | 现代 LLM 事实标准 |

---

## 12. 常见误区与 FAQ

**Q1：多头注意力 = 多层 Transformer？**  
A：❌ 完全不同。多头是**同一层内部**的 4/8/16 个并行注意力头；多层是**堆叠**的 6/12/96 个 Transformer 层。详见姊妹篇 6.8.10。

**Q2：Encoder 和 Decoder 一定要一起用？**  
A：❌ 不一定。BERT 只用 Encoder，GPT 只用 Decoder。**Encoder-Decoder 只在"两端不同"的 seq2seq 任务里必要**。

**Q3：LayerNorm 放哪最好？**  
A：现代 Transformer 全部采用 **Pre-LN**（`x + Sublayer(LN(x))`），比 Post-LN 训练稳定得多。详见本文 4.3。

**Q4：为什么 GPT 不用 Encoder？**  
A：GPT 做的是"续写"（下一个词预测），源和目标是**同一段文本**，没必要拆两半。Decoder + Masked Self-Attn 已经能同时"编码历史 + 生成未来"。

**Q5：Transformer 一定要用位置编码吗？**  
A：❌ 不一定。有了 RoPE / ALiBi 这类"融入 attention 计算"的相对位置方案后，可以省掉显式 PE 层。但**必须以某种形式把位置信息告诉模型**，否则 self-attn 是置换不变的。详见姊妹篇 8。

**Q6：训练时目标序列右移一位是什么意思？**  
A：Decoder 输入 `[<bos>, w1, w2, w3]`，labels 是 `[w1, w2, w3, <eos>]`——每个位置的 label 正好是"下一个词"。这就是 teacher forcing，见本文 9.3。

**Q7：Cross-Attention 的 K/V 从 memory 来，那 memory 每步都要重算吗？**  
A：❌ 不用！Encoder 只跑一次，memory 算一次后**整个解码过程反复复用**。这是 Encoder-Decoder 架构相对 Decoder-Only 长上下文的天然优势。见本文 7.5。

**Q8：mini Transformer 4 条数据就能全对，是不是过拟合了？**  
A：✅ 是。这是**故意的**——阶段性目标就是验证"结构能跑通、能过拟合"。真实训练需要百万级平行语料 + 正则化 + 学习率调度，见本文 9.6 结论。

---

## 13. 参数量与形状速查表

**符号约定：** `B`=batch，`L_src / L_tgt`=源/目标长度，`d`=`d_model`，`H`=`n_heads`，`d_k = d/H`，`V_src / V_tgt`=词表大小。

**关键张量形状：**

| 位置 | 张量 | 形状 |
|---|---|---|
| 源 token ID | `src_ids` | `[B, L_src]` |
| 源 embedding | `src` | `[B, L_src, d]` |
| Encoder 输出 | `memory` | `[B, L_src, d]` |
| 目标 token ID（右移） | `tgt_in` | `[B, L_tgt]` |
| 目标 embedding | `tgt` | `[B, L_tgt, d]` |
| Decoder 输出 | `dec_out` | `[B, L_tgt, d]` |
| LM Head 输出 | `logits` | `[B, L_tgt, V_tgt]` |
| MHA 内部（每头） | `q, k, v` | `[B, H, L_*, d_k]` |
| FFN 中间 | `h` | `[B, L_*, d_ff]` |

**一层参数量：**

| 组件 | 参数量 |
|---|---|
| MHA（Q/K/V/O） | `4d²` |
| FFN（`d_ff=4d`） | `8d²` |
| **Encoder Layer 小计** | **`12d²`** |
| Decoder Layer（多一个 Cross-Attn） | `18d²` |
| Token Embedding | `Vd` |
| Learned PE | `L_max · d` |
| LM Head（不共享） | `Vd` |

**整机估算：**

$$
\text{Params} \approx 12 d^2 \cdot N_{\text{enc}} + 18 d^2 \cdot N_{\text{dec}} + 2 V d
$$

---

## 14. 总结

本文以"**整机装配**"为主线，把 Transformer 拆成三层看：

1. **零件层**（姊妹篇覆盖）：Attention / MHA / Self-Cross-Masked / PosEnc / KV Cache。
2. **模块层**（本文 4 ~ 7 章）：LayerNorm + 残差 + FFN → Encoder Layer / Decoder Layer。
3. **整机层**（本文 8 ~ 10 章）：Layer 堆叠 → 输入 Embedding → LM Head → 训练管线 → 推理管线。

**记住这几条最重要的结论：**

- 🎯 Transformer 的"深度可训"来自**残差**，"训练稳定"来自 **Pre-LN**，"表达能力"来自 **Attention（横向）+ FFN（纵向）** 的分工。
- 🎯 Encoder / Decoder 的差异只在于**多不多 Cross-Attn** 以及 **Self-Attn 加不加 causal mask**——其余全部一致。
- 🎯 训练是"整句并行 + teacher forcing"，推理是"一步一 token + KV Cache 复用"，**同一套权重、两副形状**。
- 🎯 现代 LLM 主流是 **Decoder-Only + Pre-LN + RoPE + SwiGLU + GQA**——每一项都能在本文与姊妹篇里找到出处。

**姊妹篇 + 本文，就是一份完整的 Transformer 学习闭环：**

```
《Attention 机制深度笔记》            《Transformer 深度笔记》（本文）
─────────────────────────           ─────────────────────────
Attention / MHA / PosEnc / KV Cache  →  Encoder / Decoder / 整机训练 / 整机推理
零件级：手推 3 token、单头训练         整机级：mini 英→中翻译、生成策略、家族图谱
```

至此，从"一个 attention 头"到"能翻译的整机 Transformer"，**完整链路打通**。🎉
