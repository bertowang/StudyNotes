# PyTorch 自定义 CUDA 算子学习指南：打通 Kernel 与 Model 的最后一公里

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
>
> **面向读者**：会写 CUDA / Triton kernel、但不知道怎么把它接进 PyTorch 训练/推理流水线的 AI 工程师。
> **目标**：读完本文，你能用 4 种主流方式（Triton 直接调、`torch.library`、CUDA Extension、`torch.compile` 后端注册）把自己的 kernel 接进 PyTorch，还知道 autograd/dispatcher/CUDA stream 三大对齐要点。

---

## 目录

- [0. 写在最前：为什么这层桥梁必须懂](#0-写在最前为什么这层桥梁必须懂)
- [1. 四种接入姿势总览](#1-四种接入姿势总览)
- [2. 方式一：Triton kernel 直接嵌入](#2-方式一triton-kernel-直接嵌入)
- [3. 方式二：torch.library（现代推荐方式）](#3-方式二torchlibrary现代推荐方式)
- [4. 方式三：CUDA Extension（cpp_extension）](#4-方式三cuda-extensioncpp_extension)
- [5. 方式四：CUDA C++ + PYBIND11 手写打包](#5-方式四cuda-c--pybind11-手写打包)
- [6. 三大对齐要点：autograd / dispatcher / stream](#6-三大对齐要点autograd--dispatcher--stream)
- [7. torch.compile 后端注册（进阶）](#7-torchcompile-后端注册进阶)
- [8. 常见坑与调试技巧](#8-常见坑与调试技巧)
- [9. 学习路线图（3~4 周）](#9-学习路线图34-周)
- [10. 精选资源与官方链接](#10-精选资源与官方链接)

---

## 0. 写在最前：为什么这层桥梁必须懂

**痛点场景**：

- 你花两周写了个 SOTA 的 FlashAttention 变体（Triton 版），性能超越官方 30%；
- 结果发现——**没法直接放进你的 Transformer 里！**
- 因为你还不知道：
  - 怎么让 `x.grad_fn` 自动记录你的 kernel？
  - 怎么让它支持 `torch.compile`？
  - 怎么让它支持 `.cuda()` 迁移 device？
  - 怎么让它支持 `torch.jit.script` 导出？

**这就是"自定义算子"层要解决的问题**——把裸 kernel 变成 PyTorch 的"一等公民"。

**懂了这层，你才是完整的 GPU 算子工程师**：
- 上游（Model）：能把新算子无缝接入 Transformer/Diffusion；
- 中游（Autograd）：能写 backward、支持训练；
- 下游（Kernel）：能对接 Triton/CUDA/CUTLASS。

### 0.1 一句话总结

> **PyTorch 自定义算子 = "把你的 kernel 用 `torch.library` 注册一下"**——现代方式 5 行代码就能让 `torch.compile`、autograd、`.cuda()` 全部生效。老式的 `cpp_extension` 只在需要极致性能或特殊 C++ 依赖时才用。

### 0.2 学到什么程度算"够用"？

| 级别 | 能力标志 |
|:--|:--|
| **G1 认知** | 说清 4 种方式的区别与适用场景 |
| **G2 会用** | 能用 `torch.library` 把 Triton kernel 接入 PyTorch，支持 autograd |
| **G3 会写** | 能写 CUDA Extension + 完整 forward/backward |
| **G4 会调** | 能对接 `torch.compile`、fake tensor、dynamo、meta kernel |

**建议**：读完本文你到 **G2**，配合手写 1~2 个算子冲到 **G3**。

---

## 1. 四种接入姿势总览

| 方式 | 何时用 | 学习成本 | 性能 | PyTorch 版本 |
|:--|:--|:--|:--|:--|
| **① Triton kernel 直接调** | 快速原型、纯 GPU 操作 | ⭐ | 好 | ≥ 1.11 |
| **② `torch.library`** ⭐ | 现代推荐，支持 `torch.compile` | ⭐⭐ | 最好 | ≥ 2.4 |
| **③ CUDA Extension** | 需要复杂 C++ 依赖 / CUTLASS | ⭐⭐⭐ | 最好 | 全部 |
| **④ 手写 PYBIND11 + setup** | 极特殊场景 / 老项目 | ⭐⭐⭐⭐ | 最好 | 全部 |

**决策树**：

```
你写的 kernel 是什么？
    │
    ├─ Python 层的 Triton kernel
    │     ├─ 只是 forward → 直接调（方式一）
    │     └─ 要 autograd 或 torch.compile → torch.library（方式二）
    │
    ├─ CUDA C++ 手写 / CUTLASS
    │     ├─ PyTorch >= 2.4 → torch.library.custom_op（方式二 + C++）
    │     └─ PyTorch < 2.4 或老项目 → cpp_extension（方式三）
    │
    └─ 要跨框架用（TensorRT 也要）
          └─ 单独打包 .so + pybind11（方式四）
```

---

## 2. 方式一：Triton kernel 直接嵌入

**最简单**——Triton kernel 是纯 Python，直接调即可：

```python
import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(x_ptr, y_ptr, out_ptr, N, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    mask = offs < N
    x = tl.load(x_ptr + offs, mask=mask)
    y = tl.load(y_ptr + offs, mask=mask)
    tl.store(out_ptr + offs, x + y, mask=mask)


def triton_add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    N = x.numel()
    grid = lambda meta: (triton.cdiv(N, meta['BLOCK']),)
    add_kernel[grid](x, y, out, N, BLOCK=1024)
    return out

# 使用
a = torch.randn(1000, device='cuda')
b = torch.randn(1000, device='cuda')
c = triton_add(a, b)   # ✅ 直接可用
```

**问题**：
- ❌ 没有 autograd（`c.backward()` 会报错）；
- ❌ `torch.compile(triton_add)` 无法优化；
- ❌ 不支持 `torch.jit.script`。

**适用**：Kernel 内联在 Python 中、只做推理、不需要求导。

---

## 3. 方式二：torch.library（现代推荐方式）

**PyTorch 2.4+ 的官方推荐**，10 行代码搞定一切。

### 3.1 完整示例：Triton kernel + autograd + torch.compile

```python
import torch
from torch.library import custom_op, register_fake

# ① 注册算子（forward）
@custom_op("mylib::triton_add", mutates_args=())
def triton_add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    N = x.numel()
    add_kernel[(triton.cdiv(N, 1024),)](x, y, out, N, BLOCK=1024)
    return out

# ② 注册 fake kernel（给 torch.compile / meta device 用）
@register_fake("mylib::triton_add")
def _(x, y):
    return torch.empty_like(x)

# ③ 注册反向传播
def setup_context(ctx, inputs, output):
    ctx.save_for_backward(*inputs)

def backward(ctx, grad_out):
    return grad_out, grad_out   # d(x+y)/dx = 1, d(x+y)/dy = 1

triton_add.register_autograd(backward, setup_context=setup_context)

# ✅ 现在这个算子全能：
a = torch.randn(1000, device='cuda', requires_grad=True)
b = torch.randn(1000, device='cuda', requires_grad=True)
c = triton_add(a, b)
c.sum().backward()   # ✅ 支持 autograd
compiled = torch.compile(triton_add)   # ✅ 支持 torch.compile
```

### 3.2 三大关键装饰器

| 装饰器 | 作用 |
|:--|:--|
| `@custom_op` | 注册 forward + 声明 schema（输入输出类型）|
| `@register_fake` | 注册"假 kernel"给 dynamo / meta tensor 用 |
| `.register_autograd()` | 注册 backward |

### 3.3 mutates_args：告诉 PyTorch 你改了什么

```python
# 如果算子原地修改某个输入：
@custom_op("mylib::relu_", mutates_args=("x",))
def relu_(x: torch.Tensor) -> None:
    ...
```

**不写 `mutates_args` = PyTorch 假设是纯函数**（可以被 CSE、reorder 优化）。写错 = 崩溃。

---

## 4. 方式三：CUDA Extension（cpp_extension）

**用于需要复杂 C++（如引入 CUTLASS）的场景**。

### 4.1 项目结构

```
myops/
├── setup.py
├── myops/
│   └── __init__.py
└── src/
    ├── add_cuda.cpp     # C++ 接口
    └── add_kernel.cu    # CUDA kernel
```

### 4.2 CUDA kernel（add_kernel.cu）

```cpp
#include <cuda.h>
#include <cuda_runtime.h>

__global__ void add_kernel(const float* x, const float* y, float* out, int N) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) out[idx] = x[idx] + y[idx];
}

void add_cuda_launch(const float* x, const float* y, float* out, int N, cudaStream_t stream) {
    int block = 256;
    int grid = (N + block - 1) / block;
    add_kernel<<<grid, block, 0, stream>>>(x, y, out, N);
}
```

### 4.3 C++ 接口（add_cuda.cpp）

```cpp
#include <torch/extension.h>
#include <ATen/cuda/CUDAContext.h>

void add_cuda_launch(const float*, const float*, float*, int, cudaStream_t);

torch::Tensor add_cuda(torch::Tensor x, torch::Tensor y) {
    TORCH_CHECK(x.is_cuda() && y.is_cuda(), "Inputs must be CUDA");
    TORCH_CHECK(x.sizes() == y.sizes(), "Shape mismatch");
    auto out = torch::empty_like(x);
    auto stream = at::cuda::getCurrentCUDAStream();
    add_cuda_launch(
        x.data_ptr<float>(), y.data_ptr<float>(), out.data_ptr<float>(),
        x.numel(), stream
    );
    return out;
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("add_cuda", &add_cuda, "Add two tensors (CUDA)");
}
```

### 4.4 setup.py

```python
from setuptools import setup
from torch.utils.cpp_extension import BuildExtension, CUDAExtension

setup(
    name='myops',
    ext_modules=[
        CUDAExtension(
            name='myops._C',
            sources=['src/add_cuda.cpp', 'src/add_kernel.cu'],
        ),
    ],
    cmdclass={'build_ext': BuildExtension},
)
```

### 4.5 编译 & 使用

```bash
pip install -e .
```

```python
from myops._C import add_cuda
c = add_cuda(a, b)
```

### 4.6 JIT 模式（不用 setup.py）

**开发调试时更方便**：

```python
from torch.utils.cpp_extension import load

myops = load(
    name='myops',
    sources=['src/add_cuda.cpp', 'src/add_kernel.cu'],
    verbose=True,
)
c = myops.add_cuda(a, b)
```

---

## 5. 方式四：CUDA C++ + PYBIND11 手写打包

**极少用**——只在完全脱离 PyTorch 依赖时才需要（比如你想把同一份 .so 卖给 TensorRT 用户和 PyTorch 用户）。

```cpp
// 直接用 pybind11，不 include torch/extension.h
#include <pybind11/pybind11.h>
namespace py = pybind11;

PYBIND11_MODULE(mylib, m) {
    m.def("add_cuda_raw", &add_cuda_raw);  // 接受裸指针
}
```

Python 侧再手写 `torch.Tensor -> void*` 的转换。**大部分场景没必要**。

---

## 6. 三大对齐要点：autograd / dispatcher / stream

### 6.1 Autograd：正确写 backward

**核心原则**：**forward 里出现过的张量运算，backward 都要还回去**。

```python
def setup_context(ctx, inputs, output):
    # 保存 backward 需要的东西（尽量少）
    x, y = inputs
    ctx.save_for_backward(x, y)
    ctx.some_scalar = 3.14   # 非张量存 ctx 属性

def backward(ctx, grad_out):
    x, y = ctx.saved_tensors
    grad_x = grad_out * y     # d(x*y)/dx = y
    grad_y = grad_out * x
    return grad_x, grad_y    # 顺序对应 forward 的 inputs
```

**常见错误**：

| 错误 | 后果 |
|:--|:--|
| 忘记 `save_for_backward` | 反向时张量已释放，报错 |
| 保存了整个 activation | 显存爆炸（能重算就不要存）|
| 返回值数量不对 | 报错 |
| 返回 None 但 forward 有 requires_grad | 梯度丢失 |

### 6.2 Dispatcher：让算子支持多 device

```python
@custom_op("mylib::add", mutates_args=())
def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    ...

# 分别为不同 device 注册实现
@add.register_kernel("cuda")
def _(x, y):
    return triton_add_cuda(x, y)

@add.register_kernel("cpu")
def _(x, y):
    return x + y   # CPU 走 PyTorch 原生

# 用户不用管 device，自动 dispatch
```

### 6.3 CUDA Stream：不要抢别人的流

**每次启动 kernel，必须用当前 PyTorch stream**：

```cpp
// C++ 里
auto stream = at::cuda::getCurrentCUDAStream();
my_kernel<<<grid, block, 0, stream>>>(...);   // ✅

// ❌ 错误：用了默认流，会破坏 PyTorch 的异步流水线
my_kernel<<<grid, block>>>(...);
```

**Python 里同样**：

```python
stream = torch.cuda.current_stream()
with torch.cuda.stream(stream):
    kernel[grid](...)
```

---

## 7. torch.compile 后端注册（进阶）

如果你想让 `torch.compile` **自动选中你的算子**（而不只是"能编过"），需要注册到 Inductor：

```python
from torch._inductor.lowering import register_lowering

@register_lowering(torch.ops.mylib.triton_add)
def _(x, y):
    # 告诉 Inductor 怎么用它降级
    ...
```

**极小众**，只在写自定义硬件后端 / 深度定制 Inductor 时才用到。

---

## 8. 常见坑与调试技巧

### 8.1 十大常见坑

| # | 坑 | 表现 | 修法 |
|:--:|:--|:--|:--|
| 1 | 忘写 `register_fake` | `torch.compile` 报错 "no meta kernel" | 加上假实现 |
| 2 | forward 的 output 不 contiguous | backward 时 stride 错乱 | `output.contiguous()` |
| 3 | 忘 sync 就打印 | 数据还没算完就读 | `torch.cuda.synchronize()` |
| 4 | schema 类型错 | dispatch 找不到 | 严格 hint `torch.Tensor` |
| 5 | 用了 `torch.no_grad` 但注册了 autograd | 反向丢失 | 拆分 fwd/bwd |
| 6 | CUDA Extension 每次改代码都重编译很慢 | 开发效率低 | 用 JIT `load()` |
| 7 | Nsight 找不到你的 kernel | 没标 NVTX | 加 `torch.cuda.nvtx.range` |
| 8 | 多 GPU 时 stream 错 | 结果不确定 | 一定 `getCurrentCUDAStream` |
| 9 | fp16/bf16 溢出 | NaN | 关键累加用 fp32 |
| 10 | mutates_args 写错 | `torch.compile` 结果错 | 严格声明 |

### 8.2 调试三板斧

1. **eager 模式先跑通**：先关掉 `torch.compile`，确认逻辑对；
2. **对齐 PyTorch reference**：写个 `torch_add(x, y) = x + y`，用 `torch.allclose` 验证；
3. **gradcheck 验证**：`torch.autograd.gradcheck(fn, (x, y))` 自动数值验证 backward。

---

## 9. 学习路线图（3~4 周）

### Week 1：Triton + torch.library 入门
- 写一个 vector add 的 Triton kernel；
- 用 `torch.library.custom_op` 注册；
- 加 backward，用 `gradcheck` 验证；
- 用 `torch.compile` 测速。

### Week 2：CUDA Extension
- 装 CUDA toolkit；
- 用 `cpp_extension.load` JIT 编译一个 kernel；
- 熟悉 `torch::Tensor` C++ API、`at::cuda::getCurrentCUDAStream`；
- 打包 setup.py，发到 pip 试试。

### Week 3：接入真实模型
- 挑一个你 Transformer 里的层（如 LayerNorm），自己重写 CUDA kernel；
- 用 `torch.library` 注册、加 backward；
- 用 Nsight 对比新旧 kernel 性能；
- 端到端跑 mini-GPT，验证 loss 收敛。

### Week 4（可选）：进阶
- 读 vLLM 的 `csrc/` 目录，学工业级 CUDA Extension；
- 学 `torch.compile` 后端 lowering 注册；
- 尝试 CUTLASS + PyTorch 集成。

---

## 10. 精选资源与官方链接

### 10.1 官方文档
- **PyTorch Custom Ops Tutorial**：<https://pytorch.org/tutorials/advanced/custom_ops_landing_page.html>
- **torch.library 文档**：<https://pytorch.org/docs/stable/library.html>
- **cpp_extension 文档**：<https://pytorch.org/tutorials/advanced/cpp_extension.html>
- **Dispatcher 机制**：<https://pytorch.org/tutorials/advanced/dispatcher.html>

### 10.2 优秀开源例子
- **vLLM `csrc/`**：<https://github.com/vllm-project/vllm/tree/main/csrc>（工业级 CUDA Ext）
- **flash-attn**：<https://github.com/Dao-AILab/flash-attention>（cpp_extension 典范）
- **xFormers**：<https://github.com/facebookresearch/xformers>（多算子打包）
- **triton-lang tutorials**：<https://triton-lang.org/main/getting-started/tutorials/>

### 10.3 姊妹篇
- [Triton 编程学习指南](./Triton编程学习指南.md)（Kernel 层）
- [面向 AI 的 CUDA 编程学习指南](./CUDA-AI编程学习指南.md)（CUDA C++ 基础）
- [torch.compile 编程学习指南](./torch.compile编程学习指南.md)（Inductor 后端）
- [Nsight 性能分析学习指南](./Nsight性能分析学习指南.md)（性能剖析）
- [FlashAttention 源码学习指南](./FlashAttention源码学习指南.md)（复杂算子实战）

---

**版权声明**：本文由汪亮（bertonwang）撰写，转载请注明出处。欢迎邮件（<47608843@qq.com>）交流勘误。

**一句话总结全文**：**PyTorch 自定义算子 = 把 kernel 变成 PyTorch 一等公民**——现代方式用 `torch.library` 5 行搞定 autograd + torch.compile；老式方式用 `cpp_extension`；两者对齐 autograd/dispatcher/stream 三大要点，你的 kernel 就能无缝进 Transformer/Diffusion 训练流水线。
