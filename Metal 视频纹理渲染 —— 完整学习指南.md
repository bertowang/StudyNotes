# Metal 视频纹理渲染 —— 完整学习指南

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-24

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
> 
> 本文档系统讲解 Apple Metal 视频渲染的完整技术栈：从底层命令编码原理到逐步优化的纹理上传技术。  
> 覆盖 macOS / iOS / iPadOS，通过 5 个递进式示例（01~05），从入门到生产级完整呈现。

---

## 目录

- [第一部分：Metal 渲染管线基础](#第一部分metal-渲染管线基础)
  - [一、整体渲染架构概览](#一整体渲染架构概览)
  - [二、Metal 设备与命令队列初始化](#二metal-设备与命令队列初始化)
  - [三、几何数据准备 —— 全屏四边形](#三几何数据准备--全屏四边形)
  - [四、纹理系统 —— 视频帧上传到 GPU](#四纹理系统--视频帧上传到-gpu)
  - [五、Shader 着色器详解 (MSL)](#五shader-着色器详解-msl)
  - [六、渲染命令编码 —— Draw Call 的底层过程](#六渲染命令编码--draw-call-的底层过程)
  - [七、CAMetalLayer 与三缓冲](#七cametallayer-与三缓冲)
  - [八、完整数据流总结](#八完整数据流总结)
- [第二部分：纹理上传优化技术](#第二部分纹理上传优化技术)
  - [九、优化路线总览](#九优化路线总览)
  - [十、示例 02: replaceRegion 直接上传](#十示例-02-replaceregion-直接上传)
  - [十一、示例 03: MTLBuffer + Blit 编码器异步上传](#十一示例-03-mtlbuffer--blit-编码器异步上传)
  - [十二、示例 04: 三缓冲 + Shared Memory 零拷贝](#十二示例-04-三缓冲--shared-memory-零拷贝)
  - [十三、示例 05: CVMetalTextureCache + YUV GPU 转换](#十三示例-05-cvmetaltexturecache--yuv-gpu-转换)
- [第三部分：综合对比与最佳实践](#第三部分综合对比与最佳实践)
  - [十四、五种方案的底层差异总结](#十四五种方案的底层差异总结)
  - [十五、性能分析与瓶颈](#十五性能分析与瓶颈)
  - [十六、Metal 与 OpenGL 的优劣势对比](#十六metal-与-opengl-的优劣势对比)
  - [十七、关键 API 速查表](#十七关键-api-速查表)
- [附录](#附录)

---

# 第一部分：Metal 渲染管线基础

> 基于示例 `01_basic_texture`，详细讲解 Metal 从初始化到画面最终呈现的完整底层逻辑。

---

## 一、整体渲染架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                    应用层 (Swift / Objective-C++)                 │
│  ┌──────────┐   ┌──────────────┐   ┌──────────────────────┐     │
│  │ AVFound. │──▶│ replaceRegion│──▶│ Command Encoder      │     │
│  │ 视频解码  │   │ 纹理上传      │   │ drawIndexedPrimitives│     │
│  └──────────┘   └──────────────┘   └──────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Metal 命令缓冲 (CPU 端构建)                    │
│                                                                   │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐     │
│  │ Blit Encoder │──▶│Render Encoder│──▶│ Present Drawable │     │
│  │ (数据拷贝)    │   │ (绘制命令)    │   │ (提交上屏)        │     │
│  └──────────────┘   └──────────────┘   └──────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              │  commit
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Metal 驱动 + GPU (硬件端执行)                    │
│                                                                   │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────┐ │
│  │顶点着色器  │──▶│ 图元装配   │──▶│ 光栅化      │──▶│片段着色器│ │
│  │(Vertex Fn) │   │(Primitive) │   │(Rasterize) │   │(Fragment│ │
│  └────────────┘   └────────────┘   └────────────┘   └────────┘ │
│                                                          │       │
│                                                          ▼       │
│                                              ┌──────────────┐   │
│                                              │ CAMetalLayer  │   │
│                                              │  Drawable    │   │
│                                              └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**Metal 与 OpenGL 的根本区别**：

| 维度 | OpenGL | Metal |
|------|--------|-------|
| 状态管理 | 全局状态机（隐式） | 显式对象（PSO / Descriptor） |
| 命令提交 | 立即模式（driver 记录） | 命令缓冲（应用显式记录） |
| 多线程 | 单线程绑定 context | 天生多线程友好 |
| 同步 | 驱动隐式管理 | 显式 fence / event |
| 着色器 | GLSL 运行时编译 | MSL 预编译为 .metallib |

---

## 二、Metal 设备与命令队列初始化

### 2.1 创建 MTLDevice

```swift
guard let device = MTLCreateSystemDefaultDevice() else {
    fatalError("Metal is not supported on this device")
}
```

**底层逻辑**：

1. `MTLCreateSystemDefaultDevice()` 返回一个 GPU 设备句柄
   - macOS 上可能是集显 / 独显 / 外接 GPU
   - iOS 上就是 Apple Silicon 集成 GPU
2. `MTLDevice` 是所有 Metal 资源的**工厂**，纹理、缓冲、PSO 都从它创建
3. 在 Apple Silicon 上，CPU 和 GPU **共享同一块物理内存**（UMA - Unified Memory Architecture）

### 2.2 创建命令队列

```swift
guard let commandQueue = device.makeCommandQueue() else {
    fatalError("Failed to create command queue")
}
```

- **MTLCommandQueue** 是提交命令的通道
- 一个 App 通常只需要 1~2 个队列（渲染 + 计算）
- 命令按提交顺序**顺序执行**（除非显式使用 event 打乱顺序）

### 2.3 CAMetalLayer 配置

```swift
metalLayer.device = device
metalLayer.pixelFormat = .bgra8Unorm  // ★ 注意是 BGRA，不是 RGBA
metalLayer.framebufferOnly = true      // 只用作显示，允许驱动优化
metalLayer.displaySyncEnabled = false  // 关闭 VSync（macOS）
```

**关键点**：
- `bgra8Unorm` 是 Apple 硬件的**原生格式**（省一次色彩通道交换）
- `framebufferOnly = true` 让驱动可以使用 Tile Memory 优化（TBDR 架构）
- iOS 上关闭 VSync 需要用 `CADisplayLink` 手动驱动

---

## 三、几何数据准备 —— 全屏四边形

### 3.1 为什么依然需要四边形？

与 OpenGL 完全相同：Metal 也是"图元光栅化"模型，必须提供顶点数据才能触发片段着色。视频帧作为纹理贴到全屏四边形上。

### 3.2 顶点数据结构（Swift 侧）

```swift
struct Vertex {
    var position: SIMD2<Float>
    var texCoord: SIMD2<Float>
}

let vertices: [Vertex] = [
    Vertex(position: [-1,  1], texCoord: [0, 0]),  // 左上
    Vertex(position: [ 1,  1], texCoord: [1, 0]),  // 右上
    Vertex(position: [ 1, -1], texCoord: [1, 1]),  // 右下
    Vertex(position: [-1, -1], texCoord: [0, 1]),  // 左下
]

let indices: [UInt16] = [0, 1, 2, 0, 2, 3]
```

### 3.3 坐标系差异

```
Metal NDC 坐标系             纹理坐标 (Metal)
     Y                            V
     ↑                            |
     |                     (0,0)──┼──(1,0)
(-1,1)───(1,1)                    |
  |         |                     |
  |  屏幕   |             (0,1)───┴───(1,1)
  |         |
(-1,-1)──(1,-1)              ← 注意：Metal 纹理原点在左上
     ──────→ X               ← 与 OpenGL 相反（GL 在左下）
```

**Metal vs OpenGL 坐标差异**：

| 系统 | NDC Y 轴 | 纹理 V 轴 | 深度范围 |
|------|---------|----------|---------|
| OpenGL | Y 向上 | V 向下（左下起） | [-1, 1] |
| Metal | Y 向上 | V 向下（左上起） | [0, 1] |
| Vulkan | Y 向下 | V 向下（左上起） | [0, 1] |

> ⚠️ 从 OpenGL 移植时，视频纹理**通常不需要翻转** UV（因为解码出来的像素本来就是左上起）。

### 3.4 创建顶点/索引缓冲

```swift
let vertexBuffer = device.makeBuffer(
    bytes: vertices,
    length: MemoryLayout<Vertex>.stride * vertices.count,
    options: .storageModeShared   // ★ CPU/GPU 都可访问
)

let indexBuffer = device.makeBuffer(
    bytes: indices,
    length: MemoryLayout<UInt16>.stride * indices.count,
    options: .storageModeShared
)
```

**Metal 的三种存储模式**：

| 模式 | CPU 可见 | GPU 可见 | 使用场景 |
|------|---------|---------|---------|
| `.storageModeShared` | ✅ | ✅ | 小数据、频繁更新（顶点/uniform） |
| `.storageModePrivate` | ❌ | ✅ | GPU 独享（大纹理、渲染目标） |
| `.storageModeManaged` | ✅ | ✅ (需同步) | macOS 独显，显式管理拷贝 |

> 💡 **Apple Silicon 特殊性**：UMA 架构下 `.storageModeShared` 就是零拷贝，无需 DMA。这是相比 OpenGL 的巨大优势。

---

## 四、纹理系统 —— 视频帧上传到 GPU

### 4.1 纹理描述符

```swift
let textureDescriptor = MTLTextureDescriptor()
textureDescriptor.pixelFormat = .bgra8Unorm
textureDescriptor.width = videoWidth
textureDescriptor.height = videoHeight
textureDescriptor.usage = [.shaderRead]
textureDescriptor.storageMode = .shared   // 或 .private

let texture = device.makeTexture(descriptor: textureDescriptor)!
```

**Metal 与 OpenGL 的对比**：

| OpenGL | Metal | 说明 |
|--------|-------|------|
| `glGenTextures` | `makeTexture(descriptor:)` | Metal 一步完成 |
| `glTexParameteri` | `MTLSamplerDescriptor` | Metal 采样器是独立对象 |
| `glBindTexture` | 无（编码时直接引用） | Metal 无绑定状态 |

### 4.2 每帧纹理上传 (replaceRegion) — 示例 01 的基础方案

```swift
let region = MTLRegionMake2D(0, 0, videoWidth, videoHeight)
texture.replace(
    region: region,
    mipmapLevel: 0,
    withBytes: frameData,
    bytesPerRow: videoWidth * 4  // BGRA = 4 字节
)
```

**参数详解**：

| 参数 | 含义 |
|------|------|
| `region` | 要更新的矩形区域 |
| `mipmapLevel` | Mipmap 层级 0 |
| `withBytes` | CPU 内存中的像素数据指针 |
| `bytesPerRow` | 每行字节数（stride，需处理对齐） |

**底层发生了什么**：

```
非 Apple Silicon (Intel Mac + 独显):
CPU 内存                              GPU 显存
┌──────────────────┐                 ┌──────────────────┐
│ frameData        │  ──DMA拷贝──▶  │ 纹理内存         │
│ BGRA 像素数据    │  (同步阻塞)     │ W × H × 4 bytes │
└──────────────────┘                 └──────────────────┘

Apple Silicon (M1/M2/M3, iOS):
统一内存 (Unified Memory)
┌──────────────────────────────────────────────────┐
│  frameData ←───memcpy───→ 纹理内存                │
│  (仅 CPU memcpy，无 DMA！)                        │
└──────────────────────────────────────────────────┘
```

⚠️ **性能特征**：
1. `replaceRegion` 是**同步**的：函数返回时数据已在纹理中
2. macOS 独显：涉及 PCIe DMA，与 OpenGL 类似的瓶颈
3. Apple Silicon：仅一次 memcpy，比 OpenGL 高效得多
4. 但仍然阻塞 CPU 线程

---

## 五、Shader 着色器详解 (MSL)

Metal Shading Language (MSL) 基于 C++14，编译到 Metal IR，然后由驱动 JIT 到 GPU ISA。

### 5.1 顶点函数（`basic.metal`）

```metal
#include <metal_stdlib>
using namespace metal;

struct VertexIn {
    float2 position [[attribute(0)]];
    float2 texCoord [[attribute(1)]];
};

struct VertexOut {
    float4 position [[position]];    // ★ 内置输出，等价于 gl_Position
    float2 texCoord;
};

vertex VertexOut vertex_main(VertexIn in [[stage_in]]) {
    VertexOut out;
    out.position = float4(in.position, 0.0, 1.0);
    out.texCoord = in.texCoord;
    return out;
}
```

**逐行解析**：

| 代码 | 底层含义 |
|------|----------|
| `[[attribute(0)]]` | 对应顶点描述符中的属性 0（等价于 GLSL `layout(location=0)`） |
| `[[stage_in]]` | 由前一阶段（顶点装配器）传入 |
| `[[position]]` | 内置语义，标记为裁剪空间坐标输出 |
| `vertex` 关键字 | 声明这是顶点函数（相比 GLSL 需要单独文件，MSL 可在一个文件里放多个函数） |

### 5.2 片段函数

```metal
fragment float4 fragment_main(VertexOut in [[stage_in]],
                              texture2d<float> tex [[texture(0)]],
                              sampler texSampler [[sampler(0)]]) {
    return tex.sample(texSampler, in.texCoord);
}
```

**逐行解析**：

| 代码 | 底层含义 |
|------|----------|
| `fragment` | 声明片段函数 |
| `texture2d<float>` | 纹理类型（模板参数是采样返回类型） |
| `[[texture(0)]]` | 绑定到纹理槽 0 |
| `[[sampler(0)]]` | 采样器槽 0（Metal 中采样器独立于纹理） |
| `tex.sample(...)` | 等价于 GLSL `texture(sampler2D, uv)` |

### 5.3 Shader 编译流程

```
MSL 源码 (.metal 文件)
       │
       │ 编译期（Xcode 构建时）
       ▼
┌──────────────────┐
│ metal 编译器      │  MSL → AIR (Apple Intermediate Representation)
│ (Xcode 内置)      │
└──────────────────┘
       │
       │ metallib 打包
       ▼
┌──────────────────┐
│ default.metallib │  嵌入 App Bundle
└──────────────────┘
       │
       │ 运行时加载
       ▼
┌──────────────────┐
│ device.makeDefault│
│ Library()        │  返回 MTLLibrary
└──────────────────┘
       │
       │ makeFunction(name:)
       ▼
┌──────────────────┐
│ MTLFunction      │  提取具体函数
└──────────────────┘
       │
       │ RenderPipelineDescriptor
       ▼
┌──────────────────┐
│ MTLRenderPipeline│  ★ PSO：显式的完整管线对象
│ State (PSO)      │    创建后不可修改
└──────────────────┘
```

**与 OpenGL 的核心差异**：Metal 的 Shader **预编译**为二进制，程序启动即可用，无 `glCompileShader` 的运行时抖动。

### 5.4 渲染管线状态对象 (PSO)

```swift
let pipelineDescriptor = MTLRenderPipelineDescriptor()
pipelineDescriptor.vertexFunction = library.makeFunction(name: "vertex_main")
pipelineDescriptor.fragmentFunction = library.makeFunction(name: "fragment_main")
pipelineDescriptor.colorAttachments[0].pixelFormat = .bgra8Unorm
pipelineDescriptor.vertexDescriptor = vertexDescriptor

let pipelineState = try device.makeRenderPipelineState(descriptor: pipelineDescriptor)
```

**PSO 的意义**：
- 把 Shader + 顶点布局 + 混合状态 + 光栅化状态**打包为不可变对象**
- 创建时驱动就能完成所有硬件寄存器配置
- 运行时切换 PSO 比 OpenGL 切换状态**快 10 倍以上**

---

## 六、渲染命令编码 —— Draw Call 的底层过程

### 6.1 命令编码代码

```swift
// 1. 获取下一帧的 Drawable
guard let drawable = metalLayer.nextDrawable() else { return }

// 2. 创建命令缓冲
let commandBuffer = commandQueue.makeCommandBuffer()!

// 3. 创建 render pass 描述符
let renderPassDescriptor = MTLRenderPassDescriptor()
renderPassDescriptor.colorAttachments[0].texture = drawable.texture
renderPassDescriptor.colorAttachments[0].loadAction = .clear
renderPassDescriptor.colorAttachments[0].clearColor = MTLClearColorMake(0, 0, 0, 1)
renderPassDescriptor.colorAttachments[0].storeAction = .store

// 4. 创建渲染命令编码器
let encoder = commandBuffer.makeRenderCommandEncoder(descriptor: renderPassDescriptor)!

// 5. 编码绘制命令
encoder.setRenderPipelineState(pipelineState)
encoder.setVertexBuffer(vertexBuffer, offset: 0, index: 0)
encoder.setFragmentTexture(texture, index: 0)
encoder.setFragmentSamplerState(sampler, index: 0)
encoder.drawIndexedPrimitives(
    type: .triangle,
    indexCount: 6,
    indexType: .uint16,
    indexBuffer: indexBuffer,
    indexBufferOffset: 0
)
encoder.endEncoding()

// 6. 提交上屏
commandBuffer.present(drawable)
commandBuffer.commit()
```

### 6.2 与 OpenGL 的根本区别

```
┌──────────────────────────────────────────────────────────────────┐
│                    OpenGL vs Metal 命令模型                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│ OpenGL (立即模式):                                                │
│                                                                   │
│   glClear()  ──▶ 立即执行? 不，驱动内部记录到隐藏的命令流           │
│   glBindTexture() ──▶ 修改全局状态机                              │
│   glDrawElements() ──▶ 驱动构造 draw call 送入 GPU                │
│   glSwapBuffers() ──▶ Flush 命令流并交换                          │
│                                                                   │
│   问题: 应用不知道驱动什么时候真正执行，难以优化                    │
│                                                                   │
│ Metal (显式命令缓冲):                                             │
│                                                                   │
│   makeCommandBuffer() ──▶ 创建可写命令容器                        │
│   makeRenderCommandEncoder() ──▶ 开始记录一个 render pass         │
│   setRenderPipelineState() ──▶ 记录 PSO 切换命令                  │
│   drawIndexedPrimitives() ──▶ 记录 draw call                     │
│   endEncoding() ──▶ 完成本段编码                                  │
│   commit() ──▶ ★ 现在才提交给 GPU 执行                            │
│                                                                   │
│   优势: 可在多线程并行编码不同的 command buffer                    │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 6.3 GPU 端管线执行

Metal 的 GPU 管线阶段与 OpenGL 几乎完全一致（毕竟都是硬件），但在 Apple Silicon 上有独特优化：

```
┌─────────────────────────────────────────────────────────────────────┐
│              Apple GPU 的 TBDR (Tile-Based Deferred Rendering)        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ① 顶点着色器（在整个 framebuffer 上执行）                          │
│     └─ 输出到中间存储（Parameter Buffer）                           │
│                                                                      │
│  ② 屏幕分块（Tile Binning）                                         │
│     └─ 将 framebuffer 分成 32×32 或 64×64 的 tile                   │
│     └─ 每个三角形关联到覆盖的 tile 列表                              │
│                                                                      │
│  ③ 逐 Tile 处理（在 Tile Memory 中）                                │
│     ├─ HSR (Hidden Surface Removal) 硬件级 Early-Z                  │
│     ├─ 片段着色器（只对可见片段执行！）                              │
│     └─ 混合、深度测试全部在片上内存中完成                            │
│                                                                      │
│  ④ Tile → 主内存（仅一次写回）                                       │
│                                                                      │
│  → 相比 OpenGL 的 Immediate Mode，带宽降低 5~10 倍                   │
└─────────────────────────────────────────────────────────────────────┘
```

对视频渲染来说，TBDR 的意义：**片段着色器只对最终可见的像素执行**，帧缓冲带宽极低，这也是 iPhone 能长时间流畅播 4K 视频的核心原因。

---

## 七、CAMetalLayer 与三缓冲

### 7.1 主循环（CADisplayLink 驱动）

```swift
let displayLink = CADisplayLink(target: self, selector: #selector(renderFrame))
displayLink.add(to: .main, forMode: .default)

@objc func renderFrame() {
    autoreleasepool {
        // 1. 更新视频帧
        updateVideoTexture()
        
        // 2. 编码渲染命令
        renderOneFrame()
    }
}
```

### 7.2 三缓冲机制

```
┌───────────────────────────────────────────────────────────────┐
│              CAMetalLayer 三缓冲 (Triple Buffering)             │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐              │
│  │ Drawable 0│   │ Drawable 1│   │ Drawable 2│              │
│  │ (显示中)  │   │ (合成中)  │   │ (App渲染) │              │
│  └───────────┘   └───────────┘   └───────────┘              │
│       ↑                ↑                ↑                    │
│       │                │                │                    │
│  显示控制器      Core Animation    Metal 渲染               │
│                                                                │
│  每帧 App 调用 nextDrawable() 拿到"App渲染"槽位              │
│  → present 后进入"合成中"                                    │
│  → 合成完毕进入"显示中"                                       │
│                                                                │
└───────────────────────────────────────────────────────────────┘
```

**与 OpenGL 双缓冲的差别**：
- OpenGL：前后两个 framebuffer 硬切换（`SwapBuffers`）
- Metal：3 个 Drawable 循环使用，允许 App 提前 1~2 帧渲染

**Frame Pacing 建议**：使用 `DispatchSemaphore(value: 3)` 限制在途帧数，避免 App 领先 GPU 太多。

---

## 八、完整数据流总结

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          一帧的完整数据流 (Metal)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. AVFoundation / VideoToolbox 解码 → CVPixelBuffer                     │
│                          │                                               │
│  2. texture.replace(region:) ──────┘                                     │
│     Apple Silicon: memcpy (UMA零拷贝)                                    │
│     Intel Mac: DMA 传输                                                  │
│                          │                                               │
│  3. GPU 纹理内存 ────────┘                                               │
│                          │                                               │
│  4. commandBuffer 编码 ──┘                                               │
│     ├─▶ setRenderPipelineState (PSO 切换，零开销)                        │
│     ├─▶ setFragmentTexture (绑定纹理到槽位)                              │
│     └─▶ drawIndexedPrimitives (提交 draw call)                          │
│                          │                                               │
│  5. commandBuffer.commit() → GPU 执行                                    │
│          │                                                               │
│          ├─▶ TBDR: 顶点→分块→逐tile片段处理                              │
│          └─▶ 写入 Drawable 纹理                                          │
│                          │                                               │
│  6. commandBuffer.present(drawable) ──┘                                  │
│     Core Animation 合成 → 屏幕                                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 第二部分：纹理上传优化技术

> 基于示例 02~05，逐步讲解从基础到高级的纹理上传优化技术。  
> 每个示例只重点讲解**与前一个示例不同的部分**。

---

## 九、优化路线总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Metal 纹理上传优化演进路线                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  01 基础方案         02 直接replace       03 Blit异步         04 三缓冲Shared│
│  ┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────┐    │
│  │每帧新建   │──────▶│复用纹理  │──────▶│MTLBuffer │──────▶│3×Shared  │    │
│  │Texture   │       │replace   │       │+ Blit    │       │无锁乒乓   │    │
│  │Region    │       │Region    │       │异步拷贝  │       │信号量同步 │    │
│  └──────────┘       └──────────┘       └──────────┘       └──────────┘    │
│                                                                              │
│                                              05 CVMetal + YUV                │
│                                         ┌──────────────────────┐            │
│                                         │ VideoToolbox 硬解     │            │
│                                         │ IOSurface 零拷贝      │            │
│                                         │ Y/CbCr 双纹理         │            │
│                                         │ Shader 转 RGB         │            │
│                                         └──────────────────────┘            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 性能对比预期 (1080p@60fps, Apple M1)

| 示例 | 每帧数据流转 | CPU 占用 | GPU 占用 | 预期帧时间 |
|------|-------------|---------|---------|-----------|
| 01 基础 | makeTexture+replace | ~8% | ~3% | ~8ms |
| 02 复用纹理 | replaceRegion 到已有纹理 | ~6% | ~3% | ~6ms |
| 03 Blit 异步 | Buffer→Blit→Texture | ~4% | ~3% | ~4ms |
| 04 三缓冲 | 3 个 shared buffer 轮转 | ~2% | ~3% | ~3ms |
| 05 CVMetal | IOSurface 直接映射为纹理 | <1% | ~2% | ~2ms |

---

## 十、示例 02: replaceRegion 直接上传

### 核心思想

**一句话总结**：预创建纹理，每帧只调用 `replaceRegion` 覆盖数据，不重新分配纹理对象。

### 与 01 的关键区别

```
01 的做法（每帧）:                    02 的做法:
┌─────────────────────┐              ┌─────────────────────┐
│ makeTexture()       │              │ 初始化时（仅一次）:  │
│  ├─ 分配纹理描述符    │              │   makeTexture()     │
│  ├─ 驱动分配 GPU 内存 │              │                     │
│  └─ replace 数据     │              │ 每帧:                │
│                     │              │   replaceRegion()   │
│ 每帧重新分配!        │              │   (原地更新)        │
└─────────────────────┘              └─────────────────────┘
```

### 关键代码

```swift
// 初始化时创建纹理（一次）
class VideoRenderer {
    let texture: MTLTexture
    
    init(device: MTLDevice, width: Int, height: Int) {
        let desc = MTLTextureDescriptor.texture2DDescriptor(
            pixelFormat: .bgra8Unorm,
            width: width, height: height,
            mipmapped: false
        )
        desc.usage = [.shaderRead]
        desc.storageMode = .shared   // Apple Silicon 上零拷贝
        self.texture = device.makeTexture(descriptor: desc)!
    }
    
    // 每帧调用
    func updateFrame(data: UnsafeRawPointer, bytesPerRow: Int) {
        let region = MTLRegionMake2D(0, 0, texture.width, texture.height)
        texture.replace(
            region: region,
            mipmapLevel: 0,
            withBytes: data,
            bytesPerRow: bytesPerRow
        )
    }
}
```

### 底层差异

```
┌──────────────────────────────────────────────────────────────┐
│                    Metal 存储模式对比                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ .storageModeShared (Apple Silicon 推荐):                     │
│   ┌────────────────────────────────────┐                    │
│   │  统一物理内存                       │                    │
│   │  ┌────────┐        ┌────────┐     │                    │
│   │  │ CPU 视图│◀──────▶│ GPU 视图│     │                    │
│   │  └────────┘        └────────┘     │                    │
│   │       (同一块内存，零拷贝)          │                    │
│   └────────────────────────────────────┘                    │
│                                                               │
│ .storageModePrivate (Intel Mac 独显推荐):                    │
│   ┌────────────┐            ┌────────────┐                  │
│   │ CPU 内存    │  ── DMA ──▶│ VRAM        │                  │
│   │ (staging)  │            │ (纹理)      │                  │
│   └────────────┘            └────────────┘                  │
│                                                               │
│ .storageModeManaged (Intel Mac 兼容模式):                    │
│   ┌────────────┐            ┌────────────┐                  │
│   │ CPU 副本   │◀── 显式同步 ▶│ GPU 副本   │                  │
│   │            │  didModify/  │            │                  │
│   │            │  synchronize │            │                  │
│   └────────────┘            └────────────┘                  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 性能提升原理

1. **纹理对象复用**：避免了 `makeTexture` 的描述符解析和驱动内存分配
2. **Apple Silicon 上零 DMA**：Shared 模式下 memcpy 就是全部开销
3. **驱动缓存友好**：同一纹理对象反复更新，驱动可以做更好的资源管理

### 局限性

- `replaceRegion` 是**同步**的：函数返回时上传已完成
- 若 GPU 还在读取旧纹理数据，会产生**隐式等待**
- 想要真正并行需要用 Blit 编码器或多缓冲

---

## 十一、示例 03: MTLBuffer + Blit 编码器异步上传

### 核心思想

**一句话总结**：使用 `MTLBuffer` 作为 staging buffer，通过 Blit 编码器提交异步 GPU 端拷贝命令。

### Blit 编码器是什么？

Blit 编码器是 Metal 中专门处理**内存拷贝**的命令编码器（类似 Vulkan 的 Transfer Queue），可以：
- Buffer ↔ Buffer 拷贝
- Buffer ↔ Texture 拷贝
- Texture ↔ Texture 拷贝
- 生成 mipmap
- 内存同步（`synchronize`）

### 与 02 的关键区别

```
02 的做法（同步）:                    03 的做法（异步）:
┌─────────────────────┐              ┌─────────────────────┐
│ texture.replace()   │              │ 1. memcpy → buffer  │
│  阻塞，等待完成      │              │ 2. Blit编码器发起拷贝│
│                     │              │    (仅提交命令)     │
│                     │              │ 3. commandBuffer提交│
│                     │              │ 4. CPU 立即返回     │
└─────────────────────┘              └─────────────────────┘
```

### 关键代码

```swift
class BlitVideoRenderer {
    let device: MTLDevice
    let commandQueue: MTLCommandQueue
    let texture: MTLTexture       // .storageModePrivate
    let stagingBuffer: MTLBuffer  // .storageModeShared
    
    init(device: MTLDevice, width: Int, height: Int) {
        self.device = device
        self.commandQueue = device.makeCommandQueue()!
        
        // 纹理使用 private 模式（GPU 独享，性能最佳）
        let texDesc = MTLTextureDescriptor.texture2DDescriptor(
            pixelFormat: .bgra8Unorm,
            width: width, height: height, mipmapped: false
        )
        texDesc.usage = [.shaderRead]
        texDesc.storageMode = .private
        self.texture = device.makeTexture(descriptor: texDesc)!
        
        // Staging buffer 使用 shared 模式（CPU 可写）
        let bufferSize = width * height * 4
        self.stagingBuffer = device.makeBuffer(
            length: bufferSize,
            options: .storageModeShared
        )!
    }
    
    func updateFrame(data: UnsafeRawPointer, size: Int) {
        // 1. CPU 写入 staging buffer
        memcpy(stagingBuffer.contents(), data, size)
        
        // 2. 创建命令缓冲和 Blit 编码器
        let cmdBuf = commandQueue.makeCommandBuffer()!
        let blit = cmdBuf.makeBlitCommandEncoder()!
        
        // 3. 编码 buffer → texture 拷贝
        blit.copy(
            from: stagingBuffer,
            sourceOffset: 0,
            sourceBytesPerRow: texture.width * 4,
            sourceBytesPerImage: texture.width * texture.height * 4,
            sourceSize: MTLSize(width: texture.width, height: texture.height, depth: 1),
            to: texture,
            destinationSlice: 0,
            destinationLevel: 0,
            destinationOrigin: MTLOrigin(x: 0, y: 0, z: 0)
        )
        blit.endEncoding()
        
        // 4. 提交（异步！）
        cmdBuf.commit()
        // CPU 立即返回，不等待拷贝完成
    }
}
```

### 底层数据流

```
┌────────────────────────────────────────────────────────────────┐
│                Blit 异步上传时序                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CPU 线程:                                                      │
│  ──[memcpy→buffer]──[encode blit]──[commit]──[继续执行]──      │
│                                       │                         │
│                                       │ (仅提交命令)             │
│                                       ▼                         │
│  GPU DMA 引擎:                                                  │
│  ─────────────────────[Blit: buffer→texture]──[完成]──         │
│                                                                 │
│  GPU 渲染引擎:                                                  │
│  ────────────────────────────────────[等Blit完成]──[渲染]──    │
│                                                                 │
│  Metal 自动依赖追踪:                                             │
│  同一 CommandQueue 内的命令按提交顺序执行                        │
│  渲染 pass 会自动等待 blit pass 完成                             │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### storageModePrivate 的意义

对比 02（shared 纹理）与 03（private 纹理）：

| 维度 | 02 shared 纹理 | 03 private 纹理 |
|------|--------------|----------------|
| CPU 写入速度 | 快（直接写内存） | 需通过 staging buffer |
| GPU 读取速度 | 中（一致性开销） | 快（GPU 独享缓存） |
| 纹理压缩 | 不支持 | 支持（驱动自动压缩） |
| Tile Memory | 部分支持 | 完全支持 |
| 推荐场景 | 频繁 CPU 更新 | GPU 独享（推荐生产用） |

### 性能提升原理

1. **纹理使用 private 模式**：GPU 内存布局最优，可启用压缩
2. **CPU/GPU 并行**：Blit 提交后 CPU 立即返回，做下一帧解码
3. **Metal 自动同步**：无需手动 fence，驱动确保渲染前拷贝完成

### 局限性

- 只有 1 个 staging buffer，若下一帧 CPU 写入时 GPU 还在读，会隐式等待
- 需要**多个 staging buffer 轮转**才能完全消除等待

---

## 十二、示例 04: 三缓冲 + Shared Memory 零拷贝

### 核心思想

**一句话总结**：3 个 staging buffer 循环使用，通过 `DispatchSemaphore` 控制在途帧数，实现 CPU/GPU 完全并行。

### 为什么是"3"缓冲？

```
┌─────────────────────────────────────────────────────────────────────┐
│                    三缓冲的时间线                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  帧 N:                                                               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │ CPU 写 Buf_0  │ │ GPU Blit Buf_2│ │ GPU 渲染 Buf_1│  ← 三路并行  │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                      │
│  帧 N+1:                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │ CPU 写 Buf_1  │ │ GPU Blit Buf_0│ │ GPU 渲染 Buf_2│               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                      │
│  帧 N+2:                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │ CPU 写 Buf_2  │ │ GPU Blit Buf_1│ │ GPU 渲染 Buf_0│               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                      │
│  → GPU 有 1 帧的处理延迟，恰好被 3 缓冲吸收                          │
│  → 显示落后 2 帧，但吞吐量最大                                       │
└─────────────────────────────────────────────────────────────────────┘
```

Apple 官方 Best Practice：`MaxBuffersInFlight = 3`。

### 与 03 的关键区别

| 方面 | 03 单 Buffer | 04 三 Buffer |
|------|-------------|-------------|
| Staging 数量 | 1 | 3 |
| CPU/GPU 关系 | 部分并行 | 完全并行 |
| 同步机制 | Metal 隐式 | Semaphore 显式 |
| 延迟 | 0~1 帧 | 2 帧 |
| 吞吐量 | 中 | 最高 |

### 关键代码

```swift
class TripleBufferRenderer {
    static let maxFramesInFlight = 3
    let semaphore = DispatchSemaphore(value: maxFramesInFlight)
    
    var stagingBuffers: [MTLBuffer] = []
    var frameIndex = 0
    let texture: MTLTexture
    
    init(device: MTLDevice, width: Int, height: Int) {
        let bufferSize = width * height * 4
        for _ in 0..<Self.maxFramesInFlight {
            let buf = device.makeBuffer(length: bufferSize, options: .storageModeShared)!
            stagingBuffers.append(buf)
        }
        // 纹理省略...
    }
    
    func updateAndRender(frameData: UnsafeRawPointer, size: Int) {
        // ★ 关键：等待信号量（最多 3 帧在途）
        semaphore.wait()
        
        // 选择当前帧的 staging buffer
        let currentBuffer = stagingBuffers[frameIndex]
        frameIndex = (frameIndex + 1) % Self.maxFramesInFlight
        
        // 1. CPU 写入
        memcpy(currentBuffer.contents(), frameData, size)
        
        // 2. 创建命令缓冲
        let cmdBuf = commandQueue.makeCommandBuffer()!
        
        // ★ 关键：完成回调中释放信号量
        cmdBuf.addCompletedHandler { [weak self] _ in
            self?.semaphore.signal()
        }
        
        // 3. Blit 编码
        let blit = cmdBuf.makeBlitCommandEncoder()!
        blit.copy(from: currentBuffer, sourceOffset: 0, ...,
                  to: texture, destinationSlice: 0, ...)
        blit.endEncoding()
        
        // 4. 渲染编码
        let renderEnc = cmdBuf.makeRenderCommandEncoder(descriptor: ...)!
        renderEnc.setRenderPipelineState(pipelineState)
        renderEnc.setFragmentTexture(texture, index: 0)
        renderEnc.drawIndexedPrimitives(...)
        renderEnc.endEncoding()
        
        // 5. 提交
        cmdBuf.present(drawable)
        cmdBuf.commit()
    }
}
```

### 信号量的作用图解

```
┌────────────────────────────────────────────────────────────────┐
│              DispatchSemaphore(value: 3) 工作原理                │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  信号量计数 = 3 (初始)                                          │
│                                                                 │
│  帧 1: wait() → 计数=2, 提交, GPU 处理中                       │
│  帧 2: wait() → 计数=1, 提交, GPU 处理中                       │
│  帧 3: wait() → 计数=0, 提交, GPU 处理中                       │
│  帧 4: wait() → 阻塞！ (计数=0)                                │
│           │                                                     │
│           │  等待帧 1 完成                                      │
│           ▼                                                     │
│  帧 1 GPU 完成 → signal() → 计数=1 → 帧 4 wait() 返回          │
│                                                                 │
│  → 保证 CPU 最多领先 GPU 3 帧，防止显存爆炸                     │
│  → 也保证 CPU 有足够 buffer 可用，永不等待                      │
└────────────────────────────────────────────────────────────────┘
```

### 性能提升原理

| 优化维度 | 效果 |
|---------|------|
| 三路并行 | CPU 写 / GPU Blit / GPU 渲染 三个阶段同时进行 |
| 零显式等待 | Semaphore 只在超过 3 帧时才阻塞 |
| GPU 命令队列饱和 | 队列中始终有 2~3 个 commandBuffer 排队执行 |
| 帧率上限 | 由 GPU 处理能力决定，而非 CPU/GPU 交互 |

### 代价

- **2 帧显示延迟**（约 33ms@60fps），对视频播放可接受，对交互游戏需权衡
- 内存占用 × 3
- 需要正确处理 Drawable 生命周期（避免 `nextDrawable()` 死锁）

---

## 十三、示例 05: CVMetalTextureCache + YUV GPU 转换

### 核心思想

**一句话总结**：VideoToolbox 硬解直接产出 `CVPixelBuffer`（内部是 IOSurface），通过 `CVMetalTextureCache` **零拷贝**映射为 Metal 纹理，Shader 完成 YUV→RGB 转换。

### 与前面所有示例的根本区别

前面 01~04 的优化都基于**软件解码 + BGRA 上传**：
- `AVAssetReader` 输出 BGRA 帧
- CPU 端 memcpy 到 staging
- Blit 或直接上传到纹理

示例 05 完全跳过这些步骤：
- **VideoToolbox** 硬解出 `CVPixelBuffer` (格式 `kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange`)
- IOSurface 底层是**跨进程可共享的 GPU 内存对象**
- `CVMetalTextureCache` 直接把 IOSurface 映射为 `MTLTexture`（零拷贝！）

```
┌─────────────────────────────────────────────────────────────────┐
│              数据流对比                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 01~04 数据流:                                                    │
│  ┌────────┐  BGRA解码  ┌────────┐  memcpy  ┌────────┐          │
│  │ AVAsset│──────────▶│ CPU内存 │─────────▶│ Metal  │          │
│  │Reader  │  8.3MB/帧 │        │  拷贝     │ Texture│          │
│  └────────┘           └────────┘          └────────┘          │
│                                                                  │
│ 05 数据流:                                                       │
│  ┌────────┐  YUV硬解  ┌────────┐  零拷贝    ┌────────┐          │
│  │Video   │──────────▶│IOSurface│─────────▶│Y+CbCr  │          │
│  │Toolbox │  硬件路径 │(内核对象)│  仅句柄   │纹理×2  │          │
│  └────────┘           └────────┘           └────────┘          │
│                                                                  │
│  → 0 次 memcpy！数据物理上只有一份，被内核对象引用                 │
└─────────────────────────────────────────────────────────────────┘
```

### CVMetalTextureCache 是什么？

它是 CoreVideo 提供的**跨框架桥接器**，能把 `CVPixelBuffer` 中的 IOSurface **零拷贝**映射为 Metal 纹理。

关键特性：
- 只做**引用**，不做拷贝
- 支持 YUV 多平面（一次映射得到多个纹理）
- 与 GPU 硬解流水线深度集成

### 关键代码

#### 1. 初始化 Cache

```swift
var textureCache: CVMetalTextureCache?
CVMetalTextureCacheCreate(nil, nil, device, nil, &textureCache)
```

#### 2. VideoToolbox 硬解出 CVPixelBuffer

```swift
// 配置解码器输出 NV12 格式
let attrs: [String: Any] = [
    kCVPixelBufferPixelFormatTypeKey as String:
        kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange,
    kCVPixelBufferMetalCompatibilityKey as String: true,  // ★ 关键
    kCVPixelBufferIOSurfacePropertiesKey as String: [:]
]

// 每帧从 VTDecompressionSession 得到 pixelBuffer
// (省略解码流程)
let pixelBuffer: CVPixelBuffer = ...
```

**NV12 格式内存布局**：

```
CVPixelBuffer (NV12 双平面):
┌────────────────────────────────────────┐
│ Plane 0: Y (亮度，全分辨率)              │
│  ┌─┬─┬─┬─┬─┬─┬─┬─┐                    │
│  │Y│Y│Y│Y│Y│Y│Y│Y│  W × H 字节         │
│  ├─┼─┼─┼─┼─┼─┼─┼─┤                    │
│  │Y│Y│Y│Y│Y│Y│Y│Y│                    │
│  └─┴─┴─┴─┴─┴─┴─┴─┘                    │
├────────────────────────────────────────┤
│ Plane 1: CbCr (色度，1/2×1/2 分辨率)     │
│  ┌───┬───┬───┬───┐                    │
│  │CbCr│CbCr│CbCr│CbCr│  (W/2) × (H/2) × 2字节│
│  ├───┼───┼───┼───┤                    │
│  │CbCr│CbCr│CbCr│CbCr│                │
│  └───┴───┴───┴───┘                    │
└────────────────────────────────────────┘

数据量 = W×H + (W/2)×(H/2)×2 = 1.5 × W × H  (与 YUV420P 相同)
但 CbCr 交织存储，硬件更友好
```

#### 3. 零拷贝映射为 Metal 纹理

```swift
func makeTextures(from pixelBuffer: CVPixelBuffer) -> (MTLTexture, MTLTexture)? {
    let width = CVPixelBufferGetWidth(pixelBuffer)
    let height = CVPixelBufferGetHeight(pixelBuffer)
    
    // Y 平面：单通道全分辨率
    var cvTexY: CVMetalTexture?
    CVMetalTextureCacheCreateTextureFromImage(
        nil, textureCache!, pixelBuffer, nil,
        .r8Unorm,                    // ★ 单通道 8 位
        width, height, 0,            // ★ planeIndex = 0
        &cvTexY
    )
    
    // CbCr 平面：双通道半分辨率
    var cvTexCbCr: CVMetalTexture?
    CVMetalTextureCacheCreateTextureFromImage(
        nil, textureCache!, pixelBuffer, nil,
        .rg8Unorm,                   // ★ 双通道 8 位
        width / 2, height / 2, 1,    // ★ planeIndex = 1
        &cvTexCbCr
    )
    
    guard let y = cvTexY.flatMap({ CVMetalTextureGetTexture($0) }),
          let cbcr = cvTexCbCr.flatMap({ CVMetalTextureGetTexture($0) }) else {
        return nil
    }
    return (y, cbcr)
}
```

**关键点**：
- `.r8Unorm` / `.rg8Unorm` 是 Metal 单/双通道纹理格式
- `planeIndex` 参数指定从 CVPixelBuffer 的第几个平面创建纹理
- 返回的 `MTLTexture` 与 IOSurface 共享同一块物理内存

#### 4. 绑定到渲染管线

```swift
encoder.setFragmentTexture(yTexture, index: 0)
encoder.setFragmentTexture(cbcrTexture, index: 1)
encoder.setFragmentSamplerState(sampler, index: 0)
encoder.drawIndexedPrimitives(...)
```

### YUV→RGB 片段函数（`yuv_nv12.metal`）

```metal
#include <metal_stdlib>
using namespace metal;

struct VertexOut {
    float4 position [[position]];
    float2 texCoord;
};

// BT.709 转换矩阵（Video Range: Y∈[16,235], CbCr∈[16,240]）
constant float3x3 kColorConversionMatrix709 = float3x3(
    float3(1.164,  1.164, 1.164),
    float3(0.000, -0.213, 2.112),
    float3(1.793, -0.533, 0.000)
);

fragment float4 yuv_nv12_fragment(
    VertexOut in [[stage_in]],
    texture2d<float> texY    [[texture(0)]],
    texture2d<float> texCbCr [[texture(1)]],
    sampler s                [[sampler(0)]]
) {
    float y  = texY.sample(s, in.texCoord).r;
    float2 cbcr = texCbCr.sample(s, in.texCoord).rg;
    
    // Video Range 归一化
    float3 yuv = float3(y - 16.0/255.0, cbcr - float2(0.5));
    float3 rgb = kColorConversionMatrix709 * yuv;
    
    return float4(saturate(rgb), 1.0);
}
```

**逐段解析**：

| 代码 | 含义 |
|------|------|
| `constant float3x3 ...` | 常量矩阵，编译期计算，寄存器保存 |
| `texCbCr.sample(...).rg` | 双通道纹理，`.rg` 分量分别是 Cb 和 Cr |
| `y - 16.0/255.0` | Video Range 的黑电平偏移 |
| `cbcr - float2(0.5)` | 色度中心化到 [-0.5, +0.5] |
| `saturate(rgb)` | 等价于 `clamp(rgb, 0, 1)`，硬件专用指令 |

### CbCr 双通道纹理的自动上采样

```
CbCr 纹理实际尺寸: (W/2) × (H/2)
采样坐标 texCoord: 归一化 [0,1]

当 texCoord = (0.5, 0.5) 时:
  Y 纹理采样位置: 像素 (W/2, H/2)
  CbCr 纹理采样位置: 像素 (W/4, H/4)  ← 落在整数格子上

当 texCoord = (0.501, 0.501) 时:
  CbCr 采样位置: 像素 (W/4+0.5, H/4+0.5)
  → 采样器自动做双线性插值！
  
→ 完全不需要手动处理 4:2:0 的 2×2 色度共享
→ 与示例 05 (OpenGL 版) 的 YUV420P 三平面方案相比：
  * NV12 只需 2 个纹理（Y + CbCr）而非 3 个
  * CbCr 交织存储对 GPU 缓存更友好
```

### 性能提升原理

| 优化维度 | 效果 |
|---------|------|
| 硬件解码 | VideoToolbox 使用专用视频解码器，功耗极低 |
| IOSurface 零拷贝 | 数据物理上只有一份，跨框架共享 |
| GPU 直接可读 | 无 memcpy、无 DMA、无 Blit |
| 数据量减少 62% | NV12 vs BGRA |
| GPU 并行转换 | 每像素并行 YUV→RGB |
| 硬件路径完整 | 视频解码器 → GPU → 显示，全在 SoC 内部 |

### 与 Android SurfaceTexture 的类比

| Android | iOS/macOS |
|---------|-----------|
| SurfaceTexture (外部纹理) | CVMetalTextureCache |
| GraphicBuffer | IOSurface |
| GL_TEXTURE_EXTERNAL_OES | Y + CbCr 双 MTLTexture |
| 驱动自动 YUV→RGB | Shader 手动转换 |

---

# 第三部分：综合对比与最佳实践

---

## 十四、五种方案的底层差异总结

### 数据传输方式对比

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    五种方案的 CPU-GPU 交互时序                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ 01 makeTexture + replace:                                                │
│ CPU: ══[create+replace]══════════════════[render encode]══               │
│ GPU: ────────────────────────────────────────────────[render]──         │
│      ↑ 完全阻塞                                                          │
│                                                                          │
│ 02 复用 replaceRegion:                                                   │
│ CPU: ══[replace]═════════════════════════[render encode]══               │
│ GPU: ────────────────────────────────────────────────[render]──         │
│      ↑ 省去对象创建                                                      │
│                                                                          │
│ 03 Blit 异步:                                                            │
│ CPU: ═[memcpy]═[blit encode]═[render encode]═[commit]═[next frame]──    │
│ GPU: ─────────────────[blit]──[render]──                                │
│      ↑ CPU 提前 1 帧                                                    │
│                                                                          │
│ 04 三缓冲:                                                                │
│ CPU: ═[Buf0]═[Buf1]═[Buf2]═[wait sema]═[Buf0]═                          │
│ GPU:      ═[blit Buf0]═[render Buf0]═[blit Buf1]═[render Buf1]═         │
│      ↑ 三阶段完全并行                                                    │
│                                                                          │
│ 05 CVMetal + YUV:                                                        │
│ VTDec: ═[HW decode → IOSurface]════════════════════════════             │
│ CPU:   ═[map to MTLTexture (零拷贝)]═[encode]══                         │
│ GPU:   ══════════════════════════════[YUV→RGB + render]══               │
│      ↑ 数据物理上只有一份                                                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Shader 差异对比

| 示例 | 顶点函数 | 片段函数 | 纹理数量 |
|------|---------|---------|---------|
| 01~04 | vertex_main | fragment_main (BGRA 采样) | 1 |
| 05 | vertex_main (相同) | yuv_nv12_fragment (YUV→RGB) | 2 (Y + CbCr) |

### 最佳实践组合

```
终极方案: VideoToolbox + CVMetalTextureCache + 三缓冲

┌──────────┐  硬解     ┌──────────┐  IOSurface  ┌──────────┐  Shader   ┌──────┐
│VTDecompr │─────────▶│CVPixelBuf│  零拷贝     │Y+CbCr    │─────────▶│BGRA  │
│Session   │          │(NV12)    │            │MTLTexture│  YUV→RGB │Drawab│
└──────────┘          └──────────┘            └──────────┘           └──────┘
                         (IOSurface 引用池，与 3 个 in-flight 帧对应)

预期性能 (iPhone 15 Pro, 4K@60fps HEVC):
  CPU 占用: <2%
  GPU 占用: <5%
  内存带宽: <100 MB/s
  功耗: <500mW (整机)
```

---

## 十五、性能分析与瓶颈

### 15.1 各方案的核心瓶颈

| 方案 | 瓶颈原因 | 优化方向 |
|------|---------|---------| 
| 01 | 每帧创建纹理对象 | 复用纹理（→ 02） |
| 02 | 同步阻塞 | 异步 Blit（→ 03） |
| 03 | 单 buffer 隐式等待 | 多 buffer 轮转（→ 04） |
| 04 | 软解 + BGRA 传输 | 硬解 + YUV（→ 05） |
| 05 | 已接近硬件极限 | （生产级最优） |

### 15.2 理论带宽计算 (1080p@60fps)

```
01~04 方案 (BGRA):
  每帧 = 1920 × 1080 × 4 = 8.3 MB
  60fps 带宽 = 498 MB/s
  Apple Silicon UMA 带宽 = 200~400 GB/s
  利用率 ≈ 0.15%

05 方案 (NV12 + 零拷贝):
  实际拷贝 = 0 MB/s (仅句柄传递)
  数据"通过" = 3.1 MB/帧 × 60 = 186 MB/s
  但 GPU 直接读取 IOSurface，不产生额外流量
```

### 15.3 功耗对比 (iPhone 15 Pro, 1080p 视频播放 1 小时)

| 方案 | 电池消耗 |
|------|---------|
| 01 软解 + BGRA + 每帧新纹理 | ~15% |
| 04 软解 + 三缓冲 Blit | ~8% |
| 05 硬解 + CVMetal 零拷贝 | ~3% |

> Apple 官方 AVPlayer 内部就是采用类似 05 的方案，这也是 iPhone 能播 6 小时高清视频的核心原因。

---

## 十六、Metal 与 OpenGL 的优劣势对比

> 本节从**设计哲学 → 能力矩阵 → 视频场景专项 → 选型建议**四个层次系统性对比 Metal 与 OpenGL (ES)，  
> 帮助从 OpenGL 迁移到 Apple 平台、或做技术选型的读者建立清晰认知。

### 16.1 设计哲学差异 —— 谁来控制硬件？

```
┌──────────────────────────────────────────────────────────────────────┐
│  OpenGL：状态机 + 隐式驱动 (1992 年设计思想)                          │
│  ────────────────────────────────────────────────────────────         │
│  glBindTexture()  ──▶ 修改全局状态                                     │
│  glTexSubImage2D()──▶ 驱动猜"你要干嘛" → 隐式同步 → 隐式重排           │
│  glDrawElements() ──▶ 驱动内部构造 draw call                          │
│                          │                                            │
│                          ▼                                            │
│                驱动做了大量"善后"工作                                 │
│                但你无法预测何时真正执行                                │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  Metal：显式命令缓冲 + 预编译 PSO (2014 年现代设计)                    │
│  ────────────────────────────────────────────────────────────         │
│  makeCommandBuffer()          ──▶ 显式创建命令容器                     │
│  encoder.setRenderPipelineState(pso) ──▶ 切换预烘焙状态对象           │
│  encoder.drawIndexedPrimitives(...)   ──▶ 记录 draw call              │
│  commit()                     ──▶ ★ 此刻才真正送 GPU                  │
│                          │                                            │
│                          ▼                                            │
│                所有行为可预测、可多线程、可 profile                    │
└──────────────────────────────────────────────────────────────────────┘
```

**一句话总结**：OpenGL 是"驱动帮你做决定"，Metal 是"你告诉驱动怎么做"。

---

### 16.2 能力矩阵 —— 12 维正面对比

| # | 维度 | OpenGL (ES) | Metal | 胜方 |
|---|------|------------|-------|------|
| 1 | **跨平台** | Windows / Linux / macOS / iOS / Android / Web | 仅 Apple 生态 | OpenGL |
| 2 | **学习曲线** | 平缓，半天出三角形 | 中等，需理解 PSO / Encoder | OpenGL |
| 3 | **运行时 CPU 开销** | 每命令驱动验证，开销大 | 命令预录制，提交极轻 | Metal |
| 4 | **多线程能力** | Context 绑单线程，扩展支持差 | 天生多线程，并行编码 | Metal |
| 5 | **着色器编译** | GLSL 运行时编译（首次卡顿） | MSL 预编译为 `.metallib` | Metal |
| 6 | **状态切换** | 改全局状态机，驱动重算 | 切 PSO（不可变对象） | Metal (10×+) |
| 7 | **内存模型** | 抽象，驱动管理 | UMA 共享内存，零拷贝 | Metal (Apple Silicon) |
| 8 | **GPU 架构适配** | 通用 Immediate Mode | TBDR 原生（HSR / Tile Memory） | Metal (Apple GPU) |
| 9 | **YUV 零拷贝** | `GL_TEXTURE_EXTERNAL_OES`（仅 Android） | `CVMetalTextureCache`（iOS/macOS） | 平手（各主平台） |
| 10 | **调试工具** | 黑屏难定位，工具老旧 | Xcode Frame Capture / GPU Trace | Metal |
| 11 | **生态资料** | 海量教程、SO 答案 | 资料成长中但偏少 | OpenGL |
| 12 | **Apple 平台前景** | 已弃用（macOS）/受限（iOS） | 官方唯一推荐 | Metal |

---

### 16.3 视频渲染场景的 6 大专项对比

针对本文档的核心主题"视频帧上传 + 全屏渲染"：

#### ① 纹理上传路径（软解 BGRA 帧）

```
OpenGL ES:
  CPU frame ──memcpy──▶ 驱动缓冲 ──DMA/隐式复制──▶ GPU 纹理
                     ↑ 至少一次额外拷贝

Metal (Apple Silicon):
  CPU frame ──memcpy──▶ shared 纹理（即 GPU 纹理，同一物理内存）
                     ↑ UMA 零 DMA，只有一次 memcpy
```
**胜方：Metal**（Apple Silicon 上省一次 DMA）

#### ② 异步上传机制

| 项目 | OpenGL ES | Metal |
|------|-----------|-------|
| 手段 | PBO + `glMapBufferRange` | `MTLBuffer` + Blit 编码器 |
| 缓冲管理 | 手动双/三 PBO 轮转 | 驱动自动依赖追踪 |
| 同步 | 手动 Fence Sync | Metal 自动 hazard tracking |
| 代码量 | 多，易出错 | 少，简洁 |

**胜方：Metal**（Blit 是一等公民命令类型）

#### ③ YUV 硬解零拷贝（对应示例 05）

| 平台 | OpenGL 路径 | Metal 路径 |
|------|-------------|-----------|
| iOS/macOS | ⚠️ 无官方 API 桥接 VideoToolbox | ✅ `CVMetalTextureCache` |
| 数据拷贝次数 | 至少 1 次 memcpy | **0 次**（IOSurface 引用） |
| YUV→RGB | Shader 手动写 | Shader 手动写（相同） |

**胜方：Metal**（Apple 生态是碾压性优势）

#### ④ 多帧并发 / Frame Pacing

```
OpenGL:  EGL 双缓冲，扩展支持有限
         └─ 想做三缓冲？需 EXT_swap_control_tear + 手动多 PBO

Metal:   CAMetalLayer 原生三缓冲 + DispatchSemaphore(value: 3)
         └─ 官方 best practice，一行代码控流
```
**胜方：Metal**（机制原生、可控）

#### ⑤ GPU 带宽（片段着色阶段）

```
OpenGL Immediate Mode (桌面 GL):
  每次片段着色都读写主 framebuffer → 带宽爆炸

Metal on Apple GPU (TBDR):
  片上 Tile Memory 完成所有中间读写 → 仅一次写回
  带宽降低 5~10×，功耗降低 3~5×
```
**胜方：Metal**（Apple GPU 架构红利）

#### ⑥ 开发效率（原型阶段）

```
OpenGL ES:  一天出一个能播的 Demo
Metal:      两天搭好 PSO + Encoder 骨架
```
**胜方：OpenGL**（原型阶段仍快，但差距不大）

---

### 16.4 迁移决策树（Apple 平台）

```
                    你要在 Apple 平台做视频渲染？
                              │
                    ┌─────────┴─────────┐
                    │                   │
              有历史 OpenGL 包袱？   全新项目？
                    │                   │
                    ▼                   ▼
        ┌──────────────────┐     ┌──────────────┐
        │ 短期维护 → 保留   │     │ 直接选 Metal │
        │ 长期规划 → 迁 Metal│     │ 无悬念       │
        └──────────────────┘     └──────┬───────┘
                                        │
                                        ▼
                              选哪个 Metal 方案？
                              ┌────────┴────────┐
                              │                 │
                        iOS 移动端          macOS 桌面
                        (功耗优先)          (性能/兼容)
                              │                 │
                              ▼                 ▼
                       示例 05             示例 04
                       VideoToolbox        三缓冲 + Shared
                       + CVMetalCache      (UMA 零拷贝)
```

---

### 16.5 结论 —— 何时选谁？

**依然选 OpenGL (ES) 的场景**：
- ✅ 一套代码跨 Android / Windows / Linux / WebGL
- ✅ 维护既有 OpenGL 代码库，无重写预算
- ✅ 目标是最广泛的兼容性（老 Android 设备）

**必须选 Metal 的场景**：
- ✅ 只做 Apple 平台（iOS / macOS / iPadOS / visionOS）
- ✅ 追求极致功耗与帧率（移动端长时视频播放）
- ✅ 需要 YUV 硬解零拷贝（`CVMetalTextureCache`）
- ✅ 项目长期演进（OpenGL 在 Apple 已无未来）

> 💡 **一句话终极总结**：在 Apple 平台上，Metal 对 OpenGL 是**代际优势**——  
> 这不只是 API 更好，而是 UMA + TBDR 硬件架构的必然结果。  
> **新项目没有理由再选 OpenGL**。

---

## 十七、关键 API 速查表

| API | 示例 | 作用 |
|-----|------|------|
| `MTLCreateSystemDefaultDevice()` | 01~05 | 获取默认 GPU 设备 |
| `device.makeCommandQueue()` | 01~05 | 创建命令队列 |
| `device.makeTexture(descriptor:)` | 01~05 | 创建纹理 |
| `texture.replace(region:...)` | 01~02 | 同步上传纹理数据 |
| `device.makeBuffer(length:options:)` | 03~04 | 创建 MTLBuffer |
| `.storageModeShared` | 01,02,04 | CPU/GPU 可见（UMA 零拷贝） |
| `.storageModePrivate` | 03 | GPU 独享（性能最佳） |
| `commandBuffer.makeBlitCommandEncoder()` | 03~04 | 创建 Blit 编码器 |
| `blit.copy(from:...to:...)` | 03~04 | 异步 GPU 端拷贝 |
| `DispatchSemaphore(value: 3)` | 04 | 限制在途帧数 |
| `commandBuffer.addCompletedHandler` | 04 | GPU 完成回调 |
| `CVMetalTextureCacheCreate` | 05 | 创建纹理缓存 |
| `CVMetalTextureCacheCreateTextureFromImage` | 05 | IOSurface→MTLTexture 零拷贝 |
| `.r8Unorm` / `.rg8Unorm` | 05 | 单/双通道纹理格式 |

### 关键 Metal 概念速查表

| 概念 | 说明 |
|------|------|
| **MTLDevice** | GPU 设备的抽象，资源工厂 |
| **MTLCommandQueue** | 命令提交队列 |
| **MTLCommandBuffer** | 一批命令的容器 |
| **MTLRenderCommandEncoder** | 记录渲染命令 |
| **MTLBlitCommandEncoder** | 记录拷贝命令 |
| **MTLRenderPipelineState (PSO)** | 不可变的完整管线状态对象 |
| **CAMetalLayer** | 用于呈现渲染结果的 Core Animation layer |
| **MTLDrawable** | 可显示的纹理，`present` 后送 Core Animation |
| **UMA** (Unified Memory Architecture) | Apple Silicon 的 CPU/GPU 统一内存 |
| **TBDR** (Tile-Based Deferred Rendering) | Apple GPU 架构 |
| **IOSurface** | 跨进程/GPU 共享的内核内存对象 |
| **CVPixelBuffer** | IOSurface 的视频封装 |
| **NV12** | 双平面 YUV 格式 (Y + CbCr 交织) |

---

## 附录

### 源文件清单（假设的项目结构）

| 文件 | 作用 |
|------|------|
| `Common/MetalRenderer.swift` | Metal 设备、队列、CAMetalLayer 管理 |
| `Common/ShaderTypes.h` | 共享的 struct 定义（Swift ↔ MSL） |
| `Common/VideoDecoder.swift` | VideoToolbox 硬解封装 |
| `01_basic_texture/Renderer.swift` | 示例01：每帧新建纹理 |
| `02_replace_region/Renderer.swift` | 示例02：复用纹理 replaceRegion |
| `03_blit_upload/Renderer.swift` | 示例03：Blit 异步上传 |
| `04_triple_buffer/Renderer.swift` | 示例04：三缓冲 + Semaphore |
| `05_cvmetal_yuv/Renderer.swift` | 示例05：CVMetalTextureCache + NV12 |
| `Shaders/basic.metal` | 顶点函数 + BGRA 片段函数 |
| `Shaders/yuv_nv12.metal` | YUV→RGB 片段函数 |

### 推荐阅读顺序

1. 先通读第一部分，理解 Metal 显式命令模型与 OpenGL 立即模式的差异
2. 运行示例 01，观察 Apple Silicon 上的基础帧率
3. 依次阅读并运行 02~04，感受多缓冲带来的 CPU/GPU 并行度提升
4. 深入示例 05，理解 IOSurface + CVMetalTextureCache 的零拷贝设计
5. 结合 Xcode Instruments 的 "Metal System Trace"，实际测量各方案性能差异

### 调试工具

| 工具 | 用途 |
|------|------|
| Xcode Frame Capture | 逐帧分析 GPU 命令、Shader、资源绑定 |
| Instruments - Metal System Trace | CPU/GPU 时间线、瓶颈分析 |
| Instruments - Metal Application | Shader 热点、内存分配 |
| GPU Frame Debugger | Shader 单步调试 |

### 参考资料

- [Metal Programming Guide](https://developer.apple.com/library/archive/documentation/Miscellaneous/Conceptual/MetalProgrammingGuide/)
- [Metal Best Practices Guide](https://developer.apple.com/library/archive/documentation/3DDrawing/Conceptual/MTLBestPracticesGuide/)
- [Metal Shading Language Specification](https://developer.apple.com/metal/Metal-Shading-Language-Specification.pdf)
- WWDC Sessions: "Modern Rendering with Metal", "Optimize Metal apps and games with GPU counters"
- [Apple Sample Code - Using Metal to Draw a View's Contents](https://developer.apple.com/documentation/metal/using_metal_to_draw_a_view_s_contents)
