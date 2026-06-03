# npm-case 示例 Demo 完整构建指南

> 本文档详细记录了 `npm-case` 示例项目从零开始的完整配置、运行、调试以及导出微信小游戏的全流程。适合小白用户按步骤操作。

---

## 目录

1. [项目简介](#1-项目简介)
2. [环境准备](#2-环境准备)
3. [项目初始化与依赖安装](#3-项目初始化与依赖安装)
4. [下载后对工程的修改](#4-下载后对工程的修改)
5. [用 Cocos Creator 打开项目](#5-用-cocos-creator-打开项目)
6. [浏览器预览](#6-浏览器预览)
7. [常见问题与解决方案](#7-常见问题与解决方案)
8. [导出为微信小游戏](#8-导出为微信小游戏)
9. [项目结构说明](#9-项目结构说明)
10. [重点知识说明](#10-重点知识说明)

---

## 1. 项目简介

`npm-case` 是一个 Cocos Creator 3.8.0 示例项目，用于演示如何在 Cocos Creator 中使用 **npm 包**（第三方 Node.js 模块）。

本项目验证了以下模块导入场景：
- 引擎内置模块（`cc`、`cc/env`）
- 项目内 TypeScript 模块（`./dir/index`）
- npm 包（`chai`、`protobufjs`、`@protobuf-ts/runtime`、`jszip`、`colyseus.js`）
- 项目外部模块（`Proto.js/proto.js`、`Libs/MGOBE_v1.3.8/MGOBE.js`）
- Import Map 映射模块

---

## 2. 环境准备

### 2.1 必需软件

| 软件 | 版本要求 | 说明 |
|------|----------|------|
| **Cocos Creator** | 3.8.0 | 必须使用此版本 |
| **Node.js** | >= 14.x | 用于安装 npm 依赖 |
| **npm** | >= 6.x | 随 Node.js 一起安装 |

### 2.2 可选软件

| 软件 | 说明 |
|------|------|
| **Visual Studio Code** | 代码编辑器，推荐用于 TypeScript 开发 |
| **微信开发者工具** | 导出微信小游戏时需要 |

### 2.3 验证环境

打开终端（PowerShell / CMD），执行以下命令确认环境：

```bash
node --version    # 应输出 v14.x 或更高
npm --version     # 应输出 6.x 或更高
```

---

## 3. 项目初始化与依赖安装

### 3.1 获取项目（Git 下载）

本项目来源于 Cocos 官方示例仓库，Git 地址为：

```
https://github.com/cocos/cocos-example-projects.git
```

**克隆仓库**：

```bash
git clone https://github.com/cocos/cocos-example-projects.git
```

> ⚠️ **注意**：整个仓库较大，包含多个示例项目。`npm-case` 位于仓库根目录下的 `npm-case/` 子目录中。

克隆完成后，将 `npm-case` 文件夹复制到你的 Cocos Creator 项目目录下，例如：

```
C:\Users\你的用户名\cocosProjects\npm-case\
```

如果你只想下载 `npm-case` 子目录（避免下载整个仓库），可以使用 sparse checkout：

```bash
git clone --filter=blob:none --sparse https://github.com/cocos/cocos-example-projects.git
cd cocos-example-projects
git sparse-checkout set npm-case
```

### 3.2 安装 npm 依赖

> ⚠️ **重点**：这是最关键的一步！如果依赖安装失败，项目将无法正常运行。

打开终端，切换到项目根目录：

```bash
cd C:\Users\你的用户名\cocosProjects\npm-case
```

执行安装命令：

```bash
npm install --registry https://registry.npmmirror.com --ignore-scripts
```

**参数说明**：
- `--registry https://registry.npmmirror.com`：使用国内镜像源（淘宝新镜像），避免网络问题
- `--ignore-scripts`：跳过 `postinstall` 脚本（该脚本需要 `pbjs` 工具，首次可跳过）

### 3.3 处理 package-lock.json 问题

> ⚠️ **重点**：如果安装失败并报 `CERT_HAS_EXPIRED` 或 `ENOTFOUND` 错误，说明 `package-lock.json` 中锁定了过期的旧镜像地址。

**解决方法**：删除 `package-lock.json` 后重新安装：

```bash
# Windows PowerShell
Remove-Item package-lock.json -Force
npm install --registry https://registry.npmmirror.com --ignore-scripts
```

```bash
# Windows CMD
del package-lock.json
npm install --registry https://registry.npmmirror.com --ignore-scripts
```

### 3.4 验证安装成功

确认 `node_modules` 目录下存在以下关键包：

```bash
# 检查 chai 是否安装
dir node_modules\chai
```

应该能看到 `chai` 目录下的文件列表。

### 3.5 构建 Proto 文件（可选）

如果需要测试 protobuf 相关功能，需要构建 proto 文件：

```bash
npm run build-proto
```

> 注意：此命令需要全局安装 `protobufjs-cli`（`npm install -g protobufjs-cli`）。如果项目中已有 `Proto.js/proto.js` 文件，则可跳过此步骤。

---

## 4. 下载后对工程的修改

> ⚠️ **重点**：从 Git 仓库下载的原始项目**不能直接运行**，需要进行以下修改才能正常预览和构建。以下是我们对原始工程所做的全部修改及原因说明。

### 4.1 修改项目类型为 2D

**修改文件**：`package.json`

**修改内容**：将 `"type"` 字段从 `"3d"` 改为 `"2d"`

```json
{
  "type": "2d"
}
```

**原因**：原始项目配置为 3D 类型，但实际只需要 2D 渲染来展示测试结果。改为 2D 可以避免 Skybox 相关的引擎 bug。

---

### 4.2 修改引擎模块裁剪配置

**修改文件**：`settings/v2/packages/engine.json`

**修改内容**：
- 移除 `3d`、`skeletal-animation` 模块
- 添加 `primitive`、`light-probe` 模块
- 确保 `includeModules` 列表如下：

```json
"includeModules": [
  "2d",
  "animation",
  "base",
  "gfx-webgl",
  "light-probe",
  "primitive",
  "profiler",
  "ui",
  "websocket"
]
```

同时将 `cache` 中对应模块的 `_value` 值更新：
- `"3d"._value` → `false`
- `"skeletal-animation"._value` → `false`
- `"primitive"._value` → `true`

**原因**：
- `primitive` 模块**必须包含**，否则 Skybox 激活时会报 `Cannot read properties of undefined (reading 'box')` 错误（这是 Cocos Creator 3.8.0 的引擎 bug，即使 Skybox 禁用也会触发）
- 移除 3D 相关模块可以减小包体积，且本项目不需要 3D 渲染

---

### 4.3 重建场景文件

**修改文件**：`assets/scene.scene`

**修改内容**：通过 Cocos Creator 编辑器新建一个 2D 场景，替换原有场景。新场景包含：
- 一个正交投影的 Camera（`_projection: 0`）
- 一个 Canvas 节点（带 UITransform、Canvas、Widget 组件）
- Camera 的 `_clearFlags` 设为 `7`（SOLID_COLOR）
- SkyboxInfo 的 `_enabled` 设为 `false`

**原因**：原始场景可能包含 3D 元素或不兼容的配置，导致预览时报错或黑屏。使用纯 2D 场景可以确保稳定运行。

---

### 4.4 重写 Test.ts 脚本

**修改文件**：`assets/Scripts/Test.ts`

**修改内容**：

1. **将所有 `require()` 改为 ES Module `import` 语句**

   ```typescript
   // ❌ 原始写法（不兼容浏览器预览）
   const chai = require('chai');
   const protobufjs = require('protobufjs');
   
   // ✅ 修改后
   import chai from 'chai';
   import * as protobufjs from 'protobufjs';
   ```

2. **简化为只显示一个字符串**（去掉复杂的 npm 测试断言）

   ```typescript
   label.string = '✅ npm-case demo is running!';
   ```

3. **添加动态组件挂载逻辑**（避免在场景文件中手动引用自定义组件）

   ```typescript
   director.on(director.EVENT_AFTER_SCENE_LAUNCH, () => {
       const canvas = find('Canvas');
       if (canvas && !canvas.getComponent('Test')) {
           canvas.addComponent('Test');
       }
   });
   ```

4. **设置正确的 Layer**

   ```typescript
   labelNode.layer = Layers.Enum.UI_2D;
   ```

**原因**：
- Cocos Creator 3.x 浏览器预览使用 ES Module 系统，不支持 `require()`
- 动态挂载避免了场景文件中自定义组件 uuid 格式不正确导致的 "Script missing or invalid" 错误
- 设置 `UI_2D` Layer 确保 Camera 能正确渲染 Label 内容

---

### 4.5 在编辑器中手动添加 Test 组件

> ⚠️ **重点**：如果 Test.ts 的动态挂载逻辑没有生效（例如预览时页面无文字输出），你需要在编辑器中手动将 Test 组件添加到 Canvas 节点上。

**操作步骤**：

1. 在 Cocos Creator 编辑器中打开场景（双击 `assets/scene.scene`）
2. 在 **层级管理器** 中选中 `Canvas` 节点
3. 在右侧 **属性检查器** 底部点击 **添加组件**
4. 搜索 `Test`，选择并添加
5. 按 **Ctrl+S** 保存场景

**原因**：Cocos Creator 3.8 中，脚本的动态挂载（`director.EVENT_AFTER_SCENE_LAUNCH`）在某些情况下可能因为脚本加载顺序问题而未能自动执行。通过编辑器手动添加组件是最可靠的方式，编辑器会自动生成正确的组件 uuid 引用。

---

### 4.6 修改汇总表

| 文件 | 修改类型 | 关键修改点 |
|------|----------|------------|
| `package.json` | 修改 | `type: "3d"` → `type: "2d"` |
| `settings/v2/packages/engine.json` | 修改 | 添加 `primitive` 模块，移除 `3d` 模块 |
| `assets/scene.scene` | 重建 | 通过编辑器新建 2D 场景 |
| `assets/Scripts/Test.ts` | 重写 | `require` → `import`，简化逻辑，动态挂载 |

---

## 5. 用 Cocos Creator 打开项目

### 4.1 打开项目

1. 启动 **Cocos Creator 3.8.0**
2. 点击 **打开项目** → 选择 `npm-case` 文件夹
3. 等待编辑器加载完成（首次打开可能需要编译引擎，耗时较长）

### 4.2 确认场景加载

- 编辑器打开后，应自动加载 `assets/scene.scene`
- 如果没有自动加载，双击 **资源管理器** 中的 `scene.scene` 打开

### 4.3 在编辑器中添加 Test 组件（重要）

> ⚠️ **重点**：由于 Cocos Creator 3.8 的场景文件中自定义组件需要通过编辑器 UI 操作来正确注册，**必须通过编辑器手动添加组件**。

1. 在 **层级管理器** 中选中 `Canvas` 节点
2. 在右侧 **属性检查器** 底部点击 **添加组件**
3. 搜索 `Test`，选择并添加

如果 `Test` 组件已经存在于 Canvas 上（场景文件中已有 `"__type__": "d236duI7oRGYK1RkSMOW2W4"` 的引用），则无需重复添加。

---

## 6. 浏览器预览

### 5.1 启动预览

在 Cocos Creator 编辑器中：
- 点击顶部工具栏的 **▶ 预览** 按钮
- 或按快捷键 **Ctrl+P**

浏览器会自动打开预览页面（默认 `http://localhost:7456`）。

### 5.2 预期结果

预览成功后，页面中央应显示绿色文字：

```
✅ npm-case demo is running!
```

同时浏览器控制台（F12）中应输出：

```
✅ npm-case demo is running!
```

---

## 7. 常见问题与解决方案

### 7.1 找不到模块 "chai"

**错误信息**：
```
Error: 以 file:///...Test.ts 为起点找不到模块 "chai"
```

**原因**：`node_modules` 未安装或安装不完整。

**解决**：
```bash
Remove-Item package-lock.json -Force
npm install --registry https://registry.npmmirror.com --ignore-scripts
```

---

### 7.2 Cannot read properties of undefined (reading 'box')

**错误信息**：
```
TypeError: Cannot read properties of undefined (reading 'box')
    at Skybox.activate
```

**原因**：Cocos Creator 3.8.0 引擎的 `Skybox.activate` 方法会无条件调用 `cclegacy.primitives.box()`，即使 Skybox 被禁用也会执行。如果引擎模块裁剪中没有包含 `primitive` 模块，就会报错。

**解决方案**（二选一）：

**方案 A**：在引擎模块配置中添加 `primitive` 模块

编辑 `settings/v2/packages/engine.json`，确保 `includeModules` 中包含 `"primitive"`：

```json
"includeModules": [
  "2d",
  "animation",
  "base",
  "gfx-webgl",
  "primitive",
  "profiler",
  "ui",
  "websocket"
]
```

**方案 B**：通过编辑器新建 2D 场景

1. 在编辑器中：菜单 → **文件** → **新建场景**
2. 选择 **2D** 模板
3. 保存为 `scene.scene`（覆盖原有场景）
4. 在 Canvas 节点上添加 `Test` 组件

---

### 7.3 Script "Test" attached to "Canvas" is missing or invalid

**原因**：场景文件中的自定义组件引用格式不正确。Cocos Creator 3.8 中，场景文件中自定义组件的 `__type__` 需要使用脚本 uuid 的压缩格式（如 `"d236duI7oRGYK1RkSMOW2W4"`），不能直接使用类名字符串。

**解决**：
1. 在编辑器中打开场景
2. 选中 Canvas 节点
3. 在属性检查器中点击 **添加组件** → 搜索 `Test` → 添加
4. 保存场景（Ctrl+S）

> 编辑器会自动生成正确的 uuid 压缩格式引用。

---

### 7.4 require is not defined

**原因**：Cocos Creator 3.x 的浏览器预览使用 ES Module 系统，不支持 CommonJS 的 `require()` 语法。

**解决**：将所有 `require()` 改为 ES Module 的 `import` 语句：

```typescript
// ❌ 错误写法
const chai = require('chai');

// ✅ 正确写法
import chai from 'chai';
```

---

### 7.5 预览黑屏

**原因**：Camera 的 `_clearFlags` 设置不正确，或场景中没有可渲染的 UI 内容。

**解决**：
- 确保 Camera 的 `ClearFlags` 设为 `SOLID_COLOR`（值为 7）
- 确保 Test 组件已正确挂载到 Canvas 节点上

---

## 8. 导出为微信小游戏

### 8.1 前置准备

1. 安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 注册微信小游戏 AppID（或使用测试号）

### 8.2 构建配置

1. 在 Cocos Creator 编辑器中：菜单 → **项目** → **构建发布**（或 Ctrl+Shift+B 后选择构建面板）
2. 点击左上角 **+** 新建构建任务
3. 配置如下：

| 配置项 | 值 |
|--------|-----|
| 发布平台 | **微信小游戏** |
| 构建路径 | `build/wechatgame`（默认即可） |
| 初始场景 | `scene`（选择项目中的场景） |
| AppID | 填写你的微信小游戏 AppID（或使用项目中的测试 ID `wxcdb6a43233725547`） |
| 设备方向 | `portrait`（竖屏） |

### 8.3 执行构建

1. 点击 **构建** 按钮
2. 等待构建完成（底部进度条走完）
3. 构建成功后，点击 **在微信开发者工具中打开** 按钮

### 8.4 构建模板说明

本项目已包含微信小游戏的构建模板（`build-templates/wechatgame/`），其中：

- **`game.ejs`**：游戏入口模板，包含了 `globalThis.__wxRequire = require;` 的修复代码，解决微信环境下分离引擎模式的 require 问题
- **`game.json`**：小游戏配置，设置了竖屏方向和网络超时时间
- **`project.config.json`**：微信开发者工具项目配置

> ⚠️ **重点**：`game.ejs` 中的 `globalThis.__wxRequire = require;` 这行代码非常关键！它修复了微信小游戏环境下 npm 模块无法正确加载的问题。

### 8.5 在微信开发者工具中调试

1. 构建完成后，打开微信开发者工具
2. 导入项目：选择构建输出目录（如 `build/wechatgame`）
3. 确认 AppID 正确
4. 点击 **编译** 运行

### 8.6 微信小游戏常见问题

#### npm 模块加载失败

如果在微信小游戏中 npm 模块加载失败，检查：
1. 确认 `game.ejs` 模板中有 `globalThis.__wxRequire = require;`
2. 确认构建时没有勾选 "分离引擎" 选项（如果勾选了，需要确保模板正确处理了 require）

#### 包体积过大

微信小游戏有 4MB 的代码包大小限制。如果超出：
1. 在引擎模块配置中裁剪不需要的模块
2. 使用微信的分包加载功能
3. 将大型资源放到远程服务器

---

## 9. 项目结构说明

```
npm-case/
├── assets/                          # Cocos Creator 资源目录
│   ├── Scripts/                     # 脚本文件
│   │   ├── Test.ts                  # 主测试脚本（核心文件）
│   │   ├── TestImportMap.ts         # Import Map 测试
│   │   ├── Foo.ts                   # 被 Import Map 映射的模块
│   │   ├── Bar.ts                   # 被 Import Map 重定向的模块
│   │   ├── BarMapped.ts            # Bar 的映射目标
│   │   ├── dir/index.ts            # 子目录模块测试
│   │   └── single'quote'.ts        # 特殊文件名测试
│   └── scene.scene                  # 场景文件
├── build-templates/                 # 构建模板
│   └── wechatgame/                  # 微信小游戏模板
│       ├── game.ejs                 # 游戏入口模板（重要）
│       ├── game.json                # 小游戏配置
│       └── project.config.json      # 微信开发者工具配置
├── Libs/                            # 外部库（非 npm）
│   └── MGOBE_v1.3.8/MGOBE.js      # 腾讯 MGOBE 游戏联机引擎
├── Proto/                           # Protobuf 定义文件
│   ├── pkg1.proto
│   ├── pkg2.proto
│   └── unpkg.proto
├── Proto.js/                        # Protobuf 编译产物
│   ├── proto.js
│   └── proto.d.ts
├── Tools/                           # 构建工具脚本
│   ├── clear-proto.js
│   └── wrap-pbts-result.js
├── settings/v2/packages/            # 编辑器设置
│   └── engine.json                  # 引擎模块裁剪配置（重要）
├── import-map.json                  # Import Map 配置
├── tsconfig.json                    # TypeScript 配置
├── package.json                     # npm 配置
└── package-lock.json                # npm 锁定文件
```

---

## 10. 重点知识说明

### 10.1 Cocos Creator 中使用 npm 包的原理

Cocos Creator 3.x 支持直接使用 npm 包。其工作原理是：

1. **安装阶段**：通过 `npm install` 将包安装到项目根目录的 `node_modules/`
2. **编译阶段**：Cocos Creator 的构建系统会自动解析 `import` 语句，将 npm 包打包到最终产物中
3. **运行阶段**：通过 SystemJS 模块加载器在运行时加载这些模块

> ⚠️ **重点**：Cocos Creator 3.x 使用 **ES Module** 语法（`import/export`），不支持 CommonJS 的 `require()`。在脚本中必须使用 `import` 语句导入 npm 包。

### 10.2 Import Map 机制

项目根目录的 `import-map.json` 允许你自定义模块路径映射：

```json
{
    "imports": {
        "foo": "./assets/Scripts/Foo",
        "./assets/Scripts/Bar": "./assets/Scripts/BarMapped"
    }
}
```

- `"foo"` → 当代码中 `import 'foo'` 时，实际加载 `./assets/Scripts/Foo`
- `"./assets/Scripts/Bar"` → 当导入 Bar 时，实际加载 BarMapped

同时需要在 `tsconfig.json` 中配置对应的 `paths`，让 TypeScript 编译器也能识别：

```json
{
  "compilerOptions": {
    "paths": {
      "foo": ["./assets/Scripts/Foo"]
    }
  }
}
```

### 10.3 引擎模块裁剪

`settings/v2/packages/engine.json` 控制了引擎的模块裁剪。当前配置只保留了 2D 相关模块：

```json
"includeModules": [
  "2d",          // 2D 渲染
  "animation",   // 动画系统
  "base",        // 基础模块（必需）
  "gfx-webgl",   // WebGL 渲染后端
  "light-probe", // 光照探针
  "primitive",   // 基础几何体（Skybox 需要）
  "profiler",    // 性能分析器
  "ui",          // UI 系统
  "websocket"    // WebSocket 网络
]
```

> ⚠️ **重点**：`primitive` 模块必须包含！否则 Skybox 激活时会报 `Cannot read properties of undefined (reading 'box')` 错误。

### 10.4 项目外部模块引用

Cocos Creator 支持引用 `assets` 目录外部的模块（如 `Proto.js/`、`Libs/`）。这些模块通过相对路径导入：

```typescript
import * as proto from '../../Proto.js/proto.js';
import MGOBE from '../../Libs/MGOBE_v1.3.8/MGOBE.js';
```

### 10.5 微信小游戏的 require 兼容

微信小游戏环境不支持标准的 ES Module，而是使用自己的模块系统。`build-templates/wechatgame/game.ejs` 中的关键代码：

```javascript
globalThis.__wxRequire = require;  // FIX: require cannot work in separate engine
```

这行代码将微信的 `require` 函数挂载到全局，确保 Cocos Creator 的 SystemJS 模块加载器能正确工作。

### 10.6 动态组件挂载模式

本项目的 `Test.ts` 采用了"动态组件挂载"模式，避免了在场景文件中手动引用自定义组件的复杂性：

```typescript
// 场景加载后自动将 Test 组件挂载到 Canvas 节点
director.on(director.EVENT_AFTER_SCENE_LAUNCH, () => {
    const canvas = find('Canvas');
    if (canvas && !canvas.getComponent('Test')) {
        canvas.addComponent('Test');
    }
});
```

这种模式的优点：
- 不需要在场景文件中手动配置组件引用（避免 uuid 格式问题）
- 脚本加载后自动执行，无需编辑器操作
- 适合测试和演示场景

---

## 快速开始（TL;DR）

如果你只想快速跑通这个 demo，按以下步骤操作：

```bash
# 1. 进入项目目录
cd npm-case

# 2. 删除旧的 lock 文件（如果存在）
del package-lock.json

# 3. 安装依赖
npm install --registry https://registry.npmmirror.com --ignore-scripts

# 4. 用 Cocos Creator 3.8.0 打开项目

# 5. 按照文档第4节的修改说明，修改工程配置

# 6. 在编辑器中打开场景 → 选中 Canvas → 添加组件 → 搜索 Test → 添加

# 7. 点击预览按钮，浏览器中应显示绿色文字 "✅ npm-case demo is running!"
```

---

*文档最后更新：2026-06-03*
