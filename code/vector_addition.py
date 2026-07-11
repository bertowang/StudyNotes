#!/usr/bin/env python3
"""
向量加法示例 - GPU 编程的 Hello World
对比 CPU 和 GPU (MPS) 的性能差异
"""

import torch
import time
import numpy as np

def vector_addition_cpu(n):
    """CPU 向量加法"""
    a = np.random.randn(n)
    b = np.random.randn(n)
    
    start = time.time()
    c = a + b
    end = time.time()
    
    return end - start, c

def vector_addition_gpu(n, device):
    """GPU (MPS) 向量加法"""
    a = torch.randn(n, device=device)
    b = torch.randn(n, device=device)
    
    # 预热
    _ = a + b
    if device.type == "mps":
        torch.mps.synchronize()
    
    # 正式测试
    start = time.time()
    c = a + b
    
    # 同步以确保计算完成
    if device.type == "mps":
        torch.mps.synchronize()
    
    end = time.time()
    
    return end - start, c.cpu().numpy()

def main():
    print("=" * 60)
    print("向量加法性能测试 - CPU vs GPU (MPS)")
    print("=" * 60)
    
    # 设备选择
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        print(f"\n✅ 使用设备: {device} (Apple M1 GPU)")
    else:
        device = torch.device("cpu")
        print(f"\n⚠️  MPS 不可用，使用设备: {device}")
    
    # 测试不同大小的向量
    vector_sizes = [
        1_000,          # 1K
        100_000,        # 100K
        1_000_000,      # 1M
        10_000_000,     # 10M
        100_000_000,    # 100M
    ]
    
    print(f"\n{'向量大小':<20} {'CPU 时间 (ms)':<20} {'GPU 时间 (ms)':<20} {'加速比':<10}")
    print("-" * 70)
    
    for n in vector_sizes:
        # CPU 测试
        cpu_time, _ = vector_addition_cpu(n)
        
        # GPU 测试
        if device.type == "mps":
            gpu_time, _ = vector_addition_gpu(n, device)
        else:
            gpu_time = cpu_time  # 如果 MPS 不可用，使用 CPU 时间
        
        # 计算加速比
        speedup = cpu_time / gpu_time if gpu_time > 0 else 0
        
        print(f"{n:<20,} {cpu_time*1000:<20.4f} {gpu_time*1000:<20.4f} {speedup:<10.2f}x")
    
    # 详细示例：小的向量
    print("\n" + "=" * 60)
    print("详细示例：向量加法 (n=10)")
    print("=" * 60)
    
    n = 10
    a = torch.randn(n, device=device)
    b = torch.randn(n, device=device)
    c = a + b
    
    print(f"\n向量 a: {a.cpu().numpy()}")
    print(f"向量 b: {b.cpu().numpy()}")
    print(f"向量 c = a + b: {c.cpu().numpy()}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n💡 提示:")
    print("   - 向量越大，GPU 的并行优势越明显")
    print("   - 小数组时，CPU 可能更快（数据传输开销）")
    print("   - 实际使用中，尽量批量处理大数据")

if __name__ == "__main__":
    main()
