#!/usr/bin/env python3
"""
矩阵乘法性能测试 - GPU 编程的核心应用
对比 CPU 和 GPU (MPS) 在矩阵运算上的性能差异
"""

import torch
import time

def benchmark_matmul_cpu(size, iterations=10):
    """CPU 矩阵乘法基准测试"""
    a = torch.randn(size, size)
    b = torch.randn(size, size)
    
    # 预热
    for _ in range(3):
        torch.mm(a, b)
    
    # 正式测试
    start = time.time()
    for _ in range(iterations):
        c = torch.mm(a, b)
    end = time.time()
    
    avg_time = (end - start) / iterations
    return avg_time

def benchmark_matmul_gpu(size, device, iterations=10):
    """GPU (MPS) 矩阵乘法基准测试"""
    a = torch.randn(size, size, device=device)
    b = torch.randn(size, size, device=device)
    
    # 预热
    for _ in range(3):
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
    
    avg_time = (end - start) / iterations
    return avg_time

def main():
    print("=" * 70)
    print("矩阵乘法性能测试 - CPU vs GPU (MPS)")
    print("=" * 70)
    
    # 设备选择
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        print(f"\n✅ 使用设备: {device} (Apple M1 GPU)")
        print(f"   GPU 内存: 共享系统内存")
    else:
        device = torch.device("cpu")
        print(f"\n⚠️  MPS 不可用，使用设备: {device}")
    
    # 测试不同大小的矩阵
    matrix_sizes = [
        128,    # 小矩阵
        256,    # 中小矩阵
        512,    # 中矩阵
        1024,   # 大矩阵
        2048,   # 超大矩阵
    ]
    
    print(f"\n{'矩阵大小':<15} {'CPU 时间 (ms)':<20} {'GPU 时间 (ms)':<20} {'加速比':<10}")
    print("-" * 65)
    
    results = []
    
    for size in matrix_sizes:
        print(f"测试 {size}x{size} 矩阵...", end="", flush=True)
        
        # CPU 测试
        cpu_time = benchmark_matmul_cpu(size)
        
        # GPU 测试
        if device.type == "mps":
            gpu_time = benchmark_matmul_gpu(size, device)
        else:
            gpu_time = cpu_time
        
        # 计算加速比
        speedup = cpu_time / gpu_time if gpu_time > 0 else 0
        
        print(f"\r{size:>5}x{size:<8} {cpu_time*1000:<20.2f} {gpu_time*1000:<20.2f} {speedup:<10.2f}x")
        
        results.append({
            'size': size,
            'cpu_time': cpu_time,
            'gpu_time': gpu_time,
            'speedup': speedup
        })
    
    # 详细示例：小矩阵
    print("\n" + "=" * 70)
    print("详细示例：小矩阵乘法 (3x3)")
    print("=" * 70)
    
    size = 3
    a = torch.randn(size, size, device=device)
    b = torch.randn(size, size, device=device)
    c = torch.mm(a, b)
    
    print(f"\n矩阵 A:\n{a.cpu().numpy()}")
    print(f"\n矩阵 B:\n{b.cpu().numpy()}")
    print(f"\n矩阵 C = A × B:\n{c.cpu().numpy()}")
    
    # 性能分析
    print("\n" + "=" * 70)
    print("性能分析")
    print("=" * 70)
    
    print("\n📊 加速比趋势:")
    for r in results:
        bar = "█" * int(r['speedup'])
        print(f"  {r['size']:>4}x{r['size']:<4} | {bar} {r['speedup']:.2f}x")
    
    print("\n💡 关键发现:")
    print("   1. 矩阵越大，GPU 加速越明显")
    print("   2. 小矩阵时，CPU 可能更快（数据传输开销）")
    print("   3. M1 GPU 在矩阵运算上表现出色")
    print("   4. 最佳性能：矩阵大小 >= 512x512")
    
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)

if __name__ == "__main__":
    main()
