---
tags:
  - analog-ic
  - ai
  - eda
  - pyspice
  - bayesian-optimization
  - ltspice
  - ngspice
aliases:
  - AI辅助模拟电路设计
  - PySpice自动Sizing
created: 2026-06-20
---

# AI 辅助模拟电路设计

---

## 一、AI × 模拟电路的四个融合层次

| 融合层面 | 做什么 | 成熟度 |
|:---|:---|:---|
| EDA 智能优化 | 自动 sizing / bias / layout | ⭐⭐⭐⭐ 商用化中 |
| 仿真加速 | NN surrogate 替 SPICE | ⭐⭐⭐ 研究+试用 |
| 拓扑生成 | Spec → OTA/OpAmp 自动生成 | ⭐⭐ 学术为主 |
| 模拟 AI 芯片 | 存算一体 / SNN / crossbar | ⭐⭐⭐ 前沿产品化 |

---

## 二、层次一：AI 辅助模拟电路设计（最成熟）

### 2.1 参数自动调优（Sizing / Biasing）

模拟设计最痛点：手调 MOS 尺寸 (W/L)、偏置电流、负载电容……

AI/ML 做法：
- 把晶体管尺寸 → 连续/离散优化问题
- 用 Bayesian Optimization / RL / GA + NN surrogate 搜索满足：
  - 增益 / bandwidth / slew rate / PSRR / noise / power
- 比手工 sweep 快几倍～几十倍

工业/学术案例：
- Cadence Virtuoso AI-assisted sizing
- Stanford DASS / Berkeley Agera
- 用 GNN 预测 circuit performance → 反向搜索 sizing

### 2.2 版图 / 匹配 / 对称性检查

- CNN/GNN 学已有高质量模拟版图
- 自动建议：共质心 layout、dummy fill、guard ring
- DRC/LVS 违例预测（减少反复提取）

---

## 三、层次二：AI 建模仿真加速（替代 SPICE）

### 3.1 行为级模型替代（Surrogate Model）

- 用 NN（MLP / Siren / PINN）拟合：
  - I-V 特性
  - 小信号参数（gm/gds/Cgg）
  - 温度 / process corner 变化
- 训练数据来自 Spectre/HSPICE 少量采样

用途：系统级 top-level 快速仿真、Monte-Carlo yield 预估

> ⚠️ 不能替代 sign-off SPICE，只做 early-stage / co-sim

### 3.2 时域加速（Time-Step Prediction）

- LSTM / Neural ODE 学微分方程解轨迹
- 对 LDO、PLL、ADC 行为级建模有效

---

## 四、层次三：AI-Driven 电路拓扑生成（早期研究）

> "给定 Spec → 自动生成模拟电路拓扑"

目前仍偏学术，但已有成果：
- Graph Neural Network + RL
  - 节点 = 器件（MOS/R/C/L）
  - 边 = 连接
  - Reward = 是否满足 spec
- 能生成：OTA、两级运放、简单 bandgap

代表工作：Google/Stanford AnalogNAS、TCAD/DATE/ICCAD 多篇 paper

> ⚠️ 工业上还没完全落地，但 Cadence/Synopsys 在做原型

---

## 五、层次四：AI-Inherent 模拟电路（存算一体/神经形态）

最彻底的融合：不再"用 AI 设计模拟电路"，而是**模拟电路本身就是 AI 计算载体**。

### 5.1 模拟存内计算（Analog In-Memory Computing）

- 利用欧姆定律（$I \propto V \times G$）+ Kirchhoff 电流求和
- 用 Crossbar Array（ReRAM/PCM/SRAM 伪差分）做矩阵乘（MAC）

> 模拟电路 = 神经网络权重物理实现

### 5.2 神经形态 / 脉冲神经网络（SNN）IC

- 用亚阈值 MOS（指数函数近似 neuron）、电容积分 → 膜电位、比较器 → spike
- 典型：IBM TrueNorth、Intel Loihi

---

## 六、模拟工程师 AI 入坑路线

> 目标：用 Python + PySpice + Bayesian Optimization 自动找 MOS 尺寸/偏置，满足 Spec

最终能做到：
- 给定一个 OTA/CS Amplifier/LDO 网表
- 给定 Spec（Gain > 60dB, BW > 10MHz, Power < 1mW …）
- **自动跑 SPICE → 提取指标 → BO 搜索最优 W/L/Ibias**

### 6.1 技术栈总览

```
┌──────────────┐
│  ngspice / Spectre (仿真引擎)
├──────────────┤
│  PySpice (Python ⇄ SPICE)
├──────────────┤
│  Python (pandas / numpy / matplotlib)
├──────────────┤
│  Scikit-Optimize (Bayesian Opt)
│  或 Ax / BoTorch / Nevergrad
└──────────────┘
```

### 6.2 Step 1：环境搭建

```bash
# macOS
brew install ngspice

# Python 环境
pip install PySpice scikit-optimize matplotlib
```

> 如果用 Cadence Spectre：可用 `subprocess.call('spectre netlist.scs')`

### 6.3 Step 2：用 PySpice 跑 DC/AC 仿真

```python
import PySpice.Logging.Logging as Logging
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *
import numpy as np

circuit = Circuit('cs_amp')

circuit.V('dd', 'VDD', circuit.gnd, 1.8@u_V)
circuit.I('bias', 'VDD', 'D', 100@u_uA)

circuit.MOSFET('1', 'D', 'G', circuit.gnd, circuit.gnd,
               model='nmos', w=10@u_um, l=0.18@u_um)

circuit.V('in', 'G', circuit.gnd, 0.9@u_V)
circuit.R('load', 'D', 'VDD', 10@u_kΩ)

simulator = circuit.simulator(temperature=27, nominal_temperature=27)
analysis = simulator.dc(Vin=slice(0.8, 1.0, 0.01))

# 简单 gain 估算
Vout = analysis.D.as_ndarray()
Vin  = analysis.Vin.as_ndarray()
gain = -np.gradient(Vout, Vin[1]-Vin[0])
print("Approx Gain:", np.max(np.abs(gain)))
```

学会：动态生成网表、参数化 W/L/Ibias、提取仿真结果到 Python

### 6.4 Step 3：定义代价函数（Cost/Objective）

```python
def evaluate(W, L, Ibias):
    # 1. 生成 netlist
    run_spice(W, L, Ibias)

    # 2. 提取指标
    gain = get_gain_from_raw()
    bw   = get_3db_bw()
    pwr  = get_power()

    # 3. 软约束（越小越好）
    cost = 0
    if gain < 60:
        cost += (60 - gain) * 10
    if bw < 10e6:
        cost += (10e6 - bw) * 1e-6
    cost += pwr * 1e3   # 尽量低功耗

    return cost
```

> 工业工具本质也是：Spec → penalty function → nonlinear optimizer

### 6.5 Step 4：贝叶斯优化搜索尺寸

```python
from skopt import gp_minimize
from skopt.space import Real

space = [
    Real(2e-6, 50e-6, name='W'),       # MOS W
    Real(0.18e-6, 1e-6, name='L'),     # MOS L
    Real(10e-6, 200e-6, name='Ibias')  # bias current
]

res = gp_minimize(
    lambda p: evaluate(*p),
    space,
    n_calls=30,
    random_state=42
)

print("Best W/L/Ibias:", res.x)
print("Best cost:", res.fun)
```

- ✅ 一般 20~50 次 SPICE 调用就能收敛
- ✅ 比 grid search（数千次）快 1~2 个数量级

### 6.6 Step 5：进阶方向

| 方向 | 怎么做 |
|:---|:---|
| 多 Corner | 同时跑 TT/FF/SS/低温/高温 → max penalty |
| Surrogate Model | 先用 DOEs 采样 → 训 NN/GP → BO 用 surrogate 减 SPICE 次数 |
| Yield / Monte-Carlo | 加 mismatch σ → 优化 σ(gain) |
| Topology Search | 不同电路结构 → 不同 netlist template |
| Cadence 联动 | `subprocess.run('spectre')` + Ocean/Python 后处理 |

### 6.7 常见坑

| 坑 | 对策 |
|:---|:---|
| SPICE 不收敛 → BO 炸 | 加 `try/except`：不收敛返回大 penalty |
| W/L 单位 & model 对齐 | 确认 `.lib` 中 MOS model 支持你的 W/L 范围 |
| BO 初始采样太少 | `n_initial_points=5~10` 保底 |
| 不要完全信 BO 结果 | BO 找到的是局部最优满足 penalty，仍需人工 verify phase margin/stability/PSRR |

---

## 七、PySpice vs LTspice 对比

### 7.1 本质区别

| 维度 | LTspice | PySpice |
|:---|:---|:---|
| 是什么 | 独立 SPICE 仿真软件（GUI + 仿真内核） | Python 库，调用 Ngspice/Xyce 引擎 |
| 仿真引擎 | LTspice 私有（很快，SMPS 优化） | Ngspice/Xyce（开源） |
| 原理图绘制 | ✅ 拖放画电路、放探头 | ❌ 无 GUI，需写网表或用 KiCad 导出 |
| 交互仿真 | ✅ 点运行、光标测 gain/phase | ❌ 批处理/脚本驱动 |
| 参数扫描/自动化 | ⚠️ 靠 `.step` + 手动，有限制 | ✅ Python for-loop / BO / ML 原生 |
| 模型库 | ✅ ADI 等厂商模型极丰富 | ⚠️ 需自己挂 `.lib`（Ngspice 兼容） |
| 结果查看 | 内置波形查看器 | Matplotlib / Pandas / NumPy |
| 版控/复现 | 不易（二进制 `.asc`） | ✅ 纯代码，Git 友好 |
| IC PDK 兼容 | ❌ | ⚠️ Ngspice + 自由模型可 |

### 7.2 PySpice 的优势（LTspice 做不到或很弱的）

- 参数自动搜索 / 贝叶斯优化
- 大规模 Monte-Carlo + Python 后处理
- 版本控制、CI/CD、可复现实验
- 与 ML 框架（NumPy/Scikit-learn/BO）直接打通
- Linux headless 服务器批量跑仿真

### 7.3 典型工作流（推荐）

```
日常调试 / 初判拓扑 → LTspice（画、看波形、调 bias）
         ↓
确认拓扑后做 sizing/search/MC → PySpice + Ngspice + Python
         ↓（如需 LTspice 特有模型）
用 PyLTSpice 库调 LTspice CLI 跑批处理
```

> **PySpice 不能完全取代 LTspice**——它们不是同类东西。LTspice = "示波器+面包板"；PySpice = "SPICE + Python 脚本层"。最佳实践是**两者共存**。

---

## 八、Ngspice vs Xyce 引擎介绍

### 8.1 Ngspice

基于 Berkeley SPICE 3f5 演进的开源混合信号仿真器，是 KiCad、Qucs-S 的默认后端。

| 维度 | 说明 |
|:---|:---|
| 来源 | SPICE3f5 + XSpice（行为建模）+ CIDER（器件数值仿真） |
| 分析类型 | DC/AC/TRAN/TF/PZ/失真/瞬态噪声 |
| 器件模型 | 二极管、BJT(VBIC)、MOS(BSIM3/4/SOI)、JFET、Verilog-A（OpenVAF） |
| 混合信号 | XSpice 数字事件驱动，可通过 Verilator/GHDL 做 Verilog/VHDL 协仿 |
| 接口 | `libngspice` 共享库，可被 Python/C/Tcl 嵌入调用（PySpice 工作原理） |
| 平台 | Linux/Windows/macOS（含 Apple Silicon） |

### 8.2 Xyce

美国桑迪亚国家实验室从零用 C++ 重写的 SPICE 兼容大规模并行电路仿真器。

| 维度 | 说明 |
|:---|:---|
| 并行架构 | 原生 MPI + 共享内存并行，可扩展到数十～数百核 |
| 数学内核 | 基于 Trilinos 求解库（KLU、AztecOO），DAE 框架 |
| 高级分析 | + Harmonic Balance (`.HB`)、灵敏度分析、模型降阶（MOR） |
| 模型支持 | SPICE 标准模型 + Verilog-A（ADMS 转 C++）+ 神经元模型 |
| 局限 | 部分 LTspice/PSpice 私有语法不支持；小电路加速不明显 |

### 8.3 对比速览

| 维度 | Ngspice | Xyce |
|:---|:---|:---|
| 代码渊源 | Berkeley SPICE3f5 衍生（C） | 从零 C++ 重写 |
| 并行能力 | 基本单线程 | MPI 大规模并行 |
| 典型用途 | 中小规模模拟/混合信号、教学 | 超大规模电路、Power Grid |
| PySpice 支持 | ✅ 首选后端 | ✅ 支持 |
| 上手难度 | 较低（资料多、KiCad 内置） | 较高（需懂 MPI/并行概念） |

> **Ngspice 够起步；Xyce 是"大规模并行升级选项"。**

---

## 九、一句话总结

> AI × 模拟电路 =
> - **短期**：AI 帮模拟工程师少调管子、快出版图、加速验证
> - **中期**：AI 替代部分手工探索（sizing / topology search）
> - **长期**：模拟电路本身成为 AI 计算单元（存算一体 / 神经形态）
>
> 入坑路线 = SPICE 会跑 → PySpice 参数化 → Python 提指标 → Penalty Function → Bayesian Opt → 自动 sizing。这是模拟工程师用 AI 最立竿见影的第一步。
