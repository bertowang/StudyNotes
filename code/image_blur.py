#!/usr/bin/env python3
"""
图像处理示例 - GPU 加速的高斯模糊
展示如何使用 GPU 进行实际的图像处理任务
"""

import torch
import torch.nn.functional as F
import time
import numpy as np

def gaussian_kernel(kernel_size=5, sigma=1.0, device="cpu"):
    """创建高斯核"""
    ax = torch.arange(kernel_size) - kernel_size // 2
    xx, yy = torch.meshgrid(ax, ax, indexing='ij')
    kernel = torch.exp(-(xx**2 + yy**2) / (2 * sigma**2))
    kernel = kernel / kernel.sum()
    return kernel.to(device)

def apply_gaussian_blur_cpu(image, kernel_size=5, sigma=1.0):
    """CPU 高斯模糊"""
    # 创建高斯核
    kernel = gaussian_kernel(kernel_size, sigma, "cpu")
    kernel = kernel.view(1, 1, kernel_size, kernel_size)
    kernel = kernel.repeat(3, 1, 1, 1)  # 3 通道
    
    # 应用卷积
    start = time.time()
    blurred = F.conv2d(image, kernel, padding=kernel_size//2, groups=3)
    end = time.time()
    
    return blurred, end - start

def apply_gaussian_blur_gpu(image, device, kernel_size=5, sigma=1.0):
    """GPU (MPS) 高斯模糊"""
    # 创建高斯核并移到 GPU
    kernel = gaussian_kernel(kernel_size, sigma, device)
    kernel = kernel.view(1, 1, kernel_size, kernel_size)
    kernel = kernel.repeat(3, 1, 1, 1)
    
    # 图像已在 GPU 上
    # 应用卷积
    start = time.time()
    blurred = F.conv2d(image, kernel, padding=kernel_size//2, groups=3)
    
    # 同步
    if device.type == "mps":
        torch.mps.synchronize()
    
    end = time.time()
    
    return blurred, end - start

def create_test_image(size=512, device="cpu"):
    """创建测试图像（带噪声的渐变图）"""
    # 创建坐标网格
    y, x = torch.meshgrid(
        torch.linspace(0, 1, size),
        torch.linspace(0, 1, size),
        indexing='ij'
    )
    
    # 创建 RGB 通道
    r = x  # 红色通道：水平渐变
    g = y  # 绿色通道：垂直渐变
    b = (x + y) / 2  # 蓝色通道：对角渐变
    
    # 添加噪声
    noise = torch.randn(size, size) * 0.1
    r = r + noise
    g = g + noise
    b = b + noise
    
    # 裁剪到 [0, 1]
    r = torch.clamp(r, 0, 1)
    g = torch.clamp(g, 0, 1)
    b = torch.clamp(b, 0, 1)
    
    # 组合成图像 (3, H, W)
    image = torch.stack([r, g, b], dim=0)
    
    # 添加批次维度 (1, 3, H, W)
    image = image.unsqueeze(0)
    
    return image.to(device)

def main():
    print("=" * 60)
    print("GPU 加速图像处理 - 高斯模糊")
    print("=" * 60)
    
    # 设备选择
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        print(f"\n✅ 使用设备: {device} (Apple M1 GPU)")
    else:
        device = torch.device("cpu")
        print(f"\n⚠️  MPS 不可用，使用设备: {device}")
    
    # 测试不同大小的图像
    image_sizes = [
        (256, 256),
        (512, 512),
        (1024, 1024),
        (2048, 2048),
    ]
    
    print(f"\n{'图像大小':<15} {'CPU 时间 (ms)':<20} {'GPU 时间 (ms)':<20} {'加速比':<10}")
    print("-" * 65)
    
    for height, width in image_sizes:
        print(f"创建 {width}x{height} 图像...", end="", flush=True)
        
        # CPU 测试
        image_cpu = create_test_image(min(width, height), "cpu")
        _, cpu_time = apply_gaussian_blur_cpu(image_cpu)
        
        # GPU 测试
        if device.type == "mps":
            image_gpu = create_test_image(min(width, height), device)
            _, gpu_time = apply_gaussian_blur_gpu(image_gpu, device)
        else:
            gpu_time = cpu_time
        
        # 计算加速比
        speedup = cpu_time / gpu_time if gpu_time > 0 else 0
        
        print(f"\r{width:>4}x{height:<10} {cpu_time*1000:<20.2f} {gpu_time*1000:<20.2f} {speedup:<10.2f}x")
    
    # 详细示例：小图像
    print("\n" + "=" * 60)
    print("详细示例：小图像高斯模糊")
    print("=" * 60)
    
    # 创建小图像
    size = 8
    image = create_test_image(size, device)
    
    print(f"\n原始图像 (8x8, 裁剪显示):")
    print(f"  红色通道 (前 8x8):")
    print(image[0, 0, :5, :5].cpu().detach().numpy())
    
    # 应用高斯模糊
    blurred, gpu_time = apply_gaussian_blur_gpu(image, device, kernel_size=3, sigma=1.0)
    
    print(f"\n模糊后图像 (GPU 耗时: {gpu_time*1000:.2f} ms):")
    print(f"  红色通道 (前 8x8):")
    print(blurred[0, 0, :5, :5].cpu().detach().numpy())
    
    # 保存结果（可选）
    print("\n" + "=" * 60)
    print("实际应用建议")
    print("=" * 60)
    print("\n📝 图像处理流程:")
    print("   1. 加载图像: PIL/OpenCV → NumPy → Torch Tensor")
    print("   2. 移动到 GPU: tensor.to('mps')")
    print("   3. 批处理: 一次处理多张图像")
    print("   4. 应用滤波: conv2d, pool 等")
    print("   5. 移回 CPU: tensor.cpu()")
    print("   6. 保存结果: Torch Tensor → PIL/OpenCV")
    
    print("\n⚡ 性能优化:")
    print("   - 使用大批量 (batch_size >= 4)")
    print("   - 避免频繁 CPU-GPU 数据传输")
    print("   - 使用半精度 (float16) 减少内存占用")
    print("   - 重用高斯核等常量张量")
    
    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
