# MLIR 编译器底座学习指南：Triton / Mojo / TVM Unity 的共同地基

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：想搞懂 Triton / Mojo / TVM Unity / IREE / OpenXLA 为什么都建在同一个东西上、想成为编译器/芯片工程师的 AI 开发者。
> **目标**：读完本文，你能说清 MLIR 的 Dialect / Operation / Region / Pass 四大概念，看得懂 `triton-opt --print-ir-after-all` 的输出，知道 MLIR 生态里每个"方言"的定位。

---

## 目录

- [0. 写在最前：为什么现在必须懂 MLIR](#0-写在最前为什么现在必须懂-mlir)
- [1. LLVM 的痛点与 MLIR 的诞生](#1-llvm-的痛点与-mlir-的诞生)
- [2. 四大核心概念：Dialect / Operation / Region / Pass](#2-四大核心概念dialect--operation--region--pass)
- [3. 主流 Dialect 生态图谱](#3-主流-dialect-生态图谱)
- [4. Triton / Mojo / TVM Unity 是如何用 MLIR 的](#4-triton--mojo--tvm-unity-是如何用-mlir-的)
- [5. 亲手体验：读一份 Triton 编译过程的 IR](#5-亲手体验读一份-triton-编译过程的-ir)
- [6. 学习路径：从"能读 IR"到"能写 Pass"](#6-学习路径从能读-ir-到能写-pass)
- [7. 什么时候你需要写 MLIR？什么时候不用？](#7-什么时候你需要写-mlir什么时候不用)
- [8. 学习路线图（6~8 周）](#8-学习路线图68-周)
- [9. 精选资源与官方链接](#9-精选资源与官方链接)

---

## 0. 写在最前：为什么现在必须懂 MLIR

### 0.1 一个惊人的事实

以下 6 个明星项目，**底层都是 MLIR**：

| 项目 | 用 MLIR 做什么 |
|:--|:--|
| **Triton** | Python DSL → Triton IR → LLVM IR → PTX |
| **Mojo** | 全部编译栈基于 MLIR |
| **TVM Unity (Relax)** | 从 Relay 迁到 MLIR 生态 |
| **IREE** | 端到端 ML 编译器，基于 MLIR 派生 |
| **OpenXLA / StableHLO** | XLA 的重写版，基于 MLIR |
| **ONNX-MLIR** | ONNX 官方编译器 |
| **CIRCT** | 硬件 EDA 领域 |

**结论**：**MLIR 是 21 世纪 20 年代所有主流编译器的共同基础**。不懂 MLIR，你就无法参与下一代 AI 编译器的设计。

### 0.2 一句话总结

> **MLIR = LLVM 的下一代**——LLVM 只支持一种 IR（LLVM IR），MLIR 允许你**自定义任意多层 IR（"方言" Dialect）**，从 Python AST 到硬件汇编无缝下降。**它是所有现代 DSL 编译器的地基**。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **G1 认知** | 说清 Dialect / Operation / Region / Pass，看得懂 IR 文本 |
| **G2 会读** | 能读懂 Triton / MLIR 官方 dialect（arith / affine / scf / llvm）的 IR |
| **G3 会调** | 能用 mlir-opt / triton-opt 做 pipeline 调试 |
| **G4 会写** | 能实现自定义 Dialect + Pass，把新 IR 下降到 LLVM |

**建议**：读完本文你到 **G1~G2**，配合 MLIR Toy Tutorial 冲到 **G3**。

---

## 1. LLVM 的痛点与 MLIR 的诞生

### 1.1 LLVM 时代的困境

LLVM 用一份"通用 IR"（LLVM IR）作为编译器中间语言：

```
C/C++/Rust/Swift → Clang → LLVM IR → x86/ARM/GPU 汇编
```

**问题**：**LLVM IR 太低阶了**——它是"接近汇编"的 IR，做**高层优化**（如张量运算融合）非常困难。

**每个 DSL 都要自己造一个"高阶 IR"**：
- Tensorflow 有 GraphDef；
- PyTorch 有 FX；
- Halide 有自己的 IR；
- Swift 有 SIL；
- Rust 有 MIR；
- 每个都是独立轮子，互不复用。

### 1.2 MLIR 的核心思想（Chris Lattner，2019）

**"允许任意多层 IR，每层解决自己的问题"**：

```
Python 源码
    ↓
高阶 IR（张量、for 循环、算子）—— 做算子融合、tiling
    ↓
中阶 IR（线性代数、内存管理）—— 做布局优化、循环变换
    ↓
低阶 IR（LLVM 兼容）—— 交给 LLVM 生成机器码
    ↓
PTX / x86 / ARM
```

**每一层用一种"Dialect"（方言）**，MLIR 帮你定义、验证、下降。

### 1.3 一个类比

- **LLVM 就像一门"通用汇编"** —— 所有语言都要翻译成它；
- **MLIR 就像"编译器的乐高"** —— 你可以搭出任何形状的编译栈。

---

## 2. 四大核心概念：Dialect / Operation / Region / Pass

### 2.1 Operation（操作）

**MLIR 里一切都是 Operation**——函数、循环、算子甚至模块本身都是 Operation。

```mlir
// 一个 Operation 长这样：
%c = arith.addi %a, %b : i32
//    └──┬──┘  └┬┘  └┬┘   └┬┘
//    dialect  name inputs type
```

结构：
- **名字**：`arith.addi` （dialect.opname）
- **参数**：`%a, %b`（`%` 前缀的都是 SSA 值）
- **返回值**：`%c`
- **属性**：常量、字符串等编译期信息
- **Region**：可能包含子 Operation（下面说）

### 2.2 Region 与 Block

**Region = 一段"子代码"**，可以嵌套：

```mlir
func.func @main(%a: i32, %b: i32) -> i32 {          // ← 函数体是一个 Region
    %c = arith.addi %a, %b : i32
    scf.for %i = %c0 to %c10 step %c1 {              // ← for 循环体也是 Region
        // 这里嵌套一个 Region
    }
    return %c : i32
}
```

**Block** = Region 内的基本块，Region 由若干 Block 组成（就像 LLVM）。

### 2.3 Dialect（方言）——MLIR 最革命的设计

**Dialect = 一组相关 Operation 的集合**，就像编程语言的"标准库"。

**MLIR 官方常用 Dialect**：

| Dialect | 抽象层级 | 干啥用 |
|:--|:--|:--|
| `arith` | 中阶 | 算术运算（add/mul/cmp）|
| `scf` | 中阶 | 结构化控制流（for/if/while）|
| `affine` | 中阶 | 仿射循环（用于 polyhedral 优化）|
| `linalg` | 高阶 | 线性代数原语（matmul/generic）|
| `tensor` | 高阶 | 张量操作（extract/insert/reshape）|
| `memref` | 中阶 | 内存引用（相当于 C 的指针 + shape）|
| `gpu` | 中阶 | GPU 相关（kernel launch、thread id）|
| `llvm` | 低阶 | 完全对应 LLVM IR |
| `func` | 全阶 | 函数定义 |
| `nvgpu` / `nvvm` | 低阶 | NVIDIA 专属（MMA、TMA）|

**社区/项目自定义 Dialect**：

| Dialect | 出品 | 用途 |
|:--|:--|:--|
| `tt` (Triton) | OpenAI | Triton 的高阶 IR |
| `triton_gpu` | OpenAI | Triton 的 GPU 中阶 IR |
| `stablehlo` | OpenXLA | 从 XLA HLO 演化而来 |
| `tosa` | Arm | Tensor Operator Set Architecture |
| `hw` / `sv` | CIRCT | 硬件描述 |

### 2.4 Pass（编译遍）

**Pass = 对 IR 做一次转换**，MLIR 提供完整基建：

```bash
# 依次跑一堆 Pass
mlir-opt input.mlir \
    -convert-linalg-to-loops \    # linalg → scf
    -convert-scf-to-cf \           # scf → cf
    -convert-arith-to-llvm \       # arith → llvm
    -convert-func-to-llvm \        # func → llvm
    -reconcile-unrealized-casts \
    | mlir-translate --mlir-to-llvmir \
    | llc -filetype=obj -o output.o
```

**Pass 类型**：
- **Rewrite Pattern**：局部改写（如 `a + 0 → a`）；
- **Conversion Pass**：一整个 dialect 下降到另一个（如 linalg → loops）；
- **Analysis Pass**：只分析不修改（如数据流分析）；
- **Pipeline**：多个 Pass 组合。

---

## 3. 主流 Dialect 生态图谱

```
                    ┌─ 高阶 ─┐
                    │        │
     用户 DSL       │  tt    │←── Triton
                    │ stablehlo│←── OpenXLA / JAX
                    │  torch  │←── Torch-MLIR
                    │  onnx   │←── ONNX-MLIR
                    │  tosa   │←── Arm
                    │        │
                    ├─ 中阶 ─┤
                    │        │
     通用抽象       │ linalg  │
                    │ tensor  │
                    │ affine  │
                    │  scf    │
                    │ memref  │
                    │        │
                    ├─ 低阶 ─┤
                    │        │
     硬件相关       │  gpu    │
                    │ nvvm    │←── NVIDIA
                    │ rocdl   │←── AMD
                    │ spirv   │←── Vulkan
                    │  llvm   │←── x86/ARM
                    └────────┘
```

**编译栈就是从高阶一路"降级"到低阶**，每一层做各自擅长的优化。

---

## 4. Triton / Mojo / TVM Unity 是如何用 MLIR 的

### 4.1 Triton 的编译栈

```
Python @triton.jit 函数
    ↓ AST 转换
Triton IR (tt dialect)          ← 张量、指针、程序 id
    ↓ 优化：coalescing、pipelining、layout
Triton GPU IR (triton_gpu)      ← 分块、warp 分配
    ↓ 下降
LLVM IR (with nvvm)
    ↓
PTX → SASS → 硬件执行
```

**看 Triton 的 pass**：

```bash
# 查看所有 pass
triton-opt --help

# 例子
triton-opt kernel.mlir \
    --tritongpu-coalesce \       # 访存合并
    --tritongpu-pipeline \        # 软件流水
    --tritongpu-remove-layout-conversions
```

### 4.2 Mojo 的编译栈

Mojo 号称"Python 的超集"，但**编译器全栈基于 MLIR**：
- Mojo AST → **Mojo Dialect**（自定义）；
- → linalg / arith / scf / affine；
- → GPU/CPU dialect；
- → LLVM IR → 机器码。

**优势**：因为在 MLIR 里，Mojo 天然能对接 Triton / OpenXLA / IREE。

### 4.3 TVM Unity (Relax)

新一代 TVM 从 Relay IR 逐步迁移到 MLIR 兼容格式：
- Relax IR（TVM 自己的 tensor IR）；
- 逐步支持与 MLIR 生态互通；
- BYOC（Bring Your Own Codegen）经常嵌入 MLIR-based 后端。

---

## 5. 亲手体验：读一份 Triton 编译过程的 IR

### 5.1 打开 Triton 的中间产物

```python
import triton
import triton.language as tl

@triton.jit
def vector_add(a_ptr, b_ptr, c_ptr, N, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    mask = offs < N
    a = tl.load(a_ptr + offs, mask=mask)
    b = tl.load(b_ptr + offs, mask=mask)
    tl.store(c_ptr + offs, a + b, mask=mask)

# warmup 一次拿到编译产物
kernel = vector_add.warmup(...)
print(kernel.asm['ttir'])      # ← Triton IR（tt dialect）
print(kernel.asm['ttgir'])     # ← Triton GPU IR
print(kernel.asm['llir'])      # ← LLVM IR
print(kernel.asm['ptx'])       # ← PTX 汇编
```

### 5.2 Triton IR 长啥样

```mlir
// ttir 层（伪造示例）
module {
  tt.func @vector_add(%a_ptr: !tt.ptr<f32>, %b_ptr: !tt.ptr<f32>,
                      %c_ptr: !tt.ptr<f32>, %N: i32) {
    %pid = tt.get_program_id x : i32
    %block = arith.constant 1024 : i32
    %start = arith.muli %pid, %block : i32
    %range = tt.make_range {start = 0, end = 1024} : tensor<1024xi32>
    // ... 各种张量操作
    %a = tt.load %ptrs, %mask : tensor<1024x!tt.ptr<f32>>
    %b = tt.load ...
    %c = arith.addf %a, %b : tensor<1024xf32>
    tt.store %ptrs, %c, %mask
    tt.return
  }
}
```

**关键点**：**IR 里的张量是"抽象张量"**，不涉及 warp / block；直到 ttgir 才引入 layout。

### 5.3 IR 下降的 5 层

| 层 | 表现 |
|:--|:--|
| ttir | 抽象张量 |
| ttgir | 加入 layout、warp 分配 |
| shared | 加入 shared memory 分配 |
| llir | LLVM IR（有 nvvm intrinsic）|
| ptx | NVIDIA 汇编 |

---

## 6. 学习路径：从"能读 IR"到"能写 Pass"

### 6.1 三段式学习曲线

```
Stage 1: 能读 IR
    - 认识 arith / scf / linalg / gpu / llvm
    - 看 Triton `--print-ir-after-all` 输出

Stage 2: 能调 Pipeline
    - 用 mlir-opt 手动跑 pass
    - 用 triton-opt 调试 kernel 编译
    - 对比 pass 前后差异

Stage 3: 能写 Pass / Dialect
    - 跟着 MLIR Toy Tutorial 走一遍
    - 用 TableGen 定义 op
    - 实现 rewrite pattern
```

### 6.2 Toy Tutorial（官方入门）

MLIR 官方提供了一个 **7 章 Toy 语言教程**（<https://mlir.llvm.org/docs/Tutorials/Toy/>），从零实现：

- 第 1~2 章：定义一个玩具 Dialect；
- 第 3 章：写 rewrite pattern；
- 第 4 章：泛型化 & 类型转换；
- 第 5 章：接入 affine（loop 抽象）；
- 第 6 章：下降到 LLVM；
- 第 7 章：JIT 执行。

**跟完这 7 章，你就能写自己的 Dialect 和 Pass 了**。

---

## 7. 什么时候你需要写 MLIR？什么时候不用？

### 7.1 决策矩阵

| 你是什么角色？ | 要不要学 MLIR？ |
|:--|:--|
| **PyTorch 应用开发者** | ❌ 不用（就用 `torch.compile`）|
| **Triton kernel 工程师** | ⚠️ 会看 IR 就够（帮助调优）|
| **AI 编译器工程师** | ✅ **必修** |
| **自研芯片工程师** | ✅ **必修** |
| **DSL 语言设计者** | ✅ **必修** |
| **想读 Triton / IREE 源码** | ✅ **强烈推荐** |

### 7.2 三个反直觉忠告

1. **不要一上来就写 Dialect** —— 先能读懂官方 dialect 的 IR，再谈自定义；
2. **优先跑 MLIR Toy Tutorial** —— 是最快的学习路径，一周能上手；
3. **别指望短期内产出成果** —— MLIR 是"投入 3~6 个月才见效"的技术。

---

## 8. 学习路线图（6~8 周）

### Week 1：认识 MLIR
- 装 MLIR / LLVM（`brew install llvm` 或从源码）；
- 用 `mlir-opt` 打印一些 dialect 的 IR；
- 读官方 language reference 前 5 章。

### Week 2~3：Toy Tutorial
- 跟完 7 章 Toy Tutorial；
- 亲手实现一次 Dialect + Pass；
- 理解 TableGen（`.td` 文件）。

### Week 4~5：读 Triton 编译栈
- 装 Triton 源码；
- 用 `triton-opt` 打印 IR，理解每个 pass 的作用；
- 修改一个 Triton pass 看效果。

### Week 6~8（可选）：产出
- 挑一个想法：新算子 dialect / 新硬件后端 / 新优化 pass；
- 用 MLIR 实现最小 demo；
- 在自己项目里做 poc。

---

## 9. 精选资源与官方链接

### 9.1 官方
- **MLIR 主页**：<https://mlir.llvm.org/>
- **Toy Tutorial**：<https://mlir.llvm.org/docs/Tutorials/Toy/>
- **Language Reference**：<https://mlir.llvm.org/docs/LangRef/>
- **Dialects 目录**：<https://mlir.llvm.org/docs/Dialects/>

### 9.2 论文 / 视频
- **MLIR 论文**（Chris Lattner et al., 2020）：<https://arxiv.org/abs/2002.11054>
- **MLIR CGO 2021 tutorial**（YouTube）
- **LLVM Developers' Meeting** MLIR track 视频合集

### 9.3 相关项目
- **Triton**：<https://github.com/triton-lang/triton>
- **IREE**：<https://github.com/iree-org/iree>
- **OpenXLA / StableHLO**：<https://github.com/openxla/stablehlo>
- **Torch-MLIR**：<https://github.com/llvm/torch-mlir>
- **ONNX-MLIR**：<https://github.com/onnx/onnx-mlir>
- **CIRCT (硬件)**：<https://github.com/llvm/circt>
- **Mojo (Modular)**：<https://www.modular.com/mojo>

### 9.4 姊妹篇
- [Triton 编程学习指南](./Triton编程学习指南.md)（MLIR 最典型的用户）
- [TVM 编程学习指南](./TVM编程学习指南.md)（同为编译器）
- [torch.compile 编程学习指南](./torch.compile编程学习指南.md)（Inductor 与 Triton IR）

---

**版权声明**：本文由汪亮（bertonwang）撰写，转载请注明出处。欢迎邮件（<47608843@qq.com>）交流勘误。

**一句话总结全文**：**MLIR = 编译器的乐高**——允许你搭出任意多层 IR，Triton/Mojo/IREE/OpenXLA 都建在其上。**看得懂它，你就看得懂下一代 AI 编译器的全部**。
