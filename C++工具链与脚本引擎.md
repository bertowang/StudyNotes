---
tags:
  - c++
  - cmake
  - ninja
  - scripting
  - quickjs
  - ecs
  - ffi
  - calling-convention
  - stdcall
  - cdecl
  - git
  - gitignore
aliases:
  - C++17与构建工具
  - ScriptX脚本引擎
  - CMake vs Ninja
  - QuickJS简介
  - Venus与MSF微服务
  - FFI外部函数接口
  - stdcall与cdecl调用约定
created: 2026-06-20
updated: 2026-06-20
---

# C++ 工具链与脚本引擎

---

## 一、C++1z = C++17

### 1.1 命名由来

C++ 标准在正式发布前使用临时代号：

```
C++0x → C++11（原预计 200x 年发布）
C++1y → C++14（C++11 之后的下一个标准）
C++1z → C++17（按字母表 x→y→z）
```

### 1.2 语言核心特性

| 特性 | 示例 |
|:---|:---|
| **结构化绑定** | `auto [key, value] = map_entry;` |
| **if/switch 初始化** | `if (auto it = map.find(k); it != end())` |
| **折叠表达式** | `(std::cout << ... << args)` |
| **constexpr if** | `if constexpr (std::is_pointer_v<T>)` |
| **类模板参数推导** | `std::pair p(1, 2.0);` — 无需写 `<int,double>` |
| **内联变量** | `inline` 可用于变量定义 |

### 1.3 标准库增强

- `std::filesystem` — 文件系统操作
- `std::execution::par` — 并行算法
- `std::string_view` — 零拷贝字符串视图
- `std::variant`, `std::optional`, `std::any` — 类型安全的多值/可选/任意类型

### 1.4 编译器使用

```bash
# GCC / Clang
g++ -std=c++17 main.cpp

# MSVC
cl /std:c++17 main.cpp
```

---

## 二、CMake vs Ninja

> [!important] 核心关系
> CMake 和 Ninja **不是竞争对手**，而是构建流程中**不同阶段的协作工具**：
> - **CMake** = 构建系统**生成器**（高级配置 → 生成低级构建文件）
> - **Ninja** = 构建系统**执行器**（以最快速度执行构建任务）

### 2.1 角色分工

| | CMake（架构师/项目经理）| Ninja（专注高效的施工队）|
|:---|:---|:---|
| 核心任务 | 配置编译环境 → 生成底层构建脚本 | 读取 `build.ninja` → 高度并行调用编译器 |
| 输入 | `CMakeLists.txt`（人类可写）| `build.ninja`（机器生成）|
| 输出 | Makefile / `.sln` / `build.ninja` 等 | 编译产物（`.o`, `.a`, 可执行文件）|
| 设计目标 | 跨平台配置、易用性、功能丰富 | 极致构建速度 |

### 2.2 典型工作流程

```bash
# CMake 生成 Ninja 构建文件
cmake -B build -G Ninja .

# Ninja 执行构建
cd build && ninja
```

### 2.3 多维对比

| 特性维度 | CMake | Ninja |
|:---|:---|:---|
| 核心定位 | 构建系统生成器 | 构建系统执行器 |
| 用户接口 | 丰富命令和模块 | 极其简单（主要是 `ninja` 命令）|
| 依赖检查 | 生成阶段解析高级依赖 | 构建阶段极快速精确的增量依赖检查 |
| 平台支持 | 全平台：Linux/macOS/Windows | 全平台 |
| 可读性 | `CMakeLists.txt` 可读性高 | `build.ninja` 机器可读，人不该手写 |

### 2.4 Visual Studio 生成器速查

```bat
:: VS 2022
cmake .. -G "Visual Studio 17 2022" -A x64

:: VS 2019
cmake .. -G "Visual Studio 16 2019" -A x64

:: VS 2017
cmake .. -G "Visual Studio 15 2017" -A x64
```

> [!tip] 最佳实践
> 现代 C++ 开发的最佳实践：用 CMake 的强大配置能力生成 Ninja 构建文件，结合两者优势——既灵活又高效。

---

## 三、ScriptX — 跨平台脚本引擎抽象层

### 3.1 核心概述

ScriptX 是字节跳动开源的**跨平台脚本引擎抽象层**。提供一套统一的 C++ API，让应用无缝对接多种底层脚本引擎（V8、JavaScriptCore、Lua、LuaJIT、QuickJS 等）。

### 3.2 解决的问题

| 痛点 | ScriptX 方案 |
|:---|:---|
| 不同平台脚本引擎性能差异 | 运行时切换后端，无需改业务代码 |
| 历史项目使用不同脚本语言 | 统一 API，一套代码绑定多种引擎 |
| 直接调用 V8/Lua 原生 API | 抽象层屏蔽底层差异，切换引擎零成本 |

### 3.3 核心架构

```
┌─────────────────────────────┐
│    统一接口层（业务代码）      │  ← engine->get(), func.call()
├─────────────────────────────┤
│    抽象实现层（通用逻辑）      │  ← 引用计数、GC 协调、异常处理
├─────────────────────────────┤
│    后端绑定层（引擎驱动）      │  ← V8 / JSC / Lua / LuaJIT / QuickJS
└─────────────────────────────┘
```

### 3.4 双向互操作

ScriptX 支持**两个方向**的互操作：

#### 方向一：脚本调用 C++（主要场景 — 暴露 C++ 功能给脚本）

```cpp
// C++ 暴露 Player 类给脚本
auto playerClass = engine->registerClass<Player>("Player");
playerClass.function("getName", &Player::getName);
playerClass.function("moveTo", &Player::moveTo);
```

```javascript
// 脚本侧调用
var player = new Player();
player.setHealth(100);
player.moveTo(10.5, 20.3);
```

#### 方向二：C++ 调用脚本函数

```cpp
auto calculateDamage = engine->getGlobal().getProperty("calculateDamage");
auto result = calculateDamage.call({}, 50, 30);
```

### 3.5 消息队列与事件循环

核心目标：**线程安全**。脚本引擎（V8、Lua 等）通常不是线程安全的。

```
任意线程（生产者） → MessageQueue.post() → 任务入队
                                              ↓ FIFO
主线程（消费者）   → EventLoop 轮询取出 → 安全执行
```

```cpp
// 主线程事件循环
void mainThreadEventLoop() {
    while (!shouldQuit) {
        processPlatformEvents();   // 平台消息（UI 等）
        messageQueue.processOnce(); // 处理一个脚本任务
        renderFrame();             // 渲染
    }
}

// 任意线程投递脚本任务
mq.post([]() {
    auto result = scriptEngine.eval("1 + 2");
});
```

> 协同流程：网络线程封装脚本任务 → 投递到主线程的消息队列 → 主线程事件循环取任务 → 安全执行

### 3.6 主要优势

- **彻底解耦**：一套代码运行在多种脚本引擎上
- **高性能**：抽象层开销极低
- **内存安全**：内置 GC 协调机制
- **开源**：GitHub `code-bytecode/ScriptX`

---

## 四、QuickJS — 轻量级 JavaScript 引擎

### 4.1 核心定位

Fabrice Bellard（FFmpeg、QEMU 的创建者）和 Charlie Gordon 开发的**小巧但功能强大的 JS 引擎**。目标是提供完整、可嵌入、符合最新 ECMAScript 标准的 JS 实现。

### 4.2 关键特点

| 特点 | 说明 |
|:---|:---|
| **极致轻量** | 源码压缩后仅几百 KB，零外部依赖 |
| **高兼容性** | 支持 ES2020+：ES6 模块、异步生成器、可选链等 |
| **独立可执行** | 可编译为独立的 `qjs` 可执行文件 |
| **内置 GC** | 引用计数为主，延迟极低且可预测 |
| **数学精度** | 默认 IEEE 754 双精度浮点数，可配置为 64 位整数 |

### 4.3 性能特点

- 启动速度极快，内存占用极低
- 峰值计算性能通常不如 V8，但非常适合**短生命周期**或**快速响应**的脚本任务

### 4.4 C API 快速示例

```c
#include "quickjs.h"

int main(int argc, char **argv) {
    JSRuntime *rt = JS_NewRuntime();
    JSContext *ctx = JS_NewContext(rt);

    const char *script = "1 + 2";
    JSValue result = JS_Eval(ctx, script, strlen(script), "<eval>", 0);

    int int_result;
    JS_ToInt32(ctx, &int_result, result);
    printf("Result: %d\n", int_result);

    JS_FreeValue(ctx, result);
    JS_FreeContext(ctx);
    JS_FreeRuntime(rt);
    return 0;
}
```

### 4.5 与 ScriptX 的关系

QuickJS 是 ScriptX 支持的后端引擎之一，通过 ScriptX 的统一 API 可以方便地使用 QuickJS。

---

## 五、维纳斯 SDK（WNS）与 MSF SDK

> 腾讯内部广泛使用的后端服务核心中间件。本节面向了解大厂基础设施设计的读者。

### 5.1 维纳斯 SDK — 高性能 RPC 框架

| 特性 | 说明 |
|:---|:---|
| 核心定位 | 腾讯自研的高性能、跨平台企业级 RPC 框架 |
| 网络通信 | 基于 epoll 等高性能 I/O 模型 |
| 协议支持 | 私有二进制协议等 |
| 服务治理 | 注册与发现、负载均衡、熔断降级、监控统计 |
| 多语言 | C++, Java, Go, PHP 等 |
| 工作流程 | IDL 定义接口 → 代码生成 → 服务端注册 → 客户端像调本地方法一样调远程 |

### 5.2 MSF SDK — 微服务框架

| 特性 | 说明 |
|:---|:---|
| 核心定位 | 构建在维纳斯等 RPC 框架之上的**微服务全家桶** |
| 开箱即用 | API 网关、配置中心、服务网格、监控告警、分布式追踪 |
| 管理平台 | 可视化控制台 |
| 生态集成 | 与腾讯云深度集成 |

### 5.3 两者关系

```
MSF SDK（整车：API网关 + 配置中心 + 监控 + 部署 + 运维）
  └── 维纳斯 SDK（发动机：核心服务间通信）
```

> 维纳斯和 MSF 是支撑微信、QQ、游戏等海量业务的关键技术基础设施。

---

> [!note] 相关文档
> - [[C++图形与游戏开发]] — EntityX ECS、Filament/bgfx 渲染引擎、GLB 模型格式
> - [[嵌入式系统生态_Arduino到RT-Thread]] — 嵌入式 C/C++ 开发

---

## 六、FFI：外部函数接口

### 6.1 核心概念

**FFI**（Foreign Function Interface，外部函数接口）允许不同编程语言间相互调用函数和共享数据，常用于性能优化、复用现有库或跨语言开发。

| 方面 | 说明 |
|:---|:---|
| 作用 | 打破语言壁垒，实现跨语言函数调用（如 Python 调 C、Rust 集成 C 库） |
| 常见场景 | 高性能计算（Python 通过 C 扩展加速）、复用 C/C++ 库（如 OpenSSL）、系统级编程（Rust/Go 调系统 API） |

### 6.2 实现步骤（以 Python 调用 C 为例）

**步骤 1：编写 C 代码**

```c
// example.c
#include <stdio.h>
int add(int a, int b) { return a + b; }
void greet(const char* name) { printf("Hello, %s!\n", name); }
```

**步骤 2：编译为共享库**

```bash
# Linux/macOS
gcc -shared -o libexample.so -fPIC example.c
# Windows
gcc -shared -o example.dll example.c
```

**步骤 3：Python 使用 ctypes 调用**

```python
from ctypes import CDLL, c_int, c_char_p

lib = CDLL('./libexample.so')
lib.add.argtypes = [c_int, c_int]
lib.add.restype = c_int
print(lib.add(3, 5))  # 输出 8

lib.greet.argtypes = [c_char_p]
lib.greet(b"World")   # 输出 Hello, World!
```

### 6.3 Rust 调用 C

```rust
extern "C" {
    fn add(a: i32, b: i32) -> i32;
}
fn main() {
    unsafe { println!("3 + 5 = {}", add(3, 5)); }
}
```

### 6.4 关键注意事项

| 方面 | 说明 |
|:---|:---|
| **数据类型映射** | 确保双方类型一致（如 C 的 `int` ↔ Python 的 `c_int`） |
| **内存管理** | 明确内存所有权（C 分配的内存由 C 释放）；Rust 中用 `Box::into_raw` / `Box::from_raw` |
| **调用约定** | 指定 `stdcall` 或 `cdecl`（影响栈平衡，尤其在 Windows API 中） |
| **错误处理** | 检查 C 函数返回的错误码，转换为宿主语言异常 |

### 6.5 常见工具

| 语言 | 工具 |
|:---|:---|
| Python | `ctypes`, `cffi`, `Cython` |
| Rust | `libc`, `bindgen`（自动生成绑定） |
| Java | JNI（Java Native Interface） |
| Node.js | `node-ffi`, N-API |

---

## 七、stdcall 与 cdecl 调用约定

### 7.1 核心区别

在跨语言编程或系统级开发中，**stdcall** 和 **cdecl** 是两种常见的函数调用约定，定义了函数调用时参数传递、栈清理和名称修饰的规则。

| 特性 | stdcall | cdecl |
|:---|:---|:---|
| **栈清理责任** | **被调用函数**清理栈（如 `ret 8`） | **调用者**清理栈（如 `add esp, 8`） |
| **参数传递顺序** | 从右到左 | 从右到左 |
| **名称修饰** | `_func@N`（N = 参数总字节数，如 `_sum@8`） | `_func`（如 `_sum`） |
| **可变参数** | ❌ 不支持 | ✅ 支持（如 `printf`） |
| **典型应用** | Windows API（`MessageBox`, `WinMain` 等） | 标准 C 库（`printf`, `malloc` 等） |

### 7.2 栈清理示例

假设函数 `sum(int a, int b)` 被调用：

**stdcall**（被调用者清理）：
```asm
push 3           ; 参数 b
push 5           ; 参数 a
call _sum@8      ; 函数返回时执行 ret 8，自动清理 8 字节栈
```

**cdecl**（调用者清理）：
```asm
push 3           ; 参数 b
push 5           ; 参数 a
call _sum        ; 调用函数
add esp, 8       ; 调用者手动清理 8 字节栈
```

### 7.3 C 语言声明示例

```c
// stdcall（Windows API 常用）
__declspec(dllexport) int __stdcall sum_stdcall(int a, int b) { return a + b; }

// cdecl（默认）
__declspec(dllexport) int __cdecl sum_cdecl(int a, int b) { return a + b; }
```

### 7.4 如何确定 DLL 函数的调用约定

```bash
# Windows
dumpbin /exports example.dll
# _func@8 → stdcall
# _func   → cdecl

# Linux
nm -D libexample.so
```

> [!important] 错误约定的后果
> 调用者与被调用者的约定不匹配 → 栈指针（ESP）指向错误位置 → 程序崩溃（如 `0xC0000005` 内存访问违规）。

---

## 八、extern "stdcall" 与 extern "C"

### 8.1 核心概念

在 Rust 等跨语言编程中，`extern "stdcall"` 和 `extern "C"` 是两种不同的**函数调用约定声明**。

| 声明 | 调用约定 | 典型应用 |
|:---|:---|:---|
| `extern "C"` | **cdecl**（默认） | 跨平台 C 库、Unix/Linux 系统 API |
| `extern "stdcall"` | **stdcall** | Windows API、COM 组件 |

### 8.2 关键区别

| 特性 | `extern "C"` | `extern "stdcall"` |
|:---|:---|:---|
| 栈清理 | 调用者清理（cdecl） | 被调用者清理（stdcall） |
| 名称修饰 | `_func` | `_func@N` |
| 可变参数 | ✅ 支持 | ❌ 不支持 |
| 平台 | 跨平台通用 | 主要用于 Windows |

### 8.3 Rust 代码示例

**调用 C 标准库（extern "C"）**：

```rust
extern "C" {
    fn printf(format: *const u8, ...) -> i32;
}
fn main() {
    unsafe { printf(b"Hello, %s!\0".as_ptr(), b"World\0".as_ptr()); }
}
```

**调用 Windows API（extern "stdcall"）**：

```rust
#[link(name = "user32")]
extern "stdcall" {
    fn MessageBoxA(
        hWnd: isize, text: *const u8,
        caption: *const u8, uType: u32
    ) -> i32;
}
fn main() {
    unsafe {
        MessageBoxA(0, b"Hello!\0".as_ptr(), b"Rust\0".as_ptr(), 0);
    }
}
```

### 8.4 选型

| 场景 | 推荐约定 |
|:---|:---|
| 调用标准 C 库 | `extern "C"` |
| 调用 Windows API | `extern "stdcall"` |
| 编写 Rust 库供 C 调用 | `#[no_mangle] pub extern "C"` |
| 跨平台且需兼容 Windows | 条件编译 `#[cfg(windows)] extern "stdcall"` |

---

## 九、Git 忽略规则：排除与例外

### 9.1 基本语法

```gitignore
# 忽略所有 data 目录
data/

# 但保留 data/game 目录及其内容
!data/game/
```

**关键规则**：
- `data/` — 末尾斜杠确保仅匹配目录而非同名文件，递归忽略所有子目录
- `!data/game/` — 否定符 `!` 重新包含指定路径，路径需写出完整子目录结构

### 9.2 通配符匹配子目录

保留 `data` 下所有以 `game` 开头的子目录：

```gitignore
# 忽略 data 目录下的所有内容
data/*

# 保留所有以 "game" 开头的子目录及其内容
!data/game*/
!data/game*/**
```

- `data/*` — 忽略 data 下的直接子项，但不完全排除 data 目录本身
- `!data/game*/` — 通配符 `*` 匹配所有以 game 开头的目录名
- `!data/game*/**` — 进一步包含这些子目录下的所有内容

### 9.3 注意事项

| 要点 | 说明 |
|:---|:---|
| **顺序敏感** | 先声明忽略规则，再声明例外规则 |
| **已提交文件** | 若 data 目录已提交，需先执行 `git rm -r --cached data` |
| **验证配置** | `git check-ignore -v <path>` 检查某文件是否被忽略 |
| **查看状态** | `git status` 确认最终效果 |

### 9.4 常见扩展场景

```gitignore
# 仅保留特定文件类型
data/*
!data/*.json

# 多层嵌套匹配
logs/**/*.log
!logs/important/**/*.log
```
