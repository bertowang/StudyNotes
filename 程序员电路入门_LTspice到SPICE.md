---
tags:
  - ltspice
  - spice
  - circuit
  - learning
  - beginner
aliases:
  - 程序员电路入门
  - LTspice速通清单
  - 标准SPICE指南
created: 2026-06-20
---

# 程序员电路入门：从 LTspice 到标准 SPICE

---

## 一、工具选择：LTspice 还是 PySpice？

> **首选 LTspice**，把 PySpice(Ngspice) 作为第二步工具，而非第一步替代品。

### 为什么不是直接上 PySpice？

PySpice 是写网表 + 调仿真引擎，前提是你要：
- 懂 SPICE 网表语法（`M1 D G S B nmos W= L=...`）
- 知道该跑 `.op`/`.dc`/`.ac`/`.tran`
- 知道怎么从波形判断放大、相位裕度等

没有电路直觉时，PySpice 会让你同时学"模拟电路 + SPICE 网表 + Python 封装"，挫败感很强。

### 推荐三阶段路线

```
Phase 1: LTspice 建立电路直觉（1~2周）
   ↓
Phase 2: 读 LTspice 生成的 .cir 网表
   ↓
Phase 3: PySpice + Ngspice 自动化 / AI Sizing
```

> LTspice = "示波器 + 面包板"，教你"电路长什么样"
> PySpice = 教你"让计算机帮你找参数"

---

## 二、Phase 1：LTspice 程序员速通 · 10 个 Mini 实验

### 实验目标

每个实验：搭电路 → 跑仿真 → 用鼠标量 → 解释为什么

> 不背公式，看波形验证脑子里"代码一样的因果逻辑"

### ① NMOS IV 曲线（Id ~ Vds / Vgs）

```
Vds: 0→5V sweep
Vgs: 0/1/2/3V step
NMOS (W=10u L=0.18u)
源接地，漏串 Vds
```

- `.dc Vds 0 5 0.05 Vgs 0 3 1`
- 观察：Vgs<Vth → 截止；Vds 小 → 线性区（电阻）；Vds 大 → 饱和（Id≈const）
- 🧠 这就是 `if(Vgs>Vth && Vds>(Vgs-Vth)) then saturation`

### ② PMOS IV 曲线（对称理解）

同理，源接 VDD，Vsg sweep。确认 PMOS 镜像对称、电流方向相反

### ③ 电阻分压 + Thevenin 直觉

```
VDD─R1─┬─R2─GND
       └─Vout
```

- `.op` 看 Vout
- 改 R1/R2 → 验证 $V_{out} = V_{DD} \cdot R_2/(R_1+R_2)$
- ✅ 为偏置电路打底

### ④ 电流镜（基本 Iref → Icopy）

```
Iref 恒流 → NMOS1(D=G) → NMOS2(G 相连, S 接地)
```

- `.dc Iref 1u 100u 1u`
- 看 Icopy vs Iref
- ✅ 理解：W/L 比例 = 电流比例

### ⑤ Common Source（CS）放大器 — DC 工作点

```
VDD ─ load(R or PMOS load)
       └─ Drain ← NMOS
          Gate ← Vbias
          Source ─ GND
```

- `.op` 确认 $V_d \approx V_{DD}/2$（最大摆幅）
- 调 Vbias/W/L 使进入饱和
- ✅ 这是"初始化变量"的感觉

### ⑥ CS 放大器 — 小信号 Gain（.AC）

- 输入加 `ac 1`
- `.ac dec 100 1 100Meg`
- 看 `dB(V(D))`
- ✅ 确认：中频增益 $\approx -g_m \cdot (r_o \| R_{load})$，高频滚降（密勒效应）
- 🧠 第一次看到增益是频率函数

### ⑦ CS + 源极负反馈电阻（Gain ↔ Linearity）

- 加 Re 到 source（旁路或未旁路）
- ✅ 未旁路 → gain↓ 但线性↑
- ✅ 并 C 旁路 → 低频 gain↓，高频恢复原 gain
- 👉 理解反馈 trade-off

### ⑧ 差分对（长尾电流源）

```
Vin+ ─┬─M1─┐
       │   ├─ Iss ─ GND
Vin- ─┬─M2─┘
```

- `.dc Vin+ 0 1.8 0.01 Vin- = 0.9`
- 看 $V(D_1)-V(D_2)$ 转移曲线
- ✅ 确认：差分跨导区 ≈ ±100mV，尾电流决定线性范围

### ⑨ 运放 + 反馈（闭环 Step Response）

- 用简并 OTA（差分对 + current mirror load）
- 接负反馈 R1/R2（$\beta = R_2/(R_1+R_2)$）
- `.tran 0 1u`，输入加 100mV step
- ✅ 看：稳定 / 过冲 / 振铃；改变补偿电容 Cc → 影响稳定

### ⑩ 相位 Margin（开环 AC 断环法）

- 断环路、加 large L/C 维持 DC、注入 ac
- `.ac dec 100 1 100Meg`
- 看 loop gain $T(j\omega) = V_{fb\_inj} / V_{inj}$
- 光标读：Unity Gain Frequency (UGF)、Phase Margin = 180° + phase@UGF

> ✅ PM < 45° → 过冲明显
> ✅ Cc ↑ → PM ↑，GBW ↓
> 🎯 这是模拟设计核心 KPI

### 完成后的能力映射

| 概念 | 来源 |
|:---|:---|
| MOS 截止/线性/饱和 | ① ② |
| 偏置 & 电流镜 | ④ ⑤ |
| 小信号 gain / -3dB | ⑥ |
| 负反馈 & 稳定性 | ⑨ ⑩ |
| 差分对 & CMRR 直觉 | ⑧ |
| 补偿电容 ↔ PM | ⑩ |

---

## 三、LTspice 文件后缀全解析

### 3.1 文件关系总览

```
┌──────────────┐
│  .asc  原理图（LTspice 私有）        ← 你画电路的地方
├──────────────┤
│  .cir  SPICE 网表（标准 SPICE 文本） ← 仿真器真正吃的东西
├──────────────┤
│  .model  单器件模型（通常嵌在 .lib）
│  .lib   模型/子电路库（标准 SPICE）
└──────────────┘
```

### 3.2 `.asc` — LTspice 原理图文件

- LTspice 专有二进制+文本混合格式
- 保存：元件位置、连线、参数（W/L、R值等）、仿真命令、关联 `.lib`/`.model` 调用
- **仿真器不直接读 `.asc`**：LTspice 内部把 `.asc` → 临时 `.cir`（网表） → 送给 SPICE 引擎
- ❌ 不可被 Ngspice/PySpice 直接使用（需导出 `.cir`）
- 查看生成网表：`View → SPICE Netlist`

### 3.3 `.cir` — SPICE 网表

标准 SPICE 文本文件，SPICE 仿真器真正执行的输入：

```spice
* OTA example
M1 D G S B nmos W=10u L=0.18u
Vdd VDD 0 1.8
.lib "models/cmos018.lib"
.tran 0 1u
.end
```

- Ngspice/Xyce/HSpice/PSpice 都能直接读
- LTspice 也能直接打开 `.cir` 跑（无原理图）
- 另存为 `.cir`：`File → Save As... → *.cir`

### 3.4 `.model` — 单个 SPICE 器件模型

```spice
.MODEL nmos nmos (
    + VTO=0.45
    + KP=120u
    + LAMBDA=0.06
    + TOX=4.1n
)
```

- 适用于：NMOS/PMOS、DIODE、NPN/PNP、SWITCH 等
- 通常不单独建 `.model` 文件，写在 `.lib` 里

### 3.5 `.lib` — SPICE 模型库（最重要）

文本文件，可包含：
- 多个 `.MODEL`（NMOS/PMOS/Diode/BJT）
- `.SUBCKT`（运放、比较器、功率 MOS 等宏模型）
- 参数 `.PARAM`、温度/bin 分组（TT/FF/SS/Slow/Fast）

在 LTspice 中使用：原理图里右键 → Spice Directive 加 `.lib models/cmos018.lib`

> Foundry PDK 用 BSIM3/BSIM4 `.lib`（W/L 相关参数巨多）；厂商（TI/ADI）运放宏模型 = `.SUBCKT` in `.lib`

### 3.6 仿真时文件关系

```
your_ota.asc
   │  (LTspice 内部转换)
   ▼
temp_XXXX.cir   ← 自动生成网表
   │
   ├── 引用 .lib  ← 包含 .MODEL / .SUBCKT
   │
   └── 仿真引擎(LTspice solver) → 波形 .raw
```

### 3.7 一句话总结

| 后缀 | 本质 | LTspice 角色 |
|:---|:---|:---|
| `.asc` | 原理图 | 你画电路、设仿真 |
| `.cir` | SPICE 网表 | 仿真器真正输入 |
| `.model` | 单器件参数 | 被 `.lib` 包含 |
| `.lib` | 模型/子电路库 | 提供 MOS/二极管/运放模型 |

---

## 四、标准 SPICE 介绍

### 4.1 什么是「标准 SPICE」？

SPICE = **S**imulation **P**rogram with **I**ntegrated **C**ircuit **E**mphasis

- 诞生于 1973 UC Berkeley，最初用 Fortran 写
- 输入：网表（Netlist） → 输出：电压/电流随时间或频率
- 本质：把电路拓扑 + 器件模型 → 数学方程 → Newton-Raphson + 数值积分求解

### 4.2 版本演变

| 版本 | 特点 |
|:---|:---|
| SPICE2 (1975) | Fortran，经典教科书版本 |
| SPICE3 (1985) | ⭐ C 重写，交互式模式、改进 MOS 模型 |
| SPICE3f5 | 最后一个 Berkeley 官方发布 → **Ngspice 直系祖先** |
| HSpice/PSpice | 商业扩展（更好收敛、RF、加密模型） |
| Spectre | Cadence，SPICE-like，RF/瞬态噪声强 |
| Ngspice | SPICE3f5 + XSpice + CIDER |
| LTspice | 私有引擎，SPICE3 语法兼容（不完全等同） |

> "标准 SPICE"通常指 **SPICE3f5 语法 + 分析类型**

### 4.3 SPICE 内部在算什么？（程序员视角）

1. **拓扑 → 改进节点方程（MNA）**：$Gx + C\dot{x} = b(u,t)$
2. **DC 分析（`.op`/`.dc`）**：非线性器件 → Newton-Raphson 迭代，线性化 I-V 曲线
3. **Transient（`.tran`）**：数值积分（默认梯形法 Gear），每时间步非线性 solve
4. **AC 小信号（`.ac`）**：在 DC 工作点线性化，代入 $s=j\omega$ → 复数矩阵求解

> 🧠 SPICE 本质 = 稀疏矩阵 + Newton + 数值积分 + 器件模型

### 4.4 标准 SPICE 网表结构

```spice
* 注释（标题）
.title Simple CS Amp

* ===== 电源 =====
Vdd   VDD   0   1.8
Vin   IN    0   dc 0.9 ac 1

* ===== 器件 =====
R1    VDD   D   10k
M1    D    IN   0   0   nmos   W=10u   L=0.18u
Cload D    0   1p

* ===== 库 =====
.lib "models/cmos018.lib"

* ===== 仿真控制 =====
.op
.dc Vin 0.8 1.0 0.01
.ac dec 100 1k 100Meg
.tran 0 100n

.end
```

### 4.5 关键语法元素

#### 节点

- `0` = 全局地（GND），必须存在
- 节点名可数字或字符

#### 被动器件

```spice
Rname +node -node value
Cname +node -node value
Lname +node -node value
```

#### 独立源

```spice
Vname + - DC value
Vname + - PULSE(0 1 0 1n 1n 100n 200n)
Vname + - AC 1      ; 小信号 AC 幅值
```

#### 半导体器件

```spice
Mname D G S B model_name W= L=
Dname A K model_name
Qname C B E model_name
```

#### 常用分析指令

| 指令 | 含义 |
|:---|:---|
| `.op` | 直流工作点 |
| `.dc var start stop step` | 直流扫描 |
| `.ac dec/oct/lin pts fstart fstop` | 交流小信号 |
| `.tran tstep tstop` | 瞬态 |
| `.noise` | 噪声分析 |
| `.tf v(out) vin` | 传输函数 |

### 4.6 工具与标准 SPICE 的关系

| 工具 | 和标准 SPICE 关系 |
|:---|:---|
| LTspice | 接受 SPICE3 网表 + 私有扩展；引擎不同 |
| Ngspice | ⭐ 最接近标准 SPICE3f5 + XSpice，PySpice 后端 |
| HSpice/PSpice | 超集，向下兼容 |
| Cadence Spectre | SPICE-compatible netlist，求解器不同 |
| PySpice | 生成/调 Ngspice → 吃标准 SPICE 网表 |

> ✅ 学标准 SPICE 网表 = 所有工具通吃

---

## 五、标准 SPICE 网表逐行解析

以 NMOS Common-Source 放大器为例：

### 5.1 完整网表

```spice
* ----------------------------------------
* CS Amplifier — Standard SPICE Netlist
* ----------------------------------------
.title CS_AMP_nmos

* ---- Power Supply ----
Vdd   VDD   0   DC 1.8
Vin   IN    0   DC 0.9 AC 1

* ---- Load Resistor ----
Rd    VDD   D   10k

* ---- NMOS ----
M1    D    IN   0   0   nmos   W=10u   L=0.18u

* ---- Load Capacitor (parasitic / test) ----
Cload D    0   1p

* ---- Model Library ----
.lib "models/cmos018.lib"

* ---- Analysis ----
.op
.dc   Vin  0.7  1.1  0.01
.ac   dec  100  1k  100Meg
.tran 0   50n

* ---- End ----
.end
```

### 5.2 逐行解析

#### 注释 & 标题

```spice
* CS Amplifier — Standard SPICE Netlist
.title CS_AMP_nmos
```

- `*` → 整行注释
- `.title` → 可选，写入输出日志

#### 独立电压源

```spice
; Vname  +node  -node  [DC val]  [AC val]  [TRANSIENT src]
Vdd   VDD   0   DC 1.8
Vin   IN    0   DC 0.9 AC 1
```

| 名字 | +端 | -端 | 说明 |
|:---|:---|:---|:---|
| Vdd | VDD | 0(GND) | DC 1.8V 电源 |
| Vin | IN | 0 | DC=0.9V 偏置 + AC=1（小信号激励） |

- `.ac 1` 表示 AC 幅值 1V，仅用于 `.ac` 分析
- DC 值用于 `.op`/`.dc`/`.tran` 偏置

#### 电阻 — Rd

```spice
Rd    VDD   D   10k
; Rname  node1  node2  value
```

接在 VDD ↔ Drain，作有源负载

#### MOSFET — M1（最关键）

```spice
M1    D    IN   0   0   nmos   W=10u   L=0.18u
; Mname  Drain  Gate  Source  Bulk  ModelName  [W=] [L=]
```

| 端子 | 本例 |
|:---|:---|
| D | D（漏 → Rd） |
| G | IN（输入） |
| S | 0（源接地） |
| B | 0（衬底接地 → 防 body effect） |
| model | `nmos`（须由 `.lib` 提供） |

> ⚠️ NMOS 衬底一般接最低电位，PMOS 接最高电位

#### 电容 — Cload

```spice
Cload D    0   1p
```

模拟输出节点寄生电容 / 测试负载，不影响 DC，决定 -3dB 带宽

#### 模型库引用 — `.lib`

```spice
.lib "models/cmos018.lib"
```

内部应包含：
```spice
.MODEL nmos nmos ( VTO=0.45 KP=120u ... )
.MODEL pmos pmos ( VTO=-0.48 KP=40u ... )
```

> ❌ 若路径错或 model 名不匹配 → `Unknown model nmos`

#### 仿真控制

| 指令 | 含义 |
|:---|:---|
| `.op` | 求 DC 工作点（V(D), Id, region） |
| `.dc Vin 0.7 1.1 0.01` | DC 扫描 Vin |
| `.ac dec 100 1k 100Meg` | 小信号频响（需 AC 源） |
| `.tran 0 50n` | 时域仿真 |

#### 结束标记

```spice
.end
```

- ✅ 必须存在
- ❌ 之后内容全部忽略

### 5.3 SPICE 内部解析流程

1. 建节点表（VDD / IN / D / 0）
2. 实例化器件 → 插入 MNA 方程
3. 读 `.lib` → 绑定 `.MODEL` 参数到 M1
4. DC 初始化（Newton 迭代）
5. 根据分析类型：`.op`→解非线性代数；`.ac`→线性化 @ OP → complex solve；`.tran`→数值积分 + NR per step
6. 写 `.raw`/`.log` 供查看

### 5.4 常见网表错误速查

| 现象 | 原因 |
|:---|:---|
| `floating node` | 节点无 DC path to GND |
| `unknown model` | 忘 `.lib` 或 model 名拼错 |
| 不收敛 | 初始 guess 差 / 浮 MOS / 强正反馈 |
| 零 gain | MOS 没进 saturation（查 `.op`） |
| 无 AC 响应 | 忘 `AC 1` 源 或 开路输出 |

---

## 六、一句话总结

> SPICE 网表 = 电路拓扑 + 器件参数 + 分析指令的文本描述。每行声明一个物理元件或控制行为；节点 `0` 是全局参考；`.model`/`.lib` 给器件生命；`.op`/`.dc`/`.ac`/`.tran` 告诉求解器干什么。
>
> 搞明白 `.cir`，就能彻底脱离"只会点 LTspice Run"，可以：✅ 手写 Ngspice 网表、✅ 用 PySpice 自动生成、✅ 读懂任何 PDK/参考设计。
>
> **学习顺序：LTspice → 读网表 → PySpice。LTspice 教你"电路长什么样"，PySpice 教你"让计算机帮你找参数"。两者不冲突，依次进阶。**
