---
tags:
  - mathematics
  - euler-identity
  - complex-analysis
aliases:
  - 欧拉恒等式
  - e的负iπ次方
created: 2026-06-20
updated: 2026-06-20
---

# 欧拉公式与 $e^{-i\pi}$

---

## 一、欧拉公式

$$
e^{i\theta} = \cos\theta + i\sin\theta
$$

当 $\theta = \pi$ 时，得欧拉恒等式：

$$
e^{i\pi} = \cos\pi + i\sin\pi = -1 + i \cdot 0 = -1
$$

即著名的 **$e^{i\pi} + 1 = 0$**。

---

## 二、$e^{-i\pi}$ 的计算

### 方法一：直接代入欧拉公式

$$
\begin{aligned}
e^{-i\theta} &= \cos(-\theta) + i\sin(-\theta) \\
&= \cos\theta - i\sin\theta \quad (\cos \text{偶函数}, \sin \text{奇函数})
\end{aligned}
$$

代入 $\theta = \pi$：

$$
e^{-i\pi} = \cos\pi - i\sin\pi = -1 - i \cdot 0 = -1
$$

### 方法二：共轭关系

$e^{i\pi} = -1$ 是实数，实数的共轭为其自身：

$$
e^{-i\pi} = \overline{e^{i\pi}} = \overline{-1} = -1
$$

### 方法三：倒数关系

$$
e^{-i\pi} = \frac{1}{e^{i\pi}} = \frac{1}{-1} = -1
$$

### 方法四：复平面几何意义

$e^{i\theta}$ 对应单位圆上角度为 $\theta$ 的点。$\theta = \pi$（逆时针）与 $\theta = -\pi$（顺时针）都指向 $(-1, 0)$。

### 方法五：泰勒展开

$$
e^{-i\pi} = 1 - i\pi - \frac{\pi^2}{2!} + \frac{i\pi^3}{3!} + \frac{\pi^4}{4!} - \cdots
$$

- 实部：$1 - \frac{\pi^2}{2!} + \frac{\pi^4}{4!} - \cdots = \cos\pi = -1$
- 虚部：$-\pi + \frac{\pi^3}{3!} - \frac{\pi^5}{5!} + \cdots = -\sin\pi = 0$

结果：$-1 + 0i = -1$。

---

## 三、结论

$$
\boxed{e^{-i\pi} = -1}
$$

无论 $e^{i\pi}$ 还是 $e^{-i\pi}$，结果均为 $-1$。这是因为在复平面上，正负 $\pi$ 角度都旋转到同一个点 $(-1, 0)$。

---

> [!note] 相关文档
> - [[DFT与FFT蝶形运算详解]] — 旋转因子的数学基础及其在 FFT 中的应用
