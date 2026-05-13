# 图形学基础 —— 虎书 + LearnOpenGL 双主线入门版

> **作者**：汪亮 bertonwang  📧 47608843@qq.com
>
> **目标读者**：会一点 C/C++（知道指针、类、CMake 大致是什么），看过《GPU 渲染与图形学入门》总览文档，想**真正动手**进入图形学领域的同学。
>
> **本文风格**：把"理论（虎书）"和"实战（LearnOpenGL）"**编织在一起**，每个知识点都同时给出 **"为什么 / 公式 / 代码 / 怎么调试"** 四件套，让你能跟着写、跟着调、跟着看到画面变化。
>
> **预计学习时长**：每天 1.5~2 小时，**12 周（约 3 个月）** 走完全部内容，能写出一个有光照、纹理、相机、模型加载的小型 3D 场景。
>
> 🎯 **本版承诺（深度补强版）**：本文档**自包含（self-contained）**——你**不需要离开本文档**，从安装编译器、第一行代码、每周作品到展厅毕业项目，所有**完整可编译的源码**都在文中。需要外部网页时仅作为

---

## 目录

**Part 0 — 准备工作**

- [0. 一句话先说清楚这份资料怎么用](#0-一句话先说清楚这份资料怎么用)
- [A0. 先修知识 30 分钟：C++20 / 线代 / 三角 / 坐标系](#a0-先修知识-30-分钟c20--线代--三角--坐标系)
- [1. 学习思路：为什么"虎书 + LearnOpenGL"是黄金搭档？](#1-学习思路为什么虎书--learnopengl-是黄金搭档)
- [2. 12 周学习节奏表（先看这个）](#2-12-周学习节奏表先看这个)
- [3. 环境搭建：从零跑通"Hello Triangle"](#3-环境搭建从零跑通hello-triangle)

**Part 1 — 数学基础（虎书 Ch 2~5）**

- [4. 向量与点：图形学的"原子"](#4-向量与点图形学的原子)
- [5. 矩阵与变换：让物体"动起来"](#5-矩阵与变换让物体动起来)
- [6. 三大空间变换：模型 → 世界 → 视图 → 投影](#6-三大空间变换模型--世界--视图--投影)
- [7. 齐次坐标：为什么矩阵是 4×4？](#7-齐次坐标为什么矩阵是-44)

**Part 2 — 渲染管线（虎书 Ch 8~9 + LearnOpenGL "入门"）**

- [8. 管线全貌：从顶点到像素的 6 步](#8-管线全貌从顶点到像素的-6-步)
- [9. 第一个三角形：搞懂 VAO / VBO / EBO](#9-第一个三角形搞懂-vao--vbo--ebo)
- [10. 着色器入门：GLSL 你必须懂的 5 件事](#10-着色器入门glsl-你必须懂的-5-件事)
- [11. 光栅化与深度测试：像素是怎么"诞生"的](#11-光栅化与深度测试像素是怎么诞生的)

**Part 3 — 纹理与光照（虎书 Ch 10~11 + LearnOpenGL "纹理"+"光照"）**

- [12. 纹理映射：把图片"贴"到模型上](#12-纹理映射把图片贴到模型上)
- [13. 光照基础：Phong / Blinn-Phong 模型](#13-光照基础phong--blinn-phong-模型)
- [14. 光源类型：方向光 / 点光源 / 聚光灯](#14-光源类型方向光--点光源--聚光灯)
- [15. 摄像机：让用户"走进"场景](#15-摄像机让用户走进场景)

**Part 4 — 模型加载与综合实战**

- [16. 模型加载：用 Assimp 读取 OBJ / glTF](#16-模型加载用-assimp-读取-obj--gltf)
- [17. 综合实战：搭一个"展厅"小场景](#17-综合实战搭一个展厅小场景)

**Part 5 — 调试与避坑**

- [18. 着色器调试 5 招（含 RenderDoc 入门）](#18-着色器调试-5-招含-renderdoc-入门)
- [19. 初学者最常见的 10 个 Bug](#19-初学者最常见的-10-个-bug)

**Part 6 — 进阶补强（避免常见踩坑）**

- [20. Gamma 校正与 HDR：为什么我画面发暗 / 颜色不对？](#20-gamma-校正与-hdr为什么我画面发暗--颜色不对)
- [21. 法线矩阵 / reflect / refract / gl_FragCoord](#21-法线矩阵--reflect--refract--gl_fragcoord)

**Part 7 — 完整可复用代码库（拷走即用）**

- [C1. Shader 类完整源码](#c1-shader-类完整源码)
- [C2. Camera 类完整源码](#c2-camera-类完整源码)
- [C3. Texture 工具完整源码](#c3-texture-工具完整源码)
- [C4. Mesh / Model 类完整源码](#c4-mesh--model-类完整源码)

**附录**

- [A. 资料速查表](#附录-a资料速查表)
- [B. 数学公式小抄](#附录-b数学公式小抄)
- [C. OpenGL API 速查](#附录-copengl-api-速查)
- [A4. 12 周自检清单（每周打勾表）](#附录-a412-周自检清单每周打勾表)

---

## 0. 一句话先说清楚这份资料怎么用

> **这不是新教程，而是把虎书 + LearnOpenGL 拧成一股绳的"学习路径图"。**

每一节的结构都长这样：

```text
┌──────────────────────────────────────────┐
│ 📖 虎书对应章节  +  💻 LearnOpenGL 对应教程 │
│ ─────────────────────────────────────────│
│ 1) 大白话讲一遍核心概念                    │
│ 2) 关键公式 / 关键 API（最少够用版）       │
│ 3) 必做练习（把它写出来才算学会）          │
│ 4) 常见坑 + 调试方法                       │
└──────────────────────────────────────────┘
```

> 💡 **使用建议**：左手开虎书 PDF（中英任选），右手开 LearnOpenGL 网页，本文档作为"导航 + 串讲"。**理论先行 1~2 节虎书，再去 LearnOpenGL 把对应代码敲一遍**。

> ⚙️ **本版本（深度补强）的差异**：所有学习里程碑的**完整源码**（Hello Triangle / 旋转立方体 / Camera / Blinn-Phong / 多光源 / 模型加载 / 展厅项目）都收录在 §C1~§C4 与各章末尾，**不需离开本文档即可学完**。

---

## A0. 先修知识 30 分钟：C++20 / 线代 / 三角 / 坐标系

> 本节的目的是**把后续章节会用到的最少前置知识压缩到 30 分钟**。如果你已熟悉，可直接跳过。**不熟悉的话，强烈建议先把这一节啃完**——后面所有代码都建立在这些"原子认知"上。

### A0.1 C++20 你必须知道的 8 件事

本文档全部代码使用 **C++20**（`-std=c++20` / `CMAKE_CXX_STANDARD 20`）。

| # | 特性 | 长这样 | 为什么用 |
|---|---|---|---|
| 1 | **结构化绑定** | `auto [w, h] = getSize();` | 一次解包多返回值 |
| 2 | **`std::filesystem`** | `fs::path p = "shaders/x.vert";` | 跨平台路径 |
| 3 | **`std::format`**（或 `fmt`） | `std::format("err: {}", code)` | 比 `printf` 安全 |
| 4 | **`std::span<T>`** | `void f(std::span<float> v)` | 替代裸指针+长度 |
| 5 | **`std::numbers::pi`** | `using namespace std::numbers;` | 不用自己写 `3.14159...` |
| 6 | **`concepts`/`requires`** | `template<std::floating_point T>` | 模板约束更清晰 |
| 7 | **指定初始化** | `Vertex{.pos=p, .uv=u}` | 字段顺序错也不出 bug |
| 8 | **`<chrono>` literals** | `using namespace std::chrono_literals; 16ms` | 帧率/时间更直观 |

> 💡 **OpenGL 与 C++20 关系**：OpenGL 本身是 **C 接口**，所有 `glXxx` 都是全局函数。我们用 C++20 是为了**封装、内存管理、异常安全**，不影响 GL 调用本身。

#### 必须会写的 RAII 包装小例子

```cpp
// 用 RAII 自动释放 OpenGL 资源（C++20 风格）
class GLBuffer {
    GLuint id_ = 0;
public:
    GLBuffer() { glGenBuffers(1, &id_); }
    ~GLBuffer() { if (id_) glDeleteBuffers(1, &id_); }

    GLBuffer(const GLBuffer&) = delete;             // 禁止拷贝
    GLBuffer& operator=(const GLBuffer&) = delete;
    GLBuffer(GLBuffer&& o) noexcept : id_(o.id_) { o.id_ = 0; } // 允许移动
    GLBuffer& operator=(GLBuffer&& o) noexcept {
        if (this != &o) { if (id_) glDeleteBuffers(1, &id_); id_ = o.id_; o.id_ = 0; }
        return *this;
    }
    GLuint id() const noexcept { return id_; }
};
```

后续 §C1~§C4 全部按这个模式封装（"五法则"：析构、删拷贝构造、删拷贝赋值、移动构造、移动赋值）。

### A0.2 线性代数：只需 3 个概念

#### ① 向量（Vector）

> "**带方向的箭头**"。在图形学里，**点和向量都用 (x,y,z) 三个数表示**，区别只在第 4 个分量 w（见 §7）。

#### ② 矩阵 (Matrix)

> "**一张数表，能批量改造向量**"。4×4 矩阵能同时表达"先缩放、再旋转、再平移"。

矩阵乘以向量：

```text
                    v.x        v.x'
[ a b c d ]         v.y        v.y'
[ e f g h ]    ×    v.z   =    v.z'
[ i j k l ]         1.0        1.0'
[ m n o p ]
```

`v.x' = a*v.x + b*v.y + c*v.z + d*1.0`，其余类推。

> 💡 **重点**：矩阵乘法**不满足交换律**——`A·B ≠ B·A`，所以做"先平移再旋转"和"先旋转再平移"画面完全不同。

#### ③ 点积与叉积（Dot & Cross）

| 运算 | 公式 | 结果类型 | 用途 |
|---|---|---|---|
| `a·b` | `ax*bx + ay*by + az*bz` | **标量** | 判断方向相似度（光照） |
| `a×b` | （见下） | **向量**（垂直于 a、b） | 求法线、判左右手 |

叉积展开：

```text
a × b = (ay*bz - az*by,
         az*bx - ax*bz,
         ax*by - ay*bx)
```

> 💡 一个重要事实：`|a×b| = |a|·|b|·sinθ`，所以**叉积长度等于平行四边形面积**——光栅化里求三角形面积、重心坐标都靠它。

### A0.3 三角函数 90 秒回顾

```text
        |
        |  对边
        |________
   斜边/|        |
      / |        |
     /  |        |
    /θ__|________|

sin(θ) = 对边 / 斜边
cos(θ) = 邻边 / 斜边
tan(θ) = 对边 / 邻边
```

图形学只需记住：

- `cos(0) = 1`、`sin(0) = 0`、`cos(90°) = 0`、`sin(90°) = 1`
- `cos²θ + sin²θ = 1`
- **OpenGL/GLM 用弧度**，不是角度：`glm::radians(45.0f)` 才能得到 `π/4`。

### A0.4 右手坐标系（OpenGL 默认）

```text
        +Y (上)
         │
         │
         │_______ +X (右)
        /
       /
      +Z (朝向你/出屏幕)
```

> ⚠️ 摄像机默认看向 **-Z 方向**（背向你）。这是 LearnOpenGL 全部教程的约定，**记错会导致"模型在背后"**。

判断右手系：右手食指 +X、中指 +Y、拇指自然指向 +Z。

### A0.5 颜色与浮点

| 表示法 | 范围 | 例子 |
|---|---|---|
| 整数 RGB | 0~255 | `(255, 128, 0)` 橙色 |
| 浮点 RGB（OpenGL 用） | 0.0~1.0 | `(1.0, 0.5, 0.0)` 橙色 |
| HDR 浮点 | 可 > 1.0 | `(5.0, 5.0, 5.0)` 强光（用于 Bloom） |

GLSL 中颜色一律是 `vec3` 或 `vec4`（带 alpha），**值在 [0,1]**，超过 1 会被显示器截断（除非走 HDR 流程，见 §20）。

### A0.6 一句话术语对照

| 术语 | 一句话 |
|---|---|
| **顶点 (Vertex)** | 一个 3D 点 + 它附带的属性（颜色、UV、法线…） |
| **图元 (Primitive)** | 三角形 / 线 / 点 |
| **片段 (Fragment)** | "潜在像素"——可能被深度测试丢弃 |
| **着色器 (Shader)** | 在 GPU 上跑的小程序 |
| **Uniform** | CPU 传给所有顶点/片段共享的常量（矩阵、时间） |
| **Attribute** | 每个顶点都不一样的输入（位置、UV） |
| **Varying / out-in** | Vertex → Fragment 之间会自动插值的变量 |

> ✅ 记住这 7 个词，看 LearnOpenGL 任何一节都不会再"卡名词"。

---

## 1. 学习思路：为什么"虎书 + LearnOpenGL"是黄金搭档？

| 维度 | 虎书（理论派） | LearnOpenGL（实战派） |
|---|---|---|
| **核心问题** | "**为什么**这样画" | "**怎么**写代码画" |
| **强项** | 数学推导、原理、广度 | 代码、API、可跑通 |
| **弱项** | 缺代码、跑不起来 | 数学一笔带过 |
| **风格** | 像教科书 | 像兄长手把手带你 |

如果**只看虎书**：会"懂了但写不出来"。
如果**只看 LearnOpenGL**：会"代码跑通了但不知道为什么"。
**两者结合**：理论 + 实践 = 真正掌握。

### 1.1 学习铁律

```text
看 1 节理论 → 写对应代码 → 改参数玩 5 分钟 → 进下一节
                  ▲
                  └── 90% 的人卡在这里
```

> ⚠️ **千万别只看不写**——图形学是手感学科，调出错误的画面、再调对，才是真正的学习。

---

## 2. 12 周学习节奏表（先看这个）

| 周次 | 虎书章节 | LearnOpenGL | 当周产出（自己能跑） |
|---|---|---|---|
| **W1** | Ch 2: 数学基础（向量、点积、叉积） | 入门：环境搭建 + Hello Window | 一个能开关的黑窗口 |
| **W2** | Ch 5: 线性代数（矩阵、变换） | 入门：Hello Triangle + Shaders | **彩色三角形** |
| **W3** | Ch 6: 变换矩阵 | 入门：Textures + Transformations | 能旋转的贴图矩形 |
| **W4** | Ch 7: 视图与投影 | 入门：Coordinate Systems | **3D 立方体（10 个会转的小方块）** |
| **W5** | 复习 + Ch 8 前半 | 入门：Camera | 自由飞行 FPS 摄像机 |
| **W6** | Ch 10: 表面着色（光照） | 光照：Colors + Basic Lighting | **Phong 光照下的立方体** |
| **W7** | Ch 10 续 | 光照：Materials + Lighting Maps | 带高光贴图的木箱 |
| **W8** | Ch 10 末尾 | 光照：Light Casters + Multiple Lights | **3 种光源 + 4 个点光源** |
| **W9** | Ch 11: 纹理映射深入 | 模型：Assimp + Mesh + Model | 加载 nanosuit / 任意 OBJ 模型 |
| **W10** | Ch 9: 可见面 + Z-buffer | 高级：Depth Testing + Stencil Testing | 能正确遮挡的多模型场景 |
| **W11** | Ch 11 末尾：MIP-map / 立方体贴图 | 高级：Cubemaps + Framebuffers | **天空盒 + 简单后处理** |
| **W12** | 复习 + 项目整合 | 综合 demo | **个人小展厅项目交付** |

> 💡 **进度可弹性**：上班族可拉长到 6 个月；学生暑假可压缩到 6 周。**关键不是速度，是产出**。

---

## 3. 环境搭建：从零跑通"Hello Triangle"

> 本节目标：**从一个空文件夹**到看到第一个橙色三角形。**Windows / macOS / Linux 三平台通吃**。

### 3.1 最小依赖清单

| 工具 | 用途 | 推荐版本 |
|---|---|---|
| **C++20 编译器** | 编写代码 | MSVC 19.30+ (VS 2022) / Clang 14+ / GCC 12+ |
| **CMake** | 跨平台构建 | 3.20+ |
| **Git** | 拉子仓库 | 任意 |
| **GLFW** | 创建窗口、处理输入 | 3.3+ |
| **GLAD** | 加载 OpenGL 函数指针 | 在线生成 |
| **GLM** | 数学库（向量/矩阵） | 0.9.9+ |
| **stb_image** | 加载图片 | 单文件头 |
| **Assimp**（W9 才用） | 加载 3D 模型 | 5.x |

### 3.2 一步步装环境（Windows 版）

> macOS / Linux 用户跳到 §3.2.5 看简化指令。

#### 3.2.1 安装 Visual Studio 2022（含 C++20）

1. 下载 [Visual Studio Community 2022](https://visualstudio.microsoft.com/zh-hans/vs/community/)（免费）
2. 安装时勾选 **"使用 C++ 的桌面开发"** workload
3. 在 "**单个组件**" 里额外勾选：
   - `MSVC v143 - VS 2022 C++ x64/x86 生成工具`
   - `适用于最新 v143 生成工具的 C++ ATL`
   - `适用于 Windows 的 C++ CMake 工具`

#### 3.2.2 验证 C++20 是否可用

打开 "Developer PowerShell for VS 2022"，运行：

```powershell
cl /std:c++20 /Bv 2>&1 | findstr "Microsoft"
# 应输出：Compiler Passes: ... 19.3x.xxxxx
```

#### 3.2.3 安装 CMake 与 Git

```powershell
winget install Kitware.CMake
winget install Git.Git
```

#### 3.2.4 在线生成 GLAD

1. 打开 <https://glad.dav1d.de/>
2. 选择：
   - **Language**: C/C++
   - **Specification**: OpenGL
   - **API → gl**: Version 3.3
   - **Profile**: Core
   - **Options**: 勾选 "Generate a loader"
3. 点 "Generate" → 下载 zip → 解压
4. 把里面的 `include/` 和 `src/glad.c` 放到 `third_party/glad/` 下

#### 3.2.5 macOS / Linux 一键脚本

```bash
# macOS
brew install cmake git
xcode-select --install     # 装 Apple Clang（含 C++20）

# Ubuntu 22.04+
sudo apt update
sudo apt install -y cmake git build-essential libgl1-mesa-dev \
                    libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev
```

### 3.3 完整目录结构（最终形态）

```text
my-graphics/
├── CMakeLists.txt
├── third_party/
│   ├── glad/
│   │   ├── include/glad/glad.h
│   │   ├── include/KHR/khrplatform.h
│   │   └── src/glad.c
│   ├── glfw/                    ← git submodule
│   ├── glm/                     ← git submodule（header-only）
│   └── stb/
│       └── stb_image.h          ← 单文件下载
├── shaders/
│   ├── basic.vert
│   └── basic.frag
├── src/
│   ├── main.cpp
│   ├── Shader.hpp / .cpp        ← §C1
│   ├── Camera.hpp / .cpp        ← §C2
│   ├── Texture.hpp / .cpp       ← §C3
│   └── Mesh.hpp Model.hpp       ← §C4
└── assets/
    ├── textures/
    └── models/
```

#### 一次性把第三方库拉下来

```powershell
mkdir my-graphics; cd my-graphics
git init
git submodule add https://github.com/glfw/glfw.git third_party/glfw
git submodule add https://github.com/g-truc/glm.git third_party/glm
# stb：只取单个文件
mkdir third_party/stb
curl -L -o third_party/stb/stb_image.h https://raw.githubusercontent.com/nothings/stb/master/stb_image.h
```

### 3.4 完整 CMakeLists.txt（C++20，可直接复制）

```cmake
cmake_minimum_required(VERSION 3.20)
project(my_graphics CXX C)

# ---- C++20 ----
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ---- 第三方库 ----
# GLFW
set(GLFW_BUILD_DOCS    OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_TESTS   OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
add_subdirectory(third_party/glfw)

# GLAD（C 文件单独编译成静态库）
add_library(glad STATIC third_party/glad/src/glad.c)
target_include_directories(glad PUBLIC third_party/glad/include)

# GLM 是 header-only
add_library(glm INTERFACE)
target_include_directories(glm INTERFACE third_party/glm)

# stb_image
add_library(stb INTERFACE)
target_include_directories(stb INTERFACE third_party/stb)

# ---- 可选：Assimp（W9 之后再放开）----
# set(ASSIMP_BUILD_TESTS OFF CACHE BOOL "" FORCE)
# set(ASSIMP_BUILD_ASSIMP_TOOLS OFF CACHE BOOL "" FORCE)
# add_subdirectory(third_party/assimp)

# ---- 主程序 ----
file(GLOB SRCS CONFIGURE_DEPENDS src/*.cpp)
add_executable(app ${SRCS})

target_link_libraries(app PRIVATE glad glfw glm stb)

# 把 shaders/ 和 assets/ 复制到运行目录，省得到处找路径
add_custom_command(TARGET app POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
            ${CMAKE_SOURCE_DIR}/shaders $<TARGET_FILE_DIR:app>/shaders)
add_custom_command(TARGET app POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
            ${CMAKE_SOURCE_DIR}/assets  $<TARGET_FILE_DIR:app>/assets)

# MSVC：开启 UTF-8 与最高警告
if(MSVC)
    target_compile_options(app PRIVATE /W4 /utf-8)
else()
    target_compile_options(app PRIVATE -Wall -Wextra -Wpedantic)
endif()
```

构建命令：

```powershell
cmake -S . -B build
cmake --build build --config Release
.\build\Release\app.exe
```

### 3.5 第一个完整 `src/main.cpp`（橙色三角形，~150 行）

把下面这一份**完整代码**保存为 `src/main.cpp`。它已经包含：窗口创建、GL 加载、shader 编译错误检查、VAO/VBO、主循环、清理。

```cpp
// src/main.cpp  ——  Hello Triangle，C++20 完整可运行版
#include <glad/glad.h>
#include <GLFW/glfw3.h>

#include <iostream>
#include <string>
#include <string_view>
#include <format>     // C++20

// ---------- 顶点 / 片段着色器（直接内嵌字符串，方便第一次跑） ----------
constexpr std::string_view kVS = R"(
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aColor;
out vec3 vColor;
void main() {
    gl_Position = vec4(aPos, 1.0);
    vColor = aColor;
}
)";

constexpr std::string_view kFS = R"(
#version 330 core
in  vec3 vColor;
out vec4 FragColor;
void main() {
    FragColor = vec4(vColor, 1.0);
}
)";

// ---------- 工具：编译单个 shader + 错误检查 ----------
GLuint compileShader(GLenum type, std::string_view src) {
    GLuint id = glCreateShader(type);
    const char* p = src.data();
    GLint len = static_cast<GLint>(src.size());
    glShaderSource(id, 1, &p, &len);
    glCompileShader(id);

    GLint ok = 0;
    glGetShaderiv(id, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[1024]{};
        glGetShaderInfoLog(id, sizeof(log), nullptr, log);
        std::cerr << std::format("[Shader compile error] type={} :\n{}\n",
                                 (type == GL_VERTEX_SHADER ? "VS" : "FS"), log);
        std::abort();
    }
    return id;
}

// ---------- 工具：链接 program ----------
GLuint linkProgram(GLuint vs, GLuint fs) {
    GLuint prog = glCreateProgram();
    glAttachShader(prog, vs);
    glAttachShader(prog, fs);
    glLinkProgram(prog);
    GLint ok = 0;
    glGetProgramiv(prog, GL_LINK_STATUS, &ok);
    if (!ok) {
        char log[1024]{};
        glGetProgramInfoLog(prog, sizeof(log), nullptr, log);
        std::cerr << "[Program link error]\n" << log << "\n";
        std::abort();
    }
    glDeleteShader(vs);
    glDeleteShader(fs);
    return prog;
}

// ---------- 窗口尺寸变化回调 ----------
void onResize(GLFWwindow*, int w, int h) { glViewport(0, 0, w, h); }

int main() {
    // 1) GLFW 初始化
    if (!glfwInit()) { std::cerr << "glfwInit failed\n"; return -1; }
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
#ifdef __APPLE__
    glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE);
#endif

    GLFWwindow* win = glfwCreateWindow(1280, 720, "Hello Triangle (C++20)", nullptr, nullptr);
    if (!win) { glfwTerminate(); return -1; }
    glfwMakeContextCurrent(win);
    glfwSetFramebufferSizeCallback(win, onResize);

    // 2) GLAD 加载所有 GL 函数
    if (!gladLoadGLLoader(reinterpret_cast<GLADloadproc>(glfwGetProcAddress))) {
        std::cerr << "gladLoadGL failed\n"; return -1;
    }
    std::cout << std::format("GL: {}\n", reinterpret_cast<const char*>(glGetString(GL_VERSION)));

    // 3) 编译 shader + 链接
    GLuint vs = compileShader(GL_VERTEX_SHADER,   kVS);
    GLuint fs = compileShader(GL_FRAGMENT_SHADER, kFS);
    GLuint prog = linkProgram(vs, fs);

    // 4) 顶点数据：3 个顶点 = 3 位置 + 3 颜色
    constexpr float vertices[] = {
        // pos               color
        -0.5f, -0.5f, 0.0f,  1.0f, 0.5f, 0.0f, // 橙
         0.5f, -0.5f, 0.0f,  0.0f, 1.0f, 0.5f, // 绿
         0.0f,  0.5f, 0.0f,  0.5f, 0.0f, 1.0f, // 紫
    };
    GLuint VAO = 0, VBO = 0;
    glGenVertexArrays(1, &VAO);
    glGenBuffers(1, &VBO);
    glBindVertexArray(VAO);
    glBindBuffer(GL_ARRAY_BUFFER, VBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);

    // 解释 VBO 字节布局：每顶点 6 个 float
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float),
                          (void*)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);
    glBindVertexArray(0);

    // 5) 主循环
    while (!glfwWindowShouldClose(win)) {
        if (glfwGetKey(win, GLFW_KEY_ESCAPE) == GLFW_PRESS) glfwSetWindowShouldClose(win, true);

        glClearColor(0.10f, 0.12f, 0.15f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        glUseProgram(prog);
        glBindVertexArray(VAO);
        glDrawArrays(GL_TRIANGLES, 0, 3);

        glfwSwapBuffers(win);
        glfwPollEvents();
    }

    // 6) 清理
    glDeleteVertexArrays(1, &VAO);
    glDeleteBuffers(1, &VBO);
    glDeleteProgram(prog);
    glfwDestroyWindow(win);
    glfwTerminate();
    return 0;
}
```

> ✅ **W1~W2 验收**：跑出来一个**渐变色三角形**（顶点橙/绿/紫，光栅化自动插值），就算通过了。

### 3.6 学习里程碑：跑通 LearnOpenGL "Hello Triangle"

跟着 <https://learnopengl-cn.github.io/01%20Getting%20started/04%20Hello%20Triangle/> 把代码再读一遍，对照本文 §3.5 看哪些地方简化了。

> 💡 **第一周最关键的事不是看懂代码，而是把环境跑通**。卡住别硬扛，找视频对照（B 站搜"LearnOpenGL 配置"）。

### 3.7 常见配置错误速查

| 错误信息 | 原因 | 解法 |
|---|---|---|
| `cannot find -lGL` | Linux 没装 mesa | `sudo apt install libgl1-mesa-dev` |
| `glfw3.h: No such file` | submodule 没拉 | `git submodule update --init --recursive` |
| MSVC `error C7555: 指定初始化` | 没开 C++20 | CMake 加 `CMAKE_CXX_STANDARD 20` |
| 黑窗口、无三角形 | shader 编译失败但没看 log | 用 §3.5 的 `compileShader` 自带检查 |
| `glClear` 报 `GL_INVALID_OPERATION` | 没 `glfwMakeContextCurrent` | 在 GLAD load 之前调用 |

---

## 4. 向量与点：图形学的"原子"

📖 **虎书 Ch 2.4** + 💻 **LearnOpenGL "Transformations" 前半**

### 4.1 为什么图形学离不开向量？

图形学里所有东西都是**点和方向**：

- 模型上的一个顶点 = **点**（position）
- 光的方向 = **向量**（direction）
- 法线 = **向量**（normal）
- 颜色 (R,G,B) = **向量**（用 vec3 存）

学会向量运算，等于拿到了图形学的"工具箱"。

### 4.2 4 个必须背下来的向量运算

| 运算 | 公式 | 几何意义 | 代码（GLM） |
|---|---|---|---|
| **加法** | `a + b` | 平移 / 合成 | `a + b` |
| **数乘** | `k·a` | 缩放 / 反向 | `k * a` |
| **点积**（dot） | `a·b = \|a\|\|b\|cosθ` | **判断方向相似度**（光照核心） | `dot(a,b)` |
| **叉积**（cross） | `a×b` 垂直于 a、b | **求法线**（垂直方向） | `cross(a,b)` |

### 4.3 点积的核心应用：朗伯光照

```text
亮度 = max(0, dot(法线 N, 光线方向 L))
```

- N、L 同向 → dot=1 → **最亮**
- N、L 垂直 → dot=0 → **不受光**
- N、L 反向 → dot 为负 → **被遮挡**（取 0）

> 💡 **理解了点积，光照模型就理解了一半**。

### 4.4 必做练习

```cpp
#include <glm/glm.hpp>
#include <iostream>

int main() {
    glm::vec3 a(1, 0, 0), b(0, 1, 0);
    std::cout << "dot   = " << glm::dot(a, b) << "\n";   // 0
    std::cout << "cross = " << glm::cross(a, b).z << "\n"; // 1
    return 0;
}
```

把所有 4 个运算手算 + 用 GLM 验证一遍。

---

## 5. 矩阵与变换：让物体"动起来"

📖 **虎书 Ch 5 + Ch 6** + 💻 **LearnOpenGL "Transformations"**

### 5.1 为什么要矩阵？

矩阵是**"批量操作向量"的工具**。一个 4×4 矩阵能同时表达：

- **缩放（Scale）**
- **旋转（Rotate）**
- **平移（Translate）**

### 5.2 三大基本变换矩阵（4×4）

#### 缩放 S(sx, sy, sz)

```text
| sx  0  0  0 |
|  0 sy  0  0 |
|  0  0 sz  0 |
|  0  0  0  1 |
```

#### 平移 T(tx, ty, tz)

```text
| 1  0  0  tx |
| 0  1  0  ty |
| 0  0  1  tz |
| 0  0  0   1 |
```

#### 绕 Y 轴旋转 R_y(θ)

```text
|  cosθ  0  sinθ  0 |
|    0   1    0   0 |
| -sinθ  0  cosθ  0 |
|    0   0    0   1 |
```

### 5.3 顺序很重要！矩阵不是交换律

```text
先平移再旋转  ≠  先旋转再平移
```

OpenGL 默认列向量、左乘：

```text
最终矩阵 = T · R · S      (先 S，再 R，再 T)
变换点：v' = T · R · S · v
```

> 💡 **记忆口诀**：**SRT 顺序**——先 Scale，再 Rotate，最后 Translate。GLM 代码也是这个顺序写。

### 5.4 GLM 实战

```cpp
glm::mat4 model(1.0f);                              // 单位矩阵
model = glm::translate(model, glm::vec3(2,0,0));    // 平移
model = glm::rotate(model, glm::radians(45.0f),
                    glm::vec3(0,1,0));              // 绕 Y 转 45°
model = glm::scale(model, glm::vec3(0.5f));         // 缩小一半
```

> ⚠️ **GLM 写法是"反过来读"**：上面代码**实际执行顺序是 Scale → Rotate → Translate**（最后写的最先做）。

### 5.5 手算示例：一个点被变换 5 步

设原点 `P = (1, 2, 0, 1)`（齐次坐标 w=1），我们要：**缩小 0.5 倍 → 绕 Z 转 90° → 平移 (3, 0, 0)**。

```text
Step 1: 缩小
S · P =  | 0.5  0  0  0 |   | 1 |   | 0.5 |
         |  0 0.5  0  0 | · | 2 | = | 1.0 |
         |  0  0 0.5  0 |   | 0 |   | 0.0 |
         |  0  0  0  1 |   | 1 |   | 1.0 |

Step 2: 绕 Z 转 90° (cos90=0, sin90=1)
Rz · (S·P) = | 0 -1 0 0 |   | 0.5 |   | -1.0 |
              | 1  0 0 0 | · | 1.0 | = |  0.5 |
              | 0  0 1 0 |   | 0.0 |   |  0.0 |
              | 0  0 0 1 |   | 1.0 |   |  1.0 |

Step 3: 平移 (3,0,0)
T · (Rz·S·P) = | 1 0 0 3 |   | -1.0 |   |  2.0 |
               | 0 1 0 0 | · |  0.5 | = |  0.5 |
               | 0 0 1 0 |   |  0.0 |   |  0.0 |
               | 0 0 0 1 |   |  1.0 |   |  1.0 |

最终点 P' = (2.0, 0.5, 0.0)
```

验证：

```cpp
glm::vec4 P{1, 2, 0, 1};
glm::mat4 M(1.0f);
M = glm::translate(M, glm::vec3(3, 0, 0));
M = glm::rotate(M, glm::radians(90.0f), glm::vec3(0, 0, 1));
M = glm::scale(M, glm::vec3(0.5f));
auto P2 = M * P;          // 输出 (2.0, 0.5, 0.0, 1.0) ✅
```

> 💡 **亲手算一遍**，你就永远不会忘记"为什么 GLM 要反着写"。

---

## 6. 三大空间变换：模型 → 世界 → 视图 → 投影

📖 **虎书 Ch 7** + 💻 **LearnOpenGL "Coordinate Systems"** ⭐⭐⭐⭐⭐

> 这是图形学最核心、最容易让新人迷茫的一节，**务必反复看**。

### 6.1 为什么有这么多空间？

把"显示一个 3D 模型到屏幕"拆成 5 步：

```text
[模型空间]  ──Model──→  [世界空间]  ──View──→  [视图空间]
   ↓                                              │
   ↓ "茶杯自己的坐标系"                        Projection
   ↓                                              ↓
   ↓                                          [裁剪空间]
                                                  ↓
                                              透视除法
                                                  ↓
                                              [NDC -1~1]
                                                  ↓
                                                视口
                                                  ↓
                                            [屏幕坐标]
```

每个空间的意义：

| 空间 | 一句话定义 | 类比 |
|---|---|---|
| **模型空间** | 物体自己的坐标系 | 茶杯设计师只管杯子本身 |
| **世界空间** | 整个场景共用的坐标系 | 把茶杯**放到桌上某位置** |
| **视图空间** | 以摄像机为原点 | 你**站着看**这个桌子 |
| **裁剪空间** | 透视 / 正交投影后 | 决定"看得见看不见" |
| **NDC** | 归一化到 [-1,1]³ | 标准化方块 |
| **屏幕空间** | 像素坐标 | 显示器上的位置 |

### 6.2 MVP 矩阵（最重要的 3 个矩阵）

```text
裁剪坐标 = Projection · View · Model · 模型坐标
                ↑          ↑       ↑
              透视/正交   摄像机   物体自身变换
```

着色器代码：

```glsl
gl_Position = projection * view * model * vec4(aPos, 1.0);
```

### 6.3 投影矩阵：透视 vs 正交

| 类型 | 效果 | 适用 | GLM API |
|---|---|---|---|
| **透视投影** | 近大远小（真实） | 第一/第三人称游戏 | `glm::perspective(fov, aspect, near, far)` |
| **正交投影** | 平行线永远平行 | UI、CAD、2D 游戏 | `glm::ortho(left, right, bottom, top, near, far)` |

```cpp
glm::mat4 proj = glm::perspective(glm::radians(45.0f),
                                  width/(float)height,
                                  0.1f, 100.0f);
```

### 6.4 透视矩阵从哪里来？（推导简略版）

透视投影的本质：**远处物体在屏幕上变小**。数学上是让 (x, y, z) 除以一个与 z 成正比的量：`x' = x/(-z)`。

通过齐次坐标的技巧：把这个除法延后到"透视除法"一步，所以透视矩阵会让 `w' = -z`。其反着 Z 轴倒下来的三角形被重新映射到 [-1,1] 正方体：

```text
输入：fov（视野）、aspect（宽高比）、near、far
输出矩阵（OpenGL 右手系、NDC 在 [-1,1]）：

              | f/aspect   0          0                 0           |
  P_persp =   |    0       f          0                 0           |
              |    0       0   (n+f)/(n-f)   (2*n*f)/(n-f)         |
              |    0       0         -1                 0           |

  其中 f = 1 / tan(fov / 2)
```

你**不需要背这个矩阵**，只需知道：

- **fov 越大** → 东西看起来越小（鱼眼镶嵌感）
- **near/far 比值越大** → z-fighting 越严重（建议 `near=0.1, far=100` 起步）
- 透视除法后 `clip.xyz / clip.w`，w 正是原本的 -z

### 6.5 必做练习

完成 LearnOpenGL **"坐标系统"** 这一节，**屏幕上出现 10 个会转的彩色立方体** —— 这是图形学的"成人礼"。

```cpp
// 关键代码（节选）
for (int i = 0; i < 10; ++i) {
    glm::mat4 model(1.0f);
    model = glm::translate(model, cubePositions[i]);
    model = glm::rotate(model, (float)glfwGetTime() * glm::radians(50.0f),
                        glm::vec3(0.5f, 1.0f, 0.0f));
    shader.setMat4("model", model);
    glDrawArrays(GL_TRIANGLES, 0, 36);
}
```

### 6.6 W4 验收作品：完整可运行的 main.cpp

> 依赖 [§C1 Shader 类](#c1-shader-类完整源码)。把下面代码贴进 `src/main.cpp` 即可看到 10 个转动立方体。

```cpp
// src/main.cpp — W4 验收：10 个旋转立方体（C++20）
#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>

#include "Shader.hpp"
#include <array>
#include <numbers>
#include <iostream>

// 36 个顶点的立方体（位置 + 颜色）
constexpr float kCube[] = {
    // pos              color
    -.5f,-.5f,-.5f,  1,0,0,   .5f,-.5f,-.5f,  1,0,0,   .5f, .5f,-.5f,  1,0,0,
     .5f, .5f,-.5f,  1,0,0,  -.5f, .5f,-.5f,  1,0,0,  -.5f,-.5f,-.5f,  1,0,0,

    -.5f,-.5f, .5f,  0,1,0,   .5f,-.5f, .5f,  0,1,0,   .5f, .5f, .5f,  0,1,0,
     .5f, .5f, .5f,  0,1,0,  -.5f, .5f, .5f,  0,1,0,  -.5f,-.5f, .5f,  0,1,0,

    -.5f, .5f, .5f,  0,0,1,  -.5f, .5f,-.5f,  0,0,1,  -.5f,-.5f,-.5f,  0,0,1,
    -.5f,-.5f,-.5f,  0,0,1,  -.5f,-.5f, .5f,  0,0,1,  -.5f, .5f, .5f,  0,0,1,

     .5f, .5f, .5f,  1,1,0,   .5f, .5f,-.5f,  1,1,0,   .5f,-.5f,-.5f,  1,1,0,
     .5f,-.5f,-.5f,  1,1,0,   .5f,-.5f, .5f,  1,1,0,   .5f, .5f, .5f,  1,1,0,

    -.5f,-.5f,-.5f,  1,0,1,   .5f,-.5f,-.5f,  1,0,1,   .5f,-.5f, .5f,  1,0,1,
     .5f,-.5f, .5f,  1,0,1,  -.5f,-.5f, .5f,  1,0,1,  -.5f,-.5f,-.5f,  1,0,1,

    -.5f, .5f,-.5f,  0,1,1,   .5f, .5f,-.5f,  0,1,1,   .5f, .5f, .5f,  0,1,1,
     .5f, .5f, .5f,  0,1,1,  -.5f, .5f, .5f,  0,1,1,  -.5f, .5f,-.5f,  0,1,1,
};

constexpr std::array<glm::vec3, 10> kPositions = {{
    { 0.0f,  0.0f,  0.0f}, { 2.0f,  5.0f,-15.0f}, {-1.5f, -2.2f, -2.5f},
    {-3.8f, -2.0f,-12.3f}, { 2.4f, -0.4f, -3.5f}, {-1.7f,  3.0f, -7.5f},
    { 1.3f, -2.0f, -2.5f}, { 1.5f,  2.0f, -2.5f}, { 1.5f,  0.2f, -1.5f},
    {-1.3f,  1.0f, -1.5f},
}};

int main() {
    glfwInit();
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
    auto* win = glfwCreateWindow(1280, 720, "10 Cubes", nullptr, nullptr);
    glfwMakeContextCurrent(win);
    gladLoadGLLoader((GLADloadproc)glfwGetProcAddress);
    glEnable(GL_DEPTH_TEST);                          // ✌️ 必须开

    Shader sh("shaders/cube.vert", "shaders/cube.frag");

    GLuint VAO=0, VBO=0;
    glGenVertexArrays(1,&VAO); glGenBuffers(1,&VBO);
    glBindVertexArray(VAO);
    glBindBuffer(GL_ARRAY_BUFFER, VBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(kCube), kCube, GL_STATIC_DRAW);
    glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,6*sizeof(float),(void*)0);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,6*sizeof(float),
                          (void*)(3*sizeof(float)));
    glEnableVertexAttribArray(1);

    while (!glfwWindowShouldClose(win)) {
        if (glfwGetKey(win, GLFW_KEY_ESCAPE) == GLFW_PRESS)
            glfwSetWindowShouldClose(win, true);

        glClearColor(0.05f, 0.07f, 0.10f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        const float t = static_cast<float>(glfwGetTime());
        glm::mat4 view = glm::translate(glm::mat4(1.0f), glm::vec3(0,0,-12));
        glm::mat4 proj = glm::perspective(glm::radians(45.0f),
                                          1280.0f/720.0f, 0.1f, 100.0f);
        sh.use();
        sh.setMat4("view", view);
        sh.setMat4("projection", proj);

        glBindVertexArray(VAO);
        for (std::size_t i = 0; i < kPositions.size(); ++i) {
            glm::mat4 model(1.0f);
            model = glm::translate(model, kPositions[i]);
            float angle = 20.0f * static_cast<float>(i) + t * 50.0f;
            model = glm::rotate(model, glm::radians(angle),
                                glm::vec3(0.5f, 1.0f, 0.3f));
            sh.setMat4("model", model);
            glDrawArrays(GL_TRIANGLES, 0, 36);
        }
        glfwSwapBuffers(win);
        glfwPollEvents();
    }
    glfwTerminate();
}
```

```glsl
// shaders/cube.vert
#version 330 core
layout(location=0) in vec3 aPos;
layout(location=1) in vec3 aColor;
out vec3 vColor;
uniform mat4 model, view, projection;
void main() {
    gl_Position = projection * view * model * vec4(aPos, 1.0);
    vColor = aColor;
}
```

```glsl
// shaders/cube.frag
#version 330 core
in  vec3 vColor;
out vec4 FragColor;
void main() { FragColor = vec4(vColor, 1.0); }
```

---

## 7. 齐次坐标：为什么矩阵是 4×4？

📖 **虎书 Ch 6.3**

### 7.1 一句话理解

> **加一个第 4 维 w，是为了把"平移"也变成矩阵乘法**。

3×3 矩阵能做缩放、旋转，但**做不了平移**（平移是加法）。把点扩展为 (x, y, z, 1)：

```text
| 1 0 0 tx |   | x |   | x + tx |
| 0 1 0 ty | · | y | = | y + ty |
| 0 0 1 tz |   | z |   | z + tz |
| 0 0 0  1 |   | 1 |   |   1    |
```

平移 = 矩阵乘法 ✅

### 7.2 点 vs 向量的区别

| 类型 | w | 例子 | 受平移影响吗？ |
|---|---|---|---|
| **点（Point）** | 1 | `vec4(pos, 1.0)` | ✅ 受 |
| **向量（Vector）** | 0 | `vec4(dir, 0.0)` | ❌ 不受（w=0 把平移列乘掉） |

> 💡 **着色器里一个超常见的坑**：传法线时如果 w=1 会被错误平移！必须用 `vec4(normal, 0.0)`，或干脆只乘上 3×3 部分。

---

## 8. 管线全貌：从顶点到像素的 6 步

📖 **虎书 Ch 8** + 💻 **LearnOpenGL "Hello Triangle" 开篇图**

```text
[CPU 端]                          [GPU 端]
顶点数据 ──→ 顶点着色器 ──→ 图元装配 ──→ 光栅化 ──→ 片段着色器 ──→ 测试与混合 ──→ 屏幕
 (你给)    (你写 GLSL)   (硬件做)    (硬件做)   (你写 GLSL)    (深度/模板)
```

| 阶段 | 输入 | 输出 | 你写代码吗？ |
|---|---|---|---|
| Vertex Shader | 顶点属性（位置、UV、法线…） | `gl_Position` + 自定义 out | ✅ |
| 图元装配 | 顶点 | 三角形 | ❌ |
| 光栅化 | 三角形 | 一堆片段（潜在像素） | ❌ |
| Fragment Shader | 插值后的属性 | `FragColor` | ✅ |
| 测试 & 混合 | 片段 + 已有像素 | 最终像素 | 配置 |

> 💡 **关键认知**：你能控制的**只有顶点着色器和片段着色器**，其他都是硬件固定流水线。**学图形学 = 学怎么写好这两个着色器**。

---

## 9. 第一个三角形：搞懂 VAO / VBO / EBO

💻 **LearnOpenGL "Hello Triangle" + "Shaders"** ⭐⭐⭐⭐⭐

### 9.1 三个对象的分工

| 名称 | 全称 | 作用 | 类比 |
|---|---|---|---|
| **VBO** | Vertex Buffer Object | **存顶点数据** 的显存块 | 一袋子原料 |
| **VAO** | Vertex Array Object | **记录如何解释 VBO** 的状态 | 配方说明书 |
| **EBO** | Element Buffer Object | 存**索引**（三角形用哪几个顶点） | 装配顺序表 |

### 9.2 标准三件套代码

```cpp
float vertices[] = {
    // 位置        // 颜色
    -0.5f,-0.5f,0, 1,0,0,
     0.5f,-0.5f,0, 0,1,0,
     0.0f, 0.5f,0, 0,0,1,
};

GLuint VAO, VBO;
glGenVertexArrays(1, &VAO);
glGenBuffers(1, &VBO);

glBindVertexArray(VAO);                                    // ① 绑 VAO
glBindBuffer(GL_ARRAY_BUFFER, VBO);                        // ② 绑 VBO
glBufferData(GL_ARRAY_BUFFER, sizeof(vertices),
             vertices, GL_STATIC_DRAW);                    // ③ 上传数据

// ④ 告诉 OpenGL 怎么解释这些字节
glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE,
                      6 * sizeof(float), (void*)0);
glEnableVertexAttribArray(0);
glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE,
                      6 * sizeof(float), (void*)(3*sizeof(float)));
glEnableVertexAttribArray(1);

glBindVertexArray(0);                                      // 解绑
```

### 9.3 必做练习

1. 跟着 LearnOpenGL 画出三角形（橘色）
2. 把它扩展成 **彩色三角形**（每个顶点不同颜色，看着色器自动插值）
3. 用 EBO 画一个矩形（4 顶点 + 6 索引）

> 💡 **里程碑**：能独立写出"绘制矩形 + 顶点颜色插值"的代码，VAO/VBO/EBO 就过关了。

---

## 10. 着色器入门：GLSL 你必须懂的 5 件事

💻 **LearnOpenGL "Shaders"** ⭐⭐⭐⭐⭐

### 10.1 着色器是什么

> **着色器 = 在 GPU 上跑的 C 风格小程序**。Vertex Shader 处理每个顶点，Fragment Shader 处理每个像素。

### 10.2 最简顶点着色器 + 片段着色器

```glsl
// === Vertex Shader ===
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aColor;
out vec3 vColor;            // 传给 fragment
uniform mat4 mvp;           // CPU 传入的 MVP 矩阵
void main() {
    gl_Position = mvp * vec4(aPos, 1.0);
    vColor = aColor;
}
```

```glsl
// === Fragment Shader ===
#version 330 core
in vec3 vColor;             // 来自 vertex（已自动插值）
out vec4 FragColor;
void main() {
    FragColor = vec4(vColor, 1.0);
}
```

### 10.3 必懂的 5 个关键字

| 关键字 | 含义 | 何时用 |
|---|---|---|
| `in` | 输入 | 顶点属性 / 上一阶段输出 |
| `out` | 输出 | 传给下一阶段 |
| `uniform` | CPU 端传入的"常量" | 矩阵、时间、颜色 |
| `layout(location=N)` | 指定属性槽位 | 配合 VAO |
| `gl_Position` | 内置：顶点裁剪坐标 | **必须赋值** |

### 10.4 数据流向小图

```text
[CPU]
  │ glUniform...()   ← uniform
  │ VBO 顶点数据     ← in (location=0,1...)
  ▼
[Vertex Shader]
  │ out vec3 vColor;
  ▼
[光栅化插值]
  │ in vec3 vColor;
  ▼
[Fragment Shader]
  │ out vec4 FragColor;
  ▼
[屏幕像素]
```

### 10.5 必做练习

- 写一个**让三角形随时间变色**的 fragment shader（用 `uniform float u_time`）
- 写一个**让顶点位置随时间波动**的 vertex shader（`gl_Position.y += sin(u_time)`）

---

## 11. 光栅化与深度测试：像素是怎么"诞生"的

📖 **虎书 Ch 8.1 + Ch 9** + 💻 **LearnOpenGL "Depth Testing"**

### 11.1 光栅化做了什么

```text
三角形（3 个顶点）
   │  扫描线算法
   ▼
判断每个像素是否在三角形内
   │  对在内部的像素：
   ▼
插值出该像素的属性（颜色、UV、法线…）
   │
   ▼
送进 Fragment Shader
```

> 💡 这就是为什么你 vertex shader 写一个 `out vec3 vColor`，fragment shader 收到的是**插值后的 vColor**——光栅化阶段做了重心坐标插值。

#### 重心坐标插值（Barycentric Interpolation）

任意三角形内一点 `P` 可表示为顶点 `A B C` 的加权和：

```text
P = α·A + β·B + γ·C　　（α + β + γ = 1，且都 ≥ 0）
```

其中 α、β、γ 是"顶点对面子三角形面积 / 总面积"。颜色、UV、法线都按同样权重插值：

```text
color(P) = α·color(A) + β·color(B) + γ·color(C)
```

> ⚠️ **透视正确插值（Perspective-correct）**：OpenGL 默认在屏幕空间插值时会除以 w，否则贴图越远越失真（主机游戏里地面接缝出现折叠 = 忘开）。GLSL 默认就是透视正确，除非用 `noperspective` 关键字。

### 11.2 深度测试（Z-Buffer）

**问题**：场景里有两个物体重叠，怎么知道谁挡住谁？

**答案**：每个像素保存一个 **深度值（z）**，新片段画上来时比一下深度：

```text
if (新片段.z < 已存深度) {
    覆盖颜色和深度;
} else {
    丢弃;          // 被挡住了
}
```

### 11.3 开启 Z-Buffer

```cpp
glEnable(GL_DEPTH_TEST);                               // 必须开
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);    // 每帧清空
```

### 11.4 必做练习

LearnOpenGL **"Coordinate Systems"** 那 10 个旋转立方体——**关掉深度测试看看**会发生什么（前后穿插错乱），再打开。**亲眼看到 Z-Buffer 在干活**。

---

## 12. 纹理映射：把图片"贴"到模型上

📖 **虎书 Ch 11** + 💻 **LearnOpenGL "Textures"** ⭐⭐⭐⭐⭐

### 12.1 核心概念：UV 坐标

每个顶点除了位置，还要一个 **UV 坐标 (u,v) ∈ [0,1]²**，表示"用纹理图的哪一点"。

```text
纹理图（图片）              模型表面
v=1 ┌────┐                     ┌────┐
    │    │   ─映射→            │    │
v=0 └────┘                     └────┘
    u=0  u=1
```

### 12.2 OpenGL 纹理代码模板

```cpp
GLuint tex;
glGenTextures(1, &tex);
glBindTexture(GL_TEXTURE_2D, tex);

// 包装方式 + 过滤
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);

// stb_image 加载图片
int w, h, ch;
stbi_set_flip_vertically_on_load(true);     // ⚠️ Y 轴 flip
unsigned char* data = stbi_load("brick.png", &w, &h, &ch, 0);
glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0,
             GL_RGB, GL_UNSIGNED_BYTE, data);
glGenerateMipmap(GL_TEXTURE_2D);
stbi_image_free(data);
```

### 12.3 着色器里采样

```glsl
in vec2 vUV;
uniform sampler2D uTex;
out vec4 FragColor;
void main() {
    FragColor = texture(uTex, vUV);
}
```

### 12.4 三个必懂概念

| 概念 | 解决什么 | 关键参数 |
|---|---|---|
| **Wrap（环绕方式）** | UV 超出 [0,1] 怎么办 | `GL_REPEAT` / `GL_CLAMP_TO_EDGE` |
| **Filter（过滤）** | 像素和纹素不对齐 | `GL_NEAREST`（像素风）/ `GL_LINEAR`（平滑） |
| **Mipmap** | 远处贴图采样失真 | `glGenerateMipmap` |

### 12.5 必做练习

完成 LearnOpenGL **"纹理"** 章节，画出 **"木箱 + 笑脸"双纹理混合矩形**。

### 12.6 完整可运行：双纹理矩形 main.cpp

> 用了 `Shader` 类（见 [§C1](#c1-shader-类完整源码)） 与 `Texture` 工具（见 [§C3](#c3-texture-工具完整源码)）。`shaders/tex.vert`、`shaders/tex.frag` 与资源准备奷7-§C3.

```cpp
// src/main.cpp —— 双纹理混合矩形（C++20）
#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include "Shader.hpp"
#include "Texture.hpp"
#include <iostream>

int main() {
    glfwInit();
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
    auto* win = glfwCreateWindow(800, 600, "DualTex", nullptr, nullptr);
    glfwMakeContextCurrent(win);
    gladLoadGLLoader((GLADloadproc)glfwGetProcAddress);

    Shader sh("shaders/tex.vert", "shaders/tex.frag");
    GLuint texWood  = loadTexture2D("assets/textures/wall.jpg");
    GLuint texFace  = loadTexture2D("assets/textures/awesomeface.png", /*flipY=*/true);

    constexpr float V[] = {
        // pos          uv
         0.5f, 0.5f,0,  1,1,
         0.5f,-0.5f,0,  1,0,
        -0.5f,-0.5f,0,  0,0,
        -0.5f, 0.5f,0,  0,1,
    };
    constexpr unsigned I[] = { 0,1,3, 1,2,3 };

    GLuint VAO=0, VBO=0, EBO=0;
    glGenVertexArrays(1,&VAO); glGenBuffers(1,&VBO); glGenBuffers(1,&EBO);
    glBindVertexArray(VAO);
    glBindBuffer(GL_ARRAY_BUFFER, VBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(V), V, GL_STATIC_DRAW);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(I), I, GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5*sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5*sizeof(float),
                          (void*)(3*sizeof(float)));
    glEnableVertexAttribArray(1);

    sh.use();
    sh.setInt("uTex0", 0);
    sh.setInt("uTex1", 1);

    while (!glfwWindowShouldClose(win)) {
        if (glfwGetKey(win, GLFW_KEY_ESCAPE) == GLFW_PRESS)
            glfwSetWindowShouldClose(win, true);

        glClearColor(0.1f,0.1f,0.12f,1); glClear(GL_COLOR_BUFFER_BIT);

        glActiveTexture(GL_TEXTURE0); glBindTexture(GL_TEXTURE_2D, texWood);
        glActiveTexture(GL_TEXTURE1); glBindTexture(GL_TEXTURE_2D, texFace);

        sh.use();
        glBindVertexArray(VAO);
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, 0);

        glfwSwapBuffers(win);
        glfwPollEvents();
    }
    glfwTerminate();
}
```

```glsl
// shaders/tex.vert
#version 330 core
layout(location=0) in vec3 aPos;
layout(location=1) in vec2 aUV;
out vec2 vUV;
void main() {
    gl_Position = vec4(aPos, 1.0);
    vUV = aUV;
}
```

```glsl
// shaders/tex.frag
#version 330 core
in  vec2 vUV;
out vec4 FragColor;
uniform sampler2D uTex0;
uniform sampler2D uTex1;
void main() {
    vec4 c0 = texture(uTex0, vUV);
    vec4 c1 = texture(uTex1, vUV);
    FragColor = mix(c0, c1, 0.3);    // 30% 笑脸·70% 木纹
}
```

---

## 13. 光照基础：Phong / Blinn-Phong 模型

📖 **虎书 Ch 10** + 💻 **LearnOpenGL "Basic Lighting"** ⭐⭐⭐⭐⭐

### 13.1 Phong 三分量

> **最终颜色 = 环境光 + 漫反射 + 镜面反射**

```text
I = I_ambient + I_diffuse + I_specular
```

| 分量 | 公式 | 直觉 |
|---|---|---|
| **Ambient（环境光）** | `ka · Light` | 模拟全局漫反射，给个最暗底色 |
| **Diffuse（漫反射）** | `kd · max(0, N·L) · Light` | **朗伯定律**，糙面反射 |
| **Specular（镜面）** | `ks · max(0, R·V)^n · Light` | 高光斑，n 越大越锐 |

符号：
- N = 法线，L = 光线方向，R = 反射方向，V = 视线方向
- ka/kd/ks = 材质三系数
- n = 高光指数（光泽度）

### 13.2 Blinn-Phong（更现代）

把 `R·V` 换成 `N·H`，H 是半程向量 `H = normalize(L+V)`：

```text
specular = ks · max(0, N·H)^n · Light
```

**优点**：高光更柔和、更物理正确，性能也略好。**LearnOpenGL 进阶章节用的就是它**。

### 13.3 GLSL 实现（Phong）

```glsl
in vec3 vNormal;     // 世界空间法线
in vec3 vFragPos;    // 世界空间位置
uniform vec3 lightPos;
uniform vec3 viewPos;
uniform vec3 lightColor;
uniform vec3 objectColor;

void main() {
    // ambient
    vec3 ambient = 0.1 * lightColor;

    // diffuse
    vec3 N = normalize(vNormal);
    vec3 L = normalize(lightPos - vFragPos);
    float diff = max(dot(N, L), 0.0);
    vec3 diffuse = diff * lightColor;

    // specular (Blinn-Phong)
    vec3 V = normalize(viewPos - vFragPos);
    vec3 H = normalize(L + V);
    float spec = pow(max(dot(N, H), 0.0), 32.0);
    vec3 specular = 0.5 * spec * lightColor;

    vec3 result = (ambient + diffuse + specular) * objectColor;
    FragColor = vec4(result, 1.0);
}
```

### 13.4 必做练习

- LearnOpenGL "基础光照"完整跑一遍
- 调 `n`（高光指数）从 8 → 256，观察高光从软变硬
- 关掉 ambient 看看暗面有多黑（理解为什么需要环境光）

> 💡 **重大里程碑**：能写出 Blinn-Phong = 真正进入"3D 渲染"门槛。

### 13.5 完整可运行：Blinn-Phong 光照的立方体

> 依赖 [§C1](#c1-shader-类完整源码) + [§C2](#c2-camera-类完整源码)。

```cpp
// src/main.cpp — W6 ：Blinn-Phong 光照 + 可控相机
#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include "Shader.hpp"
#include "Camera.hpp"
#include <iostream>

// 含法线的立方体 (36 顶点 × (3pos + 3normal))
constexpr float kCubeN[] = {
    // 面 -Z
    -.5f,-.5f,-.5f,  0,0,-1,   .5f,-.5f,-.5f, 0,0,-1,   .5f, .5f,-.5f, 0,0,-1,
     .5f, .5f,-.5f,  0,0,-1,  -.5f, .5f,-.5f, 0,0,-1,  -.5f,-.5f,-.5f, 0,0,-1,
    // 面 +Z
    -.5f,-.5f, .5f,  0,0, 1,   .5f,-.5f, .5f, 0,0, 1,   .5f, .5f, .5f, 0,0, 1,
     .5f, .5f, .5f,  0,0, 1,  -.5f, .5f, .5f, 0,0, 1,  -.5f,-.5f, .5f, 0,0, 1,
    // 面 -X
    -.5f, .5f, .5f, -1,0,0,   -.5f, .5f,-.5f,-1,0,0,  -.5f,-.5f,-.5f,-1,0,0,
    -.5f,-.5f,-.5f, -1,0,0,   -.5f,-.5f, .5f,-1,0,0,  -.5f, .5f, .5f,-1,0,0,
    // 面 +X
     .5f, .5f, .5f,  1,0,0,    .5f, .5f,-.5f, 1,0,0,   .5f,-.5f,-.5f, 1,0,0,
     .5f,-.5f,-.5f,  1,0,0,    .5f,-.5f, .5f, 1,0,0,   .5f, .5f, .5f, 1,0,0,
    // 面 -Y
    -.5f,-.5f,-.5f,  0,-1,0,   .5f,-.5f,-.5f, 0,-1,0,  .5f,-.5f, .5f, 0,-1,0,
     .5f,-.5f, .5f,  0,-1,0,  -.5f,-.5f, .5f, 0,-1,0, -.5f,-.5f,-.5f, 0,-1,0,
    // 面 +Y
    -.5f, .5f,-.5f,  0,1,0,    .5f, .5f,-.5f, 0,1,0,   .5f, .5f, .5f, 0,1,0,
     .5f, .5f, .5f,  0,1,0,   -.5f, .5f, .5f, 0,1,0,  -.5f, .5f,-.5f, 0,1,0,
};

Camera g_cam{glm::vec3(0,0,3)};
float g_lastX = 640, g_lastY = 360;
bool  g_firstMouse = true;
float g_dt = 0.0f, g_last = 0.0f;

void mouseCb(GLFWwindow*, double x, double y) {
    if (g_firstMouse) { g_lastX=(float)x; g_lastY=(float)y; g_firstMouse=false; }
    float dx = (float)x - g_lastX, dy = g_lastY - (float)y;
    g_lastX = (float)x; g_lastY = (float)y;
    g_cam.processMouse(dx, dy);
}
void scrollCb(GLFWwindow*, double, double yoff) { g_cam.processScroll((float)yoff); }

int main() {
    glfwInit();
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
    auto* win = glfwCreateWindow(1280, 720, "Blinn-Phong", nullptr, nullptr);
    glfwMakeContextCurrent(win);
    glfwSetInputMode(win, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
    glfwSetCursorPosCallback(win, mouseCb);
    glfwSetScrollCallback(win, scrollCb);
    gladLoadGLLoader((GLADloadproc)glfwGetProcAddress);
    glEnable(GL_DEPTH_TEST);

    Shader objSh("shaders/lit.vert", "shaders/lit.frag");
    Shader lampSh("shaders/lit.vert", "shaders/lamp.frag");

    GLuint VAO=0, VBO=0;
    glGenVertexArrays(1,&VAO); glGenBuffers(1,&VBO);
    glBindVertexArray(VAO);
    glBindBuffer(GL_ARRAY_BUFFER, VBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(kCubeN), kCubeN, GL_STATIC_DRAW);
    glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,6*sizeof(float),(void*)0);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,6*sizeof(float),
                          (void*)(3*sizeof(float)));
    glEnableVertexAttribArray(1);

    glm::vec3 lightPos(1.2f, 1.0f, 2.0f);

    while (!glfwWindowShouldClose(win)) {
        float now = (float)glfwGetTime();
        g_dt = now - g_last; g_last = now;

        if (glfwGetKey(win, GLFW_KEY_ESCAPE) == GLFW_PRESS)
            glfwSetWindowShouldClose(win, true);
        if (glfwGetKey(win, GLFW_KEY_W) == GLFW_PRESS) g_cam.processKey(Camera::FORWARD,  g_dt);
        if (glfwGetKey(win, GLFW_KEY_S) == GLFW_PRESS) g_cam.processKey(Camera::BACKWARD, g_dt);
        if (glfwGetKey(win, GLFW_KEY_A) == GLFW_PRESS) g_cam.processKey(Camera::LEFT,     g_dt);
        if (glfwGetKey(win, GLFW_KEY_D) == GLFW_PRESS) g_cam.processKey(Camera::RIGHT,    g_dt);

        glClearColor(0.05f,0.06f,0.08f,1);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        glm::mat4 view = g_cam.viewMatrix();
        glm::mat4 proj = glm::perspective(glm::radians(g_cam.fov()),
                                          1280.f/720.f, 0.1f, 100.f);

        // 物体
        objSh.use();
        objSh.setVec3("objectColor", {1.0f, 0.5f, 0.31f});
        objSh.setVec3("lightColor",  {1.0f, 1.0f, 1.0f});
        objSh.setVec3("lightPos",    lightPos);
        objSh.setVec3("viewPos",     g_cam.position());
        objSh.setMat4("model", glm::mat4(1.0f));
        objSh.setMat4("view",  view);
        objSh.setMat4("projection", proj);
        glBindVertexArray(VAO);
        glDrawArrays(GL_TRIANGLES, 0, 36);

        // 灯泲本体
        lampSh.use();
        glm::mat4 m(1.0f);
        m = glm::translate(m, lightPos);
        m = glm::scale(m, glm::vec3(0.2f));
        lampSh.setMat4("model", m);
        lampSh.setMat4("view", view);
        lampSh.setMat4("projection", proj);
        glDrawArrays(GL_TRIANGLES, 0, 36);

        glfwSwapBuffers(win);
        glfwPollEvents();
    }
    glfwTerminate();
}
```

```glsl
// shaders/lit.vert
#version 330 core
layout(location=0) in vec3 aPos;
layout(location=1) in vec3 aNormal;
out vec3 vNormal;
out vec3 vFragPos;
uniform mat4 model, view, projection;
void main() {
    vFragPos = vec3(model * vec4(aPos, 1.0));
    vNormal  = mat3(transpose(inverse(model))) * aNormal;   // 法线矩阵
    gl_Position = projection * view * vec4(vFragPos, 1.0);
}
```

```glsl
// shaders/lit.frag (Blinn-Phong)
#version 330 core
in  vec3 vNormal;
in  vec3 vFragPos;
out vec4 FragColor;
uniform vec3 objectColor, lightColor, lightPos, viewPos;
void main() {
    vec3 ambient = 0.15 * lightColor;
    vec3 N = normalize(vNormal);
    vec3 L = normalize(lightPos - vFragPos);
    float diff = max(dot(N, L), 0.0);
    vec3 diffuse = diff * lightColor;
    vec3 V = normalize(viewPos - vFragPos);
    vec3 H = normalize(L + V);
    float spec = pow(max(dot(N, H), 0.0), 64.0);
    vec3 specular = 0.5 * spec * lightColor;
    FragColor = vec4((ambient + diffuse + specular) * objectColor, 1.0);
}
```

```glsl
// shaders/lamp.frag
#version 330 core
out vec4 FragColor;
void main() { FragColor = vec4(1.0); }
```

---

## 14. 光源类型：方向光 / 点光源 / 聚光灯

💻 **LearnOpenGL "Light Casters" + "Multiple Lights"**

### 14.1 三种光源对比

| 类型 | 物理模型 | 例子 | 关键参数 |
|---|---|---|---|
| **方向光（Directional）** | 平行光、无衰减 | 太阳光 | 方向 |
| **点光源（Point）** | 从一点发散、有衰减 | 灯泡 | 位置 + 衰减系数 |
| **聚光灯（Spot）** | 圆锥范围 | 手电筒 | 位置 + 方向 + 内/外角度 |

### 14.2 衰减公式（点光源核心）

```text
attenuation = 1.0 / (constant + linear·d + quadratic·d²)
```

LearnOpenGL 给了一个**距离-参数对照表**，照抄即可。

### 14.3 多光源模板

```glsl
vec3 result = CalcDirLight(dirLight, N, V);
for (int i = 0; i < NR_POINT_LIGHTS; ++i)
    result += CalcPointLight(pointLights[i], N, vFragPos, V);
result += CalcSpotLight(spotLight, N, vFragPos, V);
FragColor = vec4(result, 1.0);
```

### 14.4 必做练习

完成 LearnOpenGL **"多光源"** demo —— 1 方向光 + 4 点光源 + 1 手电筒，看到一个**夜晚街道感**的场景。

### 14.5 多光源 fragment shader 完整版

```glsl
// shaders/multi.frag — 1 方向光 + 4 点光 + 1 聚光灯
#version 330 core
out vec4 FragColor;
in  vec3 vNormal;
in  vec3 vFragPos;
in  vec2 vUV;

struct Material {
    sampler2D diffuse;
    sampler2D specular;
    float shininess;
};

struct DirLight {
    vec3 direction;
    vec3 ambient, diffuse, specular;
};

struct PointLight {
    vec3 position;
    float constant, linear, quadratic;
    vec3 ambient, diffuse, specular;
};

struct SpotLight {
    vec3 position, direction;
    float cutOff, outerCutOff;
    float constant, linear, quadratic;
    vec3 ambient, diffuse, specular;
};

#define NR_POINT 4
uniform vec3       viewPos;
uniform Material   material;
uniform DirLight   dirLight;
uniform PointLight pointLights[NR_POINT];
uniform SpotLight  spotLight;

vec3 calcDir(DirLight L, vec3 N, vec3 V);
vec3 calcPoint(PointLight L, vec3 N, vec3 P, vec3 V);
vec3 calcSpot(SpotLight L, vec3 N, vec3 P, vec3 V);

void main() {
    vec3 N = normalize(vNormal);
    vec3 V = normalize(viewPos - vFragPos);
    vec3 result = calcDir(dirLight, N, V);
    for (int i = 0; i < NR_POINT; ++i)
        result += calcPoint(pointLights[i], N, vFragPos, V);
    result += calcSpot(spotLight, N, vFragPos, V);
    FragColor = vec4(result, 1.0);
}

vec3 calcDir(DirLight L, vec3 N, vec3 V) {
    vec3 lightDir = normalize(-L.direction);
    float diff = max(dot(N, lightDir), 0.0);
    vec3 H = normalize(lightDir + V);
    float spec = pow(max(dot(N, H), 0.0), material.shininess);
    vec3 a = L.ambient  * vec3(texture(material.diffuse,  vUV));
    vec3 d = L.diffuse  * diff * vec3(texture(material.diffuse,  vUV));
    vec3 s = L.specular * spec * vec3(texture(material.specular, vUV));
    return a + d + s;
}

vec3 calcPoint(PointLight L, vec3 N, vec3 P, vec3 V) {
    vec3 lightDir = normalize(L.position - P);
    float diff = max(dot(N, lightDir), 0.0);
    vec3 H = normalize(lightDir + V);
    float spec = pow(max(dot(N, H), 0.0), material.shininess);
    float dist = length(L.position - P);
    float att = 1.0 / (L.constant + L.linear*dist + L.quadratic*dist*dist);
    vec3 a = L.ambient  * vec3(texture(material.diffuse,  vUV));
    vec3 d = L.diffuse  * diff * vec3(texture(material.diffuse,  vUV));
    vec3 s = L.specular * spec * vec3(texture(material.specular, vUV));
    return (a + d + s) * att;
}

vec3 calcSpot(SpotLight L, vec3 N, vec3 P, vec3 V) {
    vec3 lightDir = normalize(L.position - P);
    float diff = max(dot(N, lightDir), 0.0);
    vec3 H = normalize(lightDir + V);
    float spec = pow(max(dot(N, H), 0.0), material.shininess);
    float dist = length(L.position - P);
    float att = 1.0 / (L.constant + L.linear*dist + L.quadratic*dist*dist);
    float theta   = dot(lightDir, normalize(-L.direction));
    float epsilon = L.cutOff - L.outerCutOff;
    float intensity = clamp((theta - L.outerCutOff) / epsilon, 0.0, 1.0);
    vec3 a = L.ambient  * vec3(texture(material.diffuse,  vUV));
    vec3 d = L.diffuse  * diff * vec3(texture(material.diffuse,  vUV));
    vec3 s = L.specular * spec * vec3(texture(material.specular, vUV));
    return (a + d*intensity + s*intensity) * att;
}
```

> 💡 表结构 + 函数拆分是多光源的干净写法。LearnOpenGL 原文也是这个骨架。

---

## 15. 摄像机：让用户"走进"场景

💻 **LearnOpenGL "Camera"** ⭐

### 15.1 视图矩阵的本质

> **View 矩阵 = 把"摄像机"变成"原点 + 看向 -Z 方向"的逆变换**。

```cpp
glm::mat4 view = glm::lookAt(
    cameraPos,                  // 摄像机位置
    cameraPos + cameraFront,    // 看向的目标点
    cameraUp);                  // 上方向（一般 (0,1,0)）
```

### 15.2 FPS 相机三件套

| 输入 | 控制什么 | 关键变量 |
|---|---|---|
| **WASD** | 前后左右移动 | `cameraPos += cameraFront * dt` |
| **鼠标移动** | 看的方向 | `yaw / pitch` 角度 |
| **滚轮** | 缩放 fov | `fov -= scroll` |

### 15.3 yaw/pitch 转 cameraFront

```cpp
glm::vec3 front;
front.x = cos(glm::radians(yaw)) * cos(glm::radians(pitch));
front.y = sin(glm::radians(pitch));
front.z = sin(glm::radians(yaw)) * cos(glm::radians(pitch));
cameraFront = glm::normalize(front);
```

### 15.4 必做练习

完整跑通 LearnOpenGL **"摄像机"** —— 自己飞着看 10 个立方体，**这是图形学最爽的瞬间之一** 🚀。

### 15.5 与主循环集成的输入处理范例

完整的使用示例已在 [§13.5](#135-完整可运行blinn-phong-光照的立方体) 中给出（含 WASD、鼠标、滾轮、deltaTime 全部逻辑）。这里再提炼三个**初学者最常忘记的调用**：

```cpp
// 1) 隐藏并锁定鼠标到窗口中央
glfwSetInputMode(win, GLFW_CURSOR, GLFW_CURSOR_DISABLED);

// 2) 注册三个回调
glfwSetCursorPosCallback(win, mouseCb);
glfwSetScrollCallback(win, scrollCb);
glfwSetFramebufferSizeCallback(win, [](GLFWwindow*, int w, int h){ glViewport(0,0,w,h); });

// 3) 每帧计算 dt 防止高帧率变快
float now = (float)glfwGetTime();
g_dt = now - g_last; g_last = now;
```

---

## 16. 模型加载：用 Assimp 读取 OBJ / glTF

💻 **LearnOpenGL "Model Loading"** ⭐⭐⭐⭐

### 16.1 为什么需要模型加载库

3D 模型格式上百种（OBJ / FBX / glTF / DAE / STL …），自己解析太累。**Assimp** 一行代码搞定 40+ 格式。

### 16.2 Assimp 使用三步

```cpp
Assimp::Importer importer;
const aiScene* scene = importer.ReadFile(path,
    aiProcess_Triangulate | aiProcess_FlipUVs | aiProcess_GenNormals);

if (!scene || scene->mFlags & AI_SCENE_FLAGS_INCOMPLETE) {
    std::cerr << importer.GetErrorString();
    return;
}
processNode(scene->mRootNode, scene);
```

### 16.3 数据结构设计

```text
Model
 └── vector<Mesh>
       ├── vector<Vertex>   (位置、法线、UV)
       ├── vector<unsigned> (索引)
       └── vector<Texture>  (diffuse / specular 等)
```

### 16.4 必做练习

下载 LearnOpenGL 推荐的 **nanosuit 模型**，用代码加载并渲染——**人生第一个加载的 3D 角色** 🤖。

### 16.5 Assimp CMake 接入一行额外备注

```cmake
# CMakeLists.txt 补充
set(ASSIMP_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(ASSIMP_BUILD_ASSIMP_TOOLS OFF CACHE BOOL "" FORCE)
set(ASSIMP_INSTALL OFF CACHE BOOL "" FORCE)
add_subdirectory(third_party/assimp)
target_link_libraries(app PRIVATE assimp)
```

完整的 `Mesh` / `Model` C++20 类在 [§C4](#c4-mesh--model-类完整源码) 给出，main 里仅需：

```cpp
Model suit("assets/models/nanosuit/nanosuit.obj");
// 在渲染循环里：
shader.use();
shader.setMat4("model", glm::mat4(1.0f));
shader.setMat4("view",  cam.viewMatrix());
shader.setMat4("projection", proj);
suit.draw(shader);
```

---

## 17. 综合实战：搭一个"展厅"小场景

> **目标**：用前 16 节学到的全部技能，做一个**毕业作品**。

### 17.1 项目需求清单

| 功能 | 要求 |
|---|---|
| 场景 | 一个有地面 + 4 面墙的"展厅" |
| 模型 | 至少 3 个加载的 3D 模型（自由选） |
| 材质 | 至少 2 种材质（带 diffuse/specular 贴图） |
| 光照 | 1 方向光 + 2 点光源 + 1 聚光灯（手电筒） |
| 相机 | FPS 自由飞行（WASD + 鼠标 + 滚轮） |
| 加分 | 天空盒、深度可视化、简单后处理 |

### 17.2 推荐开发顺序

```text
1. 搭环境（CMake + 基础类：Shader/Camera/Mesh/Model）
2. 画地面（一个大平面 + 砖块纹理）
3. 加 Blinn-Phong 光照
4. 加多光源
5. 加载模型（nanosuit 或 sponza）
6. 加天空盒
7. 调相机参数 + UI 调试面板（ImGui，可选）
```

### 17.3 验收标准

录一段 30 秒视频：你按 WASD 在展厅里走、看到模型在不同光照下的高光变化、手电筒能照亮局部。**做到这步，你已经超越 80% 的图形学初学者**。

### 17.4 展厅项目骨架 main.cpp（最终项目拼装）

```cpp
// src/main.cpp — W12 展厅项目骨架
#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include "Shader.hpp"
#include "Camera.hpp"
#include "Texture.hpp"
#include "Model.hpp"           // §C4

Camera g_cam{glm::vec3(0,1.5f,5)};
float  g_dt=0, g_last=0, g_lx=640, g_ly=360;
bool   g_first=true;

int main() {
    /* GLFW + GLAD + GL_DEPTH_TEST 初始化（同 §13.5） */

    Shader sh("shaders/multi.vert", "shaders/multi.frag");
    Model  pillar("assets/models/pillar/pillar.obj");
    Model  bust  ("assets/models/bust/bust.obj");
    Model  vase  ("assets/models/vase/vase.obj");

    while (!glfwWindowShouldClose(win)) {
        /* 计算 g_dt、处理 WASD（同 §13.5） */
        glClearColor(0.02f,0.02f,0.05f,1);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        sh.use();
        sh.setMat4("view", g_cam.viewMatrix());
        sh.setMat4("projection",
                   glm::perspective(glm::radians(g_cam.fov()),16.f/9.f,0.1f,100.f));
        sh.setVec3("viewPos", g_cam.position());

        // 方向光
        sh.setVec3("dirLight.direction", {-0.2f,-1.0f,-0.3f});
        sh.setVec3("dirLight.ambient",   {0.05f,0.05f,0.05f});
        sh.setVec3("dirLight.diffuse",   {0.4f,0.4f,0.4f});
        sh.setVec3("dirLight.specular",  {0.5f,0.5f,0.5f});
        // 4 个点光源 (资源位置作为厰灯) + spotLight (手电筒)… §14.5 完整参数

        // 画 3 个模型
        for (auto&& [m, pos] : std::array<std::pair<Model*,glm::vec3>,3>{
                {{&pillar, {-2,0, 0}}, {&bust, {0,1, 0}}, {&vase, {2,0, 0}}}}) {
            glm::mat4 model = glm::translate(glm::mat4(1.0f), pos);
            sh.setMat4("model", model);
            m->draw(sh);
        }

        glfwSwapBuffers(win); glfwPollEvents();
    }
}
```

> 模型可从 <https://sketchfab.com/> 免费下载。**推荐三选 OBJ + 同路径 .mtl + 贴图**。

---

## 18. 着色器调试 5 招（含 RenderDoc 入门）

### 18.1 调试招数

| 招 | 用法 | 适用场景 |
|---|---|---|
| **① 把变量当颜色输出** | `FragColor = vec4(vUV, 0, 1);` | 看 UV 是否对 |
| **② 法线可视化** | `FragColor = vec4(vNormal*0.5+0.5, 1);` | 看法线是否正确 |
| **③ 深度可视化** | `FragColor = vec4(vec3(gl_FragCoord.z), 1);` | 看深度分布 |
| **④ glGetError** | `cout << glGetError();` | 找 OpenGL API 错误 |
| **⑤ RenderDoc 抓帧** | F12 抓帧 → 看 draw call | 终极武器 ⭐ |

### 18.2 RenderDoc 入门

1. 下载：<https://renderdoc.org/>
2. 打开 RenderDoc → "Launch Application" → 选你的 exe
3. 按 **F12** 抓一帧
4. 在 Event Browser 里点每个 `glDrawElements`，能看到：
   - 每个 draw call 的输入网格、纹理、uniform
   - 每个 pipeline stage 的输出

> 💡 **RenderDoc 是图形程序员的"打印调试"**——学会它，找 bug 效率提升 10 倍。

---

## 19. 初学者最常见的 10 个 Bug

| # | 现象 | 原因 | 解法 |
|---|---|---|---|
| 1 | 黑屏 | 忘了 `glClear` 或 shader 编译失败 | 加 shader 错误检查 |
| 2 | 三角形不显示 | VAO 没绑定 / 顶点位置在视锥外 | 用 `(0,0,-3)` 立方体测试 |
| 3 | 纹理颠倒 | 未 `stbi_set_flip_vertically_on_load(true)` | 加上即可 |
| 4 | 模型怪异变形 | 法线被错误平移 | normal 用 mat3(transpose(inverse(model))) 变换 |
| 5 | 光照黑乎乎 | 法线方向反 / 在视图空间算光照混了世界空间 | 统一坐标系 |
| 6 | 立方体前后乱穿 | 没开 `GL_DEPTH_TEST` | `glEnable(GL_DEPTH_TEST)` |
| 7 | 模型一闪即消 | near/far 设置不当导致 z-fighting | 拉大 near，比如 `0.1f` |
| 8 | uniform 不生效 | 没 `glUseProgram` 就设置 | 先 use 再 set |
| 9 | 着色器无效但不报错 | 忘了检查编译/链接 log | 写 `checkCompileErrors()` |
| 10 | 帧率突降 | mipmap 没生成 / 纹理过大 | `glGenerateMipmap` |

---

## 20. Gamma 校正与 HDR：为什么我画面发暗 / 颜色不对？

📖 **虎书 Ch 21 摘要** + 💻 **LearnOpenGL "Advanced Lighting → Gamma Correction / HDR"**

> 这是 LearnOpenGL 进阶章节的内容，但**初学者第一周就会撞到**——光照算出来的画面"灰扑扑、发暗"，多半就是 Gamma 没处理。

### 20.1 sRGB 与线性空间：一句话

> 你看到的 PNG / JPG 图片**已经是 Gamma 编码（≈ pow(x, 1/2.2)）的**，目的是节省存储位深度。但**光照计算要求线性空间**。

```text
[sRGB 纹理]  ──pow(x, 2.2)──→  [线性空间，做光照]  ──pow(x, 1/2.2)──→  [显示器]
                                      ↑                                   ↑
                                 Phong / Blinn-Phong                  Gamma 编码
```

### 20.2 OpenGL 的两种正确做法

#### 方法 A：让硬件自动做（推荐）

```cpp
// 1) 加载 sRGB 纹理时声明：
glTexImage2D(GL_TEXTURE_2D, 0, GL_SRGB_ALPHA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data);

// 2) 创建窗口时开启 sRGB 帧缓冲 + 启用：
glfwWindowHint(GLFW_SRGB_CAPABLE, GLFW_TRUE);
glEnable(GL_FRAMEBUFFER_SRGB);
```

#### 方法 B：手动在 fragment shader 末尾 Gamma 编码

```glsl
void main() {
    vec3 color = ...;                          // 线性空间结果
    color = pow(color, vec3(1.0/2.2));         // Gamma 编码
    FragColor = vec4(color, 1.0);
}
```

### 20.3 HDR 简介

| 概念 | 一句话 |
|---|---|
| **HDR**（High Dynamic Range） | 中间结果颜色**允许 > 1.0**，最后再压回 [0,1] |
| **Tone Mapping** | 把 HDR 结果**压**到显示器范围的算法（如 Reinhard、ACES） |
| **Bloom** | HDR 高亮区域提取后做高斯模糊再叠回，模拟"亮瞎眼"效果 |

最简单的 Reinhard tone mapping：

```glsl
vec3 color = ...;                  // HDR (可能 > 1.0)
color = color / (color + 1.0);     // 压到 [0,1]
color = pow(color, vec3(1.0/2.2)); // Gamma
FragColor = vec4(color, 1.0);
```

> 💡 **学完这一节，再去看《荒野大镖客》《2077》之类的现代游戏，你会发现"原来 Bloom + ACES 是这么回事"**。

---

## 21. 法线矩阵 / reflect / refract / gl_FragCoord

> 4 个**初学者最容易困惑的小知识点**，集中讲清楚。

### 21.1 法线矩阵（Normal Matrix）

**问题**：模型矩阵里有缩放（特别是非均匀缩放）时，**直接用 `model * normal` 会把法线方向算错**。

**正解**：法线要乘 `mat3(transpose(inverse(model)))`，简称**法线矩阵**：

```glsl
// vertex shader
vNormal = mat3(transpose(inverse(model))) * aNormal;
```

> 💡 性能优化：`transpose(inverse(...))` 在每帧每顶点算太贵。**实际项目里 CPU 端算好后通过 uniform 传**：
>
> ```cpp
> glm::mat3 normalMat = glm::mat3(glm::transpose(glm::inverse(model)));
> shader.setMat3("normalMatrix", normalMat);
> ```

### 21.2 GLSL 内置函数三件套

| 函数 | 含义 | 用途 |
|---|---|---|
| `reflect(I, N)` | 反射方向（I 入射，N 法线） | 镜面反射、环境贴图 |
| `refract(I, N, eta)` | 折射方向（eta = n1/n2） | 玻璃、水面 |
| `mix(a, b, t)` | 线性插值 `a*(1-t) + b*t` | 双纹理混合、过渡 |

```glsl
// 玻璃材质 (eta=1/1.52 ≈ 0.658)
vec3 I = normalize(vFragPos - viewPos);
vec3 R = refract(I, normalize(vNormal), 0.658);
FragColor = vec4(texture(skybox, R).rgb, 1.0);
```

### 21.3 `gl_FragCoord`

Fragment shader 内置变量：当前片段的**屏幕坐标 (x, y, z, 1/w)**。

| 分量 | 含义 |
|---|---|
| `gl_FragCoord.xy` | 像素坐标（左下原点，单位像素） |
| `gl_FragCoord.z` | 深度 [0,1]（写到 depth buffer 的值） |
| `gl_FragCoord.w` | 1 / 视空间 z |

最常用：**深度可视化 / 屏幕空间效果**

```glsl
float depth = gl_FragCoord.z;
FragColor = vec4(vec3(depth), 1.0);   // 越远越白
```

---

## C1. Shader 类完整源码

> **本节给出可以**直接放进 `src/Shader.hpp` 与 `src/Shader.cpp`** 的完整代码。**支持读取文件、错误检查、所有 setXxx**。

### `src/Shader.hpp`

```cpp
#pragma once
#include <glad/glad.h>
#include <glm/glm.hpp>
#include <string>
#include <string_view>
#include <filesystem>

class Shader {
public:
    Shader(const std::filesystem::path& vsPath,
           const std::filesystem::path& fsPath);
    ~Shader();

    Shader(const Shader&) = delete;
    Shader& operator=(const Shader&) = delete;
    Shader(Shader&& o) noexcept : id_(o.id_) { o.id_ = 0; }
    Shader& operator=(Shader&& o) noexcept;

    void use() const { glUseProgram(id_); }
    GLuint id() const noexcept { return id_; }

    void setBool (std::string_view name, bool  v) const;
    void setInt  (std::string_view name, int   v) const;
    void setFloat(std::string_view name, float v) const;
    void setVec2 (std::string_view name, const glm::vec2& v) const;
    void setVec3 (std::string_view name, const glm::vec3& v) const;
    void setVec4 (std::string_view name, const glm::vec4& v) const;
    void setMat3 (std::string_view name, const glm::mat3& m) const;
    void setMat4 (std::string_view name, const glm::mat4& m) const;

private:
    GLuint id_ = 0;
    static std::string readFile(const std::filesystem::path& p);
    static GLuint compile(GLenum type, const std::string& src,
                          const std::filesystem::path& path);
    static void   checkLink(GLuint program);
    GLint loc(std::string_view name) const;
};
```

### `src/Shader.cpp`

```cpp
#include "Shader.hpp"
#include <fstream>
#include <sstream>
#include <iostream>
#include <format>
#include <glm/gtc/type_ptr.hpp>

std::string Shader::readFile(const std::filesystem::path& p) {
    std::ifstream f(p);
    if (!f) {
        std::cerr << std::format("[Shader] open fail: {}\n", p.string());
        std::abort();
    }
    std::stringstream ss; ss << f.rdbuf();
    return ss.str();
}

GLuint Shader::compile(GLenum type, const std::string& src,
                       const std::filesystem::path& path) {
    GLuint id = glCreateShader(type);
    const char* p = src.c_str();
    glShaderSource(id, 1, &p, nullptr);
    glCompileShader(id);

    GLint ok = 0;
    glGetShaderiv(id, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[2048]{};
        glGetShaderInfoLog(id, sizeof(log), nullptr, log);
        std::cerr << std::format("[Shader compile error] {}:\n{}\n",
                                 path.string(), log);
        std::abort();
    }
    return id;
}

void Shader::checkLink(GLuint program) {
    GLint ok = 0;
    glGetProgramiv(program, GL_LINK_STATUS, &ok);
    if (!ok) {
        char log[2048]{};
        glGetProgramInfoLog(program, sizeof(log), nullptr, log);
        std::cerr << "[Shader link error]\n" << log << "\n";
        std::abort();
    }
}

Shader::Shader(const std::filesystem::path& vsPath,
               const std::filesystem::path& fsPath) {
    auto vs = compile(GL_VERTEX_SHADER,   readFile(vsPath), vsPath);
    auto fs = compile(GL_FRAGMENT_SHADER, readFile(fsPath), fsPath);
    id_ = glCreateProgram();
    glAttachShader(id_, vs);
    glAttachShader(id_, fs);
    glLinkProgram(id_);
    checkLink(id_);
    glDeleteShader(vs);
    glDeleteShader(fs);
}

Shader::~Shader() { if (id_) glDeleteProgram(id_); }

Shader& Shader::operator=(Shader&& o) noexcept {
    if (this != &o) { if (id_) glDeleteProgram(id_); id_ = o.id_; o.id_ = 0; }
    return *this;
}

GLint Shader::loc(std::string_view name) const {
    // 注意：GL 接受的是以 \0 结尾的 const char*，string_view 不一定带，
    // 这里安全起见用 string 拷贝
    return glGetUniformLocation(id_, std::string(name).c_str());
}

void Shader::setBool (std::string_view n, bool  v)  const { glUniform1i (loc(n), (int)v); }
void Shader::setInt  (std::string_view n, int   v)  const { glUniform1i (loc(n), v); }
void Shader::setFloat(std::string_view n, float v)  const { glUniform1f (loc(n), v); }
void Shader::setVec2 (std::string_view n, const glm::vec2& v) const { glUniform2fv(loc(n),1,glm::value_ptr(v)); }
void Shader::setVec3 (std::string_view n, const glm::vec3& v) const { glUniform3fv(loc(n),1,glm::value_ptr(v)); }
void Shader::setVec4 (std::string_view n, const glm::vec4& v) const { glUniform4fv(loc(n),1,glm::value_ptr(v)); }
void Shader::setMat3 (std::string_view n, const glm::mat3& m) const { glUniformMatrix3fv(loc(n),1,GL_FALSE,glm::value_ptr(m)); }
void Shader::setMat4 (std::string_view n, const glm::mat4& m) const { glUniformMatrix4fv(loc(n),1,GL_FALSE,glm::value_ptr(m)); }
```

---

## C2. Camera 类完整源码

> 第一人称自由飞行相机，支持 WASD + 鼠标 + 滚轮。

### `src/Camera.hpp`

```cpp
#pragma once
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>

class Camera {
public:
    enum Direction { FORWARD, BACKWARD, LEFT, RIGHT };

    explicit Camera(glm::vec3 position = {0,0,3},
                    glm::vec3 worldUp  = {0,1,0},
                    float yawDeg   = -90.0f,
                    float pitchDeg = 0.0f);

    glm::mat4 viewMatrix() const { return glm::lookAt(pos_, pos_ + front_, up_); }
    glm::vec3 position()   const { return pos_; }
    float     fov()        const { return fov_; }

    void processKey   (Direction d, float dt);
    void processMouse (float dx, float dy, bool constrainPitch = true);
    void processScroll(float dy);

private:
    void updateVectors();

    glm::vec3 pos_, front_{0,0,-1}, up_{0,1,0}, right_{1,0,0}, worldUp_;
    float yaw_, pitch_;
    float speed_       = 4.0f;
    float sensitivity_ = 0.1f;
    float fov_         = 45.0f;
};
```

### `src/Camera.cpp`

```cpp
#include "Camera.hpp"
#include <algorithm>

Camera::Camera(glm::vec3 position, glm::vec3 worldUp, float yawDeg, float pitchDeg)
    : pos_(position), worldUp_(worldUp), yaw_(yawDeg), pitch_(pitchDeg) {
    updateVectors();
}

void Camera::updateVectors() {
    glm::vec3 f;
    f.x = std::cos(glm::radians(yaw_)) * std::cos(glm::radians(pitch_));
    f.y = std::sin(glm::radians(pitch_));
    f.z = std::sin(glm::radians(yaw_)) * std::cos(glm::radians(pitch_));
    front_ = glm::normalize(f);
    right_ = glm::normalize(glm::cross(front_, worldUp_));
    up_    = glm::normalize(glm::cross(right_, front_));
}

void Camera::processKey(Direction d, float dt) {
    float v = speed_ * dt;
    switch (d) {
        case FORWARD : pos_ += front_ * v; break;
        case BACKWARD: pos_ -= front_ * v; break;
        case LEFT    : pos_ -= right_ * v; break;
        case RIGHT   : pos_ += right_ * v; break;
    }
}

void Camera::processMouse(float dx, float dy, bool constrainPitch) {
    yaw_   += dx * sensitivity_;
    pitch_ += dy * sensitivity_;
    if (constrainPitch) pitch_ = std::clamp(pitch_, -89.0f, 89.0f);
    updateVectors();
}

void Camera::processScroll(float dy) {
    fov_ = std::clamp(fov_ - dy, 1.0f, 80.0f);
}
```

---

## C3. Texture 工具完整源码

> 单文件 stb_image 加载 + 自动 mipmap + sRGB 选项。

### `src/Texture.hpp`

```cpp
#pragma once
#include <glad/glad.h>
#include <filesystem>

// 加载 2D 纹理；srgb=true 表示作为 sRGB 颜色贴图
GLuint loadTexture2D(const std::filesystem::path& path,
                     bool flipY = true,
                     bool srgb  = false);

// 加载立方体贴图（6 个面）
GLuint loadCubemap(const std::array<std::filesystem::path, 6>& faces);
```

### `src/Texture.cpp`

```cpp
// ⚠️ 全工程**只在这一个 .cpp 里**写下面这一行：
#define STB_IMAGE_IMPLEMENTATION
#include <stb_image.h>

#include "Texture.hpp"
#include <iostream>
#include <format>
#include <array>

static GLenum pickFormat(int channels, bool srgb) {
    switch (channels) {
        case 1: return GL_RED;
        case 3: return srgb ? GL_SRGB    : GL_RGB;
        case 4: return srgb ? GL_SRGB_ALPHA : GL_RGBA;
        default: return GL_RGB;
    }
}
static GLenum pickDataFormat(int channels) {
    switch (channels) {
        case 1: return GL_RED;
        case 3: return GL_RGB;
        case 4: return GL_RGBA;
        default: return GL_RGB;
    }
}

GLuint loadTexture2D(const std::filesystem::path& path, bool flipY, bool srgb) {
    GLuint tex = 0;
    glGenTextures(1, &tex);

    stbi_set_flip_vertically_on_load(flipY);
    int w, h, ch;
    auto* data = stbi_load(path.string().c_str(), &w, &h, &ch, 0);
    if (!data) {
        std::cerr << std::format("[Texture] load fail: {}\n", path.string());
        return tex;
    }

    glBindTexture(GL_TEXTURE_2D, tex);
    glTexImage2D(GL_TEXTURE_2D, 0, pickFormat(ch, srgb), w, h, 0,
                 pickDataFormat(ch), GL_UNSIGNED_BYTE, data);
    glGenerateMipmap(GL_TEXTURE_2D);

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
                    GL_LINEAR_MIPMAP_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);

    stbi_image_free(data);
    return tex;
}

GLuint loadCubemap(const std::array<std::filesystem::path, 6>& faces) {
    GLuint tex = 0;
    glGenTextures(1, &tex);
    glBindTexture(GL_TEXTURE_CUBE_MAP, tex);

    stbi_set_flip_vertically_on_load(false);   // cubemap 不要 flip
    for (std::size_t i = 0; i < faces.size(); ++i) {
        int w, h, ch;
        auto* data = stbi_load(faces[i].string().c_str(), &w, &h, &ch, 0);
        if (!data) { std::cerr << "cubemap face fail: " << faces[i] << "\n"; continue; }
        glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_X + (GLenum)i, 0,
                     pickFormat(ch, false), w, h, 0,
                     pickDataFormat(ch), GL_UNSIGNED_BYTE, data);
        stbi_image_free(data);
    }
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE);
    return tex;
}
```

---

## C4. Mesh / Model 类完整源码

> 用于 §16 / §17 加载 OBJ / glTF 模型。需要 Assimp。

### `src/Mesh.hpp`

```cpp
#pragma once
#include <glad/glad.h>
#include <glm/glm.hpp>
#include "Shader.hpp"
#include <vector>
#include <string>

struct Vertex {
    glm::vec3 position;
    glm::vec3 normal;
    glm::vec2 uv;
};

struct TextureRef {
    GLuint id    = 0;
    std::string type;            // "texture_diffuse" / "texture_specular"
    std::string path;            // 用于去重
};

class Mesh {
public:
    Mesh(std::vector<Vertex> vs,
         std::vector<unsigned> is,
         std::vector<TextureRef> ts);
    void draw(const Shader& sh) const;

private:
    void setup();
    std::vector<Vertex>     vertices_;
    std::vector<unsigned>   indices_;
    std::vector<TextureRef> textures_;
    GLuint VAO_=0, VBO_=0, EBO_=0;
};
```

### `src/Mesh.cpp`

```cpp
#include "Mesh.hpp"
#include <format>

Mesh::Mesh(std::vector<Vertex> vs, std::vector<unsigned> is,
           std::vector<TextureRef> ts)
    : vertices_(std::move(vs)), indices_(std::move(is)), textures_(std::move(ts)) {
    setup();
}

void Mesh::setup() {
    glGenVertexArrays(1, &VAO_);
    glGenBuffers(1, &VBO_);
    glGenBuffers(1, &EBO_);
    glBindVertexArray(VAO_);

    glBindBuffer(GL_ARRAY_BUFFER, VBO_);
    glBufferData(GL_ARRAY_BUFFER,
                 vertices_.size() * sizeof(Vertex),
                 vertices_.data(), GL_STATIC_DRAW);

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO_);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER,
                 indices_.size() * sizeof(unsigned),
                 indices_.data(), GL_STATIC_DRAW);

    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex),
                          (void*)offsetof(Vertex, position));
    glEnableVertexAttribArray(1);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex),
                          (void*)offsetof(Vertex, normal));
    glEnableVertexAttribArray(2);
    glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, sizeof(Vertex),
                          (void*)offsetof(Vertex, uv));
    glBindVertexArray(0);
}

void Mesh::draw(const Shader& sh) const {
    int diffN = 0, specN = 0;
    for (std::size_t i = 0; i < textures_.size(); ++i) {
        glActiveTexture(GL_TEXTURE0 + (GLenum)i);
        std::string name = textures_[i].type == "texture_diffuse"
            ? std::format("material.diffuse{}",  ++diffN)
            : std::format("material.specular{}", ++specN);
        sh.setInt(name, (int)i);
        glBindTexture(GL_TEXTURE_2D, textures_[i].id);
    }
    glBindVertexArray(VAO_);
    glDrawElements(GL_TRIANGLES, (GLsizei)indices_.size(), GL_UNSIGNED_INT, 0);
    glBindVertexArray(0);
    glActiveTexture(GL_TEXTURE0);
}
```

### `src/Model.hpp`

```cpp
#pragma once
#include "Mesh.hpp"
#include <assimp/scene.h>
#include <filesystem>

class Model {
public:
    explicit Model(const std::filesystem::path& path);
    void draw(const Shader& sh) const;

private:
    void processNode(aiNode* node, const aiScene* scene);
    Mesh processMesh(aiMesh* mesh, const aiScene* scene);
    std::vector<TextureRef> loadMaterialTextures(aiMaterial* mat,
                                                 unsigned type,
                                                 const std::string& typeName);

    std::vector<Mesh>       meshes_;
    std::vector<TextureRef> loadedCache_;
    std::filesystem::path   directory_;
};
```

### `src/Model.cpp`

```cpp
#include "Model.hpp"
#include "Texture.hpp"
#include <assimp/Importer.hpp>
#include <assimp/postprocess.h>
#include <iostream>

Model::Model(const std::filesystem::path& path) {
    Assimp::Importer imp;
    const aiScene* scene = imp.ReadFile(path.string(),
        aiProcess_Triangulate | aiProcess_FlipUVs | aiProcess_GenNormals);
    if (!scene || scene->mFlags & AI_SCENE_FLAGS_INCOMPLETE || !scene->mRootNode) {
        std::cerr << "Assimp: " << imp.GetErrorString() << "\n";
        return;
    }
    directory_ = path.parent_path();
    processNode(scene->mRootNode, scene);
}

void Model::draw(const Shader& sh) const {
    for (auto& m : meshes_) m.draw(sh);
}

void Model::processNode(aiNode* node, const aiScene* scene) {
    for (unsigned i = 0; i < node->mNumMeshes; ++i)
        meshes_.push_back(processMesh(scene->mMeshes[node->mMeshes[i]], scene));
    for (unsigned i = 0; i < node->mNumChildren; ++i)
        processNode(node->mChildren[i], scene);
}

Mesh Model::processMesh(aiMesh* m, const aiScene* scene) {
    std::vector<Vertex>   vs;  vs.reserve(m->mNumVertices);
    std::vector<unsigned> is;  is.reserve(m->mNumFaces * 3);

    for (unsigned i = 0; i < m->mNumVertices; ++i) {
        Vertex v{};
        v.position = {m->mVertices[i].x, m->mVertices[i].y, m->mVertices[i].z};
        if (m->HasNormals())
            v.normal = {m->mNormals[i].x, m->mNormals[i].y, m->mNormals[i].z};
        if (m->mTextureCoords[0])
            v.uv = {m->mTextureCoords[0][i].x, m->mTextureCoords[0][i].y};
        vs.push_back(v);
    }
    for (unsigned i = 0; i < m->mNumFaces; ++i) {
        const aiFace& f = m->mFaces[i];
        for (unsigned j = 0; j < f.mNumIndices; ++j)
            is.push_back(f.mIndices[j]);
    }

    std::vector<TextureRef> ts;
    if (m->mMaterialIndex >= 0) {
        aiMaterial* mat = scene->mMaterials[m->mMaterialIndex];
        auto d = loadMaterialTextures(mat, aiTextureType_DIFFUSE,  "texture_diffuse");
        auto s = loadMaterialTextures(mat, aiTextureType_SPECULAR, "texture_specular");
        ts.insert(ts.end(), d.begin(), d.end());
        ts.insert(ts.end(), s.begin(), s.end());
    }
    return Mesh(std::move(vs), std::move(is), std::move(ts));
}

std::vector<TextureRef> Model::loadMaterialTextures(aiMaterial* mat,
                                                    unsigned type,
                                                    const std::string& typeName) {
    std::vector<TextureRef> out;
    for (unsigned i = 0; i < mat->GetTextureCount((aiTextureType)type); ++i) {
        aiString str; mat->GetTexture((aiTextureType)type, i, &str);
        std::string filename = str.C_Str();

        auto it = std::find_if(loadedCache_.begin(), loadedCache_.end(),
                               [&](const TextureRef& t){ return t.path == filename; });
        if (it != loadedCache_.end()) { out.push_back(*it); continue; }

        TextureRef t;
        t.id   = loadTexture2D(directory_ / filename, /*flipY=*/false);
        t.type = typeName;
        t.path = filename;
        out.push_back(t);
        loadedCache_.push_back(t);
    }
    return out;
}
```

---

## 附录 A：资料速查表

### A.1 必备链接（收藏夹）

- 📘 **虎书中文翻译**：<https://github.com/NWPU66/Fundamentals-Of-Computer-Graphics-5th-CN>
- 💻 **LearnOpenGL 中文版**：<https://learnopengl-cn.github.io/>
- 🎬 **GAMES101 视频**：B 站搜 "GAMES101"
- 🛠️ **GLAD 在线生成**：<https://glad.dav1d.de/>
- 🔍 **RenderDoc**：<https://renderdoc.org/>
- 🎨 **ShaderToy（练 Fragment Shader）**：<https://www.shadertoy.com/>
- 📊 **GLM 文档**：<https://github.com/g-truc/glm>

### A.2 推荐对应章节

| 周次 | 虎书 | LearnOpenGL |
|---|---|---|
| 数学基础 | Ch 2.4, Ch 5 | Transformations |
| 变换/空间 | Ch 6, Ch 7 | Coordinate Systems |
| 管线 | Ch 8 | Hello Triangle |
| 着色器 | — | Shaders |
| 纹理 | Ch 11 | Textures |
| 光照 | Ch 10 | Basic Lighting + Materials |
| 模型 | — | Model Loading |
| 深度 | Ch 9 | Depth Testing |

---

## 附录 B：数学公式小抄

```text
# 向量
点积:  a·b  = ax*bx + ay*by + az*bz = |a||b|cosθ
叉积:  a×b  = (ay*bz - az*by, az*bx - ax*bz, ax*by - ay*bx)
归一化: â  = a / |a|

# 朗伯漫反射
diffuse = max(0, N·L)

# Blinn-Phong 高光
H = normalize(L + V)
specular = pow(max(0, N·H), shininess)

# 反射方向
R = 2(N·L)N - L      // 也可用 reflect(-L, N)

# MVP
clip = Projection * View * Model * vec4(localPos, 1.0)

# 投影矩阵（透视）
fov 越大 → 鱼眼，fov 越小 → 望远镜
near/far 比值越大 → z-fighting 越严重
```

---

## 附录 C：OpenGL API 速查

```cpp
// ====== 初始化 ======
glfwInit();  glfwCreateWindow(...);
gladLoadGLLoader((GLADloadproc)glfwGetProcAddress);
glViewport(0, 0, w, h);
glEnable(GL_DEPTH_TEST);

// ====== 缓冲对象 ======
glGenBuffers / glBindBuffer / glBufferData
glGenVertexArrays / glBindVertexArray
glVertexAttribPointer / glEnableVertexAttribArray

// ====== 着色器 ======
glCreateShader(GL_VERTEX_SHADER) / glShaderSource / glCompileShader
glCreateProgram / glAttachShader / glLinkProgram
glUseProgram

// ====== Uniform ======
GLint loc = glGetUniformLocation(prog, "name");
glUniform1f / glUniform3fv / glUniformMatrix4fv

// ====== 纹理 ======
glGenTextures / glBindTexture / glTexImage2D
glTexParameteri / glGenerateMipmap
glActiveTexture(GL_TEXTURE0); glBindTexture(...);

// ====== 绘制 ======
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
glDrawArrays(GL_TRIANGLES, 0, n)
glDrawElements(GL_TRIANGLES, n, GL_UNSIGNED_INT, 0)
```

---

## 参考资料

1. **虎书中文**：<https://github.com/NWPU66/Fundamentals-Of-Computer-Graphics-5th-CN>
2. **LearnOpenGL 中文**：<https://learnopengl-cn.github.io/>
3. **LearnOpenGL 英文原版**：<https://learnopengl.com/>
4. **GAMES101**：<https://sites.cs.ucsb.edu/~lingqi/teaching/games101.html>
5. **OpenGL 官方文档**：<https://www.khronos.org/opengl/>
6. **GLM**：<https://github.com/g-truc/glm>
7. **GLFW**：<https://www.glfw.org/>
8. **stb_image**：<https://github.com/nothings/stb>
9. **Assimp**：<https://github.com/assimp/assimp>
10. **RenderDoc**：<https://renderdoc.org/>
11. **The Book of Shaders**（Fragment Shader 入门）：<https://thebookofshaders.com/>
12. **Inigo Quilez**：<https://iquilezles.org/>

---

## 附录 A4：12 周自检清单（每周打勾表）

> **建议**：每周日花 10 分钟对照下表，**所有 ✅ 必须自己亲眼跑出来**才算合格。卡在哪一格，就回那一节再读一次。

### W1 · 数学 + Hello Window
- [ ] 我能解释**点积/叉积**的几何含义（§4.2 + §A0.2）
- [ ] 我能写出 `dot / cross` 的 GLM 调用并手算验证
- [ ] 环境跑通：`build/Release/app.exe` 弹出黑窗口、按 ESC 关闭
- [ ] **思考题**：`dot(a,b)` 为什么能判断"光是否照到表面"？

### W2 · Hello Triangle + Shaders
- [ ] §3.5 完整 main.cpp 跑出**渐变三角形**
- [ ] 我能解释 VAO / VBO 的分工（§9.1）
- [ ] 写出"随时间变色"的 fragment shader（§10.5）
- [ ] **思考题**：去掉 `glEnableVertexAttribArray(0)` 会发生什么？

### W3 · 变换 + 旋转纹理矩形
- [ ] 完成 §5.5 手算 5 步变换 + GLM 验证
- [ ] §12.6 双纹理矩形跑通（30% 笑脸 + 70% 木纹）
- [ ] 改 `mix(c0, c1, t)` 的 t 看混合比例变化
- [ ] **思考题**：为什么 `glm::translate` 写在最前面，画面里看起来却是"最后做"？

### W4 · 3D 立方体 ⭐
- [ ] §6.6 完整 main 跑出**10 个旋转立方体**
- [ ] 关掉 `glEnable(GL_DEPTH_TEST)` 看穿插错乱（§11）
- [ ] 把 fov 从 45° 改成 110°，观察"鱼眼"效果
- [ ] **思考题**：透视除法发生在哪一步？

### W5 · FPS 摄像机
- [ ] §C2 Camera 类放进项目，能 WASD + 鼠标看
- [ ] 鼠标 yaw/pitch 限制在 ±89°（避免翻面）
- [ ] 滚轮缩放 fov 平滑
- [ ] **思考题**：为什么 `cameraFront` 用 yaw/pitch 算，而不是直接存？

### W6 · Phong 光照 ⭐
- [ ] §13.5 完整 Blinn-Phong 跑通（橙色立方体 + 白光球）
- [ ] shininess 从 8 调到 256，亲眼看到高光变锐
- [ ] 法线矩阵正确：把 model 设为非均匀缩放看是否歪
- [ ] **思考题**：为什么 ambient 不是 0？

### W7 · 材质 + 贴图
- [ ] 木箱使用 diffuse + specular 两张贴图
- [ ] 高光只出现在金属边框，木头部分没高光
- [ ] **思考题**：specular map 的黑色像素表示什么？

### W8 · 多光源 ⭐
- [ ] §14.5 多光源 frag 跑通：1 方向光 + 4 点光 + 1 手电筒
- [ ] 距离衰减系数对照 LearnOpenGL 表配 50 单位距离
- [ ] **思考题**：为什么聚光灯要有 inner/outer 两个角度？

### W9 · 模型加载
- [ ] §C4 Mesh / Model 类编译通过
- [ ] 加载 nanosuit（或自己下的 OBJ）
- [ ] 模型法线正确（用 §18 法线可视化检查）
- [ ] **思考题**：为什么 OBJ 加载要 `aiProcess_FlipUVs`？

### W10 · 深度 + 模板
- [ ] 多模型场景遮挡正确
- [ ] 用模板缓冲做"物体描边"
- [ ] **思考题**：z-fighting 发生时，如何用 near/far 缓解？

### W11 · 天空盒 + 后处理 ⭐
- [ ] 立方体贴图天空盒能跟着相机转
- [ ] 离屏 FBO 渲染 + 全屏四边形后处理（反色 / 灰度）
- [ ] **思考题**：天空盒的 vertex shader 为什么要 `gl_Position = pos.xyww`？

### W12 · 展厅项目交付 ⭐⭐⭐
- [ ] §17.4 展厅 main 完整跑通：3 模型 + 多光源 + FPS 相机
- [ ] 录一段 30 秒视频（手电筒能扫过模型）
- [ ] **可选加分**：开 §20 Gamma 校正，对比开关效果
- [ ] **思考题**：如果让你给画面加 Bloom，你会怎么做？

---

> 🎓 **当所有 ✅ 都打勾**，恭喜你已经具备**独立做小型 3D Demo / 看懂主流渲染论文前置知识 / 进入 GAMES202、PBR、光线追踪进阶**的能力。
>
> 下一阶段推荐：
>
> 1. **GAMES202**（实时渲染：阴影、SSAO、PBR、全局光照）
> 2. **Real-Time Rendering 4th**（业界圣经）
> 3. **Ray Tracing in One Weekend**（光线追踪入门 5 天）
> 4. **学一个 GPU API 进阶**：Vulkan / Metal / DirectX 12（任选）
>
> 加油，画家 🎨。
