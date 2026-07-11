---
tags:
  - statistics
  - t-distribution
  - mutual-information
  - hypothesis-testing
  - kurtosis
  - bayesian-estimation
  - beta-distribution
  - quantile-function
aliases:
  - t分布与t检验
  - 互信息I(X;Y)
  - 样本方差自由度
  - 峰度与偏度
  - 贝叶斯参数估计
  - Beta分布与共轭先验
  - 分位函数
created: 2026-06-20
updated: 2026-06-20
---

# 统计基础：t 分布、峰度、贝叶斯估计与 Beta 分布

---

## 一、样本方差分母为何是 n−1

### 1.1 核心原因：自由度的损失

计算样本方差 $s^2$ 时，必须先求出样本均值 $\bar{x}$。

$$
s^2 = \frac{1}{n-1}\sum_{i=1}^{n}(x_i - \bar{x})^2
$$

由于约束条件 $\sum_{i=1}^{n}(x_i - \bar{x}) = 0$，$n$ 个离差中只有 $n-1$ 个是独立的——知道了其中 $n-1$ 个，最后一个被约束唯一确定。这就是**自由度为 $n-1$** 的直观含义。

### 1.2 无偏性的数学证明

若用 $n$ 做分母：

$$
E\left[\frac{1}{n}\sum_{i=1}^{n}(x_i - \bar{x})^2\right] = \sigma^2 - \frac{\sigma^2}{n} < \sigma^2
$$

**系统性地低估了总体方差**。改用 $n-1$ 后：

$$
E\left[\frac{1}{n-1}\sum_{i=1}^{n}(x_i - \bar{x})^2\right] = \sigma^2
$$

$s^2$ 成为 $\sigma^2$ 的**无偏估计量**。

> [!tip] 直观理解
> 用样本估计方差时需付出 **1 个自由度**的代价。样本量越小，尾部越厚（不确定性越大）。

---

## 二、t 统计量为何服从 $t(n-1)$

### 2.1 t 统计量的构成

$$
t = \frac{\bar{x} - \mu_0}{s / \sqrt{n}}
= \frac{\dfrac{\bar{x} - \mu_0}{\sigma / \sqrt{n}}}{\sqrt{\dfrac{s^2}{\sigma^2}}}
$$

分子：在正态假设下，$\dfrac{\bar{x} - \mu_0}{\sigma / \sqrt{n}} \sim N(0, 1)$

分母：由样本方差的性质

$$
\frac{(n-1)s^2}{\sigma^2} \sim \chi^2(n-1)
$$

因此

$$
\frac{s^2}{\sigma^2} = \frac{\chi^2(n-1)}{n-1}
$$

### 2.2 t 分布定义

若 $Z \sim N(0,1)$，$V \sim \chi^2(k)$ 且 $Z$ 与 $V$ 相互独立，则

$$
T = \frac{Z}{\sqrt{V / k}} \sim t(k)
$$

代入 $k = n-1$，得 $t \sim t(n-1)$。

> [!important] 总结
> 分母 $n-1$ 保证了 $s^2$ 是无偏估计，进而使 $\frac{(n-1)s^2}{\sigma^2}$ 服从 $\chi^2(n-1)$，t 统计量继承该自由度，服从 $t(n-1)$。

---

## 三、t 分布详解

### 3.1 定义

当总体标准差 $\sigma$ 未知且样本较小（通常 $n < 30$）时，标准化样本均值的分布不再是标准正态，而是 **t 分布**。

$$
t = \frac{\bar{X} - \mu}{S / \sqrt{n}}, \quad df = n - 1
$$

其中 $S^2 = \frac{1}{n-1}\sum (X_i - \bar{X})^2$。

### 3.2 关键特征

| 特性 | 说明 |
|:---|:---|
| 形状 | 对称、钟形，比标准正态**尾部更厚**、峰部略低 |
| 自由度效应 | $df$ 越小，尾部越厚；$df \to \infty$ 时，$t$ 分布趋近 $N(0,1)$ |
| 均值 | $0$（$df > 0$） |
| 方差 | $\dfrac{df}{df - 2}$（$df > 2$），大于标准正态的方差 $1$ |

### 3.3 密度函数

$$
f(t) = \frac{\Gamma\left(\frac{df+1}{2}\right)}{\sqrt{df\,\pi}\; \Gamma\left(\frac{df}{2}\right)}
\left(1 + \frac{t^2}{df}\right)^{-\frac{df+1}{2}}
$$

### 3.4 不同自由度的形态

> 图片来源：[Wikipedia - Student's t-distribution](https://en.wikipedia.org/wiki/Student%27s_t-distribution)

![[assets/Student_t_pdf.png]]

图中可见：$df=1$ 时尾部极厚；$df=2, 5$ 逐渐收窄；$df \to \infty$ 时趋近标准正态（黑色虚线）。

### 3.5 核心用途

- **单样本 t 检验**：$H_0: \mu = \mu_0$
- **两独立样本 t 检验**：比较两组均值
- **配对样本 t 检验**：比较配对数据差值
- **总体均值置信区间**：$\bar{X} \pm t_{\alpha/2, df} \cdot \dfrac{S}{\sqrt{n}}$

---

## 四、互信息 $I(X; Y)$

### 4.1 定义

互信息衡量一个随机变量 $Y$ 能提供多少关于另一个随机变量 $X$ 的信息——或者说，**知道 $Y$ 后，$X$ 的不确定性减少了多少**。

$$
I(X; Y) = H(X) - H(X \mid Y)
$$

其中：
- $H(X)$：$X$ 的熵（先验不确定性）
- $H(X \mid Y)$：已知 $Y$ 后 $X$ 的条件熵（剩余不确定性）

### 4.2 公式关系

$$
I(X; Y) = H(X) + H(Y) - H(X, Y)
$$

即独立熵之和减去联合熵。互信息正是熵的 Venn 图中 $X$ 与 $Y$ 的交集部分。

### 4.3 基本性质

| 性质 | 公式 | 含义 |
|:---|:---|:---|
| 对称性 | $I(X; Y) = I(Y; X)$ | $Y$ 提供关于 $X$ 的信息量 = $X$ 提供关于 $Y$ 的信息量 |
| 非负性 | $I(X; Y) \ge 0$ | 知道 $Y$ 不会增加 $X$ 的不确定性 |
| 极值 | $0 \le I(X; Y) \le \min\{H(X), H(Y)\}$ | 互信息不超过任一变量的自有熵 |

### 4.4 如果 $X$ 和 $Y$ 独立

$H(X \mid Y) = H(X)$，故 $I(X; Y) = 0$——$Y$ 没有提供任何关于 $X$ 的信息。

### 4.5 主要应用

| 领域 | 应用 |
|:---|:---|
| 机器学习 | 特征选择：选与目标变量互信息最高的特征 |
| 通信理论 | 信道容量：$C = \max_{p(x)} I(X; Y)$ |
| 数据压缩 | 评估压缩效率：冗余 = $H(X) - I(X; Y)$ |
| 生物信息学 | 基因调控网络推断 |

---

## 五、峰度（Kurtosis）

### 5.1 定义

峰度是描述概率分布**尾部厚重程度**和**峰态陡峭程度**的指标，有两种常见定义：

| 定义 | 公式 | 正态分布值 | 用途 |
|:---|:---|:---|:---|
| **标准峰度**（Excess Kurtosis） | $\displaystyle \frac{\mu_4}{\sigma^4} - 3$ | **0** | 最常用，以正态分布为基准判断厚尾/薄尾 |
| **Pearson 原始峰度** | $\displaystyle \frac{\mu_4}{\sigma^4}$ | **3** | 历史定义，不常见于现代软件 |

其中 $\mu_4 = E[(X - \mu)^4]$ 为四阶中心矩。

### 5.2 判定

- 标准峰度 $> 0$（原始 $\mu_4/\sigma^4 > 3$）：**尖峰、厚尾**——尾部比正态更重，极端值出现概率更高（如金融收益数据）
- 标准峰度 $< 0$（原始 $< 3$）：**低峰、薄尾**——数据更集中于均值附近（如均匀分布）
- 标准峰度 $= 0$：接近正态分布

### 5.3 正态分布原始峰度 = 3 的推导

设 $X \sim N(\mu, \sigma^2)$，证明 $\displaystyle \frac{\mu_4}{\sigma^4} = 3$。

**① 标准化**：令 $Z = \dfrac{X - \mu}{\sigma} \sim N(0,1)$，则需证 $E[Z^4] = 3$。

**② 四阶矩积分**：

$$
E[Z^4] = \frac{1}{\sqrt{2\pi}} \int_{-\infty}^{\infty} z^4 e^{-z^2/2}\, dz
$$

**③ 分部积分**：令 $u = z^3$，$dv = z e^{-z^2/2}\, dz$，则 $v = -e^{-z^2/2}$：

$$
\begin{aligned}
\int z^4 e^{-z^2/2}\, dz &= \left[-z^3 e^{-z^2/2}\right]_{-\infty}^{\infty} + 3\int z^2 e^{-z^2/2}\, dz \\
&= 0 + 3\int z^2 e^{-z^2/2}\, dz
\end{aligned}
$$

（边界项为 0，因指数衰减快于多项式增长）

**④ 递归**：对 $\int z^2 e^{-z^2/2}\, dz$ 再次分部积分：

$$
\int z^2 e^{-z^2/2}\, dz = 0 + \int e^{-z^2/2}\, dz = \sqrt{2\pi}
$$

**⑤ 代回**：

$$
E[Z^4] = \frac{1}{\sqrt{2\pi}} \cdot 3 \cdot \sqrt{2\pi} = 3
$$

**⑥ 一般正态**：

$$
\mu_4 = E[(X - \mu)^4] = E[(\sigma Z)^4] = \sigma^4 \cdot 3 \quad\Rightarrow\quad \frac{\mu_4}{\sigma^4} = 3
$$

### 5.4 偏度 vs 峰度

> [!important] 注意区分
> - **偏度（Skewness）**：$\displaystyle \frac{\mu_3}{\sigma^3}$，衡量分布的**不对称性**。正态分布偏度恒为 **0**。
> - **峰度（Kurtosis）**：$\displaystyle \frac{\mu_4}{\sigma^4}$，衡量分布的**尾部厚重程度**。正态分布原始峰度为 **3**，标准峰度为 **0**。

### 5.5 Python 计算

```python
from scipy.stats import kurtosis
data = [1, 2, 3, 4, 5]
print(kurtosis(data, bias=False))  # 默认输出 Excess Kurtosis（正态=0）
```

---

## 六、贝叶斯参数估计

### 6.1 核心思想

贝叶斯参数估计通过结合**先验知识**和**观测数据**，更新对未知参数的认知，最终得到参数的**后验概率分布**。

> 本质：**用数据更新信念**。仅用概率基本规则，从假设检验到参数估计全部统一。

### 6.2 核心概念

| 概念 | 符号 | 含义 |
|:---|:---|:---|
| **先验概率** | $P(H)$ | 观测数据前对假设 $H$ 的初始信念 |
| **似然函数** | $P(D \mid H)$ | 假设 $H$ 成立时，观测数据 $D$ 出现的概率 |
| **后验概率** | $P(H \mid D)$ | 观测数据后，假设 $H$ 的更新概率 |
| **证据** | $P(D)$ | 数据的总概率，用于归一化：$P(D) = \sum_H P(D \mid H)P(H)$ |

### 6.3 贝叶斯定理

$$
P(H \mid D) = \frac{P(D \mid H) \cdot P(H)}{P(D)}
$$

离散形式：后验 ∝ 似然 × 先验。

### 6.4 实现步骤

1. **定义似然**：计算 $P(D \mid H)$ — "假设成立时，当前数据有多可能"
2. **遍历所有假设**：对参数所有可能取值，计算每个假设下的似然
3. **归一化**：除以总和形成后验分布 $P(H \mid D)$

### 6.5 Beta-Binomial 共轭更新

当先验为 Beta 分布、似然为二项分布时，后验仍然是 Beta 分布——参数直接相加即可：

$$
\text{Beta}(\alpha_{\text{后}}, \beta_{\text{后}}) = \text{Beta}(\alpha_{\text{先}} + \alpha_{\text{似然}}, \; \beta_{\text{先}} + \beta_{\text{似然}})
$$

- $\alpha_{\text{似然}}$：观测数据中成功次数（如正面）
- $\beta_{\text{似然}}$：观测数据中失败次数（如反面）

**例子**：先验 Beta(1,1)（均匀分布），观测 10 正 5 反 → 后验 Beta(11, 6)。

### 6.6 贝叶斯方法优势

| 优势 | 说明 |
|:---|:---|
| 统一框架 | $P(D \mid H)$ → 贝叶斯定理 → 贝叶斯因子 → 参数估计 → 假设检验 |
| 融入先验 | 利用历史信息提升小样本估计稳定性 |
| 直接概率解释 | 后验给出参数的可信区间（如"p 有 95% 概率落在 [0.4, 0.6]"） |

### 6.7 例子：硬币抛掷

- 先验：Beta(2, 2)（弱先验，倾向 0.5）
- 数据：10 次抛掷，6 正 4 反
- 后验：Beta(2+6, 2+4) = Beta(8, 6)
- 后验均值：$\frac{8}{8+6} \approx 0.57$

---

## 七、Beta 分布详解

### 7.1 定义

若随机变量 $X$ 服从参数为 $\alpha, \beta$ 的 Beta 分布，记为 $X \sim \text{Beta}(\alpha, \beta)$，其中 $\alpha > 0, \beta > 0$ 为形状参数。取值范围 $x \in (0, 1)$。

### 7.2 概率密度函数（PDF）

$$
f(x; \alpha, \beta) = \frac{x^{\alpha-1} (1 - x)^{\beta-1}}{B(\alpha, \beta)}, \quad 0 < x < 1
$$

其中 $B(\alpha, \beta)$ 为 Beta 函数：

$$
B(\alpha, \beta) = \int_0^1 t^{\alpha-1} (1-t)^{\beta-1}\, dt = \frac{\Gamma(\alpha)\,\Gamma(\beta)}{\Gamma(\alpha + \beta)}
$$

### 7.3 累积分布函数（CDF）

$$
F(x; \alpha, \beta) = I_x(\alpha, \beta) = \frac{1}{B(\alpha, \beta)} \int_0^x t^{\alpha-1} (1-t)^{\beta-1}\, dt
$$

其中 $I_x(\alpha, \beta)$ 为不完全 Beta 函数，一般通过数值方法计算。

### 7.4 参数含义与形状

| $\alpha, \beta$ 取值 | 分布形状 |
|:---|:---|
| $\alpha > 1, \beta > 1$ | **单峰**，均值附近集中 |
| $\alpha < 1, \beta < 1$ | **U 形**，两端极端值概率高 |
| $\alpha = 1, \beta = 1$ | **均匀分布** $U(0,1)$ |
| $\alpha = \beta$ | 关于 $x = 0.5$ **对称** |
| $\alpha > \beta$ | **右偏**（倾向于较大值） |
| $\alpha < \beta$ | **左偏**（倾向于较小值） |

**参数直观解释**：$\alpha$ 可看作"成功次数 + 1"，$\beta$ 可看作"失败次数 + 1"。

### 7.5 数字特征

$$
E(X) = \frac{\alpha}{\alpha + \beta}, \qquad
\text{Var}(X) = \frac{\alpha\beta}{(\alpha + \beta)^2 (\alpha + \beta + 1)}
$$

### 7.6 关键性质

1. **取值范围固定**：$X \in [0, 1]$，天然适合建模概率、比例
2. **共轭先验性**：二项分布的共轭先验 — 先验 Beta + 二项似然 → 后验仍为 Beta
3. **对称性**：当 $\alpha = \beta$ 时关于 $x = 0.5$ 对称

### 7.7 $\theta$ 的含义

在 Beta 分布的实际应用中，随机变量 $\theta$ 通常表示：

| 解释 | 场景 |
|:---|:---|
| **概率参数** | 硬币正面概率、点击率、次品率 — 作为二项分布的共轭先验 |
| **比例参数** | 市场份额、成分占比（如合金中某金属比例） |

### 7.8 应用场景

| 领域 | 用途 |
|:---|:---|
| **贝叶斯推断** | 二项分布参数的先验/后验分布 |
| **项目管理** | 任务完成时间估算（介于最早和最晚之间） |
| **机器学习** | 朴素贝叶斯分类器中的概率建模 |

### 7.9 Python 示例

```python
import numpy as np
from scipy.stats import beta
import matplotlib.pyplot as plt

alpha, beta_param = 2, 5
samples = beta.rvs(alpha, beta_param, size=1000)
x = np.linspace(0, 1, 100)
pdf = beta.pdf(x, alpha, beta_param)

plt.plot(x, pdf, 'r-', lw=2, label='Beta PDF')
plt.hist(samples, bins=30, density=True, alpha=0.2, label='Samples')
plt.title(f'Beta Distribution (α={alpha}, β={beta_param})')
plt.xlabel('x'); plt.ylabel('Probability Density')
plt.legend(); plt.show()

print(f"Mean: {beta.mean(alpha, beta_param)}")
print(f"Variance: {beta.var(alpha, beta_param)}")
```

---

## 八、贝叶斯公式中的先验-似然-后验串联

### 8.1 二项分布的似然函数

$n$ 次伯努利试验，成功 $k$ 次，似然为：

$$
L(\theta \mid k, n) \propto \theta^{\,k}\, (1 - \theta)^{\,n - k}
$$

### 8.2 Beta 先验与后验更新推导

先验：$p(\theta \mid \alpha, \beta) \propto \theta^{\alpha-1}(1 - \theta)^{\beta-1}$

根据贝叶斯定理：

$$
\begin{aligned}
p(\theta \mid k, n) &\propto p(\theta \mid \alpha, \beta) \cdot L(\theta \mid k, n) \\
&\propto \theta^{\alpha-1}(1 - \theta)^{\beta-1} \cdot \theta^{k}(1 - \theta)^{n-k} \\
&= \theta^{\alpha + k - 1}(1 - \theta)^{\beta + n - k - 1}
\end{aligned}
$$

这正是 $\text{Beta}(\alpha + k,\; \beta + n - k)$ 的核。完整归一化形式：

$$
p(\theta \mid k, n) = \frac{\theta^{\alpha + k - 1}(1 - \theta)^{\beta + n - k - 1}}{B(\alpha + k,\; \beta + n - k)}
$$

### 8.3 组合数公式

组合数 $C(n, k)$ 表示从 $n$ 个不同元素中取 $k$ 个的方案数：

$$
C(n, k) = \frac{n!}{k!\,(n - k)!}
$$

**推导**：排列数 $A(n, k) = \frac{n!}{(n - k)!}$，每个组合可产生 $k!$ 种排列，故 $A(n, k) = C(n, k) \times k!$，得证。

---

## 九、分位函数（Quantile Function）

### 9.1 定义

给定 CDF $F(x)$，分位函数 $Q(p)$ 是其反函数：

$$
Q(p) = F^{-1}(p) = \inf\{x \in \mathbb{R} \mid F(x) \ge p\}, \quad p \in [0, 1]
$$

通俗理解："在概率 $p$ 下，随机变量 $X$ 的值不超过多少？"

### 9.2 与 CDF 的关系

| 函数 | 输入 | 输出 | 含义 |
|:---|:---|:---|:---|
| CDF $F(x)$ | $x$ 值 | 概率 $p$ | $P(X \le x) = p$ |
| 分位函数 $Q(p)$ | 概率 $p$ | $x$ 值 | $P(X \le Q(p)) = p$ |

数学关系：$F(Q(p)) = p$，$Q(F(x)) = x$。

### 9.3 常见分布的分位函数

| 分布 | $Q(p)$ |
|:---|:---|
| 均匀分布 $U(a, b)$ | $a + p(b - a)$ |
| 指数分布 $\text{Exp}(\lambda)$ | $-\dfrac{\ln(1 - p)}{\lambda}$ |
| 正态分布 $N(\mu, \sigma^2)$ | 数值计算，$Q(0.5) = \mu$，$Q(0.975) \approx \mu + 1.96\sigma$ |
| Beta 分布 $\text{Beta}(\alpha, \beta)$ | 数值计算（如 $\text{Beta}(2,5)$ 中位数 $Q(0.5) \approx 0.285$） |

### 9.4 应用

| 领域 | 用途 |
|:---|:---|
| **风险管理** | VaR（风险价值）：$\text{VaR}_\alpha = Q(1 - \alpha)$ |
| **假设检验** | 临界值计算：$Q(0.95)$ 用于单侧检验 |
| **随机数生成** | 逆变换采样：$X = Q(U)$，$U \sim U(0,1)$ |
| **机器学习** | 分位数回归：直接建模条件分位函数 |

### 9.5 Python 示例

```python
from scipy.stats import norm, beta

# 标准正态 Q(0.95) = 1.645
q_norm = norm.ppf(0.95)

# Beta(2,5) 中位数
q_beta = beta.ppf(0.5, a=2, b=5)  # ≈ 0.285

# 逆变换采样
import numpy as np
lambda_ = 1.0
U = np.random.rand(1000)
X = -np.log(1 - U) / lambda_  # 指数分布 Exp(1)
```

---

> [!note] 下一篇
> 统计推断的其他分布（F 分布、$\chi^2$ 分布）可后续补充。
