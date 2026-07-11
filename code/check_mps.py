#!/usr/bin/env python3
"""
检查 M1 Mac 的 MPS (Metal Performance Shaders) 可用性
MPS 是 Apple 的 GPU 计算框架，作为 CUDA 的替代方案
"""

import torch

def main():
    print("=" * 60)
    print("M1 Mac GPU (MPS) 可用性检查")
    print("=" * 60)
    
    # 检查 MPS 是否可用
    print(f"\n[1] MPS 可用性检查:")
    print(f"    MPS 可用: {torch.backends.mps.is_available()}")
    print(f"    MPS 已构建: {torch.backends.mps.is_built()}")
    
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        print(f"\n✅ [2] MPS 设备已就绪")
        print(f"    设备: {device}")
        
        # 创建一个张量并移动到 MPS
        print(f"\n[3] 测试张量操作:")
        x = torch.randn(3, 3).to(device)
        y = torch.randn(3, 3).to(device)
        z = x + y
        
        print(f"    张量 x 设备: {x.device}")
        print(f"    张量 y 设备: {y.device}")
        print(f"    张量 z = x + y 设备: {z.device}")
        print(f"\n    张量 x:\n{x.cpu().numpy()}")
        print(f"\n    张量 y:\n{y.cpu().numpy()}")
        print(f"\n    张量 z = x + y:\n{z.cpu().numpy()}")
        
        # 检查内存
        print(f"\n[4] MPS 内存信息:")
        allocated = torch.mps.current_allocated_memory() / 1024**2
        print(f"    当前已分配内存: {allocated:.2f} MB")
        
    else:
        print("\n❌ MPS 不可用")
        print("    可能的原因:")
        print("    1. 您的 Mac 不支持 Metal (2012 年前的设备)")
        print("    2. PyTorch 版本不支持 MPS (需要 PyTorch 1.12+)")
        print("    3. 在虚拟机或远程环境中运行")
        print("\n    解决方案:")
        print("    1. 更新 PyTorch: pip install --upgrade torch")
        print("    2. 确保您在真实的 Mac 设备上 (不是虚拟机)")
        print("    3. 使用 CPU 作为后备方案")
        
        device = torch.device("cpu")
        print(f"\n⚠️  将使用 CPU 设备: {device}")
    
    print("\n" + "=" * 60)
    print("检查完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
