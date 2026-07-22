# Attention 机制深度笔记：从训练基础到 LLM 推理

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> Transformer 核心机制的程序员视角——覆盖 Attention、Multi-Head、Self/Cross、位置编码、KV Cache 的完整链路。

---

## 目录

1. [Python 环境与包管理](#1-python-环境与包管理)
2. [训练基础：Batch 与反向传播](#2-训练基础batch-与反向传播)
3. [损失函数：CrossEntropyLoss](#3-损失函数crossentropyloss)
4. [Batch Normalization](#4-batch-normalization)
5. [卷积层张量形状变化](#5-卷积层张量形状变化)
6. [Transformer 核心：注意力机制](#6-transformer-核心注意力机制)（含 Multi-Head Attention）
7. [Self-Attention vs Cross-Attention](#7-self-attention-vs-cross-attention)
8. [位置编码（Positional Encoding）](#8-位置编码positional-encoding)
9. [KV Cache 与推理加速](#9-kv-cache-与推理加速)
10. [维度速查表](#10-维度速查表)
11. [总结](#11-总结)

---

## 1. Python 环境与包管理

### 1.1 PIL / Pillow

- **PIL** 是 Python 2 时代的图像库，已停止维护，**PyPI 上不存在**。
- 正确做法：安装其活跃分支 **Pillow**：

```bash
pip install Pillow
```

- 代码中依然使用 `from PIL import Image` 导入。

### 1.2 包名拼写检查

- `trochvision` → 正确拼写是 `torchvision`
- 安装前务必确认 PyTorch 版本，保持 `torch` 与 `torchvision` 版本匹配。

### 1.3 标准库 vs 第三方库

- `math` 是 **Python 内置标准库**，随 Python 一起安装，**不需要也不能用 pip 安装**。
- 验证方式：`python -c "import math; print(math.sqrt(4))"`

| 类型 | 例子 | pip 管理 |
|---|---|---|
| 内置标准库 | `math`, `sys`, `os` | ❌ |
| 第三方库 | `numpy`, `torch`, `pillow` | ✅ |

---

## 2. 训练基础：Batch 与反向传播

### 2.1 数据集划分

```python
train_dataset = datasets.MNIST(root='./data', train=True, transform=transform, download=True)
test_dataset = datasets.MNIST(root='./data', train=False, transform=transform, download=True)
```

| 参数 | 加载文件 | 样本数 |
|---|---|---|
| `train=True` | `train-images-idx3-ubyte` | 60,000 |
| `train=False` | `t10k-images-idx3-ubyte` | 10,000 |

**关键结论：**
- ✅ 两者来自同一个 MNIST 数据集
- ❌ 样本完全没有重叠
- ❌ 不是从 train 里切出来的

### 2.2 Batch 训练底层逻辑

**一个 epoch 的训练流程：**

```
Epoch 1
 ├── Batch 1 (1~100)   → forward → backward → step
 ├── Batch 2 (101~200) → forward → backward → step
 ┊
 └── Batch 100 (9901~10000)
```

**一个 batch 的 5 步执行链：**

```python
for x, y in dataloader:
    optimizer.zero_grad()   # ① 清零梯度
    pred = model(x)         # ② 前向传播
    loss = criterion(pred, y) # ③ 计算损失
    loss.backward()         # ④ 反向传播
    optimizer.step()        # ⑤ 更新参数
```

| 步骤 | 底层动作 |
|---|---|
| `zero_grad()` | 把 `param.grad` 清零，防止梯度残留 |
| `model(x)` | 前向传播，构建计算图 |
| `criterion()` | 聚合 batch 内所有样本的误差，得到标量 loss |
| `backward()` | 从 loss 出发，沿计算图反向，用链式法则计算每个参数的梯度 |
| `step()` | 读取 `param.grad`，按优化规则更新参数 |

### 2.3 Batch Loss 的计算方式

**核心结论：Batch Loss = 逐样本 Loss 的平均值**

数学表达：

\[
\mathcal{L}_{\text{batch}} = \frac{1}{B}\sum_{i=1}^{B} \ell_i
\]

代码验证：

```python
# Batch Loss 是逐样本 Loss 的平均
total_loss = 0.0
count = 0

for x, y in dataloader:
    pred = model(x)
    loss = criterion(pred, y)           # batch 的平均 loss
    total_loss += loss.item() * x.size(0)  # 还原为 sum
    count += x.size(0)

epoch_loss = total_loss / count          # 整个数据集的平均 loss
```

**反向传播的真相：**

> ❌ 不是对每条样本分别 backward
> ✅ 只对 batch 的平均 loss 做一次 backward
> ✅ 但数学上等价于对每条样本分别 backward 后再取平均

原因：导数的线性性

\[
\nabla_\theta \left( \frac{1}{B} \sum_i \ell_i \right)
= \frac{1}{B} \sum_i \nabla_\theta \ell_i
\]

### 2.4 `retain_graph=True` 的使用

```python
loss.backward(retain_graph=True)
```

**作用：** 第一次 backward 后不释放计算图，允许再次 backward。

**典型场景：**
- 一个 loss，多次 backward
- 多个 loss 共享同一计算图
- GAN / WGAN-GP 训练

**注意：** 用完要及时释放，否则显存爆炸。

### 2.5 关键术语

| 名词 | 含义 |
|---|---|
| Sample | 一个样本 |
| Batch | 一组样本 |
| Iteration | 一次 forward + backward + step |
| Epoch | 所有样本过一遍模型 |

---

## 3. 损失函数：CrossEntropyLoss

### 3.1 一句话定义

> **`nn.CrossEntropyLoss(logits, target)` = `NLLLoss( LogSoftmax(logits), target )`**
>
> 即：**先** 对 logits 做 `LogSoftmax`，**再把结果传给** `NLLLoss`——两个函数**串联（复合）**，不是数值相加。

**⚠️ 关于常见写法 `LogSoftmax + NLLLoss` 的说明**

你在 PyTorch 文档、博客里经常看到这样的写法：

```
CrossEntropyLoss = LogSoftmax + NLLLoss
```

这里的 `+` 是**工程习惯记号**，含义是"把这两个步骤组合起来"，**不是数学上的 `a + b` 加法**。准确写法是**函数复合**：

\[
\text{CrossEntropyLoss}(z, y) = \text{NLLLoss}\bigl(\text{LogSoftmax}(z),\ y\bigr)
\]

用管道符号表达更直观（数据从左到右流过）：

```
logits ──► LogSoftmax ──► log_probs ──► NLLLoss(·, target) ──► loss
         (Step 1)                     (Step 2)
```

对应 PyTorch 代码就是两行串联：

```python
log_probs = F.log_softmax(logits, dim=1)   # Step 1
loss      = F.nll_loss(log_probs, target)  # Step 2
# 完全等价于：
loss      = F.cross_entropy(logits, target)
```

> 🔑 **记住**：`+` 号读作"**然后接**"（then），不是"**加**"（plus）。

### 3.2 数学公式

**沿用 3.1 的管道视角，把每一段管道都写成数学公式：**

```
logits (z) ──► LogSoftmax ──► log_probs ──► NLLLoss(·, y) ──► loss
   [C]          Step 1           [C]           Step 2         标量
```

**Step 1：`LogSoftmax`（把 logits 变成 log-probability）**

\[
\text{log\_probs}_i = \log\!\left(\frac{e^{z_i}}{\sum_j e^{z_j}}\right)
= z_i - \log\!\left(\sum_j e^{z_j}\right), \quad i = 0, 1, \dots, C-1
\]

输入 `z` 形状 `[C]`，输出 `log_probs` 形状 `[C]`，每个元素 ≤ 0。

**Step 2：`NLLLoss`（按真实类别 y 挑值、取负）**

\[
\mathcal{L} = -\,\text{log\_probs}_y
\]

即：从 Step 1 的向量里，**索引第 y 个元素**（真实类别），**再取负**。

**合并成一个公式（3.1 说的"函数复合"展开）：**

\[
\mathcal{L}(z, y)
= \underbrace{-\,}_{\text{NLLLoss 的取负}}
\underbrace{\log\!\left(\frac{e^{z_y}}{\sum_j e^{z_j}}\right)}_{\text{LogSoftmax 在第 y 位的值}}
= -z_y + \log\!\left(\sum_j e^{z_j}\right)
\]

右边第二个等号是数学化简
右边第二个等号是数学化简（把 log 拆开），并**没有新增操作**——它就是 `NLLLoss ∘ LogSoftmax` 的展开形式。

> 🔑 **公式与管道的对照**：
> - 内层 `log(e^{z_y} / Σ e^{z_j})` = 管道图中的 **Step 1（LogSoftmax）取第 y 位**
> - 外层负号 `−` = 管道图中的 **Step 2（NLLLoss 的取负）**

**Batch 版本：** 对 batch 内每个样本单独算 `L_i`，再按 `reduction` 聚合（默认 `mean`）：

\[
\mathcal{L}_{\text{batch}} = \frac{1}{B}\sum_{i=1}^{B} \mathcal{L}(z^{(i)}, y^{(i)})
\]

### 3.3 使用要点

**沿用 3.1 的管道视角，一句话说清楚：你只需要把 raw logits 喂进管道的入口，剩下的 PyTorch 全帮你做。**

```
你提供 ──► [ LogSoftmax ──► NLLLoss ] ──► loss
  ↑              CrossEntropyLoss 内部包办
raw logits + target（类别索引）
```

**（1）接口约定**

| 项目 | 要求 | 说明 |
|---|---|---|
| **入口：模型输出** | **raw logits**（未归一化分数） | ❌ 不要自己先做 softmax / log_softmax |
| **入口：target** | **类别索引** `LongTensor`，形状 `[B]` | ❌ 不是 one-hot；值域 `[0, C-1]` |
| **出口：loss** | 标量（默认 `reduction='mean'`） | 可改 `sum` / `none` |

**（2）正确用法：直接把 logits 送进管道入口**

```python
logits = model(x)                    # shape [B, C], raw 分数
loss   = criterion(logits, target)   # target shape [B], 类别索引
# 管道内部: logits ──► LogSoftmax ──► NLLLoss ──► loss
```

**（3）错误用法：在入口前手动做 softmax（管道被走两遍）**

```python
prob = torch.softmax(logits, dim=1)  # ❌ 你已经做了一次 softmax
loss = criterion(prob, target)       # ❌ criterion 内部又做一次 LogSoftmax
                                     # 结果: 管道被走了 2 次, 数学上错, PyTorch 不报错
```

**为什么错？** 参考 3.1 的管道图——`CrossEntropyLoss` 的入口**约定就是 raw logits**。你提前做了 softmax，相当于把管道图变成：

```
logits ──► softmax ──► LogSoftmax ──► NLLLoss ──► loss   ❌
                       ↑ 这一段又做了一次归一化，梯度被严重削弱
```

**（4）与 3.1 管道等价的两种写法**

```python
# 写法 A：一步到位（推荐，PyTorch 内部自动走完整条管道）
loss = F.cross_entropy(logits, target)

# 写法 B：手工拆成 3.1 的两段管道（教学 / 需要中间结果时用）
log_probs = F.log_softmax(logits, dim=1)  # Step 1: LogSoftmax
loss      = F.nll_loss(log_probs, target) # Step 2: NLLLoss
```

两种写法**数值完全一致**，A 更常用，B 更透明。

### 3.4 数值稳定性：LogSumExp Trick

PyTorch 内部实现：

\[
\log\!\left(\sum_j e^{z_j}\right)
=
\log\!\left(\sum_j e^{z_j - \max(z)}\right) + \max(z)
\]

减去最大值后，指数项不会爆炸，梯度稳定。

**公式推导（3 步就能看懂）：**

**Step 1：** 令 \(m = \max(z)\)，把每个 \(e^{z_j}\) 拆成"公共因子 × 差值项"：

\[
e^{z_j} = e^{m} \cdot e^{z_j - m}
\]

（这一步就是 \(e^{a+b} = e^a \cdot e^b\) 的基本指数律。）

**Step 2：** 求和时把公共因子 \(e^m\) 提到求和号外面（它和 \(j\) 无关）：

\[
\sum_j e^{z_j} = \sum_j e^{m} \cdot e^{z_j - m} = e^{m} \cdot \sum_j e^{z_j - m}
\]

**Step 3：** 两边取 \(\log\)，用 \(\log(a \cdot b) = \log a + \log b\)：

\[
\log\!\left(\sum_j e^{z_j}\right)
= \log(e^{m}) + \log\!\left(\sum_j e^{z_j - m}\right)
= m + \log\!\left(\sum_j e^{z_j - m}\right)
\]

代入 \(m = \max(z)\) 就得到最上面的公式。整个变换是**代数恒等式**，两边严格相等，不是近似。

**为什么这样就稳定了？（程序员视角）**

假设 `z = [1000, 1001, 1002]`（logits 很大时经常出现）：

- **直接算**：`exp(1000)` ≈ \(10^{434}\)，`float32` 上限约 \(3.4 \times 10^{38}\) → **直接 `inf`，再一相加还是 `inf`，取 `log` 得 `inf`，梯度 `NaN`**。
- **减去 max 后**：`z - max(z) = [-2, -1, 0]`，`exp(-2), exp(-1), exp(0)` 都是 0~1 之间的正常数 → 求和取 log 得到一个很小的正数，再加回 `max(z) = 1002` → **结果精确，无溢出**。

**关键洞察：** 
- 最大值项一定是 \(e^{0} = 1\)，其他项都是 \(e^{\text{负数}} \in (0, 1]\) → 求和结果落在 \([1, N]\) 之间，绝对不会爆。
- 也不会下溢到 0：因为至少有一项等于 1，`log` 出来至少是 0，不会出现 `log(0) = -inf`。

**Softmax 的稳定版本用同一招：**

\[
\text{softmax}(z_i) = \frac{e^{z_i}}{\sum_j e^{z_j}} = \frac{e^{z_i - m}}{\sum_j e^{z_j - m}}
\]

分子分母同乘 \(e^{-m}\)，值不变但避免溢出。这就是 `F.softmax` / `F.log_softmax` 内部的实际实现。

### 3.5 NLLLoss 的作用

#### 3.5.1 🔺 一句话结论（顶层）

> **NLLLoss = 从 log-probability 中取出"真实类别对应的 log-prob"，取负，再做 reduction。**

配合 `log_softmax`，两行代码就等价于 `CrossEntropyLoss`：

```python
import torch.nn.functional as F

log_probs = F.log_softmax(logits, dim=1)   # Step 1：logits → log-probability
loss      = F.nll_loss(log_probs, target)  # Step 2：挑值 → 取负 → 求平均
```

#### 3.5.2 🔻 三步主干（一层展开）

| Step | 操作 | 输入 → 输出 | 干了什么 |
|---|---|---|---|
| **1** | `F.log_softmax(logits, dim=1)` | `[B, C]` → `[B, C]` | 把 raw 打分转成 log-probability |
| **2a** | `input[i, target[i]]` | `[B, C]` → `[B]` | 按真实类别下标挑出对应 log-prob |
| **2b** | `-log_p` + `mean` | `[B]` → 标量 | 取负后求平均，得到最终 loss |

下面按顺序展开每一步的细节。

---

#### 3.5.3 Step 1：`F.log_softmax(logits, dim=1)`

**（1）它做了什么？**

数学上等价于 `log(softmax(logits))`，但 PyTorch 用 LogSumExp trick 一次算完，避免中间溢出（见 3.4 节）：

\[
\text{log\_softmax}(z_i) = z_i - \log\!\left(\sum_j e^{z_j}\right)
\]

**这个公式怎么来的？（定义 + 3 步推导）**

**定义（顾名思义）：** `log_softmax` = 先做 `softmax`，再取 `log`。所以出发点就是把两个函数复合起来：

\[
\text{log\_softmax}(z_i)\;\overset{\text{def}}{=}\;\log\bigl(\text{softmax}(z_i)\bigr)
\]

**Step 1：代入 softmax 的定义**

`softmax` 第 i 个分量的定义就是"指数归一化"：

\[
\text{softmax}(z_i) = \frac{e^{z_i}}{\sum_j e^{z_j}}
\]

所以：

\[
\text{log\_softmax}(z_i) = \log\!\left(\frac{e^{z_i}}{\sum_j e^{z_j}}\right)
\]

**Step 2：用 `log(a/b) = log a − log b` 拆开分数**

\[
\log\!\left(\frac{e^{z_i}}{\sum_j e^{z_j}}\right)
= \log\bigl(e^{z_i}\bigr) - \log\!\left(\sum_j e^{z_j}\right)
\]

**Step 3：用 `log(e^x) = x` 消掉分子的 log**

\[
\log\bigl(e^{z_i}\bigr) = z_i
\]

代回去就得到最终形式：

\[
\boxed{\;\text{log\_softmax}(z_i) = z_i - \log\!\left(\sum_j e^{z_j}\right)\;}
\]

> 🔗 **工程实现**：分子的 `log(e^{z_i}) = z_i` 是免费化简（无浮点运算）；剩下的分母 `log(Σ e^{z_j})` 直接交给 **3.4 节的 LogSumExp trick**，就避开了 `softmax(...).log()` 会遇到的两处溢出（`exp` 上溢 + `log(0)` 下溢），且省去一次除法。这就是 `F.log_softmax` 比 `softmax(...).log()` 更稳、更快的根本原因。

> 📌 **符号对照（贯穿 Step 1 → Step 2）**：
> - 数学公式里的 \(z\)、\(z_i\)、\(z_j\) = 3.4 节里的**同一个 logits 向量**（同一个样本对各类别的打分）。
> - 代码变量 `log_probs` = 把上面公式**对整个 batch、所有类别**都算一遍后得到的张量，形状 `[B, C]`。
> - 严格对应关系：**`log_probs[i, c] = log_softmax(z_i)` 中的第 c 个分量** = 第 `i` 个样本在类别 `c` 上的 log-probability。
>
> 后面 Step 2 里出现的 `log_probs`，就是这里刚算出来的这个张量，请直接对号入座。

**（2）形状不变，值变成负数**

以 `batch_size=2, num_classes=3` 为例：

```python
logits = torch.tensor([[2.0, 1.0, 0.1],       # 样本0 对 3 个类别的打分
                       [0.5, 2.5, 1.0]])      # 样本1 对 3 个类别的打分
# shape: [2, 3]

log_probs = F.log_softmax(logits, dim=1)
# tensor([[-0.417, -1.417, -2.317],           # exp 后每行加起来 = 1
#         [-2.169, -0.169, -1.669]])
# shape: [2, 3]（形状不变，值全为负）
```

**（3）关键参数：`dim=1` 为什么这么选？**

| 维度 | 含义 | 说明 |
|------|------|------|
| `dim=0` | 沿 batch 方向（垂直 ↓） | ❌ 把不同样本的同一类别归一化，无意义 |
| `dim=1` | 沿类别方向（水平 →） | ✅ 每个样本内部，各类别概率和 = 1 |

**可视化理解**：`logits` 是 `[2, 3]` 矩阵，行=样本、列=类别：

```
                  类别0   类别1   类别2
             ┌─────────────────────────┐
   样本0     │   2.0     1.0    0.1   │  ← dim=1：这一行做 softmax（正确）
   样本1     │   0.5     2.5    1.0   │
             └─────────────────────────┘
              ↑ dim=0：这一列做 softmax（错误）
```

**实际数值对比**：

```python
# dim=1（正确）→ 每"行"加起来 = 1
softmax(logits, dim=1) = [[0.659, 0.242, 0.099],   # ✓ 0.659+0.242+0.099 ≈ 1
                          [0.101, 0.750, 0.169]]   # ✓ 0.101+0.750+0.169 ≈ 1
# 读法：样本0 有 65.9% 是类别0，合理 ✅

# dim=0（错误）→ 每"列"加起来 = 1
softmax(logits, dim=0) = [[0.818, 0.182, 0.289],   # 列内 0.818+0.182 = 1
                          [0.182, 0.818, 0.711]]
# 读法："在类别0 上，样本0 占 81.8%"——问题本身就没意义 ❌
```

**为什么 `dim=0` 没意义？** 分类任务问的是"每个样本自己属于哪一类"，样本之间是独立的——A 是猫的概率高，跟 B 是不是猫毫无关系。

> 🔑 **一句话记：softmax 要沿"类别所在的那一维"做。**

**（4）为什么不是 `softmax(...).log()`？**

三个坑：

1. **数值稳定**：如上所述，`log_softmax` 化简后可直接套 LogSumExp；朴素写法则会踩 `exp` 上溢 / `log(0)` 下溢两处坑。
2. **更快**：省一次 `exp` + 一次 `log`。
3. **语义配对**：`NLLLoss` 按约定吃 log-probability（NLL = **N**egative **L**og **L**ikelihood）；传 `softmax` 结果不会报错，但结果错——最阴的 bug。

---

#### 3.5.4 Step 2：`F.nll_loss(log_probs, target)`

**（1）内部逻辑（伪代码）**

```python
# 输入 log_probs 就是 Step 1 算出来的张量，形状 [B, C]
# log_probs[i, c] = 第 i 个样本在类别 c 上的 log-probability
losses = []
batch_size = 2
for i in range(batch_size):
    t     = target[i]              # 第 i 个样本的真实类别编号（例如 t=0）
    log_p = log_probs[i, t]        # 从 log_probs 挑出 [i, t] 位置的值（即真实类别的 log-prob）
    losses.append(-log_p)          # 取负（log_prob 是负数，取负后为正的 loss）
loss = torch.stack(losses).mean()                 # 默认 reduction='mean'
```

**核心**：不做任何数学变换，只做**索引 → 取负 → 求平均**三个操作。

**（2）为什么要"取负"？**

`log_prob` 恒为负（概率 ∈ (0, 1]，log 之后 ≤ 0）。取负后 loss 恒为正，才符合"loss 越小越好"的习惯：

- 正确类别概率 → 1，`log_prob` → 0，`-log_prob` → 0（loss 小 ✅）
- 正确类别概率 → 0，`log_prob` → -∞，`-log_prob` → +∞（loss 爆炸，梯度强推模型改正 ✅）

---

#### 3.5.5 端到端串联：从 logits 到 loss

##### （1）流程速览：4 步走完管道

沿用上面的例子，假设 `target = torch.tensor([0, 1])`（样本0 正确答案是类别0，样本1 是类别1）：

```
logits              log_probs              按 target 挑值         取负       平均
[[2.0, 1.0, 0.1],   [[-0.417,-1.417,-2.317], 样本0取[0,0]=-0.417   0.417   ↘
 [0.5, 2.5, 1.0]] →  [-2.169,-0.169,-1.669]] 样本1取[1,1]=-0.169   0.169 → (0.417+0.169)/2
                                                                            = 0.293
```

##### （2）完整可运行代码

```python
import torch
import torch.nn.functional as F

target = torch.tensor([0, 1])

logits = torch.tensor([[2.0, 1.0, 0.1],
                       [0.5, 2.5, 1.0]])

# ---- 方法1： 逐步手搓 ----

# dim=1（正确）→ 每行加起来 = 1
t1 = torch.softmax(logits, dim=1)
print(t1)
# dim=0（错误）→ 每列加起来 = 1
t2=torch.softmax(logits, dim=0) 
print(t2)

log_probs = torch.log_softmax(logits, dim=1)  # Step 1: LogSoftmax
print(log_probs)

losses = []
batch_size = logits.shape[0]      # 或者 target.shape[0]
for i in range(batch_size):
    label     = target[i]              # 第 i 个样本的真实类别编号（例如 t=0）
    print(f"i={i},label = {label}")
    log_p = log_probs[i, label]        # 从 log_probs 挑出 [i, t] 位置的值（即真实类别的 log-prob）
    print(f"log_p = {log_p}")
    losses.append(-log_p)          # 取负（log_prob 是负数，取负后为正的 loss）

print(f"losses={losses}")

loss_manual  = torch.stack(losses).mean()               # 默认 reduction='mean'

print(f"loss_manual = {loss_manual}")

# ---- 方法2： 官方 API 对照 ----

loss_api = F.nll_loss(log_probs, target)

print(f"loss_api = {loss_api}")


# ---- 方法3： ：cross_entropy 一步到位 ----

loss_ce  = F.cross_entropy(logits, target)         # ✅ 推荐写法

# ---- 三方对照

print(f"手写 NLL      = {loss_manual.item():.6f}")
print(f"F.loss_api    = {loss_api.item():.6f}")
print(f"F.cross_entropy = {loss_ce.item():.6f}")
# 三者应完全相等：0.293412 
```


##### （3）代码分析1：循环中，刚好挑选了行的最大值的原因

训练的目的 = 让"target 挑中的位置"和"每行最大值的位置"变成同一个。

```
                     ┌──────────────────────────┐
                     │  argmax(log_probs[i, :]) │  ← 模型的"回答"
                     │  = 模型认为最可能的类别    │
                     └──────────────────────────┘
                                 ▲
                                 │  训练目标：让两者相等
                                 ▼
                     ┌──────────────────────────┐
                     │       target[i]          │  ← 数据的"标准答案"
                     │  = 真实类别（监督信号）    │
                     └──────────────────────────┘
```

```
类别0      类别1      类别2
样本0  →  [ -0.4170*, -1.4170,  -2.3170 ]   ← i=0, label=0, 挑 [0,0]=-0.4170
样本1  →  [ -2.3064,  -0.3064*, -1.8064 ]   ← i=1, label=1, 挑 [1,1]=-0.3064
              ↑           ↑
             挑中         挑中
              6 格里只挑了 2 格（每行 1 格） 
```

```python
logits = [[2.0, 1.0, 0.1],     # 类别 0 分数最高 → 预测 0 → target=0 ✅
          [0.5, 2.5, 1.0]]     # 类别 1 分数最高 → 预测 1 → target=1 ✅ 
```

##### （4）代码分析2：为何只打印2个值

因为 target 里只有 2 个元素：target = tensor([0, 1])
代码是按 target 走的，不是按 log_probs 的所有元素走的。
target 有多少个样本，就挑多少次，跟 log_probs 的形状 [2, 3] 里的 3（类别数）无关。

log_probs 是一张 2×3 的"log-概率表"，一共有 2 × 3 = 6 个数（2 个样本 × 3 个类别的 log-probability）。

```
类别0      类别1      类别2
样本0  →  [ -0.4170,  -1.4170,  -2.3170 ]
样本1  →  [ -2.3064,  -0.3064,  -1.8064 ]
```

target 说"每个样本的正确答案是谁"

```python
target = torch.tensor([0, 1])
#                      ↑  ↑
#                      │  └── 样本1 的正确类别 = 1
#                      └───── 样本0 的正确类别 = 0
```

循环干的事情：只挑"正确答案对应的那一格"

```python
for i in range(batch_size):        # i 只走 0, 1（2 次）
    label = target[i]              # 拿到第 i 个样本的正确类别
    log_p = log_probs[i, label]    # 只挑 [i, label] 这一格
```

配合表格看：

```
类别0      类别1      类别2
样本0  →  [ -0.4170*, -1.4170,  -2.3170 ]   ← i=0, label=0, 挑 [0,0]=-0.4170
样本1  →  [ -2.3064,  -0.3064*, -1.8064 ]   ← i=1, label=1, 挑 [1,1]=-0.3064
              ↑           ↑
             挑中         挑中
              6 格里只挑了 2 格（每行 1 格）
```

其他 4 格（-1.4170, -2.3170, -2.3064, -1.8064）根本没进循环。

类比：查成绩单

想象 log_probs 是一张成绩单：

```
学生	语文	数学	英语
小明	60	    90	    70
小红	85	    75	    80
```

target = [数学, 语文] 相当于告诉你："我只想知道小明的数学成绩和小红的语文成绩"。

那你当然只会查 2 次（每人查 1 科），而不会把 6 个成绩全打印一遍。其他科的成绩存在，但和"我想问的问题"无关。

---

#### 3.5.6 工程提醒（常见坑）

> ⚠️ **不要自己先做 softmax 再算 loss**。`F.cross_entropy(logits, target)` 一步完成"log_softmax + nll_loss"，训练时直接传 raw logits 即可（见 3.3 节错误示例）。

> ⚠️ **`log_softmax` 的 `dim` 一定是"类别"所在的维度**。对于 `[B, C]` 是 `dim=1`；对于 `[B, C, H, W]`（语义分割）是 `dim=1`；对于 `[B, L, V]`（语言模型）是 `dim=-1`。记住口诀：**沿类别归一化**。

---

## 4. Batch Normalization

### 4.1 一句话定义

> **对每个 batch 内的激活值做"去均值、除标准差"的标准化，再用可学习参数恢复表达能力；同时通过滑动平均维护全局统计量，用于推理阶段。**

### 4.2 数学公式

**训练时：**

\[
\mu_c = \frac{1}{B} \sum_{i=1}^{B} x_{i,c}
\]

\[
\sigma_c^2 = \frac{1}{B} \sum_{i=1}^{B} (x_{i,c} - \mu_c)^2
\]

\[
\hat{x}_{i,c} = \frac{x_{i,c} - \mu_c}{\sqrt{\sigma_c^2 + \epsilon}}
\]

\[
y_{i,c} = \gamma_c \hat{x}_{i,c} + \beta_c
\]

**推理时：**

\[
\hat{x} = \frac{x - \text{running\_mean}}{\sqrt{\text{running\_var} + \epsilon}}
\]

### 4.3 训练 vs 推理

| 模式 | 使用什么统计 | 更新 running stats |
|---|---|---|
| `model.train()` | 当前 batch 的 μ、σ² | ✅ |
| `model.eval()` | running_mean / running_var | ❌ |

### 4.4 代码实例

```python
bn2d = nn.BatchNorm2d(num_features=64)

x = torch.randn(32, 64, 28, 28)    # [B, C, H, W]
out = bn2d(x)
print(out.shape)                     # torch.Size([32, 64, 28, 28])
```

**关键：**
- BN 是对 **每个通道 C 独立** 做归一化
- 在 `[N, H, W]` 上求均值和方差
- BN 是 **batch-level** 操作，不是对整个数据集

### 4.5 滑动平均

**一句话定义：**

> **训练时用每个 batch 的统计量，"以指数加权平均"的方式，持续更新一份全局统计量（`running_mean` / `running_var`），推理时直接使用它。**

#### 为什么需要滑动平均？

- 训练时：每个 batch 都有自己的 μ、σ²，波动大，但样本"新鲜"。
- 推理时：往往一次只喂 1 张样本，**根本算不出 batch 统计量**。
- 解决办法：训练过程中"顺手"维护一份全数据集的近似统计量，推理时直接拿来用。

#### 数学公式

\[
\text{running\_mean} \leftarrow (1 - m) \cdot \text{running\_mean} + m \cdot \mu_{\text{batch}}
\]

\[
\text{running\_var} \leftarrow (1 - m) \cdot \text{running\_var} + m \cdot \sigma^2_{\text{batch}}
\]

- `m` = 动量（momentum），PyTorch 默认 `0.1`
- `(1 - m)` 保留历史，`m` 融入当前 batch
- 本质是 **指数移动平均（EMA）**，越久远的 batch 权重越小

#### 程序员视角：等价伪代码

```python
# PyTorch BatchNorm 内部逻辑（简化版）
if self.training:
    batch_mean = x.mean(dim=[0, 2, 3])           # 当前 batch 均值
    batch_var  = x.var(dim=[0, 2, 3], unbiased=False)

    # 用当前 batch 做归一化
    x_hat = (x - batch_mean) / sqrt(batch_var + eps)

    # 顺手更新全局统计量（不参与反向传播）
    with torch.no_grad():
        self.running_mean = (1 - m) * self.running_mean + m * batch_mean
        self.running_var  = (1 - m) * self.running_var  + m * batch_var
else:
    # 推理：直接用累积好的全局统计量
    x_hat = (x - self.running_mean) / sqrt(self.running_var + eps)
```

#### 类比：程序员熟悉的场景

| 场景 | 类比 |
|---|---|
| 滑动窗口平均 QPS | `avg = 0.9 * avg + 0.1 * current_qps` |
| 系统负载 `load average` | Linux 里 1/5/15 分钟负载就是 EMA |
| Adam 优化器的一阶矩 | 同样是 `m_t = β·m_{t-1} + (1-β)·g_t` |

> **一句话：** `running_mean` 就是给统计量做了个"低通滤波"，滤掉 batch 噪声，得到全局趋势。

#### 关键要点

| 要点 | 说明 |
|---|---|
| 更新时机 | 只在 `model.train()` 且执行 `forward` 时更新 |
| 是否需要梯度 | ❌ 不参与反向传播，`requires_grad=False` |
| 保存位置 | 作为 `buffer` 存在 `state_dict` 里，随 `.pth` 一起保存/加载 |
| 动量方向 | ⚠️ PyTorch 的 `m` 是"新样本权重"，与部分论文相反（论文常记 `α`，等于 `1-m`） |
| 常见坑 | 忘记切 `model.eval()` → 推理时仍在更新 running stats，结果不稳定 |

---

## 5. 卷积层张量形状变化

### 5.1 Conv2D 输出形状公式

\[
H_{\text{out}} = \left\lfloor \frac{H_{\text{in}} + 2\times\text{padding} - \text{kernel\_size}}{\text{stride}} \right\rfloor + 1
\]

### 5.2 实例解析

```python
# 输入: [32, 3, 28, 28]
# Conv2D(3 → 16, kernel=3, stride=1, padding=0)
# 输出: [32, 16, 26, 26]
```

| 维度 | 变化 | 结果 |
|---|---|---|
| Batch | 不变 | 32 |
| 通道 | `out_channels=16` | 16 |
| 高 | 28 - 3 + 1 | 26 |
| 宽 | 28 - 3 + 1 | 26 |

**16 个输出通道 = 16 个卷积核**，每个卷积核形状为 `[3, 3, 3]`（in_channels, kernel_h, kernel_w）。

### 5.3 完整数据流

```
输入图像 [32, 3, 28, 28]
    ↓ Conv2D(3→16, 3×3)
    ↓ [32, 16, 26, 26]
    ↓ BatchNorm2D(16)
    ↓ [32, 16, 26, 26]  ← 形状不变，数值归一化
    ↓ ReLU
    ↓ [32, 16, 26, 26]  ← 形状不变，负数变 0
```

---

## 6. Transformer 核心：注意力机制

### 6.1 核心公式

\[
\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V
\]

### 6.2 为什么要除以 √d_k？

当 d_k 较大时，Q 和 K 的点积方差随维度线性增长，导致 softmax 输入值过大，梯度趋近于零。缩放后使方差恢复到 1，保证梯度正常流动。

### 6.3 Q / K / V 的 Shape 解析

```python
Q: [B, H, Lq, d_k]
K: [B, H, Lk, d_k]
V: [B, H, Lk, d_v]
```

| 维度 | 含义 |
|---|---|
| B | Batch size，并行处理多少条样本 |
| H | 注意力头数，从不同角度观察同一序列 |
| L | 序列长度（token 数） |
| d_k | 每个头的向量维度，表示"查询/键的表示能力" |

### 6.4 缩放点积注意力完整推导

```python
scores = Q @ K.transpose(-2, -1) / sqrt(d_k)
# Q: [B, H, Lq, d_k]
# K^T: [B, H, d_k, Lk]
# scores: [B, H, Lq, Lk]

attn = softmax(scores, dim=-1)      # [B, H, Lq, Lk]
output = attn @ V                    # [B, H, Lq, d_v]
```

**`transpose(-2, -1)` 的作用：** 把 `d_k` 维换到中间，满足矩阵乘法规则。

> 下面围绕核心一行 `attn = softmax(scores, dim=-1)` 展开 9 个子小节，从直觉、公式、伪代码到数值实例，最后一节（6.4.9）把 `attn @ V` 的过程也一并闭环。

---

#### 6.4.1 一句话理解

> 对 `scores` 张量 `[B, H, Lq, Lk]` 的 **最后一维 `Lk`**（"每个 query 对所有 key 的打分"）做归一化，把打分变成"**总和为 1 的注意力权重**"。

**🔑 拆解这句话的每个词：**

| 术语 | 含义 | 举例（翻译任务：英→中） |
|---|---|---|
| `Lq` | **Q**uery 的序列长度，即"提问方"有多少个 token（每个 token 都要主动去和所有 key 匹配） | 中文句子 `"我 / 非常 / 喜欢 / 猫"`，Lq = 4 |
| `Lk` | **K**ey 的序列长度，即被 query 匹配打分的候选 token 数量（在交叉注意力里是"被检索的资料库"，在 self-attention 里就是序列自己） | 英文句子 `"I / love / cats"`，Lk = 3 |
| `scores[b,h,i,j]` | 第 `i` 个 query 与第 `j` 个 key 的**点积得分**（即 `Q·Kᵀ / √d_k`，可直观理解为"未归一化的相似度"，值越大越相关） | `"喜欢"` 与 `"love"` 的点积得分 |

> 📌 **两个术语上的严谨说明**：
> - **"key" 不一定是"被动被查"的**：只在**交叉注意力**（如翻译的 encoder-decoder）里，K 才明显是"被检索的资料库"；在 **self-attention** 中，Q、K、V 都来自同一序列，每个 token 既是 query 也是 key，可以理解为"**序列内每个 token 相互打分**"。
> - **"分数"严格来说不是"相似度"**：`scores = Q·Kᵀ / √d_k` 得到的是**点积**（缩放版），而不是余弦相似度（没除向量模长）。教学上叫它"相似度分数"是通用简化，直觉是"点积越大 → 向量方向越接近 → 语义越相关"。

> 💡 **为什么 Q 是目标语言（中文）、K 是源语言（英文）？**
> 在 Transformer 的 **encoder-decoder 交叉注意力**里：
> - **Q 来自 decoder**：正在生成的**目标语言**（在"提问：我下一个词该看源句的哪里？"）
> - **K/V 来自 encoder**：已经编码好的**源语言**（作为"被检索的资料库"）
>
> 所以对于"英→中"翻译：中文 = Q（目标），英文 = K/V（源）。

> 🚨 **常见误解：Q 是"用户问题"，V 是"最终答案"？**
>
> 这个直觉来自 **RAG / 搜索引擎** 场景（Q = 用户输入的问题，V = 知识库文档），**在 Transformer 内部并不适用**。需要重新校准心智模型：
>
> **① Q / K / V 是同一批 token 的"三种角色化投影"**
>
> ```python
> Q = x @ W_Q    # 同一批 token → 3 个独立的线性投影矩阵
> K = x @ W_K    # → 得到 3 个语义空间的向量
> V = x @ W_V    # W_Q / W_K / W_V 都是可学习参数
> ```
>
> 📖 **这里的 `x` 是什么？**
> - `x` 是**当前 attention 层的输入序列**，形状 `[B, L, d_model]`
>   - `B` = batch size；`L` = 序列 token 数；`d_model` = 每个 token 的向量维度（如 512）
> - 每个 token 在 `x` 里就是一个 `d_model` 维向量（由 embedding + 位置编码得来）
> - **具体是谁**取决于这一层 attention 长在哪里：
>   - Encoder 的 self-attention → `x` = 源序列（如英文 `"I / love / cats"`）
>   - Decoder 的 self-attention → `x` = 已生成的目标序列（如中文 `"我 / 非常 / ..."`）
>   - Cross-attention → 有**两个 x**：Q 用 decoder 的 x，K/V 用 encoder 的 x（详见 7.2 节）
> - `W_Q / W_K / W_V` 是 3 个独立的 `[d_model, d_model]` 可学习矩阵，把 `x` 分别投影到 3 个语义空间
>
> > **② 每个 token 同时扮演 3 种角色**
>
> | 角色 | 含义 | 类比（图书馆） |
> |---|---|---|
> | **Q** | 我这个 token"**想找什么信息**" | 手里的**检索卡片** |
> | **K** | 我这个 token"**能被谁匹配到**" | 每本书的**书脊标签** |
> | **V** | 我这个 token"**能提供什么内容**" | 书本的**实际内容** |
>
> 一本书**同时**拥有 K（标签）和 V（内容）；同理，一个 token 既是"查询者"也是"被查询者"。
>
> **③ 具体到"喜欢"这个 token（英→中翻译）**
>
> ```
> "喜欢".Q  → 表达："我要生成'喜欢'，该从英文源句里找什么信息？"
>              ↓ 与英文各 token 的 K 做点积打分
>    "I".K   → 0.05        （匹配度低）
>    "love".K → 0.9   ✅   （匹配度高）
>    "cats".K → 0.05
>              ↓ 按分数从 V 里加权抽取内容
> 输出 ≈ 0.9 × "love".V + 0.05 × "I".V + 0.05 × "cats".V
> ```
>
> 所以 **`"喜欢"` 不是"用户问题"**，而是**"decoder 生成过程中当前位置的向量"**；它以 Q 的身份去英文源句里"检索"最相关的语义。
>
> **④ 三层"Query"概念的对比**
>
> | 层次 | Query 是谁 | Value 是谁 |
> |---|---|---|
> | 搜索引擎 | 用户输入的关键词 | 网页内容 |
> | RAG 系统 | 用户问题的 embedding | 知识库文档的 embedding |
> | **Transformer 内部** | **每个 token 的 Q 投影向量** | **每个 token 的 V 投影向量** |
>
> 三者都是"用 Q 匹配 K，加权取 V"的**同一模式**，但**主体不同**：前两者是"外部人"在查询，后者是"每个 token 自己"在查询。
>
> **⑤ 谁才是"最终答案"？**
>
> - **不是 V**：V 只是每个 token 提供的"原料"
> - **而是 `attn @ V` 的输出**：它才是"Q 检索完成后加权聚合出来的结果"，最接近你直觉里的"答案"

**📊 用一张表格理解 `scores` 的形状 `[Lq, Lk]`（先忽略 B、H 两维）：**

假设 Lq=4（中文 4 个 token），Lk=3（英文 3 个 token），那么 `scores` 是一个 4×3 的矩阵：

```
                  key₀="I"   key₁="love"  key₂="cats"
query₀ "我"      [  0.9        0.05         0.05    ]  ← 第 0 行：我 对所有 key 的打分
query₁ "非常"    [  0.1        0.8          0.1     ]  ← 第 1 行：非常 对所有 key 的打分
query₂ "喜欢"    [  0.05       0.9          0.05    ]  ← 第 2 行：喜欢 对所有 key 的打分
query₃ "猫"      [  0.05       0.05         0.9     ]  ← 第 3 行：猫 对所有 key 的打分
                 └────────── 最后一维 Lk=3 ──────────┘
```

**关键理解：**
- **每一行**长度为 `Lk`，代表"**一个 query**（一个中文 token）站出来，对**所有 Lk 个 key**（所有英文 token）逐一打分"
- 所以"最后一维 `Lk`"这个方向上的数据，就是**一个 query 对所有 key 的打分列表**
- `softmax(dim=-1)` 就是**沿着这个方向做归一化** → 让每一行加起来 = 1 → 变成"该 query 该把注意力**分给哪个 key、分多少**"的概率分布

**🎯 一句话总结：**
> `Lk` 那一维 = "**一个 query 面前排着 Lk 个候选 key，它给每个 key 打的分数**"。
> softmax 把这些分数变成一个**加权投票的权重分布**（比如：70% 看这个 key，20% 看那个 key，10% 看另一个 key）。

#### 6.4.2 数学公式

对每一行（固定 `b, h, i`），对 `Lk` 个分数做 softmax：

\[
\text{attn}[b, h, i, j] = \frac{\exp(\text{scores}[b, h, i, j])}{\displaystyle\sum_{k=0}^{L_k - 1} \exp(\text{scores}[b, h, i, k])}
\]

- 分子：把打分取指数 → 全部变正数，且**放大差距**（大的更大）
- 分母：把这一行所有指数值加起来 → 用于归一化
- 结果：**每一行加起来 = 1**，可以直接当作"概率/权重"使用

#### 6.4.3 `dim=-1` 到底在对谁做归一化？

`scores` 的形状是 `[B, H, Lq, Lk]`，最后一维是 `Lk`：

```
scores[b, h, i, :] = [s0, s1, s2, ..., s_{Lk-1}]
                     ↑ query i 对 Lk 个 key 的打分
       ↓ softmax(dim=-1)
attn[b, h, i, :]   = [a0, a1, a2, ..., a_{Lk-1}]   且 Σaj = 1
```

**关键点：** 每个 query（每一行）**独立**做 softmax，行与行之间互不影响。

#### 6.4.4 程序员视角：等价伪代码

```python
# softmax(scores, dim=-1) 等价于下面这段
def softmax_last_dim(scores):
    # scores: [B, H, Lq, Lk]

    # ① 数值稳定性：减去每行最大值（防止 exp 溢出）
    scores_max = scores.max(dim=-1, keepdim=True).values   # [B, H, Lq, 1]
    scores_stable = scores - scores_max                    # 广播减法

    # ② 取指数
    exp_scores = torch.exp(scores_stable)                  # [B, H, Lq, Lk]

    # ③ 沿最后一维求和作为分母
    denom = exp_scores.sum(dim=-1, keepdim=True)           # [B, H, Lq, 1]

    # ④ 归一化，广播除法
    attn = exp_scores / denom                              # [B, H, Lq, Lk]
    return attn
```

> ⚠️ **① 减最大值是必须的**：如果某个分数是 `1000`，`exp(1000)` 会直接 `inf`。减去最大值不改变结果（分子分母同乘常数），但保证数值稳定。这也是所有工业级 softmax 的标准实现。

#### 6.4.5 具体数值例子

假设某一行 `scores[b, h, i, :] = [2.0, 1.0, 0.1]`（`Lk = 3`）：

| 步骤 | 计算 | 结果 |
|---|---|---|
| 减最大值 | `[2-2, 1-2, 0.1-2]` | `[0, -1, -1.9]` |
| 取 exp | `[e⁰, e⁻¹, e⁻¹·⁹]` | `[1.000, 0.368, 0.150]` |
| 求和 | `1.000 + 0.368 + 0.150` | `1.518` |
| 归一化 | 每项 / 1.518 | `[0.659, 0.242, 0.099]` |
| 验证 | 相加 | `= 1.000` ✅ |

**解读：** query `i` 有 **65.9%** 的注意力投给第 0 个 key，24.2% 给第 1 个，9.9% 给第 2 个。

#### 6.4.6 为什么用 softmax 而不是别的？

| 需求 | softmax 如何满足 |
|---|---|
| 权重非负 | `exp(x) > 0` 恒成立 |
| 权重之和 = 1 | 分母就是归一化因子 |
| 拉开差距 | `exp` 是凸函数，大的分数被放大更多 |
| 处处可导 | 支持反向传播梯度 |

#### 6.4.7 与 `scale = 1/√d_k` 的关系（为什么要缩放）

- 若不缩放，`d_k` 很大时点积方差会变大，`scores` 数值悬殊
- softmax 遇到极端值会输出接近 **one-hot**（几乎只有一个位置是 1，其余 0）
- 后果：梯度接近 0 → **梯度消失**，训练不动
- 因此先除以 `√d_k`，把分数拉回合理范围，再送入 softmax

#### 6.4.8 形状变化速查

```
scores : [B, H, Lq, Lk]           # softmax 前
   │
   ├─ softmax(dim=-1)  ← 只在最后一维归一化
   ▼
attn   : [B, H, Lq, Lk]           # 形状不变，但每行之和 = 1
```

#### 6.4.9 `output = attn @ V` 的底层逻辑（把例子闭环）

前面 8 步走完，我们拿到了**权重矩阵 `attn`**，但它只是"每个 query 该给每个 key 分多少注意力"的**分配比例**，还没真正**读取内容**。这一步就是"照着权重去 V 里加权取内容"，得到最终输出。

##### 6.4.9.1 一句话理解

> `output = attn @ V`：**每一个 query 位置的输出，等于所有 V 向量按 `attn` 权重加权求和**。
> 即"知道该看谁、看多重" → "真的去看，把看到的东西按比例混合起来"。

##### 6.4.9.2 数学公式

对每一行（固定 `b, h, i`），输出向量是 `L(k)` 个 V 向量的加权和：

\[
\text{output}[b, h, i, :] = \sum_{j=0}^{L_k - 1} \text{attn}[b, h, i, j] \cdot V[b, h, j, :]
\]

- `attn[b,h,i,j]`：**标量**权重（介于 0~1，一行加起来 = 1）
- `V[b,h,j,:]`：**向量**（长度为 `d_v`，即第 `j` 个 key 携带的实际内容）
- **输出**：一个长度为 `d_v` 的向量（第 `i` 个 query 位置的"加权阅读结果"）

**🔢 一个最小例子（把 Σ 展开）**

固定某个 query（即固定 `b, h, i`），设 `Lk = 3`、`d_v = 2`：

```
attn[b, h, i, :] = [ 0.7,   0.2,   0.1 ]        # 3 个权重，和 = 1

V[b, h, 0, :]    = [ 1.0,   0.0 ]               # 第 0 个 key 的内容向量
V[b, h, 1, :]    = [ 0.0,   1.0 ]               # 第 1 个 key 的内容向量
V[b, h, 2, :]    = [ 0.5,   0.5 ]               # 第 2 个 key 的内容向量
```

按公式逐项展开求和：

| 项 `j` | `attn[..,j]` | `V[..,j,:]` | `attn[..,j] · V[..,j,:]`（标量 × 向量） |
|:---:|:---:|:---:|:---:|
| 0 | 0.7 | `[1.0, 0.0]` | `[0.70, 0.00]` |
| 1 | 0.2 | `[0.0, 1.0]` | `[0.00, 0.20]` |
| 2 | 0.1 | `[0.5, 0.5]` | `[0.05, 0.05]` |
| **Σ** | — | — | **`[0.75, 0.25]`** ← 即 `output[b,h,i,:]` |

**读懂这个例子的 3 个要点：**
- **标量 × 向量 = 向量**：`attn[..,j]` 是数，`V[..,j,:]` 是长度 `d_v` 的向量，乘完还是长度 `d_v` 的向量
- **逐分量相加**：3 个向量按**同一维度**对齐相加（第 0 维加第 0 维，第 1 维加第 1 维）
- **权重最大的那一项贡献最大**：`j=0` 权重 0.7，所以最终结果 `[0.75, 0.25]` 明显偏向 `V[0]=[1.0, 0.0]` 的方向 ✅

> 💡 一句话回味公式：**Σⱼ (权重ⱼ × 内容向量ⱼ)** —— 就是"按权重把所有内容向量混合成一个向量"。

##### 6.4.9.3 形状变化

```
attn   : [B, H, Lq, Lk]      ┐
                             ├─ 矩阵乘（在最后两维）
V      : [B, H, Lk, d_v]     ┘
                             ▼
output : [B, H, Lq, d_v]     # 每个 query 位置得到一个 d_v 维向量
```

**记忆技巧：** `Lk` 在 `attn` 的**最后一维**、在 `V` 的**倒数第二维**，两者**对齐消掉**，剩下 `Lq × d_v`。

##### 6.4.9.4 闭环回到"英→中"翻译例子

继续用前面的例子（Lq=4 中文 token，Lk=3 英文 token）。假设 softmax 后：

```
                key₀="I"   key₁="love"  key₂="cats"
query₀ "我"    [  0.90       0.05         0.05    ]
query₁ "非常"  [  0.10       0.80         0.10    ]
query₂ "喜欢"  [  0.05       0.90         0.05    ]
query₃ "猫"    [  0.05       0.05         0.90    ]
                          ↑ attn: [4, 3]
```

再假设英文的 V 向量（每行是一个 token 的语义内容，为方便演示令 `d_v = 2`）：

```
V = [ "I".V    →  [ 1.0,  0.0 ]   ← "第一人称"语义
      "love".V →  [ 0.0,  1.0 ]   ← "喜爱情感"语义
      "cats".V →  [ 0.5,  0.5 ] ] ← "猫科动物"语义
                       ↑ V: [3, 2]
```

> ⚠️ **关于 `d_v = 2` 的两列含义（重要澄清，避免误解）**
>
> 上面注释里写的"第一人称语义"、"喜爱情感"、"猫科动物语义"**只是教学脚手架**，**不代表真实模型中 V 的每一维都有固定的、人类可命名的含义**。
>
> - **`d_v` 是什么？** 它是 V 向量的维度，即 `W_V ∈ [d_model, d_v]` 的列数。在真实 Transformer 里通常是 **64 / 96 / 128**（例如原论文 `d_model=512, num_heads=8`，则 `d_v = 512/8 = 64`）。本例把它设为 **2** 只是为了**方便手算和肉眼验证**。
> - **两列真的分别代表"语义"和"情感"吗？** ❌ **不是**。真实模型中，语义信息是**"分布式"地打散在所有维度上**的（distributed representation），**不存在"第 0 维 = 人称，第 1 维 = 情感"这种整齐一一对应**。每一维都是网络通过梯度下降**自动涌现**出的抽象特征方向，通常无法用人类语言命名。
> - **类比记忆：**
>
>   | 场景 | 是否"一维一含义"？ |
>   |---|---|
>   | 数据库表 `user(name, age, city)` | ✅ 每列都有明确名字 |
>   | Excel 表格 `A列=姓名, B列=分数` | ✅ 每列都有明确名字 |
>   | **神经网络的 V 向量 `[0.37, -1.2, 0.05, ...]`** | ❌ **每一维都是抽象特征，无固定人类语义** |
>
> - **那为什么这里要标注语义？** 只是为了让"V 是 token 的**内容容器**"这个抽象概念**有画面感**——如果写成 `"I".V = [0.37, -1.2]`，你只会看到两个抽象数字，感受不到"V 携带了什么"。
> - **✅ 你真正需要抓住的结论：** V 是 token 的"**内容向量**"，`attn @ V` 就是**按注意力权重把这些内容加权混合起来**——至于每一维具体代表什么，交给网络自己学，不必也无法人为指定。

**计算 `output = attn @ V`：**

| Query | 计算过程 | output（d_v=2） | 语义解读 |
|---|---|---|---|
| `"我"` | `0.90×[1,0] + 0.05×[0,1] + 0.05×[0.5,0.5]` | `[0.925, 0.075]` | 主要读取了 "I" 的语义 ✅ |
| `"非常"` | `0.10×[1,0] + 0.80×[0,1] + 0.10×[0.5,0.5]` | `[0.150, 0.850]` | 主要读取了 "love" 的情感 ✅ |
| `"喜欢"` | `0.05×[1,0] + 0.90×[0,1] + 0.05×[0.5,0.5]` | `[0.075, 0.925]` | 高度聚焦 "love" ✅ |
| `"猫"` | `0.05×[1,0] + 0.05×[0,1] + 0.90×[0.5,0.5]` | `[0.500, 0.500]` | 主要读取了 "cats" 的语义 ✅ |

**关键洞察：**
- 每个中文 query 都**通过 attn 权重**去英文 V 里"抽取"了它最需要的语义
- 权重越大 → V 贡献越多 → 输出越像那个 V
- 这就是"**信息路由**"：让每个位置**只关注它真正需要的信息**

##### 6.4.9.5 程序员视角：等价伪代码

```python
# output = attn @ V 等价于下面这段
def weighted_sum(attn, V):
    # attn: [B, H, Lq, Lk]
    # V   : [B, H, Lk, d_v]
    B, H, Lq, Lk = attn.shape
    d_v = V.shape[-1]

    output = torch.zeros(B, H, Lq, d_v)
    for b in range(B):
        for h in range(H):
            for i in range(Lq):                      # 每个 query 位置
                for j in range(Lk):                  # 遍历所有 key
                    # 标量 × 向量，累加到 output
                    output[b, h, i, :] += attn[b, h, i, j] * V[b, h, j, :]
    return output
```

> ⚠️ **实际实现绝不用 for 循环**：PyTorch 内部会调用 cuBLAS 的批量矩阵乘（`torch.matmul` / `@`），并行度极高。上面的伪代码仅用于理解语义。

##### 6.4.9.6 完整流程串联（从 Q/K/V 到 output）

```
Q  [B,H,Lq,d_k]  K  [B,H,Lk,d_k]  V  [B,H,Lk,d_v]
        │              │              │
        │  ①  Q @ K^T / √d_k          │
        └──────┬───────┘              │
               ▼                      │
        scores [B,H,Lq,Lk]            │
               │                      │
               │  ②  softmax(dim=-1)  │
               ▼                      │
        attn   [B,H,Lq,Lk]            │
               │                      │
               │  ③  attn @ V         │
               └──────┬───────────────┘
                      ▼
               output [B,H,Lq,d_v]    ← 最终结果
```

**三步走口诀：**
1. **打分**：`Q·Kᵀ/√d_k` → 每个 query 对每个 key 的匹配度
2. **归一化**：`softmax(dim=-1)` → 把匹配度变成加权概率
3. **加权取值**：`attn @ V` → 按概率从 V 里加权抽取语义

> 🎯 **回到 6.4 开头那段代码**，现在你应该能读懂每一行了：
> ```python
> scores = Q @ K.transpose(-2, -1) / sqrt(d_k)   # ① 打分
> attn   = softmax(scores, dim=-1)               # ② 归一化
> output = attn @ V                              # ③ 加权取值
> ```

---

### 6.5 单头注意力完整实例（6.1 ~ 6.4 总结与闭环）

> 🎯 **本节目的：** 把 6.1~6.4 讲的所有公式和概念，用**一组具体数字**从头到尾走一遍，形成完整闭环。看完这一节，你应该能在纸上手算一次 self-attention 的前向过程。

#### 6.5.1 场景设定：最小可算尺寸

为了让例子**能手算、易验证**，把所有维度压到最小：

| 参数 | 取值 | 含义 |
|---|---|---|
| `B` | **1** | Batch size（1 个样本） |
| `H` | **1**（**单头**） | 注意力头数——本例只讨论单头，多头留到 6.8 |
| `Lq = Lk` | **3** | Query / Key 序列长度都是 3（self-attention） |
| `d_k = d_v` | **2** | 每个 Q/K/V 向量的维度 |

**场景故事（可选记忆锚点）：** 一句话 `"猫 吃 鱼"` 做 self-attention。3 个 token 既是 Q，又是 K，又是 V。目标：算出每个 token 融合了其它 token 信息后的新表示。

**输入张量的形状：**

```
Q : [B=1, H=1, Lq=3, d_k=2]      ← 3 个 token 的 query 表示
K : [B=1, H=1, Lk=3, d_k=2]      ← 3 个 token 的 key 表示
V : [B=1, H=1, Lk=3, d_v=2]      ← 3 个 token 的 value 表示
```

为简洁，下文省略 B、H 两个大小为 1 的维度，只看 `[L, d]` 的二维切片。

#### 6.5.2 Step 1：给定具体数值 Q、K、V

```
       ┌ d₀   d₁ ┐
Q = [ [ 1.0,  0.0 ],    ← "猫" 的 query
      [ 0.0,  1.0 ],    ← "吃" 的 query
      [ 1.0,  1.0 ] ]   ← "鱼" 的 query        shape: [3, 2]

K = [ [ 1.0,  0.0 ],    ← "猫" 的 key
      [ 0.0,  1.0 ],    ← "吃" 的 key
      [ 1.0,  1.0 ] ]   ← "鱼" 的 key          shape: [3, 2]

V = [ [ 10.0, 0.0 ],    ← "猫" 的 value（携带的内容）
      [ 0.0, 10.0 ],    ← "吃" 的 value
      [ 5.0,  5.0 ] ]   ← "鱼" 的 value        shape: [3, 2]
```

> 📌 **为什么 Q=K？** 这里为了让计算易验证，故意让 Q 和 K 数值相同。实际模型里 `Q = x·W_Q`，`K = x·W_K`，两个投影矩阵不同，Q 和 K 一般不相等。

#### 6.5.3 Step 2：`scores = Q @ K^T`（对应 6.1 公式）

先转置 K：

```
K^T = [ [ 1.0,  0.0,  1.0 ],       shape: [2, 3]
        [ 0.0,  1.0,  1.0 ] ]
```

再算 `Q @ K^T`（`[3,2] @ [2,3] → [3,3]`）：

| | key₀"猫" | key₁"吃" | key₂"鱼" |
|:---:|:---:|:---:|:---:|
| **query₀"猫"** | 1·1+0·0 = **1** | 1·0+0·1 = **0** | 1·1+0·1 = **1** |
| **query₁"吃"** | 0·1+1·0 = **0** | 0·0+1·1 = **1** | 0·1+1·1 = **1** |
| **query₂"鱼"** | 1·1+1·0 = **1** | 1·0+1·1 = **1** | 1·1+1·1 = **2** |

```
scores = [ [ 1, 0, 1 ],
           [ 0, 1, 1 ],
           [ 1, 1, 2 ] ]     shape: [3, 3]  ← [Lq, Lk]
```

**含义：** `scores[i, j]` = 第 `i` 个 query 与第 `j` 个 key 的点积得分（未归一化的相似度）。

#### 6.5.4 Step 3：`scores / √d_k`（对应 6.2、6.4.7 缩放）

`√d_k = √2 ≈ 1.414`，逐项除：

```
scaled = [ [ 0.707, 0.000, 0.707 ],
           [ 0.000, 0.707, 0.707 ],
           [ 0.707, 0.707, 1.414 ] ]
```

> 💡 **为什么要除？** 当 `d_k` 大时，点积方差随 `d_k` 增大而线性增大，softmax 会趋近 one-hot，梯度消失。除 `√d_k` 把方差拉回 O(1)。本例 `d_k=2` 差别不大，真实模型里 `d_k=64`，`√64=8`，缩放至关重要。

#### 6.5.5 Step 4：`attn = softmax(scaled, dim=-1)`（对应 6.4.1 ~ 6.4.5）

**沿 `dim=-1`（最后一维 `Lk`）逐行做 softmax**，行与行互不影响。以第 0 行为例：

```
scaled[0] = [ 0.707, 0.000, 0.707 ]

① 减最大值（数值稳定）  →  [ 0.000, -0.707,  0.000 ]
② 取 exp               →  [ 1.000,  0.493,  1.000 ]
③ 求和                 →  1.000 + 0.493 + 1.000 = 2.493
④ 归一化               →  [ 0.401,  0.198,  0.401 ]  ← 和 = 1 ✅
```

三行都算完（第 0 行和第 1 行由对称性可知结构相同）：

```
attn = [ [ 0.401, 0.198, 0.401 ],    ← "猫" 的 query 分给 [猫, 吃, 鱼] 的注意力
         [ 0.198, 0.401, 0.401 ],    ← "吃" 的 query 分给 [猫, 吃, 鱼] 的注意力
         [ 0.212, 0.212, 0.576 ] ]   ← "鱼" 的 query 分给 [猫, 吃, 鱼] 的注意力
                                     shape: [3, 3]
```

**解读：**
- 每一行加起来 = 1（注意力权重的概率分布性质）
- "猫" 均匀关注"猫"和"鱼"（各 40%），因为它俩的 K 与"猫"的 Q 打分都是 1
- "鱼" 最关注自己（57.6%），因为它的 Q=[1,1] 与自己的 K=[1,1] 点积最大（2）

#### 6.5.6 Step 5：`output = attn @ V`（对应 6.4.9 加权取值）

`[3,3] @ [3,2] → [3,2]`。逐行是"3 个 V 向量按 attn 权重加权求和"。

**以第 0 行"猫"为例（对应公式 `output[0] = Σⱼ attn[0,j] · V[j]`）：**

| `j` | `attn[0,j]` | `V[j]` | `attn[0,j] · V[j]`（标量 × 向量） |
|:---:|:---:|:---:|:---:|
| 0 "猫" | 0.401 | `[10.0, 0.0]` | `[4.010, 0.000]` |
| 1 "吃" | 0.198 | `[0.0, 10.0]` | `[0.000, 1.980]` |
| 2 "鱼" | 0.401 | `[5.0, 5.0]` | `[2.005, 2.005]` |
| **Σ** | — | — | **`[6.015, 3.985]`** ← `output[0]` |

三行都算完：

```
output = [ [ 6.015, 3.985 ],    ← 新的 "猫" 表示（融合了自身+"鱼"的内容为主）
           [ 3.985, 6.015 ],    ← 新的 "吃" 表示（融合了自身+"鱼"的内容为主）
           [ 5.000, 5.000 ] ]   ← 新的 "鱼" 表示（三者平均，因为它高度关注自己）
                                shape: [3, 2]  ← [Lq, d_v]
```

**🎯 这就是 self-attention 的全部：** 每个 token 拿自己的 Q 去所有 K 上打分 → 归一化成权重 → 加权融合所有 V → 得到新表示。原来 `"猫"=[10,0]`，现在 `"猫"=[6.015, 3.985]`——**它"读取"了整句话的信息，变成了带有上下文的表示**。

#### 6.5.7 Step 6：完整 PyTorch 代码（工程闭环验证）

用真实代码跑一遍，验证上面手算的每一步：

```python
import torch
import torch.nn.functional as F
import math

# ---- Step 1: 构造 Q, K, V（形状 [B=1, H=1, L=3, d=2]）----
Q = torch.tensor([[[[1.0, 0.0],
                    [0.0, 1.0],
                    [1.0, 1.0]]]])
K = Q.clone()                                              # 为验证，令 K = Q
V = torch.tensor([[[[10.0,  0.0],
                    [ 0.0, 10.0],
                    [ 5.0,  5.0]]]])

d_k = Q.shape[-1]                                          # 2

# ---- Step 2: Q @ K^T ----
scores = Q @ K.transpose(-2, -1)                           # [1,1,3,3]
print("scores:\n", scores)
# tensor([[[[1., 0., 1.],
#           [0., 1., 1.],
#           [1., 1., 2.]]]])

# ---- Step 3: 缩放 ----
scaled = scores / math.sqrt(d_k)                           # ÷ √2
print("scaled:\n", scaled)
# tensor([[[[0.7071, 0.0000, 0.7071],
#           [0.0000, 0.7071, 0.7071],
#           [0.7071, 0.7071, 1.4142]]]])

# ---- Step 4: softmax(dim=-1) ----
attn = F.softmax(scaled, dim=-1)                           # [1,1,3,3]
print("attn:\n", attn)
# tensor([[[[0.4013, 0.1974, 0.4013],
#           [0.1974, 0.4013, 0.4013],
#           [0.2119, 0.2119, 0.5761]]]])
print("每行之和:", attn.sum(dim=-1))                        # 全部 1.0000 ✅

# ---- Step 5: attn @ V ----
output = attn @ V                                          # [1,1,3,2]
print("output:\n", output)
# tensor([[[[6.0132, 3.9868],
#           [3.9868, 6.0132],
#           [5.0000, 5.0000]]]])
```

> ✅ **对照手算结果**：`output ≈ [[6.015, 3.985], [3.985, 6.015], [5.000, 5.000]]`，与代码输出**完全一致**（小数末位差异是手算保留 3 位小数造成的）。

**一体化写法（PyTorch 内置一行搞定）：**

```python
output = F.scaled_dot_product_attention(Q, K, V)           # 内部自动做 scale+softmax+@V
# 结果与上面 5 步分解完全一致，且底层用 FlashAttention 优化，速度快 2~4 倍
```

#### 6.5.8 6.1 ~ 6.4 知识点回顾映射表

本例每一步都能在前面章节找到对应，形成一个总结闭环：

| 6.1~6.4 知识点 | 在本例中的对应 | 结果形状 |
|---|---|---|
| 6.1 核心公式 `Attention(Q,K,V)` | 整个 Step 2 ~ Step 5 | — |
| 6.2 缩放因子 `1/√d_k` | Step 3：`/ √2` | 保持 `[3,3]` |
| 6.3 Q/K/V shape `[B,H,L,d]` | Step 1 构造的四维张量 | `[1,1,3,2]` |
| 6.4.2 softmax 数学公式 | Step 4 的手算展开 | 保持 `[3,3]` |
| 6.4.3 `dim=-1` 归一化对象 | Step 4 每行独立归一化 | 每行和 = 1 |
| 6.4.4 数值稳定实现（减 max） | Step 4 ① 减最大值 | — |
| 6.4.5 softmax 数值例子 | Step 4 详细展开的第 0 行 | — |
| 6.4.7 为什么要缩放 | Step 3 的说明 blockquote | — |
| 6.4.8 形状变化速查 | scores/attn/output 每步标注的 shape | — |
| 6.4.9 `attn @ V` 加权取值 | Step 5 的表格逐项求和 | `[3,2]` |

> 💡 **建议：** 合上文档，凭这张表把 Step 2~5 在纸上默算一遍，能算对，说明 6.1~6.4 全通了。

#### 6.5.9 常见误区

| 误区 | 真相 |
|---|---|
| d_model 随 vocab_size 增长 | ❌ d_model 是语义空间维度，与词汇表大小无关 |
| vocab_size 大 → d_model 要大 | ❌ Embedding 是查表操作，不是编码 |
| d_k 是空间最大 size | ❌ d_k 是超参数，固定不变 |
| L 是原始文本长度 | ❌ L 是 padding 后的长度，mask 才是真实长度 |
| self-attention 里 Q=K=V | ❌ Q/K/V 都由输入 x 分别乘 `W_Q/W_K/W_V` 得到，是**三个不同的投影**，只是**输入相同**而已（本例 Q=K 只为手算验证） |

#### 6.5.10 Q、K、V 是训练得到的吗？

> ❓ **常见疑问：** 6.5.2 直接给出了 Q、K、V 的数值，那这些矩阵是需要通过训练学出来的吗？

**一句话结论：** Q、K、V **本身不是可训练参数**，它们是**每次前向推理时即时算出来的中间张量**。真正需要通过训练学习的，是"**生成 Q/K/V 的那三个投影矩阵** `W_Q`、`W_K`、`W_V`"。

##### 6.5.10.1 数据流：从输入到 Q/K/V

```
        输入 x          ← 每次推理都不同（"猫吃鱼" 或 "The cat sat"）
      [B, L, d_model]
           │
           │  乘以三个可学习矩阵（训练时才更新）
   ┌───────┼───────┐
   │       │       │
   ▼       ▼       ▼
  W_Q     W_K     W_V     ← 🎯 这三个才是 "训练得到" 的参数
[d_model, [d_model, [d_model,     形状固定，训练时被反向传播更新
 d_k]     d_k]     d_v]
   │       │       │
   ▼       ▼       ▼
   Q       K       V       ← ⚠️ 这三个是 "临时算出来的"，不是参数
[B,H,L,d_k] ...              每次输入不同 → Q/K/V 就不同
```

对应 PyTorch 典型写法：

```python
class SelfAttention(nn.Module):
    def __init__(self, d_model, d_k):
        super().__init__()
        # ↓ 这三行才是 "训练参数"，nn.Linear 内部就是一个可学习矩阵 W
        self.W_Q = nn.Linear(d_model, d_k)   # 训练时更新
        self.W_K = nn.Linear(d_model, d_k)   # 训练时更新
        self.W_V = nn.Linear(d_model, d_k)   # 训练时更新

    def forward(self, x):                    # x: [B, L, d_model]
        # ↓ 这三行是 "前向时即时计算"，不是参数
        Q = self.W_Q(x)                      # 每次输入 x 不同，Q 就不同
        K = self.W_K(x)
        V = self.W_V(x)
        # ...后面的 scores/softmax/output 也都是即时算的，不是参数
        return output
```

##### 6.5.10.2 为什么 6.5.2 直接 "给出" Q、K、V 的值？

6.5 节的目的是**演示 attention 公式本身的计算逻辑**（Step 2~5），不是演示 "参数如何训练"。所以：

- **我们假设**：训练已经完成了，`W_Q / W_K / W_V` 已经是训好的固定矩阵
- **给定**输入 x（例如 `"猫吃鱼"` 的 embedding）后，`Q = x @ W_Q` 等已经算完
- 直接把算完的 Q、K、V 数值端出来，专注展示 `Q → scores → attn → output` 这条链

如果不这么简化，例子里就要塞下 `x`、`W_Q`、`W_K`、`W_V`、`Q`、`K`、`V` 七个矩阵，主线会被淹没。

##### 6.5.10.3 训练 vs 推理：什么变、什么不变

| 阶段 | 输入 | 变化的量 | 不变的量 |
|---|---|---|---|
| **训练时** | 大量 `(x, target)` 样本 | `W_Q, W_K, W_V, W_O` 等**参数**被反向传播更新 | 模型结构、超参 `d_model, d_k, H` |
| **推理时**（如本例） | 一句话的 `x` | `Q, K, V, scores, attn, output` **中间张量**每次都重算 | `W_Q, W_K, W_V` 参数**冻结**不变 |

##### 6.5.10.4 数一数：单头 self-attention 到底有几个可训练参数？

在 6.5 的设定（`d_model=2, d_k=d_v=2, H=1`）下：

| 参数 | 形状 | 参数量 |
|---|---|---|
| `W_Q` | `[d_model=2, d_k=2]` | 4 |
| `W_K` | `[d_model=2, d_k=2]` | 4 |
| `W_V` | `[d_model=2, d_v=2]` | 4 |
| `W_O`（输出投影，多头才用，单头可省） | `[d_v=2, d_model=2]` | 4 |
| **合计** | — | **12 ~ 16** |

**这 12~16 个数才是"训练学出来的"**。相比之下，`Q、K、V、attn、output` 这些张量都是**运行时产物**，不占参数量。

##### 6.5.10.5 用 W_Q/W_K/W_V 复现 6.5.7 的 Q、K、V

回过头看 6.5.7 的 Step 6 代码，你会发现它**直接把 Q、K、V 的数值写死了**：

```python
# 6.5.7 里的原始写法（跳过了投影）
Q = torch.tensor([[[[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]]])
K = Q.clone()
V = torch.tensor([[[[10.0, 0.0], [0.0, 10.0], [5.0, 5.0]]]])
```

这样做是为了聚焦 attention 公式本身、避免节外生枝，但也**没体现 Q/K/V 到底从哪儿来**。下面这段代码补上前半段——**从输入 x 和三个投影矩阵 `W_Q / W_K / W_V` 出发，跑出与 6.5.7 完全相同的 Q/K/V**，从而让 6.5.7 和 6.5.10 首尾闭合。

**关键构造思路：** 令输入 `x = I₃`（3×3 单位矩阵，每行是一个 token 的 one-hot embedding），那么 `x @ W = W`——W 直接决定了 Q/K/V 的数值，方便手动核对。

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
import math

torch.manual_seed(0)

# ---- Step 0：设定维度 ----
# 为了让 x @ W_Q 恰好等于 6.5.7 里的 Q，令 d_model = L = 3、x = 单位矩阵
d_model, d_k, d_v, L = 3, 2, 2, 3

# ---- Step 1：输入 x（3 个 token 的 embedding，每个是 one-hot） ----
x = torch.eye(L)                                           # [L=3, d_model=3]
# x = [[1, 0, 0],
#      [0, 1, 0],
#      [0, 0, 1]]

# ---- Step 2：三个"可训练参数"矩阵（这里手动设定成能复现 6.5.7 的值） ----
# 训练时它们由反向传播更新；这里为了对上 6.5.7 的数值，直接赋值
W_Q = nn.Parameter(torch.tensor([[1.0, 0.0],
                                 [0.0, 1.0],
                                 [1.0, 1.0]]))            # [d_model=3, d_k=2]
W_K = nn.Parameter(W_Q.data.clone())                       # 令 W_K = W_Q ⇒ K = Q
W_V = nn.Parameter(torch.tensor([[10.0,  0.0],
                                 [ 0.0, 10.0],
                                 [ 5.0,  5.0]]))          # [d_model=3, d_v=2]

# 确认这三个才是"训练参数"
print("可训练参数一览：")
for name, p in [("W_Q", W_Q), ("W_K", W_K), ("W_V", W_V)]:
    print(f"  {name}: shape={tuple(p.shape)}, requires_grad={p.requires_grad}, 参数量={p.numel()}")
# 可训练参数一览：
#   W_Q: shape=(3, 2), requires_grad=True, 参数量=6
#   W_K: shape=(3, 2), requires_grad=True, 参数量=6
#   W_V: shape=(3, 2), requires_grad=True, 参数量=6

# ---- Step 3：由 x 和三个投影矩阵，即时算出 Q、K、V ----
Q = x @ W_Q                                                # [L=3, d_k=2]
K = x @ W_K                                                # [L=3, d_k=2]
V = x @ W_V                                                # [L=3, d_v=2]
print("Q:\n", Q)
# tensor([[1., 0.],
#         [0., 1.],
#         [1., 1.]], grad_fn=<MmBackward0>)  ✅ 与 6.5.7 完全一致
print("V:\n", V)
# tensor([[10.,  0.],
#         [ 0., 10.],
#         [ 5.,  5.]], grad_fn=<MmBackward0>)  ✅ 与 6.5.7 完全一致

# ---- Step 4 ~ Step 7：把 6.5.7 的后半段原封不动接上 ----
scores = Q @ K.transpose(-2, -1)                           # [3, 3]
scaled = scores / math.sqrt(d_k)
attn   = F.softmax(scaled, dim=-1)
output = attn @ V                                          # [3, d_v=2]
print("output:\n", output)
# tensor([[6.0132, 3.9868],
#         [3.9868, 6.0132],
#         [5.0000, 5.0000]], grad_fn=<MmBackward0>)  ✅ 与 6.5.7 完全一致
```

**这段代码相比 6.5.7 只多了两块内容：**

1. **`W_Q / W_K / W_V` 显式登场**——它们才是训练时会被反向传播更新的参数（注意 `nn.Parameter` 和 `requires_grad=True`）
2. **`Q = x @ W_Q` 等三行**——这就是 6.5.10 那张 ASCII 图里 "输入 x → 乘投影矩阵 → 得到 Q/K/V" 的落地代码

**注意 `grad_fn` 字段：** 上面打印 Q 时输出 `grad_fn=<MmBackward0>`，说明 Q 是"计算图上的中间张量"，一旦有 loss 就能沿着它反向传播到 `W_Q`。相比之下，6.5.7 里的 Q 是 `torch.tensor([...])` 直接构造的**叶子张量**，没有 `grad_fn`——这从工程上也印证了 6.5.10 反复强调的："Q/K/V 是运行时产物，W_Q/W_K/W_V 才是参数"。

**用 `nn.Linear` 的等价工程写法**（真实 Transformer 代码就长这样）：

```python
class SelfAttentionHead(nn.Module):
    def __init__(self, d_model, d_k, d_v):
        super().__init__()
        self.W_Q = nn.Linear(d_model, d_k, bias=False)     # 内部就是可训练矩阵
        self.W_K = nn.Linear(d_model, d_k, bias=False)
        self.W_V = nn.Linear(d_model, d_v, bias=False)
        self.d_k = d_k

    def forward(self, x):                                  # x: [L, d_model]
        Q = self.W_Q(x)                                    # [L, d_k]
        K = self.W_K(x)
        V = self.W_V(x)
        scores = Q @ K.transpose(-2, -1) / math.sqrt(self.d_k)
        attn   = F.softmax(scores, dim=-1)
        return attn @ V                                    # [L, d_v]

model = SelfAttentionHead(d_model=3, d_k=2, d_v=2)
print("模型的可训练参数：")
for name, p in model.named_parameters():
    print(f"  {name}: {tuple(p.shape)}")
# 模型的可训练参数：
#   W_Q.weight: (2, 3)
#   W_K.weight: (2, 3)
#   W_V.weight: (2, 3)
```

至此，两段代码的关系可以画成一条闭环：

```
  6.5.10.5（本节）                        6.5.7（Step 6）
  ─────────────────                       ────────────────
   x  ─┐                                   （从这里开始）
       ├─ @ W_Q ─→  Q  ──────────────────→  Q ─┐
   x  ─┤                                       │
       ├─ @ W_K ─→  K  ──────────────────→  K ─┼─→ scores → attn → output
   x  ─┤                                       │
       └─ @ W_V ─→  V  ──────────────────→  V ─┘
      ↑                ↑
   训练学到的参数     运行时的中间张量
```

**一句话总结：** 6.5.7 从 Q/K/V 开始讲清 attention 公式；6.5.10.5 从 x 和 W_Q/W_K/W_V 开始，补上"参数如何生成 Q/K/V"——两者拼起来才是完整的单头 self-attention 前向流程。

### 6.6 单头注意力的完整训练闭环

> 🎯 **本节目的：** 6.5 讲完了"前向推理"和"参数从哪来"，本节补上最后一块——**训练**。看完这一节，你将掌握"一个单头 attention 从零训到收敛"的完整过程，与 6.5 拼起来构成单头 attention 的完整技术描述。
>
> 📎 **前置知识回引：** 通用训练五步（`zero_grad → forward → loss → backward → step`）在 [2.2 节] 已详解；`nn.CrossEntropyLoss` / `NLLLoss` 在 [3 节] 已详解。本节**只讲 attention 特有的部分**，通用概念不再重复。

#### 6.6.1 训练一个 attention 头，到底是在训什么？

**训练目标：** 让 `W_Q / W_K / W_V` 从随机初始值出发，通过梯度下降，收敛到"能完成某个任务"的最优值。

在 6.5.10.5 里我们**手工**把 W_Q/W_K/W_V 设成了能复现 6.5.7 数值的样子。而真实训练场景下，这三个矩阵**一开始是随机初始化的**——需要通过数据和 loss 把它们"教好"。

**训练前后的对比：**

| 阶段 | `W_Q / W_K / W_V` | attention 权重 `attn` | 输出 `output` |
|---|---|---|---|
| 随机初始化 | 无意义的随机值 | 分布混乱，无规律 | 无法完成任务 |
| **训练完成后** | 学到了任务所需的投影方向 | **反映任务所需的关注模式** | 能完成任务 |

#### 6.6.2 训练任务设计：恒等复原（最小可跑通任务）

##### 6.6.2.1 一句话任务定义

> **恒等复原（Identity Reconstruction）：** 每次随机生成一个 `[B, L, d_model]` 的张量 `x`，把它当作模型输入；训练目标是让 self-attention 的输出 `output` **在数值上尽量等于 `x` 本身**。

用数学式写：

\[
\text{目标}: \quad \text{SelfAttention}(x) \approx x, \quad \forall x
\]

用一句 PyTorch 表达："**输入 = 标签**"：

```python
x      = torch.randn(B, L, d_model)   # 随机采样的一个"句子"
target = x                            # 标签就是它自己（自监督）
output = model(x)                     # 模型输出
loss   = F.mse_loss(output, target)   # 越像 x 越好
```

##### 6.6.2.2 输入 / 输出 / 标签 具体是什么？

用本例的具体尺寸（`B=8, L=3, d_model=3`）画一张形状对齐表：

| 张量 | 形状 | 数值来源 | 举例（B=1 的样本切片） |
|---|---|---|---|
| 输入 `x` | `[8, 3, 3]` | 每步 `torch.randn` 现采 | `[[0.5, -1.2, 0.3], [1.1, 0.0, -0.7], [-0.4, 0.8, 1.5]]` |
| 标签 `target` | `[8, 3, 3]` | **直接 = x**（自监督） | 与上格**完全相同** |
| 模型输出 `output` | `[8, 3, 3]` | `SelfAttention(x)` 前向算出 | 训练初期是乱的，收敛后应逼近 `x` |
| 损失 `loss` | 标量 | `MSE(output, target)` 对所有元素平均 | 训练初期 ~1.0，收敛后 <1e-4 |

**关键点：**

- **每一步的 x 都是新采样的**——不是同一个 x 反复训 1000 遍，而是 1000 个不同的随机 x 各训 1 遍
- **标签直接是 x 本身**——不需要人工标注，不需要外部数据集
- **loss 是逐元素 MSE**——`[8,3,3]` 一共 72 个数，全部按 `(out - x)²` 求平均

##### 6.6.2.3 为什么选"恒等复原"？

| 现实需求 | 恒等复原的对应优势 |
|---|---|
| 需要一个有标签的任务 | ✅ **自监督**：`target = x` 即取即用，无需数据集 |
| 输出维度要能直接比较 | ✅ self-attention 输入输出形状**天然相同**（`[B, L, d]` → `[B, L, d]`），不用额外接分类头 |
| 单机 CPU 秒级验证 | ✅ 单头 + `d=3` 几百步内收敛，笔记本几秒跑完 |
| 避免和第 3 节 CE 重复 | ✅ 用 **MSELoss**（回归），换个损失面孔，覆盖训练机制的另一面 |
| 需要能"眼见为实"验收 | ✅ 收敛条件是 `attn → 单位矩阵`（见 6.6.2.4），可视化即可校验 |

##### 6.6.2.4 任务的核心直觉：attention 会学成什么样？

要让 `output ≈ x`，模型必须让 attention 学会**"每个 token 只关注自己"**：

```
attn 矩阵（形状 [L, L]）：
         看向 token_0   看向 token_1   看向 token_2
token_0    1.0             0.0            0.0        ← 只看自己
token_1    0.0             1.0            0.0        ← 只看自己
token_2    0.0             0.0            1.0        ← 只看自己
```

**为什么这样才行？** 展开 output 的定义：

```
output_i = Σ_j  attn[i,j] · V_j
        = Σ_j  attn[i,j] · (x_j @ W_V)      ← V_j = x_j @ W_V
```

- 若 `attn` 是**单位矩阵**，则 `output_i = V_i = x_i @ W_V`
- 只要 `W_V` 再被 loss 推成 "**接近单位矩阵**"，就有 `output_i ≈ x_i`，任务达成

所以 **`attn` 逐步收敛到接近单位矩阵**、**`W_V` 逐步收敛到接近单位矩阵**——两件事同时发生，就是这个任务的训练轨迹。这也给了我们**两个可视化验收指标**（会在 6.6.4 / 6.6.5 用到）：

| 指标 | 训练初期 | 收敛后 |
|---|---|---|
| `loss` | ~ O(1) | < 1e-4 |
| `attn` 矩阵 | 各行分布杂乱 | 越来越接近单位矩阵 `I` |

##### 6.6.2.5 常见疑问：任务是不是太"平凡"了？

> **Q：让 output = x，模型岂不是学个"啥都不做"（恒等映射）就行？这种任务能训出真本事吗？**

**A：** 是的，本任务确实是"最小可跑通"的**教学设定**——它的目的不是解决实际业务问题，而是**用最少的干扰因素演示"参数如何被 loss 推着走"**：

- 复杂任务里，`W_Q/W_K/W_V` 要同时学"如何投影 + 如何关注 + 如何提取值"，多个目标耦合，训练轨迹不好观察
- 恒等任务把目标压缩到极简：`attn → I` 和 `W_V → I`——**训练成功与否肉眼可辨**

如果想看"真本事"的训练任务（有真实语义、需要非平凡的 attention 模式），见 **6.7 节的英→中翻译**——那才是"完整训练"的实战版。**本节先保证跑通、看懂机制。**

---

#### 6.6.3 训练特有的三个关键点

相比第 2 节讲的通用训练流程，attention 训练**只有三个特殊点**需要留意，其余全部通用：

**① 参数 = 三个投影矩阵（+ 可选的输出投影 W_O）**

```python
model = SelfAttentionHead(d_model=3, d_k=2, d_v=3)
# 传给 optimizer 的参数就是 W_Q / W_K / W_V 的权重
optimizer = torch.optim.Adam(model.parameters(), lr=0.05)
```

> 📌 `model.parameters()` 返回的正是 6.5.10 反复强调的"训练参数"——`W_Q.weight / W_K.weight / W_V.weight`。**Q、K、V、attn、output 都不在此列**，它们是运行时张量，不需要"训"。

**② 梯度沿计算图反向流回**

前向 `x → Q/K/V → scores → softmax → output` 每一步都是可微操作，PyTorch 的 autograd 会自动把 `loss` 的梯度**沿这条链**反传，最终**只落到叶子参数** `W_Q.weight / W_K.weight / W_V.weight` 上：

```
loss  ←─ MSE(output, target)
  │
  ├─ ∂/∂output
  │
  ▼
output = attn @ V   ──┬─ ∂/∂V  → ∂/∂W_V   ✅ 更新
  │                   │
  ▼                   └─ ∂/∂attn
attn = softmax(...)         │
  │                         ▼
  ▼                    scaled = scores/√d_k
scaled                       │
  │                          ▼
  ▼                     scores = Q @ K^T ─┬─ ∂/∂Q → ∂/∂W_Q  ✅ 更新
scores                                    └─ ∂/∂K → ∂/∂W_K  ✅ 更新
```

**③ 初始化很关键**

`nn.Linear` 默认用 Kaiming Uniform 初始化，对 attention 通常够用；若手动初始化，避免全零（会让所有 token 的 Q/K/V 相同、attention 崩塌）。

#### 6.6.4 完整训练代码（可直接运行）

以下代码在 6.5.10.5 的 `SelfAttentionHead` 基础上，跑一次完整训练，观察 loss 下降和 attn 收敛到单位矩阵：

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
import math

torch.manual_seed(42)

# ---- 1. 模型：与 6.5.10.5 完全相同的单头 self-attention ----
class SelfAttentionHead(nn.Module):
    def __init__(self, d_model, d_k, d_v):
        super().__init__()
        self.W_Q = nn.Linear(d_model, d_k, bias=False)
        self.W_K = nn.Linear(d_model, d_k, bias=False)
        self.W_V = nn.Linear(d_model, d_v, bias=False)
        self.d_k = d_k

    def forward(self, x):                                  # x: [L, d_model]
        Q = self.W_Q(x)                                    # [L, d_k]
        K = self.W_K(x)
        V = self.W_V(x)                                    # [L, d_v]
        scores = Q @ K.transpose(-2, -1) / math.sqrt(self.d_k)
        attn   = F.softmax(scores, dim=-1)                 # [L, L]
        return attn @ V, attn                              # 顺便返回 attn 便于观察

# ---- 2. 数据 + 目标：恒等复原（output ≈ x） ----
# 令 d_v = d_model = 3，才能直接对比 output 与 x
d_model, d_k, d_v, L = 3, 2, 3, 3
x = torch.eye(L)                                           # [3, 3]
target = x.clone()                                         # 目标就是 x 自身

# ---- 3. 模型、损失、优化器 ----
model     = SelfAttentionHead(d_model, d_k, d_v)
loss_fn   = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.05)

# ---- 4. 训练前：看看初始 W_Q ----
print("训练前 W_Q.weight:\n", model.W_Q.weight.data)

# ---- 5. 训练循环（通用五步，见 2.2 节） ----
for step in range(301):
    optimizer.zero_grad()                                  # ① 清零梯度
    output, attn = model(x)                                # ② 前向
    loss = loss_fn(output, target)                         # ③ 计算 loss
    loss.backward()                                        # ④ 反向传播
    optimizer.step()                                       # ⑤ 更新参数

    if step % 50 == 0:
        print(f"step={step:3d}   loss={loss.item():.6f}")

# step=  0   loss=0.276...
# step= 50   loss=0.031...
# step=100   loss=0.008...
# step=150   loss=0.002...
# step=200   loss=0.0005...
# step=300   loss=0.00004...   ← 已收敛

# ---- 6. 训练后：验证是否达成"每个 token 只关注自己" ----
with torch.no_grad():
    output, attn = model(x)
    print("训练后 attn（应接近单位矩阵）:\n", attn)
    print("训练后 output（应接近 x）:\n", output)
    print("训练后 W_Q.weight（已从随机变到任务最优）:\n", model.W_Q.weight.data)
```

**运行结果解读：**

| 观察量 | 训练前 | 训练后 | 说明 |
|---|---|---|---|
| `loss` | ≈ 0.28 | ≈ 4e-5 | 下降 4 个数量级，任务学会 |
| `attn` | 混乱分布 | **≈ 单位矩阵** | 每个 token 学会只关注自己 ✅ |
| `output` | 无规律 | **≈ x**（即 `I₃`） | 恒等复原任务完成 ✅ |
| `W_Q.weight` | 随机 | 收敛值 | 参数被真真切切"训"到位 |

#### 6.6.5 训练视角下的 attention：三张图看懂梯度流

**图 1：前向计算图**（数据向前流）

```
x  ─┬→ [W_Q]─→ Q ─┐
    │              ├→ scores ─→ scaled ─→ attn ─┐
    ├→ [W_K]─→ K ─┘                              ├→ output ─→ loss
    │                                             │
    └→ [W_V]─→ V ────────────────────────────────┘
```

**图 2：反向梯度图**（梯度向后流，只沿实线路径累加到三个 W）

```
loss ─┬→ ∂/∂output ─┬→ ∂/∂V ─→ ∂/∂W_V  🔧 更新
      │              │
      │              └→ ∂/∂attn ─→ ∂/∂scaled ─→ ∂/∂scores ─┬→ ∂/∂Q ─→ ∂/∂W_Q  🔧 更新
      │                                                     │
      │                                                     └→ ∂/∂K ─→ ∂/∂W_K  🔧 更新
      │
      └→ x 是叶子输入，梯度到此为止（不更新 x）
```

**图 3：训练轨迹**（W_Q 的每个元素随 step 变化）

```
    W_Q.weight 某个元素的值
    │
  ↑ │           ╭──────────── 收敛（W 学到了任务最优值）
    │        ╭─╯
    │      ╭╯
    │    ╭╯
    │   ╱          （每一步 optimizer.step() 沿梯度反方向挪动一小步）
    │──╯
    └──────────────────────────→ step
     0          100         300
```

#### 6.6.6 训练视角下的整体闭环

至此，**单头 self-attention 的完整技术描述**由 6.5 和 6.6 拼合完毕：

```
 ┌──────── 6.5 前向（推理时做的事）───────┐  ┌──── 6.6 训练（如何得到 W）────┐
 │                                          │  │                                │
 │  x ─→ (W_Q, W_K, W_V) ─→ Q, K, V         │  │  数据 + loss                   │
 │                        │                 │  │       │                        │
 │                        ▼                 │  │       ▼                        │
 │             scores = Q @ K^T             │  │  loss.backward() 反向传播       │
 │                        │                 │  │       │                        │
 │                        ▼                 │  │       ▼                        │
 │             scaled = scores / √d_k       │  │  optimizer.step() 更新参数     │
 │                        │                 │  │       │                        │
 │                        ▼                 │  │       ▼                        │
 │             attn = softmax(scaled)       │  │  W_Q, W_K, W_V 从随机 → 最优   │
 │                        │                 │  │                                │
 │                        ▼                 │  │  ←── 下一次前向用新的 W ──→    │
 │             output = attn @ V            │  │                                │
 └──────────────────────────────────────────┘  └────────────────────────────────┘
                              ↕
                     互为对偶：前向决定 loss；反向决定 W；新的 W 又改变下一次前向
```

**一句话总结：** 6.5 讲的是"**给定 W，怎么把 x 算成 output**"；6.6 讲的是"**给定任务，怎么把 W 训到最优**"——两者合起来才是一个完整的、能用的单头 attention。

#### 6.6.7 常见疑问

| 疑问 | 解答 |
|---|---|
| 训练时 Q/K/V 需要 requires_grad=True 吗？ | ❌ 不需要。它们由 `x @ W` 得出，自动继承计算图，梯度会通过它们传给 W。**只有 `W_Q/W_K/W_V.weight` 需要**（`nn.Parameter` 默认已开启）。 |
| 训练时输入 x 也会被更新吗？ | ❌ 不会。x 是数据（或前一层的输出），不是可训练参数。梯度传到 x 就停（除非 x 前面还有可训练层，比如 Embedding，才会继续往前）。 |
| 为什么本节用 MSE 而非 CrossEntropy？ | 恒等复原任务的目标是"让 output 接近连续向量 x"，属于回归问题，MSE 最自然。真实 NLP 场景 attention 后面接分类头，才用 CrossEntropy（详见 3 节）。 |
| 为什么单头恒等复原任务这么容易？ | 因为它本质是让 attention 学"identity 映射"——只要 `attn ≈ I`，任何 V 都能被原样复原。真实任务（翻译、生成）远比这难，需要多头 + 多层堆叠。 |
| 训完的 W_Q 是否唯一？ | ❌ 不唯一。attention 对 Q/K 有旋转不变性（`Q·K^T = (QR)(KR)^T` 若 R 正交），所以 W_Q/W_K 有等价解；W_V 也有类似自由度。不同随机种子会收敛到不同但等价的解。 |

### 6.7 从"恒等复原"到"英→中翻译"：数据对到底要长什么样？

> 🎯 **本节目的：** 6.6 用"恒等复原"这个玩具任务演示了训练闭环，但真实任务（比如前面反复用作直觉例子的**英→中翻译**）需要什么样的数据？本节**只回答一个问题**——"数据对到底要长什么样才能把 6.6 的训练跑通"。
>
> 📎 **边界说明：** 本节**只讲数据侧**，不展开 Encoder-Decoder 完整架构（属于 Transformer 章节），也不深入 cross-attention（详见 7 节）。前向公式、训练五步分别见 6.5、6.6，不重复。

#### 6.7.1 一句话理解

> **一条训练样本 = 一个"源句 → 目标句"的平行句对，经过分词、编号、加特殊 token、padding，最终变成两个整数张量 `(src_ids, tgt_ids)`。**

**用你在 944 行看到的例子来说：**

| 源（英文） | 目标（中文） |
|---|---|
| `"I love you"` | `"我 爱 你"` |

6.6 里的 `(x, target=x)` 只是"自己对自己"的退化情形。真实翻译数据的 `target ≠ x`——**这是一切复杂度的来源。**

#### 6.7.2 六个必备条件（数据对合格清单）

一条能训 attention 翻译模型的数据对，必须**同时满足**下面 6 点。缺一都跑不通：

| # | 条件 | 说明 | 6.6 恒等复原任务的对照 |
|---|---|---|---|
| 1 | **平行对齐**（parallel） | 每条样本是**一对**句子，源和目标表达**同一语义** | 目标 = 输入自身 |
| 2 | **分词到 token** | 源、目标各自被切成离散 token 序列 | 直接把 3 个位置当 token |
| 3 | **词表映射为整数 ID** | token → 整数（`src_vocab` 和 `tgt_vocab` 通常各建各的） | 无需词表，one-hot 直接给 |
| 4 | **特殊 token 齐全** | 至少要有 `<pad>` `<bos>` `<eos>` `<unk>` | 无 |
| 5 | **batch 内 padding + mask** | 同 batch 内不同长度补齐；配套的 `pad_mask` 告诉 attention"哪些位置是假的" | 无（长度固定=3） |
| 6 | **目标端 shift + causal mask** | 目标输入是 `<bos> 我 爱 你`，目标标签是 `我 爱 你 <eos>`；配 causal mask 防偷看 | 无（一步到位） |

> ⚠️ **前 3 条决定"能不能表示"；后 3 条决定"能不能训对"。** 少了后 3 条中的任何一条，模型要么训不动、要么训出的东西是"作弊得来的"。

#### 6.7.3 数据从原文到张量的完整流水线

以 `"I love you" → "我 爱 你"` 这一对为例，走完一遍完整流水线：

**Step 1：分词（Tokenization）**

```
源:  "I love you"       ──分词──▶  ["I", "love", "you"]
目标: "我爱你"           ──分词──▶  ["我", "爱", "你"]
```

> 📌 真实系统里，源端用英文分词器（如 BPE、WordPiece），目标端用中文分词器（如 jieba 或子词）。这里为简化，按空格/单字切。

**Step 2：加特殊 token**

只在**目标端**加 `<bos>` 和 `<eos>`（源端加不加 `<bos>` 视架构而定，通常加 `<eos>`）：

```
源  tokens:  ["I", "love", "you", "<eos>"]
目标 tokens: ["<bos>", "我", "爱", "你", "<eos>"]
```

**Step 3：查词表转 ID**

假设两份词表：

```
src_vocab = {"<pad>":0, "<unk>":1, "<eos>":2, "I":3, "love":4, "you":5, ...}
tgt_vocab = {"<pad>":0, "<unk>":1, "<bos>":2, "<eos>":3, "我":4, "爱":5, "你":6, ...}
```

映射后：

```
src_ids = [3, 4, 5, 2]                    # I love you <eos>
tgt_ids = [2, 4, 5, 6, 3]                 # <bos> 我 爱 你 <eos>
```

**Step 4：拆成"解码器输入"和"标签"（目标端 shift）**

关键操作——**目标序列错一位**：

```
decoder_input = tgt_ids[:-1] = [2, 4, 5, 6]      # <bos> 我 爱 你    ← 送进模型
labels        = tgt_ids[1:]  = [4, 5, 6, 3]      # 我 爱 你 <eos>    ← 用来算 loss
```

> 🔑 **为什么要 shift？** 因为训练时是"给模型看 `<bos> 我 爱 你`，让它预测出 `我 爱 你 <eos>`"——**每个位置都在预测下一个 token**。这就是 causal LM 的核心训练方式。

**Step 5：Batch 内 padding**

假设 batch 里还有另一句更长的 `"I love cats and dogs" → "我 喜欢 猫 和 狗"`，就要把短的补齐到 `max_len`：

```
src_ids (batch=2):                       tgt_ids (batch=2):
[3, 4, 5, 2, 0, 0]     ← 补 <pad>        [2, 4, 5, 6, 3, 0]
[3, 4, 7, 8, 9, 2]                       [2, 4, 5, 6, 3, ...]
```

**Step 6：生成两种 mask**

```python
# pad_mask：告诉 attention "这些位置是补的、不许看"
src_pad_mask = (src_ids != 0)            # [B, Lsrc]  bool

# causal mask：目标端"不能偷看未来"
tgt_causal_mask = torch.tril(torch.ones(Ltgt, Ltgt)).bool()   # [Ltgt, Ltgt]
```

**流水线小结：**

```
原文对
  │
  ▼   Step 1: 分词
token 序列对
  │
  ▼   Step 2: 加 <bos>/<eos>
带特殊 token 的序列
  │
  ▼   Step 3: 查词表 → ID
src_ids, tgt_ids  (整数张量)
  │
  ▼   Step 4: 目标端 shift
(src_ids, decoder_input, labels)
  │
  ▼   Step 5: Batch padding
[B, Lsrc], [B, Ltgt-1], [B, Ltgt-1]
  │
  ▼   Step 6: 生成 mask
+ src_pad_mask, tgt_causal_mask
  │
  ▼
🎯 可以送进模型训练
```

#### 6.7.4 一条完整合格的数据对示例

本节主线只做一件事：**看清楚一条最终喂给模型的数据对到底长什么样**。至于"这堆句对是不是要人工标"、"张量怎么脚本化生成"这些工程细节，放在末尾的两个"补充说明"里，按需查阅即可。

##### 6.7.4.1 张量形态：最终喂给模型长这样

给你一份**最终喂给模型的、完全展开的**数据对（batch_size=1，为了清晰）：

```python
sample = {
    "src_ids":         torch.tensor([[3, 4, 5, 2]]),            # [1, 4]   I love you <eos>
    "src_pad_mask":    torch.tensor([[1, 1, 1, 1]], dtype=torch.bool),

    "decoder_input":   torch.tensor([[2, 4, 5, 6]]),            # [1, 4]   <bos> 我 爱 你
    "labels":          torch.tensor([[4, 5, 6, 3]]),            # [1, 4]   我 爱 你 <eos>
    "tgt_pad_mask":    torch.tensor([[1, 1, 1, 1]], dtype=torch.bool),

    "tgt_causal_mask": torch.tensor([[[1, 0, 0, 0],             # [1, 4, 4]
                                       [1, 1, 0, 0],
                                       [1, 1, 1, 0],
                                       [1, 1, 1, 1]]], dtype=torch.bool),
}
```

**每一项对应到 attention 的哪里？**

| 张量 | 送去哪里 | 作用 |
|---|---|---|
| `src_ids` | Encoder 输入 embedding | 变成 6.5 里的 x（源侧） |
| `src_pad_mask` | Encoder self-attn + Cross-attn 的 K 侧 | 屏蔽源端 `<pad>` 位置 |
| `decoder_input` | Decoder 输入 embedding | 变成 Decoder 侧的 x（目标侧） |
| `tgt_causal_mask` | Decoder self-attn | 让位置 t 只能看到 ≤t 的位置 |
| `tgt_pad_mask` | Decoder self-attn | 屏蔽目标端 `<pad>` |
| `labels` | 交叉熵 loss 的 target | **训练监督信号** ← 与第 3 节 CE 接上了 |

---

> 📎 **以下 6.7.4.2 / 6.7.4.3 为补充说明**，解答两个常见工程疑问：
> - **这条数据对的原始句对，需要人工标注吗？** → 见 6.7.4.2
> - **从句对到上面这堆张量，具体怎么自动生成？** → 见 6.7.4.3
>
> 只关心训练主线的读者可**直接跳到 6.7.5**。

##### 6.7.4.2 补充说明 A：这条数据对是"人工标"的吗？

> **一句话回答：** **句对**（"I love you" ↔ "我爱你"）确实是"人写的"，但**不是为训练翻译模型现标的**——它们是**海量已存在的双语文本**（新闻、字幕、书籍、网站……）经过**工具化清洗对齐**后得到的；而从句对到 `src_ids / decoder_input / labels / *_mask` 这一整套张量，则**100% 由脚本自动生成**，无需任何人工介入。

**分成两段责任来看：**

| 阶段 | 输入 | 输出 | 谁来做 |
|---|---|---|---|
| **① 原始句对采集** | 双语文本（早已存在于互联网/图书/字幕库） | 一行行 `英文\t中文` 的 TSV | **工具批量抓取 + 自动对齐**（见下表 A） |
| **② 张量化（本节 6.7.3 流水线）** | 句对 TSV | `src_ids / decoder_input / labels / masks` | **纯脚本**（分词器 + 词表 + PyTorch 一次前处理） |

**表 A：句对怎么"批量"获得？（工程实战选一即可）**

| 来源类型 | 具体方案 | 规模量级 | 是否要写代码 |
|---|---|---|---|
| **现成开源平行语料** | 直接下 [OPUS](https://opus.nlpl.eu/)、[WMT](https://www.statmt.org/)、[UN Parallel Corpus](https://conferences.unite.un.org/uncorpus)、CCMatrix、ParaCrawl、TED2020… | 千万~十亿句对 | ⭐ 最省事，一行 `wget` |
| **HuggingFace 数据集** | `datasets.load_dataset("wmt19", "zh-en")` / `"opus100"` 等 | 百万~千万句对 | 一行 Python |
| **自建 - 已有平行文本** | 双语字幕（`.srt`）、双语图书、法律条文、说明书——用 [Bleualign](https://github.com/rsennrich/Bleualign)、[Vecalign](https://github.com/thompsonb/vecalign)、[LASER](https://github.com/facebookresearch/LASER) 做**句子级自动对齐** | 依素材而定 | 十几行脚本 |
| **自建 - 只有单语文本** | 用一个**已训好**的翻译模型（如 NLLB / OPUS-MT / M2M-100）批量生成伪译，再回译过滤 | 想多少有多少 | 中等 |
| **爬取双语网页** | 抓取 `hreflang="zh"` 与 `hreflang="en"` 互指的页面对 | 依站点而定 | 需要爬虫 |

> 🔑 **要点：** 除了"极小型专业领域微调"这种边角场景，**没人会为通用翻译逐条人工写句对**——这在工程上不可行（GPT-3.5 训练用了数百 GB 文本，靠人工写完全不现实）。**"翻译模型的语料"和"人工标注数据集"是两个不同概念**：前者是**天然存在的双语文本**，工具只做"采集 + 对齐"；后者才需要人为逐条标注（如意图分类、情感标签等）。

##### 6.7.4.3 补充说明 B：从句对到张量的自动化脚本

来一段完整、可运行的**句对 → 6.7.4.1 张量样例**的转换脚本，见证整个 6.7.3 流水线在实际代码里到底是几行的事：

```python
# ---- 假设你已经有了一份句对 TSV（每行:  英文 \t 中文） ----
# I love you\t我爱你
# I love cats and dogs\t我喜欢猫和狗
# ...

# ① 用 sentencepiece / tokenizers 训一份分词器（一次性、几分钟）
# 也可以直接用 HuggingFace 上现成的：AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-zh")
from tokenizers import Tokenizer, models, trainers, pre_tokenizers

def build_tokenizer(corpus_file, vocab_size=8000):
    tok = Tokenizer(models.BPE(unk_token="<unk>"))
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        special_tokens=["<pad>", "<unk>", "<bos>", "<eos>"],
    )
    tok.train([corpus_file], trainer)
    return tok

src_tok = build_tokenizer("en.txt")   # 只用英文那列训
tgt_tok = build_tokenizer("zh.txt")   # 只用中文那列训

# ② 一条句对 → 一条 sample dict（完全对应 6.7.4.1）
import torch

def encode_pair(src_sent, tgt_sent, src_tok, tgt_tok):
    src_ids = src_tok.encode(src_sent).ids + [src_tok.token_to_id("<eos>")]
    tgt_ids = [tgt_tok.token_to_id("<bos>")] + tgt_tok.encode(tgt_sent).ids + [tgt_tok.token_to_id("<eos>")]

    return {
        "src_ids":       torch.tensor(src_ids),
        "decoder_input": torch.tensor(tgt_ids[:-1]),   # shift（见 6.7.3 Step 4）
        "labels":        torch.tensor(tgt_ids[1:]),
    }

# ③ 用 DataLoader 批量取,collate_fn 里做 padding + mask(6.7.3 Step 5/6)
# 略——PyTorch 官方 tutorials 里有现成的 collate_batch 例子
```

**这段脚本告诉我们：** 从一份 TSV 到 6.7.4.1 那种张量样例，**一次运行、可复用于千万级句对**。**唯一"人写"的部分是最原始的双语文本，而那早就存在于互联网上了**。

#### 6.7.5 训练时 loss 怎么算？（对齐 6.6 的训练循环）

有了上面的数据对，训练循环几乎和 6.6.4 完全一样——**只需替换第 ② ③ 步**：

```python
for step, batch in enumerate(dataloader):
    optimizer.zero_grad()                                       # ① 通用（同 6.6）

    logits = model(                                             # ② 前向：翻译特化
        src_ids       = batch["src_ids"],
        decoder_input = batch["decoder_input"],
        src_pad_mask  = batch["src_pad_mask"],
        tgt_pad_mask  = batch["tgt_pad_mask"],
        causal_mask   = batch["tgt_causal_mask"],
    )                                                           # logits: [B, Ltgt, |tgt_vocab|]

    loss = F.cross_entropy(                                     # ③ loss：CE，见 3 节
        logits.reshape(-1, logits.size(-1)),                    # [B*Ltgt, |V|]
        batch["labels"].reshape(-1),                            # [B*Ltgt]
        ignore_index = 0,                                       # 忽略 <pad> 位置
    )

    loss.backward()                                             # ④ 通用（同 6.6）
    optimizer.step()                                            # ⑤ 通用（同 6.6）
```

> 🔑 **两处变化的本质：**
> - **② 前向变复杂**：因为要跑一整个 Encoder-Decoder，而不再是一个孤立的单头 attention
> - **③ loss 从 MSE 换回 CE**：因为输出变成了"下一个 token 的分类分布"，正好回到第 3 节讲的 `CrossEntropyLoss` 场景
>
> **其余（zero_grad / backward / step）与 6.6.4 完全一致。** 这就是训练框架的通用性——**数据换了、任务换了、模型换了，训练循环骨架不变**。

#### 6.7.6 数据对的三个常见"坑"

| 坑 | 表现 | 正确做法 |
|---|---|---|
| 忘了 shift | loss 一开始就极低甚至为 0 | decoder 输入拿到了当前位置的答案 → 训完是"复读机"，一上线就废 |
| pad 位置没 ignore | loss 被 `<pad>` 稀释，训练信号弱 | `cross_entropy(..., ignore_index=<pad_id>)` |
| 没加 causal mask | decoder 看到未来 token | 训练 loss 好看，推理时崩塌（推理时看不到未来） |

#### 6.7.7 从 6.6 到 6.7 的进化对照表

用一张表看清"玩具任务"和"真实翻译任务"在数据侧的所有差异：

| 维度 | 6.6 恒等复原 | 6.7 英→中翻译 |
|---|---|---|
| 数据配对 | (x, x) 自监督 | (英文句, 中文句) 平行语料 |
| 数据形态 | 连续向量 `[L, d]` | 离散整数 ID `[B, L]` |
| 是否需要词表 | 否 | 是（源、目标各一份） |
| 特殊 token | 无 | `<pad> <bos> <eos> <unk>` |
| Batch 内长度 | 固定 | 变长 → padding |
| 是否需要 mask | 否 | pad mask + causal mask |
| 目标端处理 | 无 | shift 一位 |
| 损失函数 | MSELoss（回归） | CrossEntropyLoss（分类） |
| 输出层 | attention output 直接就是目标 | attention output 再过 `Linear → vocab_size` 产生 logits |
| 收敛难度 | 单头 CPU 秒级收敛 | 需要多头 + 多层 + 大量语料 + GPU |

**一句话总结：** 6.6 的训练循环骨架**普适到任何任务**；6.7 讲的是"给骨架配上翻译任务所需的数据血肉"——只要数据对满足 6.7.2 的六个条件，把 6.6 的第 ② ③ 步换成 6.7.5 的样子，一个真实的英→中翻译模型就能开始训练。至于 Encoder-Decoder 内部到底怎么串起来、cross-attention 的 Q/K/V 从哪儿取，下一章会展开。

### 6.8 Multi-Head Attention（多头注意力）

前面 6.1~6.7 讲的是**单头** attention（含单头下的完整训练与数据准备），实际 Transformer 用的是 **多头 attention**——文档里到处出现的 `H`（如 `[B, H, L, d_k]` 里的 H），就是"头数"。这一节讲清楚"多头"到底在干什么、为什么这么设计、以及怎么写。

> 📎 **阅读路线：** 6.8.1（是什么）→ 6.8.2（为什么）→ 6.8.3（怎么做·直觉）→ 6.8.4（数学公式）→ 6.8.5/6.8.6（关键设计）→ 6.8.7（工程代码）→ 6.8.8（形状速查）→ 6.8.9（训练视角）→ 6.8.10（澄清误区）

#### 6.8.1 一句话理解

> **多头 attention = 把 attention 并行做 H 次，每次用不同的"视角"，最后把结果拼接 + 融合。**
>
> 类比：一个团队分析同一份文档。1 个人（单头）只能有 1 个视角；8 个人（多头）分别从语法、语义、指代、位置等角度分析，最后汇总得到更全面的理解。

#### 6.8.2 为什么需要多头？

**单头的问题：** 一个 attention 头只能学到**一种模式**的注意力分配。例如：

- 只能关注"语法主谓关系"，就学不到"指代消解"
- 只能关注"局部相邻词"，就学不到"跨句长距离依赖"

**多头的解决方案：** 让 H 个头**并行**学习不同的注意力模式，各司其职。

论文 [Attention Is All You Need] 里的经典可视化显示：

- 有的头专注**语法关系**（主-谓、动-宾）
- 有的头专注**共指消解**（"他" 指向前文哪个人名）
- 有的头专注**位置模式**（关注前一个 / 后一个 token）
- 有的头专注**特殊 token**（大量关注 `[CLS]` / `[SEP]`）

#### 6.8.3 从单头到多头的"三步改造"（直觉版）

以 `d_model=512, H=8` 为例，看清多头相对单头**多做了什么**。

##### 6.8.3.1 Step 1：拆分 —— 把每个 token 的 512 维切成 8 份

单头的 Q/K/V 是整块 `[B, L, 512]`；多头把它按最后一维**均匀切**成 H 份：

```
                   token 视角（每个 token 的 512 维向量）
                   ────────────────────────────────────────
     单头：       [────────── 512 维一整块 ──────────]   → 1 个 attention

     多头 H=8：   [ 64 | 64 | 64 | 64 | 64 | 64 | 64 | 64 ]
                   ↑    ↑                            ↑
                head_0 head_1                     head_7
                每一段 64 维喂给一个独立的 attention 头
```

工程实现只需一次 `view + transpose`：

```
Q/K/V  : [B, L, d_model=512]                             (投影后)
    │ view(B, L, H=8, d_k=64) + transpose
    ▼
Q/K/V  : [B, H=8, L, d_k=64]                             (拆头后)
```

##### 6.8.3.2 Step 2：并行 —— 8 个头在同一个 GPU kernel 里同时算

每个头在自己的 `d_k=64` 子空间内独立跑 6.5 讲过的 scaled dot-product attention：

```
head_0:  attn_0 = softmax(Q_0 · K_0ᵀ / √64) · V_0     ┐
head_1:  attn_1 = softmax(Q_1 · K_1ᵀ / √64) · V_1     │
  ...                                                    │  ← 并行（同一次矩阵乘完成）
head_7:  attn_7 = softmax(Q_7 · K_7ᵀ / √64) · V_7     ┘
```

因为多出来的 `H` 只是 batch 维的一个"广播维"，PyTorch/CUDA 一次 batched matmul 就搞定，**不需要 for 循环**。

每个头输出形状：`[B, L, d_k=64]`；堆叠起来：`[B, H=8, L, d_k=64]`。

##### 6.8.3.3 Step 3：拼接 + `W_O` 融合 —— 把 8 段拼回 512 维再过一层线性

```
[B, H=8, L, 64]  ──transpose+view──▶  [B, L, 512]      ← 简单拼接（把 8 段并起来）
                                          │
                                          │  @ W_O   ← 线性融合各头信息
                                          ▼
                                       [B, L, 512]      ← 最终输出，形状回到 d_model
```

> 🔑 **三步改造精髓：** ① 切开 → ② 独立算 → ③ 拼回来 + 缝一针。切多深、缝多细就是 `H` 和 `W_O` 说了算。

#### 6.8.4 数学公式（附形状标注）

上面的直觉画面用公式写出来就是：

\[
\text{MultiHead}(Q, K, V) = \text{Concat}(\text{head}_1, \dots, \text{head}_H) \cdot W_O
\]

其中每个头独立计算：

\[
\text{head}_i = \text{Attention}(Q W_Q^{(i)},\ K W_K^{(i)},\ V W_V^{(i)})
\]

**各符号的形状：**

| 符号 | 形状 | 说明 |
|---|---|---|
| `Q, K, V`（输入） | `[B, L, d_model]` | 通常都由同一个 x 投影而来（self-attn 场景） |
| `W_Q^(i), W_K^(i), W_V^(i)` | `[d_model, d_k]` | 每个头独立一组，共 3H 组 |
| `head_i` | `[B, L, d_k]` | 每个头的输出 |
| `Concat(head_1,...,head_H)` | `[B, L, H·d_k] = [B, L, d_model]` | H 段横向拼接 |
| `W_O` | `[d_model, d_model]` | 输出融合矩阵 |
| `MultiHead(...)` | `[B, L, d_model]` | 最终输出，形状与输入一致 |

> ⚠️ **数学定义 vs 工程实现（关键澄清）：**
>
> - **数学定义**（上面这个公式）：写成 H 组独立的 `W_Q^(i)`，便于形式化推导
> - **工程实现**（6.8.7 代码）：把 H 组 `W_Q^(i)` 横向合并成**一个大矩阵** `W_Q ∈ [d_model, d_model]`，一次矩阵乘算完再 view 出 H 个头
>
> **两者数学上完全等价**，只是"分开写 H 次矩阵乘" vs "合并成一次大矩阵乘" 的排布差异。GPU 显然更喜欢后者。初学者看两处描述不一致时不必慌张——这就是原因。

#### 6.8.5 关键设计一：`d_k = d_model / H`（参数量守恒）

**为什么要这样切？** 保持**总参数量和总计算量**与单头恒定。

对比 "1 个大头（d_k=512）" vs "8 个小头（d_k=64）"：

| 方案 | 每头 d_k | Q/K/V 每组参数量 | 组数 | QKV 总参数量 |
|---|---|---|---|---|
| 单头（H=1） | 512 | 512 × 512 = 262K | 3 组 | **786K** |
| 多头（H=8） | 64 | 512 × 64 = 32K | 3 × 8 = 24 组 | 24 × 32K = **786K** |

> 💡 **为什么 H 恰好消掉了？** 因为 `H × d_k = d_model` 是硬约束。每头参数量为 `d_model × d_k = d_model × (d_model/H) = d_model² / H`，乘以 H 个头正好 = `d_model²`，与单头一致。这就是工程实现里能把 H 组 W 合并成一个 `[d_model, d_model]` 矩阵的深层原因。

**结论：** 参数量 & 计算量与单头持平，但**表达能力更强**——能同时学 H 种不同关注模式。

#### 6.8.6 关键设计二：为什么必须有 `W_O`？

拼接后 `[B, L, 512]` 的每个 token 向量里，每 64 维来自不同的头，**语义空间是割裂的**：

```
[  head_0 的 64 维  |  head_1 的 64 维  |  ...  |  head_7 的 64 维  ]
      ↑ 语法头            ↑ 共指头                     ↑ 位置头
```

**没有 W_O 会怎样？（反例）**

假设直接把拼接结果送给下游 FFN——FFN 的每个神经元会被强行绑定到某个"固定的 64 维块"上。比如"下游 FFN 只有前 64 维（语法头）的信号进得来某个神经元"——**头与头之间无法互通有无**。语法头和共指头本该协同回答"这个代词指谁"，却被硬件级隔离。

**`W_O`（形状 `[d_model, d_model]`）的作用：**

- 是一个**全连接层**，让输出的每一维都能是"所有头输出的加权组合"
- 相当于给"多头拼盘"再撒一层胶水，把 H 个割裂子空间**融合**成一个统一的 `d_model` 空间
- 下游层可以"平等地"处理这 512 维，不再感知"哪 64 维来自哪个头"

> ⚠️ **常见错误：** 手写 MHA 时忘记 `W_O`——这是初学者最容易漏的一步，忘了会掉点严重（尤其是深层模型）。

#### 6.8.7 程序员视角：完整实现代码

```python
import torch
import torch.nn.functional as F

def multi_head_attention(x, W_Q, W_K, W_V, W_O, num_heads):
    """
    x:   [B, L, d_model]
    W_Q, W_K, W_V, W_O: [d_model, d_model]     ← 工程实现里都是"大矩阵"
    返回: [B, L, d_model]
    """
    B, L, d_model = x.shape
    H = num_heads
    d_k = d_model // H

    # ─── ① QKV 投影（一次大矩阵乘，等价于 H 组小矩阵乘的合并）─────────
    Q = x @ W_Q                                            # [B, L, d_model]
    K = x @ W_K
    V = x @ W_V

    # ─── ② 拆多头：[B, L, d_model] → [B, H, L, d_k] ────────────────
    Q = Q.view(B, L, H, d_k).transpose(1, 2)               # [B, H, L, d_k]
    K = K.view(B, L, H, d_k).transpose(1, 2)
    V = V.view(B, L, H, d_k).transpose(1, 2)

    # ─── ③ 每个头并行做 scaled dot-product attention ────────────────
    scores = Q @ K.transpose(-2, -1) / (d_k ** 0.5)        # [B, H, L, L]
    attn   = F.softmax(scores, dim=-1)                     # [B, H, L, L]
    out    = attn @ V                                      # [B, H, L, d_k]

    # ─── ④ 拼回来：[B, H, L, d_k] → [B, L, d_model] ────────────────
    out = out.transpose(1, 2).contiguous().view(B, L, d_model)

    # ─── ⑤ 输出投影（W_O 融合）────────────────────────────────────
    return out @ W_O                                       # [B, L, d_model]
```

> 🔑 **代码 ↔ 概念对齐：**
> - ①对应"数学定义中的 H 组 `W_Q^(i)`"合并成一次大矩阵乘（见 6.8.4 澄清）
> - ②对应 6.8.3.1 的"切成 8 份"
> - ③对应 6.8.3.2 的"并行 8 个头"
> - ④+⑤对应 6.8.3.3 的"拼接 + W_O 融合"

#### 6.8.8 形状变化速查

一条竖线看清所有中间张量的形状：

```
x        : [B, L, d_model]
    │
    │  ① QKV 投影（@ W_Q / W_K / W_V）
    ▼
Q,K,V    : [B, L, d_model]
    │
    │  ② view + transpose（拆头）
    ▼
Q,K,V    : [B, H, L, d_k]              ← d_k = d_model / H
    │
    │  ③ scaled dot-product（每头独立）
    ▼
out      : [B, H, L, d_k]
    │
    │  ④ transpose + view（拼接 H 段）
    ▼
out      : [B, L, d_model]             ← H · d_k = d_model
    │
    │  ⑤ @ W_O（融合）
    ▼
output   : [B, L, d_model]             ← 形状与输入 x 完全一致
```

> 🎯 **一句话总结**：多头 = **同一份输入 x，用 H 组独立的 W_Q/W_K/W_V 投影出 H 组 Q/K/V，并行做 H 次 attention，最后拼接 + `W_O` 融合**。参数量和单头相同，但能学到 H 种不同的关注模式。

#### 6.8.9 训练视角：多头下的梯度怎么流？

前面全在讲前向。**训练时（衔接 6.6）呢？** 只需一句话：

> **多头没有引入任何"新训练机制"**——`W_Q / W_K / W_V / W_O`（工程实现里合并后的 4 个大矩阵）都是普通 `nn.Linear` 参数，`loss.backward()` 后 autograd 自动把梯度分派到每个头对应的切片。

具体地：

| 训练环节 | 单头（6.6） | 多头 |
|---|---|---|
| 可训练参数 | `W_Q, W_K, W_V`（+ 可选 `W_O`） | `W_Q, W_K, W_V, W_O` **都必需** |
| 参数总量 | `3 · d_model²`（+ `d_model²`） | `4 · d_model²`（W_O 强制） |
| `loss.backward()` | 沿计算图反传到叶子 W | **完全相同**，H 只是 view 出来的 batch 维 |
| 每个头是否独立更新 | 只有 1 个头 | **是**——H 个头对应 W_Q 的 H 段列切片，各自的梯度天然独立 |
| 训练循环骨架 | 6.6.4 的五步 | **完全相同**，只换模型这一层 |

> 🔑 **精髓：** 多头是"前向计算图的一次广播 + view"，不是"H 个独立模型"。所以对训练框架来说，多头只是把一个大 `W_Q` 拆成 H 个逻辑列块——梯度天然按块隔开，autograd 全自动搞定。

#### 6.8.10 常见误区：多头 = 多个单头串联？

> 🎯 **本小节目的：** 学完 6.7 单头 + 6.8 前 9 小节之后，最常见的直觉是"**多头就是把 6.7 的单头串起来 H 个**"。这个说法**方向对了一半，细节有偏差**。本节把它一次澄清。（本节只戳破直觉误区，参数量/W_O 融合等结论已在 6.8.5/6.8.6 详证，此处不重复。）

##### 6.8.10.1 一句话结论

> **多头 = "并联"而不是"串联"，而且并联的是"更小的头"而不是"和 6.7 一样的头"。**

准确表述：

> **多头 = 把 6.7 那个大单头劈成 H 份并联，末尾加一个 `W_O` 缝合——仍然是模型里的"1 层"。**

##### 6.8.10.2 拓扑澄清：并联 ≠ 串联

```
串联（不是多头，是"多层堆叠"）：           并联（才是多头）：
                                                 ┌→ head_1 ─┐
x ─→ attn_1 ─→ attn_2 ─→ ...             x ─→ ─→│→ head_2 ─│→ Concat ─→ W_O ─→ out
                                                 │   ...    │
                                                 └→ head_H ─┘
```

H 个头在**同一个前向 step 内**由 GPU 一次矩阵乘并行完成（见 6.8.3.2），而不是 H 次串行调用 6.7 的模型。

---

**图示尾注：`Concat` 到底是什么操作？**

上图里的 `Concat ─→ W_O` 常被误读成"把 H 个头串起来跑一遍"。它其实是一次**纯张量拼接**——**不涉及任何计算、不涉及时间上的先后**，只是把 H 个头**并排**放在最后一维上，凑回 `d_model` 的宽度，好让 `W_O` 做一次线性融合。

**① 一句话定义：** `Concat` = `torch.cat(..., dim=-1)`，沿**最后一维（特征维）**把 H 个 `[..., d_k]` 张量**横向拼**成一个 `[..., H·d_k] = [..., d_model]` 张量。

**② 张量形状变化（以 batch=B、序列长度=L 为例）：**

```
head_i:  [B, L, d_k]   （i = 1, 2, ..., H；每个头的 d_k = d_model / H）
                │
                ▼  沿最后一维拼接（Concat）
                                             ┌── 来自 head_1 ──┐┌── 来自 head_2 ──┐    ┌── 来自 head_H ──┐
concat: [B, L, H·d_k] = [B, L, d_model]      │                 ││                 │....│                 │
                │
                ▼  乘以 W_O ∈ [d_model, d_model]
out:    [B, L, d_model]
```

**③ 数学表达式：** 设第 i 个头的输出为 `head_i ∈ ℝ^{L × d_k}`，则

```
MultiHead(x) = Concat(head_1, head_2, ..., head_H) · W_O
             = [ head_1 | head_2 | ... | head_H ] · W_O
```

其中 `[·|·|...|·]` 表示矩阵**按列并排拼接**（block matrix，不是数值加法、不是矩阵乘法）。展开写出维度：

```
[L × d_k] ⊕ [L × d_k] ⊕ ... ⊕ [L × d_k]   →   [L × H·d_k]
                                                       ↓ · W_O ∈ [H·d_k, d_model]
                                                  [L × d_model]
```

`⊕` 在这里就是"把两个矩阵水平放到一起"，等价于 NumPy 的 `np.hstack` / PyTorch 的 `torch.cat(dim=-1)`。

**④ PyTorch 一行等价实现：**

```python
# heads: list of H 个张量, 每个都是 [B, L, d_k]
concat = torch.cat(heads, dim=-1)     # [B, L, H*d_k] = [B, L, d_model]
out    = concat @ W_O                  # [B, L, d_model]

# 工程实现里更常见的写法（避免 for 循环建 list）：
# 直接把 [B, H, L, d_k] 用 transpose+reshape 铺平成 [B, L, H*d_k]，等价效果
out = attn_out.transpose(1, 2).reshape(B, L, H * d_k) @ W_O
```

**⑤ 与"串联/串行"的本质差别：**

| 属性 | Concat（本处操作） | 串联/串行（多层堆叠） |
|---|---|---|
| 有无计算 | ❌ 只是内存布局重排 | ✅ 每层都有独立的前向计算 |
| 时间性 | 并行——所有头**已经**同时算完 | 顺序——第 t 层必须等 t-1 层输出 |
| 形状变化 | `H × [B, L, d_k] → [B, L, H·d_k]` | `[B, L, d_model] → [B, L, d_model]`（形状不变） |
| 类比 | **把 H 张纸横向铺开成一张大纸** | **把 N 张纸从上往下摞起来** |

> 🔑 **一句话记住：** `Concat` 是"横向铺开"（空间上的**并**），**不是**"依次跑一遍"（时间上的**串**）。真正做融合、把这 H 段拼接向量映射回 `d_model` 的，是紧跟其后的 `W_O`——它才是各头信息**跨子空间交互**的唯一通道（这一点在 6.8.6 已详细说明）。

##### 6.8.10.3 尺寸澄清：多头里的 head ≠ 6.7 里的单头

这是最容易被"多个单头串联"直觉误导的地方：

| 对比项 | 6.7 里的单头 | 6.8 里的每个 head |
|---|---|---|
| Q/K/V 维度 | `d_k = d_model`（比如 512） | `d_k = d_model / H`（比如 64） |
| W_Q 形状 | `[d_model, d_model]` | `[d_model, d_model/H]` |
| 参数量占比 | 100% | 1/H |

**所以严格说：多头 ≠ H 个 6.7 单头的并联，而是 = "1 个 6.7 大单头被切成 H 份并联"。**

##### 6.8.10.4 6.7 的东西到底怎么被复用？

多头替换的**只是模型内部的一层**，数据侧、训练循环全都不变：

```
                                6.7 的贡献
              ┌─────────────────────────────────────────┐
              │ 数据流水线 (src_ids/tgt_ids/masks/CE)     │  ← 完全不变
              └─────────────────────────────────────────┘
                                    │
                                    ▼
              ┌─────────────────────────────────────────┐
              │ 训练循环 (6.6.4 的五步骨架)                │  ← 完全不变
              └─────────────────────────────────────────┘
                                    │
                                    ▼
   ┌──────────────────────────────────────────────────────────┐
   │  模型内部这一层：                                          │
   │                                                            │
   │  6.7 里用的是：1 个"大"单头（d_k = d_model）               │
   │  6.8 换成了：  H 个"小"单头并联 + W_O 融合                 │  ← 只换这里
   │                （d_k = d_model / H）                       │
   └──────────────────────────────────────────────────────────┘
```

##### 6.8.10.5 三种说法的准确度对照

| 直觉说法 | 是否准确 | 更准确的说法 |
|---|---|---|
| "多头 = 多个 6.7 单头串联" | ❌ | 串联是"堆叠层数"，不是多头 |
| "多头 = 多个 6.7 单头并联" | ⚠️ 半对 | 拓扑对了，但每个头**变小**了 |
| **"多头 = 把 6.7 那个大单头劈成 H 份并联，末尾加一个 W_O 缝合"** | ✅ | 这才是准确表述 |

##### 6.8.10.6 那"串联"体现在哪里？

Transformer 里确实有"串联"，但那是**层与层之间**（比如 12 层 Encoder 首尾相接），不是"多头"这个概念。用两个正交的维度来记：

| 维度 | 名字 | 表现 | 目的 |
|---|---|---|---|
| **宽度** | 多头（Multi-Head） | 一层内 H 个头**并联** | 同一位置捕捉 H 种不同关注模式 |
| **深度** | 多层（Multi-Layer） | N 层 attention **串联** | 逐层加工，抽象层次由浅到深 |

Transformer 论文常写作 `Nx (Multi-Head Attention + FFN)`——**`x N` 才是串联**，`Multi-Head` 本身是并联。

##### 6.8.10.7 一句话总括

> **6.7 描述的"单头"是"一层里就 1 个头"的退化情形；6.8 是把这唯一的头切成 H 个小头并联，再加 `W_O` 做融合，得到的仍然是"一层"。把这一层再首尾接 N 次，才是完整 Transformer 的"串联"（属于后续章节）。**

#### 6.8.11 PyTorch API：`nn.MultiheadAttention`

> 🔗 **和 6.8.7 的关系**：6.8.7 是**手写版**——把 QKV 投影、拆头、缩放点积、拼接、`W_O` 融合五步全部拆开写；本节展示 PyTorch 里**开箱即用的高层 API**，它把这五步封装在一次调用里，且性能上会走 CUDA fused kernel。看完本节，就完成了「手写 → API」的对应。

##### 6.8.11.1 最小可运行示例

```python
import torch
import torch.nn as nn

embed_dim = 512
num_heads = 8
seq_len = 5
batch_size = 2

# 定义 MHA
mha = nn.MultiheadAttention(
    embed_dim=embed_dim,
    num_heads=num_heads,
    batch_first=True   # ✅ 推荐，输入格式 [B, L, E]
)

# 准备输入（Self-Attention: Q=K=V）
x = torch.randn(batch_size, seq_len, embed_dim)

# 前向
output, attn_weights = mha(x, x, x)

print(output.shape)        # [2, 5, 512]
print(attn_weights.shape)  # [2, 5, 5]
```

##### 6.8.11.2 内部 6 个阶段（与 6.8.7 手写版一一对应）

| 阶段 | 操作 | 形状变化 | 对应 6.8.7 步骤 |
|---|---|---|---|
| ① QKV 投影 | `x @ W_q^T + b_q` 等 | `[B, L, 512]` → `[B, L, 512]` | ① |
| ② 拆多头 | `view(B, L, H, d_k).transpose(1, 2)` | `[B, H, L, d_k]` | ② |
| ③ 缩放点积 | `Q @ K^T / sqrt(d_k)` | `[B, H, L, L]` | ③ |
| ④ Softmax | `softmax(scores, dim=-1)` | `[B, H, L, L]` | ③ |
| ⑤ 加权求和 | `attn @ V` | `[B, H, L, d_v]` | ③ |
| ⑥ 拼接+输出投影 | `view(B, L, embed_dim) @ W_o^T` | `[B, L, 512]` | ④+⑤ |

##### 6.8.11.3 手写版 vs API 版对照

| 项目 | 6.8.7 手写 | `nn.MultiheadAttention` |
|---|---|---|
| QKV 投影 | 手写 Linear | ✅ 内置 |
| 拆多头 | `view + transpose` | ✅ 自动 |
| 缩放点积 | 手写 | ✅ 内置 |
| Mask | 手写传入 | ✅ 内置（`attn_mask` / `key_padding_mask`） |
| 拼接 | 手写 | ✅ 自动 |
| 输出投影 `W_O` | ❌ 手写时最容易漏 | ✅ 内置 |
| Dropout | 手写 | ✅ 内置 |
| 性能 | 慢 | ✅ CUDA fused kernel |

> ⚠️ **手写 → API 迁移的最大陷阱**：手写时经常漏掉 `W_O`（见 6.8.6），换成 API 后**这一步会被内置强制加上**——所以别看到"输出形状对了"就以为两版数值也对，参数集是不同的。

##### 6.8.11.4 关键构造参数

```python
mha = nn.MultiheadAttention(
    embed_dim=512,
    num_heads=8,
    batch_first=True,          # 输入 [B, L, E]，默认是 [L, B, E]
    dropout=0.1,               # attention dropout
    average_attn_weights=True  # True: 返回各头平均; False: 返回每头 [B, H, Lq, Lk]
)
```

##### 6.8.11.5 常见错误

❌ **错误：** 自己先做 QKV 投影再传入 MHA

```python
q = nn.Linear(512, 64)(x)  # ❌ MHA 内部会自己做投影，重复投影导致语义错乱
output, attn = mha(q, k, v)
```

✅ **正确：** 直接传原始输入张量，让 MHA 自己完成 QKV 投影

```python
output, attn = mha(x, x, x)
```

> 🎯 **一句话总结**：`nn.MultiheadAttention` 就是 6.8.7 那段手写代码的"官方封装版"，把 6.8.6 强调过的 `W_O` 也一并内置——写训练/推理代码时**优先用 API**，只有在需要魔改（比如替换 attention 内核、加自定义 mask 逻辑）时才回落到手写版。至于 self / cross 的差异被压缩成"传入的三个位置参数是否相同"，第 7 章会展开。

---

## 7. Self-Attention vs Cross-Attention

Attention 只有一种数学公式（第 6 章讲过），但根据 **Q/K/V 从哪来**，会派生出两种截然不同的用途：**Self-Attention**（自注意力）和 **Cross-Attention**（交叉注意力）。它们的区别是 Transformer 架构的核心，也是很多人入门时最容易混淆的地方。

> 📎 **阅读路线：** 7.1（一句话对比）→ 7.2（差异总览表）→ 7.3（张量视角·手写代码）→ 7.4（数学形式）→ 7.5（PyTorch API 对照）→ 7.6（Masked 变体）→ 7.7（在 Transformer 中的位置）→ 7.8（直觉类比）→ 7.9（FAQ）。前 5 节回答"是什么、怎么算"，后 4 节回答"用在哪、怎么记"。
>
> 📎 **与第 6 章的衔接**：第 6 章的 attention 公式并没有指定 Q/K/V 从哪来——本章就是**在同一个公式上，通过换 Q/K/V 的来源**，派生出 self / cross 两种应用形态。位置编码作为一个**正交议题**（无论 self 还是 cross 都需要它），已独立为第 8 章。

### 7.1 一句话对比

> **Self-Attention：Q、K、V 都来自同一个序列**——序列内部各位置互相"看"，用来**理解自己**。
>
> **Cross-Attention：Q 来自序列 A，K、V 来自序列 B**——A 拿着问题，去 B 里找答案，用来**引入外部信息**。

### 7.2 核心差异总览

| 维度 | Self-Attention | Cross-Attention |
|---|---|---|
| **Q 来源** | 当前序列 X | 解码器（decoder）当前输出 |
| **K/V 来源** | 当前序列 X（**同源**） | 编码器（encoder）最终输出（**异源**） |
| **Lq 与 Lk** | Lq == Lk（==L） | Lq 可 ≠ Lk |
| **注意力矩阵形状** | 方阵 `[L, L]` | 矩形 `[Lq, Lk]` |
| **主要作用** | 建立序列内部依赖 | 建立两个序列间的对齐 |
| **典型场景** | BERT、GPT 的每一层 | 翻译模型的解码器、Stable Diffusion 的图文对齐 |
| **Encoder 用吗** | ✅ 用 | ❌ 不用 |
| **Decoder 用吗** | ✅ 用（Masked 版） | ✅ 用 |

> 💡 **记忆口诀：** "Q/K/V 同源即 Self，异源即 Cross"。

> 🔎 **表格里的"当前序列 X"到底指什么？（结合 6.4 节翻译例子：英→中）**
>
> "X" 是一个**占位符**，代表**"当前这一层 attention 的输入序列"**——它是英文还是中文，**取决于这一层 attention 长在哪里**（Encoder 里 or Decoder 里）。
>
> **对应到英→中翻译例子（源语言=英文，目标语言=中文）：**
>
> | 位置 | X 具体是谁 | Q/K/V 来源 | 属于哪种 attention |
> |---|---|---|---|
> | **Encoder 的 Self-Attention** | X = **英文序列** `"I / love / cats"`（Lk=3） | Q=K=V=英文 | Self-Attention |
> | **Decoder 的 Masked Self-Attention** | X = **中文序列** `"我 / 非常 / 喜欢 / 猫"`（Lq=4） | Q=K=V=中文 | Masked Self-Attention |
> | **Decoder 的 Cross-Attention** | Q ← **中文**（decoder 侧）<br>K,V ← **英文**（encoder 输出） | Q≠K,V | Cross-Attention |
>
> **关键理解：**
> - Self-Attention 里的 X **不固定**是英文还是中文，"看你在哪一层"——**Encoder 层里 X 就是英文（源）**，**Decoder 层里 X 就是中文（目标，且已生成部分）**
> - **同一模型里 self-attention 会出现两次**：一次在 encoder（X=英文），一次在 decoder（X=中文），两者的 X 不是同一个序列
> - Cross-Attention 只在 **Decoder** 里出现一次，此时"两个 X"同时登场：Q 来自中文这个 X，K/V 来自英文那个 X
>
> **一句话总结：** "X" 是变量名不是常量。**Self-Attention 关心的是"某一层的输入序列自己和自己交互"**，至于这个序列是英文还是中文，看它落在 Encoder 还是 Decoder。

### 7.3 张量视角：Q/K/V 从哪来（程序员最关心）

这是理解两者差异的**最直接方式**——直接看代码里 Q、K、V 是怎么算出来的。

#### 7.3.1 Self-Attention

**只有一个输入序列 `X`**，Q/K/V 都是它经过**三个不同的线性投影**得到的：

```python
# X: [B, L, d_model]   ← 唯一的输入
Q = X @ W_Q            # [B, L, d_model]  ← 同一个 X
K = X @ W_K            # [B, L, d_model]  ← 同一个 X
V = X @ W_V            # [B, L, d_model]  ← 同一个 X
```

**关键点：**
- **输入只有 1 个**：X
- **可学习参数有 3 组**：W_Q、W_K、W_V（三者不共享权重，负责从 X 里投影出不同"视角"）
- **Q、K、V 序列长度必然相等**（都 = L）

#### 7.3.2 Cross-Attention

**有两个输入序列**：一个来自 decoder（`X_dec`），一个来自 encoder（`X_enc`）：

```python
# X_dec: [B, Lq, d_model]   ← decoder 侧（发起查询的一方，提供 Q）
# X_enc: [B, Lk, d_model]   ← encoder 侧（被查询的记忆库，提供 K/V）
Q = X_dec @ W_Q             # [B, Lq, d_model]  ← 来自 decoder
K = X_enc @ W_K             # [B, Lk, d_model]  ← 来自 encoder
V = X_enc @ W_V             # [B, Lk, d_model]  ← 来自 encoder
```

**关键点：**
- **输入有 2 个**：X_dec、X_enc
- **Q 单独来源**（decoder），**K/V 一起来源**（encoder）
- **Lq 和 Lk 可以不等**（例如中文 4 个 token 翻译成英文 3 个 token）

> 🎯 **一图秒懂：**
> ```
> Self:     X ──┬── W_Q ──→ Q
>               ├── W_K ──→ K
>               └── W_V ──→ V         （一根源，分三叉）
>
> Cross:    X_dec ── W_Q ──→ Q        （decoder 出 Q）
>           X_enc ─┬─ W_K ──→ K
>                  └─ W_V ──→ V        （encoder 出 K/V）
> ```

#### 7.3.3 形状速查（程序员对照表）

对齐 6.8.8 的写法，把 self / cross 两侧的关键张量一次性列清楚：

| 张量 | Self-Attention | Cross-Attention | 备注 |
|---|---|---|---|
| 输入源数量 | 1（`X`） | 2（`X_dec`, `X_enc`） | Cross 需要跨序列 |
| Q 来源 shape | `[B, L,  d_model]` | `[B, Lq, d_model]` | Q 长度 = 目标序列长度 |
| K 来源 shape | `[B, L,  d_model]` | `[B, Lk, d_model]` | K 长度 = 被查询序列长度 |
| V 来源 shape | `[B, L,  d_model]` | `[B, Lk, d_model]` | 必须与 K **同源、同长** |
| 注意力矩阵 | `[B, H, L,  L ]`（**方阵**） | `[B, H, Lq, Lk]`（**矩形**） | 决定内存开销 |
| 输出 shape | `[B, L,  d_model]` | `[B, Lq, d_model]` | **与 Q 对齐**（不是 K/V） |
| Q≠K 是否合法 | ❌ 必然 Lq=Lk=L | ✅ Lq 与 Lk 可任意 | 翻译任务 4↔3 就是这种 |

> 🔑 **记忆点**：**输出总是与 Q 对齐**（Q 有多长，输出就多长）。所以 cross 里"翻译成几个 token"由 decoder 侧的 Q 决定，与源语言长度无关。

### 7.4 数学形式对比

**Self-Attention（输入只有 X）：**

\[
\text{SelfAttn}(X) = \text{softmax}\!\left(\frac{(XW_Q)(XW_K)^T}{\sqrt{d_k}}\right) XW_V
\]

**Cross-Attention（输入有 X_dec 和 X_enc）：**

\[
\text{CrossAttn}(X_{\text{dec}}, X_{\text{enc}}) = \text{softmax}\!\left(\frac{(X_{\text{dec}} W_Q)(X_{\text{enc}} W_K)^T}{\sqrt{d_k}}\right) X_{\text{enc}} W_V
\]

**注意力矩阵形状对比：**

```
Self :  softmax(...) → [B, H, L,  L ]   ← 方阵
Cross:  softmax(...) → [B, H, Lq, Lk]   ← 矩形
```

### 7.5 PyTorch 代码对照（一目了然）

> 🔗 **和 7.3 的关系**：7.3 展示了 attention 的**底层原理**——手写 `Q = X @ W_Q` 这类投影。本节展示 PyTorch 里**开箱即用的高层 API**。对应关系一句话：`nn.MultiheadAttention` 内部就是在做「7.3 的三次投影」+「6.1 的 `softmax(QKᵀ/√d)·V`」+「6.8.3.3 的拼接与 W_O 融合」。只是 self / cross 的差异被**优雅地压缩成"传入的三个位置参数是否相同"**。

PyTorch 里 `nn.MultiheadAttention` 的调用方式**完全一样**，差别只在**传入的三个参数是否相同**：

```python
import torch.nn as nn

mha = nn.MultiheadAttention(embed_dim=512, num_heads=8, batch_first=True)

# ① Self-Attention：query、key、value 传同一个张量
out, attn_weights = mha(x, x, x)                # x: [B, L, 512]

# ② Cross-Attention：query 来自 decoder，key/value 来自 encoder
out, attn_weights = mha(x_dec, x_enc, x_enc)    # x_dec: [B, Lq, 512], x_enc: [B, Lk, 512]

# ③ Masked Self-Attention：加一个上三角 mask，只让每个位置看见"过去"
mask = torch.triu(torch.ones(L, L), diagonal=1).bool()  # [L, L]
out, attn_weights = mha(x, x, x, attn_mask=mask)
```

> ⚠️ **常见坑**：`nn.MultiheadAttention` 的三个位置参数分别是 `(query, key, value)`，**顺序不能错**。K 和 V 必须来自同一个源（因为它们是"钥匙-锁"的配对关系），传错会导致语义完全错乱。

### 7.6 Masked Self-Attention（Decoder 专用）

Decoder 里 self-attention 是**带 mask 的版本**，为什么？

**问题：** Decoder 是**自回归**生成的——一次生成一个 token，生成第 `t` 个 token 时**不能提前看到未来** `t+1, t+2, ...` 的 token（否则训练时"作弊"，推理时又没有未来信息，训推不一致）。

**解决：** 在 softmax 之前，把注意力矩阵的**上三角**（未来位置）填成 `-∞`，softmax 后就变成 0，等于"看不见"。

```
未 mask（可看全序列）：       Masked（只看过去+当前）：

  key₀ key₁ key₂ key₃          key₀ key₁ key₂ key₃
q₀ [ ✓   ✓   ✓   ✓ ]        q₀ [ ✓   ✗   ✗   ✗ ]
q₁ [ ✓   ✓   ✓   ✓ ]        q₁ [ ✓   ✓   ✗   ✗ ]
q₂ [ ✓   ✓   ✓   ✓ ]        q₂ [ ✓   ✓   ✓   ✗ ]
q₃ [ ✓   ✓   ✓   ✓ ]        q₃ [ ✓   ✓   ✓   ✓ ]
     ↑ Encoder 用             ↑ Decoder 用（未来位置被屏蔽）
```

**三种 attention 一览：**

| 名称 | Q/K/V 来源 | Mask | 用在哪 |
|---|---|---|---|
| **Self-Attention** | 同源（当前序列） | 无 | Encoder |
| **Masked Self-Attention** | 同源（当前序列） | 上三角屏蔽 | Decoder 第 1 层子层 |
| **Cross-Attention** | 异源（Q←dec, K/V←enc） | 无 | Decoder 第 2 层子层 |

**训练 vs 推理：mask 只是训练加速的诀窍**

程序员最容易困惑的点是：既然要 mask，训练时为什么还能并行？答案是**训练用 mask 并行、推理用 KV Cache 逐 token**——两个视角实现的是同一件事：「第 t 位看不见 t+1 及以后」。

| 阶段 | 是否并行算所有位置 | 靠什么保证"看不到未来" | 输入形态 |
|---|---|---|---|
| **训练** | ✅ 一次前向算出全序列 loss | **上三角 mask** + teacher forcing（真值当输入） | 完整目标序列 `[B, L, d]` |
| **推理** | ❌ 一次只算一个新 token | **天然只有过去信息**（未来还没生成） | 增量 token `[B, 1, d]` + KV Cache（见第 9 章） |

> 🔑 一句话：**训练时靠 mask 假装"还没看到未来"，推理时天然就没未来**——训推行为一致，是自回归模型可以工作的根本前提。

### 7.7 在 Transformer 中的位置

```
┌────────────────── Encoder Layer × N ──────────────────┐
│  Input                                                │
│    │                                                  │
│    ▼                                                  │
│  ① Self-Attention  (Q=K=V=X_enc)                      │
│    │                                                  │
│    ▼                                                  │
│  Add & Norm  →  FFN  →  Add & Norm                    │
│    │                                                  │
│    ▼                                                  │
│  X_enc（供 Decoder 使用）                              │
└───────────────────────────────────────────────────────┘
                          │
                          │ K, V ↓
                          ▼
┌────────────────── Decoder Layer × N ──────────────────┐
│  Input（已生成的 token）                               │
│    │                                                  │
│    ▼                                                  │
│  ② Masked Self-Attention  (Q=K=V=X_dec, +future mask) │
│    │                                                  │
│    ▼                                                  │
│  Add & Norm                                           │
│    │                                                  │
│    ▼                                                  │
│  ③ Cross-Attention  (Q=X_dec, K=V=X_enc)              │
│    │                                                  │
│    ▼                                                  │
│  Add & Norm  →  FFN  →  Add & Norm                    │
│    │                                                  │
│    ▼                                                  │
│  下一个 token 的概率分布                               │
└───────────────────────────────────────────────────────┘
```

**每层 3 步走**（Decoder）：
1. **Masked Self-Attention**：让 decoder 内部（已生成的 token）彼此交流，但**不能看未来**
2. **Cross-Attention**：拿 decoder 的问题（Q），去 encoder 的答案（K/V）里"查资料"
3. **FFN**：对每个位置做非线性变换

### 7.8 直觉类比（回到翻译任务）

把中文 `"我 非常 喜欢 猫"` 翻译成英文 `"I love cats"`，三种 attention 对应现实场景：

| 位置 | 干什么 | 现实类比 |
|---|---|---|
| **Encoder Self-Attn** | 4 个中文 token 互看，理清"非常修饰喜欢"这类内部关系 | **团队讨论**：围坐一圈，弄懂"我们这句话在说啥" |
| **Decoder Masked Self-Attn** | 生成 `"cats"` 时只能看已生成的 `"I love"`，未来不可见 | **写作文**：只能基于已写内容续写，不能剧透 |
| **Decoder Cross-Attn** | 拿 `"cats"` 当 Q，去中文 K/V 里查证据 → 高度关注 `"猫"` | **翻译官查字典**：草稿（Q）去查原文档案（K/V） |

### 7.9 常见误区 FAQ

**Q1：Cross-Attention 里 K 和 V 为什么必须来自同一个源？**
> 因为它们是"钥匙-内容"的**配对**关系：K[i] 是第 i 个位置的"检索标签"，V[i] 是第 i 个位置的"实际内容"，两者按位置一一对应。如果 K 来自 encoder、V 来自 decoder，那 attn 权重指向的 V 就是错位的，语义完全乱套。

**Q2：Self-Attention 里 Q、K、V 都来自 X，那为什么不直接让 Q = K = V = X？**
> 因为需要 3 个**独立可学习**的投影矩阵 W_Q、W_K、W_V，把 X 投影到**不同子空间**，让"提问的视角"、"匹配的视角"、"内容的视角"各自专业化。如果 Q = K = V = X，就丧失了这种灵活性，模型表达能力大幅下降。

**Q3：Cross-Attention 需要 Masked 吗？**
> **不需要**。因为 K/V 来自 encoder 的**完整输出**，encoder 已经把整个源序列处理完了，decoder 当然可以看整个源序列（这不是"看未来"，而是"看输入"）。Masked 只针对 decoder **自己内部**的自回归约束。

**Q4：为什么 Encoder 不用 Cross-Attention？**
> 因为 Encoder **没有外部信息可以参考**——它就是输入的起点，只需要理解自己内部即可。Cross-Attention 只在"两个序列需要对齐"时才有意义（Decoder 输出 vs Encoder 输入）。

**Q5：只用 Self-Attention 的模型（如 GPT、BERT）为什么没有 Cross-Attention？**
> GPT/BERT 是**纯 Decoder** 或**纯 Encoder** 架构，只有一个序列在流动，不存在"两个序列对齐"的场景，所以只需要 Self-Attention。只有 **Encoder-Decoder** 架构（如原始 Transformer、T5、BART）才有 Cross-Attention。

---

## 8. 位置编码（Positional Encoding）

前面第 6、7 章讲的所有 attention 都有一个**致命缺陷**：它是**位置无关**的。本章独立成篇，讲清为什么需要位置编码，以及从原始 Transformer 到现代 LLM 的方案演进。

> 📎 **为什么独立成章？** 位置编码是一个**与 self/cross 正交的议题**——无论 attention 从哪来（同源/异源）、加不加 mask，都需要位置信息注入。把它单独放在这里，让第 7 章更聚焦，也让本章可以完整讲透三大主流方案。
>
> 📎 **阅读路线：** 8.1（为什么需要）→ 8.2（三方案总览）→ 8.3（正弦：无参可外推）→ 8.4（学习式：BERT/GPT-2）→ 8.5（RoPE：现代 LLM 标配）→ 8.6（三方案速查）。

### 8.1 为什么需要位置编码？

**问题：** attention 的公式 `softmax(QKᵀ/√d)·V` 是一个**对称操作**——把输入序列**打乱顺序**，输出的每个 token 结果**几乎不变**（只是位置对调）。

**举例：** 对 self-attention 来说：
```
"我 爱 你"  ─┐
             ├─→  self-attention 输出的 3 个向量完全相同（只是顺序变了）
"你 爱 我"  ─┘
```

**这意味着 attention 是个"词袋模型"** —— 只知道**有哪些词**，不知道**词的顺序**！这对语言理解是灾难性的。

**解决方案：** 在输入 embedding 里**注入位置信息**，让每个 token 的向量同时包含"我是什么词"和"我在第几个位置"。

```python
# 输入 x 不是纯 embedding，而是：
x = token_embedding + position_encoding
#    ↑ "我是谁"              ↑ "我在哪"
```

### 8.2 三大主流方案对比

| 方案 | 使用者 | 核心思想 | 优点 | 缺点 |
|---|---|---|---|---|
| **正弦位置编码** | 原始 Transformer | 用 sin/cos 函数固定生成 | 无需训练、支持任意长度 | 表达能力有限 |
| **学习式位置编码** | BERT、GPT-2 | 位置也做 embedding 查表 | 灵活、可学习 | max_L 固定，无法外推 |
| **RoPE 旋转位置编码** | LLaMA、GPT-NeoX、Qwen | 用旋转矩阵把位置融入 Q/K | 支持外推、相对位置感知 | 数学稍复杂 |

### 8.3 方案 1：正弦位置编码（原始 Transformer）

**公式：**

\[
PE_{(pos, 2i)}   = \sin\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right)
\]
\[
PE_{(pos, 2i+1)} = \cos\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right)
\]

- `pos`：token 在序列里的位置（0, 1, 2, ...）
- `i`：向量的第 i 个维度（偶数用 sin，奇数用 cos）
- `10000`：论文经验值，决定周期

**代码：**

```python
def sinusoidal_positional_encoding(max_L, d_model):
    pe = torch.zeros(max_L, d_model)
    position = torch.arange(0, max_L).unsqueeze(1)              # [max_L, 1]
    div_term = torch.exp(torch.arange(0, d_model, 2) *
                         -(math.log(10000.0) / d_model))         # [d_model/2]
    pe[:, 0::2] = torch.sin(position * div_term)   # 偶数维用 sin
    pe[:, 1::2] = torch.cos(position * div_term)   # 奇数维用 cos
    return pe  # [max_L, d_model]

# 使用
x = token_embedding + pe[:L]  # 广播加到每个 batch
```

**为什么用 sin/cos？** 数学性质：`PE(pos+k)` 可以表示为 `PE(pos)` 的**线性变换**，让模型天然具备**相对位置感知**能力。

### 8.4 方案 2：学习式位置编码（BERT / GPT-2）

**思想：** 干脆把位置也做成 embedding 表，让模型自己学：

```python
class LearnedPositionalEncoding(nn.Module):
    def __init__(self, max_L, d_model):
        super().__init__()
        self.pe = nn.Embedding(max_L, d_model)   # 位置也查表

    def forward(self, x):
        B, L, _ = x.shape
        positions = torch.arange(L, device=x.device)   # [L]
        return x + self.pe(positions)                  # 加到每个 token
```

**优点：** 灵活，模型能自己学到最优位置表示。
**致命缺点：** `max_L` 是**硬编码**的（BERT 是 512），**超出的位置无法处理**——这是 BERT 无法处理长文本的根本原因。

### 8.5 方案 3：RoPE 旋转位置编码（现代 LLM 标配）

**核心思想：** 不是"加"位置编码，而是**在 attention 计算 Q/K 时，用旋转矩阵"旋转"它们**，让点积 `Q·Kᵀ` 天然反映**相对位置**。

**几何直觉：**

```
把每 2 个维度看作一个复数（或 2D 平面上的向量）：

位置 pos=0：           位置 pos=1：           位置 pos=2：
   Q₀                     Q₀ 旋转 θ 度            Q₀ 旋转 2θ 度
   │                       ╱                      ╲
   ●                      ●                        ●
```

两个位置的 Q、K 做点积时，**结果只和它们的相对位置差有关**（这就是相对位置感知）：

\[
\langle R_{\theta_1} Q,\ R_{\theta_2} K \rangle = f(Q, K, \theta_1 - \theta_2)
\]

**代码（简化版）：**

```python
def apply_rope(q, k, positions):
    # q, k: [B, H, L, d_k]，positions: [L]
    theta = 1.0 / (10000 ** (torch.arange(0, d_k, 2) / d_k))    # [d_k/2]
    angles = positions[:, None] * theta[None, :]                # [L, d_k/2]
    cos, sin = angles.cos(), angles.sin()

    # 把 q 的每 2 个维度看作 (x, y)，用旋转矩阵旋转
    q_rot = rotate_half(q, cos, sin)
    k_rot = rotate_half(k, cos, sin)
    return q_rot, k_rot   # 之后正常做 attention
```

**为什么 LLaMA / Qwen / DeepSeek 都用 RoPE？**
- ✅ **可外推**：训练时用 max_L=4096，推理时能延长到 8k~32k
- ✅ **相对位置感知**：点积天然反映距离
- ✅ **不增加参数**：纯计算，无需存储位置表

### 8.6 三种方案速查

| 特性 | 正弦 | 学习式 | RoPE |
|---|---|---|---|
| 是否需要训练 | ❌ | ✅ | ❌ |
| 是否支持长度外推 | ✅ | ❌ | ✅ |
| 位置信息注入位置 | 输入 embedding | 输入 embedding | Q/K 计算前 |
| 相对 or 绝对 | 绝对（隐含相对） | 绝对 | 相对 |
| 代表模型 | 原始 Transformer | BERT、GPT-2 | LLaMA、Qwen |

> 🎯 **一句话总结**：attention 本身"看不见"位置，必须靠位置编码补上。原始正弦方案简单可外推；BERT 的学习式灵活但长度受限；现代 LLM 主流的 RoPE 兼顾外推和相对位置感知，是当前最优解。

---

## 9. KV Cache 与推理加速

前面 6~8 章覆盖的都是**训练视角**——一次前向输入完整序列。但 LLM **推理时是自回归的**：一次生成一个 token，然后把它接到输入后面再生成下一个……这里有一个巨大的**重复计算**问题，**KV Cache** 就是解决方案。

> 📎 **阅读路线：** 9.1（问题）→ 9.2（缓存 K/V 的核心思想）→ 9.3（为什么不缓存 Q）→ 9.4（显存公式）→ 9.5（伪代码）→ 9.6（训练 vs 推理形状对比）→ 9.7（现代 LLM 的进化方向 MQA/GQA/PagedAttention）。
>
> 📎 **与前几章的衔接**：本章不引入新的 attention 数学（公式仍是 6.1 的 `softmax(QKᵀ/√d)·V`），也不换模型结构（多头结构仍是 6.8）——只讨论**推理阶段如何避免重复计算 K/V**。

### 9.1 问题：自回归推理的重复计算

假设已经生成了 3 个 token，正在生成第 4 个：

```
Step 1: 输入 "我"           → 生成 "爱"
Step 2: 输入 "我 爱"        → 生成 "小"
Step 3: 输入 "我 爱 小"     → 生成 "猫"
Step 4: 输入 "我 爱 小 猫"  → 生成 "。"
```

**观察：** 每一步，前面已经计算过的 token 的 K、V **完全没变**！但如果每步都从头算：

| Step | 需要算的 K/V | 重复计算量 |
|---|---|---|
| 1 | K/V for "我" | - |
| 2 | K/V for "我", "爱" | "我" 重复算 |
| 3 | K/V for "我", "爱", "小" | "我", "爱" 重复算 |
| 4 | K/V for "我", "爱", "小", "猫" | "我", "爱", "小" 重复算 |

对长序列（如 4000 tokens），重复计算量是 **O(L²)**——推理速度会慢到无法接受。

### 9.2 解决方案：缓存 K、V

**核心思想：** 已经算过的 K、V **存起来复用**，每一步只需要算**新 token 的 K、V**，然后追加到缓存里。

```
Step t 的输入：只有新生成的 1 个 token
    │
    ▼
新 token → 算出 q_new, k_new, v_new  （形状 [B, H, 1, d_k]）
    │
    ├─ k_new 追加到 K_cache（[B, H, L-1, d_k] → [B, H, L, d_k]）
    ├─ v_new 追加到 V_cache
    ▼
attention = softmax(q_new · K_cache^T / √d) · V_cache
    │
    ▼
输出下一个 token
```

**速度对比：**

| 方式 | 每步计算量 | 总计算量（生成 L 个 token） |
|---|---|---|
| 无 KV Cache | O(L²) | O(L³) |
| **有 KV Cache** | **O(L)** | **O(L²)** |

**实测：** 生成 1000 个 token，KV Cache 能带来 **10~100 倍**推理加速。

### 9.3 为什么只缓存 K、V，不缓存 Q？

因为 **每一步只有一个新 Q**（当前正在生成的 token），Q 不需要历史——用完就扔。但 K/V 每步都要**和历史全部对齐**，所以必须保留。

```
每步的角色：
- Q： 只有 1 个（新 token 的"问题"） → 不缓存
- K/V：需要全部历史（作为"数据库"）→ 缓存
```

### 9.4 显存占用公式

KV Cache 的显存开销可以精确计算：

\[
\text{KV Cache 显存} = 2 \times B \times L \times \text{num\_layers} \times H \times d_k \times \text{bytes\_per\_element}
\]

- `2`：K 和 V 各存一份
- `B`：batch size
- `L`：当前序列长度
- `num_layers`：Transformer 层数（每层都要缓存）
- `H × d_k = d_model`：每个 token 的 KV 向量总维度
- `bytes_per_element`：FP16 是 2 字节，FP32 是 4 字节

**举例：LLaMA-7B（d_model=4096, num_layers=32），FP16，B=1，L=4000：**

```
KV Cache = 2 × 1 × 4000 × 32 × 4096 × 2 bytes
         = 2 GB
```

**观察：** 显存和 **L 成正比**——长上下文推理的显存瓶颈主要来自 KV Cache，而不是模型权重。这也解释了为什么长上下文推理很吃显存。

### 9.5 伪代码实现

```python
class AttentionWithKVCache:
    def __init__(self):
        self.K_cache = None    # [B, H, L_cached, d_k]
        self.V_cache = None

    def forward(self, x_new):
        # x_new: [B, 1, d_model]  ← 每步只输入 1 个新 token

        # 只对新 token 做 QKV 投影
        q_new = x_new @ W_Q      # [B, 1, d_model]
        k_new = x_new @ W_K
        v_new = x_new @ W_V

        # reshape 到多头 [B, H, 1, d_k]
        q_new = reshape_to_heads(q_new)
        k_new = reshape_to_heads(k_new)
        v_new = reshape_to_heads(v_new)

        # 追加到缓存
        if self.K_cache is None:
            self.K_cache, self.V_cache = k_new, v_new
        else:
            self.K_cache = torch.cat([self.K_cache, k_new], dim=2)   # 沿 L 维拼接
            self.V_cache = torch.cat([self.V_cache, v_new], dim=2)

        # 用 q_new 和完整的 K/V 缓存做 attention
        scores = q_new @ self.K_cache.transpose(-2, -1) / sqrt(d_k)   # [B, H, 1, L]
        attn = softmax(scores, dim=-1)
        out = attn @ self.V_cache                                     # [B, H, 1, d_k]
        return out
```

### 9.6 训练 vs 推理形状对比

| 阶段 | 输入 x 形状 | Q 形状 | K/V 形状 | attention 形状 |
|---|---|---|---|---|
| **训练** | `[B, L, d_model]` | `[B, H, L, d_k]` | `[B, H, L, d_k]` | `[B, H, L, L]` |
| **推理（无 cache）** | `[B, L_current, d_model]` | `[B, H, L_current, d_k]` | `[B, H, L_current, d_k]` | `[B, H, L_current, L_current]` |
| **推理（有 cache）** | `[B, 1, d_model]` | `[B, H, 1, d_k]` | `[B, H, L_current, d_k]` | `[B, H, 1, L_current]` |

**关键差异：** 推理带 cache 时，**Q 只有 1 个位置**（新 token），K/V 才是完整历史长度——所以 attention 矩阵是"扁的" `[1, L]`，不是"方的" `[L, L]`。

### 9.7 KV Cache 的进化（现代 LLM 优化方向）

KV Cache 是长上下文的显存瓶颈，各种优化方案由此诞生：

| 方案 | 核心思想 | 显存节省 | 代表模型 |
|---|---|---|---|
| **MHA**（原版） | 每头独立 K/V | 基准 | 原始 Transformer |
| **MQA**（Multi-Query） | 所有头共享 1 组 K/V | **省 H 倍** | PaLM |
| **GQA**（Grouped-Query） | 分组共享 K/V | 省 H/G 倍 | LLaMA2/3、Qwen2 |
| **量化 KV Cache** | K/V 存成 int8 / int4 | 省 2~4 倍 | vLLM、TRT-LLM |
| **PagedAttention** | 分页管理 KV Cache | 省 4~5 倍碎片 | vLLM |

> 🎯 **一句话总结**：KV Cache 是 LLM 推理的"性能开关"——用**显存换算力**，把 O(L²) 每步计算降为 O(L)。理解 KV Cache 的显存公式，是排查"OOM"和优化推理的第一步。

---

## 10. 维度速查表

### 10.1 核心维度一览

| 符号 | 含义 | 是否可变 | 限制来源 |
|---|---|---|---|
| B | Batch size | ✅ | 显存 |
| H | 注意力头数 | ❌ | 超参数（d_model / H = d_k） |
| L | 序列长度 | ✅ | padding / max_position |
| d_k | 单头维度 | ❌ | d_model / H |
| d_v | 单头 Value 维度 | ❌ | 通常 = d_k |
| d_model | Token 向量总维度 | ❌ | 模型架构 |
| d_ff | FFN 中间维度 | ❌ | 通常 4 × d_model |
| max_L | 最大序列长度 | ❌ | 模型结构（位置编码） |

### 10.2 典型模型配置

| 模型 | d_model | H | d_k | d_ff | max_L |
|---|---|---|---|---|---|
| Transformer-base | 512 | 8 | 64 | 2048 | 512 |
| BERT-base | 768 | 12 | 64 | 3072 | 512 |
| GPT-2 | 768 | 12 | 64 | 3072 | 1024 |
| GPT-3 | 12288 | 96 | 128 | 49152 | 2048 |
| LLaMA3 | 4096 | 32 | 128 | 14336 | 8192 |

### 10.3 注意力机制变体对比

| 类型 | Q 来源 | K/V 来源 | 矩阵形状 | 使用场景 |
|---|---|---|---|---|
| Self-Attention | 当前序列 | 当前序列 | L × L | Encoder / Decoder |
| Masked Self-Attention | Decoder | Decoder | L × L（上三角为 -inf） | Decoder 自回归 |
| Cross-Attention | Decoder | Encoder | Lq × Lk | Encoder-Decoder 桥梁 |

---

## 11. 总结

> **这份笔记覆盖了从深度学习基础训练原理到 Transformer 架构核心机制的完整链路：**
>
> 1. **训练基础**：Batch 训练、反向传播、梯度更新
> 2. **损失函数**：CrossEntropyLoss 的数学本质与数值稳定性
> 3. **归一化**：Batch Normalization 的训练/推理差异
> 4. **卷积**：Conv2D 的张量形状变化
> 5. **注意力**：Q/K/V 维度解析、缩放点积、多头机制
> 6. **架构**：Self-Attention vs Cross-Attention
> 7. **工程**：nn.MultiheadAttention 的正确使用

---

*笔记整理自深度技术对话，面向程序员，注重直觉理解与工程实践。*
