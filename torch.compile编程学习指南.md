# torch.compile (Inductor) 编程学习指南（Windows/Linux + RTX 3060 + PyTorch 2.x）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：写 PyTorch 的 AI/ML 工程师、模型训练与推理性能工程师。已经用过 `nn.Module`、能读懂 `torch.autograd`，想**一行 `torch.compile(model)` 提速 1.5~3x**，进一步想**看懂 Inductor 生成的 Triton 代码、能自定义 fusion、写 custom op 让编译器识别**。
> **目标**：3~7 天内，从"一行装饰器加速训练/推理"到"能读 `TORCH_COMPILE_DEBUG` 产物、能理解 Dynamo 抓的 FX Graph、能定位 recompile 与 graph break、能配合 Triton 写自定义 kernel"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1** + PyTorch **2.4+** + Python **3.10+**。**Linux/WSL2 首选**（Windows 上 Inductor 支持 2.4 后基本可用，但生态更成熟在 Linux）。

---

## 目录

- [0. 写在最前：为什么要学 torch.compile？](#0-写在最前为什么要学-torchcompile)
- [1. torch.compile 是什么：一句话讲清 vs JIT / vs TorchScript / vs TensorRT](#1-torchcompile-是什么一句话讲清-vs-jit--vs-torchscript--vs-tensorrt)
- [2. 环境搭建（Windows / Linux / WSL2）](#2-环境搭建windows--linux--wsl2)
- [3. torch.compile 的心智模型：Dynamo → AOTAutograd → Inductor → Triton](#3-torchcompile-的心智模型dynamo--aotautograd--inductor--triton)
- [4. 第一个程序：一行装饰器，逐段拆解](#4-第一个程序一行装饰器逐段拆解)
- [5. 关键概念：Graph Break / Recompile / Guard / Dynamic Shape](#5-关键概念graph-break--recompile--guard--dynamic-shape)
- [6. 三大 backend & mode：inductor / cudagraphs / reduce-overhead / max-autotune](#6-三大-backend--modeinductor--cudagraphs--reduce-overhead--max-autotune)
- [7. 读 Inductor 生成的代码：`TORCH_COMPILE_DEBUG` 全流程](#7-读-inductor-生成的代码torch_compile_debug-全流程)
- [8. 高阶：Custom Op / Fusion / 与 Triton 集成](#8-高阶custom-op--fusion--与-triton-集成)
- [9. 性能分析与调优](#9-性能分析与调优)
- [10. torch.compile vs TorchScript / TensorRT / ONNX / TVM](#10-torchcompile-vs-torchscript--tensorrt--onnx--tvm)
- [11. 学习路线图（1 周）](#11-学习路线图1-周)
- [12. 精选资源与踩坑清单](#12-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 torch.compile？

你可能会问：**PyTorch 现在跑得已经挺快了，为什么还要学 `torch.compile`？** 答案是三点：

1. **一行代码 1.5~3x 加速**——训练/推理直接白嫖，没有理由不用；
2. **PyTorch 2.x 时代的默认打开方式**——Meta 官方的下一代性能路线；
3. **理解它就是理解"Python 的动态图如何变成 GPU 上的融合 kernel"**——这是现代 AI 编译器的核心问题。

### 0.1 一句话对比

| 场景 | 原生 PyTorch | **torch.compile** |
|:--|:--|:--|
| ResNet-50 训练 | 100% baseline | **150~180%** |
| Llama-7B 推理 | 100% | **200~300%** |
| 显存占用 | baseline | **常降 10~30%**（激活重计算 + 融合）|
| 改代码工作量 | 0 | **1 行** |
| 缺点 | — | 首次编译 5~30 秒 |

### 0.2 torch.compile 现在有多重要？

- **PyTorch 2.0（2023）核心特性**，官方视为 "下一代 PyTorch"；
- **Meta / OpenAI / HuggingFace / vLLM** 都在用；
- **Inductor 是 PyTorch 官方编译器后端**，会长期发展；
- **底层生成的就是 Triton kernel**——学它 = 见识"自动写 Triton"；
- **PyTorch 3.x 的默认路径**几乎就是 compile-first。

**一句话**：**torch.compile = PyTorch 官方"用 Python 写、GPU 峰值跑"的答案**——2.x 时代必修。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **C1 入门** | 会 `torch.compile(model)`、理解 3 种 mode |
| **C2 熟练** | 会用 `TORCH_LOGS` / `TORCH_COMPILE_DEBUG` 排障、能识别 graph break |
| **C3 高阶** | 会 dynamic shape、会写 `@torch.compile` 兼容代码、能读 Inductor 生成的 Triton |
| **C4 专家** | 会写 `custom_op` 让编译器识别、能自定义 pattern matcher / lowering |

**建议**：**1~2 天到 C1**（能加速你的模型）；**3~7 天到 C2/C3**（能排障、能读代码）。

---

## 1. torch.compile 是什么：一句话讲清 vs JIT / vs TorchScript / vs TensorRT

### 1.1 torch.compile 的定义

> **torch.compile 是 PyTorch 2.0+ 内置的即时编译器**，由 **TorchDynamo**（Python 字节码级图捕获）+ **AOTAutograd**（前后向图统一）+ **Inductor**（生成 Triton / C++ kernel）三件套组成。**装饰器一行、动态图心智不变、GPU/CPU 都支持**。

关键三点：

1. **Python 字节码级捕获**——不改代码、支持数据依赖控制流；
2. **生成 Triton 代码**——GPU 上 Inductor 直接产 Triton kernel（可读）；
3. **保留 eager 兼容性**——遇到不支持的算子自动 fallback（"graph break"）。

### 1.2 torch.compile vs 前辈们

| 维度 | TorchScript (`jit.script`)| ONNX Export | TensorRT | **torch.compile** |
|:--|:--|:--|:--|:--|
| 心智 | 静态图 subset | 图导出 + 外部推理 | 图导出 + 外部推理 | **eager + JIT** |
| 抓图方式 | 语法/类型分析 | tracing | ONNX 转换 | **字节码级 Dynamo** |
| 支持控制流 | 部分 | ⚠️ | ⚠️ | **✅ 天然** |
| 训练支持 | ⚠️ | ❌ | ❌ | **✅** |
| 生成什么 | TorchScript IR | ONNX + engine | TRT engine | **Triton / C++** |
| 学习曲线 | 陡 | 陡 | 陡 | **极低（一行）** |
| Python 侧兼容度 | 弱 | 弱 | 弱 | **极高** |

**记忆口诀**：
- **torch.compile = "Python 依旧、GPU 峰值"**——两全其美；
- **老 TorchScript 已过时**，PyTorch 2.x 起官方主推 compile；
- **TensorRT 仍是纯推理极致方案**，但训练与 debug 不友好。

### 1.3 一张图看清 torch.compile 在栈里的位置

```
┌──────────────────────────────────────────────────────────┐
│  用户代码（PyTorch nn.Module，全 Python）                   │
├──────────────────────────────────────────────────────────┤
│  @torch.compile 装饰器                                     │
├──────────────────────────────────────────────────────────┤
│  TorchDynamo（Python 字节码 → FX Graph）                    │
├──────────────────────────────────────────────────────────┤
│  AOTAutograd（前向 + 反向 图统一）                          │
├──────────────────────────────────────────────────────────┤
│  Inductor（图 → Triton / C++ 源码）                        │
├──────────────────────────────────────────────────────────┤
│  Triton / OpenMP  →  PTX / x86                            │
├──────────────────────────────────────────────────────────┤
│  cuBLAS / cuDNN（大算子直调）                              │
├──────────────────────────────────────────────────────────┤
│  CUDA Runtime + GPU 硬件（3060 / SM86）                    │
└──────────────────────────────────────────────────────────┘
```

**核心洞察**：`torch.compile` 是**把动态 PyTorch 编译到 Triton/C++**——用户什么都不用改，编译器自动融合、autotune、cache。

---

## 2. 环境搭建（Windows / Linux / WSL2）

### 2.1 平台

| 平台 | 支持 | 说明 |
|:--|:--|:--|
| Linux 原生 | ✅ 最好 | **首选**，生态成熟 |
| WSL2 | ✅ 好 | 学习首选（无重启） |
| Windows 原生 | ⚠️ PyTorch 2.4+ 可用 | Inductor Windows 支持逐步完善 |
| macOS (MPS) | ⚠️ 部分 | Metal 后端在完善 |

### 2.2 安装（3 分钟）

```bash
# 建虚拟环境
python -m venv .venv
source .venv/bin/activate            # Linux/WSL
# 或 .\.venv\Scripts\activate         # Windows

# 装 PyTorch 2.4+ CUDA 12.1
pip install --index-url https://download.pytorch.org/whl/cu121 \
    torch torchvision torchaudio

# 装 triton（Linux 会自动装；Windows 需 Triton 官方 wheel）
pip install triton               # Linux
# Windows 用 nightly：pip install --pre triton-windows
```

### 2.3 一步验证：hello_compile.py

```python
import torch

@torch.compile
def add_relu(x, y):
    return torch.relu(x + y)

x = torch.randn(1024, 1024, device="cuda")
y = torch.randn_like(x)

# 首次调用会触发编译（3~10 秒）
z = add_relu(x, y)
print("shape:", z.shape, "dtype:", z.dtype)

# 之后调用几乎无开销
import time
torch.cuda.synchronize(); t0 = time.time()
for _ in range(1000): z = add_relu(x, y)
torch.cuda.synchronize()
print(f"{(time.time()-t0)*1e3/1000:.3f} ms/iter")
```

期望：一句 `torch.compile` 装饰器就把 `add + relu` 融合成 **一个 Triton kernel**，比 eager 快 30~50%。

### 2.4 常见坑速查

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 首次调用很慢 | 正在编译 | 正常，会缓存到 `~/.cache/torch_compile` |
| Windows 报 Triton 缺失 | Windows Triton 装错 | 用 nightly `triton-windows` |
| `dynamic=True` 出错 | shape 变化太剧烈 | 换成 `dynamic="auto"` 或固定 shape |
| `graph break` 太多 | 代码有非 tensor 操作 | 用 `TORCH_LOGS="graph_breaks"` 查 |
| 显存爆 | max-autotune 打开了 CUDA Graph | 换 default mode |
| 结果与 eager 不一致 | 有 in-place 或 randomness | 用 `torch.compile(fullgraph=True)` 排查 |

---

## 3. torch.compile 的心智模型：Dynamo → AOTAutograd → Inductor → Triton

### 3.1 三层四阶段

```
Python 代码
   │
   ▼  ①  TorchDynamo：抓字节码 → FX Graph
   │
   ▼  ②  AOTAutograd：追加 backward 图（训练时）
   │
   ▼  ③  Inductor：图分区 + 融合 + 生成 Triton/C++ 源码
   │
   ▼  ④  Triton / cpp_extension：编译到 PTX / .so
   │
   ▼  执行
```

### 3.2 TorchDynamo：Python 字节码级抓图

- **不 tracing、不 scripting**——直接改 CPython 字节码；
- 遇到不能抓的地方（`print`、`np.random`、动态 shape 变化）→ **graph break**：把当前图 flush 掉，剩下用 eager 跑；
- 抓出来的中间表示是 **FX Graph**（PyTorch 官方 IR）。

**优势**：**代码不用改**，动态图心智完全保留。

### 3.3 AOTAutograd：前向 + 反向图统一

- Autograd 原本是 eager 时构建反向图；
- AOTAutograd 让编译器**同时看到前向和反向**，能一起融合优化（例如 activation 重计算）。

### 3.4 Inductor：融合器 + 代码生成器

- 输入：融合前的 FX Graph；
- 关键 Pass：
  - **算子分类**：pointwise / reduction / matmul / conv；
  - **融合**：相邻 pointwise 合成一个 Triton kernel；
  - **调度**：分块、tile、shared memory；
- 输出：**Triton 源码**（.py 文件）或 **C++ 源码**（CPU 时）。

**Inductor 生成的 Triton 代码是可以直接看的**——第 7 章详解。

### 3.5 Guard：怎么知道该不该重编译？

- 每次编译时生成一组 **Guard**（守卫条件）：例如 "输入 dtype=float16、shape=(N, 512)、stride=(512, 1)"；
- 下次调用：**Guard 全过** → 复用缓存；**任一 Guard 失败** → **Recompile**；
- Recompile 太频繁 = 性能杀手（每次 5~30 秒）。

---

## 4. 第一个程序：一行装饰器，逐段拆解

### 4.1 训练完整示例

```python
import torch, torch.nn as nn, torch.optim as optim

class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(1024, 4096), nn.GELU(),
            nn.Linear(4096, 4096), nn.GELU(),
            nn.Linear(4096, 10))
    def forward(self, x): return self.net(x)

model = MLP().cuda()
opt   = optim.AdamW(model.parameters(), lr=1e-3)

# ★ 一行加速
model = torch.compile(model, mode="default")

x = torch.randn(256, 1024, device="cuda")
y = torch.randint(0, 10, (256,), device="cuda")
loss_fn = nn.CrossEntropyLoss()

for step in range(100):
    logits = model(x)
    loss = loss_fn(logits, y)
    loss.backward()
    opt.step(); opt.zero_grad(set_to_none=True)
    if step % 10 == 0:
        print(f"step {step}, loss {loss.item():.4f}")
```

### 4.2 小白级逐段讲透

```python
model = torch.compile(model, mode="default")
```
**发生了什么？**  
- **暂时什么都没发生**（compile 是懒的）；
- 第一次 `model(x)` 调用时，**Dynamo** 才开始抓字节码；
- 抓完给 **AOTAutograd**，追加 backward；
- 给 **Inductor**，生成 Triton；
- **Triton 编译到 PTX** → 加载 → 执行。

**大约 5~15 秒后，第一步 loss 才打印**。之后每一步都走缓存，极快。

### 4.3 4 种最常用的 mode

| mode | 特点 | 首选场景 |
|:--|:--|:--|
| `"default"` | 通用，Inductor 融合 | **多数情况** |
| `"reduce-overhead"` | 加 CUDA Graph，减 launch overhead | **小 batch 推理** |
| `"max-autotune"` | 尝试多种 tile，选最快 | **模型固定、要极致性能** |
| `"max-autotune-no-cudagraphs"` | 上者但不用 CUDA Graph | **显存吃紧时** |

### 4.4 6 个新手常见坑

| # | 坑 | 症状 | 解决 |
|:--|:--|:--|:--|
| 1 | 首次巨慢就取消 | 5~30 秒编译被误当卡死 | 耐心等 |
| 2 | `.item()` / `.tolist()` 太频繁 | 触发 graph break | 只在需要时取 |
| 3 | shape 每次变 | 频繁 recompile | 用 `dynamic="auto"` 或 pad 到定长 |
| 4 | Python 副作用（print/list.append） | graph break | 移到编译外 |
| 5 | 结果与 eager 不一致 | 有 in-place / 随机 | `fullgraph=True` 排查 |
| 6 | max-autotune 时间太长 | tuning 慢 | 用 default 或 reduce-overhead |

---

## 5. 关键概念：Graph Break / Recompile / Guard / Dynamic Shape

### 5.1 Graph Break：Dynamo 抓不下去时

**典型触发**：
- `print(x)` → 副作用；
- `if x.item() > 0:` → 数据依赖 + 从 GPU 拷回 CPU；
- `numpy` / `list.append(t)` / 第三方 C 库；
- 未支持的算子。

**排查**：
```bash
TORCH_LOGS="graph_breaks,recompiles" python your_script.py
```

**降低 break 数量的技巧**：
- 用 `torch.where` 替代 `if x.item()`；
- 累积 loss 时用 tensor 累加而非 Python list；
- 尽量把 IO / logging 移到 compile 外。

### 5.2 Recompile：Guard 失败

每次 shape/dtype/stride 变化都可能重编。**查次数**：
```bash
TORCH_LOGS="recompiles" python your_script.py
```

**减少 Recompile**：
- **固定 batch size**（推理时补齐 padding）；
- 用 `torch.compile(dynamic=True)` 一次性生成动态 shape 图；
- 用 `torch._dynamo.mark_dynamic(x, dim=0)` 显式标记哪一维动态。

### 5.3 Dynamic Shape：让一个图支持多种 shape

```python
model = torch.compile(model, dynamic=True)
# 或
torch._dynamo.mark_dynamic(x, 0)   # 只把 dim 0 标为动态
```

**权衡**：Dynamic Shape 编译一次多 shape 都能用，但可能比全静态慢 5~20%。

---

## 6. 三大 backend & mode：inductor / cudagraphs / reduce-overhead / max-autotune

### 6.1 Backend

```python
torch.compile(model, backend="inductor")   # 默认，主力
torch.compile(model, backend="cudagraphs") # 仅 CUDA Graph，简单模型可用
torch.compile(model, backend="eager")      # 只捕图不编译，调试用
torch.compile(model, backend="aot_eager")  # + AOTAutograd，调试反向
```

**推荐**：**99% 场景用 `inductor`**。

### 6.2 常用 mode

| mode | inductor + | 用途 |
|:--|:--|:--|
| `default` | 融合 | 通用 |
| `reduce-overhead` | + CUDA Graph | 小 batch / 推理 |
| `max-autotune` | + CUDA Graph + tuning | 极致性能 |
| `max-autotune-no-cudagraphs` | + tuning | 显存紧 |

### 6.3 何时选 CUDA Graph？

- **小 batch 推理**（batch=1，launch overhead 占比大）→ 巨大收益；
- **动态 shape / 训练** → CUDA Graph 有限制，用 default 更稳。

---

## 7. 读 Inductor 生成的代码：`TORCH_COMPILE_DEBUG` 全流程

### 7.1 一键 dump 全部产物

```bash
TORCH_COMPILE_DEBUG=1 python your_script.py
```

会在 `./torch_compile_debug/` 下产生：
```
run_2026_07_14/
  ├── aot_forward_graph.py     # AOTAutograd 前向 FX
  ├── aot_backward_graph.py    # 反向 FX
  ├── fx_graph_readable.py     # 融合前的 FX
  ├── fx_graph_transformed.py  # 融合后的 FX
  ├── output_code.py           # ★ Inductor 生成的 Triton 源码
  └── ...
```

### 7.2 output_code.py 长什么样

```python
# 简化示意
@triton.jit
def triton_poi_fused_add_relu_0(in_ptr0, in_ptr1, out_ptr0, xnumel, XBLOCK: tl.constexpr):
    xoffset = tl.program_id(0) * XBLOCK
    xindex  = xoffset + tl.arange(0, XBLOCK)[:]
    xmask   = xindex < xnumel

    x0 = tl.load(in_ptr0 + xindex, xmask)
    x1 = tl.load(in_ptr1 + xindex, xmask)
    x2 = x0 + x1
    x3 = tl.where(x2 > 0, x2, 0)     # ReLU
    tl.store(out_ptr0 + xindex, x3, xmask)
```

**看得懂就是 Triton 学的水平**——Inductor **就是自动写 Triton**。

### 7.3 常用 log flag

```bash
TORCH_LOGS="+dynamo,+inductor,graph_breaks,recompiles"
# +dynamo 详细 dynamo 日志
# +inductor 详细 inductor 日志
# graph_breaks 只关注 break
# recompiles 只关注重编译
```

---

## 8. 高阶：Custom Op / Fusion / 与 Triton 集成

### 8.1 让编译器识别你的自定义 op

```python
from torch.library import custom_op

@custom_op("my_lib::my_matmul", mutates_args=())
def my_matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    return a @ b

# 关键：给 Dynamo/Inductor 一个 "假实现"，告诉它 shape/dtype
@my_matmul.register_fake
def _(a, b):
    return a.new_empty((a.size(0), b.size(1)))
```

这样 `torch.compile` 遇到 `my_matmul` 就不会 graph break，能纳入图里融合。

### 8.2 直接嵌入自己的 Triton kernel

Inductor 天然支持 `triton.jit` 函数——你写的 Triton kernel 可以直接在 `@torch.compile` 的函数里调用（PyTorch 2.3+）：

```python
import triton, triton.language as tl

@triton.jit
def my_kernel(x_ptr, y_ptr, ...): ...

@torch.compile
def f(x, y):
    z = torch.empty_like(x)
    my_kernel[(grid,)](x, y, z, ...)   # 直接调 Triton
    return z * 2                       # 剩下的 Inductor 融合
```

---

## 9. 性能分析与调优

### 9.1 三条铁律

1. **减少 graph break**——每 break 一次都是 eager + 边界开销；
2. **稳住 shape**——推理时 padding 到定长，避免 recompile；
3. **算子融合越多越好**——大量 pointwise/reduction 场景 compile 收益最大。

### 9.2 profile

```python
with torch.profiler.profile(activities=[
    torch.profiler.ProfilerActivity.CPU,
    torch.profiler.ProfilerActivity.CUDA]) as prof:
    for _ in range(20): model(x)
print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=20))
```

看融合后的 kernel 数量是否显著减少（例如从 200 个降到 20 个）。

### 9.3 结合 Nsight Compute

```bash
ncu --set full python your_script.py
```

看 Inductor 生成的 kernel 是否打到硬件峰值。

---

## 10. torch.compile vs TorchScript / TensorRT / ONNX / TVM

| 需求 | TorchScript | ONNX + Runtime | TensorRT | TVM | **torch.compile** |
|:--|:--|:--|:--|:--|:--|
| 训练加速 | ⚠️ | ❌ | ❌ | ❌ | **✅** |
| 推理加速 | ⚠️ | ✅ | ✅ 最强 | ✅ 强 | **✅** |
| Python 兼容度 | 低 | 低 | 低 | 低 | **极高** |
| 学习成本 | 陡 | 陡 | 陡 | 陡 | **一行** |
| 部署跨平台 | ⚠️ | ✅ | GPU only | ✅ | 需 PyTorch runtime |
| 生态活跃度 | 停滞 | 强 | 强 | 中 | **极强（官方主推）** |

**决策口诀**：
- **训练 + Python 环境部署** → **torch.compile**；
- **纯 GPU 极致推理** → TensorRT；
- **跨平台推理（含 CPU/边端）** → ONNX Runtime / TVM；
- **实验编译器技术** → TVM。

---

## 11. 学习路线图（1 周）

| Day | 目标 | 关键产出 |
|:--|:--|:--|
| **1** | 一行装饰器加速 ResNet50 / GPT-2 | 感受 1.5~3x 提速 |
| **2** | 学 `TORCH_LOGS`、graph_break/recompile | 会看日志 |
| **3** | 学 4 种 mode、CUDA Graph 收益判定 | 会选 mode |
| **4** | Dynamic Shape + `mark_dynamic` | 减少 recompile |
| **5** | `TORCH_COMPILE_DEBUG=1` 读 Triton 产物 | 看懂融合 |
| **6** | Custom Op / 嵌入自定义 Triton | 会扩展编译器 |
| **7** | 结合 Nsight，profile 一个真实模型 | 定位瓶颈 |

---

## 12. 精选资源与踩坑清单

### 12.1 必读资源

| 资源 | 链接 |
|:--|:--|
| PyTorch 官方 torch.compile 教程 | <https://pytorch.org/tutorials/intermediate/torch_compile_tutorial.html> |
| Inductor 源码 | <https://github.com/pytorch/pytorch/tree/main/torch/_inductor> |
| Dynamo 源码 | <https://github.com/pytorch/pytorch/tree/main/torch/_dynamo> |
| PT2 官方博客 | <https://pytorch.org/blog/pytorch-2-paper-tutorial/> |
| Horace He 系列文章 | <https://horace.io/> |
| tlparse（日志可视化）| <https://github.com/ezyang/tlparse> |

### 12.2 完整踩坑清单

| 症状 | 原因 | 解决 |
|:--|:--|:--|
| 首次巨慢 | 编译 | 正常，会缓存 |
| 每次 shape 都重编 | shape 变 | `dynamic=True` |
| `.item()` graph break | 数据依赖 | 移到 compile 外 |
| Windows Triton 装不上 | 需 nightly | `pip install --pre triton-windows` |
| `max-autotune` 显存爆 | CUDA Graph 缓存 | `max-autotune-no-cudagraphs` |
| DDP + compile 卡住 | compile 在 DDP 外 | 先 wrap DDP 再 compile（新版可反过来）|
| checkpoint + compile 冲突 | 老 API | 用 `torch.utils.checkpoint` + `use_reentrant=False` |
| loss 与 eager 不一致 | 数值精度 | 用 `torch.set_float32_matmul_precision('high')` |
| 反向图崩 | 有非 differentiable op | 用 `no_grad` 隔离 |
| Inductor 生成的代码错 | rare bug | 提 issue，暂用 `backend="eager"` 定位 |
| 缓存占磁盘 | 编译产物累积 | 清 `~/.cache/torch_compile` |
| 多进程编译冲突 | 并发写缓存 | 各 rank 独立 cache dir |

### 12.3 一句话总结

> **torch.compile = PyTorch 2.x 官方"Python 依旧、GPU 峰值"的答案**。**Dynamo 抓图 + AOTAutograd 合前后向 + Inductor 生 Triton** 三件套，一行装饰器换 1.5~3x 加速。**理解 graph break、recompile、guard 三大概念 = 会用**；**能读 output_code.py（Triton 源码）= 融会贯通**。是 AI 工程师 2026 年的必备内功。

---

**祝你一行装饰器，训练推理齐飞。有勘误或想交流，欢迎来信 <47608843@qq.com>。**
