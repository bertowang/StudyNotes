# GPU 渲染与图形学入门 —— 初学者版

> **作者**：汪亮 bertonwang  📧 47608843@qq.com
>
> **目标读者**：会一点编程（C/C++、Python、JS 任一即可），但**没接触过图形学/GPU 编程**，想搞清楚 OpenGL / Vulkan / Metal / DirectX 这些"图形 API"到底是什么、它们之间什么关系、以及最快的入门路径在哪里。
>
> **本文风格**：先讲"是什么 / 为什么"，再讲"怎么学"，最后给出**学习路线图 + 精选资料 + 避坑指南**，让你不走弯路、不被名词淹没。

---

## 目录

**第一部分：建立全局认知（先看这部分，再选具体方向）**

- [0. 一句话先说清楚](#0-一句话先说清楚)
- [1. 为什么需要 GPU 和图形 API？](#1-为什么需要-gpu-和图形-api)
- [2. 一张图看懂渲染管线（Rendering Pipeline）](#2-一张图看懂渲染管线rendering-pipeline)
- [3. 图形学 vs GPU 编程 vs 游戏引擎，三者什么关系？](#3-图形学-vs-gpu-编程-vs-游戏引擎三者什么关系)

**第二部分：四大图形 API 横向对比**

- [4. OpenGL / Vulkan / Metal / DirectX：选哪个入门？](#4-opengl--vulkan--metal--directx选哪个入门)
- [5. 现代 API（Vulkan / Metal / DX12）和老 API（OpenGL）的本质差别](#5-现代-api-vulkan--metal--dx12-和老-api-opengl-的本质差别)
- [6. 着色器语言（GLSL / HLSL / MSL / SPIR-V）速览](#6-着色器语言glsl--hlsl--msl--spir-v速览)

**第三部分：学习路线（强烈推荐按这个顺序）**

- [7. 总路线图：从零到能写出像样画面的 4 个阶段](#7-总路线图从零到能写出像样画面的-4-个阶段)
- [8. 阶段一：图形学基础（虎书 + LearnOpenGL）](#8-阶段一图形学基础虎书--learnopengl)
- [9. 阶段二：现代渲染 API（Vulkan / Metal 二选一）](#9-阶段二现代渲染-apivulkan--metal-二选一)
- [10. 阶段三：进阶主题（PBR / 实时光追 / 计算着色器）](#10-阶段三进阶主题pbr--实时光追--计算着色器)
- [11. 阶段四：游戏引擎与项目实战](#11-阶段四游戏引擎与项目实战)

**第四部分：精选资料清单**

- [12. 书籍推荐（按阶段分类）](#12-书籍推荐按阶段分类)
- [13. 在线教程与课程](#13-在线教程与课程)
- [14. 视频与公开课](#14-视频与公开课)
- [15. 工具链速查（编辑器 / 调试器 / 数学库）](#15-工具链速查编辑器--调试器--数学库)

**第五部分：避坑与速查**

- [16. 初学者最容易踩的 8 个坑](#16-初学者最容易踩的-8-个坑)
- [17. 名词速查表（中英对照）](#17-名词速查表中英对照)
- [18. 一句话总结：怎样最快入门？](#18-一句话总结怎样最快入门)

---

## 0. 一句话先说清楚

> **GPU 渲染 = 用显卡（GPU）把"3D 模型 + 材质 + 光照"变成屏幕上看到的"2D 图像"的过程**。
>
> 而 **OpenGL / Vulkan / Metal / DirectX 就是程序员"指挥 GPU 干活"的 4 种语言**——它们不是不同的算法，而是**同一件事的 4 种 API（接口）**。

学图形学，本质上就是学：

```text
1) 数学（向量、矩阵、空间变换）
2) 渲染原理（管线、着色器、光照模型）
3) 一种图形 API（OpenGL / Vulkan / Metal / DirectX）
4) 着色器语言（GLSL / HLSL / MSL）
```

这 4 块缺一不可，但**入门顺序很重要**——这也是本文要解决的核心问题。

---

## 1. 为什么需要 GPU 和图形 API？

### 1.1 CPU 和 GPU 的根本区别

| 维度 | CPU | GPU |
|---|---|---|
| 核心数 | 几个~几十个（强壮） | **几千个**（弱小但人多） |
| 擅长 | 复杂逻辑、串行任务 | **大规模并行计算** |
| 类比 | 几个博士生 | 一万个小学生齐刷刷做加法 |

渲染一帧 1080P 的画面 = 处理 **207 万个像素**，每个像素要算颜色、光照、阴影……这种"重复劳动"恰好是 GPU 的强项。

### 1.2 为什么不直接写 GPU 汇编，要用图形 API？

GPU 厂商有 NVIDIA、AMD、Intel、Apple、高通……**每家硬件不一样**。如果直接对硬件编程：

```text
代码 → NVIDIA → 跑得起来
     ↘ AMD     → 跑不了 ❌
     ↘ Apple   → 跑不了 ❌
```

图形 API 就是中间的"翻译层"：

```text
你的代码 → 图形 API → 显卡驱动 → 各家 GPU
       (OpenGL/Vulkan等)
```

> 💡 **类比**：图形 API 就像 USB 接口——**你不用关心鼠标内部怎么造的，插上 USB 就能用**。

---

## 2. 一张图看懂渲染管线（Rendering Pipeline）

> **渲染管线 = GPU 把 3D 模型变成 2D 像素的"流水线工序"。**

```text
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐
│ 顶点数据 │→│ 顶点着色器│→│ 图元装配 │→│ 光栅化   │→│ 片段着色器│→│ 输出 │
│ (3D点)  │  │ Vertex   │  │ Primitive│  │ Raster   │  │ Fragment │  │ 像素 │
│         │  │ Shader   │  │ Assembly │  │          │  │ Shader   │  │      │
└─────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────┘
   你给的     "把 3D 点    "把点连成    "决定哪些     "给每个像素   屏幕上
   一堆       变换到屏幕    三角形"      像素被三角     算颜色"      看到
   三角形      位置"                     形覆盖"
```

### 2.1 每一步在干什么（用大白话）

| 阶段 | 干什么 | 你能控制吗 |
|---|---|---|
| **Vertex Shader（顶点着色器）** | 把 3D 模型的每个顶点从"模型坐标"变换到"屏幕坐标" | ✅ 你写代码 |
| **图元装配** | 把顶点连成三角形 | ❌ 硬件做 |
| **光栅化** | 把三角形"切片"成一个个像素 | ❌ 硬件做 |
| **Fragment Shader（片段着色器）** | 给每个像素算最终颜色（贴图、光照、阴影） | ✅ 你写代码 |
| **输出合并** | 深度测试、混合，把最终颜色写入屏幕 | 部分可控 |

> 💡 **关键认知**：你写图形程序，**90% 的时间在写两个着色器**（Vertex + Fragment）。学图形学的核心，就是学这两个着色器怎么写。

### 2.2 现代管线的额外阶段（了解即可）

- **几何着色器 / 曲面细分着色器**：可以动态生成或细分三角形
- **计算着色器 (Compute Shader)**：用 GPU 干**通用计算**（不一定是渲染），比如物理模拟、AI 推理
- **光线追踪着色器**：RTX 显卡支持，用于实时光追

---

## 3. 图形学 vs GPU 编程 vs 游戏引擎，三者什么关系？

很多新人会被这三个词搞混，其实它们是**层层递进**的关系：

```text
┌─────────────────────────────────────────────┐
│  ③ 游戏引擎（Unity / Unreal / Godot）      │  ← 应用层：开发完整游戏
│     封装了渲染、物理、音效、UI、脚本…       │
├─────────────────────────────────────────────┤
│  ② GPU 编程 / 图形 API（OpenGL / Vulkan…） │  ← 接口层：直接指挥 GPU
│     学会"怎么调 GPU 画一个三角形"           │
├─────────────────────────────────────────────┤
│  ① 计算机图形学（数学 + 渲染原理）          │  ← 理论层：底层数学和算法
│     向量/矩阵、光照模型、空间变换…           │
└─────────────────────────────────────────────┘
```

| 你的目标 | 该重点学哪一层 |
|---|---|
| 想做独立游戏 / 商业游戏 | **③ 游戏引擎**（Unity / Unreal）+ ① 基础 |
| 想做引擎开发 / 渲染器 | **① + ②**（图形学 + 图形 API） |
| 想做技术美术（TA） | **① + ② + ③**（着色器 + 引擎） |
| 想做 GPGPU / AI / 科学计算 | ② 中的 **CUDA / Compute Shader** |

> 💡 **本文聚焦的是 ① + ②**——也就是"真正理解 GPU 怎么画图"，这是绕不过去的硬功夫。

---

## 4. OpenGL / Vulkan / Metal / DirectX：选哪个入门？

### 4.1 四大 API 一览

| API | 厂商 | 平台 | 风格 | 学习曲线 |
|---|---|---|---|---|
| **OpenGL** | Khronos（开放） | Win / Linux / macOS（已弃） / Android | 老式、简单 | ⭐⭐ 最低 |
| **Vulkan** | Khronos（开放） | Win / Linux / Android（macOS 通过 MoltenVK） | 现代、底层 | ⭐⭐⭐⭐⭐ 极高 |
| **Metal** | Apple | macOS / iOS | 现代、相对友好 | ⭐⭐⭐ 中等 |
| **DirectX 11** | Microsoft | Windows / Xbox | 中等 | ⭐⭐⭐ 中等 |
| **DirectX 12** | Microsoft | Windows / Xbox | 现代、底层 | ⭐⭐⭐⭐⭐ 极高 |
| **WebGL / WebGPU** | Khronos / W3C | 浏览器 | OpenGL/现代 子集 | ⭐⭐ ~ ⭐⭐⭐⭐ |

### 4.2 入门强烈推荐：OpenGL（理由）

虽然 OpenGL 已经被 Apple 抛弃、被 Khronos 标记为"维护模式"，但它仍然是**最佳入门选择**，原因：

1. **教程最多最全**：LearnOpenGL、闫令琪 GAMES101 等顶级资源都用它
2. **API 简单直观**：几十行代码就能画出三角形（Vulkan 要 1000+ 行）
3. **跨平台兼容好**：Windows / Linux / macOS（10.x）都能跑
4. **思想是通用的**：学会 OpenGL 后，转 Vulkan / Metal / DX12 主要是学"工程封装"

### 4.3 不同目标的最优选择

| 你的目标 / 平台 | 推荐入门 API |
|---|---|
| **零基础、就是想学图形学** | ✅ **OpenGL**（无脑选） |
| 只用 macOS / iOS 开发 | OpenGL → **Metal** |
| Windows 游戏 / 引擎开发 | OpenGL → **DirectX 11 → DirectX 12** |
| 跨平台、追求性能极致 | OpenGL → **Vulkan** |
| Web 前端 / 网页 3D | **WebGL** → WebGPU |
| Android 移动端 | OpenGL ES → Vulkan |

> ⚠️ **新手最大的坑**：**直接上 Vulkan/DX12**。这俩是给"已经会图形学的人"用的工业级 API，1000 行代码才能画一个三角形，会让你怀疑人生。**先 OpenGL，后现代 API**，这是几乎所有过来人的共识。

---

## 5. 现代 API（Vulkan / Metal / DX12）和老 API（OpenGL）的本质差别

| 维度 | OpenGL（老） | Vulkan / Metal / DX12（现代） |
|---|---|---|
| **状态管理** | 全局状态机（容易出 bug） | 显式对象、无全局状态 |
| **多线程** | 几乎不支持 | **原生多线程**记录命令 |
| **驱动开销** | 驱动帮你干很多事（也容易黑盒） | **驱动只做最少事**，性能可控 |
| **错误检查** | 运行时自动检查 | 默认不检查（用 Validation Layer 调试） |
| **代码量** | 画三角形 ~50 行 | 画三角形 ~1000 行 |
| **心智负担** | 低 | **极高**（你要管内存、同步、屏障…） |

### 5.1 一句话总结现代 API 的哲学

> **OpenGL：你告诉 GPU "画个三角形"，剩下交给驱动。**
> **Vulkan：你告诉 GPU "在这块显存的这个位置、用这个着色器、按这个顺序、和这个队列同步、然后画三角形"。**

性能确实暴涨，但代价是**复杂度暴涨**。所以：**先用 OpenGL 理解原理，再用现代 API 追求性能**。

---

## 6. 着色器语言（GLSL / HLSL / MSL / SPIR-V）速览

着色器就是"在 GPU 上跑的小程序"，每种 API 配一套语法略有不同的语言：

| 语言 | 配套 API | 风格 | 备注 |
|---|---|---|---|
| **GLSL** | OpenGL / Vulkan | 类 C | 入门最常见 |
| **HLSL** | DirectX / Vulkan | 类 C | 微软系，工业界常用 |
| **MSL** | Metal | 类 C++ | Apple 平台 |
| **SPIR-V** | Vulkan 内部 | **二进制中间码** | 由 GLSL/HLSL 编译来 |
| **WGSL** | WebGPU | 新设计的现代语法 | Web 平台 |

> 💡 **重要事实**：四种语言**长得都很像**（都是类 C），核心概念一致（vertex/fragment、uniform、texture）。**学会一种，其他迁移成本极低**。

### 6.1 一段最简单的 GLSL 片段着色器

```glsl
#version 330 core
out vec4 FragColor;        // 输出：这个像素的颜色

uniform vec3 lightColor;   // 输入：光的颜色（CPU 传进来）
in vec3 vertexColor;       // 输入：顶点着色器传过来的颜色

void main() {
    FragColor = vec4(vertexColor * lightColor, 1.0);  // 颜色相乘 + alpha=1
}
```

读懂这种代码，你就摸到了图形学的门。

---

## 7. 总路线图：从零到能写出像样画面的 4 个阶段

```text
┌────────────────────────────────────────────────────────────┐
│ 阶段 1：图形学基础（2~3 个月）                              │
│  虎书 + GAMES101 + LearnOpenGL（前 4 章）                   │
│  目标：理解管线、变换矩阵、光照模型、纹理映射                 │
└──────────────────────────┬─────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────┐
│ 阶段 2：现代渲染 API（2~4 个月）                            │
│  从 OpenGL 进阶到 Vulkan / Metal / DX12 任选一              │
│  目标：理解显式同步、命令缓冲、描述符、渲染图               │
└──────────────────────────┬─────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────┐
│ 阶段 3：进阶主题（持续）                                    │
│  PBR / IBL / 阴影 / 后处理 / 实时光追 / 计算着色器          │
│  目标：能写出现代游戏级别的画面                              │
└──────────────────────────┬─────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────┐
│ 阶段 4：项目实战 / 引擎研究                                 │
│  做一个小渲染器，或读 Unreal / Filament / bgfx 源码         │
└────────────────────────────────────────────────────────────┘
```

下面逐阶段展开。

---

## 8. 阶段一：图形学基础（虎书 + LearnOpenGL）

这是**最重要的阶段**——基础打不牢，后面学什么都吃力。

### 8.1 双主线推荐：理论 + 实践 并行

```text
┌──────────────────────┐    ┌──────────────────────┐
│  理论主线：虎书       │    │  实践主线：LearnOpenGL│
│  + GAMES101 视频     │    │   写代码画三角形      │
│  （讲为什么）         │    │   （讲怎么做）        │
└──────────┬───────────┘    └───────────┬──────────┘
           └─────────────┬───────────────┘
                         ▼
                    每周交替学
```

### 8.2 主推资源

#### ① **虎书**：《Fundamentals of Computer Graphics》（计算机图形学基础）

- **作者**：Steve Marschner、Peter Shirley（封面有只老虎，所以叫"虎书"）
- **地位**：全球公认的图形学入门圣经，CMU/MIT/Stanford 都用它
- **中文版 GitHub**（你提到的）：<https://github.com/NWPU66/Fundamentals-Of-Computer-Graphics-5th-CN>
- **优点**：覆盖全（从数学到光追）、章节短小、有插图
- **缺点**：偏理论，需要配合代码实践

> 📖 **建议章节**：前 8 章（数学基础、光栅化、变换、可视性、着色），其余按需读。

#### ② **GAMES101**：闫令琪老师的现代计算机图形学课

- **传送门**：<https://sites.cs.ucsb.edu/~lingqi/teaching/games101.html>
- **B 站官方**：搜"GAMES101"即可
- **特点**：**国内最强、最易懂的图形学入门视频课**，中文讲解
- **作业**：8 次代码作业（C++），从画线段到光线追踪

> 💡 **强烈建议**：虎书 + GAMES101 **完全互补**——虎书是教材，GAMES101 是配套讲解。

#### ③ **LearnOpenGL** ⭐⭐⭐⭐⭐

- **网址**：<https://learnopengl.com/>
- **中文版**：<https://learnopengl-cn.github.io/>
- **地位**：**全网最优秀的 OpenGL 入门教程**，没有之一
- **路径**：从画第一个三角形 → 摄像机 → 光照 → 模型加载 → 高级 OpenGL → PBR → 实时光追
- **预计学习时间**：每天 2 小时，约 2~3 个月学完前 4 章核心内容

### 8.3 阶段一推荐节奏（约 12 周）

| 周次 | 虎书章节 | LearnOpenGL 章节 | 产出 |
|---|---|---|---|
| 1~2 | 第 2~5 章：数学基础、光栅化 | 入门：环境搭建、画三角形 | 屏幕上画一个彩色三角形 |
| 3~4 | 第 6~7 章：变换、视图 | 着色器、纹理、变换 | 一个旋转的贴图立方体 |
| 5~6 | 第 8 章：着色 | 摄像机、颜色、光照 | 自由移动的摄像机 + 光照 |
| 7~8 | 第 11 章：纹理映射 | 投光物、多光源 | 多光源场景 |
| 9~10 | 第 9~10 章：可见性 | 模型加载、深度测试、模板测试 | 加载一个 3D 模型 |
| 11~12 | 综合 | 立方体贴图、几何着色器 | 一个有天空盒的小场景 |

---

## 9. 阶段二：现代渲染 API（Vulkan / Metal 二选一）

**前提**：阶段一已经完成，能用 OpenGL 写出基本场景。

### 9.1 选哪个？看平台和目标

| 你的情况 | 推荐 |
|---|---|
| Windows + 想做跨平台 / 引擎 | **Vulkan** |
| macOS / iOS 用户 | **Metal**（更友好） |
| Windows + 主做游戏 | **DirectX 12** |
| 浏览器 / 跨端轻量 | **WebGPU** |

### 9.2 Vulkan 推荐路径

1. **官方教程**：<https://vulkan-tutorial.com/> ⭐
   - 中文版：<https://github.com/fangcun010/VulkanTutorialCN>
   - **从零画三角形到加载模型，约 1000 行代码**
2. **进阶**：Sascha Willems 的 [Vulkan Samples](https://github.com/SaschaWillems/Vulkan)（200+ 实战例子）
3. **书籍**：《Vulkan Programming Guide》/《Learning Vulkan》

### 9.3 Metal 推荐路径

1. **Apple 官方文档**：<https://developer.apple.com/metal/>
2. **教程**：Ray Wenderlich 的 *Metal by Tutorials*（中文社区有翻译）
3. **特点**：API 比 Vulkan 友好得多，**Apple 平台首选**

### 9.4 DirectX 12 推荐路径

1. **微软官方教程**：DirectX-Graphics-Samples GitHub
2. **书籍**：《DirectX 12 3D 游戏开发实战》（Frank Luna，俗称 *龙书*）⭐
3. **特点**：Windows / Xbox 游戏开发标配

### 9.5 WebGPU（新生力量，值得关注）

- **传送门**：<https://www.w3.org/TR/webgpu/>
- **教程**：<https://webgpufundamentals.org/>
- **特点**：浏览器原生支持现代 GPU，**未来 Web 3D 的标准**，比 WebGL 强大得多

---

## 10. 阶段三：进阶主题（PBR / 实时光追 / 计算着色器）

进阶后，每个方向都可以独立深耕：

| 主题 | 解决什么问题 | 推荐资源 |
|---|---|---|
| **PBR（基于物理的渲染）** | 让画面接近现实 | LearnOpenGL PBR 章节、《Real-Time Rendering》第 9 章 |
| **IBL（基于图像的光照）** | 真实反射、环境光 | LearnOpenGL IBL 章节 |
| **阴影（Shadow Mapping / VSM / CSM）** | 软硬阴影 | LearnOpenGL 高级章节 |
| **后处理（Bloom / SSAO / TAA）** | HDR、抗锯齿、辉光 | LearnOpenGL + GPU Gems |
| **延迟渲染 / Forward+** | 大量光源场景优化 | 《Real-Time Rendering》第 20 章 |
| **实时光追（RTX）** | 物理级真实反射/折射/阴影 | NVIDIA RT Gems、Vulkan Ray Tracing 教程 |
| **计算着色器 (Compute)** | 用 GPU 干通用计算 | LearnOpenGL Compute、《GPU Pro/Zen》系列 |
| **CUDA**（非渲染但同源） | GPGPU、AI 加速 | NVIDIA CUDA 官方文档 |

### 10.1 神书推荐

📖 **《Real-Time Rendering, 4th》**（实时渲染，俗称"RTR"）

- 作者：Tomas Akenine-Möller 等
- 地位：**实时渲染领域的百科全书**
- 适合：阶段一完成后随时查阅，不用从头看到尾
- 网站：<https://www.realtimerendering.com/>

📖 **《Physically Based Rendering: From Theory to Implementation》**（PBR 圣经）

- 网站：<https://pbrt.org/>（**全书免费在线**）
- 适合：想深入做离线渲染 / 路径追踪

---

## 11. 阶段四：游戏引擎与项目实战

### 11.1 推荐项目（由易到难）

| 难度 | 项目 | 学到什么 |
|---|---|---|
| ⭐ | 软光栅渲染器（CPU 实现） | 透彻理解管线 |
| ⭐⭐ | OpenGL 小型场景查看器 | 模型加载、相机、光照 |
| ⭐⭐⭐ | PBR + IBL 渲染器 | 现代渲染流程 |
| ⭐⭐⭐⭐ | Vulkan 多线程渲染器 | 现代 API 的工程化 |
| ⭐⭐⭐⭐⭐ | 自制小型游戏引擎 | 全栈能力 |

### 11.2 优秀开源引擎/渲染器（值得读源码）

| 项目 | 特点 | GitHub |
|---|---|---|
| **bgfx** | 跨平台渲染抽象层，**初学者神器** | bkaradzic/bgfx |
| **Filament** | Google 开源 PBR 引擎，工程极佳 | google/filament |
| **Godot** | 完整开源游戏引擎，C++ | godotengine/godot |
| **Piccolo** | **GAMES104 配套教学引擎** | BoomingTech/Piccolo |
| **Mesa** | 开源 OpenGL/Vulkan 驱动 | 适合超进阶 |

### 11.3 GAMES104：现代游戏引擎入门

- **传送门**：<https://games104.boomingtech.com/>
- **B 站**：搜"GAMES104"
- **特点**：闫令琪+王希团队出品，**国内最完整的游戏引擎中文公开课**
- **配套引擎**：Piccolo（开源，可读源码）

---

## 12. 书籍推荐（按阶段分类）

### 12.1 入门必读 ⭐⭐⭐⭐⭐

| 书名 | 中文别名 | 用途 |
|---|---|---|
| *Fundamentals of Computer Graphics* | **虎书** | 图形学入门圣经 |
| *Real-Time Rendering, 4th* | **RTR** | 实时渲染百科全书 |
| *Computer Graphics: Principles and Practice* | **大黑书** | 偏理论的厚教材，按需查阅 |

### 12.2 OpenGL 实战

| 书名 | 备注 |
|---|---|
| *OpenGL Programming Guide*（红宝书） | 官方权威，工具书 |
| *OpenGL Superbible*（蓝宝书） | 实战例子多 |
| *OpenGL 4 Shading Language Cookbook* | 着色器配方手册 |

### 12.3 DirectX

| 书名 | 备注 |
|---|---|
| 《DirectX 12 3D 游戏开发实战》（**龙书**） | Frank Luna 著，**DX 入门首选** |
| *Introduction to 3D Game Programming with DirectX 11* | 同作者 DX11 版 |

### 12.4 Vulkan

| 书名 | 备注 |
|---|---|
| *Vulkan Programming Guide*（**官方指南**） | Khronos 出品 |
| *Learning Vulkan* | 实战导向 |

### 12.5 进阶 / 离线渲染

| 书名 | 备注 |
|---|---|
| *Physically Based Rendering*（**PBRT**） | **PBR 圣经，免费在线** |
| *Ray Tracing in One Weekend* 三部曲 | **几小时入门光追**，免费 |
| *GPU Gems* 1/2/3 | NVIDIA 出品，免费在线，**经典案例集** |
| *GPU Pro / GPU Zen* 系列 | 业界一线工程师文集 |

### 12.6 数学基础（图形学的硬基础）

| 书名 | 备注 |
|---|---|
| *Mathematics for 3D Game Programming and Computer Graphics* | 实用 |
| 《3D 数学基础：图形与游戏开发》 | 中文，入门友好 |
| *Linear Algebra Done Right* | 线代深化 |

---

## 13. 在线教程与课程

| 资源 | 链接 | 评价 |
|---|---|---|
| **LearnOpenGL** ⭐⭐⭐⭐⭐ | learnopengl.com / learnopengl-cn.github.io | OpenGL 入门顶级 |
| **GAMES101** ⭐⭐⭐⭐⭐ | sites.cs.ucsb.edu/~lingqi/teaching/games101.html | 中文图形学最佳 |
| **GAMES104** ⭐⭐⭐⭐⭐ | games104.boomingtech.com | 中文游戏引擎最佳 |
| **GAMES202** ⭐⭐⭐⭐ | sites.cs.ucsb.edu/~lingqi/teaching/games202.html | 高质量实时渲染 |
| **Scratchapixel** | scratchapixel.com | 偏离线渲染原理 |
| **Vulkan Tutorial** | vulkan-tutorial.com | Vulkan 入门首选 |
| **WebGPU Fundamentals** | webgpufundamentals.org | WebGPU 入门 |
| **The Cherno（YouTube）** | youtube.com/@TheCherno | 实战 vlog 风格 |
| **Inigo Quilez** | iquilezles.org | 着色器艺术大神博客 |
| **ShaderToy** | shadertoy.com | **片段着色器在线写画**，灵感无穷 |

---

## 14. 视频与公开课

| 课程 | 平台 | 适合 |
|---|---|---|
| **GAMES101 现代计算机图形学** | B 站 | 入门首选（中文） |
| **GAMES104 现代游戏引擎** | B 站 | 引擎方向（中文） |
| **GAMES202 高质量实时渲染** | B 站 | 进阶（中文） |
| **MIT 6.837 Computer Graphics** | OCW | 经典（英文） |
| **CMU 15-462 Computer Graphics** | YouTube | 一流名校（英文） |
| **The Cherno – Game Engine Series** | YouTube | 边写边学（英文） |
| **闫令琪 Disney/Pixar 渲染分享** | B 站 | 工业界视角 |

---

## 15. 工具链速查（编辑器 / 调试器 / 数学库）

### 15.1 开发环境

| 工具 | 用途 |
|---|---|
| **Visual Studio** (Win) / **Xcode** (Mac) / **CLion** | C++ IDE |
| **CMake** | 跨平台构建系统（**必学**） |
| **vcpkg** / **Conan** | C++ 包管理 |

### 15.2 GPU 调试器（神器，能看到每帧每个 draw call）

| 工具 | 适用 API |
|---|---|
| **RenderDoc** ⭐ | OpenGL / Vulkan / DX11 / DX12 |
| **NVIDIA Nsight** | NVIDIA 卡专用，性能分析顶级 |
| **Xcode GPU Frame Capture** | Metal |
| **PIX** | DirectX |

### 15.3 常用数学库

| 库 | 语言 | 备注 |
|---|---|---|
| **GLM** | C++ | 模仿 GLSL 语法，**OpenGL 标配** |
| **Eigen** | C++ | 通用线代库 |
| **DirectXMath** | C++ | DX 配套 |
| **simd** | Apple | Metal 配套 |

### 15.4 常用辅助库

| 库 | 用途 |
|---|---|
| **GLFW** / **SDL2** | 创建窗口、处理键鼠 |
| **GLAD** / **GLEW** | 加载 OpenGL 函数指针 |
| **stb_image** | 加载图片（单头文件） |
| **Assimp** | 加载 3D 模型（FBX / OBJ / glTF） |
| **Dear ImGui** | 即时模式 GUI，**调试面板神器** |

---

## 16. 初学者最容易踩的 8 个坑

### 坑 1：**直接上 Vulkan / DX12**

后果：1000 行代码画一个三角形，半路放弃。
**解决**：先 OpenGL，理解管线后再上现代 API。

### 坑 2：**忽略数学基础**

后果：看到矩阵变换就懵，调不出正确的画面。
**解决**：花 1~2 周专门补线代（向量、矩阵、点乘叉乘、变换矩阵）。GAMES101 前 4 节足够。

### 坑 3：**只看不写**

后果：看了一堆教程，让你自己写还是写不出。
**解决**：**LearnOpenGL 每一节代码都自己敲一遍**，不要复制粘贴。

### 坑 4：**坐标系搞不清**

后果：模型出现在屏幕外、被反过来、看不到。
**解决**：把"模型坐标 → 世界坐标 → 视图坐标 → 裁剪坐标 → 屏幕坐标"五个空间记牢，画图理解。

### 坑 5：**Y 轴方向混乱**

后果：贴图上下颠倒，模型上下反着。
**解决**：记住 OpenGL Y 朝上、DirectX/Vulkan 默认 Y 朝下（NDC 不同），加载图片要 flip。

### 坑 6：**显卡驱动不匹配 / 版本问题**

后果：示例代码跑不起来，报奇怪的错。
**解决**：升级显卡驱动；用 RenderDoc 抓帧看到底哪步出错。

### 坑 7：**着色器不会调试**

后果：画面是黑的，不知道为什么。
**解决**：把变量当颜色输出（`FragColor = vec4(uv, 0, 1)` 看 uv 对不对）；上 RenderDoc。

### 坑 8：**追求大而全**

后果：什么都想学，最后什么都没学完。
**解决**：先聚焦"画出一个有光照、有纹理、能转的小场景"这个**具体目标**。

---

## 17. 名词速查表（中英对照）

| 英文 | 中文 | 一句话解释 |
|---|---|---|
| Rendering | 渲染 | 把 3D 变成 2D 像素 |
| Pipeline | 管线 | GPU 的流水线工序 |
| Vertex | 顶点 | 3D 模型的一个点 |
| Fragment / Pixel | 片段 / 像素 | 屏幕上一个小方格 |
| Shader | 着色器 | 跑在 GPU 上的小程序 |
| GLSL / HLSL / MSL | 着色器语言 | 写 shader 的语言 |
| Texture | 纹理 / 贴图 | 贴在模型表面的图 |
| UV | UV 坐标 | 纹理坐标（2D） |
| MVP Matrix | 模型-视图-投影矩阵 | 把 3D 点变到屏幕的 3 个矩阵 |
| NDC | 归一化设备坐标 | [-1,1]³ 标准空间 |
| Rasterization | 光栅化 | 三角形 → 像素 |
| Depth Buffer / Z-Buffer | 深度缓冲 | 记录每个像素深度 |
| Stencil Buffer | 模板缓冲 | 像"遮罩" |
| Frame Buffer | 帧缓冲 | 一帧的画面存储 |
| Mipmap | 多级渐远纹理 | 不同分辨率纹理金字塔 |
| Anti-Aliasing (AA) | 抗锯齿 | 让边缘平滑 |
| MSAA / TAA / FXAA | 抗锯齿算法 | 多种抗锯齿方法 |
| BRDF | 双向反射分布函数 | 光打表面如何反射 |
| PBR | 基于物理的渲染 | 物理正确的光照模型 |
| IBL | 基于图像的光照 | 用 HDR 图当环境光 |
| Deferred Rendering | 延迟渲染 | 先存几何信息再算光照 |
| Forward Rendering | 前向渲染 | 边画边算光照 |
| Ray Tracing | 光线追踪 | 模拟光线物理传播 |
| Path Tracing | 路径追踪 | 蒙特卡洛光追 |
| Compute Shader | 计算着色器 | 用 GPU 算非渲染任务 |
| Draw Call | 绘制调用 | CPU 命令 GPU 画一次 |
| API | 应用编程接口 | 程序员用的"按钮" |

---

## 18. 一句话总结：怎样最快入门？

> **第一步：买虎书 + 看 GAMES101 + 跟着 LearnOpenGL 写代码。**
> **第二步：用 OpenGL 写完一个有光照、贴图、模型的小场景。**
> **第三步：根据自己平台和目标，选 Vulkan / Metal / DX12 中的一个深入。**
> **第四步：选一个进阶主题（PBR / 光追 / 引擎）做一个项目。**

记住三句话：

1. **图形学的本质是数学 + 流水线**——把这两件事吃透，所有 API 都是壳。
2. **永远先用最简单的 API（OpenGL）理解原理**——再去碰 Vulkan / DX12。
3. **代码必须自己敲、画面必须自己调**——光看教程一辈子也学不会。

---

## 附录 A：6 个月入门时间表（参考）

```text
Month 1: 数学基础 + GAMES101 前半 + LearnOpenGL "入门"章节
Month 2: GAMES101 后半 + LearnOpenGL "光照" + "模型加载"
Month 3: LearnOpenGL "高级 OpenGL" + 一个综合 demo
Month 4: 选一个现代 API（Vulkan / Metal / DX12）入门
Month 5: PBR + IBL + 阴影
Month 6: 自制小渲染器 / 阅读 Filament / bgfx 源码
```

## 附录 B：高频问答（FAQ）

**Q1：完全不会 C++ 能学吗？**
A：不建议。C++ 是图形学事实标准语言。先花 2~3 周补 C++ 基础（变量、指针、类、CMake）再来。

**Q2：OpenGL 已经"过时"了，还要学吗？**
A：**完全要学**。它是图形学最佳教学 API，思想完全通用。Vulkan/Metal/DX12 都是它的"工程化升级版"。

**Q3：M 系列 Mac 还能学 OpenGL 吗？**
A：能。Apple 标记"deprecated"但还能用，足够学习。深入做应用建议转 Metal。

**Q4：学 Unity / Unreal 算图形学吗？**
A：算"应用图形学"。如果只用引擎不写 shader，永远摸不到底层；如果写 shader、做技术美术，就触到图形学了。

**Q5：图形学和 AI / 大模型还有关系吗？**
A：有。① 神经渲染（NeRF / 3D Gaussian Splatting）② 神经网络辅助渲染（DLSS / FSR）③ AI 生成 3D 资产。这是 2024~2026 最热的方向之一。

**Q6：要不要学 CUDA？**
A：如果做 GPGPU、AI、科学计算，要学。如果纯做图形渲染，**计算着色器（Compute Shader）就够了**，CUDA 只是 NVIDIA 私有方言。

---

## 参考资料

1. **LearnOpenGL**：<https://learnopengl-cn.github.io/>
2. **虎书中文版**（GitHub 翻译）：<https://github.com/NWPU66/Fundamentals-Of-Computer-Graphics-5th-CN>
3. **GAMES101 现代计算机图形学**：<https://sites.cs.ucsb.edu/~lingqi/teaching/games101.html>
4. **GAMES104 现代游戏引擎**：<https://games104.boomingtech.com/>
5. **GAMES202 高质量实时渲染**：<https://sites.cs.ucsb.edu/~lingqi/teaching/games202.html>
6. **Real-Time Rendering 官网**：<https://www.realtimerendering.com/>
7. **PBRT 官网（全书免费）**：<https://pbrt.org/>
8. **Vulkan Tutorial**：<https://vulkan-tutorial.com/>
9. **WebGPU Fundamentals**：<https://webgpufundamentals.org/>
10. **Khronos Vulkan 文档**：<https://www.khronos.org/vulkan/>
11. **Apple Metal 文档**：<https://developer.apple.com/metal/>
12. **DirectX 官方仓库**：<https://github.com/microsoft/DirectX-Graphics-Samples>
13. **NVIDIA GPU Gems（免费在线）**：<https://developer.nvidia.com/gpugems/>
14. **ShaderToy**：<https://www.shadertoy.com/>
15. **Inigo Quilez 博客**：<https://iquilezles.org/>

---

> 📌 **结语**：图形学是少数几个**学得越深越觉得有趣**的领域——你会从"屏幕怎么显示一个点"，一路推到"光在世界中如何传播"。
>
> 走完这条路，你不仅能写出漂亮的 3D 画面，更能从根本上理解**所有游戏、影视、VR、AI 视觉**背后的原理。
>
> 祝你早日画出第一个让自己惊艳的画面 ✨
