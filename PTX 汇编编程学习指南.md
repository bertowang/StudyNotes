# PTX 汇编编程学习指南（Windows/Linux + RTX 3060 + CUDA 12.1）

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：已经会写 CUDA C++（至少读过《面向 AI 的 CUDA 编程学习指南》），想进一步**看懂 `nvcc` 生成的汇编、能在 CUDA 里内联 `asm`、能读 CUTLASS/FlashAttention 里那些"看不懂的一行"**的程序员。
> **目标**：3~4 周内，从"读第一行 PTX"到"能用 `asm volatile` 手写关键指令挤出 5~15% 性能、能定位 SASS 层的性能瓶颈"。
> **本机环境**：NVIDIA GeForce RTX 3060 + Compute Capability **8.6 (Ampere)** + CUDA **12.1** + `nvcc` / `ptxas` / `cuobjdump` / `nvdisasm`。

---

## 目录

- [0. 写在最前：为什么要学 PTX？](#0-写在最前为什么要学-ptx)
- [1. PTX 是什么：CUDA 编译栈里的"中间语言"](#1-ptx-是什么cuda-编译栈里的中间语言)
- [2. 环境搭建：不用装任何东西，`nvcc` 就够了](#2-环境搭建不用装任何东西nvcc-就够了)
- [3. PTX 编程模型：寄存器、状态空间与指令格式](#3-ptx-编程模型寄存器状态空间与指令格式)
- [4. 第一份 PTX：`nvcc` 生成的向量加法长啥样](#4-第一份-ptx-nvcc-生成的向量加法长啥样)
- [5. 六类必读指令：mov / ld / st / add / mad / cvta / bar / cp.async](#5-六类必读指令-mov--ld--st--add--mad--cvta--bar--cpasync)
- [6. 内联 PTX：在 CUDA C++ 里嵌 `asm volatile`](#6-内联-ptx在-cuda-c-里嵌-asm-volatile)
- [7. Tensor Core 直通车：`mma.sync` / `wgmma` 指令族](#7-tensor-core-直通车mmasync--wgmma-指令族)
- [8. 从 PTX 到 SASS：`cuobjdump` / `nvdisasm` 反汇编实战](#8-从-ptx-到-sasscuobjdump--nvdisasm-反汇编实战)
- [9. 性能优化：靠 PTX 能多挤出多少？](#9-性能优化靠-ptx-能多挤出多少)
- [10. 学习路线图（3~4 周）](#10-学习路线图34-周)
- [11. 精选资源与踩坑清单](#11-精选资源与踩坑清单)

---

## 0. 写在最前：为什么要学 PTX？

大多数 CUDA 教程会告诉你："别碰 PTX，编译器比你聪明。" **这句话对，也不对**。对的一面是：99% 的场景 `nvcc -O3` 生成的 PTX 已经够好；不对的一面是——

- 你**读不懂** CUTLASS 里的 `mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32`；
- 你**看不懂** FlashAttention 源码里 `asm volatile("cp.async.ca.shared.global ...")`；
- 你**看不到** `-Xptxas -v` 里那句 "spill stores: 128 bytes" 到底哪来的；
- 你**分析不了** Nsight Compute 里 "Warp Stall: Long Scoreboard" 具体是哪条指令卡住。

**PTX 是 GPU 世界的"汇编 + 中间语言"**——它比 C++ 低一层、又比最终的 SASS 高一层，是**你能读能写的最贴近硬件的语言**。学它不是为了替代编译器，而是为了：

1. **看懂**编译器生成了什么、为什么慢；
2. **改写**那 1% 关键路径，靠 `asm` 内联挤出 5~15% 性能；
3. **看懂**社区里那些 CUTLASS / FlashAttention / cuBLAS 汇编级源码。

### 0.1 一句话对比

| 需求 | 只会 CUDA C++ | 会 PTX |
|:--|:--|:--|
| 读懂 `nvcc --ptx` 输出 | ❌ 天书 | ✅ 一目了然 |
| 定位寄存器溢出（register spill）| 只知道结果 | **能看到具体哪个变量** |
| 用 Tensor Core | 靠 `wmma::` API | **能直接写 `mma.sync`** |
| 融合 `ldmatrix` + `mma` 打满 Tensor Core | 做不到 | **CUTLASS 就是这么写的** |
| 读 FlashAttention 源码 | 跳过 `asm` 段 | **看懂每一行** |

### 0.2 PTX 现在有多重要？

- **CUTLASS 3.x** 大量使用内联 `mma.sync` / `wgmma` / `cp.async` / `tma`——不会 PTX 就读不了；
- **FlashAttention-2/3** 在关键路径里手写 PTX 来控制指令调度和 async pipeline；
- **cuDNN / cuBLASLt / TensorRT** 的 kernel 都是 PTX 层调优出来的（虽然闭源，但你能反汇编看）；
- **Triton / torch.compile** 生成的最终代码就是 PTX——**看懂 PTX = 看懂编译器到底做了什么**。

**一句话**：**你不用天天写 PTX，但看不懂 PTX 就永远停在"调库工程师"的天花板下**。

### 0.3 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **P1 认知** | 能读懂 `nvcc --ptx` 输出的向量加法、知道 `.reg` / `.shared` / `.global` 是啥 |
| **P2 阅读** | 能读 CUTLASS 里的 `mma.sync` / `cp.async` / `ldmatrix`，知道每个 modifier 什么意思 |
| **P3 内联** | 能在 CUDA C++ 里用 `asm volatile` 嵌 PTX、能修改现有 kernel 的关键指令 |
| **P4 手写** | 能直接写 `.ptx` 文件、用 `ptxas` 编译、能针对 SM86 / SM90 分别调优 |

**建议**：**多数程序员冲到 P2 就够用**（1~2 周），能读源码即可；如果做 Kernel 优化则冲到 P3。**P4 只有做编译器/芯片对接的人才需要**。

---

## 1. PTX 是什么：CUDA 编译栈里的"中间语言"

### 1.1 PTX 的定义

> **PTX（Parallel Thread eXecution）** 是 NVIDIA 定义的**虚拟指令集**（Virtual ISA），介于 CUDA C++ 和真实 GPU 机器码（SASS）之间。它的角色相当于 CPU 世界里的 LLVM IR / .NET IL——**跨代际、可读、可反汇编、可手写**。

关键三点：

1. **虚拟 ISA**：PTX **不是**任何一代 GPU 的真实指令；驱动会把 PTX **JIT 编译成 SASS**（真实机器码）再运行；
2. **前向兼容**：Ampere 编译出的 PTX 可以在 Hopper 上跑（驱动重新 JIT），但 SASS 不行；
3. **人类可读**：类似汇编，`add.f32 %r1, %r2, %r3;` 这种一眼就能看懂。

### 1.2 CUDA 编译栈全图

```
┌─────────────────────────────────────────────────┐
│  .cu  (CUDA C++ 源码)                            │
└────────────────┬────────────────────────────────┘
                 │  nvcc（前端 = clang 改的）
                 ▼
┌─────────────────────────────────────────────────┐
│  .ptx  (PTX 中间语言 —— 本文主角)                 │  ← 你能读、能写、能嵌
└────────────────┬────────────────────────────────┘
                 │  ptxas（NVIDIA 汇编器）
                 ▼
┌─────────────────────────────────────────────────┐
│  .cubin  (SASS，SM 特定的真实机器码)              │  ← 只能反汇编看，不能写
└────────────────┬────────────────────────────────┘
                 │  Driver JIT（如果目标 SM 更新）
                 ▼
┌─────────────────────────────────────────────────┐
│  在 GPU 上执行                                   │
└─────────────────────────────────────────────────┘
```

**几个关键命令**（后面会用到）：

| 命令 | 作用 |
|:--|:--|
| `nvcc -ptx a.cu -o a.ptx` | 编译到 PTX 停下（人类可读） |
| `nvcc -cubin a.cu -o a.cubin` | 编译到 SASS 停下 |
| `nvcc -Xptxas -v a.cu` | 编译时打印寄存器/共享内存/spill 用量 |
| `cuobjdump --dump-ptx a.out` | 从可执行文件反出 PTX |
| `cuobjdump --dump-sass a.out` | 反出 SASS |
| `nvdisasm a.cubin` | 更详细的 SASS 反汇编（带控制流图） |

### 1.3 PTX vs SASS vs LLVM IR vs Triton IR

| 维度 | LLVM IR | Triton IR | **PTX** | SASS |
|:--|:--|:--|:--|:--|
| **抽象层级** | 通用中间语言 | GPU tile 级 | GPU 虚拟 ISA | GPU 真实 ISA |
| **谁产出** | clang / rustc | Triton 编译器 | `nvcc` / 你手写 | `ptxas` |
| **人类可读** | ✅ | ✅ | ✅ | ⚠️ 能读但难 |
| **能手写吗** | 少 | 不需要 | ✅ **本文主角** | ❌（只能反汇编看） |
| **跨 SM 兼容** | N/A | ✅ | ✅ | ❌（SM86 ≠ SM90） |

**记忆口诀**：
- **PTX = 你能写的最底层**；
- **SASS = 你能看但不能写**；
- **中间的差距 = ptxas 的工作**（寄存器分配、指令调度、峰值利用率优化）。

---

## 2. 环境搭建：不用装任何东西，`nvcc` 就够了

### 2.1 前置条件

- 装了 CUDA Toolkit（12.x 优先）；
- 显卡驱动 ≥ Toolkit 要求；
- 会用 `nvcc` 编译 `.cu` 文件（不会请先看《面向 AI 的 CUDA 编程学习指南》）。

**验证**：

```bash
nvcc --version                  # 应输出 12.x
nvidia-smi                      # 应能看到你的 GPU
cuobjdump --version             # PTX/SASS 反汇编工具，Toolkit 自带
```

### 2.2 一分钟看 PTX：Hello PTX

新建 `hello.cu`：

```cpp
__global__ void add(int *a, int *b, int *c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) c[i] = a[i] + b[i];
}
```

生成 PTX：

```bash
nvcc -arch=sm_86 -ptx hello.cu -o hello.ptx
```

打开 `hello.ptx`，你会看到类似（节选）：

```asm
.visible .entry _Z3addPiS_S_i(
    .param .u64 _Z3addPiS_S_i_param_0,
    .param .u64 _Z3addPiS_S_i_param_1,
    .param .u64 _Z3addPiS_S_i_param_2,
    .param .u32 _Z3addPiS_S_i_param_3
)
{
    .reg .pred      %p<2>;
    .reg .b32       %r<6>;
    .reg .b64       %rd<11>;

    ld.param.u64    %rd1, [_Z3addPiS_S_i_param_0];
    ld.param.u64    %rd2, [_Z3addPiS_S_i_param_1];
    ld.param.u64    %rd3, [_Z3addPiS_S_i_param_2];
    ld.param.u32    %r2,  [_Z3addPiS_S_i_param_3];
    mov.u32         %r3,  %ctaid.x;      // blockIdx.x
    mov.u32         %r4,  %ntid.x;       // blockDim.x
    mov.u32         %r5,  %tid.x;        // threadIdx.x
    mad.lo.s32      %r1,  %r3, %r4, %r5; // i = block * dim + thread
    setp.ge.s32     %p1,  %r1, %r2;      // if (i >= n)
    @%p1 bra        BB0_2;
    ...
```

**看不懂没关系，第 3~5 章会把每个符号讲清楚**。先记住一件事：**PTX 就是一堆"三操作数"指令**，`op.type  dst, src1, src2;`。

### 2.3 一个"看 PTX + SASS"的常备脚本

保存为 `see.sh`（Windows 下改成 `.bat`）：

```bash
#!/bin/bash
# 用法: ./see.sh kernel.cu
FILE=$1
BASE=${FILE%.cu}
nvcc -arch=sm_86 -O3 -Xptxas -v -ptx $FILE -o $BASE.ptx     2>&1 | tee $BASE.reg.log
nvcc -arch=sm_86 -O3 -cubin              $FILE -o $BASE.cubin
cuobjdump --dump-sass $BASE.cubin > $BASE.sass
echo "== PTX  : $BASE.ptx"
echo "== SASS : $BASE.sass"
echo "== 寄存器/共享内存/spill: $BASE.reg.log"
```

以后**每写一个 kernel，跑一次 `see.sh`**——这是从 CUDA 走向"懂 PTX"最快的路径。

---

## 3. PTX 编程模型：寄存器、状态空间与指令格式

### 3.1 三大要素

PTX 的世界只有三样东西：**状态空间（Space）**、**寄存器与类型**、**指令**。

#### ① 状态空间（State Space）

即"变量存在哪里"，等价于 CUDA C++ 的 `__global__` / `__shared__` / `__constant__` 等修饰符。

| 状态空间 | 关键字 | 对应 CUDA 概念 | 备注 |
|:--|:--|:--|:--|
| 全局内存 | `.global` | `__device__` 全局变量 / 传参指针指向 | 慢，但大 |
| 共享内存 | `.shared` | `__shared__` | 快，块内共享 |
| 常量内存 | `.const` | `__constant__` | 缓存友好，只读 |
| 局部内存 | `.local` | 编译器 spill 到显存的部分 | ⚠️ 出现 = 性能警告 |
| 寄存器 | `.reg` | 编译器分配的临时变量 | 最快 |
| 参数 | `.param` | kernel 参数 | 一次性只读 |

#### ② 寄存器与类型

寄存器**不是真的物理寄存器**，而是虚拟的（`ptxas` 会做寄存器分配）。写法：

```
.reg  .type  %name<count>;

.reg .pred   %p<3>;         // 3 个 1-bit 谓词
.reg .b32    %r<10>;        // 10 个 32-bit 通用
.reg .b64    %rd<5>;        // 5  个 64-bit
.reg .f32    %f<8>;         // 8  个 32-bit 浮点
```

**常见类型**：

| 类型 | 长度 | 说明 |
|:--|:--|:--|
| `.pred` | 1 bit | 谓词（true/false） |
| `.b8/.b16/.b32/.b64` | 无符号"位串" | 一般寄存器 |
| `.s8/.s16/.s32/.s64` | 有符号整数 | 带符号运算 |
| `.u8/.u16/.u32/.u64` | 无符号整数 | 无符号运算 |
| `.f16/.f32/.f64` | 浮点 | FP16/32/64 |
| `.bf16` / `.tf32` / `.e5m2` / `.e4m3` | 新格式 | Ampere 起 |

#### ③ 指令格式

**永远是三段式**：

```
[@predicate]   op.modifier.type    dst, src1, src2 [, src3];
```

例子：

```asm
add.s32     %r1, %r2, %r3;              // r1 = r2 + r3
mad.lo.s32  %r1, %r2, %r3, %r4;         // r1 = (r2 * r3) 的低 32 位 + r4
@%p1  bra   L_END;                       // 如果 p1 为真，跳到 L_END
ld.global.f32  %f1, [%rd1];              // 从全局内存 [rd1] 加载 f32
st.shared.b32  [%r5+0], %r6;             // 存到共享内存 [r5+0]
```

### 3.2 内置变量（等价于 CUDA 的 `threadIdx` 等）

| CUDA C++ | PTX 特殊寄存器 |
|:--|:--|
| `threadIdx.x/y/z` | `%tid.x/y/z` |
| `blockIdx.x/y/z` | `%ctaid.x/y/z` |
| `blockDim.x/y/z` | `%ntid.x/y/z` |
| `gridDim.x/y/z` | `%nctaid.x/y/z` |
| `warpSize` | `%WARP_SZ` (常 32) |
| `laneid` | `%laneid` |

### 3.3 最少必须记住的 10 条指令

| 指令 | 作用 | 例 |
|:--|:--|:--|
| `mov` | 拷贝 | `mov.u32 %r1, %tid.x;` |
| `ld` / `st` | 读/写内存 | `ld.global.f32 %f1, [%rd1];` |
| `add` / `sub` / `mul` | 加减乘 | `mul.lo.s32 %r1, %r2, %r3;` |
| `mad` | 乘加融合 | `mad.lo.s32 %r1,%r2,%r3,%r4;` |
| `setp` | 比较置谓词 | `setp.ge.s32 %p1, %r1, %r2;` |
| `@p bra` | 条件跳转 | `@%p1 bra L1;` |
| `cvta` | 通用/局部地址互转 | `cvta.to.global.u64 %rd2, %rd1;` |
| `cvt` | 类型转换 | `cvt.f32.s32 %f1, %r1;` |
| `bar.sync` | 块内同步 | `bar.sync 0;`（= `__syncthreads()`） |
| `mma.sync` | Tensor Core 矩阵乘加 | 见第 7 章 |

**结论**：**读 90% 的 PTX 你只要认识上面 10 条 + 3 类修饰符（`.type / .space / .mode`）**。

---

## 4. 第一份 PTX：`nvcc` 生成的向量加法长啥样

### 4.1 CUDA 源码

```cpp
// vec_add.cu
__global__ void vec_add(const float* a, const float* b, float* c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) c[i] = a[i] + b[i];
}
```

编译：

```bash
nvcc -arch=sm_86 -O3 -ptx vec_add.cu -o vec_add.ptx
```

### 4.2 逐行读 PTX（重点）

```asm
.visible .entry _Z7vec_addPKfS0_Pfi(
    .param .u64 _Z7vec_addPKfS0_Pfi_param_0,   // const float* a
    .param .u64 _Z7vec_addPKfS0_Pfi_param_1,   // const float* b
    .param .u64 _Z7vec_addPKfS0_Pfi_param_2,   // float*       c
    .param .u32 _Z7vec_addPKfS0_Pfi_param_3    // int          n
)
{
    .reg .pred %p<2>;                           // 声明：1 个谓词寄存器
    .reg .b32  %r<6>;                           // 6 个 32-bit
    .reg .f32  %f<4>;                           // 4 个 32-bit 浮点
    .reg .b64  %rd<11>;                         // 11 个 64-bit（存地址）

    // === 加载参数 ===
    ld.param.u64  %rd1, [_..._param_0];         // rd1 = a
    ld.param.u64  %rd2, [_..._param_1];         // rd2 = b
    ld.param.u64  %rd3, [_..._param_2];         // rd3 = c
    ld.param.u32  %r2,  [_..._param_3];         // r2  = n

    // === i = blockIdx.x * blockDim.x + threadIdx.x ===
    mov.u32     %r3, %ctaid.x;                  // r3 = blockIdx.x
    mov.u32     %r4, %ntid.x;                   // r4 = blockDim.x
    mov.u32     %r5, %tid.x;                    // r5 = threadIdx.x
    mad.lo.s32  %r1, %r3, %r4, %r5;             // r1 = i

    // === if (i >= n) return; ===
    setp.ge.s32 %p1, %r1, %r2;                  // p1 = (r1 >= r2)
    @%p1 bra    $L__BB0_2;                       // 真 → 跳出

    // === 计算地址：a + i*4, b + i*4, c + i*4 ===
    cvta.to.global.u64 %rd4, %rd1;              // 把通用指针转成全局地址
    mul.wide.s32       %rd5, %r1, 4;            // rd5 = i * 4（float 4 字节）
    add.s64            %rd6, %rd4, %rd5;        // rd6 = a + i*4

    cvta.to.global.u64 %rd7, %rd2;
    add.s64            %rd8, %rd7, %rd5;        // rd8 = b + i*4

    // === c[i] = a[i] + b[i] ===
    ld.global.f32  %f1, [%rd6];                 // f1 = a[i]
    ld.global.f32  %f2, [%rd8];                 // f2 = b[i]
    add.f32        %f3, %f1, %f2;               // f3 = f1 + f2

    cvta.to.global.u64 %rd9, %rd3;
    add.s64            %rd10, %rd9, %rd5;       // rd10 = c + i*4
    st.global.f32  [%rd10], %f3;                // c[i] = f3

$L__BB0_2:
    ret;
}
```

### 4.3 抓 5 个知识点

1. **`mad.lo.s32`**：一条指令完成 `a*b+c` 的低 32 位——比 `mul + add` 快，是编译器的标配；
2. **`cvta.to.global.u64`**：把 CUDA 传进来的"通用指针"转成"全局地址"，加速访存；
3. **`mul.wide.s32`**：32-bit × 32-bit → 64-bit，避免地址计算溢出；
4. **`setp` + `@%p1 bra`**：PTX 的 if/else 全靠这两条实现；
5. **寄存器命名规则**：`%r` = 32-bit 整数、`%rd` = 64-bit、`%f` = 32-bit 浮点、`%p` = 谓词——**看名字就知道类型**。

**建议动作**：把这段 PTX **手抄一遍**，比看 10 页文档管用。

---

## 5. 六类必读指令：mov / ld / st / add / mad / cvta / bar / cp.async

### 5.1 `mov` —— 拷贝一切

```asm
mov.u32   %r1, %tid.x;              // 从特殊寄存器读
mov.f32   %f1, 0f3F800000;          // 立即数：0f + IEEE754 十六进制 = 1.0
mov.b32   %r2, %r3;                 // 寄存器间拷贝
mov.u64   %rd1, sm_shared_buf;      // 取一个 .shared 变量的地址
```

### 5.2 `ld` / `st` —— 内存访问

```asm
ld.global.f32    %f1, [%rd1];              // 从全局内存读
ld.global.v4.f32 {%f1,%f2,%f3,%f4}, [%rd1]; // 128-bit 向量化读（4 个 float）
ld.shared.f32    %f1, [%r2];               // 从共享内存读
ld.const.f32     %f1, [my_const];          // 从常量内存读

st.global.f32       [%rd1], %f1;
st.global.v4.f32    [%rd1], {%f1,%f2,%f3,%f4};   // 向量化写
```

**性能要点**：`v2 / v4` 向量化访存**几乎免费**，能凑就凑——CUTLASS 全靠这个。

### 5.3 `add` / `sub` / `mul` / `mad` —— 算术

```asm
add.f32     %f1, %f2, %f3;              // 浮点加
add.s32     %r1, %r2, %r3;              // 32-bit 整加
mul.lo.s32  %r1, %r2, %r3;              // 低 32 位
mul.wide.s32 %rd1, %r2, %r3;            // 32×32 → 64
mad.lo.s32  %r1, %r2, %r3, %r4;         // r1 = r2*r3 + r4（低 32 位）
fma.rn.f32  %f1, %f2, %f3, %f4;         // 浮点乘加（Round to Nearest）
```

**重点记住 `fma`**：一条 = 一次乘 + 一次加，且**只 round 一次**（精度更高、速度也快）——**Tensor Core 前的世界靠它撑起 FLOPS**。

### 5.4 `cvta` / `cvt` —— 地址与类型转换

```asm
cvta.to.global.u64 %rd2, %rd1;      // 通用指针 → 全局地址
cvta.to.shared.u64 %rd2, %rd1;      // 通用指针 → 共享内存地址
cvt.f32.s32        %f1, %r1;        // int → float
cvt.rn.f16.f32     %h1, %f1;        // float → half（RN 舍入）
cvt.rz.s32.f32     %r1, %f1;        // float → int（RZ 向零舍入）
```

### 5.5 `bar.sync` —— 块内同步

```asm
bar.sync 0;                          // 等价于 __syncthreads()
bar.arrive 0;                        // 只到达不等待（异步屏障，Ampere+）
```

### 5.6 `cp.async` —— Ampere 起的杀手锏

```asm
// 从全局内存异步拷贝 16 字节到共享内存
cp.async.ca.shared.global [%dst], [%src], 16;
cp.async.commit_group;               // 提交一批 async 拷贝
cp.async.wait_group 0;               // 等最新一批完成
```

**为什么重要**：**这一条指令 = FlashAttention 快过普通 attention 的一半原因**。它让"从 HBM 搬到 SMEM"和"计算"能真正重叠——**没有 `cp.async`，Tensor Core 就永远等数据**。

CUDA C++ 里对应的 API 是 `__pipeline_memcpy_async()`，编译出来就是 `cp.async`。

---

## 6. 内联 PTX：在 CUDA C++ 里嵌 `asm volatile`

### 6.1 基本语法

```cpp
asm volatile("<PTX 指令模板>"
             : "=r"(out1), "=r"(out2)      // 输出操作数
             : "r"(in1),  "l"(in2)         // 输入操作数
             : "memory");                  // 副作用声明
```

**约束字符对照表**：

| 约束 | 类型 | 说明 |
|:--|:--|:--|
| `r` | `.b32` / `s32` / `u32` | 32-bit 通用寄存器 |
| `l` | `.b64` / `s64` / `u64` | 64-bit（常用于地址） |
| `h` | `.b16` | 16-bit |
| `f` | `.f32` | 单精度浮点 |
| `d` | `.f64` | 双精度浮点 |
| `n` | 立即数 | 编译期常量 |

### 6.2 例 1：手写一次 `fma`

```cpp
__device__ float my_fma(float a, float b, float c) {
    float d;
    asm volatile("fma.rn.f32 %0, %1, %2, %3;"
                 : "=f"(d)
                 : "f"(a), "f"(b), "f"(c));
    return d;
}
```

### 6.3 例 2：调 `cp.async`（Ampere 起）

```cpp
__device__ inline void cp_async_16B(void* smem_dst, const void* gmem_src) {
    uint32_t smem_ptr = __cvta_generic_to_shared(smem_dst);   // 通用地址 → SMEM 地址
    asm volatile("cp.async.ca.shared.global [%0], [%1], 16;\n"
                 :: "r"(smem_ptr), "l"(gmem_src));
}
__device__ inline void cp_async_commit() { asm volatile("cp.async.commit_group;\n"); }
__device__ inline void cp_async_wait0()  { asm volatile("cp.async.wait_group 0;\n"); }
```

**这段代码你会在任何一个高性能 GEMM/Attention 里见到**——CUTLASS、FlashAttention、cuBLAS 内核统统都是这么写的。

### 6.4 例 3：`__ldg` 的等价 PTX

```cpp
__device__ float ldg_ro(const float* ptr) {
    float v;
    asm volatile("ld.global.nc.f32 %0, [%1];"
                 : "=f"(v) : "l"(ptr));
    return v;
}
```

`ld.global.nc` = "non-coherent load"，走**只读缓存**（相当于纹理缓存）——比普通 `ld.global` 更快，适合"整个 kernel 不会写"的输入。

---

## 7. Tensor Core 直通车：`mma.sync` / `wgmma` 指令族

### 7.1 为什么要直接写 `mma`

CUDA 提供了 `wmma::` C++ API，但**限制多**（固定 shape、不支持 async pipeline）。**CUTLASS 3 全部不用 `wmma::`，全部直写 `mma.sync`**。

### 7.2 `mma.sync` 指令格式（Ampere）

```asm
mma.sync.aligned.<shape>.<layout>.<layout>.<dtype>.<dtype>.<dtype>.<dtype>
    {D0, D1, D2, D3},         // 输出（累加器，f32 x 4）
    {A0, A1, A2, A3},         // A 矩阵（f16 x 4 = 8 个 half）
    {B0, B1},                 // B 矩阵（f16 x 2 = 4 个 half）
    {C0, C1, C2, C3};         // 累加器输入
```

一个典型例子（**记这一条就够读 CUTLASS 了**）：

```asm
mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32
    {%f0,%f1,%f2,%f3},
    {%r0,%r1,%r2,%r3},
    {%r4,%r5},
    {%f0,%f1,%f2,%f3};
```

**逐段解读**：

| 字段 | 含义 |
|:--|:--|
| `m16n8k16` | **一个 warp（32 线程）**协作完成 `16×8 = 16×16 · 16×8` 的矩阵乘 |
| `row.col` | A 行主序、B 列主序 |
| `f32.f16.f16.f32` | 累加器 f32、A/B 是 f16、输出 f32 |
| 4+4+2+4 个寄存器 | 由 32 个线程**分布式**持有 |

### 7.3 Hopper 起的 `wgmma`（warp-group MMA）

- **一个 warp-group = 4 个 warp = 128 线程**协作；
- 支持**更大 shape**（m64n256k16）、**异步执行**、**直接从 SMEM 读**（不用先 `ldmatrix`）；
- FlashAttention-3、CUTLASS 3.x、cuBLAS SM90 kernel 全用这个。

**结论**：**看懂 `m16n8k16` + `wgmma` 两条**，你就能读 90% 的现代 GEMM/Attention 源码。

---

## 8. 从 PTX 到 SASS：`cuobjdump` / `nvdisasm` 反汇编实战

### 8.1 三级视角

| 级别 | 命令 | 你能看到什么 |
|:--|:--|:--|
| **CUDA C++** | 直接看源码 | 逻辑意图 |
| **PTX**（虚拟）| `nvcc -ptx` / `cuobjdump --dump-ptx` | 编译器优化后的指令 |
| **SASS**（真实）| `cuobjdump --dump-sass` / `nvdisasm` | GPU 真正执行的机器码 |

### 8.2 常用命令

```bash
# 从可执行文件反出 PTX
cuobjdump --dump-ptx  ./my_app > out.ptx

# 从可执行文件反出 SASS
cuobjdump --dump-sass ./my_app > out.sass

# 只看某个 kernel
cuobjdump --dump-sass --function _Z7vec_addPKfS0_Pfi ./my_app

# 看 cubin 的控制流图
nvdisasm -cfg my.cubin | dot -Tpng > cfg.png
```

### 8.3 一个"PTX 一样但 SASS 不一样"的例子

同一段 PTX，在 SM86 和 SM90 上：

- **SM86 (Ampere)**：`mma.sync m16n8k16` → SASS 里对应 `HMMA.16816.F32` 指令；
- **SM90 (Hopper)**：**同一条 PTX**会被驱动 JIT 翻译成 `GMMA` (Hopper 新指令) —— **这就是 PTX 前向兼容的魔力**。

**结论**：当你想问"编译器最后到底做了什么"，答案永远在 **SASS** 里；但**能改能优化的层级**是 **PTX**。

---

## 9. 性能优化：靠 PTX 能多挤出多少？

### 9.1 三条常见收益（按投入产出比排序）

| 优化 | 收益 | 难度 |
|:--|:--|:--|
| **`-Xptxas -v` 消除 register spill** | 常常 10~30% | ⭐ 低（改 launch bounds / 减寄存器） |
| **手写 `cp.async` 拷贝流水**（如果编译器没识别到） | 5~15% | ⭐⭐ 中 |
| **手写 `mma.sync` / `ldmatrix` 组合**（CUTLASS 式） | 5~20%（相对 `wmma::`） | ⭐⭐⭐ 高 |
| **手工指令调度**（改 PTX 顺序绕 stall） | 通常 <5%，只在极端场景 | ⭐⭐⭐⭐ 极高 |

### 9.2 关注 `-Xptxas -v` 的三个数字

```
ptxas info    : Compiling entry function '_Z...'
ptxas info    : Function properties for _Z...
    128 bytes stack frame, 96 bytes spill stores, 96 bytes spill loads  ← ⚠️ 有 spill
ptxas info    : Used 64 registers, 8192 bytes smem
                    ↑                    ↑
              寄存器用量           共享内存用量
```

**三条黄金规则**：

1. **`spill stores/loads > 0`** → 编译器把变量甩到了显存（`.local`）→ 慢；
2. **`Used registers`** 越低 → 每个 SM 能同时跑的 block 越多 → occupancy 越高；
3. **两者需要权衡**：不是寄存器越少越好——够用最好。

### 9.3 案例：一个 kernel 从 60% → 85% 的过程

1. 看到 spill → 加 `__launch_bounds__(256, 4)`，寄存器降到 63 → spill 消失，提 12%；
2. Nsight 看到 "Long Scoreboard" → 加 `cp.async` 双缓冲，提 8%；
3. 把 `wmma::` 换成手写 `mma.sync + ldmatrix`，提 6%；
4. **合计提升 ~28%，从 60% 打到 85% cuBLAS。**

**结论**：**PTX 不是加速万能药，但是"看懂 → 定位 → 精修"的必经之路**。

---

## 10. 学习路线图（3~4 周）

### Week 1：认识 PTX（P1 → P2 阅读级）

- **Day 1~2**：跑通第 2 章的 `nvcc -ptx` + `see.sh`，读第 4 章的 vec_add PTX，**手抄一遍**；
- **Day 3~4**：读第 3、5 章 —— 状态空间、类型、10 条指令；
- **Day 5~7**：找 3~5 个你写过的 kernel（reduce / softmax / gemm），生成 PTX 读一遍。

### Week 2：内联 PTX（P2 → P3）

- **Day 8~10**：第 6 章内联 `asm`：改写 `fma`、`ldg`、`cp.async`；
- **Day 11~14**：给自己的一个已有 kernel **加 `cp.async` 双缓冲**，用 Nsight 对比前后性能。

### Week 3：Tensor Core（进阶 P3）

- **Day 15~17**：第 7 章 `mma.sync`——写一个**手动 mma 版 GEMM**，对比 `wmma::` 版；
- **Day 18~21**：读 CUTLASS 里 `mma_atom.hpp` 或 FlashAttention 的 PTX 内联部分，**逐行注释**。

### Week 4：SASS + 优化（P3 收官）

- **Day 22~24**：第 8 章反汇编：读 SASS，找 spill 与 stall；
- **Day 25~28**：把 Week 2/3 的成果做**一次完整性能报告**：Nsight 前后指标 + PTX 改动清单。

**通关标准**：能给自己写的一个 kernel 从 CUDA C++ 层做出 15%+ 的性能提升，并能说清是"哪条 PTX 起的作用"。

---

## 11. 精选资源与踩坑清单

### 11.1 官方文档（唯一权威）

- **PTX ISA 手册**（每代 CUDA 一份，必备）
    - <https://docs.nvidia.com/cuda/parallel-thread-execution/>
- **Inline PTX Assembly in CUDA**
    - <https://docs.nvidia.com/cuda/inline-ptx-assembly/>
- **CUDA Binary Utilities**（`cuobjdump` / `nvdisasm` 用法）
    - <https://docs.nvidia.com/cuda/cuda-binary-utilities/>

### 11.2 高质量二手资料

- **CUTLASS 源码** —— 世界上最好的 PTX 教科书之一（`include/cute/atom/mma_atom.hpp`、`cutlass/arch/mma_sm80.h`）；
- **FlashAttention** 的 CUDA 版源码：搜索 `asm volatile` 就是它的 PTX 精华；
- **Sebastian Aaltonen** 和 **Simon Boehm**（`siboehm/SGEMM_CUDA`）的博客：手把手把 PTX 挤到 cuBLAS 90%+。

### 11.3 常见踩坑

1. **`asm volatile` 里忘 `volatile`** → 编译器可能优化掉你辛苦写的 PTX；
2. **约束字符写错**（`r` vs `l` vs `f`）→ 编译期报"invalid operand"，仔细对第 6 章表；
3. **`cp.async` 忘 `commit + wait`** → 数据没到就算 → 结果乱码；
4. **共享内存指针没走 `__cvta_generic_to_shared`** → `cp.async` 会报非法地址；
5. **改了 `-arch=sm_86` 又想跑 SM90** → 记得加 `-gencode arch=compute_86,code=sm_86 -gencode arch=compute_90,code=compute_90`（后者留 PTX 让驱动 JIT）；
6. **PTX 里立即数写法**：`0f3F800000` = 1.0f（前缀 `0f` + IEEE754 hex），不是 `1.0`；
7. **`mma.sync` 的输入寄存器分布是"32 线程分摊"**：不是每个线程都拿到 A 的全部——先啃 PTX 手册的 "Matrix Fragments" 那一节。

---

## 结语

> **PTX 不是让你重新造轮子的语言，而是一副"眼镜"**——戴上它，你能看清编译器做了什么、Tensor Core 在算什么、CUTLASS 为什么快。
>
> 学到 **P2** 层次，你就已经比 95% 的 CUDA 程序员懂得深；学到 **P3**，你就能在关键路径上给团队挤出 15%+ 的性能。
>
> 记住：**先读 → 再嵌 → 少手写。让编译器做 99%，你做那关键的 1%。**

---

**版权声明**：本文由汪亮（bertonwang）原创，转载请注明来源。欢迎邮件交流：<47608843@qq.com>。
