# M1 Mac GPU 编程入门指南

> **重要说明**：Apple M1 芯片不支持 NVIDIA CUDA。本指南介绍如何在 M1 Mac 上使用 GPU 进行并行计算，使用 PyTorch 的 MPS (Metal Performance Shaders) 后端。

## 目录
1. [M1 GPU 编程概述](#1-m1-gpu-编程概述)
2. [环境准备](#2-环境准备)
3. [基础概念](#3-基础概念)
4. [实战示例](#4-实战示例)
5. [性能对比](#5-性能对比)
6. [进阶主题](#6-进阶主题)

---

## 1. M1 GPU 编程概述

### 1.1 为什么 M1 不能用 CUDA？
- **CUDA** 是 NVIDIA 专有技术，仅支持 NVIDIA GPU
- **M1 芯片** 使用 Apple 自研 GPU，基于 ARM 架构
- **替代方案**：
  - ✅ **Metal** - Apple 官方 GPU 编程框架
  - ✅ **PyTorch MPS** - 使用 Metal 后端的 PyTorch（推荐）
  - ✅ **TensorFlow Metal** - TensorFlow 的 Metal 支持
  - ❌ CUDA - 不支持

### 1.2 MPS 是什么？
- **MPS (Metal Performance Shaders)** 是 Apple 的 GPU 计算框架
- PyTorch 2.0+ 原生支持 MPS 后端
- 性能接近 CUDA（在 M1 上）

---

## 2. 环境准备

### 2.1 安装 PyTorch (支持 MPS)

```bash
# 创建 conda 环境
conda create -n m1-gpu python=3.10
conda activate m1-gpu

# 安装 PyTorch (支持 MPS)
pip install torch torchvision torchaudio

# 验证安装
python -c "import torch; print(f'PyTorch version: {torch.__version__}')"
```

### 2.2 验证 MPS 可用性

创建 `check_mps.py`：

```python
import torch

# 检查 MPS 是否可用
print(f"MPS 可用: {torch.backends.mps.is_available()}")
print(f"MPS 内置: {torch.backends.mps.is_built()}")

if torch.backends.mps.is_available():
    device = torch.device("mps")
    print(f"✅ 使用设备: {device}")
    
    # 创建一个张量并移动到 MPS
    x = torch.randn(3, 3).to(device)
    print(f"张量在 MPS 上: {x.device}")
    print(f"张量值:\n{x}")
else:
    print("❌ MPS 不可用，使用 CPU")
```

运行：
```bash
python check_mps.py
```

---

## 3. 基础概念

### 3.1 CPU vs GPU (MPS) 对比

| 特性 | CPU | GPU (MPS) |
|------|-----|-----------|
| 核心数 | 8-10 核 | 数百到数千个计算单元 |
| 擅长 | 串行任务、逻辑控制 | 并行计算、矩阵运算 |
| 适用场景 | 复杂逻辑、分支多 | 大规模数据并行处理 |

### 3.2 PyTorch 设备迁移

```python
import torch

# 设备选择
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

# 张量移动到 GPU
x = torch.randn(1000, 1000).to(device)

# 模型移动到 GPU
model = MyModel().to(device)
```

### 3.3 基本操作示例

创建 `basic_operations.py`：

```python
import torch
import time

# 设备选择
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"使用设备: {device}")

# 创建大矩阵
size = 10000
a = torch.randn(size, size, device=device)
b = torch.randn(size, size, device=device)

# 矩阵乘法计时
start = time.time()
c = torch.mm(a, b)
end = time.time()

print(f"矩阵乘法 ({size}x{size}) 耗时: {end - start:.4f} 秒")
print(f"结果张量设备: {c.device}")
```

---

## 4. 实战示例

### 示例 1：向量加法 (Hello World)

创建 `vector_addition.py`：

```python
import torch
import numpy as np

# 设备选择
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"使用设备: {device}\n")

# 创建大向量
n = 1000000  # 100 万元素
a = torch.randn(n, device=device)
b = torch.randn(n, device=device)

# GPU 向量加法
start = torch.cuda.Event(enable_timing=True) if device.type == "cuda" else None
end = torch.cuda.Event(enable_timing=True) if device.type == "cuda" else None

if start and end:
    start.record()
    c = a + b
    end.record()
    torch.cuda.synchronize()
    gpu_time = start.elapsed_time(end)
else:
    import time
    start = time.time()
    c = a + b
    # MPS 需要同步以确保计算完成
    if device.type == "mps":
        torch.mps.synchronize()
    end = time.time()
    gpu_time = (end - start) * 1000  # 转换为毫秒

print(f"✅ GPU 向量加法完成")
print(f"向量大小: {n}")
print(f"前 5 个结果: {c[:5].cpu().numpy()}")
print(f"耗时: {gpu_time:.2f} ms")

# CPU 对比
a_cpu = a.cpu()
b_cpu = b.cpu()
start = time.time()
c_cpu = a_cpu + b_cpu
cpu_time = (time.time() - start) * 1000

print(f"\n✅ CPU 向量加法完成")
print(f"耗时: {cpu_time:.2f} ms")
print(f"加速比: {cpu_time / gpu_time:.2f}x")
```

### 示例 2：矩阵乘法性能测试

创建 `matrix_multiplication.py`：

```python
import torch
import time

def benchmark_matmul(size, device, iterations=100):
    """基准测试矩阵乘法"""
    a = torch.randn(size, size, device=device)
    b = torch.randn(size, size, device=device)
    
    # 预热
    for _ in range(10):
        torch.mm(a, b)
    
    if device.type == "mps":
        torch.mps.synchronize()
    
    # 正式测试
    start = time.time()
    for _ in range(iterations):
        c = torch.mm(a, b)
    
    if device.type == "mps":
        torch.mps.synchronize()
    
    end = time.time()
    avg_time = (end - start) / iterations * 1000  # ms
    
    return avg_time

# 主程序
print("=" * 60)
print("M1 GPU (MPS) 矩阵乘法性能测试")
print("=" * 60)

# 检查 MPS 可用性
if not torch.backends.mps.is_available():
    print("❌ MPS 不可用，请安装支持 MPS 的 PyTorch")
    exit(1)

devices = [
    torch.device("cpu"),
    torch.device("mps")
]

sizes = [512, 1024, 2048, 4096]

print(f"{'矩阵大小':<15} {'CPU (ms)':<15} {'MPS (ms)':<15} {'加速比':<10}")
print("-" * 60)

for size in sizes:
    cpu_time = benchmark_matmul(size, devices[0])
    mps_time = benchmark_matmul(size, devices[1])
    speedup = cpu_time / mps_time
    
    print(f"{size}x{size:<10} {cpu_time:<15.2f} {mps_time:<15.2f} {speedup:<10.2f}x")

print("\n✅ 测试完成！")
```

### 示例 3：图像处理 - 高斯模糊

创建 `image_blur.py`：

```python
import torch
import torch.nn.functional as F
import time

# 设备选择
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"使用设备: {device}\n")

# 创建模拟图像 (批量, 通道, 高, 宽)
batch_size = 10
channels = 3
height, width = 2048, 2048

print(f"图像处理基准测试")
print(f"图像大小: {height}x{width}, 批量: {batch_size}")
print(f"总像素数: {batch_size * channels * height * width:,}\n")

# 创建随机图像
image = torch.randn(batch_size, channels, height, width, device=device)

# 创建高斯核
def gaussian_kernel(kernel_size=5, sigma=1.0):
    """创建高斯核"""
    ax = torch.arange(kernel_size) - kernel_size // 2
    xx, yy = torch.meshgrid(ax, ax, indexing='ij')
    kernel = torch.exp(-(xx**2 + yy**2) / (2 * sigma**2))
    kernel = kernel / kernel.sum()
    return kernel

# 在 CPU 上创建核，然后移到 GPU
kernel = gaussian_kernel(5, 1.0).to(device)
kernel = kernel.view(1, 1, 5, 5)
kernel = kernel.repeat(channels, 1, 1, 1)

# GPU 高斯模糊
start = time.time()
blurred = F.conv2d(image, kernel, padding=2, groups=channels)
if device.type == "mps":
    torch.mps.synchronize()
gpu_time = time.time() - start

print(f"✅ GPU 高斯模糊完成")
print(f"耗时: {gpu_time:.4f} 秒")
print(f"输出形状: {blurred.shape}")

# CPU 对比
image_cpu = image.cpu()
kernel_cpu = kernel.cpu()
start = time.time()
blurred_cpu = F.conv2d(image_cpu, kernel_cpu, padding=2, groups=channels)
cpu_time = time.time() - start

print(f"\n✅ CPU 高斯模糊完成")
print(f"耗时: {cpu_time:.4f} 秒")
print(f"加速比: {cpu_time / gpu_time:.2f}x")
```

### 示例 4：神经网络训练

创建 `neural_network.py`：

```python
import torch
import torch.nn as nn
import torch.optim as optim
import time

# 设备选择
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"使用设备: {device}\n")

# 定义简单的神经网络
class SimpleNet(nn.Module):
    def __init__(self, input_size=784, hidden_size=512, num_classes=10):
        super(SimpleNet, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, num_classes)
    
    def forward(self, x):
        x = x.view(x.size(0), -1)  # 展平
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x

# 创建模型和优化器
model = SimpleNet().to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 创建模拟数据
batch_size = 128
num_batches = 100

print(f"神经网络训练基准测试")
print(f"批量大小: {batch_size}")
print(f"迭代次数: {num_batches}\n")

# 训练循环
start = time.time()
model.train()

for batch_idx in range(num_batches):
    # 生成随机数据
    data = torch.randn(batch_size, 1, 28, 28, device=device)
    target = torch.randint(0, 10, (batch_size,), device=device)
    
    # 前向传播
    optimizer.zero_grad()
    output = model(data)
    loss = criterion(output, target)
    
    # 反向传播
    loss.backward()
    optimizer.step()
    
    if (batch_idx + 1) % 20 == 0:
        print(f"批次 [{batch_idx + 1}/{num_batches}], Loss: {loss.item():.4f}")

if device.type == "mps":
    torch.mps.synchronize()

end = time.time()
training_time = end - start

print(f"\n✅ 训练完成")
print(f"总耗时: {training_time:.2f} 秒")
print(f"平均每批次: {training_time / num_batches * 1000:.2f} ms")

# 测试推理
model.eval()
with torch.no_grad():
    test_data = torch.randn(1000, 1, 28, 28, device=device)
    start = time.time()
    output = model(test_data)
    if device.type == "mps":
        torch.mps.synchronize()
    inference_time = time.time() - start

print(f"\n✅ 推理测试 (1000 样本)")
print(f"推理耗时: {inference_time * 1000:.2f} ms")
print(f"每秒处理: {1000 / inference_time:.2f} 样本")
```

---

## 5. 性能对比

### 5.1 运行所有示例

创建 `run_all.py` 来运行所有示例：

```python
import subprocess
import sys

examples = [
    "check_mps.py",
    "basic_operations.py",
    "vector_addition.py",
    "matrix_multiplication.py",
    "image_blur.py",
    "neural_network.py"
]

print("=" * 60)
print("运行所有 M1 GPU 编程示例")
print("=" * 60)

for example in examples:
    print(f"\n{'=' * 60}")
    print(f"运行: {example}")
    print("=" * 60)
    
    try:
        subprocess.run([sys.executable, example], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 运行失败: {e}")
    except FileNotFoundError:
        print(f"❌ 文件不存在: {example}")

print(f"\n{'=' * 60}")
print("所有示例运行完成！")
print("=" * 60)
```

### 5.2 预期性能提升

在 M1 Mac 上，您可以预期：

| 操作 | CPU | MPS (GPU) | 加速比 |
|------|-----|-----------|--------|
| 向量加法 | ~10 ms | ~1 ms | 10x |
| 矩阵乘法 (4096x4096) | ~2000 ms | ~50 ms | 40x |
| 卷积 (图像模糊) | ~500 ms | ~20 ms | 25x |
| 神经网络训练 | ~100 ms/批次 | ~10 ms/批次 | 10x |

---

## 6. 进阶主题

### 6.1 内存管理

```python
# 查看 MPS 内存使用
print(f"已分配内存: {torch.mps.current_allocated_memory() / 1024**2:.2f} MB")

# 清空缓存
torch.mps.empty_cache()
```

### 6.2 混合精度训练

```python
# 使用半精度 (float16) 加速训练
model = model.half()
data = data.half()
```

### 6.3 数据并行 (多个 M1 GPU)

```python
# M1 通常只有一个 GPU，但可以使用 DataParallel 进行模拟
# 注意：M1 不支持多 GPU，这只是示例
if torch.cuda.device_count() > 1:
    model = nn.DataParallel(model)
```

### 6.4 与 CUDA 代码对比

如果您以后有机会使用 NVIDIA GPU，以下是 CUDA 和 MPS 的代码对比：

| 操作 | CUDA (NVIDIA) | MPS (Apple M1) |
|------|---------------|----------------|
| 设备选择 | `torch.device("cuda")` | `torch.device("mps")` |
| 检查可用性 | `torch.cuda.is_available()` | `torch.backends.mps.is_available()` |
| 同步 | `torch.cuda.synchronize()` | `torch.mps.synchronize()` |
| 清空缓存 | `torch.cuda.empty_cache()` | `torch.mps.empty_cache()` |

---

## 7. 常见问题

### Q1: 为什么我的代码还是运行在 CPU 上？
**A**: 确保已将张量和模型移动到 MPS 设备：
```python
device = torch.device("mps")
x = x.to(device)
model = model.to(device)
```

### Q2: MPS 支持所有 PyTorch 操作吗？
**A**: 不是所有操作都支持。如果遇到错误，可以暂时移回 CPU：
```python
x = x.cpu()
# 执行不支持的操作
x = x.to(device)
```

### Q3: 如何最大化利用 M1 GPU？
**A**: 
- 使用大批量数据（充分利用并行性）
- 使用半精度 (float16)
- 避免频繁的 CPU-GPU 数据传输

---

## 8. 总结

✅ **您学到了什么**：
1. M1 Mac 不支持 CUDA，但可以使用 MPS
2. 如何使用 PyTorch MPS 进行 GPU 编程
3. 向量加法、矩阵乘法、图像处理、神经网络训练
4. 性能优化技巧

🚀 **下一步**：
- 尝试更复杂的神经网络模型
- 学习 Metal 框架（如果需要更低级的控制）
- 如果有 NVIDIA GPU，学习 CUDA C++ 编程

---

## 附录：完整代码下载

所有示例代码已创建在当前目录下，可以直接运行：

```bash
# 运行检查脚本
python check_mps.py

# 运行向量加法示例
python vector_addition.py

# 运行矩阵乘法基准测试
python matrix_multiplication.py

# 运行图像处理示例
python image_blur.py

# 运行神经网络训练示例
python neural_network.py
```

---

**祝学习愉快！** 🎉

如有问题，请参考：
- [PyTorch MPS 官方文档](https://pytorch.org/docs/stable/notes/mps.html)
- [Apple Metal 文档](https://developer.apple.com/metal/)
