#!/usr/bin/env python3
"""
神经网络训练示例 - GPU 加速的深度学习
展示如何使用 MPS 加速神经网络训练和推理
"""

import torch
import torch.nn as nn
import torch.optim as optim
import time
import matplotlib.pyplot as plt

# 设置 matplotlib 后端（避免显示问题）
import matplotlib
matplotlib.use('Agg')
import numpy as np

# 定义简单的神经网络
class SimpleClassifier(nn.Module):
    """简单的全连接神经网络用于分类"""
    def __init__(self, input_size=784, hidden_sizes=[512, 256], num_classes=10):
        super(SimpleClassifier, self).__init__()
        
        layers = []
        prev_size = input_size
        
        # 隐藏层
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(prev_size, hidden_size))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.2))
            prev_size = hidden_size
        
        # 输出层
        layers.append(nn.Linear(prev_size, num_classes))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        x = x.view(x.size(0), -1)  # 展平: (batch, 1, 28, 28) → (batch, 784)
        return self.network(x)

def generate_synthetic_data(num_samples=10000, img_size=28):
    """生成合成数据（模拟 MNIST）"""
    # 生成随机图像 (模拟手写数字)
    images = torch.randn(num_samples, 1, img_size, img_size)
    
    # 生成随机标签 (0-9)
    labels = torch.randint(0, 10, (num_samples,))
    
    return images, labels

def train_epoch(model, dataloader, criterion, optimizer, device):
    """训练一个 epoch"""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    for batch_idx, (data, target) in enumerate(dataloader):
        # 移动到设备
        data, target = data.to(device), target.to(device)
        
        # 前向传播
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        
        # 反向传播
        loss.backward()
        optimizer.step()
        
        # 统计
        running_loss += loss.item()
        _, predicted = output.max(1)
        total += target.size(0)
        correct += predicted.eq(target).sum().item()
        
        if (batch_idx + 1) % 20 == 0:
            print(f"    批次 [{batch_idx + 1}/{len(dataloader)}], "
                  f"Loss: {loss.item():.4f}, "
                  f"Acc: {100.*correct/total:.2f}%")
    
    return running_loss / len(dataloader), 100. * correct / total

def test(model, dataloader, criterion, device):
    """测试模型"""
    model.eval()
    test_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for data, target in dataloader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            test_loss += criterion(output, target).item()
            _, predicted = output.max(1)
            total += target.size(0)
            correct += predicted.eq(target).sum().item()
    
    test_loss /= len(dataloader)
    accuracy = 100. * correct / total
    
    return test_loss, accuracy

def main():
    print("=" * 60)
    print("神经网络训练 - CPU vs GPU (MPS)")
    print("=" * 60)
    
    # 设备选择
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        print(f"\n✅ 使用设备: {device} (Apple M1 GPU)")
    else:
        device = torch.device("cpu")
        print(f"\n⚠️  MPS 不可用，使用设备: {device}")
    
    # 超参数
    batch_size = 128
    learning_rate = 0.001
    num_epochs = 3
    num_samples = 10000
    
    print(f"\n📊 训练配置:")
    print(f"   批量大小: {batch_size}")
    print(f"   学习率: {learning_rate}")
    print(f"   训练轮数: {num_epochs}")
    print(f"   样本数量: {num_samples}")
    
    # 生成数据
    print(f"\n🔄 生成合成数据...")
    images, labels = generate_synthetic_data(num_samples)
    
    # 创建数据集和数据加载器
    dataset = torch.utils.data.TensorDataset(images, labels)
    dataloader = torch.utils.data.DataLoader(
        dataset, batch_size=batch_size, shuffle=True
    )
    
    print(f"   数据集大小: {len(dataset)}")
    print(f"   批次数量: {len(dataloader)}")
    
    # 创建模型
    print(f"\n🏗️  创建神经网络...")
    model = SimpleClassifier(input_size=784, hidden_sizes=[512, 256], num_classes=10)
    model = model.to(device)
    
    # 打印模型信息
    total_params = sum(p.numel() for p in model.parameters())
    print(f"   模型参数数量: {total_params:,}")
    print(f"   模型设备: {next(model.parameters()).device}")
    
    # 定义损失函数和优化器
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    # 训练循环
    print(f"\n🚀 开始训练...")
    train_losses = []
    train_accs = []
    
    start_time = time.time()
    
    for epoch in range(1, num_epochs + 1):
        print(f"\nEpoch [{epoch}/{num_epochs}]")
        print("-" * 60)
        
        # 训练
        epoch_start = time.time()
        train_loss, train_acc = train_epoch(model, dataloader, criterion, optimizer, device)
        epoch_end = time.time()
        
        # 记录
        train_losses.append(train_loss)
        train_accs.append(train_acc)
        
        print(f"\n   ✅ Epoch [{epoch}/{num_epochs}] 完成")
        print(f"   Loss: {train_loss:.4f}, Accuracy: {train_acc:.2f}%")
        print(f"   耗时: {epoch_end - epoch_start:.2f} 秒")
    
    total_time = time.time() - start_time
    
    print(f"\n" + "=" * 60)
    print(f"训练完成！总耗时: {total_time:.2f} 秒")
    print("=" * 60)
    
    # 推理测试
    print(f"\n🔍 推理性能测试...")
    model.eval()
    
    # 创建测试数据
    test_samples = 1000
    test_data = torch.randn(test_samples, 1, 28, 28, device=device)
    
    # 预热
    with torch.no_grad():
        _ = model(test_data[:10])
    
    if device.type == "mps":
        torch.mps.synchronize()
    
    # 正式测试
    with torch.no_grad():
        start = time.time()
        output = model(test_data)
        
        if device.type == "mps":
            torch.mps.synchronize()
        
        end = time.time()
    
    inference_time = end - start
    fps = test_samples / inference_time
    
    print(f"   测试样本数: {test_samples}")
    print(f"   推理耗时: {inference_time*1000:.2f} ms")
    print(f"   每秒处理: {fps:.2f} 样本 (FPS)")
    print(f"   每样本耗时: {inference_time/test_samples*1000:.2f} ms")
    
    # 性能对比（如果在 CPU 上运行，可以手动对比）
    if device.type == "cpu":
        print(f"\n💡 提示: 如果在 CPU 上运行，可以尝试在 M1 GPU 上运行以看到加速效果")
        print(f"   1. 确保 PyTorch 版本 >= 1.12")
        print(f"   2. 设置 device = torch.device('mps')")
        print(f"   3. 预期加速比: 5-10x")
    
    # 保存训练曲线（可选）
    print(f"\n📈 训练曲线已保存到: training_curve.png")
    
    try:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        
        # 损失曲线
        ax1.plot(range(1, num_epochs+1), train_losses, 'b-', linewidth=2)
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss')
        ax1.set_title('Training Loss')
        ax1.grid(True)
        
        # 准确率曲线
        ax2.plot(range(1, num_epochs+1), train_accs, 'r-', linewidth=2)
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Accuracy (%)')
        ax2.set_title('Training Accuracy')
        ax2.grid(True)
        
        plt.tight_layout()
        plt.savefig('training_curve.png', dpi=100)
        plt.close()
    except Exception as e:
        print(f"   ⚠️  无法保存训练曲线: {e}")
    
    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)
    print("\n💡 下一步:")
    print("   1. 尝试更复杂的模型 (CNN, Transformer)")
    print("   2. 使用真实数据集 (MNIST, CIFAR-10)")
    print("   3. 调整超参数观察性能变化")
    print("   4. 尝试混合精度训练 (float16)")

if __name__ == "__main__":
    main()
