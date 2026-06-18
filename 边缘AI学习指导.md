# 边缘AI（Edge AI）学习指导

> **作者**：汪亮 bertonwang  
> **邮箱**：47608843@qq.com  
> **日期**：2026年6月
> **版本**：v1.0


## 目录

- [一、什么是边缘AI？](#一什么是边缘ai)
- [二、为什么需要边缘AI？](#二为什么需要边缘ai)
- [三、核心概念与术语](#三核心概念与术语)
- [四、硬件平台全景](#四硬件平台全景)
- [五、软件框架与工具链](#五软件框架与工具链)
- [六、模型优化技术](#六模型优化技术)
- [七、端侧部署实战](#七端侧部署实战)
- [八、典型应用场景](#八典型应用场景)
- [九、性能评估方法论](#九性能评估方法论)
- [十、进阶专题](#十进阶专题)
- [十一、学习路线图](#十一学习路线图)
- [十二、推荐资源](#十二推荐资源)

---

## 一、什么是边缘AI？

### 1.1 一句话定义

> **边缘AI** = 在靠近数据产生的地方（而非云端）运行 AI 推理/训练的技术体系。

### 1.2 直觉理解

```
传统云AI：
  摄像头 → 网络上传 → 云服务器推理 → 结果返回 → 执行动作
  延迟：100ms ~ 数秒

边缘AI：
  摄像头 → 本地芯片推理 → 立即执行动作
  延迟：1ms ~ 50ms
```

类比：
- **云AI** 像打电话问总部要答案——准确但慢
- **边缘AI** 像自己脑子直接做决定——快但资源有限

### 1.3 边缘的"边"在哪里？

```
┌─────────────────────────────────────────────────────┐
│                    云端 (Cloud)                       │
│         GPU集群、大模型训练、海量存储                   │
└──────────────────────┬──────────────────────────────┘
                       │ 网络
┌──────────────────────┴──────────────────────────────┐
│                 边缘服务器 (Edge Server)              │
│       工厂机房、5G基站、CDN节点                        │
│       算力：数十~数百 TOPS                            │
└──────────────────────┬──────────────────────────────┘
                       │ 局域网/总线
┌──────────────────────┴──────────────────────────────┐
│              边缘设备 (Edge Device)                   │
│    手机、摄像头、无人机、MCU、可穿戴设备                │
│    算力：0.1 ~ 数十 TOPS                             │
└─────────────────────────────────────────────────────┘
```

---

## 二、为什么需要边缘AI？

### 2.1 核心驱动力

| 驱动力 | 说明 | 量化对比 |
|--------|------|----------|
| **低延迟** | 自动驾驶刹车决策不能等云端 | 云端 200ms vs 边缘 5ms |
| **隐私保护** | 数据不出设备，合规（GDPR等） | 数据泄露风险降低 100% |
| **带宽节省** | 不传原始视频/音频到云端 | 1080p视频 5Mbps → 推理结果 1Kbps |
| **离线可用** | 无网环境也能工作 | 矿井、海上、偏远地区 |
| **成本降低** | 减少云端算力和带宽费用 | 大规模部署节省 60%~90% 运营成本 |

### 2.2 不适合边缘AI的场景

- 需要超大模型（如 GPT-4 级别 1.8T 参数）
- 需要跨设备全局数据聚合分析
- 对精度要求极高且算力不受限
- 模型需要频繁更新（每小时级别）

---

## 三、核心概念与术语

### 3.1 基础术语表

| 术语 | 含义 | 小白理解 |
|------|------|----------|
| **推理 (Inference)** | 用训练好的模型做预测 | 考试（用学到的知识答题） |
| **训练 (Training)** | 用数据教模型学习 | 学习（看书做题积累知识） |
| **TOPS** | 每秒万亿次操作 | 衡量AI芯片算力的单位 |
| **INT8 / FP16 / FP32** | 数据精度格式 | 精度越低→速度越快→准确度略降 |
| **量化 (Quantization)** | 降低模型数值精度 | 把高清图压缩成标清，省空间 |
| **剪枝 (Pruning)** | 去掉模型中不重要的连接 | 删掉书中的废话，保留精华 |
| **蒸馏 (Distillation)** | 大模型教小模型 | 名师带徒弟，徒弟学精髓 |
| **NPU** | 神经网络处理单元 | 专门跑AI的芯片模块 |
| **FLOPS** | 每秒浮点运算次数 | 通用算力指标 |
| **Latency** | 单次推理延迟 | 从输入到输出的时间 |
| **Throughput** | 吞吐量 | 每秒能处理多少个样本 |

### 3.2 精度格式详解

```
FP32（32位浮点）：
  ┌─┬────────┬───────────────────────┐
  │S│ 8位指数 │      23位尾数          │  → 精度最高，体积最大
  └─┴────────┴───────────────────────┘

FP16（16位浮点）：
  ┌─┬─────┬──────────┐
  │S│5位指数│ 10位尾数  │  → 精度适中，速度快2倍
  └─┴─────┴──────────┘

INT8（8位整数）：
  ┌────────┐
  │ 8位整数 │  → 精度最低，速度快4倍，体积缩小4倍
  └────────┘

INT4（4位整数）：
  ┌────┐
  │4位 │  → 极致压缩，适合大语言模型边缘部署
  └────┘
```

**精度 vs 性能权衡**：

| 精度 | 模型大小 | 推理速度 | 精度损失 | 适用场景 |
|------|----------|----------|----------|----------|
| FP32 | 100% | 1× | 0% | 训练、精度敏感任务 |
| FP16 | 50% | ~2× | <0.1% | GPU推理标配 |
| INT8 | 25% | ~4× | <1% | 边缘部署主流 |
| INT4 | 12.5% | ~8× | 1%~3% | 极端资源受限 |

---

## 四、硬件平台全景

### 4.1 主流边缘AI芯片分类

```
                    边缘AI硬件
                       │
        ┌──────────────┼──────────────┐
        │              │              │
    通用处理器      专用加速器       FPGA
    (CPU/GPU)      (NPU/TPU)
        │              │              │
   ┌────┴────┐    ┌────┴────┐    ┌───┴───┐
   │ARM Cortex│   │Google TPU│   │Xilinx │
   │x86 低功耗│   │华为昇腾  │   │Intel  │
   │RISC-V   │   │寒武纪   │    │Lattice│
   │Jetson GPU│   │地平线   │    └───────┘
   └─────────┘   │瑞芯微   │
                  │高通 HTP │
                  └─────────┘
```

### 4.2 主流平台对比

| 平台 | 算力 | 功耗 | 价格 | 适用场景 | 入门难度 |
|------|------|------|------|----------|----------|
| **Raspberry Pi 5** | 2 TOPS (CPU) | 5~12W | ¥400 | 学习、原型验证 | ⭐ |
| **Google Coral** | 4 TOPS (TPU) | 2W | ¥500 | 图像分类、目标检测 | ⭐⭐ |
| **NVIDIA Jetson Nano** | 472 GFLOPS | 5~10W | ¥800 | 入门级视觉AI | ⭐⭐ |
| **NVIDIA Jetson Orin Nano** | 40 TOPS | 7~15W | ¥1500 | 多路视频分析 | ⭐⭐⭐ |
| **NVIDIA Jetson AGX Orin** | 275 TOPS | 15~60W | ¥1万+ | 自动驾驶、机器人 | ⭐⭐⭐⭐ |
| **Rockchip RK3588** | 6 TOPS (NPU) | 5~10W | ¥300 | 安防、智能家居 | ⭐⭐ |
| **高通 QCS6490** | 12 TOPS | 5W | - | 智能摄像头 | ⭐⭐⭐ |
| **STM32 + X-CUBE-AI** | ~数百 MOPS | <1W | ¥50 | 传感器AI、关键词检测 | ⭐⭐⭐ |
| **ESP32-S3** | ~数十 MOPS | <0.5W | ¥20 | 语音唤醒、简单分类 | ⭐⭐ |

### 4.3 如何选择硬件？

```
决策树：

你的模型多大？
├── < 100KB → MCU（STM32、ESP32）
├── 100KB ~ 10MB → 轻量NPU（Coral、RK3588）
├── 10MB ~ 100MB → 中端GPU/NPU（Jetson Orin Nano）
└── > 100MB → 高端平台（Jetson AGX Orin）

你的延迟要求？
├── < 1ms → FPGA 或专用 ASIC
├── 1~10ms → NPU/GPU
└── > 10ms → CPU 也可能够用

你的功耗预算？
├── < 1W → MCU + 小模型
├── 1~10W → 移动级 NPU
└── 10~60W → 桌面级 GPU
```

---

## 五、软件框架与工具链

### 5.1 全景图

```
训练阶段                    优化阶段                    部署阶段
┌──────────┐           ┌──────────────┐          ┌──────────────┐
│PyTorch   │           │TensorRT      │          │NVIDIA Jetson │
│TensorFlow│  ──转换──→ │ONNX Runtime  │ ──部署──→ │Android/iOS   │
│JAX       │           │OpenVINO      │          │MCU (TFLite)  │
│PaddlePaddle│         │TFLite        │          │FPGA          │
└──────────┘           │NCNN          │          │浏览器(WASM)  │
                       │MNN           │          └──────────────┘
                       └──────────────┘
```

### 5.2 主流推理框架对比

| 框架 | 厂商 | 目标硬件 | 特点 | 适合谁 |
|------|------|----------|------|--------|
| **TensorRT** | NVIDIA | NVIDIA GPU | 极致优化，速度最快 | Jetson 用户 |
| **ONNX Runtime** | Microsoft | 跨平台 | 通用性强，生态好 | 需要跨平台部署 |
| **OpenVINO** | Intel | Intel CPU/GPU/VPU | Intel 硬件首选 | x86 边缘服务器 |
| **TFLite** | Google | ARM CPU/GPU/Coral | 移动端标配 | Android/MCU |
| **NCNN** | 腾讯 | ARM CPU | 极致轻量，无依赖 | 手机端、嵌入式 |
| **MNN** | 阿里 | ARM CPU/GPU | 高性能，支持训练 | 移动端全场景 |
| **RKNN** | 瑞芯微 | RK系列NPU | 专用优化 | RK3588 等平台 |
| **Paddle Lite** | 百度 | 多平台 | 中文生态好 | 国产硬件适配 |

#### 这些框架能互通吗？需要针对不同手机各自开发吗？

> **核心结论**：模型训练只需做一次，但部署时确实需要根据目标硬件选择对应的推理框架。不过，业界已经有成熟的方案来降低这个成本。

**现状：框架之间确实不能直接互通**

```
同一个模型，不能直接在不同框架之间"即插即用"：

  TensorRT 的 .engine 文件  ──✗──→  无法在 TFLite 上运行
  TFLite 的 .tflite 文件   ──✗──→  无法在 NCNN 上运行
  NCNN 的 .param/.bin      ──✗──→  无法在 Core ML 上运行

原因：每个框架有自己的模型格式、算子实现、优化策略，
      就像 .doc 文件不能直接用 WPS 的内核打开 Pages 一样。
```

**但是！有"中间格式"解决这个问题——ONNX**

```
ONNX（Open Neural Network Exchange）= AI界的"PDF格式"

训练框架（只需训练一次）
├── PyTorch  ──导出──→ ┐
├── TensorFlow ─导出─→ ├──→  ONNX（通用中间格式）
└── PaddlePaddle ─导出→ ┘           │
                                     │ 转换（自动化工具）
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
              TensorRT          TFLite            NCNN
            (NVIDIA设备)      (Android/iOS)     (ARM手机)
                    ▼                ▼                ▼
              Jetson Nano       Pixel手机         小米手机
```

**实际开发中的三种策略**：

| 策略 | 做法 | 适合场景 | 工作量 |
|------|------|----------|--------|
| **策略一：ONNX Runtime 一把梭** | 直接用 ONNX Runtime 部署，它支持几乎所有平台 | 对性能要求不极致 | ⭐ 最小 |
| **策略二：统一训练 + 多端转换** | 训练一次 → 导出 ONNX → 用脚本自动转换为各平台格式 | 需要极致性能 | ⭐⭐ 中等 |
| **策略三：跨平台框架封装** | 用 MNN/Paddle Lite 等本身就支持多平台的框架 | 国内多设备适配 | ⭐⭐ 中等 |

**具体到手机端的情况**：

| 手机平台 | 推荐框架 | 是否需要单独开发？ |
|----------|----------|-------------------|
| **iPhone (iOS)** | Core ML | ✅ 需要 Swift/ObjC 代码，但模型可从 ONNX 自动转换 |
| **Android (高通)** | TFLite / NCNN / MNN | ✅ 需要 Java/Kotlin 代码，模型从 ONNX 转换 |
| **Android (联发科)** | NeuroPilot / TFLite | 同上，框架选择略有不同 |
| **华为 (麒麟)** | MindSpore Lite / MNN | 同上，华为有自己的 NPU SDK |

> **关键点**：模型本身（算法逻辑）只开发一次，但"胶水代码"（调用摄像头、显示结果、调用推理框架的代码）确实需要按平台分别写。这和普通 App 开发面临的跨平台问题是一样的。

**降低重复开发成本的实用方案**：

```
方案1：Flutter/React Native + 推理插件
  → 业务UI跨平台，只有推理部分用原生代码
  → 推理部分通常只有几十行，工作量不大

方案2：C++ 统一推理层
  → 用 C++ 写推理逻辑（调用 NCNN/MNN/ONNX Runtime）
  → iOS 和 Android 都能直接调用 C++ 库
  → 只需写一次推理代码，两端复用

方案3：云端统一，边缘按需
  → 核心模型放云端（一套代码）
  → 边缘只部署轻量级预处理/后处理
  → 适合对延迟要求不极端的场景
```

> 💡 **总结**：不需要"从零各自开发"。实际工作流是：**训练一次 → ONNX中转 → 自动化脚本转换 → 少量平台适配代码**。真正需要按平台写的代码量通常只占整个项目的 10%~20%。

### 5.3 模型格式转换路径

```
PyTorch (.pt/.pth)
    │
    ├──→ ONNX (.onnx) ──→ TensorRT (.engine)
    │                  ──→ OpenVINO (.xml/.bin)
    │                  ──→ NCNN (.param/.bin)
    │                  ──→ RKNN (.rknn)
    │
    └──→ TorchScript (.pt) ──→ 直接用 LibTorch 部署

TensorFlow (.pb/.h5)
    │
    ├──→ TFLite (.tflite) ──→ Coral Edge TPU
    ├──→ ONNX (.onnx) ──→ 同上
    └──→ SavedModel ──→ TF Serving
```

---

## 六、模型优化技术

### 6.1 优化技术全景

> **为什么需要优化？** 训练好的AI模型通常很"胖"——几十MB甚至几GB，需要强大的GPU才能流畅运行。但边缘设备（手机、摄像头、MCU）的算力和内存都很有限。模型优化就是**给模型"瘦身"**，让它在小设备上也能跑得又快又好。

```
模型优化四大技术（本章重点）
├── 1. 量化（Quantization）     → 降低数字精度，体积缩小2~8倍
├── 2. 剪枝（Pruning）          → 删掉不重要的连接，减少计算量
├── 3. 知识蒸馏（Distillation）  → 大模型教小模型，小模型也能很强
└── 4. 轻量化网络设计            → 从头设计"天生就小"的模型结构
```

**四种技术的定位对比**：

| 技术 | 小白类比 | 什么时候用 | 难度 | 收益 |
|------|----------|-----------|------|------|
| 量化 | 把高清照片压缩成标清 | 部署前最后一步 | ⭐ | 速度×2~4，体积÷2~4 |
| 剪枝 | 删掉书中的废话 | 模型太大跑不动 | ⭐⭐ | 计算量减少30%~70% |
| 蒸馏 | 名师带徒弟学精髓 | 想要小模型但精度高 | ⭐⭐⭐ | 小模型精度提升2%~5% |
| 轻量化设计 | 从头造一辆省油的车 | 新项目从零开始 | ⭐⭐ | 天生就快就小 |

> 💡 **实际项目中通常组合使用**：先选一个轻量化网络 → 训练 → 剪枝 → 量化 → 部署。

---

### 6.2 量化（Quantization）

#### 6.2.1 什么是量化？——小白入门

**一句话**：把模型中的数字从"高精度"变成"低精度"，牺牲一点点准确性，换来巨大的速度和体积提升。

**生活类比**：

```
想象你在记录温度：
- 高精度（FP32）：今天气温是 23.456789°C  → 精确但占空间
- 低精度（INT8）：今天气温是 23°C          → 够用且省空间

对于AI模型来说：
- 模型里有数百万个数字（权重）
- 每个数字从32位 → 8位，模型体积直接缩小4倍！
- 而且8位整数的计算比32位浮点快得多
```

**直观对比**：

```
FP32 模型（原始）：
┌────────────────────────────────────────┐
│ 权重值: 0.12345678  (32位，4字节)       │
│ 模型大小: 100MB                         │
│ 推理速度: 50ms                          │
│ 精度: 95.0%                             │
└────────────────────────────────────────┘
         │
         │ 量化
         ▼
INT8 模型（量化后）：
┌────────────────────────────────────────┐
│ 权重值: 31  (8位，1字节)                │
│ 模型大小: 25MB  (缩小4倍!)              │
│ 推理速度: 15ms  (快3倍!)                │
│ 精度: 94.2%  (只降了0.8%!)              │
└────────────────────────────────────────┘
```

#### 6.2.2 量化的数学原理

量化本质是一个**线性映射**：把浮点数范围映射到整数范围。

```
核心公式：

量化（浮点 → 整数）：
  q = round(x / scale) + zero_point

反量化（整数 → 浮点）：
  x ≈ (q - zero_point) × scale

其中：
  scale = (max_val - min_val) / (2^bits - 1)
  zero_point = round(-min_val / scale)
```

**具体例子**：

```
假设某一层权重的范围是 [-1.0, +1.0]，要量化到 INT8 (0~255)：

scale = (1.0 - (-1.0)) / 255 = 0.00784
zero_point = round(1.0 / 0.00784) = 128

量化示例：
  原始值 0.5  → round(0.5 / 0.00784) + 128 = 192
  原始值 -0.3 → round(-0.3 / 0.00784) + 128 = 90
  原始值 0.0  → round(0.0 / 0.00784) + 128 = 128

反量化验证：
  192 → (192 - 128) × 0.00784 = 0.502  (误差仅 0.002!)
```

#### 6.2.3 两种量化方法

##### 方法一：训练后量化（PTQ, Post-Training Quantization）

> **适合谁**：有一个训练好的模型，想快速部署，不想重新训练。

**原理**：模型训练完成后，用少量数据（几百张图）统计每层数值范围，然后直接转换。

```python
# ============================================
# 完整示例：PyTorch 训练后量化（PTQ）
# ============================================
import torch
import torchvision.models as models

# 1. 加载训练好的模型
model = models.mobilenet_v2(pretrained=True)
model.eval()

# 2. 设置量化配置
model.qconfig = torch.quantization.get_default_qconfig('fbgemm')  # x86 CPU
# 如果是 ARM 设备，用 'qnnpack'

# 3. 准备模型（插入观察节点）
model_prepared = torch.quantization.prepare(model)

# 4. 用校准数据"跑一遍"（让模型统计每层数值范围）
# 不需要很多数据，100~500张图就够
calibration_dataset = load_calibration_data()  # 你的数据
with torch.no_grad():
    for images in calibration_dataset:
        model_prepared(images)  # 只是前向传播，不训练

# 5. 执行量化转换
model_quantized = torch.quantization.convert(model_prepared)

# 6. 保存量化模型
torch.save(model_quantized.state_dict(), 'model_int8.pth')

# 对比大小
import os
original_size = os.path.getsize('model_fp32.pth') / 1e6
quantized_size = os.path.getsize('model_int8.pth') / 1e6
print(f"原始模型: {original_size:.1f} MB")
print(f"量化模型: {quantized_size:.1f} MB")
print(f"压缩比: {original_size/quantized_size:.1f}x")
```

##### 方法二：量化感知训练（QAT, Quantization-Aware Training）

> **适合谁**：对精度要求高，愿意花时间重新训练。

**原理**：在训练过程中就模拟量化带来的误差，让模型"适应"低精度，最终量化后精度损失极小。

```python
# ============================================
# 完整示例：PyTorch 量化感知训练（QAT）
# ============================================
import torch
import torch.quantization as quant

# 1. 加载预训练模型
model = load_your_model()
model.train()

# 2. 设置 QAT 配置
model.qconfig = quant.get_default_qat_qconfig('fbgemm')

# 3. 准备 QAT（在模型中插入"伪量化"节点）
model_prepared = quant.prepare_qat(model)
# 此时模型内部会模拟量化误差，但仍用浮点计算

# 4. 正常训练（和普通训练一模一样）
optimizer = torch.optim.Adam(model_prepared.parameters(), lr=1e-4)
for epoch in range(10):  # 通常只需要原始训练轮数的10%~20%
    for images, labels in train_loader:
        output = model_prepared(images)
        loss = criterion(output, labels)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    print(f"Epoch {epoch}: loss = {loss.item():.4f}")

# 5. 转换为真正的量化模型
model_prepared.eval()
model_quantized = quant.convert(model_prepared)

# 6. 验证精度
accuracy = evaluate(model_quantized, val_loader)
print(f"量化后精度: {accuracy:.2f}%")
```

##### PTQ vs QAT 对比

| 对比项 | PTQ（训练后量化） | QAT（量化感知训练） |
|--------|-------------------|---------------------|
| 精度损失 | 1%~3% | <0.5% |
| 需要训练？ | ❌ 不需要 | ✅ 需要微调 |
| 需要数据？ | 少量校准数据（100~500张） | 完整训练集 |
| 耗时 | 几分钟 | 几小时~几天 |
| 适用场景 | 快速部署、精度不太敏感 | 精度敏感、医疗/自动驾驶 |
| 小白推荐 | ✅ 先试这个 | 进阶再用 |

#### 6.2.4 实用工具：一键量化

```bash
# 方法1：用 ONNX Runtime 量化（最通用）
pip install onnxruntime onnx
python -m onnxruntime.quantization.quantize \
    --input model.onnx \
    --output model_int8.onnx \
    --quant_format QDQ

# 方法2：用 TensorRT 量化（NVIDIA平台最快）
trtexec --onnx=model.onnx --saveEngine=model_int8.engine --int8

# 方法3：用 TFLite 量化（移动端/MCU）
# 见第七章实战代码
```

#### 6.2.5 参考资料与进一步学习

| 资源 | 类型 | 适合谁 | 链接 |
|------|------|--------|------|
| PyTorch 量化官方教程 | 教程 | 入门 | https://pytorch.org/docs/stable/quantization.html |
| TensorFlow 量化指南 | 教程 | 入门 | https://www.tensorflow.org/model_optimization/guide/quantization |
| MIT 6.5940 Lecture 5: Quantization | 视频课 | 中级 | https://hanlab.mit.edu/courses/2023-fall-65940 |
| 论文：A Survey of Quantization Methods | 综述 | 高级 | https://arxiv.org/abs/2103.13630 |
| ONNX Runtime 量化文档 | 工具 | 实战 | https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html |
| Neural Network Distiller (Intel) | 工具库 | 实战 | https://intellabs.github.io/distiller/algo_quantization.html |

---

### 6.3 剪枝（Pruning）

#### 6.3.1 什么是剪枝？——小白入门

**一句话**：找出模型中"不重要"的连接（权重），把它们删掉，模型变小变快。

**生活类比**：

```
想象一本500页的教科书：
- 其中有100页是重复的例子、过渡段落、注释
- 把这些"废话"删掉，书变成400页
- 核心知识没丢，但书更薄、翻得更快

AI模型也一样：
- 模型中有大量接近0的权重（不重要的连接）
- 删掉它们，模型变小，计算量减少
- 但模型的"知识"（精度）几乎不受影响
```

**为什么有些权重"不重要"？**

```
神经网络训练后，权重的分布通常是这样的：

数量
 │
 │      ┌───┐
 │      │   │
 │    ┌─┤   ├─┐
 │  ┌─┤ │   │ ├─┐
 │──┤ │ │   │ │ ├──
 └──┴─┴─┴───┴─┴─┴──→ 权重值
   -1  -0.5  0  0.5  1

大部分权重集中在0附近 → 这些权重对输出影响很小 → 可以安全删除！
```

#### 6.3.2 剪枝的分类

```
剪枝方式
├── 按粒度分
│   ├── 非结构化剪枝（细粒度）：删除单个权重
│   │   → 模型变稀疏，需要特殊硬件/库才能加速
│   │
│   └── 结构化剪枝（粗粒度）：删除整个通道/层
│       → 模型直接变小，普通硬件就能加速 ✅ 推荐
│
├── 按时机分
│   ├── 训练后剪枝：训练完再剪
│   ├── 训练中剪枝：边训练边剪
│   └── 训练前剪枝（彩票假说）：随机初始化时就确定结构
│
└── 按标准分
    ├── 幅度剪枝：删绝对值最小的权重（最简单）
    ├── 梯度剪枝：删梯度最小的权重
    └── 敏感度剪枝：删对输出影响最小的权重
```

**非结构化 vs 结构化 直观对比**：

```
原始卷积层（4个通道）：
┌──┐ ┌──┐ ┌──┐ ┌──┐
│C1│ │C2│ │C3│ │C4│    4个卷积核，每个3×3
└──┘ └──┘ └──┘ └──┘

非结构化剪枝（删单个权重）：
┌──┐ ┌──┐ ┌──┐ ┌──┐
│C1│ │C2│ │C3│ │C4│    每个核里有些位置变成0
└──┘ └──┘ └──┘ └──┘    → 矩阵变稀疏，但形状不变
                        → 需要稀疏计算库才能加速

结构化剪枝（删整个通道）：
┌──┐       ┌──┐ ┌──┐
│C1│  ❌   │C3│ │C4│    直接删掉C2整个通道
└──┘       └──┘ └──┘    → 矩阵直接变小
                        → 普通硬件直接加速 ✅
```

#### 6.3.3 动手实践：PyTorch 剪枝

```python
# ============================================
# 示例1：非结构化剪枝（最简单，入门用）
# ============================================
import torch
import torch.nn.utils.prune as prune
import torchvision.models as models

# 加载模型
model = models.resnet18(pretrained=True)

# 对某一层进行剪枝：删掉30%最小的权重
layer = model.layer1[0].conv1
prune.l1_unstructured(layer, name='weight', amount=0.3)

# 查看剪枝效果
total = layer.weight.nelement()
zeros = (layer.weight == 0).sum().item()
print(f"总权重数: {total}")
print(f"被剪掉的: {zeros} ({100*zeros/total:.1f}%)")

# 让剪枝永久生效（去掉mask，直接修改权重）
prune.remove(layer, 'weight')
```

```python
# ============================================
# 示例2：结构化剪枝（实际部署推荐）
# ============================================
import torch
import torch.nn.utils.prune as prune

model = models.resnet18(pretrained=True)
layer = model.layer1[0].conv1

# 按L1范数删掉20%的输出通道（整个卷积核）
prune.ln_structured(layer, name='weight', amount=0.2, n=1, dim=0)

# 查看哪些通道被删了
mask = layer.weight_mask
active_channels = mask.sum(dim=(1,2,3)) > 0
print(f"原始通道数: {mask.shape[0]}")
print(f"保留通道数: {active_channels.sum().item()}")
```

```python
# ============================================
# 示例3：全局剪枝（对整个模型统一剪枝）
# ============================================
import torch.nn.utils.prune as prune

model = models.mobilenet_v2(pretrained=True)

# 收集所有卷积层
parameters_to_prune = []
for name, module in model.named_modules():
    if isinstance(module, torch.nn.Conv2d):
        parameters_to_prune.append((module, 'weight'))

# 全局剪枝：在所有层中，删掉40%最不重要的权重
prune.global_unstructured(
    parameters_to_prune,
    pruning_method=prune.L1Unstructured,
    amount=0.4,  # 40%
)

# 统计整体稀疏度
total = 0
pruned = 0
for module, _ in parameters_to_prune:
    total += module.weight.nelement()
    pruned += (module.weight == 0).sum().item()
print(f"全局稀疏度: {100*pruned/total:.1f}%")
```

#### 6.3.4 剪枝的完整工作流

```
┌─────────────────┐
│ 1. 训练原始模型  │  正常训练到收敛
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. 评估重要性    │  计算每个权重/通道的"重要性分数"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. 执行剪枝     │  删掉分数最低的 N%
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. 微调恢复     │  用原始数据再训练几轮，恢复精度
└────────┬────────┘    （通常只需原始训练量的10%~20%）
         │
         ▼
┌─────────────────┐
│ 5. 重复2~4步    │  逐步增加剪枝比例（迭代剪枝）
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 6. 导出部署     │  结构化剪枝后模型直接变小
└─────────────────┘
```

#### 6.3.5 参考资料与进一步学习

| 资源 | 类型 | 适合谁 | 链接 |
|------|------|--------|------|
| PyTorch Pruning 官方教程 | 教程 | 入门 | https://pytorch.org/tutorials/intermediate/pruning_tutorial.html |
| MIT 6.5940 Lecture 4: Pruning and Sparsity | 视频课 | 中级 | https://hanlab.mit.edu/courses/2023-fall-65940 |
| 论文：Learning both Weights and Connections | 经典论文 | 中级 | https://arxiv.org/abs/1506.02626 |
| 论文：The Lottery Ticket Hypothesis | 里程碑 | 高级 | https://arxiv.org/abs/1803.03635 |
| Torch-Pruning 工具库（结构化剪枝） | 工具 | 实战 | https://github.com/VainF/Torch-Pruning |
| Neural Network Intelligence (NNI) | 工具 | 实战 | https://nni.readthedocs.io/en/stable/compression/overview.html |

---

### 6.4 知识蒸馏（Knowledge Distillation）

#### 6.4.1 什么是知识蒸馏？——小白入门

**一句话**：让一个"聪明的大模型"（教师）教一个"小模型"（学生），使小模型获得超越自身能力的表现。

**生活类比**：

```
场景：你要参加一场考试

方法A（自学）：
  自己看教科书 → 做题 → 考了 85 分

方法B（名师辅导 = 知识蒸馏）：
  名师先做一遍题 → 告诉你"这道题答案是C，但B也有30%的可能性"
  → 你不仅学到正确答案，还学到了"哪些选项容易混淆"
  → 考了 92 分！

AI版本：
  大模型（教师）：ResNet-152，精度96%，但太大跑不动
  小模型（学生）：MobileNet，自己训练只有91%
  蒸馏后：MobileNet 精度提升到 94%！体积不变，但更聪明了
```

#### 6.4.2 为什么蒸馏有效？——"软标签"的秘密

```
传统训练（硬标签）：
  图片是一只猫 → 标签 = [猫:1, 狗:0, 鸟:0]
  模型只知道"这是猫"，学不到更多信息

蒸馏训练（软标签）：
  大模型的输出 = [猫:0.85, 狗:0.10, 鸟:0.05]
  小模型能学到：
  - "这是猫"（主要信息）
  - "这只猫长得有点像狗"（额外信息！）
  - "这只猫完全不像鸟"（额外信息！）

这些"额外信息"就是知识蒸馏的核心价值——
大模型的输出概率分布包含了丰富的"暗知识"(Dark Knowledge)
```

#### 6.4.3 蒸馏的数学原理

```
蒸馏损失函数：

L_total = α × L_hard + (1-α) × L_soft

其中：
  L_hard = CrossEntropy(student_output, true_label)
         → 学生对照"标准答案"学习（和普通训练一样）

  L_soft = KL_Divergence(
               softmax(student_logits / T),
               softmax(teacher_logits / T)
           ) × T²
         → 学生模仿"教师的思考过程"

参数说明：
  α：平衡系数，通常 0.1~0.5（软标签权重更大）
  T：温度参数，通常 3~20

温度T的作用（关键！）：
  T=1 时：softmax([5, 3, 1]) = [0.84, 0.11, 0.02]  → 差异很大，信息少
  T=5 时：softmax([5, 3, 1]/5) = [0.45, 0.33, 0.22] → 差异变小，信息丰富
  T越大，概率分布越"平滑"，暗知识越容易被学生学到
```

#### 6.4.4 动手实践：完整蒸馏代码

```python
# ============================================
# 完整示例：知识蒸馏（图像分类）
# ============================================
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models

# ---- 1. 准备教师和学生模型 ----
# 教师：大模型（预训练好的，不再更新）
teacher = models.resnet50(pretrained=True)
teacher.eval()  # 教师固定不动
for param in teacher.parameters():
    param.requires_grad = False

# 学生：小模型（要训练的）
student = models.mobilenet_v2(pretrained=False)
# 修改最后一层匹配你的类别数
student.classifier[1] = nn.Linear(1280, num_classes)

# ---- 2. 定义蒸馏损失 ----
class DistillationLoss(nn.Module):
    def __init__(self, temperature=4.0, alpha=0.3):
        super().__init__()
        self.T = temperature
        self.alpha = alpha
        self.ce_loss = nn.CrossEntropyLoss()
        self.kl_loss = nn.KLDivLoss(reduction='batchmean')
    
    def forward(self, student_logits, teacher_logits, true_labels):
        # 硬损失：学生 vs 真实标签
        loss_hard = self.ce_loss(student_logits, true_labels)
        
        # 软损失：学生 vs 教师（用温度软化）
        student_soft = F.log_softmax(student_logits / self.T, dim=1)
        teacher_soft = F.softmax(teacher_logits / self.T, dim=1)
        loss_soft = self.kl_loss(student_soft, teacher_soft) * (self.T ** 2)
        
        # 总损失
        return self.alpha * loss_hard + (1 - self.alpha) * loss_soft

# ---- 3. 训练循环 ----
criterion = DistillationLoss(temperature=4.0, alpha=0.3)
optimizer = torch.optim.Adam(student.parameters(), lr=1e-3)

for epoch in range(50):
    student.train()
    total_loss = 0
    
    for images, labels in train_loader:
        # 教师推理（不计算梯度）
        with torch.no_grad():
            teacher_logits = teacher(images)
        
        # 学生推理
        student_logits = student(images)
        
        # 计算蒸馏损失
        loss = criterion(student_logits, teacher_logits, labels)
        
        # 反向传播（只更新学生）
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
    
    # 验证
    student.eval()
    accuracy = evaluate(student, val_loader)
    print(f"Epoch {epoch}: loss={total_loss/len(train_loader):.4f}, acc={accuracy:.2f}%")

# ---- 4. 对比结果 ----
teacher_acc = evaluate(teacher, val_loader)
student_acc = evaluate(student, val_loader)
print(f"\n教师模型精度: {teacher_acc:.2f}%  (参数量: 25.6M)")
print(f"学生模型精度: {student_acc:.2f}%  (参数量: 3.4M)")
print(f"学生只有教师 1/7 的大小，但精度接近！")
```

#### 6.4.5 蒸馏的变体

| 变体 | 原理 | 适用场景 |
|------|------|----------|
| **Logit 蒸馏**（经典） | 学生模仿教师的输出概率 | 通用分类任务 |
| **Feature 蒸馏** | 学生模仿教师的中间层特征 | 检测/分割等复杂任务 |
| **Self 蒸馏** | 模型自己蒸馏自己（深层教浅层） | 不需要额外教师模型 |
| **Online 蒸馏** | 多个学生互相学习，没有固定教师 | 没有预训练大模型时 |
| **Data-Free 蒸馏** | 不需要原始训练数据 | 数据隐私受限场景 |

#### 6.4.6 参考资料与进一步学习

| 资源 | 类型 | 适合谁 | 链接 |
|------|------|--------|------|
| 论文：Distilling the Knowledge (Hinton 2015) | 开山之作 | 中级 | https://arxiv.org/abs/1503.02531 |
| MIT 6.5940 Lecture 6: Knowledge Distillation | 视频课 | 中级 | https://hanlab.mit.edu/courses/2023-fall-65940 |
| PyTorch 蒸馏实战教程 | 教程 | 入门 | https://pytorch.org/tutorials/beginner/knowledge_distillation_tutorial.html |
| 论文：A Comprehensive Survey on KD | 综述 | 高级 | https://arxiv.org/abs/2006.05525 |
| RepDistiller 工具库 | 代码 | 实战 | https://github.com/HobbitLong/RepDistiller |
| Knowledge-Distillation-Zoo | 代码集 | 实战 | https://github.com/AberHu/Knowledge-Distillation-Zoo |

---

### 6.5 轻量化网络设计

#### 6.5.1 什么是轻量化网络？——小白入门

**一句话**：从模型结构设计层面，就让模型"天生就小"，而不是先做大再压缩。

**生活类比**：

```
造车的两种思路：

思路A（先大后压缩）：
  造一辆大卡车 → 拆掉一些零件 → 变成小货车
  → 能用，但设计上不够优雅

思路B（天生轻量 = 轻量化网络设计）：
  从一开始就设计一辆省油的小轿车
  → 每个零件都精心设计，天生就高效
  → 这就是 MobileNet、ShuffleNet 等网络的思路
```

#### 6.5.2 核心设计思想

##### 思想一：深度可分离卷积（Depthwise Separable Convolution）

这是 MobileNet 系列的核心创新，也是轻量化网络最重要的"积木块"。

```
标准卷积 vs 深度可分离卷积：

【标准卷积】
输入: 56×56×64 → 卷积核: 3×3×64×128 → 输出: 56×56×128
计算量 = 56 × 56 × 3 × 3 × 64 × 128 = 2.31亿次乘法

【深度可分离卷积】= 深度卷积 + 逐点卷积
  第1步 - 深度卷积（每个通道单独卷积）：
    输入: 56×56×64 → 卷积核: 3×3×1×64 → 输出: 56×56×64
    计算量 = 56 × 56 × 3 × 3 × 64 = 1,806,336

  第2步 - 逐点卷积（1×1卷积混合通道）：
    输入: 56×56×64 → 卷积核: 1×1×64×128 → 输出: 56×56×128
    计算量 = 56 × 56 × 64 × 128 = 25,690,112

  总计算量 = 1,806,336 + 25,690,112 = 2,750万次乘法

节省比例 = 2,750万 / 2.31亿 ≈ 1/8.4 → 计算量减少到原来的 12%！
```

**直观理解**：

```
标准卷积（一步到位）：
  每个输出通道都要"看"所有输入通道的所有空间位置
  → 计算量 = 空间 × 输入通道 × 输出通道

深度可分离卷积（分两步）：
  第1步：每个通道只看自己的空间邻域（不跨通道）
  第2步：每个位置只看所有通道（不看邻域）
  → 把"空间"和"通道"解耦，大幅减少计算

类比：
  标准卷积 = 每个人和所有人都握一次手（N²次）
  深度可分离 = 先组内握手 + 再组间代表握手（N次）
```

##### 思想二：倒残差结构（Inverted Residual）

MobileNetV2 的核心创新：

```
传统残差块（ResNet）：
  宽 → 窄 → 宽
  256通道 → 64通道(压缩) → 256通道(恢复)
  在"窄"的地方做3×3卷积

倒残差块（MobileNetV2）：
  窄 → 宽 → 窄
  24通道 → 144通道(扩展) → 24通道(压缩)
  在"宽"的地方做深度卷积

为什么"倒过来"？
  → 深度卷积在高维空间效果更好
  → 低维输入/输出节省内存
  → 跳跃连接在窄处，传输数据量小
```

##### 思想三：通道混洗（Channel Shuffle）

ShuffleNet 的核心创新：

```
问题：分组卷积虽然省计算，但组间信息不流通

解决：在分组卷积之后，把通道"洗牌"

洗牌前（2组，每组3通道）：
  组1: [C1, C2, C3]    组2: [C4, C5, C6]

洗牌后：
  组1: [C1, C4, C2]    组2: [C5, C3, C6]

→ 下一层的每个组都能看到上一层所有组的信息
→ 零额外计算量，只是重新排列内存
```

#### 6.5.3 主流轻量化网络对比

| 网络 | 年份 | 核心创新 | 参数量 | Top-1 (ImageNet) | 适合设备 |
|------|------|----------|--------|-------------------|----------|
| **MobileNetV1** | 2017 | 深度可分离卷积 | 4.2M | 70.6% | 手机 |
| **MobileNetV2** | 2018 | 倒残差 + 线性瓶颈 | 3.4M | 72.0% | 手机 |
| **MobileNetV3** | 2019 | NAS搜索 + SE注意力 + h-swish | 5.4M | 75.2% | 手机（推荐） |
| **ShuffleNetV1** | 2018 | 分组卷积 + 通道混洗 | 1.8M | 67.4% | 极端轻量 |
| **ShuffleNetV2** | 2018 | 通道分割 + 实际速度优化 | 2.3M | 69.4% | 极端轻量 |
| **EfficientNet-B0** | 2019 | 复合缩放 + NAS | 5.3M | 77.1% | 手机/边缘 |
| **EfficientNet-Lite** | 2020 | 去掉SE，适配移动端 | 4.7M | 75.1% | 移动端部署 |
| **GhostNet** | 2020 | 廉价操作生成特征图 | 5.2M | 73.9% | 华为设备 |
| **MobileNetV4** | 2024 | Universal Block + NAS | 3.8M | 73.8% | 多硬件通用 |

#### 6.5.4 动手实践：使用轻量化网络

```python
# ============================================
# 示例1：直接使用预训练的 MobileNetV3
# ============================================
import torch
import torchvision.models as models

# 加载预训练的 MobileNetV3-Small（最轻量）
model = models.mobilenet_v3_small(pretrained=True)
print(f"参数量: {sum(p.numel() for p in model.parameters())/1e6:.1f}M")

# 修改最后一层适配你的任务（比如10类分类）
model.classifier[3] = torch.nn.Linear(1024, 10)

# 正常训练即可...
```

```python
# ============================================
# 示例2：使用 timm 库（更多轻量化模型选择）
# ============================================
import timm

# 查看所有可用的轻量化模型
lightweight_models = timm.list_models('*mobile*') + timm.list_models('*efficient*')
print(f"可用轻量化模型数量: {len(lightweight_models)}")

# 加载 EfficientNet-Lite0
model = timm.create_model('efficientnet_lite0', pretrained=True, num_classes=10)

# 查看模型信息
from torchinfo import summary
summary(model, input_size=(1, 3, 224, 224))
```

```python
# ============================================
# 示例3：宽度乘子（Width Multiplier）调节模型大小
# ============================================
# MobileNet 支持用"宽度乘子"灵活调节大小
# α=1.0 是标准版，α=0.5 是半宽版（更小更快）

# PyTorch 中通过不同变体实现：
model_large = models.mobilenet_v3_large(pretrained=True)   # 大版本 5.4M
model_small = models.mobilenet_v3_small(pretrained=True)   # 小版本 2.5M

# timm 中可以更精细控制：
model_075 = timm.create_model('mobilenetv3_small_075', pretrained=True)  # 0.75倍宽
model_050 = timm.create_model('mobilenetv3_small_050', pretrained=True)  # 0.5倍宽
```

#### 6.5.5 如何选择轻量化网络？

```
决策流程：

你的目标设备是什么？
├── 手机/平板（ARM GPU + NPU）
│   ├── 精度优先 → MobileNetV3-Large / EfficientNet-B0
│   └── 速度优先 → MobileNetV3-Small / ShuffleNetV2
│
├── MCU（纯CPU，<1MB内存）
│   ├── MCUNet（MIT，专为MCU设计）
│   └── MicroNet（极致压缩）
│
├── 边缘GPU（Jetson等）
│   ├── EfficientNet-B0~B3
│   └── MobileNetV4（多硬件通用）
│
└── 多平台部署（一个模型跑多种设备）
    └── MobileNetV4 / Once-for-All (OFA)

你的任务是什么？
├── 图像分类 → 上述任何网络
├── 目标检测 → MobileNet + SSD/YOLO 检测头
├── 语义分割 → MobileNet + DeepLab/BiSeNet 分割头
└── 关键点检测 → MobileNet + Lightweight OpenPose
```

#### 6.5.6 参考资料与进一步学习

| 资源 | 类型 | 适合谁 | 链接 |
|------|------|--------|------|
| 论文：MobileNets V1 | 开山之作 | 入门 | https://arxiv.org/abs/1704.04861 |
| 论文：MobileNetV2 | 倒残差 | 中级 | https://arxiv.org/abs/1801.04381 |
| 论文：MobileNetV3 | NAS+SE | 中级 | https://arxiv.org/abs/1905.02244 |
| 论文：EfficientNet | 复合缩放 | 中级 | https://arxiv.org/abs/1905.11946 |
| 论文：ShuffleNetV2 | 实际速度指导设计 | 中级 | https://arxiv.org/abs/1807.11164 |
| MIT 6.5940 Lecture 3: Efficient Architectures | 视频课 | 中级 | https://hanlab.mit.edu/courses/2023-fall-65940 |
| timm 模型库文档 | 工具 | 实战 | https://huggingface.co/docs/timm |
| 论文：MCUNet (MCU上的AI) | 前沿 | 高级 | https://arxiv.org/abs/2007.10319 |
| 论文：Once-for-All | 前沿 | 高级 | https://arxiv.org/abs/1908.09791 |

---

### 6.6 四种技术的组合使用

在实际项目中，这四种技术通常**组合使用**以获得最佳效果：

```
实际项目的典型优化流程：

┌─────────────────────────────────────────────────────────┐
│ 步骤1：选择轻量化网络                                     │
│   MobileNetV3-Small 作为 backbone                        │
│   → 天生就小：2.5M 参数                                  │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│ 步骤2：知识蒸馏训练                                       │
│   用 ResNet-50 作为教师，蒸馏训练 MobileNetV3             │
│   → 精度从 67% 提升到 72%（+5%）                         │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│ 步骤3：结构化剪枝                                         │
│   删掉 30% 不重要的通道，微调恢复                          │
│   → 计算量减少 30%，精度降 0.5%                           │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│ 步骤4：INT8 量化                                          │
│   训练后量化（PTQ）                                       │
│   → 模型体积再缩小 4 倍，速度再快 2~3 倍                  │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 最终结果：                                                │
│   原始 ResNet-50: 25.6M参数, 100MB, 50ms, 精度76%        │
│   优化后模型:     0.8M参数,  2MB,  5ms, 精度71%          │
│   → 体积缩小50倍，速度快10倍，精度只降5%！                │
└─────────────────────────────────────────────────────────┘
```

**组合使用的注意事项**：

| 顺序 | 原因 |
|------|------|
| 先选网络结构，再蒸馏 | 结构决定了上限，蒸馏帮助逼近上限 |
| 先剪枝，再量化 | 剪枝改变结构需要微调，量化是最后一步 |
| 蒸馏和剪枝可以同时做 | 边剪枝边用教师指导恢复精度 |
| 量化放最后 | 量化不改变结构，是"无损"的最后一步优化 |

---

## 七、端侧部署实战

### 7.1 实战一：TFLite 部署图像分类（树莓派/Android）

```python
# 步骤1：模型转换（在PC上执行）
import tensorflow as tf

# 加载训练好的模型
model = tf.keras.models.load_model('my_model.h5')

# 转换为 TFLite 格式 + INT8 量化
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]

# 提供校准数据
def representative_dataset():
    for image in calibration_images:
        yield [image.astype(np.float32)]

converter.representative_dataset = representative_dataset
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.uint8
converter.inference_output_type = tf.uint8

tflite_model = converter.convert()

with open('model_int8.tflite', 'wb') as f:
    f.write(tflite_model)
```

```python
# 步骤2：边缘设备推理
import tflite_runtime.interpreter as tflite
import numpy as np
from PIL import Image

# 加载模型
interpreter = tflite.Interpreter(model_path='model_int8.tflite')
interpreter.allocate_tensors()

# 获取输入输出信息
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# 预处理图像
img = Image.open('test.jpg').resize((224, 224))
input_data = np.expand_dims(np.array(img, dtype=np.uint8), axis=0)

# 推理
interpreter.set_tensor(input_details[0]['index'], input_data)
interpreter.invoke()

# 获取结果
output = interpreter.get_tensor(output_details[0]['index'])
predicted_class = np.argmax(output)
print(f"预测类别: {predicted_class}")
```

### 7.2 实战二：ONNX Runtime 部署 YOLOv8（通用平台）

```python
# 步骤1：导出 ONNX
from ultralytics import YOLO

model = YOLO('yolov8n.pt')  # nano版本，适合边缘
model.export(format='onnx', imgsz=640, simplify=True, opset=12)
```

```python
# 步骤2：ONNX Runtime 推理
import onnxruntime as ort
import cv2
import numpy as np

# 创建推理会话
session = ort.InferenceSession(
    'yolov8n.onnx',
    providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
)

# 预处理
img = cv2.imread('test.jpg')
blob = cv2.dnn.blobFromImage(img, 1/255.0, (640, 640), swapRB=True)

# 推理
outputs = session.run(None, {'images': blob})

# 后处理（NMS等）
# ... 解析检测框 ...
```

### 7.3 实战三：TensorRT 部署（Jetson 平台）

```python
# 步骤1：ONNX → TensorRT Engine
import tensorrt as trt

logger = trt.Logger(trt.Logger.WARNING)
builder = trt.Builder(logger)
network = builder.create_network(
    1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
)
parser = trt.OnnxParser(network, logger)

# 解析 ONNX
with open('model.onnx', 'rb') as f:
    parser.parse(f.read())

# 配置优化
config = builder.create_builder_config()
config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 1 << 30)  # 1GB
config.set_flag(trt.BuilderFlag.FP16)  # 启用 FP16

# 构建引擎
engine = builder.build_serialized_network(network, config)

with open('model.engine', 'wb') as f:
    f.write(engine)
```

### 7.4 实战四：MCU 部署（STM32）

```c
/* STM32 上运行 TFLite Micro 示例 */
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "model_data.h"  // 模型数组（xxd转换）

// 分配内存（根据模型大小调整）
constexpr int kTensorArenaSize = 10 * 1024;  // 10KB
uint8_t tensor_arena[kTensorArenaSize];

void run_inference(float* input_data, float* output_data) {
    // 加载模型
    const tflite::Model* model = tflite::GetModel(g_model_data);

    // 注册需要的算子
    tflite::MicroMutableOpResolver<5> resolver;
    resolver.AddFullyConnected();
    resolver.AddRelu();
    resolver.AddSoftmax();

    // 创建解释器
    tflite::MicroInterpreter interpreter(
        model, resolver, tensor_arena, kTensorArenaSize);
    interpreter.AllocateTensors();

    // 填入输入数据
    float* input = interpreter.input(0)->data.f;
    memcpy(input, input_data, input_size * sizeof(float));

    // 执行推理
    interpreter.Invoke();

    // 读取输出
    float* output = interpreter.output(0)->data.f;
    memcpy(output_data, output, output_size * sizeof(float));
}
```

---

## 八、典型应用场景

### 8.1 场景矩阵

| 场景 | 典型模型 | 硬件选择 | 延迟要求 | 关键指标 |
|------|----------|----------|----------|----------|
| **智能安防** | YOLOv8n/s | RK3588/Jetson | <50ms | mAP、FPS |
| **自动驾驶** | BEVFormer/CenterPoint | Orin/地平线J5 | <30ms | 安全性、延迟 |
| **语音助手** | Whisper-tiny/RNNT | 高通/MTK | <200ms | WER、功耗 |
| **工业质检** | 异常检测/分割模型 | Intel OpenVINO | <100ms | 漏检率、误检率 |
| **智能家居** | 人脸识别/手势识别 | RK3566/Coral | <100ms | 准确率、功耗 |
| **可穿戴** | 心率异常检测 | STM32/nRF | <10ms | 灵敏度、功耗 |
| **无人机** | 目标跟踪/避障 | Jetson Nano | <30ms | 实时性、重量 |
| **关键词检测** | DS-CNN/DSCNN | ESP32/STM32 | <50ms | 唤醒率、误触率 |

### 8.2 案例深入：智能摄像头

```
完整Pipeline：

视频流(1080p@30fps)
    │
    ▼
┌─────────────┐
│ 解码 (硬件)  │  H.264/H.265 硬解
└──────┬──────┘
       │ YUV帧
       ▼
┌─────────────┐
│ 预处理 (NPU) │  Resize + 归一化 + 色彩转换
└──────┬──────┘
       │ Tensor
       ▼
┌─────────────┐
│ 检测 (NPU)   │  YOLOv8n: 640×640, INT8
└──────┬──────┘
       │ 检测框
       ▼
┌─────────────┐
│ 跟踪 (CPU)   │  ByteTrack / DeepSORT
└──────┬──────┘
       │ 轨迹
       ▼
┌─────────────┐
│ 业务逻辑     │  越界检测、人数统计、异常行为
└──────┬──────┘
       │ 事件
       ▼
┌─────────────┐
│ 上报/存储    │  仅上报事件，不传原始视频
└─────────────┘

性能指标（RK3588 实测）：
- 检测：YOLOv8n INT8, 640×640, ~25ms/帧 (~40FPS)
- 跟踪：ByteTrack, ~3ms/帧
- 总Pipeline延迟：~35ms
- 功耗：~5W
```

---

## 九、性能评估方法论

### 9.1 关键指标

| 指标 | 定义 | 如何测量 | 优化方向 |
|------|------|----------|----------|
| **Latency (ms)** | 单帧推理时间 | 多次推理取中位数 | 越低越好 |
| **Throughput (FPS)** | 每秒处理帧数 | 总帧数/总时间 | 越高越好 |
| **Accuracy** | 模型精度 | mAP/Top-1 等 | 在可接受范围内 |
| **Power (W)** | 功耗 | 功率计实测 | 越低越好 |
| **Efficiency (TOPS/W)** | 能效比 | 算力/功耗 | 越高越好 |
| **Model Size (MB)** | 模型文件大小 | 文件系统 | 适配存储限制 |
| **Memory (MB)** | 运行时内存占用 | 峰值RSS | 适配RAM限制 |

### 9.2 性能测试模板

```python
import time
import numpy as np

def benchmark(model, input_shape, num_warmup=10, num_runs=100):
    """标准性能测试"""
    dummy_input = np.random.randn(*input_shape).astype(np.float32)

    # 预热（排除首次加载开销）
    for _ in range(num_warmup):
        model.predict(dummy_input)

    # 正式测试
    latencies = []
    for _ in range(num_runs):
        start = time.perf_counter()
        model.predict(dummy_input)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # ms

    latencies = np.array(latencies)
    print(f"延迟统计 (ms):")
    print(f"  中位数: {np.median(latencies):.2f}")
    print(f"  平均值: {np.mean(latencies):.2f}")
    print(f"  P95:    {np.percentile(latencies, 95):.2f}")
    print(f"  P99:    {np.percentile(latencies, 99):.2f}")
    print(f"  吞吐量: {1000 / np.median(latencies):.1f} FPS")
```

### 9.3 精度-速度 Pareto 分析

```
精度(mAP)
  │
  │     ★ YOLOv8x (大模型，高精度，慢)
  │   ★ YOLOv8m
  │  ★ YOLOv8s
  │ ★ YOLOv8n        ← Pareto 最优前沿
  │★ NanoDet
  │
  └──────────────────────── 速度(FPS)

选择原则：在满足精度要求的前提下，选最快的模型
```

---

## 十、进阶专题

### 10.1 端侧训练（On-Device Training）

传统边缘AI只做推理，但新趋势是**在设备上也能训练/微调**：

| 技术 | 原理 | 应用 |
|------|------|------|
| **联邦学习** | 数据不出设备，只上传梯度 | 手机输入法个性化 |
| **增量学习** | 新数据来了不用全部重训 | 工业质检新缺陷类型 |
| **LoRA 微调** | 只训练少量适配参数 | 端侧大模型个性化 |
| **TinyTL** | 只训练偏置项 | MCU级别微调 |

### 10.2 端侧大语言模型（Edge LLM）

2024-2025 年的热门方向：

| 模型 | 参数量 | 量化后大小 | 目标设备 | 速度 |
|------|--------|-----------|----------|------|
| Phi-3 Mini | 3.8B | ~2GB (INT4) | 手机/PC | ~30 tok/s |
| Llama 3.2 1B | 1B | ~0.7GB (INT4) | 手机 | ~50 tok/s |
| Gemma 2B | 2B | ~1.5GB (INT4) | 手机/平板 | ~25 tok/s |
| Qwen2.5 0.5B | 0.5B | ~0.4GB (INT4) | 手机/IoT | ~80 tok/s |
| TinyLlama 1.1B | 1.1B | ~0.6GB (INT4) | 树莓派 | ~15 tok/s |

**关键技术**：
- **GGUF 格式** + llama.cpp：CPU 高效推理
- **INT4/INT3 量化**：GPTQ、AWQ、GGML
- **KV Cache 优化**：PagedAttention、GQA
- **推测解码**：小模型草稿 + 大模型验证

### 10.3 多模态边缘AI

```
传感器融合架构：

┌─────────┐  ┌─────────┐  ┌─────────┐
│ 摄像头   │  │ LiDAR   │  │  IMU    │
└────┬────┘  └────┬────┘  └────┬────┘
     │            │            │
     ▼            ▼            ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│图像特征  │  │点云特征  │  │运动特征  │
│提取(NPU)│  │提取(NPU)│  │处理(CPU)│
└────┬────┘  └────┬────┘  └────┬────┘
     │            │            │
     └────────────┼────────────┘
                  │
                  ▼
         ┌───────────────┐
         │  特征融合(NPU) │
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │  决策输出(CPU) │
         └───────────────┘
```

### 10.4 模型-硬件协同设计（Co-Design）

```
传统流程：
  设计模型 → 训练 → 部署到硬件 → 发现跑不动 → 重新设计 ❌

协同设计流程：
  硬件约束（算力/内存/功耗）
       │
       ▼
  NAS搜索（在约束内找最优结构）
       │
       ▼
  硬件感知训练（模拟真实延迟作为损失）
       │
       ▼
  一次性部署成功 ✅
```

代表工作：
- **Once-for-All (OFA)**：一次训练，导出适配不同硬件的子网络
- **EfficientNet-EdgeTPU**：专为 Edge TPU 优化的网络
- **MobileNetV4**：Universal Model 适配多种硬件

### 10.5 安全与隐私

| 威胁 | 描述 | 防御手段 |
|------|------|----------|
| 模型窃取 | 通过查询接口逆向模型 | 模型加密、安全芯片 |
| 对抗攻击 | 微小扰动导致误判 | 对抗训练、输入检测 |
| 数据投毒 | 污染训练数据 | 数据验证、异常检测 |
| 侧信道攻击 | 通过功耗/时序推断模型 | 恒定时间实现 |
| 隐私泄露 | 从模型推断训练数据 | 差分隐私、联邦学习 |

---

## 十一、学习路线图

### 11.1 小白路线（0→1，约 2-3 个月）

```
Week 1-2：基础概念
├── 理解 AI 推理 vs 训练
├── 了解常见模型（分类、检测、分割）
└── 安装 Python + PyTorch/TensorFlow

Week 3-4：第一个边缘AI项目
├── 用 TFLite 在树莓派上跑图像分类
├── 或用 ONNX Runtime 在 PC 上跑 YOLOv8
└── 理解预处理→推理→后处理的完整流程

Week 5-6：模型优化入门
├── 学习 INT8 量化（PTQ）
├── 对比量化前后的精度和速度
└── 尝试不同大小的模型（nano/small/medium）

Week 7-8：真实项目
├── 选一个场景（人脸检测/物体计数/手势识别）
├── 端到端完成：数据→训练→优化→部署
└── 测量延迟、精度、功耗

Week 9-12：深入一个方向
├── 选择一个硬件平台深入（Jetson/RK3588/MCU）
├── 学习该平台的专用工具链
└── 优化到极致性能
```

### 11.2 进阶路线（1→10，持续学习）

```
阶段1：精通优化（1-2个月）
├── 量化感知训练（QAT）
├── 结构化剪枝 + 微调
├── 知识蒸馏实战
└── 自定义算子开发

阶段2：系统级优化（2-3个月）
├── 多线程/异步Pipeline设计
├── CPU-NPU-GPU 异构调度
├── 内存池/零拷贝优化
├── 功耗管理（DVFS）
└── 实时操作系统（RTOS）集成

阶段3：前沿探索（持续）
├── 端侧大模型部署（LLM on Edge）
├── 端侧训练/联邦学习
├── 模型-硬件协同设计
├── 新型计算范式（存内计算、光计算、神经形态）
└── AI编译器（TVM、MLIR）
```

### 11.3 技能树

```
                        边缘AI工程师
                            │
            ┌───────────────┼───────────────┐
            │               │               │
        算法能力          系统能力         硬件理解
            │               │               │
    ┌───────┼───────┐   ┌──┼──┐       ┌────┼────┐
    │       │       │   │  │  │       │    │    │
  模型设计 模型优化 评估  OS 编译 驱动  CPU  NPU  内存
    │       │       │   │  │  │       │    │    │
 轻量网络 量化剪枝 基准 Linux C/C++ 中断 指令集 算子 带宽
 NAS     蒸馏   测试 RTOS  CMake DMA  流水线 调度 层次
```

---

## 十二、推荐资源

### 12.1 书籍

| 书名 | 适合人群 | 侧重点 |
|------|----------|--------|
| 《TinyML》(Pete Warden) | 入门 | MCU上的机器学习 |
| 《AI at the Edge》(Daniel Situnayake) | 入门~中级 | 端到端项目实战 |
| 《Efficient Deep Learning》(Menghani) | 中级~高级 | 模型压缩理论与实践 |
| 《Neural Network Quantization》 | 高级 | 量化理论深入 |

### 12.2 在线课程

| 课程 | 平台 | 特点 |
|------|------|------|
| TinyML 专项课程 | edX (Harvard) | 免费，从零开始 |
| Efficient ML | MIT 6.5940 (韩松) | 顶级课程，理论+实践 |
| NVIDIA DLI Edge AI | NVIDIA | Jetson 实战 |
| TensorFlow Lite 官方教程 | Google | 移动端部署 |

### 12.3 开源项目（动手学习）

| 项目 | 地址 | 学什么 |
|------|------|--------|
| ultralytics/yolov8 | GitHub | 目标检测 + 导出部署 |
| llama.cpp | GitHub | 端侧LLM推理 |
| ncnn | GitHub | 移动端推理框架源码 |
| microTVM | Apache TVM | AI编译器 |
| Edge Impulse | edgeimpulse.com | 零代码边缘AI平台 |
| OpenMMLab | GitHub | 全栈CV算法 |

### 12.4 社区与资讯

- **论文**：arXiv (cs.CV, cs.LG)，关注 "efficient"、"edge"、"mobile" 关键词
- **竞赛**：MLPerf Tiny、LPCV Challenge
- **会议**：tinyML Summit、CVPR ECV Workshop、NeurIPS Efficient ML
- **博客**：NVIDIA Developer Blog、Google AI Blog、Qualcomm AI Research

---

## 附录：快速参考卡片

### 常用命令速查

```bash
# ONNX 模型信息查看
python -m onnxruntime.tools.onnx_model_info model.onnx

# TFLite 模型信息
python -c "import tensorflow as tf; print(tf.lite.Interpreter('model.tflite').get_input_details())"

# TensorRT 转换（命令行）
trtexec --onnx=model.onnx --saveEngine=model.engine --fp16

# NCNN 转换
onnx2ncnn model.onnx model.param model.bin

# 查看 Jetson 资源使用
tegrastats

# 查看 NPU 使用率（RK3588）
cat /sys/kernel/debug/rknpu/load
```

### 模型选择速查

```
任务：图像分类
├── 极致轻量 → MobileNetV3-Small (1.5MB, 2ms)
├── 平衡     → EfficientNet-B0 (20MB, 5ms)
└── 高精度   → ConvNeXt-Tiny (110MB, 15ms)

任务：目标检测
├── 极致轻量 → NanoDet-Plus (4MB, 5ms)
├── 平衡     → YOLOv8n (6MB, 8ms)
└── 高精度   → YOLOv8s (22MB, 15ms)

任务：语义分割
├── 极致轻量 → PP-LiteSeg (5MB, 10ms)
├── 平衡     → BiSeNetV2 (15MB, 15ms)
└── 高精度   → SegFormer-B0 (15MB, 20ms)

任务：关键词检测（MCU）
├── 极致轻量 → DS-CNN-S (20KB, <1ms)
└── 平衡     → DS-CNN-L (100KB, 3ms)

（以上延迟为 INT8 量化后在中端NPU上的参考值）
```
