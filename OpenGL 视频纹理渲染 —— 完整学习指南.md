# OpenGL 视频纹理渲染 —— 完整学习指南

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.1 ｜ **最后更新**：2026-07-14

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
> 
> 本文档系统讲解 OpenGL 视频渲染的完整技术栈：从底层渲染管线原理到逐步优化的纹理上传技术。  
> 基于项目中 5 个递进式示例（01~05），覆盖从入门到生产级的全部知识。

---

## 目录

- [第一部分：OpenGL 渲染管线基础](#第一部分opengl-渲染管线基础)
  - [一、整体渲染架构概览](#一整体渲染架构概览)
  - [二、OpenGL 上下文初始化](#二opengl-上下文初始化)
  - [三、几何数据准备 —— 全屏四边形](#三几何数据准备--全屏四边形)
  - [四、纹理系统 —— 视频帧上传到 GPU](#四纹理系统--视频帧上传到-gpu)
  - [五、Shader 着色器详解](#五shader-着色器详解)
  - [六、渲染调用 —— Draw Call 的底层过程](#六渲染调用--draw-call-的底层过程)
  - [七、主循环与双缓冲](#七主循环与双缓冲)
  - [八、完整数据流总结](#八完整数据流总结)
- [第二部分：纹理上传优化技术](#第二部分纹理上传优化技术)
  - [九、优化路线总览](#九优化路线总览)
  - [十、示例 02: 纹理流式更新 (glTexSubImage2D)](#十示例-02-纹理流式更新-gltexsubimage2d)
  - [十一、示例 03: 单 PBO 异步上传](#十一示例-03-单-pbo-异步上传)
  - [十二、示例 04: 双 PBO 乒乓缓冲](#十二示例-04-双-pbo-乒乓缓冲)
  - [十三、示例 05: YUV420P + GPU 色彩空间转换](#十三示例-05-yuv420p--gpu-色彩空间转换)
- [第三部分：综合对比与最佳实践](#第三部分综合对比与最佳实践)
  - [十四、五种方案的底层差异总结](#十四五种方案的底层差异总结)
  - [十五、性能分析与瓶颈](#十五性能分析与瓶颈)
  - [十六、关键 API 速查表](#十六关键-api-速查表)
- [附录](#附录)

---

# 第一部分：OpenGL 渲染管线基础

> 基于示例 `01_basic_texture`，详细讲解 OpenGL 从初始化到画面最终呈现的完整底层逻辑。

---

## 一、整体渲染架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        应用层 (C++ / main.cpp)                    │
│  ┌──────────┐   ┌──────────────┐   ┌──────────────────────┐     │
│  │ FFmpeg   │──▶│ glTexImage2D │──▶│ Draw Call            │     │
│  │ 视频解码  │   │ 纹理上传      │   │ (glDrawElements)     │     │
│  └──────────┘   └──────────────┘   └──────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     OpenGL 渲染管线 (GPU)                         │
│                                                                   │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────┐ │
│  │ 顶点着色器 │──▶│ 图元装配    │──▶│ 光栅化     │──▶│片段着色器│ │
│  │(Vertex     │   │(Primitive  │   │(Rasterize) │   │(Fragment│ │
│  │ Shader)    │   │ Assembly)  │   │            │   │ Shader) │ │
│  └────────────┘   └────────────┘   └────────────┘   └────────┘ │
│                                                          │       │
│                                                          ▼       │
│                                              ┌──────────────┐   │
│                                              │ 帧缓冲输出    │   │
│                                              │ (Framebuffer) │   │
│                                              └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  屏幕显示         │
                    │ (glfwSwapBuffers) │
                    └──────────────────┘
```

---

## 二、OpenGL 上下文初始化

### 2.1 窗口与上下文创建 (`gl_utils.cpp`)

```cpp
// 请求 OpenGL 4.3 Core Profile
glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
```

**底层逻辑：**

1. **GLFW** 负责创建操作系统窗口，并向 GPU 驱动请求一个 OpenGL 4.3 Core 上下文
2. **Core Profile** 意味着不使用已废弃的固定管线功能（如 `glBegin/glEnd`），所有渲染必须通过 Shader 完成
3. **GLAD** (`gladLoadGLLoader`) 在运行时动态加载 GPU 驱动暴露的 OpenGL 函数指针，因为 OpenGL 是规范而非库，函数地址需要运行时查询

### 2.2 关闭垂直同步

```cpp
glfwSwapInterval(0);
```

- 设为 0 表示不等待显示器刷新信号（VSync），GPU 会尽可能快地渲染
- 这样可以测量真实的渲染性能上限，而不是被锁定在 60fps

---

## 三、几何数据准备 —— 全屏四边形

### 3.1 为什么需要四边形？

OpenGL 本身不能直接"显示一张图片"。它只能：
1. 接收几何顶点数据
2. 通过 Shader 处理这些顶点
3. 在光栅化后对每个像素采样纹理

所以我们需要一个**覆盖整个屏幕的四边形**作为"画布"，然后把视频帧作为纹理"贴"上去。

### 3.2 顶点数据结构

```cpp
float vertices[] = {
    // 位置(x,y)    // 纹理坐标(u,v)
    -1.0f,  1.0f,   0.0f, 0.0f,  // 左上
     1.0f,  1.0f,   1.0f, 0.0f,  // 右上
     1.0f, -1.0f,   1.0f, 1.0f,  // 右下
    -1.0f, -1.0f,   0.0f, 1.0f,  // 左下
};

unsigned int indices[] = {
    0, 1, 2,  // 第一个三角形（左上→右上→右下）
    0, 2, 3   // 第二个三角形（左上→右下→左下）
};
```

**坐标系说明：**

```
OpenGL NDC 坐标系          纹理坐标系 (UV)
     Y                         V
     ↑                         ↑
     |                         |
(-1,1)───(1,1)          (0,0)───(1,0)
  |         |              |         |
  |  屏幕   |              |  纹理   |
  |         |              |         |
(-1,-1)──(1,-1)         (0,1)───(1,1)
     ──────→ X                ──────→ U
```

- **NDC (Normalized Device Coordinates)**：OpenGL 的标准化设备坐标，范围 [-1, 1]，覆盖整个视口
- **纹理坐标 (UV)**：范围 [0, 1]，注意 V 轴方向与视频帧的 Y 轴一致（从上到下递增）

### 3.3 VAO / VBO / EBO 的底层含义

```cpp
GLuint VAO, VBO, EBO;
glGenVertexArrays(1, &VAO);  // 顶点数组对象：记录顶点属性配置
glGenBuffers(1, &VBO);        // 顶点缓冲对象：存储顶点数据
glGenBuffers(1, &EBO);        // 索引缓冲对象：存储索引数据
```

**GPU 内存布局：**

```
┌─── VAO（配置描述符，不存数据）────────────────────────┐
│                                                        │
│  属性 0 (位置): VBO offset=0, stride=16, size=2       │
│  属性 1 (纹理): VBO offset=8, stride=16, size=2       │
│  索引缓冲: EBO                                         │
│                                                        │
└────────────────────────────────────────────────────────┘

┌─── VBO（GPU 显存中的顶点数据）──────────────────────────┐
│ [-1.0, 1.0, 0.0, 0.0] [1.0, 1.0, 1.0, 0.0] ...       │
│  ▲▲▲▲▲▲▲▲  ▲▲▲▲▲▲▲▲    ▲▲▲▲▲▲▲▲  ▲▲▲▲▲▲▲▲           │
│  位置 xy    纹理 uv      位置 xy    纹理 uv             │
└────────────────────────────────────────────────────────┘

┌─── EBO（索引数据）─────────┐
│ [0, 1, 2, 0, 2, 3]        │
│  三角形1    三角形2         │
└────────────────────────────┘
```

### 3.4 顶点属性指针配置

```cpp
// 位置属性 (location = 0)
glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void*)0);
glEnableVertexAttribArray(0);

// 纹理坐标属性 (location = 1)
glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void*)(2 * sizeof(float)));
glEnableVertexAttribArray(1);
```

| 参数 | 含义 |
|------|------|
| `0` / `1` | 属性索引，对应 Shader 中的 `layout(location = 0/1)` |
| `2` | 每个属性有 2 个分量 (x,y 或 u,v) |
| `GL_FLOAT` | 数据类型为 32 位浮点 |
| `GL_FALSE` | 不需要归一化 |
| `4 * sizeof(float)` | 步长 = 16 字节（每个顶点占 4 个 float） |
| `(void*)0` / `(void*)(2*sizeof(float))` | 起始偏移量 |

---

## 四、纹理系统 —— 视频帧上传到 GPU

### 4.1 纹理对象创建

```cpp
GLuint texture;
glGenTextures(1, &texture);
glBindTexture(GL_TEXTURE_2D, texture);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
```

**底层逻辑：**

- `glGenTextures`：在 GPU 驱动中分配一个纹理对象句柄（此时还没有分配显存）
- `glBindTexture`：将该纹理绑定到当前上下文的 `GL_TEXTURE_2D` 目标上
- `GL_LINEAR`：双线性插值过滤，当纹理被放大/缩小时，对相邻像素进行线性混合

### 4.2 每帧纹理上传 (glTexImage2D) — 示例 01 的基础方案

```cpp
glBindTexture(GL_TEXTURE_2D, texture);
glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
             vframe.width, vframe.height, 0,
             GL_RGBA, GL_UNSIGNED_BYTE, vframe.data[0]);
```

**参数详解：**

| 参数 | 值 | 含义 |
|------|-----|------|
| target | `GL_TEXTURE_2D` | 2D 纹理目标 |
| level | `0` | Mipmap 层级 0（原始分辨率） |
| internalformat | `GL_RGBA` | GPU 内部存储格式（每像素 4 字节） |
| width/height | 视频宽高 | 纹理尺寸 |
| border | `0` | 必须为 0（历史遗留参数） |
| format | `GL_RGBA` | 输入数据的像素格式 |
| type | `GL_UNSIGNED_BYTE` | 每个通道 8 位无符号整数 |
| data | `vframe.data[0]` | CPU 内存中的像素数据指针 |

**底层发生了什么：**

```
CPU 内存                              GPU 显存
┌──────────────────┐                 ┌──────────────────┐
│ vframe.data[0]   │  ──DMA传输──▶  │ 纹理对象内存      │
│ RGBA像素数据      │  (同步阻塞)    │ (每帧重新分配!)   │
│ W × H × 4 bytes │                 │ W × H × 4 bytes │
└──────────────────┘                 └──────────────────┘
```

⚠️ **性能瓶颈**：`glTexImage2D` 每次调用都会：
1. 在 GPU 端重新分配纹理内存（即使尺寸没变）
2. CPU→GPU 的数据传输是**同步阻塞**的，CPU 必须等待传输完成
3. 对于 1920×1080 RGBA 视频：每帧传输 `1920 × 1080 × 4 = 8.3 MB`

---

## 五、Shader 着色器详解

### 5.1 顶点着色器 (`basic.vert`)

```glsl
#version 430 core

layout (location = 0) in vec2 aPos;       // 输入：顶点位置
layout (location = 1) in vec2 aTexCoord;  // 输入：纹理坐标

out vec2 TexCoord;  // 输出：传递给片段着色器的纹理坐标

void main() {
    gl_Position = vec4(aPos, 0.0, 1.0);   // 设置裁剪空间坐标
    TexCoord = aTexCoord;                   // 直接传递纹理坐标
}
```

**逐行解析：**

| 代码 | 底层含义 |
|------|----------|
| `#version 430 core` | 使用 GLSL 4.30 版本，Core Profile |
| `layout (location = 0) in vec2 aPos` | 从 VAO 属性 0 读取 2 分量浮点向量 |
| `layout (location = 1) in vec2 aTexCoord` | 从 VAO 属性 1 读取纹理坐标 |
| `out vec2 TexCoord` | 声明输出变量，光栅化时会被插值 |
| `gl_Position = vec4(aPos, 0.0, 1.0)` | 输出裁剪坐标 (x, y, z=0, w=1) |
| `TexCoord = aTexCoord` | 将纹理坐标传递到下一阶段 |

**`gl_Position` 的 w 分量：**
- `w = 1.0` 表示不进行透视除法（因为我们是 2D 全屏渲染，不需要透视效果）
- GPU 会自动执行 `NDC = gl_Position.xyz / gl_Position.w`

**为什么不需要 MVP 矩阵？**
- 顶点坐标已经是 NDC 空间 [-1, 1]，直接覆盖整个屏幕
- 不需要模型变换（Model）、视图变换（View）、投影变换（Projection）

### 5.2 片段着色器 (`basic.frag`) — 示例 01~04 使用

```glsl
#version 430 core

in vec2 TexCoord;           // 输入：从顶点着色器插值而来的纹理坐标
out vec4 FragColor;         // 输出：该像素的最终颜色

uniform sampler2D tex;      // 纹理采样器（绑定到纹理单元）

void main() {
    FragColor = texture(tex, TexCoord);  // 从纹理中采样颜色
}
```

**逐行解析：**

| 代码 | 底层含义 |
|------|----------|
| `in vec2 TexCoord` | 接收光栅化后插值的纹理坐标 |
| `out vec4 FragColor` | 输出 RGBA 颜色到帧缓冲 |
| `uniform sampler2D tex` | 纹理采样器，通过 uniform 绑定到纹理单元 |
| `texture(tex, TexCoord)` | 在坐标 (u,v) 处对纹理进行双线性采样 |

**`texture()` 函数的底层操作：**

```
1. 将 TexCoord (0~1) 映射到纹理像素坐标 (0~width, 0~height)
2. 由于使用 GL_LINEAR 过滤，取周围 4 个像素进行双线性插值：

   ┌─────┬─────┐
   │ P00 │ P10 │    最终颜色 = lerp(lerp(P00, P10, fx),
   ├─────┼─────┤                    lerp(P01, P11, fx), fy)
   │ P01 │ P11 │
   └─────┴─────┘
        ↑
     采样点 (fx, fy) 为小数部分
```

### 5.3 Shader 编译与链接流程

```cpp
// 1. 创建着色器对象
GLuint shader = glCreateShader(type);

// 2. 附加源代码
glShaderSource(shader, 1, &source, nullptr);

// 3. 编译（GPU 驱动将 GLSL 编译为 GPU 机器码）
glCompileShader(shader);

// 4. 创建程序对象并链接
programID = glCreateProgram();
glAttachShader(programID, vertexShader);
glAttachShader(programID, fragmentShader);
glLinkProgram(programID);
```

**底层流程：**

```
GLSL 源码 (文本)
       │
       ▼ glCompileShader()
┌──────────────────┐
│ GPU 驱动编译器    │  将 GLSL 编译为中间表示 (IR)
│ (NVIDIA/AMD/Intel)│  或直接编译为 GPU ISA
└──────────────────┘
       │
       ▼ glLinkProgram()
┌──────────────────┐
│ 链接器            │  解析 in/out 变量匹配
│                  │  分配 uniform 位置
│                  │  生成最终可执行程序
└──────────────────┘
       │
       ▼ glUseProgram()
┌──────────────────┐
│ GPU 执行单元      │  加载程序到 GPU 核心执行
└──────────────────┘
```

---

## 六、渲染调用 —— Draw Call 的底层过程

### 6.1 渲染代码

```cpp
glClear(GL_COLOR_BUFFER_BIT);           // 清除帧缓冲
shader.use();                            // 激活 Shader 程序
shader.setInt("tex", 0);                 // 设置 uniform: 纹理单元 0
glActiveTexture(GL_TEXTURE0);            // 激活纹理单元 0
glBindTexture(GL_TEXTURE_2D, texture);   // 绑定纹理到单元 0
glBindVertexArray(quadVAO);              // 绑定 VAO
glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, 0);  // 绘制！
```

### 6.2 `glDrawElements` 触发的 GPU 管线

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GPU 渲染管线执行流程                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ① 输入装配 (Input Assembly)                                         │
│     ├─ 从 EBO 读取索引: [0, 1, 2, 0, 2, 3]                         │
│     ├─ 根据索引从 VBO 获取 4 个顶点数据                              │
│     └─ 组装为 2 个三角形                                             │
│                                                                      │
│  ② 顶点着色器 (Vertex Shader) × 4 次                                │
│     ├─ 输入: aPos + aTexCoord                                       │
│     ├─ 输出: gl_Position + TexCoord                                 │
│     └─ 每个顶点独立并行执行                                          │
│                                                                      │
│  ③ 图元装配 (Primitive Assembly)                                     │
│     └─ 将顶点组装为三角形                                            │
│                                                                      │
│  ④ 光栅化 (Rasterization)                                           │
│     ├─ 确定三角形覆盖哪些像素                                        │
│     ├─ 对每个像素，插值顶点输出 (TexCoord)                           │
│     └─ 生成"片段" (Fragment)                                        │
│                                                                      │
│  ⑤ 片段着色器 (Fragment Shader) × 每个像素                           │
│     ├─ 输入: 插值后的 TexCoord                                       │
│     ├─ 从纹理采样: texture(tex, TexCoord)                           │
│     ├─ 输出: FragColor (RGBA)                                       │
│     └─ 所有像素大规模并行执行 (GPU 有数千个核心)                      │
│                                                                      │
│  ⑥ 输出合并 (Output Merger)                                         │
│     ├─ 深度测试（本例无需，2D渲染）                                   │
│     ├─ 混合（本例无透明度混合）                                       │
│     └─ 写入帧缓冲 (Framebuffer)                                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.3 光栅化插值的数学原理

当光栅化器处理三角形内部的某个像素时，它使用**重心坐标 (Barycentric Coordinates)** 对顶点属性进行插值：

```
设三角形三个顶点为 V0, V1, V2
像素 P 的重心坐标为 (λ0, λ1, λ2)，其中 λ0 + λ1 + λ2 = 1

则该像素的 TexCoord = λ0 * V0.TexCoord + λ1 * V1.TexCoord + λ2 * V2.TexCoord
```

这就是为什么我们只需要在 4 个顶点上指定纹理坐标，GPU 就能自动为每个像素计算出正确的采样位置。

---

## 七、主循环与双缓冲

### 7.1 主循环逻辑 (`mainLoop`)

```cpp
void mainLoop(GLFWwindow* window, std::function<void()> renderFunc) {
    while (!glfwWindowShouldClose(window)) {
        renderFunc();              // 执行渲染（写入后缓冲）
        glfwSwapBuffers(window);   // 交换前后缓冲
        glfwPollEvents();          // 处理输入事件
    }
    glfwDestroyWindow(window);
    glfwTerminate();
}
```

### 7.2 双缓冲机制

```
┌──────────────────────────────────────────────────┐
│                 双缓冲 (Double Buffering)          │
├──────────────────────────────────────────────────┤
│                                                   │
│  ┌─────────────┐        ┌─────────────┐         │
│  │  前缓冲      │        │  后缓冲      │         │
│  │ (Front)     │        │ (Back)      │         │
│  │             │        │             │         │
│  │ 正在显示的   │  swap  │ 正在渲染的   │         │
│  │ 上一帧画面   │◀──────▶│ 当前帧画面   │         │
│  │             │        │             │         │
│  └──────┬──────┘        └──────┬──────┘         │
│         │                      │                 │
│         ▼                      ▼                 │
│     显示器输出             GPU 渲染目标            │
│                                                   │
└──────────────────────────────────────────────────┘
```

- **前缓冲 (Front Buffer)**：当前正在被显示器扫描输出的帧
- **后缓冲 (Back Buffer)**：GPU 正在渲染的目标帧
- `glfwSwapBuffers`：交换两个缓冲的指针，瞬间完成（不复制数据）
- 避免了"撕裂"现象（画面上半部分是旧帧，下半部分是新帧）

---

## 八、完整数据流总结

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          一帧的完整数据流                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. FFmpeg 解码视频帧 → CPU 内存 (RGBA 像素数组)                         │
│                          │                                               │
│  2. glTexImage2D ────────┘                                               │
│     CPU → GPU 同步传输 (PCIe 总线, ~8.3MB/帧@1080p)                      │
│                          │                                               │
│  3. GPU 纹理内存 ────────┘                                               │
│     存储为 2D 纹理对象                                                    │
│                          │                                               │
│  4. glDrawElements ──────┘                                               │
│     触发渲染管线                                                          │
│          │                                                               │
│          ├─▶ 顶点着色器: 4个顶点 → 裁剪坐标 + 纹理坐标                   │
│          ├─▶ 光栅化: 三角形 → 百万个片段 (每个片段有插值的UV)             │
│          ├─▶ 片段着色器: texture(tex, UV) → 每像素颜色                   │
│          └─▶ 写入后缓冲                                                  │
│                          │                                               │
│  5. glfwSwapBuffers ─────┘                                               │
│     交换前后缓冲，画面显示到屏幕                                          │
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
│                        纹理上传优化演进路线                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  01 基础方案          02 流式更新          03 单PBO           04 双PBO       │
│  ┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────┐    │
│  │glTexImage│──────▶│glTexSub  │──────▶│ PBO +    │──────▶│ 双PBO    │    │
│  │2D        │       │Image2D   │       │ DMA异步  │       │ 乒乓缓冲 │    │
│  │每帧重分配│       │复用内存  │       │ CPU不阻塞│       │ 完全并行 │    │
│  └──────────┘       └──────────┘       └──────────┘       └──────────┘    │
│                                                                              │
│                                              05 YUV GPU 渲染                 │
│                                         ┌──────────────────────┐            │
│                                         │ 跳过CPU格式转换       │            │
│                                         │ 上传原始YUV数据       │            │
│                                         │ GPU Shader做色彩转换  │            │
│                                         │ 数据量减少62%         │            │
│                                         └──────────────────────┘            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 性能对比预期 (1080p@60fps)

| 示例 | 每帧上传量 | CPU阻塞 | GPU利用率 | 预期帧时间 |
|------|-----------|---------|-----------|-----------| 
| 01 基础 | 8.3MB (RGBA) | 完全阻塞 | 低 | ~16ms |
| 02 流式 | 8.3MB (RGBA) | 完全阻塞 | 低 | ~14ms |
| 03 单PBO | 8.3MB (RGBA) | 部分并行 | 中 | ~10ms |
| 04 双PBO | 8.3MB (RGBA) | 完全并行 | 高 | ~7ms |
| 05 YUV | 3.1MB (YUV420) | 完全阻塞* | 高 | ~6ms |

> *示例05可与PBO技术组合使用，进一步提升性能

---

## 十、示例 02: 纹理流式更新 (glTexSubImage2D)

### 核心思想

**一句话总结**：预先分配纹理内存，每帧只更新像素数据，不重新分配。

### 与 01 的关键区别

```
01 的做法（每帧）:                    02 的做法:
┌─────────────────────┐              ┌─────────────────────┐
│ glTexImage2D        │              │ 初始化时（仅一次）:    │
│  ├─ 释放旧纹理内存   │              │   glTexImage2D(null) │
│  ├─ 分配新纹理内存   │              │   └─ 分配纹理内存    │
│  └─ 复制像素数据     │              │                      │
│                     │              │ 每帧:                 │
│ 每帧都做这三步！     │              │   glTexSubImage2D    │
│ 内存分配是昂贵操作   │              │   └─ 只更新像素数据   │
└─────────────────────┘              └─────────────────────┘
```

### 关键代码解析

#### 初始化阶段：预分配纹理

```cpp
// 传入 nullptr —— 只分配内存，不填充数据
glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
             video.getWidth(), video.getHeight(), 0,
             GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
```

**底层逻辑**：
- 调用 `glTexImage2D` 并传入 `nullptr`，GPU 驱动会分配一块 `W × H × 4` 字节的显存
- 这块内存在整个程序生命周期内保持不变，不会被释放和重新分配

#### 每帧更新：glTexSubImage2D

```cpp
glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0,
                vframe.width, vframe.height,
                GL_RGBA, GL_UNSIGNED_BYTE, vframe.data[0]);
```

**参数对比**：

| 参数 | glTexImage2D | glTexSubImage2D |
|------|-------------|-----------------| 
| 第3/4参数 | internalformat, width | xoffset, yoffset (更新起始位置) |
| 内存操作 | 重新分配 + 复制 | 仅复制（原地覆盖） |
| border参数 | 有 | 无 |

**底层差异**：

```
glTexImage2D (每帧):                    glTexSubImage2D (每帧):
┌──────────────────────┐               ┌──────────────────────┐
│ 1. glDeleteTexture   │               │ 1. 直接 DMA 传输     │
│    (隐式释放旧内存)   │               │    CPU → 已有GPU内存  │
│ 2. 驱动分配新显存     │               │                      │
│    (可能触发碎片整理)  │               │ 就这一步！            │
│ 3. DMA 传输数据      │               │                      │
│    CPU → 新GPU内存    │               │                      │
└──────────────────────┘               └──────────────────────┘
```

### 性能提升原理

1. **省去内存分配**：GPU 显存分配是昂贵操作，涉及驱动内部的内存管理器
2. **避免内存碎片**：频繁分配/释放会导致 GPU 显存碎片化
3. **驱动优化机会**：驱动知道纹理大小不变，可以做更好的缓存策略

### 局限性

- CPU→GPU 的数据传输仍然是**同步阻塞**的
- CPU 必须等待 `glTexSubImage2D` 完成才能继续执行后续代码
- 传输带宽瓶颈没有解决

---

## 十一、示例 03: 单 PBO 异步上传

### 核心思想

**一句话总结**：引入 PBO 作为中转站，将 CPU→GPU 的数据传输变为异步操作。

### PBO 是什么？

PBO (Pixel Buffer Object) 是一块**由 GPU 驱动管理的缓冲区**，位于 GPU 可直接访问的内存区域（通常是 PCIe BAR 空间或 pinned memory）。

```
没有 PBO 的传输路径:
┌──────┐                              ┌──────┐
│ CPU  │ ─── glTexSubImage2D ────────▶│ GPU  │
│ 内存  │    (同步阻塞，CPU等待)        │ 纹理  │
└──────┘                              └──────┘

有 PBO 的传输路径:
┌──────┐    memcpy     ┌──────┐    DMA (异步)    ┌──────┐
│ CPU  │ ────────────▶ │ PBO  │ ──────────────▶ │ GPU  │
│ 内存  │  (CPU控制)    │ 缓冲  │  (GPU自行完成)   │ 纹理  │
└──────┘               └──────┘                  └──────┘
                    (GPU可访问的内存)
```

### 与 02 的关键区别

| 方面 | 02 (glTexSubImage2D) | 03 (PBO) |
|------|---------------------|-----------| 
| 数据源 | CPU 普通内存指针 | PBO 缓冲区 |
| 传输方式 | 同步（CPU等待完成） | 异步（DMA引擎独立工作） |
| CPU 行为 | 阻塞等待传输完成 | 发起传输后可继续其他工作 |
| 内存类型 | 用户态虚拟内存 | 驱动管理的 pinned memory |

### 关键代码解析

#### 1. PBO 创建

```cpp
GLuint pbo;
glGenBuffers(1, &pbo);
glBindBuffer(GL_PIXEL_UNPACK_BUFFER, pbo);
glBufferData(GL_PIXEL_UNPACK_BUFFER, dataSize, nullptr, GL_STREAM_DRAW);
```

**底层逻辑**：

| API | 底层操作 |
|-----|---------| 
| `glGenBuffers` | 分配缓冲对象句柄 |
| `GL_PIXEL_UNPACK_BUFFER` | 标记为"像素解包"用途（CPU→GPU方向） |
| `GL_STREAM_DRAW` | 提示驱动：数据会被频繁写入，每次写入后只用一次 |

`GL_STREAM_DRAW` 的提示让驱动将 PBO 分配在**对 CPU 写入和 GPU 读取都高效的内存区域**（通常是 write-combined memory）。

#### 2. 映射 PBO 到 CPU 地址空间

```cpp
void* ptr = glMapBufferRange(GL_PIXEL_UNPACK_BUFFER, 0, dataSize,
                             GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT);
memcpy(ptr, vframe.data[0], dataSize);
glUnmapBuffer(GL_PIXEL_UNPACK_BUFFER);
```

**标志位含义**：

| 标志 | 作用 |
|------|------|
| `GL_MAP_WRITE_BIT` | 只需要写权限（不读取旧数据） |
| `GL_MAP_INVALIDATE_BUFFER_BIT` | 告诉驱动：旧数据可以丢弃 |

**`GL_MAP_INVALIDATE_BUFFER_BIT` 的重要性**：

```
没有 INVALIDATE:                      有 INVALIDATE:
┌─────────────────────┐              ┌─────────────────────┐
│ 驱动必须确保旧数据   │              │ 驱动知道旧数据不需要 │
│ 在映射期间仍然有效   │              │ 可以直接给一块新内存 │
│                     │              │                      │
│ 如果 GPU 还在用旧数据│              │ 即使 GPU 还在用旧PBO │
│ CPU 必须等待 GPU 完成│              │ 驱动分配新缓冲，无需等│
│ (产生 pipeline stall)│              │ (称为 buffer orphaning)│
└─────────────────────┘              └─────────────────────┘
```

#### 3. 从 PBO 上传到纹理（异步）

```cpp
glBindBuffer(GL_PIXEL_UNPACK_BUFFER, pbo);  // 绑定 PBO
glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h,
                GL_RGBA, GL_UNSIGNED_BYTE, (void*)0);  // 注意：最后参数是 0！
```

**关键变化**：当 `GL_PIXEL_UNPACK_BUFFER` 被绑定时，`glTexSubImage2D` 的最后一个参数的含义**完全改变**：

| 状态 | 最后一个参数含义 |
|------|-----------------| 
| 无 PBO 绑定 | CPU 内存指针（直接读取） |
| 有 PBO 绑定 | PBO 内的字节偏移量（`0` = 从头开始） |

**底层发生了什么**：

```
┌─────────────────────────────────────────────────────────────┐
│                    PBO 异步上传时序                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  CPU 线程:                                                   │
│  ──[memcpy到PBO]──[发起glTexSubImage2D]──[继续执行其他代码]── │
│                          │                                   │
│                          │ (仅提交命令，不等待)               │
│                          ▼                                   │
│  GPU DMA 引擎:                                               │
│  ─────────────────────[PBO → 纹理 DMA 传输]──[完成]──        │
│                                                              │
│  GPU 渲染引擎:                                               │
│  ──────────────────────────────────[等DMA完成]──[渲染]──     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 性能提升原理

1. **CPU 不阻塞**：`glTexSubImage2D` 只是向 GPU 命令队列提交一个 DMA 传输命令，立即返回
2. **DMA 引擎独立工作**：GPU 有专门的 DMA 引擎（Copy Engine），与渲染引擎并行
3. **Write-Combined Memory**：PBO 使用的内存类型对顺序写入特别高效

### 局限性

- 单 PBO 时，如果 GPU 还在读取 PBO 数据，CPU 的 `glMapBufferRange` 可能仍需等待
- `GL_MAP_INVALIDATE_BUFFER_BIT` 通过 buffer orphaning 缓解了这个问题，但驱动实现不一定完美
- 真正的完全并行需要**双 PBO**

---

## 十二、示例 04: 双 PBO 乒乓缓冲

### 核心思想

**一句话总结**：两个 PBO 交替使用，CPU 写入一个的同时 GPU 从另一个上传，实现完全并行。

### 乒乓缓冲原理

```
┌─────────────────────────────────────────────────────────────────────┐
│                    双 PBO 乒乓缓冲时序图                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  帧 N:                                                               │
│  ┌─────────────────────┐  ┌─────────────────────┐                  │
│  │ CPU 写入 PBO_A      │  │ GPU 从 PBO_B 上传    │  ← 完全并行！    │
│  │ (当前帧数据)         │  │ (上一帧数据→纹理)    │                  │
│  └─────────────────────┘  └─────────────────────┘                  │
│                                                                      │
│  帧 N+1:                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐                  │
│  │ CPU 写入 PBO_B      │  │ GPU 从 PBO_A 上传    │  ← 角色互换！    │
│  │ (当前帧数据)         │  │ (上一帧数据→纹理)    │                  │
│  └─────────────────────┘  └─────────────────────┘                  │
│                                                                      │
│  帧 N+2:                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐                  │
│  │ CPU 写入 PBO_A      │  │ GPU 从 PBO_B 上传    │  ← 循环往复     │
│  └─────────────────────┘  └─────────────────────┘                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 与 03 的关键区别

| 方面 | 03 (单PBO) | 04 (双PBO) |
|------|-----------|-----------| 
| PBO 数量 | 1 个 | 2 个 |
| CPU/GPU 关系 | 部分并行（可能等待） | 完全并行（永不等待） |
| 延迟 | 当前帧数据当前帧显示 | 当前帧数据**下一帧**显示（1帧延迟） |
| 吞吐量 | 中等 | 最高 |

### 关键代码解析

#### 1. 双 PBO 创建

```cpp
GLuint pbos[2];
glGenBuffers(2, pbos);
for (int i = 0; i < 2; i++) {
    glBindBuffer(GL_PIXEL_UNPACK_BUFFER, pbos[i]);
    glBufferData(GL_PIXEL_UNPACK_BUFFER, dataSize, nullptr, GL_STREAM_DRAW);
}
```

#### 2. 乒乓索引逻辑

```cpp
int writeIdx = pboIndex;          // CPU 写入这个 PBO
int uploadIdx = 1 - pboIndex;     // GPU 从这个 PBO 上传（上一帧写入的）
```

**索引交替**：

```
帧号    pboIndex    writeIdx    uploadIdx
 0        0           0           1        ← 第一帧 GPU 上传空数据（PBO_B 初始为空）
 1        1           1           0        ← GPU 上传帧0的数据
 2        0           0           1        ← GPU 上传帧1的数据
 3        1           1           0        ← GPU 上传帧2的数据
 ...
```

#### 3. 先上传，再写入（顺序很重要！）

```cpp
// ★ 步骤 1：GPU 从上一帧的 PBO 异步上传到纹理
glBindBuffer(GL_PIXEL_UNPACK_BUFFER, pbos[uploadIdx]);
glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h,
                GL_RGBA, GL_UNSIGNED_BYTE, (void*)0);

// ★ 步骤 2：同时，CPU 写入当前帧数据到另一个 PBO
glBindBuffer(GL_PIXEL_UNPACK_BUFFER, pbos[writeIdx]);
void* ptr = glMapBufferRange(GL_PIXEL_UNPACK_BUFFER, 0, dataSize,
                             GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT);
if (ptr) {
    memcpy(ptr, vframe.data[0], dataSize);
    glUnmapBuffer(GL_PIXEL_UNPACK_BUFFER);
}

// 交换索引
pboIndex = 1 - pboIndex;
```

**为什么这个顺序能实现并行？**

```
时间线 ──────────────────────────────────────────────────────▶

CPU:  [发起DMA命令] [映射PBO_A] [memcpy写入PBO_A] [unmap] [渲染命令]
       │(立即返回)   │                                │
       │             │← CPU 在这段时间做有用的工作 →│
       ▼             
GPU:  [接收DMA命令] ─────[DMA: PBO_B → 纹理]─────── [渲染]
       
       ↑ CPU 和 GPU 在同一时间做不同的事情 = 并行！
```

### 1 帧延迟的代价

双 PBO 引入了 **1 帧的显示延迟**：

```
帧 0: CPU 写入帧0数据 → PBO_A    GPU 上传 PBO_B (空) → 显示黑屏
帧 1: CPU 写入帧1数据 → PBO_B    GPU 上传 PBO_A (帧0) → 显示帧0  ← 延迟1帧
帧 2: CPU 写入帧2数据 → PBO_A    GPU 上传 PBO_B (帧1) → 显示帧1
```

对于视频播放来说，1 帧延迟（约 16ms@60fps）通常是可以接受的。但对于实时交互（如游戏输入响应），需要权衡。

### 性能提升原理

1. **零等待**：CPU 永远不需要等待 GPU 释放 PBO，因为两个 PBO 各自独立
2. **流水线化**：类似 CPU 的指令流水线，将"写入"和"上传"两个阶段重叠执行
3. **最大化总线利用率**：PCIe 总线在 CPU 写入和 GPU DMA 之间无缝切换

---

## 十三、示例 05: YUV420P + GPU 色彩空间转换

### 核心思想

**一句话总结**：跳过 CPU 端的 YUV→RGB 转换，直接上传原始 YUV 数据，让 GPU Shader 完成色彩转换。

### 与前面所有示例的根本区别

前面 01~04 的优化都集中在**传输方式**上，但传输的数据量始终是 RGBA（4字节/像素）。  
示例 05 从**数据格式**入手，直接减少需要传输的数据量。

```
01~04 的数据流:
┌──────────┐   sws_scale    ┌──────────┐   上传 8.3MB   ┌──────────┐
│ FFmpeg   │ ─────────────▶ │ RGBA     │ ─────────────▶ │ GPU      │
│ YUV解码  │  CPU转换(慢!)   │ 像素数据  │  (PCIe带宽)    │ 纹理     │
└──────────┘                └──────────┘                └──────────┘

05 的数据流:
┌──────────┐   直接上传 3.1MB   ┌──────────┐   Shader转换   ┌──────────┐
│ FFmpeg   │ ─────────────────▶ │ GPU      │ ────────────▶ │ RGB      │
│ YUV解码  │   (省62%带宽!)     │ YUV纹理  │  (GPU并行,0开销)│ 帧缓冲   │
└──────────┘                    └──────────┘               └──────────┘
```

### YUV420P 格式详解

#### 什么是 YUV420P？

```
YUV420P 内存布局 (以 8×4 像素为例):

Y 平面 (全分辨率 8×4 = 32 字节):
┌─┬─┬─┬─┬─┬─┬─┬─┐
│Y│Y│Y│Y│Y│Y│Y│Y│  每个像素一个 Y 值
├─┼─┼─┼─┼─┼─┼─┼─┤  Y = 亮度 (Luminance)
│Y│Y│Y│Y│Y│Y│Y│Y│  范围: 0~255 (归一化后 0.0~1.0)
├─┼─┼─┼─┼─┼─┼─┼─┤
│Y│Y│Y│Y│Y│Y│Y│Y│
├─┼─┼─┼─┼─┼─┼─┼─┤
│Y│Y│Y│Y│Y│Y│Y│Y│
└─┴─┴─┴─┴─┴─┴─┴─┘

U 平面 (1/4 分辨率 4×2 = 8 字节):
┌──┬──┬──┬──┐
│U │U │U │U │  每 2×2 像素共享一个 U 值
├──┼──┼──┼──┤  U = 蓝色色度 (Cb)
│U │U │U │U │  范围: 0~255 (归一化后 -0.5~+0.5)
└──┴──┴──┴──┘

V 平面 (1/4 分辨率 4×2 = 8 字节):
┌──┬──┬──┬──┐
│V │V │V │V │  每 2×2 像素共享一个 V 值
├──┼──┼──┼──┤  V = 红色色度 (Cr)
│V │V │V │V │  范围: 0~255 (归一化后 -0.5~+0.5)
└──┴──┴──┴──┘

总数据量 = 32 + 8 + 8 = 48 字节
等效 RGBA = 8 × 4 × 4 = 128 字节
压缩比 = 48/128 = 37.5% (节省 62.5%)
```

#### 为什么 UV 可以降采样？

人眼对**亮度变化**非常敏感，但对**色彩变化**不太敏感。YUV420 利用这个特性：
- Y（亮度）保持全分辨率 → 保证画面清晰度
- U/V（色度）降为 1/4 → 大幅减少数据量，人眼几乎察觉不到

### 关键代码解析

#### 1. 以 YUV420P 格式打开视频

```cpp
// ★ 不做 CPU 端的 YUV→RGBA 转换
glvideo::VideoReader video;
video.open(VIDEO_PATH, glvideo::PixelFormat::YUV420);
```

对比前面的示例：
```cpp
// 01~04: FFmpeg 内部会调用 sws_scale 将 YUV 转为 RGBA
video.open(VIDEO_PATH, glvideo::PixelFormat::RGBA);
```

#### 2. 创建三个独立纹理

```cpp
GLuint textures[3]; // Y, U, V
glGenTextures(3, textures);

// Y 平面：全分辨率，单通道
glBindTexture(GL_TEXTURE_2D, textures[0]);
glTexImage2D(GL_TEXTURE_2D, 0, GL_R8, w, h, 0,
             GL_RED, GL_UNSIGNED_BYTE, nullptr);

// U 平面：宽高各减半，单通道
glBindTexture(GL_TEXTURE_2D, textures[1]);
glTexImage2D(GL_TEXTURE_2D, 0, GL_R8, w/2, h/2, 0,
             GL_RED, GL_UNSIGNED_BYTE, nullptr);

// V 平面：宽高各减半，单通道
glBindTexture(GL_TEXTURE_2D, textures[2]);
glTexImage2D(GL_TEXTURE_2D, 0, GL_R8, w/2, h/2, 0,
             GL_RED, GL_UNSIGNED_BYTE, nullptr);
```

**关键格式说明**：

| 参数 | 值 | 含义 |
|------|-----|------|
| internalformat | `GL_R8` | GPU 内部存储为单通道 8 位（1字节/像素） |
| format | `GL_RED` | 输入数据为单通道 |
| U/V 尺寸 | `w/2, h/2` | 色度平面是亮度平面的 1/4 |

对比 01~04 使用的 `GL_RGBA`（4字节/像素），`GL_R8` 只需 1字节/像素。

#### 3. 上传三个平面 + glPixelStorei

```cpp
// 上传 Y 平面
glBindTexture(GL_TEXTURE_2D, textures[0]);
glPixelStorei(GL_UNPACK_ROW_LENGTH, vframe.linesize[0]);  // ★ 关键！
glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h,
                GL_RED, GL_UNSIGNED_BYTE, vframe.data[0]);
```

**`glPixelStorei(GL_UNPACK_ROW_LENGTH, ...)` 的作用**：

FFmpeg 解码后的帧数据可能有**行对齐填充**（padding）：

```
FFmpeg 输出的 Y 平面内存布局 (假设 width=1920, linesize=1920 或 2048):

实际像素数据          填充
├─── width=1920 ───┤├──┤
┌──────────────────┬────┐
│ 第0行像素数据     │pad │  ← linesize[0] 字节
├──────────────────┼────┤
│ 第1行像素数据     │pad │  ← linesize[0] 字节
├──────────────────┼────┤
│ ...              │    │
└──────────────────┴────┘
```

`GL_UNPACK_ROW_LENGTH` 告诉 OpenGL：源数据每行的实际字节跨度（stride），这样 OpenGL 就能正确跳过 padding 读取像素。

#### 4. 绑定三个纹理到不同纹理单元

```cpp
glActiveTexture(GL_TEXTURE0);
glBindTexture(GL_TEXTURE_2D, textures[0]);
shader.setInt("tex_y", 0);  // Y → 纹理单元 0

glActiveTexture(GL_TEXTURE1);
glBindTexture(GL_TEXTURE_2D, textures[1]);
shader.setInt("tex_u", 1);  // U → 纹理单元 1

glActiveTexture(GL_TEXTURE2);
glBindTexture(GL_TEXTURE_2D, textures[2]);
shader.setInt("tex_v", 2);  // V → 纹理单元 2
```

**纹理单元机制**：

```
┌─────────────────────────────────────────────────────┐
│              GPU 纹理单元 (Texture Units)             │
├─────────────────────────────────────────────────────┤
│                                                      │
│  单元 0 (GL_TEXTURE0) ──▶ textures[0] (Y平面)       │
│  单元 1 (GL_TEXTURE1) ──▶ textures[1] (U平面)       │
│  单元 2 (GL_TEXTURE2) ──▶ textures[2] (V平面)       │
│  单元 3~15             ──▶ (未使用)                  │
│                                                      │
│  Shader 通过 uniform int 值选择从哪个单元采样         │
│  tex_y = 0 → 从单元0采样                            │
│  tex_u = 1 → 从单元1采样                            │
│  tex_v = 2 → 从单元2采样                            │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### YUV→RGB 片段着色器详解 (`yuv420p.frag`)

```glsl
#version 430 core

in vec2 TexCoord;
out vec4 FragColor;

uniform sampler2D tex_y;   // Y 平面纹理
uniform sampler2D tex_u;   // U 平面纹理
uniform sampler2D tex_v;   // V 平面纹理

void main() {
    float y = texture(tex_y, TexCoord).r;
    float u = texture(tex_u, TexCoord).r - 0.5;
    float v = texture(tex_v, TexCoord).r - 0.5;

    // BT.709 转换
    float r = y + 1.5748 * v;
    float g = y - 0.1873 * u - 0.4681 * v;
    float b = y + 1.8556 * u;

    FragColor = vec4(clamp(r, 0.0, 1.0),
                     clamp(g, 0.0, 1.0),
                     clamp(b, 0.0, 1.0),
                     1.0);
}
```

#### 逐行深度解析

**1. 采样三个平面**

```glsl
float y = texture(tex_y, TexCoord).r;       // 从 Y 纹理采样亮度
float u = texture(tex_u, TexCoord).r - 0.5; // 从 U 纹理采样，偏移到 [-0.5, +0.5]
float v = texture(tex_v, TexCoord).r - 0.5; // 从 V 纹理采样，偏移到 [-0.5, +0.5]
```

**为什么 U/V 要减 0.5？**
- 存储时 U/V 范围是 [0, 255]（归一化后 [0.0, 1.0]）
- 实际含义是以 128（0.5）为中心的有符号值
- 减去 0.5 后恢复为 [-0.5, +0.5] 的真实色度值
- U=0.5, V=0.5 表示"无色彩偏移"（灰色）

**U/V 纹理采样时的自动上采样**：

```
U 纹理实际大小: 960×540 (1080p的1/4)
采样坐标 TexCoord: 范围 [0,1] 覆盖整个画面

当 TexCoord = (0.5, 0.5) 时:
  Y 纹理采样位置: 像素 (960, 540)  ← 精确命中
  U 纹理采样位置: 像素 (480, 270)  ← 精确命中

当 TexCoord = (0.501, 0.501) 时:
  Y 纹理采样位置: 像素 (961, 540.5) ← 需要插值
  U 纹理采样位置: 像素 (480.5, 270.25) ← GL_LINEAR 自动双线性插值！

→ OpenGL 的 GL_LINEAR 过滤自动完成了 U/V 的上采样！
  不需要手动处理 2×2 像素共享色度的逻辑。
```

**2. BT.709 色彩空间转换**

```glsl
float r = y + 1.5748 * v;
float g = y - 0.1873 * u - 0.4681 * v;
float b = y + 1.8556 * u;
```

这是 **ITU-R BT.709** 标准的转换公式（适用于高清视频 720p+）：

```
┌─┐   ┌                    ┐ ┌───┐
│R│   │ 1.0    0.0    1.5748│ │ Y │
│G│ = │ 1.0   -0.1873 -0.4681│ │ U │
│B│   │ 1.0    1.8556  0.0  │ │ V │
└─┘   └                    ┘ └───┘
```

**色彩标准对比**：

| 标准 | 适用范围 | 特点 |
|------|---------|------|
| BT.601 | 标清视频 (SD, 480p/576p) | 旧标准，色域较小 |
| BT.709 | 高清视频 (HD, 720p+) | 现代标准，色域更准确 |
| BT.2020 | 超高清 (4K/8K HDR) | 最新标准，广色域 |

**3. clamp 限制范围**

```glsl
FragColor = vec4(clamp(r, 0.0, 1.0), clamp(g, 0.0, 1.0), clamp(b, 0.0, 1.0), 1.0);
```

由于矩阵运算可能产生超出 [0,1] 的值（特别是高饱和度颜色），`clamp` 确保输出在有效范围内。

### GPU 并行计算的威力

```
CPU 做 YUV→RGB 转换 (示例 01~04 中 FFmpeg 的 sws_scale):
┌─────────────────────────────────────────────────────────┐
│ for (每个像素) {           // 1920×1080 = 2,073,600 次  │
│     r = y + 1.5748 * v;   // 串行执行                   │
│     g = y - 0.1873*u - 0.4681*v;                        │
│     b = y + 1.8556 * u;                                 │
│ }                                                        │
│ 耗时: ~3-5ms (单核) 或 ~1ms (SIMD优化)                  │
└─────────────────────────────────────────────────────────┘

GPU 做 YUV→RGB 转换 (示例 05 的 Fragment Shader):
┌─────────────────────────────────────────────────────────┐
│ 2,073,600 个 GPU 核心同时执行:                           │
│   核心 0: pixel(0,0) 的 YUV→RGB                         │
│   核心 1: pixel(1,0) 的 YUV→RGB                         │
│   核心 2: pixel(2,0) 的 YUV→RGB                         │
│   ...                                                    │
│   核心 N: pixel(1919,1079) 的 YUV→RGB                   │
│                                                          │
│ 耗时: ~0.1ms (大规模并行)                                │
└─────────────────────────────────────────────────────────┘
```

### 性能提升原理

| 优化维度 | 效果 |
|---------|------|
| 减少 CPU 计算 | 省去 `sws_scale` 的 YUV→RGBA 转换（节省 1~5ms/帧） |
| 减少传输带宽 | 3.1MB vs 8.3MB，减少 62%（PCIe 带宽是稀缺资源） |
| GPU 并行转换 | 片段着色器对每个像素并行执行，几乎零额外开销 |
| 减少内存占用 | GPU 端纹理内存也减少 62% |

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
│ 01 glTexImage2D:                                                         │
│ CPU: ══[分配+传输]══════════════════════[渲染命令]══                      │
│ GPU: ─────────────────────────────────────────────[渲染]──               │
│      ↑ CPU 完全阻塞                                                      │
│                                                                          │
│ 02 glTexSubImage2D:                                                      │
│ CPU: ══[传输]══════════════════════════[渲染命令]══                       │
│ GPU: ───────────────────────────────────────────[渲染]──                 │
│      ↑ 省去分配，但仍阻塞                                                │
│                                                                          │
│ 03 单 PBO:                                                               │
│ CPU: ═[memcpy→PBO]═[发起DMA]─[其他工作...]─[渲染命令]══                  │
│ GPU: ──────────────────────[DMA传输]────────────────[渲染]──             │
│      ↑ CPU 写入后不等待 GPU                                              │
│                                                                          │
│ 04 双 PBO:                                                               │
│ CPU: ═[memcpy→PBO_A]═──────────────────────[渲染命令]══                  │
│ GPU: ═[DMA: PBO_B→纹理]═──────────────────────────[渲染]──              │
│      ↑ CPU 和 GPU 完全并行，零等待                                        │
│                                                                          │
│ 05 YUV:                                                                  │
│ CPU: ═[传输Y]═[传输U]═[传输V]═[渲染命令]══                              │
│ GPU: ──────────────────────────────────[YUV→RGB + 渲染]──               │
│      ↑ 传输量减少62%，GPU做格式转换                                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Shader 差异对比

| 示例 | 顶点着色器 | 片段着色器 | 纹理数量 |
|------|-----------|-----------|---------| 
| 01~04 | basic.vert | basic.frag (直接采样RGBA) | 1 个 |
| 05 | basic.vert (相同) | yuv420p.frag (YUV→RGB转换) | 3 个 |

### 最佳实践组合

在实际生产环境中，这些技术可以**组合使用**：

```
终极方案: 双PBO + YUV420P + GPU转换

┌──────────┐   YUV420P    ┌────────┐   DMA异步   ┌────────┐   Shader   ┌──────┐
│ FFmpeg   │ ───────────▶ │ PBO_A  │ ──────────▶ │ YUV    │ ────────▶ │ RGB  │
│ 解码     │  3.1MB/帧    │ PBO_B  │  完全并行    │ 纹理×3 │  GPU并行   │ 输出  │
└──────────┘              └────────┘             └────────┘           └──────┘
                          (乒乓缓冲)

预期性能: 1080p@60fps 仅需 ~186MB/s PCIe 带宽
          CPU 几乎零开销（只做 memcpy + 命令提交）
          GPU 做所有重活（DMA + 色彩转换 + 渲染）
```

---

## 十五、性能分析与瓶颈

### 15.1 示例 01 的瓶颈分析

| 阶段 | 耗时原因 | 优化方向 |
|------|----------|----------|
| 纹理上传 | `glTexImage2D` 每帧重新分配 GPU 内存 | 用 `glTexSubImage2D` 只更新数据 |
| 数据传输 | CPU→GPU 同步阻塞 | PBO (Pixel Buffer Object) 异步 DMA |
| 格式转换 | FFmpeg 在 CPU 上做 YUV→RGBA | 上传 YUV 纹理，GPU Shader 转换 |
| 带宽浪费 | RGBA 4字节/像素 | YUV NV12 仅 1.5字节/像素 |

### 15.2 理论带宽计算 (1080p@60fps)

```
glTexImage2D 方式 (示例 01):
  每帧数据量 = 1920 × 1080 × 4 = 8,294,400 字节 ≈ 8.3 MB
  60fps 带宽 = 8.3 × 60 = 498 MB/s

YUV420P 方式 (示例 05):
  每帧数据量 = 1920 × 1080 × 1.5 = 3,110,400 字节 ≈ 3.1 MB
  60fps 带宽 = 3.1 × 60 = 186 MB/s  (节省 63%)

终极方案 (双PBO + YUV420P):
  带宽需求 = 186 MB/s
  PCIe 3.0 x16 带宽 = 15.75 GB/s
  带宽利用率 = 186 / 15750 ≈ 1.2%  (绰绰有余)
```

---

## 十六、关键 API 速查表

| API | 示例 | 作用 |
|-----|------|------|
| `glTexImage2D(data)` | 01 | 分配纹理 + 上传数据（每帧重新分配） |
| `glTexImage2D(nullptr)` | 02~05 | 仅分配纹理内存（初始化时一次） |
| `glTexSubImage2D` | 02~05 | 更新已有纹理的像素数据 |
| `glGenBuffers` + `GL_PIXEL_UNPACK_BUFFER` | 03~04 | 创建 PBO |
| `glMapBufferRange` | 03~04 | 映射 PBO 到 CPU 地址空间 |
| `GL_MAP_INVALIDATE_BUFFER_BIT` | 03~04 | 允许驱动丢弃旧数据（避免同步） |
| `glPixelStorei(GL_UNPACK_ROW_LENGTH)` | 05 | 设置源数据行跨度（处理padding） |
| `glActiveTexture(GL_TEXTUREn)` | 05 | 激活第 n 个纹理单元 |
| `GL_R8` / `GL_RED` | 05 | 单通道 8 位纹理格式 |

### 关键 OpenGL 概念速查表

| 概念 | 说明 |
|------|------|
| **VAO** (Vertex Array Object) | 顶点属性配置的"快照"，记录如何解释 VBO 中的数据 |
| **VBO** (Vertex Buffer Object) | GPU 显存中的顶点数据缓冲区 |
| **EBO** (Element Buffer Object) | 索引缓冲，避免重复存储共享顶点 |
| **PBO** (Pixel Buffer Object) | 像素缓冲，用于异步 CPU↔GPU 像素数据传输 |
| **Texture Unit** | 纹理单元，Shader 通过单元编号访问纹理 |
| **Uniform** | Shader 中的全局常量，由 CPU 端设置 |
| **NDC** (Normalized Device Coordinates) | 标准化设备坐标 [-1,1]³ |
| **Fragment** | 光栅化产生的"候选像素"，包含插值后的属性 |
| **Framebuffer** | 帧缓冲，GPU 渲染的最终输出目标 |
| **sampler2D** | GLSL 中的 2D 纹理采样器类型 |
| **Core Profile** | 仅使用现代 OpenGL 功能，禁用废弃 API |
| **DMA** (Direct Memory Access) | 硬件级数据传输，不占用 CPU |
| **Buffer Orphaning** | 驱动丢弃旧缓冲分配新缓冲，避免 CPU/GPU 同步等待 |

---

## 附录

### 源文件清单

| 文件 | 作用 |
|------|------|
| `src/common/gl_utils.h/.cpp` | 窗口创建、主循环、全屏四边形 |
| `src/common/shader.h/.cpp` | Shader 编译、链接、Uniform 设置 |
| `src/common/timer.h/.cpp` | 性能计时工具 |
| `src/common/video_reader.h/.cpp` | FFmpeg 视频解码封装 |
| `src/01_basic_texture/main.cpp` | 示例01：基础纹理上传 |
| `src/02_texture_streaming/main.cpp` | 示例02：流式纹理更新 |
| `src/03_pbo_upload/main.cpp` | 示例03：单PBO异步上传 |
| `src/04_double_pbo/main.cpp` | 示例04：双PBO乒乓缓冲 |
| `src/05_yuv_rendering/main.cpp` | 示例05：YUV GPU渲染 |
| `shaders/basic.vert` | 通用顶点着色器 |
| `shaders/basic.frag` | RGBA 片段着色器（示例01~04） |
| `shaders/yuv420p.frag` | YUV→RGB 片段着色器（示例05） |

### 推荐阅读顺序

1. 先通读本文档第一部分，理解 OpenGL 渲染管线的完整流程
2. 运行示例 01，观察基础方案的帧率表现
3. 逐个阅读第二部分的优化章节，对照代码理解每种优化的原理
4. 依次运行示例 02~05，对比帧率变化
5. 思考如何将示例 04 和 05 的技术组合，实现终极优化方案
