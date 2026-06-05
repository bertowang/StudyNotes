# hls.js 代码工程深度分析文档

> **文档版本**: 1.0  
> **作者**: 汪亮 bertonwang  
> **邮箱**: 47608843@qq.com  
> **更新日期**: 2026-06-04  
> **目标读者**: 新手入门 + 高级开发者深入学习  
> **项目地址**: https://github.com/video-dev/hls.js

---

## 目录

1. [项目概述](#1-项目概述)
2. [架构总览](#2-架构总览)
3. [核心类与模块详解](#3-核心类与模块详解)
4. [关键流程分析](#4-关键流程分析)
5. [Seek 操作与 Buffer 管理深度分析](#5-seek-操作与-buffer-管理深度分析)
6. [音视频 PTS 处理逻辑深度分析](#6-音视频-pts-处理逻辑深度分析)
7. [Transmuxer 与 MP4Remuxer 深度分析](#7-transmuxer-与-mp4remuxer-深度分析)
8. [配置系统详解](#8-配置系统详解)
9. [事件系统](#9-事件系统)
10. [新手入门指南](#10-新手入门指南)
11. [高手进阶话题](#11-高手进阶话题)

---

## 1. 项目概述

### 1.1 什么是 hls.js

hls.js 是一个 JavaScript 库，实现了 HTTP Live Streaming (HLS) 客户端功能，允许在支持 MediaSource Extensions (MSE) 的浏览器中播放 HLS 流，而无需任何服务器端转码。

#### 为什么需要 hls.js？（背景与必要性）

**1. HLS 协议的起源与优势**

HLS (HTTP Live Streaming) 是 Apple 于 2009 年提出的基于 HTTP 的流媒体网络传输协议。相比传统流媒体协议（如 RTMP、RTSP），HLS 具有显著优势：

| 对比维度 | HLS | 传统协议 (RTMP/RTSP) |
|----------|-----|----------------------|
| 传输方式 | 基于 HTTP/HTTPS | 专用 TCP 连接 |
| 防火墙穿透 | ✅ 使用标准 HTTP 端口 (80/443) | ❌ 常被防火墙拦截 |
| CDN 支持 | ✅ 天然支持 | ❌ 需要特殊配置 |
| 自适应码率 | ✅ 原生支持 | ❌ 实现复杂 |
| 加密支持 | ✅ AES-128/SAMPLE-AES | ❌ 需额外实现 |

**2. 浏览器原生支持的局限性**

虽然 HLS 在 Apple 生态（Safari、iOS）中有原生支持，但在其他浏览器中存在严重兼容性问题：

```text
┌────────────────────────────────────────────────────────────────┐
│                    浏览器 HLS 原生支持情况                    │
├────────────────────────────────────────────────────────────────┤
│  Safari (macOS/iOS)     │  ✅ 原生支持 HLS                  │
│  Safari (Windows)       │  ❌ 不支持                        │
│  Chrome                 │  ❌ 不支持（需插件或转码）        │
│  Firefox                │  ❌ 不支持                        │
│  Edge                   │  ❌ 不支持（旧版）                │
│  Android WebView        │  ❌ 不支持                        │
└────────────────────────────────────────────────────────────────┘
```

**核心问题**：除了 Safari，其他浏览器**无法直接播放 HLS 流**。

**3. hls.js 的解决方案**

hls.js 通过在浏览器端实现 HLS 客户端协议，完美解决了跨浏览器兼容性问题：

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                        没有 hls.js 的世界                              │
├─────────────────────────────────────────────────────────────────────────┤
│  用户访问网站                                                          │
│       │                                                                │
│       ▼                                                                │
│  HLS 流 (example.com/stream.m3u8)                                     │
│       │                                                                │
│       ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  浏览器判断                                               │       │
│  │  ├─ Safari: ✅ 直接播放                                 │       │
│  │  └─ 其他浏览器: ❌ 无法播放，需要服务器端转码为 fMP4  │       │
│  └─────────────────────────────────────────────────────────────┘       │
│       │                                                                │
│       ▼                                                                │
│  服务器必须用 FFmpeg 等工具将 HLS 实时转码为 fMP4                    │
│  → 高昂的服务器成本                                                    │
│  → 转码延迟高                                                         │
│  → 无法利用 HLS 的自适应码率优势                                      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        使用 hls.js 的世界                             │
├─────────────────────────────────────────────────────────────────────────┤
│  用户访问网站                                                          │
│       │                                                                │
│       ▼                                                                │
│  引入 hls.js (<script src="hls.js"></script>)                         │
│       │                                                                │
│       ▼                                                                │
hls.js 在浏览器端：                                                   │
│  1. 下载并解析 M3U8 播放列表                                          │
│  2. 通过 MSE API 将 TS 片段转封装为 fMP4（fragmented MP4）       │
│  3. 追加到 SourceBuffer 实现无缝播放                                  ││       │                                                                │
│       ▼                                                                │
│  ✅ 所有支持 MSE 的浏览器都能播放 HLS 流                             │
│  ✅ 无需服务器端转码，节省大量成本                                    │
│  ✅ 支持自适应码率、加密、低延迟等高级特性                            │
└─────────────────────────────────────────────────────────────────────────┘
```

**4. 核心价值总结**

| 价值点 | 说明 |
|--------|------|
| **跨浏览器兼容** | 让 Chrome、Firefox、Edge 等非 Safari 浏览器也能播放 HLS |
| **零服务器端成本** | 无需转码服务器，HLS 源可以直接使用 |
| **充分利用 HLS 优势** | 支持自适应码率、加密、低延迟等 HLS 原生特性 |
| **开源活跃** | GitHub 40k+ Stars，社区活跃，持续维护 |
| **生产级稳定性** | 被 Netflix、Twitch、Facebook 等大型平台使用 |

**5. 技术实现原理（简要）**

hls.js 的核心思路是**在浏览器端实现 HLS 客户端**：

```text
HLS 源 (M3U8 + TS 片段)
          │
          ▼
    ┌───────────┐
    │  hls.js   │  1. 解析 M3U8 播放列表
    │  核心逻辑  │  2. 下载 TS 片段
    │           │  3. 解封装 TS，提取音视频 ES 流
    └─────┬─────┘  4. 重新封装为 MP4/fMP4
          │
          ▼
    MediaSource Extensions API
    (appendBuffer → SourceBuffer)
          │
          ▼
    <video> 元素播放
```

正是因为浏览器原生不支持 HLS（除 Safari 外），hls.js 才成为 HLS 在 Web 端播放的**事实标准解决方案**。

#### 核心能力

- 解析 HLS 协议（M3U8 播放列表）
- 通过 MSE API 将音视频数据追加到 SourceBuffer
- 自适应码率 (ABR) 切换
- 处理加密内容 (AES-128, SAMPLE-AES)
- 低延迟 HLS (LL-HLS) 支持

### 1.2 技术栈

| 技术 | 用途 |
|------|------|
| TypeScript | 主要开发语言 |
| MediaSource Extensions | 浏览器底层媒体播放 API |
| SourceBuffer | 音视频数据缓冲区管理 |
| Fetch/XHR | 网络请求 |
| Web Workers (可选) | 转复用处理 |

---

## 2. 架构总览

### 2.1 核心架构图

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           Hls (核心类)                                │
│                    src/hls.ts - 入口与协调者                          │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      控制器层 (Controllers)                            │
│  ┌──────────────┬──────────────┬──────────────────┬──────────────┐    │
│  │ StreamCtrl   │ BufferCtrl   │ AbrController    │ LevelCtrl    │    │
│  │ 流控制器     │ 缓冲控制器   │ 自适应码率       │ 级别控制器   │    │
│  └──────────────┴──────────────┴──────────────────┴──────────────┘    │
│  ┌──────────────┬──────────────┬──────────────────┬──────────────┐    │
│  │ GapController│ SubtitleCtrl │ AudioTrackCtrl   │ EMEController│    │
│  │ 间隙控制器   │ 字幕控制器   │ 音轨控制器       │ DRM控制器   │    │
│  └──────────────┴──────────────┴──────────────────┴──────────────┘    │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      加载器层 (Loaders)                               │
│  ┌──────────────┬──────────────┬──────────────────┐                  │
│  │ FragmentLoader│ PlaylistLoader│ KeyLoader       │                  │
│  │ 片段加载器   │ 播放列表加载 │ 密钥加载器      │                  │
│  └──────────────┴──────────────┴──────────────────┘                  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      处理层 (Processing)                              │
│  ┌──────────────┬──────────────┬──────────────────┐                  │
│  │ M3U8Parser   │ Transmuxer   │ MP4Remuxer      │                  │
│  │ M3U8解析器   │ 转复用器     │ MP4重复用器     │                  │
│  └──────────────┴──────────────┴──────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```text
src/
├── hls.ts                      # 核心 Hls 类
├── config.ts                   # 配置系统与默认值
├── events.ts                   # 事件枚举与类型定义
├── errors.ts                   # 错误类型定义
├── types/                      # TypeScript 类型定义
├── controller/                 # 控制器实现
│   ├── stream-controller.ts    # 流控制器 (主)
│   ├── base-stream-controller.ts # 流控制器基类
│   ├── buffer-controller.ts    # 缓冲控制器
│   ├── gap-controller.ts       # 间隙控制器
│   ├── abr-controller.ts       # 自适应码率控制器
│   ├── level-controller.ts     # 级别控制器
│   ├── fragment-tracker.ts     # 片段跟踪器
│   └── ...
├── loader/                     # 加载器实现
│   ├── fragment-loader.ts      # 片段加载器
│   ├── playlist-loader.ts      # 播放列表加载器
│   ├── fragment.ts             # Fragment 类定义
│   └── level-details.ts        # LevelDetails 类
├── demux/                      # 解复用器
│   ├── transmuxer.ts          # 转复用器入口
│   ├── tsdemuxer.ts           # TS 解复用
│   └── mp4demuxer.ts          # MP4 解复用
├── remux/                      # 重复用器
│   └── mp4-remuxer.ts         # MP4 重复用
└── utils/                      # 工具函数
    ├── codecs.ts               # 编解码器工具
    ├── logger.ts               # 日志工具
    └── ...
```

---

## 3. 核心类与模块详解

### 3.1 Hls 核心类 (`src/hls.ts`)

`Hls` 类是整个库的入口点和协调者，负责：
- 初始化所有控制器
- 管理配置
- 触发和处理事件
- 提供公共 API

**关键代码片段**：
```typescript
export default class Hls extends HlsEventEmitter implements HlsAPI {
  private readonly coreComponents: CoreComponent[];
  private readonly networkControllers: NetworkComponentAPI[];
  
  constructor(userConfig: Partial<HlsConfig> = {}) {
    super();
    // 合并用户配置与默认配置
    const config = this.config = new HlsConfig(userConfig);
    // 初始化所有核心组件
    this.capLevelController = new CapLevelController(this);
    this.abrController = new AbrController(this);
    this.bufferController = new BufferController(this, this.streamController);
    // ... 更多组件初始化
  }
}
```

**新手提示**：`Hls` 类继承自 `HlsEventEmitter`，这意味着它天然支持事件监听和触发，这是理解整个库运作方式的关键。

### 3.2 配置系统 (`src/config.ts`)

配置系统定义了 hls.js 的所有可调参数，位于 `src/config.ts`。

**重要配置项**：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `maxBufferLength` | 30 (VoD) / 60 (Live) | 最大缓冲长度（秒） |
| `maxBufferHole` | 0.1 | 缓冲区之间允许的最大间隙（秒） |
| `maxFragLookUpTolerance` | 0.25 | 片段查找容差 |
| `nudgeOnVideoHole` | true | 视频孔洞时是否微调 currentTime |
| `abrEwmaDefaultEstimate` | 5000000 | 默认带宽估计 (bps) |
| `startLevel` | -1 | 启动级别 (-1 表示自动) |

**配置合并逻辑**：
```typescript
// 用户配置会覆盖默认配置
const config = { ...hlsDefaultConfig, ...userConfig };
```

### 3.3 事件系统 (`src/events.ts`)

hls.js 使用事件驱动架构，所有模块通过事件进行通信。

**核心事件分类**：

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        事件流程图                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  MANIFEST_LOADING ──▶ MANIFEST_LOADED ──▶ MANIFEST_PARSED        │
│                                           │                        │
│                                           ▼                        │
│                                      LEVEL_LOADED                  │
│                                           │                        │
│              ┌────────────────────────────┤                        │
│              ▼                            ▼                        │
│         FRAG_LOADING                 LEVEL_SWITCHING                │
│              │                                                      │
│              ▼                                                      │
│         FRAG_LOADED                                                   │
│              │                                                      │
│              ▼                                                      │
│         FRAG_PARSING                                                │
│              │                                                      │
│              ▼                                                      │
│         FRAG_PARSED                                                 │
│              │                                                      │
│              ▼                                                      │
│         BUFFER_APPENDING                                            │
│              │                                                      │
│              ▼                                                      │
│         BUFFER_APPENDED                                             │
│              │                                                      │
│              ▼                                                      │
│         FRAG_BUFFERED                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**关键事件详解**：

| 事件 | 触发时机 | 携带数据 |
|------|----------|----------|
| `MANIFEST_PARSED` | M3U8 主播放列表解析完成 | levels, audioTracks, subtitleTracks |
| `LEVEL_LOADED` | 级别播放列表加载完成 | level, details |
| `FRAG_LOADING` | 开始加载片段 | frag, part |
| `FRAG_LOADED` | 片段加载完成 | frag, part, stats |
| `BUFFER_APPENDED` | 数据追加到 SourceBuffer | frag, part, timeRanges |
| `FRAG_BUFFERED` | 片段完全缓冲 | frag, part, stats |

### 3.4 错误系统 (`src/errors.ts`)

**错误类型 (ErrorTypes)**：
```typescript
export enum ErrorTypes {
  NETWORK_ERROR = 'networkError',
  MEDIA_ERROR = 'mediaError',
  KEY_SYSTEM_ERROR = 'keySystemError',
  MUX_ERROR = 'muxError',
  OTHER_ERROR = 'otherError',
}
```

**详细错误代码 (ErrorDetails)**：
```typescript
export enum ErrorDetails {
  // 网络错误
  MANIFEST_LOAD_ERROR = 'manifestLoadError',
  FRAG_LOAD_ERROR = 'fragLoadError',
  FRAG_LOAD_TIMEOUT = 'fragLoadTimeOut',
  
  // 媒体错误
  BUFFER_APPEND_ERROR = 'bufferAppendError',
  BUFFER_ADD_CODEC_ERROR = 'bufferAddCodecError',
  
  // ... 更多错误详情
}
```

---

## 4. 关键流程分析

### 4.1 初始化流程

```text
用户代码                 Hls 类                   控制器
   │                       │                        │
   │ new Hls(config)       │                        │
   │──────────────────────▶│                        │
   │                       │──▶ 合并配置            │
   │                       │──▶ 初始化控制器        │
   │                       │──▶ 注册事件监听        │
   │                       │                        │
   │ hls.loadSource(url)   │                        │
   │──────────────────────▶│                        │
   │                       │──▶ 触发 MANIFEST_LOADING│
   │                       │──▶ 创建 PlaylistLoader │
   │                       │                        │
   │                       │    M3U8 解析           │
   │                       │◀─── MANIFEST_PARSED ──│
   │                       │                        │
   │ hls.attachMedia(video)│                        │
   │──────────────────────▶│                        │
   │                       │──▶ 创建 MediaSource    │
   │                       │──▶ 创建 SourceBuffer   │
```

### 4.2 片段加载与缓冲流程

**状态机说明**：`StreamController` 使用状态机管理片段加载和缓冲流程，主要状态包括：
- `IDLE`：空闲状态，等待下一个操作
- `FRAG_LOADING`：正在加载片段
- `PARSING`：正在解析片段数据（demux + remux）
- `PARSED`：解析完成，准备追加到 buffer
- `BUFFER_FLUSHING`：正在刷新 buffer

```typescript
// ============================================================================
// 函数：doTick
// 功能：状态机的主循环，根据当前状态执行相应操作
// 调用时机：每次事件触发（如 fragment loaded、buffer appended）时调用
// ============================================================================
doTick() {
  switch (this.state) {
    case State.IDLE:
      // 【状态：空闲】
      // 决定下一个要加载的片段
      //   - 如果是首次播放：加载第一个片段
      //   - 如果正常播放：加载当前位置之后的片段
      //   - 如果 seek：加载 seek 位置对应的片段
      this.doTickIdle();
      break;
      
    case State.FRAG_LOADING:
      // 【状态：正在加载】
      // 等待片段加载完成（异步）
      // 加载完成后会自动触发 FRAG_LOADED 事件，然后再次调用 doTick()
      break;
      
    case State.PARSING:
      // 【状态：正在解析】
      // 将 TS 数据 demux 为音视频 ES 流，再 remux 为 fMP4
      // 这个过程可能在 Web Worker 中进行（如果配置了 enableWorker: true）
      break;
      
    case State.PARSED:
      // 【状态：解析完成】
      // 将 fMP4 数据追加到 SourceBuffer
      // 注意：appendBuffer() 是异步的，需要等待 'updateend' 事件
      this.appendToBuffer();
      break;
      
    case State.BUFFER_FLUSHING:
      // 【状态：缓冲区刷新】
      // 等待 SourceBuffer 完成当前操作
      // 刷新完成后才能继续追加数据
      break;
  }
}
```

**关键方法调用链**：
```text
doTick()                                          ← 入口点（事件驱动）
  └─▶ doTickIdle()                               ← 空闲时调用
       └─▶ getNextFragment()                      ← 选择下一个片段
            ├─▶ getFragmentAtPosition()           ← 根据当前位置找片段
            │    └─▶ findFragmentByPTS()          ← 通过 PTS 查找（详见 5.2.3）
            └─▶ loadFragment()                    ← 加载选中的片段
                 └─▶ fragmentLoader.load()        ← 发起网络请求
```

**完整生命周期流程图**：
```text
┌──────────────┐
│   doTick()   │ ← 事件触发（如 SEEKED、BUFFER_APPENDED）
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────────┐
│  State.IDLE  │────▶│  getNextFragment │ ← 选择下一个片段
└──────────────┘     └────────┬─────────┘
                              │
                              ▼
┌──────────────┐     ┌──────────────────┐
│ State.FRAG_  │────▶│  FragmentLoader  │ ← 下载 TS 片段
│ LOADING      │     │  .load()          │
└──────────────┘     └────────┬─────────┘
                              │
                              ▼
┌──────────────┐     ┌──────────────────┐
│ State.PARSING│────▶│  Transmuxer      │ ← TS → fMP4
└──────────────┘     │  .transmux()     │
                      └────────┬─────────┘
                               │
                               ▼
┌──────────────┐     ┌──────────────────┐
│ State.PARSED │────▶│  SourceBuffer    │ ← 追加到缓冲区
└──────────────┘     │  .appendBuffer() │
                      └────────┬─────────┘
                               │
                               ▼
                      ┌──────────────────┐
                      │  BUFFER_APPENDED │ ← 触发事件
                      └──────────────────┘
```

### 4.3 M3U8 解析流程 (`src/loader/m3u8-parser.ts`)

**主播放列表解析**：
```typescript
static parseMasterPlaylist(string, baseurl): ParsedMultivariantPlaylist {
  // 1. 使用正则 MASTER_PLAYLIST_REGEX 匹配
  // 2. 提取 #EXT-X-STREAM-INF 标签
  // 3. 创建 LevelParsed 对象数组
  // 4. 处理 #EXT-X-MEDIA 标签 (音轨/字幕)
}
```

**媒体播放列表解析**：
```typescript
static parseLevelPlaylist(string, baseurl, id, type): LevelDetails {
  // 1. 解析 #EXTINF 获取片段时长
  // 2. 解析片段 URI
  // 3. 处理 #EXT-X-KEY (加密)
  // 4. 处理 #EXT-X-MAP (初始化段)
  // 5. 构建 Fragment 对象数组
}
```

---

## 5. Seek 操作与 Buffer 管理深度分析

### 5.1 Seek 操作的完整流程

当用户执行 seek 操作时（无论是通过拖动进度条还是调用 API），hls.js 内部会经历以下流程：

```text
用户 Seek              Buffer Controller         Stream Controller
    │                        │                        │
    │   video.currentTime = x │                        │
    │───────────────────────▶│                        │
    │                        │──▶ 检测 buffer hole?  │
    │                        │                        │
    │                        │    (如果有 hole)       │
    │                        │──▶ nudgeOnVideoHole() │
    │                        │                        │
    │                        │   触发 BUFFER_STALLED  │
    │                        │───────────────────────▶│
    │                        │                        │
    │                        │   执行 seek 逻辑       │
    │                        │◀─── onBufferStalled ──│
    │                        │                        │
    │                        │                        │──▶ getNextFragment()
    │                        │                        │     (从新位置开始)
    │                        │                        │
    │                        │                        │──▶ 加载新片段
    │                        │   追加 buffer         │
    │                        │◀─── FRAG_LOADED ─────│
```

### 5.2 关键代码路径

#### 5.2.1 GapController 的 Seek 处理

**文件**: `src/controller/gap-controller.ts`

```typescript
// ============================================================================
// 函数：_tryNudgeStalledPlayback
// 功能：当播放器遇到 buffer hole（缓冲区空洞）导致卡顿时调用
// 返回：true 表示执行了 nudge（微调），false 表示无需处理
// ============================================================================
public _tryNudgeStalledPlayback(): boolean {
  const { media, config } = this;
  const { nudgeOnVideoHole, nudgeMaxRetry } = config;
  
  // 检查配置是否允许 nudge，且 media 元素存在
  if (nudgeOnVideoHole && media) {
    // 调用 nudgeOnVideoHole 检测是否存在 video hole
    const nudge = this.nudgeOnVideoHole(media);
    if (nudge) {
      // 检测到 hole，增加重试计数
      this.nudgeRetry++;
      return true;  // 告知调用者已执行 nudge
    }
  }
  return false;  // 无需处理
}

// ============================================================================
// 函数：nudgeOnVideoHole
// 功能：检查 video buffer 中是否存在 hole（缓冲区不连续）
// 原理：HTMLMediaElement 的 buffered 属性返回多个 TimeRange，
//       如果相邻 TimeRange 之间有间隙，就是 hole
// 返回：true 表示发现 hole 并已处理，false 表示没有 hole
// ============================================================================
private nudgeOnVideoHole(media: HTMLMediaElement): boolean {
  // 获取 video 类型的缓冲区 TimeRanges
  const videoBuffer = getBuffered(media, 'video');
  
  // 如果没有缓冲区数据，无需处理
  if (!videoBuffer || !videoBuffer.length) {
    return false;
  }
  
  // 【关键逻辑】遍历所有 buffer ranges 之间的间隙
  // 注意：i 从 1 开始，因为要比较 i-1 和 i 两个 range
  for (let i = 1; i < videoBuffer.length; i++) {
    const prevEnd = videoBuffer.end(i - 1);   // 前一个 range 的结束时间
    const currStart = videoBuffer.start(i);     // 当前 range 的开始时间
    const holeDuration = currStart - prevEnd;   // 计算间隙时长
    
    // 如果间隙超过配置的最大允许值（默认 0.1 秒）
    if (holeDuration > config.maxBufferHole) {
      // 【修复策略】将播放时间设置为前一个 range 的结束位置 + 微小偏移
      // 这样可以让播放器跳到缓冲区末尾，触发后续 buffer 加载
      media.currentTime = prevEnd + 0.001;
      return true;  // 已处理
    }
  }
  return false;  // 没有发现需要处理的 hole
}
```

#### 5.2.2 BaseStreamController 的片段选择

**文件**: `src/controller/base-stream-controller.ts`

```typescript
// ============================================================================
// 函数：getFragmentAtPosition
// 功能：根据当前播放位置，确定下一个应该加载的 Fragment（视频片段）
// 参数：
//   - bufferInfo: 当前缓冲区信息（起始位置、结束位置等）
//   - playlistType: 播放列表类型（VOD 或 LIVE）
//   - data: 可选参数，包含片段位置信息
// 返回：对应的 Fragment 对象，或 null 表示未找到
// ============================================================================
protected getFragmentAtPosition(
  bufferInfo: BufferInfo,
  playlistType: PlaylistLevelType,
  data?: { FragPosition: number }
): Fragment | null {
  const { fragPrevious, fragmentTracker } = this;
  const { contiguous, media } = bufferInfo;
  const fragPreviousEndTime = fragPrevious?.end;  // 上一个片段的结束时间
  
  // ==========================================================================
  // 【重要】backwardSeek 检测
  // 原理：比较「当前缓冲区结束位置」和「上一个片段的结束时间」
  //   - 如果 bufferInfo.end > fragPreviousEndTime：说明用户往回 seek 了
  //   - 例如：刚播完第 10 个片段（结束于 100s），用户 seek 到 50s
  //   - 此时 bufferInfo.end = 50s，fragPreviousEndTime = 100s
  //   - 差值 > 0，判定为 backwardSeek
  // ==========================================================================
  const backwardSeek = fragPreviousEndTime
    ? bufferInfo.end - fragPreviousEndTime > 0
    : false;
  
  // ==========================================================================
  // 【已修复 Bug 2】查找容差的设置
  // 问题：backwardSeek 时如果使用默认 tolerance（0.25秒），
  //       可能会错误地匹配到当前位置之后的片段
  // 解决：backwardSeek 时使用更小的 tolerance（最大 0.05秒）
  //   - 前向 seek：允许 0.25 秒的查找容差（正常播放）
  //   - 后向 seek：只允许 0.05 秒的容差（精确查找）
  // ==========================================================================
  const lookupTolerance = backwardSeek
    ? Math.min(this.config.maxFragLookUpTolerance, 0.05)
    : this.config.maxFragLookUpTolerance;
  
  // 调用核心查找函数，在片段列表中根据 PTS 找到对应的 Fragment
  return findFragmentByPTS(
    this.logPrefix,           // 日志前缀
    this.fragPrevious,       // 上一个片段（用于快速匹配）
    fragCurrentPosition,     // 当前播放位置（秒）
    this.fragPlaying,        // 正在播放的片段
    this.lastLoadedFragLevel,// 最后加载的片段级别
    playlistType,            // 播放列表类型
    fragments,               // 片段列表
    data,                    // 额外数据
    backwardSeek,            // 是否后向 seek
    lookupTolerance          // 查找容差
  );
}
```

#### 5.2.3 findFragmentByPTS 算法

```typescript
// ============================================================================
// 函数：findFragmentByPTS
// 功能：根据当前播放位置（PTS）在片段列表中找到对应的 Fragment
// 参数：
//   - logPrefix: 日志前缀（用于调试）
//   - fragPrevious: 上一个播放的片段（快速路径优化）
//   - fragCurrentPosition: 当前播放位置（秒）
//   - fragPlaying: 正在播放的片段
//   - lastLoadedFragLevel: 最后加载的片段级别
//   - type: 播放列表类型（VOD/LIVE）
//   - fragments: 所有可用片段的数组
//   - data: 包含 fragPosition 的额外数据
//   - backwardSeek: 是否是后向 seek
//   - lookupTolerance: 查找容差（秒）
// 返回：匹配的 Fragment，或 null
//
// 【算法说明】
// 1. 快速路径：如果上一个片段包含当前位置，直接返回（O(1)）
// 2. 慢速路径：线性遍历片段列表，找到包含当前位置的片段（O(n)）
//    注意：这里可以使用二分查找优化，但需要考虑 fragment 可能重叠的情况
// ============================================================================
export function findFragmentByPTS(
  logPrefix: string,
  fragPrevious: Fragment | null,
  fragCurrentPosition: number,
  fragPlaying: Fragment | null,
  lastLoadedFragLevel: number,
  type: PlaylistLevelType,
  fragments: Fragment[],
  data: { fragPosition: number } | undefined,
  backwardSeek: boolean,
  lookupTolerance: number
): Fragment | null {
  let frag: Fragment | null = null;
  
  // ==========================================================================
  // 【快速路径】检查上一个片段是否包含当前播放位置
  // 条件：fragPrevious 存在 且 当前位置 <= fragPrevious.end
  // 意义：大多数情况下，播放是连续的，直接复用上次的查找结果
  // 时间复杂度：O(1)，避免遍历整个片段列表
  // ==========================================================================
  if (fragPrevious && fragCurrentPosition <= fragPrevious.end) {
    frag = fragPrevious;
  } else {
    // ==========================================================================
    // 【慢速路径】遍历所有片段，找到包含当前位置的片段
    // 
    // 查找逻辑：
    //   - candidate.start <= fragCurrentPosition + lookupTolerance
    //     表示当前位置在这个片段的「开始时间 + 容差」范围内
    //   - 由于片段是按时间顺序排列的，找到最后一个满足条件的即可
    //   - 使用 lookupTolerance 是为了处理片段边界的微小误差
    //
    // 举例：
    //   片段0: [0s, 10s]
    //   片段1: [10s, 20s]
    //   片段2: [20s, 30s]
    //   当前位置: 10.1s，容差: 0.25s
    //   → 10.1 <= 0 + 0.25? No
    //   → 10.1 <= 10 + 0.25? Yes → frag = 片段1
    //   → 10.1 <= 20 + 0.25? Yes → frag = 片段2
    //   → 10.1 <= 30 + 0.25? Yes → frag = 片段2（最终）
    //   最终返回：片段2（即第一个 start > 当前位置 的片段）
    // ==========================================================================
    for (let i = 0; i < fragments.length; i++) {
      const candidate = fragments[i];
      // 如果当前片段的开始时间 <= 当前位置 + 容差，可能是目标
      if (candidate.start <= fragCurrentPosition + lookupTolerance) {
        frag = candidate;  // 暂时保存，继续找更精确的
      } else {
        break;  // 后续片段的开始时间更大，无需继续
      }
    }
  }
  
  return frag;
}
```

### 5.3 Buffer 管理机制

#### 5.3.1 前向缓冲区信息获取

**文件**: `src/controller/base-stream-controller.ts`

**功能说明**：`getFwdBufferInfo()` 用于获取从当前播放位置到缓冲区结束的信息，帮助决定是否需要继续加载片段。

**为什么需要这个函数？**
- ABR 决策需要：知道还有多少缓冲才能决定加载什么码率
- Buffer 管理需要：知道是否需要继续追加数据
- Seek 处理需要：判断 seek 位置是否在缓冲区内

```typescript
// ============================================================================
// 函数：getFwdBufferInfo (get Forward Buffer Info)
// 功能：获取前向缓冲区信息（从当前位置到 buffer 结束）
// 参数：
//   - bufferEnd: 缓冲区结束位置（秒）
//   - maxBufferHole: 允许的最大 buffer hole（秒）
//   - playlistType: 播放列表类型（VOD/LIVE）
// 返回：BufferInfo 对象，包含 len/start/end/nextStart
//
// 【算法原理】
// 1. 获取当前播放位置（pos）
// 2. 计算从 pos 到 bufferEnd 的长度（len）
// 3. 如果 len > 0，说明有前向缓冲，返回信息
// 4. 如果 len <= 0，说明在 hole 中，需要找下一个 buffer range
// ============================================================================
public static getFwdBufferInfo(
  bufferEnd: number,
  maxBufferHole: number,
  playlistType: PlaylistLevelType
): BufferInfo | null {
  const bwb = bufferEnd;  // 前向缓冲区结束位置
  
  // ==========================================================================
  // 【已修复 Bug 3】backwardSeek 时使用合理的 maxBufferHole
  // 问题：backwardSeek 后，pos 可能在 buffer range 的中间
  //       此时使用默认 maxBufferHole (0.1s) 可能太严格
  // 解决：backwardSeek 时使用更小的值（0.1s）
  // 
  // backwardSeek 检测：如果当前 pos 不在任何 buffer range 的开始位置
  // ==========================================================================
  const usedMaxBufferHole = backwardSeek
    ? Math.min(maxBufferHole, 0.1)  // backwardSeek: 最大 0.1s
    : maxBufferHole;                   // 正常: 使用配置值
  
  // ==========================================================================
  // 【核心逻辑】计算前向缓冲区长度
  // len = bufferEnd - pos
  //
  // 情况 A：len > 0 → 有前向缓冲
  //   返回：{ len, start: pos, end: bufferEnd, nextStart: -1 }
  //
  // 情况 B：len <= 0 → 当前在 hole 中
  //   需要找到下一个 buffer range 的开始位置（nextStart）
  // ==========================================================================
  const len = Math.max(0, bufferEnd - pos);
  
  if (len > 0) {
    // 情况 A：有前向缓冲
    return {
      len: len,          // 前向缓冲长度（秒）
      start: pos,         // 当前播放位置
      end: bufferEnd,     // 缓冲区结束位置
      nextStart: -1       // 下一个 buffer range 的开始（无）
    };
  } else {
    // 情况 B：在 hole 中，找下一个 buffer range
    const buffer = media.buffered;
    for (let i = 0; i < buffer.length; i++) {
      if (buffer.start(i) > pos) {
        // 找到下一个 buffer range
        return {
          len: 0,              // 当前没有前向缓冲
          start: pos,           // 当前位置
          end: pos,             // 结束 = 开始（在 hole 中）
          nextStart: buffer.start(i)  // 下一个 buffer range 的开始
        };
      }
    }
    return null;  // 没有找到任何 buffer range
  }
}
```

**BufferInfo 使用示例**：
```typescript
// 假设当前缓冲区情况：
//   buffer = [0-10s] [15-25s] [30-40s]
//   pos = 12s（在 hole 中）

const info = getFwdBufferInfo(40, 0.1, PlaylistLevelType.VOD);
// 返回：
// {
//   len: 0,           // 当前位置没有缓冲
//   start: 12,
//   end: 12,
//   nextStart: 15     // 下一个 buffer 从 15s 开始
// }
```

#### 5.3.2 SourceBuffer 管理

**文件**: `src/controller/buffer-controller.ts`

**SourceBuffer 简介**：
- `SourceBuffer` 是 MSE API 的核心接口
- 用于向 `MediaSource` 追加音视频数据
- 每个 `SourceBuffer` 对应一种 MIME 类型（如 `video/mp4; codecs="avc1.64001f,mp4a.40.2"`）

```typescript
// ============================================================================
// 函数：createSourceBuffers
// 功能：为每种编解码器创建对应的 SourceBuffer
// 参数：codecs - MIME 类型数组（如 ["video/mp4; codecs=avc1.64001f", ...]）
//
// 【重要】浏览器对 MIME 类型的检查
//   - 如果浏览器不支持该编解码器，会抛出 DOMException
//   - 需要先使用 MediaSource.isTypeSupported(codecs[i]) 检测
// ============================================================================
private createSourceBuffers(codecs: string[]) {
  const { mediaSource } = this;  // MediaSource 对象
  
  codecs.forEach((codec) => {
    // ==========================================================================
    // 创建 SourceBuffer
    // mediaSource.addSourceBuffer(codec) 可能抛出异常：
    //   - NotSupportedError: 不支持该 MIME 类型
    //   - InvalidStateError: MediaSource.readyState !== 'open'
    // ==========================================================================
    const sb = mediaSource.addSourceBuffer(codec);
    
    // ==========================================================================
    // 确定 codec 类型（audio 或 video）
    // 通过检查 MIME 类型字符串来判断
    // ==========================================================================
    const codecType = codec.startsWith('audio') ? 'audio' : 'video';
    
    // 保存到映射表中，后续可以通过类型访问
    this.sourceBuffers[codecType] = sb;
    
    // ==========================================================================
    // 监听 SourceBuffer 事件
    //   - 'updateend': 追加完成（可以追加下一批数据）
    //   - 'error': 发生错误
    //   - 'abort': 操作被中止
    // ==========================================================================
    sb.addEventListener('updateend', this.onSBUpdateEnd);
    sb.addEventListener('error', this.onSBError);
  });
}

// ============================================================================
// 函数：appendToSourceBuffer
// 功能：将数据追加到 SourceBuffer
// 参数：
//   - segmentData: Uint8Array，fMP4 数据（moof + mdat）
//   - type: 'audio' 或 'video'，指定目标 SourceBuffer
//
// 【重要】appendBuffer 是异步的！
//   - 调用后立即返回
//   - 实际追加操作在后台进行
//   - 完成后触发 'updateend' 事件
//   - 在 'updating' = true 时不能再次调用 appendBuffer
// ============================================================================
private appendToSourceBuffer(
  segmentData: Uint8Array,
  type: SourceBufferName
) {
  const sb = this.sourceBuffers[type];  // 获取对应的 SourceBuffer
  
  try {
    // ==========================================================================
    // 追加数据到 SourceBuffer
    // 浏览器会自动解析 fMP4 数据，提取采样信息
    // ==========================================================================
    sb.appendBuffer(segmentData);
  } catch (e) {
    // ==========================================================================
    // 错误处理
    // 常见错误：
    //   - QUOTA_EXCEEDED_ERR: 缓冲区已满（需要 evict buffer）
    //   - NotAllowedError: 在 wrong state 调用
    // ==========================================================================
    this.onBufferAppendError(e);
  }
}
```

**SourceBuffer 状态图**：
```text
┌─────────────┐
│  创建后     │
│  updating=false│
└──────┬──────┘
         │ appendBuffer()
         ▼
┌─────────────┐
│  追加中     │
│  updating=true │
└──────┬──────┘
         │ (异步操作完成)
         ▼
┌─────────────┐
│  追加完成   │
│  'updateend' │
└──────┬──────┘
         │ 可以追加下一批数据
         ▼
    （回到 updating=false）
```

**缓冲区驱逐（Buffer Eviction）**：
```typescript
// 当缓冲区太大时，浏览器可能自动驱逐旧数据
// hls.js 需要处理这种情况：
private onBufferEviction(e) {
  // 1. 检测哪些片段被驱逐了
  this.fragmentTracker.detectEvictedFragments(...);
  
  // 2. 重新加载被驱逐的片段（如果需要）
  if (shouldReload) {
    this.loadFragment(...);
  }
}
```

### 5.4 Seek 后 initPTS 的计算逻辑

**问题**：每次 seek 后，是否会重新调用 6.4.1 的初始化时间戳（initPTS）计算？

**答案**：**不会**。seek 操作**不会**触发 initPTS 的重新计算。

#### 5.4.1 initPTS 的计算时机

initPTS 的计算发生在以下时机（**仅在首次加载片段或连续性变更时**）：

```typescript
// 文件：src/remux/mp4-remuxer.ts
// initPTS 的计算发生在 remux() 方法中，而非 seek 时

remux(audioTrack, videoTrack, timeOffset, accurateTimeOffset) {
  // ...
  
  // initPTS 仅在以下条件满足时计算：
  // 1. 首次加载片段（this._initPTS === undefined）
  // 2. 或者片段的 continuity counter (cc) 发生变化
  
  if (this._initPTS === undefined || frag.cc !== this._lastCC) {
    // 计算 initPTS
    this._initPTS = computeInitPts(...);
    this._lastCC = frag.cc;
  }
  
  // seek 操作不会改变 cc 值，因此不会触发重新计算
}
```

#### 5.4.2 为什么 seek 后不需要重新计算 initPTS？

| 原因 | 说明 |
|------|------|
| **initPTS 是相对偏移量** | initPTS 表示片段时间戳相对于 presentationTime 的偏移，**与播放位置无关** |
| **基于 continuity counter** | initPTS 按 `cc`（连续性计数器）存储，只在 `cc` 变化时重新计算 |
| **时间戳连续性** | seek 后加载的片段与之前片段属于同一连续性流，时间戳体系一致 |
| **性能考虑** | 避免每次 seek 都重新转封装已缓冲的片段 |

#### 5.4.3 initPTS 的存储结构

```typescript
// 文件：src/controller/base-stream-controller.ts
// initPTS 按 cc 存储，支持多码率/多 Period 场景

protected initPTS: TimestampOffset[] = [];
// 数组索引 = cc (continuity counter)
// 值 = 该连续性下的 initPTS 偏移量

// 当 cc 变化时（如 LIVE 流 discontinuity），才会重新计算
```

**示意图**：
```text
Seek 操作                   initPTS 计算
──────────                 ──────────────
    │                            │
    ▼                            ▼
用户拖动进度条             首次加载片段 (cc=0)
    │                      → 计算 initPTS[0]
    ▼                            │
seek 到 10:00             加载新片段 (cc=0)
    │                      → 复用 initPTS[0] (不重新计算)
    ▼                            │
缓冲区有该位置数据          cc 变化 (cc=1)
    │                      → 重新计算 initPTS[1]
    ▼                            │
直接播放                    继续播放...
```

#### 5.4.4 源码验证

```typescript
// 文件：src/controller/base-stream-controller.ts - onMediaSeeking()
protected onMediaSeeking = () => {
  // seek 处理逻辑：
  // 1. 取消当前片段加载（如果 seek 位置不在当前片段）
  // 2. 重置 fragPrevious = null
  // 3. 更新 lastCurrentTime
  // 4. 移除 seek 位置之后的 gap fragments
  // 5. 调整 startPosition 和 nextLoadPosition
  
  // 【注意】这里没有 initPTS 的重新计算逻辑！
  // initPTS 的更新只在 transmuxer 处理新片段时触发
};
```

---

### 5.5 Seek 操作后需要重新处理的其他事项

虽然 initPTS 不会在 seek 后重新计算，但 seek 操作会触发以下需要重新处理的事项：

#### 5.5.1 片段选择（Fragment Selection）

**需要重新选择的原因**：seek 后当前播放位置改变，需要找到对应位置的片段。

```typescript
// 文件：src/controller/base-stream-controller.ts - onMediaSeeking()

// 【关键】检测 backward seek（后向 seek）
const backwardSeek = this.lastCurrentTime > currentTime;

if (backwardSeek) {
  // 后向 seek 时需要重置 fragPrevious
  // 这样下次调用 getFragmentAtPosition() 时会重新查找
  this.fragPrevious = null;
}

// 触发片段重新加载
if (fowardBuffer < 1 && this.state === State.IDLE) {
  this.tickImmediate();  // 立即执行状态机 tick
}
```

#### 5.5.2 缓冲区状态检测（Buffer Range Check）

**需要重新检测的原因**：seek 位置可能在缓冲区外，需要加载新数据。

```typescript
// onMediaSeeking() 中的缓冲区检测逻辑

const bufferInfo = BufferHelper.bufferInfo(
  mediaBuffer ? mediaBuffer : media,
  currentTime,
  config.maxBufferHole
);

const fowardBuffer = bufferInfo.len;

if (!fowardBuffer) {
  // seek 位置在缓冲区外！
  // 需要：
  // 1. 取消当前片段加载
  // 2. 从新位置开始加载
  fragCurrent.abortRequests();
  this.resetLoadingState();
}
```

#### 5.5.3 Gap Fragments 清理

**需要清理的原因**：seek 到新位置后，原位置之后的片段可能不再需要。

```typescript
// 文件：src/controller/base-stream-controller.ts - onMediaSeeking()

if (media) {
  // 移除 seek 位置之后的所有 "gap" 片段
  // 这些片段被标记为 PARTIAL，可能不是完整数据
  this.fragmentTracker.removeFragmentsInRange(
    currentTime,    // 从 seek 位置开始
    Infinity,       // 到无穷大
    this.playlistType,
    true            // 只移除 gap 片段
  );
}
```

#### 5.5.4 播放位置调整（Start Position & Next Load Position）

**需要重新调整的原因**：确保后续加载从正确位置开始。

```typescript
// onMediaSeeking() 中的位置调整逻辑

// 如果缓冲区为空（seek 到未缓冲的位置）
const bufferEmpty = !BufferHelper.isBuffered(media, currentTime);

if (bufferEmpty) {
  // 设置 startPosition 为 seek 目标位置
  // 后续加载会从这里开始
  this.startPosition = currentTime;
}

// 无论缓冲区是否为空，都更新 nextLoadPosition
this.nextLoadPosition = currentTime;
```

#### 5.5.5 LL-HLS Part 加载状态重置

**需要重置的原因**：Low-Latency HLS 使用部分片段（parts），seek 后需要重新评估。

```typescript
// onMediaSeeking() 中的 LL-HLS 处理

if (media) {
  if (!this.loadingParts) {
    const bufferEnd = Math.max(bufferInfo.end, currentTime);
    const shouldLoadParts = this.shouldLoadParts(
      this.getLevelDetails(),
      bufferEnd
    );
    if (shouldLoadParts) {
      // seek 后可能需要重新启用 part 加载
      this.loadingParts = shouldLoadParts;
    }
  }
}
```

#### 5.5.6 状态机状态重置

**需要重置的原因**：seek 可能发生在任何状态，需要恢复到可加载状态。

```typescript
// seek 可能发生在 ENDED 状态
if (this.state === State.ENDED) {
  // 从 ENDED 状态恢复，需要重置加载状态
  this.resetLoadingState();
}

// seek 时如果正在加载片段，可能需要取消
if (fragCurrent) {
  const beforeFragment = currentTime < fragCurrent.start - tolerance;
  const pastFragment = currentTime > fragCurrent.end + tolerance;
  
  if (beforeFragment || pastFragment) {
    // seek 位置不在当前片段范围内
    // 取消加载，准备从新位置加载
    fragCurrent.abortRequests();
    this.resetLoadingState();
  }
}
```

#### 5.5.7 总结：Seek 后完整处理清单

| 序号 | 处理事项 | 是否执行 | 说明 |
|------|----------|----------|------|
| 1 | **initPTS 重新计算** | ❌ 不执行 | 基于 cc，不随 seek 变化 |
| 2 | **片段选择重新计算** | ✅ 执行 | 根据新位置找到对应片段 |
| 3 | **缓冲区状态检测** | ✅ 执行 | 判断 seek 位置是否有缓冲 |
| 4 | **Gap Fragments 清理** | ✅ 执行 | 移除 seek 位置之后的临时片段 |
| 5 | **播放位置调整** | ✅ 执行 | 更新 startPosition/nextLoadPosition |
| 6 | **LL-HLS Part 状态** | ✅ 执行 | 重新评估是否需要加载 parts |
| 7 | **状态机状态重置** | ✅ 执行 | 从 ENDED 等状态恢复到 IDLE |
| 8 | **当前片段加载取消** | 条件执行 | 仅当 seek 位置不在当前片段时 |
| 9 | **backward seek 检测** | ✅ 执行 | 设置 lookupTolerance 为更小值 |
| 10 | **lastCurrentTime 更新** | ✅ 执行 | 用于下次 backward seek 检测 |

---

## 6. 音视频 PTS 处理逻辑深度分析

### 6.1 PTS 和 DTS 基础概念

在理解 hls.js 的 PTS 处理之前，需要先了解几个关键概念：

| 术语 | 全称 | 说明 |
|------|------|------|
| **PTS** | Presentation Time Stamp | 显示时间戳，决定帧何时显示 |
| **DTS** | Decoding Time Stamp | 解码时间戳，决定帧解码顺序 |
| **CTS** | Composition Time Offset | 组合时间偏移，CTS = PTS - DTS |
| **timescale** | 时间刻度 | 时间单位，如 90000 表示 1 秒 = 90000 个单位 |

**为什么 PTS 和 DTS 可能不同？**
- 视频使用 B 帧时，解码顺序（DTS）和显示顺序（PTS）不同
- 例如：I B B P 的实际解码顺序是 I P B B

### 6.2 HLS 源中的时间戳

HLS 标准（RFC 8216）规定：
- MPEG-2 TS 容器使用 33 位 PTS/DTS，timescale 为 90000 Hz
- PTS 是 33 位有符号整数，范围是 -2^32 到 2^32-1
- 当 PTS 超过 2^33 时会回绕（rollover）

### 6.3 hls.js 中的 PTS 归一化处理

**文件**: `src/remux/mp4-remuxer.ts`

**为什么需要 PTS 归一化？**
- MPEG-TS 使用 33 位 PTS/DTS，范围是 0 到 2^33 - 1
- 当播放时间超过 2^33 / 90000 ≈ 26.5 小时，PTS 会回绕（rollover）
- 回绕后 PTS 从 2^33-1 变为 0，导致时间戳不连续
- hls.js 需要检测并处理这种回绕，确保时间戳单调递增

**hls.js 使用 `normalizePts()` 函数处理 PTS 的 33 位回绕问题**：

```typescript
// ============================================================================
// 常量定义
// ============================================================================
// PTS 33位回绕常量 = 2^33 = 8589934592
// 当 PTS 超过这个值时会回绕到 0
const MPEG_TS_PTS_ROLLOVER = 8589934592; // 2^33

// ============================================================================
// 函数：normalizePts
// 功能：归一化 PTS 值，处理 33 位回绕问题
// 参数：
//   - value: 当前 PTS 值（可能已回绕）
//   - reference: 参考 PTS 值（已知正确的 PTS）
// 返回：归一化后的 PTS 值（与 reference 在同一时间域内）
//
// 【算法原理】
// PTS 是 33 位无符号整数，范围 [0, 2^33 - 1]
// 当 value 和 reference 差值超过 2^32 时，说明发生了回绕
//
// 举例：
//   假设 reference = 2^33 - 100（接近回绕点）
//   下一个 value = 0（刚刚回绕）
//   差值 = |0 - (2^33 - 100)| ≈ 2^33 > 2^32
//   → 检测到回绕，需要加 2^33 修正
// ============================================================================
export function normalizePts(value: number, reference: number | null): number {
  let offset;
  
  // 如果没有参考值，直接返回（首次调用）
  if (reference === null) {
    return value;
  }

  // ==========================================================================
  // 判断回绕方向
  //   - reference < value：当前值更大，说明正向回绕（reference 接近 2^33，value 回绕到 0）
  //     解决：需要加 2^33 让 value 回到正确域
  //   - reference > value：当前值更小，说明反向回绕（value 接近 2^33，reference 回绕到 0）
  //     解决：需要减 2^33 让 value 回到正确域
  // ==========================================================================
  if (reference < value) {
    // 需要减 2^33（检测到正向回绕）
    // 例：reference = 100, value = 2^33 - 50
    //     value 已经回绕，需要减 2^33 才能与 reference 比较
    offset = -MPEG_TS_PTS_ROLLOVER;
  } else {
    // 需要加 2^33（检测到反向回绕）
    // 例：reference = 2^33 - 50, value = 100
    //     value 还没回绕，需要加 2^33 才能与 reference 比较
    offset = MPEG_TS_PTS_ROLLOVER;
  }
  
  // ==========================================================================
  // PTS 是 33bit (从 0 到 2^33 -1)
  // 如果 value 和 reference 的差值大于振幅的一半 (2^32)，说明发生了 PTS 回绕
  //
  // 为什么是 2^32 而不是 2^33？
  //   - 33 位 PTS 的振幅是 2^33
  //   - 但差值超过一半（2^32）时，更可能是回绕而不是真的那么大
  //   - 这是"最近值"原则：假设 PTS 是连续变化的
  // ==========================================================================
  while (Math.abs(value - reference) > 4294967296) {  // 4294967296 = 2^32
    value += offset;  // 加减 2^33 修正
  }

  return value;
}
```

**归一化示例**：

```text
场景 1：正常情况（无回绕）
  reference = 90000 * 3600 = 324000000 (1小时)
  value     = 90000 * 3601 = 324090000 (1小时1秒)
  差值 = 90000 < 2^32
  → 无需修正，直接返回 value

场景 2：正向回绕（value 回绕到 0 附近）
  reference = 2^33 - 90000 (接近回绕点)
  value     = 0 (刚刚回绕)
  差值 ≈ 2^33 > 2^32
  → 检测到回绕，value += 2^33
  → 返回 2^33 (修正后的值)

场景 3：反向回绕（reference 回绕到 0 附近）
  reference = 100 (刚刚回绕)
  value     = 2^33 - 90000 (还没回绕)
  差值 ≈ 2^33 > 2^32
  → 检测到回绕，value -= 2^33 会是负数？
  → 实际上 offset = +2^33，所以 value 保持不变
  → reference 需要修正：reference += 2^33
```

### 6.4 音视频 PTS 对齐机制

**关键问题**：音频和视频的 PTS 是否确保与 HLS 源完全一致？

**答案**：**不完全一致，但保持在可接受误差范围内。**

#### 6.4.1 初始化时间戳（initPTS）计算

**文件**: `src/remux/mp4-remuxer.ts` - `computeInitPts()`

**为什么需要 initPTS？**
- fMP4 的 `tfdt` (Track Fragment Decode Time) 是相对于 init segment 的
- 需要计算一个基准时间，让所有 fragment 的时间戳从同一个原点开始
- 这样可以避免时间戳过大，同时保证音视频同步

```typescript
// ============================================================================
// 函数：computeInitPts
// 功能：计算初始化时间戳（initPTS），作为后续所有时间戳的基准
// 参数：
//   - basetime: 当前片段的基准时间（从 TS 中解析的 PTS 值）
//   - timescale: 时间刻度（如 90000 for TS）
//   - presentationTime: 期望的显示时间（通常是 0 或 seek 位置）
//   - type: 'audio' 或 'video'，区分音视频轨道
// 返回：相对于 presentationTime 的时间偏移量（单位：timescale）
//
// 【算法原理】
// 1. 将 presentationTime 转换为 timescale 单位（offset）
// 2. 归一化 basetime（处理 PTS 回绕）
// 3. 计算 basetime 相对于 offset 的偏移
// 4. 确保偏移量非负（如果 basetime < offset，需要加 2^33）
// ============================================================================
computeInitPts(
  basetime: number,
  timescale: number,
  presentationTime: number,
  type: 'audio' | 'video',
): number {
  // ==========================================================================
  // 【步骤 1】计算目标偏移量
  // presentationTime: 期望的显示时间（秒）
  // timescale: 时间刻度（如 90000）
  // offset: 期望的 PTS 起始值（timescale 单位）
  // 例如：presentationTime = 10.5 秒，timescale = 90000
  //       → offset = 10.5 * 90000 = 945000
  // ==========================================================================
  const offset = Math.round(presentationTime * timescale);
  
  // ==========================================================================
  // 【步骤 2】归一化 basetime（处理 PTS 回绕）
  // 确保 basetime 和 offset 在同一个时间域
  // ==========================================================================
  let timestamp = normalizePts(basetime, offset);
  
  // ==========================================================================
  // 【步骤 3】处理时间戳回绕
  // 如果 timestamp < offset，说明 timestamp 回绕了
  // 需要加 2^33 让它回到正确域
  //
  // 举例：
  //   offset = 945000 (10.5秒处)
  //   timestamp = 2^33 - 100 (接近回绕点)
  //   → timestamp < offset? NO（因为 2^33 很大）
  //
  // 另一种情况：
  //   offset = 2^33 - 100 (接近回绕点)
  //   timestamp = 0 (刚回绕)
  //   → timestamp < offset? YES
  //   → timestamp += 2^33 (修正)
  // ==========================================================================
  if (timestamp < offset) {
    while (timestamp < offset) {
      timestamp += MPEG_TS_PTS_ROLLOVER;  // 加 2^33
    }
  }
  
  // ==========================================================================
  // 【步骤 4】返回相对于 presentationTime 的偏移量
  // 这个返回值会作为 initPTS，后续所有 PTS 都减去这个值
  // 
  // 举例：
  //   timestamp = 1000000 (实际 PTS)
  //   offset = 945000 (10.5秒处)
  //   → 返回 55000 (表示从 10.5秒开始，过了 55000/90000 = 0.611秒)
  // ==========================================================================
  return timestamp - offset;
}
```

**initPTS 的作用示意图**：
```text
原始 TS PTS 时间轴：
  0              10.5s            26.5h (2^33)
  |──────────────────|────────────────|──────>
                     ↑
                 presentationTime
  
使用后（减去 initPTS）：
  0              0.611s           ...
  |──────────────────|──────────────────────>
                     ↑
                 initPTS 归零后
```

#### 6.4.2 音视频时间偏移校正

**文件**: `src/remux/mp4-remuxer.ts` - `remux()` 方法

**为什么需要音视频偏移校正？**
- TS 流中音频和视频的 PTS 可能不完全对齐
- 编码时可能有微小差异（如视频延迟几毫秒）
- 如果不同步，播放时会出现"音画不同步"问题

```typescript
// ============================================================================
// 【前置条件判断】
// 只有当同时满足以下条件时才进行校正：
//   1. enoughAudioSamples: 有足够音频采样数据
//   2. enoughVideoSamples: 有足够视频采样数据
//   3. timeOffset: 存在时间偏移（首次加载时可能为空）
// ============================================================================
if (enoughAudioSamples && enoughVideoSamples && timeOffset) {
  // ==========================================================================
  // 【步骤 1】获取视频起始 PTS
  // getVideoStartPts(): 从 videoTrack.samples 中获取第一个 sample 的 PTS
  // 这是视频轨道的实际起始显示时间
  // ==========================================================================
  const startPTS = this.getVideoStartPts(videoTrack.samples);
  
  // ==========================================================================
  // 【步骤 2】计算音频和视频的 PTS 差值
  //   - audioTrack.samples[0].pts: 第一个音频 sample 的 PTS
  //   - normalizePts(..., startPTS): 归一化音频 PTS（处理回绕）
  //   - tsDelta: 音频 PTS - 视频 PTS（单位：inputTimeScale）
  //
  // 举例：
  //   视频起始 PTS = 900000 (10秒处，timescale=90000)
  //   音频第一个 PTS = 900090 (比视频晚 1ms)
  //   → tsDelta = 90 (表示音频比视频晚 1ms)
  // ==========================================================================
  const tsDelta = normalizePts(audioTrack.samples[0].pts, startPTS) - startPTS;
  
  // ==========================================================================
  // 【步骤 3】转换为秒单位
  // videoTrack.inputTimeScale: 通常是 90000 (HLS TS 标准)
  // audiovideoTimestampDelta: 音视频时间差（秒）
  //
  // 举例：tsDelta = 90, inputTimeScale = 90000
  //       → audiovideoTimestampDelta = 90/90000 = 0.001 秒 = 1ms
  // ==========================================================================
  const audiovideoTimestampDelta = tsDelta / videoTrack.inputTimeScale;
  
  // ==========================================================================
  // 【步骤 4】通过调整 timeOffset 来校正音视频偏移
  //
  // 情况 A：audiovideoTimestampDelta > 0（音频晚于视频）
  //   → 需要延迟视频（videoTimeOffset += 正值）或提前音频
  //   → 代码选择：延迟视频（audioTimeOffset 不变，videoTimeOffset 增加）
  //
  // 情况 B：audiovideoTimestampDelta < 0（音频早于视频）
  //   → 需要提前视频或延迟音频
  //   → 代码选择：提前音频（audioTimeOffset 增加，videoTimeOffset 不变）
  //
  // Math.max(0, ...): 确保偏移量非负
  // ==========================================================================
  audioTimeOffset += Math.max(0, audiovideoTimestampDelta);   // 音频需要提前
  videoTimeOffset += Math.max(0, -audiovideoTimestampDelta); // 视频需要延迟
}
```

**校正逻辑示意图**：
```text
校正前（音频晚于视频 1ms）：
  视频: |─── V1 ─── V2 ─── V3 ───>
  音频:    |─── A1 ─── A2 ─── A3 ───>
            ↑ 1ms 偏移

校正后（通过调整 timeOffset）：
  视频: |─── V1 ─── V2 ─── V3 ───>
  音频: |─── A1 ─── A2 ─── A3 ───>
        ↑ 对齐
```

#### 6.4.3 音频采样率作为时间基准

**设计选择**：hls.js 使用音频采样率作为 MP4 时间刻度

```typescript
// 使用音频采样率作为 MP4 时间刻度
// 理由是：每个音频帧包含整数个音频采样（AAC 为 1024）
// 使用音频采样率有助于获得整数 MP4 帧持续时间
// 这避免了潜在的舍入问题和音视频同步问题
audioTrack.timescale = audioTrack.samplerate;
```

### 6.5 PTS 与 HLS 源的一致性分析

| 方面 | 处理方式 | 一致性 |
|------|----------|--------|
| **PTS 绝对值** | 转换为相对于 initPTS 的偏移量 | 相对一致 |
| **PTS 时序关系** | 保持原始 PTS 之间的时间间隔 | 基本一致 |
| **精确到微秒** | 转换为 fMP4 时间刻度时可能舍入 | 有微小误差 |
| **不连续处理** | 通过 discontinuity 标志重置时间戳 | 正确处理 |

**结论**：
1. hls.js **不会**完全保留 HLS 源的绝对 PTS 值
2. 但会**保持音视频之间的相对时间关系**，确保音画同步
3. 转换为 fMP4 格式时，时间戳会重新基准化（以 initPTS 为原点）
4. 这种设计是 MSE API 的要求，不影响播放体验

### 6.6 时间戳连续性保证机制

#### 6.6.1 片段间连续性检测

**文件**: `src/remux/mp4-remuxer.ts` - `remuxVideo()`

**为什么需要连续性检测？**
- HLS 片段之间可能存在间隙（hole）或重叠（overlap）
- 间隙会导致播放卡顿（buffer hole）
- 重叠会导致音视频不同步
- hls.js 需要检测并修正这些问题

```typescript
// ============================================================================
// 【前置条件】contiguous = true 表示与前一个片段连续
// 如果 contiguous = false（如 seek 后），不做连续性修正
// ============================================================================
if (contiguous) {
  // ==========================================================================
  // 【步骤 1】计算时间差
  //   - firstDTS: 当前片段第一个 sample 的 DTS
  //   - nextVideoPts: 预期的前一个片段结束 DTS（从 track 信息中获取）
  //   - delta: 实际与预期的差值
  // ==========================================================================
  const delta = firstDTS - nextVideoPts;
  
  // ==========================================================================
  // 【步骤 2】检测间隙（hole）
  // 条件：delta > averageSampleDuration
  // 意义：如果差值大于平均帧持续时间，说明有间隙
  //
  // 举例：
  //   平均帧持续时间 = 33ms (30fps)
  //   delta = 100ms
  //   → 100 > 33 → foundHole = true
  // ==========================================================================
  const foundHole = delta > averageSampleDuration;
  
  // ==========================================================================
  // 【步骤 3】检测重叠（overlap）
  // 条件：delta < -1
  // 意义：如果差值是负数且超过 1 个 tick，说明有重叠
  //
  // 举例：
  //   delta = -50ms
  //   → -50 < -1 → foundOverlap = true
  // ==========================================================================
  const foundOverlap = delta < -1;
  
  // ==========================================================================
  // 【步骤 4】处理间隙或重叠
  // ==========================================================================
  if (foundHole || foundOverlap) {
    // ==========================================================================
    // 情况 A：发现间隙（hole）
    // 策略：将当前片段的第一个 sample 时间戳设置为预期值
    // 这样可以"填补"间隙，让播放连续
    // ==========================================================================
    if (foundHole) {
      // 强制设置第一个 sample 的 DTS 和 PTS
      inputSamples[0].dts = firstDTS;  // 使用预期值
      inputSamples[0].pts = firstPTS;  // 使用预期值
    } else {
      // ==========================================================================
      // 情况 B：发现重叠（overlap）
      // 策略：逐 sample 调整时间戳，消除重叠
      // 每个 sample 减去 delta（delta 是负数，所以实际上是加）
      //
      // 举例：
      //   delta = -50ms
      //   sample[0].dts = 1000
      //   → sample[0].dts = 1000 - (-50) = 1050（向后移动 50ms）
      // ==========================================================================
      for (let i = 0; i < inputSamples.length; i++) {
        inputSamples[i].dts -= delta;  // 消除重叠
        inputSamples[i].pts -= delta;
      }
    }
  }
}
```

#### 6.6.2 Chrome 特殊处理

```typescript
// Chrome 浏览器中，如果下一个视频时间戳接近预期值，
// 即使不连续也视为连续，以避免产生 video buffer gaps
if (userAgentChromeVersion() &&
    nextVideoTs !== null &&
    Math.abs(pts - cts - (nextVideoTs + initTime)) < 15000) {
  contiguous = true;
}
```

---

## 7. Transmuxer 与 MP4Remuxer 深度分析

### 7.1 为什么需要 Transmuxer 和 MP4Remuxer？

#### 7.1.1 MSE API 的格式限制

**核心原因**：浏览器的 MediaSource Extensions (MSE) API **只支持 fMP4（fragmented MP4）容器格式**，不支持 MPEG-2 TS、普通 MP4、AAC、MP3 等原始格式。

> **注意**：MSE 要求的是 **fMP4**（fragmented MP4），不是普通的 MP4 文件。fMP4 支持流式播放，每个 fragment 包含完整的 moof（movie fragment）和 mdat（media data），适合自适应码率切换。

```text
┌────────────────────────────────────────────────────────────────┐
│                    HLS 源格式                                │
│  ┌──────────────┬──────────────┬──────────────┐            │
│  │ MPEG-2 TS    │ AAC 容器     │ MP3 容器     │            │
│  │ (常见)        │ (音频流)      │ (音频流)     │            │
│  └──────────────┴──────────────┴──────────────┘            │
│                           │                                  │
│                           ▼                                  │
│              ┌────────────────────────┐                      │
│              │   Transmuxer 转复用   │                      │
│              └────────────────────────┘                      │
│                           │                                  │
│                           ▼                                  │
│                    ┌──────────────┐                         │
│                    │   fMP4       │                         │
│                    │ (MSE 唯一支持)│                         │
│                    └──────────────┘                         │
│                           │                                  │
│                           ▼                                  │
│              ┌────────────────────────┐                      │
│              │   SourceBuffer.append()│                      │
│              └────────────────────────┘                      │
└────────────────────────────────────────────────────────────────┘
```

#### 7.1.2 MSE 规范要求的格式

根据 W3C 的 MediaSource Extensions 规范：

| 浏览器 | 必须支持的容器 | 必须支持的编解码器 |
|--------|----------------|-------------------|
| Chrome | ISO BMFF (MP4) | H.264, VP8, VP9, AV1 |
| Firefox | ISO BMFF (MP4) | H.264, VP8, VP9 |
| Safari | ISO BMFF (MP4), MPEG-2 TS (私有) | H.264, H.265 |

**fMP4 (fragmented MP4)** 的特点：
- 支持流式播放（不需要完整文件即可开始播放）
- 每个 fragment 包含完整的 `moof` (movie fragment) 和 `mdat` (media data)
- 适合自适应码率切换
- **与普通 MP4 的区别**：普通 MP4 使用 `moov` box 存储元数据（需要完整文件才能播放），而 fMP4 使用 `moof` + `mfhd` + `traf` 等 fragment 结构（可以边下边播）

### 7.2 Transmuxer 架构与处理流程

**文件**: `src/demux/transmuxer.ts`

#### 7.2.1 支持的输入格式

```typescript
type MuxConfig =
  | { demux: typeof MP4Demuxer; remux: typeof PassThroughRemuxer }
  | { demux: typeof TSDemuxer; remux: typeof MP4Remuxer }
  | { demux: typeof AC3Demuxer; remux: typeof MP4Remuxer }
  | { demux: typeof AACDemuxer; remux: typeof MP4Remuxer }
  | { demux: typeof MP3Demuxer; remux: typeof MP4Remuxer };

const muxConfig: MuxConfig[] = [
  { demux: MP4Demuxer, remux: PassThroughRemuxer },    // MP4 透传
  { demux: TSDemuxer, remux: MP4Remuxer },            // TS → MP4
  { demux: AACDemuxer, remux: MP4Remuxer },           // AAC → MP4
  { demux: MP3Demuxer, remux: MP4Remuxer },           // MP3 → MP4
];
```

#### 7.2.2 格式探测逻辑

**功能说明**：`Transmuxer` 需要自动识别输入的媒体格式（TS、AAC、MP3、MP4），然后选择对应的 Demuxer。

**为什么需要格式探测？**
- HLS 支持多种封装格式
- 不同格式需要不同的解复用器
- 需要在运行时动态选择，而不是编译时硬编码

```typescript
// ============================================================================
// 类型定义：MuxConfig
// 每个配置项包含 demuxer 和 remuxer 的构造函数
//   - demux: 解复用器类（负责解析输入格式）
//   - remux: 重复用器类（负责封装为 fMP4）
// ============================================================================
type MuxConfig = 
  | { demux: typeof MP4Demuxer; remux: typeof PassThroughRemuxer }  // MP4 输入 → 透传
  | { demux: typeof TSDemuxer; remux: typeof MP4Remuxer }           // TS 输入 → MP4
  | { demux: typeof AACDemuxer; remux: typeof MP4Remuxer }          // AAC 输入 → MP4
  | { demux: typeof MP3Demuxer; remux: typeof MP4Remuxer };         // MP3 输入 → MP4

// ============================================================================
// 配置数组：按优先级排列的探测器列表
// 注意：MP4Demuxer 排在第一位，因为 MP4 的 magic number 最容易识别
// ============================================================================
const muxConfig: MuxConfig[] = [
  { demux: MP4Demuxer, remux: PassThroughRemuxer },    // MP4 透传（无需重封装）
  { demux: TSDemuxer, remux: MP4Remuxer },            // TS → MP4（最常见）
  { demux: AACDemuxer, remux: MP4Remuxer },           // AAC → MP4
  { demux: MP3Demuxer, remux: MP4Remuxer },           // MP3 → MP4
];

// ============================================================================
// 函数：configureTransmuxer
// 功能：根据输入数据格式，选择合适的 Demuxer 和 Remuxer
// 参数：
//   - data: Uint8Array，输入数据的二进制数组
// 返回：undefined（成功）或 Error（失败）
//
// 【探测原理】
// 每种格式都有特定的"魔法数字"（magic number）：
//   - TS:  0x47 开头的字节（TS 同步字节）
//   - MP4: 包含 'ftyp' 或 'moov' box
//   - AAC: ADTS 帧头（0xFFF 开头）
//   - MP3: ID3 标签或帧同步位
// ============================================================================
private configureTransmuxer(data: Uint8Array): undefined | Error {
  let mux: MuxConfig | undefined;
  
  // ==========================================================================
  // 【步骤 1】遍历所有配置的 demuxer，找到第一个能识别该格式的
  // probe() 方法：检查数据的前几个字节是否匹配该格式的特征
  //   - 返回 true: 匹配
  //   - 返回 false: 不匹配
  // ==========================================================================
  for (let i = 0, len = muxConfig.length; i < len; i++) {
    // 调用 probe 方法检测格式
    if (muxConfig[i].demux?.probe(data, this.logger)) {
      // 找到匹配的 demuxer
      mux = muxConfig[i];
      break;  // 找到就退出（第一个匹配的优先级最高）
    }
  }
  
  // ==========================================================================
  // 【步骤 2】检查是否找到匹配的 demuxer
  // 如果没找到，返回错误
  // ==========================================================================
  if (!mux) {
    return new Error('Unsupported media format');
  }
  
  // ==========================================================================
  // 【步骤 3】创建对应的 demuxer 和 remuxer 实例
  //   - Demuxer: 解复用器（解析输入格式）
  //   - Remuxer: 重复用器（封装为 fMP4）
  // ==========================================================================
  const Demuxer = mux.demux;
  const Remuxer = mux.remux;
  
  this.demuxer = new Demuxer(observer, config, typeSupported, logger);
  this.remuxer = new Remuxer(observer, config, typeSupported, logger);
  
  return undefined;  // 成功
}
```

**格式探测顺序说明**：
```text
输入数据: [0x47, 0x40, 0x11, ...]
              ↑
           TS 同步字节
  
探测过程：
  1. MP4Demuxer.probe() → 检查是否有 'ftyp' → false
  2. TSDemuxer.probe()  → 检查 0x47 同步字节 → true!
  → 选择 TSDemuxer + MP4Remuxer
```

#### 7.2.3 处理流水线

```text
输入数据 (TS/AAC/MP3/MP4)
          │
          ▼
    ┌───────────┐
    │  探针检测   │ → 确定数据格式
    └───────────┘
          │
          ▼
    ┌───────────┐
    │  Demuxer   │ → 解复用：分离音视频 ES 流
    │  (解复用)   │   - TSDemuxer: 解析 TS 包，提取 PES
    └───────────┘     - AACDemuxer: 解析 ADTS 帧
          │              - MP3Demuxer: 解析 MP3 帧
          ▼
    ┌───────────┐
    │ AudioTrack │ → 音频采样数据
    │ VideoTrack │ → 视频采样数据 (NAL units)
    │ ID3Track   │ → 元数据
    └───────────┘
          │
          ▼
    ┌───────────┐
    │  Remuxer   │ → 重复用：封装为 fMP4
    │  (重复用)   │   - 生成 init segment (ftyp + moov box)
    └───────────┘     - 生成 media segment (moof + mdat)
          │
          ▼
    输出数据 (fMP4)
```

### 7.3 MP4Remuxer 详解

**文件**: `src/remux/mp4-remuxer.ts`

#### 7.3.1 核心职责

`MP4Remuxer` 的主要任务是将解复用后的音视频数据重新封装为 MSE 兼容的 fMP4 格式：

1. **生成 Init Segment** (`generateIS()`)
   - 创建 `ftyp` box (文件类型)
   - 创建 `moov` box (movie metadata)
   - 包含编解码器配置信息（SPS/PPS for H.264, AudioSpecificConfig for AAC）

2. **封装音频数据** (`remuxAudio()`)
  - 将 AAC/MP3/AC3 帧封装为 fMP4 audio samples
  - 处理音频时间戳和持续时间
  - 生成 `moof` + `mdat` boxes

3. **封装视频数据** (`remuxVideo()`)
  - 将 H.264/H.265 NAL units 封装为 fMP4 video samples
   - 处理视频时间戳和 CTS (Composition Time Offset)
   - 生成 `moof` + `mdat` boxes

#### 7.3.2 Init Segment 生成

**功能说明**：Init Segment（初始化段）是 fMP4 格式的必要组成部分，类似于普通 MP4 的 `moov` box。它包含了解码器初始化所需的所有配置信息，**只需要传输一次**，后续的 Media Segment 可以复用这些配置。

**为什么需要 Init Segment？**
- 普通 MP4：所有元数据都在文件头部的 `moov` box 中
- fMP4：元数据被分离到 Init Segment 中，每个 Media Segment 是自包含的
- 这样设计的好处：支持自适应码率切换、直播流、边下边播

```typescript
// ============================================================================
// 函数：generateIS (generate Init Segment)
// 功能：生成音频和视频的初始化段（Init Segment）
// 参数：
//   - audioTrack: 解复用后的音频轨道数据
//   - videoTrack: 解复用后的视频轨道数据
//   - timeOffset: 时间偏移量（用于音视频同步）
//   - accurateTimeOffset: 是否使用精确时间偏移
// 返回：包含初始化数据的对象，或 undefined（如果没有有效轨道）
// ============================================================================
generateIS(
  audioTrack: DemuxedAudioTrack,
  videoTrack: DemuxedVideoTrack,
  timeOffset: number,
  accurateTimeOffset: boolean,
): InitSegmentData | undefined {
  const tracks: TrackSet = {};
  
  // ==========================================================================
  // 【音频 Init Segment 生成】
  // 条件：audioTrack.config 存在（有编解码器配置）且 有音频采样数据
  // audioTrack.config: 对于 AAC 是 AudioSpecificConfig（16-23位）
  //                 对于 MP3 是 null（MP3 不需要额外配置）
  // ==========================================================================
  if (audioTrack.config && audioSamples.length) {
    // 设置时间刻度 = 采样率（如 44100 或 48000）
    // 这样每个 sample 的 duration 就是整数，避免舍入误差
    audioTrack.timescale = audioTrack.samplerate;
    
    // 构建音频轨道描述对象
    tracks.audio = {
      id: 'audio',                    // 轨道 ID
      container: 'audio/mp4',        // MIME 类型
      codec: audioTrack.codec,       // 编解码器（如 'mp4a.40.2' 表示 AAC-LC）
      initSegment: MP4.initSegment([audioTrack]),  // 生成 fMP4 的 init segment 二进制数据
      metadata: { channelCount: audioTrack.channelCount }  // 声道数（1=单声道，2=立体声）
    };
  }
  
  // ==========================================================================
  // 【视频 Init Segment 生成】
  // 条件：videoTrack.sps 和 videoTrack.pps 存在（H.264 的解码器配置）
  //   - SPS (Sequence Parameter Set): 序列参数集，包含视频宽高等信息
  //   - PPS (Picture Parameter Set): 图像参数集，包含编码参数
  //   这两个是 H.264 解码器初始化必需的，相当于"怎么解码这个视频"的说明书
  // ==========================================================================
  if (videoTrack.sps && videoTrack.pps && videoSamples.length) {
    // 设置时间刻度 = 输入时间刻度（通常是 90000，HLS TS 的标准 timescale）
    videoTrack.timescale = videoTrack.inputTimeScale;
    
    // 构建视频轨道描述对象
    tracks.video = {
      id: 'main',                     // 轨道 ID（视频通常是 'main'）
      container: 'video/mp4',        // MIME 类型
      codec: videoTrack.codec,       // 编解码器（如 'avc1.64001f' 表示 H.264 High Profile）
      initSegment: MP4.initSegment([videoTrack]),  // 生成 fMP4 的 init segment 二进制数据
      metadata: { 
        width: videoTrack.width,     // 视频宽度（从 SPS 中解析）
        height: videoTrack.height    // 视频高度（从 SPS 中解析）
      }
    };
  }
  
  // 返回初始化数据
  //   - tracks: 轨道集合（可能包含 audio 和/或 video）
  //   - initPTS: 初始 PTS 值（用于时间戳基准化）
  //   - timescale: 时间刻度
  //   - trackId: 轨道 ID
  return { tracks, initPTS, timescale, trackId };
}
```

**Init Segment 的 MP4 Box 结构**：
```text
ftyp (File Type Box)     ← 文件类型标识
moov (Movie Box)         ← 电影元数据
  ├── mvhd (Movie Header)  ← 电影头部（时长、timescale 等）
  ├── trak (Track)         ← 轨道信息（可能多个）
  │   ├── tkhd (Track Header)  ← 轨道头部（宽高、音量等）
  │   └── mdia (Media)        ← 媒体信息
  │       ├── mdhd (Media Header)  ← 媒体头部（timescale、duration）
  │       ├── hdlr (Handler)       ← 处理器（video/audio/subtitle）
  │       └── minf (Media Information)  ← 媒体信息
  │           └── stbl (Sample Table)    ← 采样表（关键！）
  │               ├── avcC (AVCDecoderConfigurationRecord)  ← H.264 配置（SPS/PPS）
  │               └── esds (MPEG-4 Elementary Stream Descriptor)  ← AAC 配置
  └── mvex (Movie Extends)  ← 电影扩展（fMP4 特有，用于告知后续 fragment 的结构）
      └── trex (Track Extends)  ← 轨道扩展
```

#### 7.3.3 视频 Remux 关键逻辑

**功能说明**：`remuxVideo()` 是 MP4Remuxer 中最核心的方法之一，负责将 H.264/H.265 的原始 NAL units 封装为 fMP4 格式的 video samples。

**关键概念**：
- **NAL unit**：H.264 的基本编码单元（如 SPS、PPS、I-frame、P-frame）
- **start code**：TS 流中使用 `00 00 00 01` 或 `00 00 01` 作为 NAL unit 的分隔符
- **长度前缀**：MP4 中使用 4 字节长度前缀代替 start code

```typescript
// ============================================================================
// 函数：remuxVideo
// 功能：将解复用后的视频轨道数据封装为 fMP4 格式
// 参数：
//   - track: 解复用后的视频轨道（包含 NAL units 数组）
//   - timeOffset: 时间偏移（用于音视频同步）
//   - contiguous: 是否与前一个片段连续（影响时间戳处理）
//   - audioTrackLength: 音频轨道长度（用于判断是否需要等待音频）
//   - chunkMeta: 片段元数据（序列号等）
// 返回：封装后的视频轨道数据，或 undefined
// ============================================================================
remuxVideo(
  track: DemuxedVideoTrack,
  timeOffset: number,
  contiguous: boolean,
  audioTrackLength: number,
  chunkMeta: ChunkMetadata,
): RemuxedTrack | undefined {
  // ==========================================================================
  // 【步骤 1】归一化 PTS/DTS（处理 33 位回绕）
  // 问题：MPEG-TS 的 PTS/DTS 是 33 位整数，播放 26.5 小时后会回绕
  // 解决：通过 normalizePts() 检测回绕并修正，确保时间戳单调递增
  // ==========================================================================
  for (let i = 0; i < nbSamples; i++) {
    const sample = track.samples[i];
    // 使用上一个视频片段的 PTS 作为参考（nextVideoPts）
    // 如果当前 sample.pts 与参考值相差超过 2^32，说明发生了回绕
    sample.pts = normalizePts(sample.pts, nextVideoPts);
    sample.dts = normalizePts(sample.dts, nextVideoPts);
  }
  
  // ==========================================================================
  // 【步骤 2】确保 DTS 单调递增
  // 问题：某些编码器可能产生非单调的 DTS（虽然罕见）
  // 解决：如果当前 sample 的 DTS 小于预期值，强制修正
  // dtsStep: 预期的下一个 DTS 值
  // ==========================================================================
  if (sample.dts < dtsStep) {
    sample.dts = dtsStep;  // 修正为预期值
    // 逐步增加步长（防止后续所有 sample 都需要修正）
    dtsStep += (averageSampleDuration / 4) | 0 || 1;
  }
  
  // ==========================================================================
  // 【步骤 3】转换 NAL units 为 MP4 格式
  // TS 格式：使用 start code (00 00 00 01) 分隔 NAL units
  // MP4 格式：使用 4 字节长度前缀（大端序）代替 start code
  // 
  // 示例转换：
  //   TS:  [00 00 00 01] [NAL header] [NAL data...]
  //   MP4: [00 00 00 XX] [NAL header] [NAL data...]  (XX = NAL 长度)
  // ==========================================================================
  for (let j = 0; j < nbUnits; j++) {
    const unit = VideoSampleUnits[j];
    // 写入 4 字节长度前缀（大端序）
    writeUint32(mdat, offset, unit.data.length);  // 长度前缀
    // 写入 NAL unit 数据（去掉了 start code）
    mdat.set(unit.data, offset + 4);              // NAL 数据
    offset += 4 + unit.data.length;                // 移动偏移量
  }
  
  // ==========================================================================
  // 【步骤 4】创建 MP4 samples（写入 stbl 的 stts、stsz、ctts、stss 等表）
  // MP4 sample 包含以下信息：
  //   - duration: 采样持续时间（用于 stts 表）
  //   - size: 采样大小（用于 stsz 表）
  //   - CTS (Composition Time Offset): PTS - DTS（用于 ctts 表）
  //   - flags: 是否为关键帧（用于 stss 表，同步样本表）
  // ==========================================================================
  outputSamples.push(createMp4Sample(
    VideoSample.key,        // 是否为关键帧（I-frame = 关键帧，可以被 seek 到）
    mp4SampleDuration,     // 样本持续时间（微秒或 timescale 单位）
    mp4SampleLength,       // 样本大小（字节）
    compositionTimeOffset  // CTS = PTS - DTS（B 帧需要非零 CTS）
  ));
  
  // ==========================================================================
  // 【步骤 5】生成 moof (movie fragment) 和 mdat (media data)
  // moof: 包含当前 fragment 的元数据（时间戳、sample 表等）
  // mdat: 包含实际的音视频数据（上一步准备好的 NAL units）
  // 
  // 为什么需要 moof？因为 fMP4 没有全局的 stbl（sample table），
  // 每个 fragment 需要自己的 moof 来描述其中的 samples
  // ==========================================================================
  const moof = MP4.moof(chunkMeta.sn, firstDTS, trackWithSamples);
  const mdat = MP4.mdat(trackWithSamples);
  
  // 返回封装好的 fMP4 数据
  return {
    data1: moof,   // moof box（元数据）
    data2: mdat,   // mdat box（媒体数据）
    // ...
  };
}
```

**fMP4 Video Segment 结构**：
```text
moof (Movie Fragment)
  ├── mfhd (Movie Fragment Header)  ← 序列号（每個 fragment 递增）
  └── traf (Track Fragment)         ← 视频轨道信息
      ├── tfhd (Track Fragment Header)  ← 默认参数
      ├── tfdt (Track Fragment Decode Time)  ← 第一个 sample 的 DTS
      └── trun (Track Run)           ← 采样表（duration、size、CTS、flags）
mdat (Media Data)
  └── [NAL unit 1] [NAL unit 2] ... [NAL unit N]  ← 实际的视频数据
```

#### 7.3.4 音频 Remux 关键逻辑

**功能说明**：`remuxAudio()` 将 AAC/MP3/AC3 等音频帧封装为 fMP4 格式的 audio samples。

**关键概念**：
- **AAC 帧**：每个 AAC 帧固定包含 1024 个采样点
- **ADTS 头**：AAC 在 TS 流中的封装格式，包含采样率、声道数等信息
- **Silent Frame**：静音帧，用于填补音频间隙（避免音频杂音）

```typescript
// ============================================================================
// 函数：remuxAudio
// 功能：将解复用后的音频轨道数据封装为 fMP4 格式
// 参数：
//   - track: 解复用后的音频轨道（包含音频帧数组）
//   - timeOffset: 时间偏移（用于音视频同步）
//   - contiguous: 是否与前一个片段连续
//   - accurateTimeOffset: 是否使用精确时间偏移
//   - videoTimeOffset: 视频时间偏移（用于音视频对齐）
//   - chunkMeta: 片段元数据
// 返回：封装后的音频轨道数据，或 undefined
// ============================================================================
remuxAudio(
  track: DemuxedAudioTrack,
  timeOffset: number,
  contiguous: boolean,
  accurateTimeOffset: boolean,
  videoTimeOffset: number | undefined,
  chunkMeta: ChunkMetadata,
): RemuxedTrack | undefined {
  // ==========================================================================
  // 【步骤 1】计算 MP4 时间刻度（使用音频采样率）
  // 为什么用采样率作为 timescale？
  //   - 每个音频帧包含整数个采样（AAC=1024，MP3=1152）
  //   - 使用采样率作为 timescale，每个帧的 duration 就是整数
  //   - 例如：48kHz 采样率，AAC 帧 duration = 1024/48000 = 0.02133 秒
  //   - 用 48000 作为 timescale：duration = 1024（整数，无舍入误差）
  // ==========================================================================
  const mp4timeScale = track.samplerate;  // 通常 44100 或 48000
  const scaleFactor = inputTimeScale / mp4timeScale;  // 输入 timescale 转换因子
  
  // ==========================================================================
  // 【步骤 2】处理不连续片段的音频填充
  // 问题：如果片段之间有间隙（gap），音频会出现杂音或静音
  // 解决：在间隙处注入静音帧（silent frame）
  // 
  // delta: 当前帧 PTS 与预期 PTS 的差值
  // maxAudioFramesDrift: 允许的最大帧漂移（默认 4 帧）
  // 如果 delta >= 4 帧的时长，说明有间隙，需要填充
  // ==========================================================================
  if (delta >= maxAudioFramesDrift * inputSampleDuration) {
    // 获取静音帧（不同编解码器有特定的静音帧格式）
    //   - AAC: 特殊的 SILENCE frame（包含正确的 ADTS 头）
    //   - MP3: 全零帧
    const fillFrame = AAC.getSilentFrame(codec, channelCount);
    
    // 在间隙位置插入静音帧
    inputSamples.splice(i, 0, { unit: fillFrame, pts: nextPts });
  }
  
  // ==========================================================================
  // 【步骤 3】生成 MP4 音频 samples
  // 音频 sample 与视频 sample 的区别：
  //   - 音频每个 sample 都是关键帧（可以随机访问）
  //   - 音频 CTS 通常为 0（编码顺序 = 显示顺序）
  //   - 音频 sample duration 固定（AAC=1024，MP3=1152）
  // ==========================================================================
  outputSamples.push(createMp4Sample(
    true,                     // 音频总是关键帧（没有 P/B 帧概念）
    mp4SampleDuration,        // 1024 (AAC) 或 1152 (MP3)，单位：timescale
    unitLen,                  // 音频帧长度（字节）
    0                         // 音频 CTS 通常为 0（不需要重排序）
  ));
  
  // ==========================================================================
  // 【步骤 4】生成 moof 和 mdat
  // 与视频类似，音频也有自己的 moof + mdat
  // ==========================================================================
  const moof = MP4.moof(chunkMeta.sn, firstDTS, trackWithSamples);
  const mdat = MP4.mdat(trackWithSamples);
  
  return {
    data1: moof,   // moof box
    data2: mdat,   // mdat box
    // ...
  };
}
```

**AAC 静音帧格式**（以 AAC-LC 44.1kHz 立体声为例）：
```text
ADTS Header (7 bytes):
  ├── Syncword:          0xFFF (12 bits)
  ├── MPEG Version:      0 (1 bit, MPEG-4)
  ├── Layer:             0 (2 bits)
  ├── Protection:        1 (1 bit, no CRC)
  ├── Profile:           1 (2 bits, LC)
  ├── Sampling Freq:    4 (4 bits, 44100 Hz)
  ├── Private:           0 (1 bit)
  ├── Channel Config:    2 (3 bits, Stereo)
  ├── ...

Audio Data (包含 ESCAPE_VALUE 等特殊处理)
```

**fMP4 Audio Segment 结构**：
```text
moof (Movie Fragment)
  ├── mfhd (Movie Fragment Header)
  └── traf (Track Fragment)
      ├── tfhd (Track Fragment Header)
      ├── tfdt (Track Fragment Decode Time)  ← 音频起始 DTS
      └── trun (Track Run)                   ← 音频采样表
          ├── sample duration (固定 1024)
          ├── sample size
          └── sample flags (所有都是关键帧)
mdat (Media Data)
  └── [AAC frame 1] [AAC frame 2] ... [AAC frame N]
```

### 7.4 MP4 生成器 (mp4-generator.ts)

**文件**: `src/remux/mp4-generator.ts`

`MP4` 类负责生成标准的 MP4 boxes：

```typescript
class MP4 {
  // 生成 init segment (moov box)
  static initSegment(tracks: Array<Track>): Uint8Array {
    return MP4.box(
      types.moov,
      MP4.mvhd(tracks[0].timescale, duration),  // movie header
      trak,                                      // track header
      MP4.mvex(tracks)                          // movie extends (for fMP4)
    );
  }
  
  // 生成 media segment (moof + mdat)
  static moof(
    sequenceNumber: number,
    baseMediaDecodeTime: number,
    track: Track
  ): Uint8Array {
    return MP4.box(
      types.moof,
      MP4.mfhd(sequenceNumber),     // movie fragment header
      MP4.traf(baseMediaDecodeTime, track)  // track fragment
    );
  }
}
```

### 7.5 完整的数据流转过程

```text
HLS TS 片段                    浏览器 SourceBuffer
     │                                  │
     ▼                                  │
┌───────────┐                          │
│  TS Demuxer│                          │
│  (解复用)   │                          │
└─────┬─────┘                          │
      │ 输出 DemuxedAudioTrack         │
      │ 输出 DemuxedVideoTrack         │
      │ 输出 DemuxedMetadataTrack      │
      ▼                                  │
┌───────────┐                          │
│ MP4Remuxer │                          │
│  (重复用)   │                          │
└─────┬─────┘                          │
      │ 生成 init segment (moov)       │
      │ 生成 media segment (moof+mdat) │
      ▼                                  │
┌───────────┐                          │
│ Uint8Array │─── appendBuffer() ──────▶│
└───────────┘                          │
                                       ▼
                                  ┌─────────┐
                                  │ 播放     │
                                  └─────────┘
```

### 7.6 浏览器兼容性处理

`MP4Remuxer` 包含针对特定浏览器的兼容性处理：

```typescript
// Chrome 兼容性：标记第一个 sample 为随机访问点
if (userAgentChromeVersion() && userAgentChromeVersion() < 70) {
  const flags = outputSamples[0].flags;
  flags.dependsOn = 2;  // 关键帧
  flags.isNonSync = 0;
}

// Safari 兼容性：处理不规则的 sample duration
if (userAgentSafariVersion()) {
  if (maxPtsDelta - minPtsDelta < maxDtsDelta - minDtsDelta) {
    // 使用 PTS 而不是 DTS 来确定 sample duration
    for (let i = 0; i < outputSamples.length; i++) {
      outputSamples[i].cts = 0;  // Safari 可能需要零 CTS
    }
  }
}
```

---

## 8. 配置系统详解

### 8.1 配置加载优先级

```text
默认值 (hlsDefaultConfig)
       │
       ▼
用户配置 (new Hls(userConfig))
       │
       ▼
运行时修改 (hls.config.xxx = yyy)
```

### 8.2 关键配置详解

#### 8.2.1 缓冲区相关

```typescript
// 最大缓冲长度（秒）
maxBufferLength: number = 30;  // VoD
maxBufferLength: number = 60;  // Live

// 缓冲区之间允许的最大间隙（秒）
maxBufferHole: number = 0.1;

// 查找片段时的容差（秒）
maxFragLookUpTolerance: number = 0.25;
```

#### 8.2.2 ABR 相关

```typescript
// 默认带宽估计 (bps)
abrEwmaDefaultEstimate: number = 5000000;

// EWMA 加权系数
abrEwmaSlowVoD: number = 3.0;
abrEwmaFastVoD: number = 3.0;

// 带宽因子
abrBandWidthFactor: number = 0.95;
abrBandWidthUpFactor: number = 0.7;
```

#### 8.2.3 Seek 相关

```typescript
// 是否在视频 hole 时微调 currentTime
nudgeOnVideoHole: boolean = true;

// 最大 nudge 重试次数
nudgeMaxRetry: number = 3;

// 起始播放位置偏移
startTimeOffset: number | null = null;
```

---

## 9. 事件系统

### 9.1 事件监听示例

```typescript
const hls = new Hls();

// 监听 manifest 解析完成
hls.on(Hls.Events.MANIFEST_PARSED, (event, data) => {
  console.log('Available levels:', data.levels);
  console.log('Auto start level:', hls.firstAutoLevel);
});

// 监听片段加载
hls.on(Hls.Events.FRAG_LOADED, (event, data) => {
  console.log(`Fragment ${data.frag.sn} loaded`);
});

// 监听错误
hls.on(Hls.Events.ERROR, (event, data) => {
  console.error('Error:', data.type, data.details);
});
```

### 9.2 自定义事件触发

```typescript
// 在控制器中触发事件
this.hls.trigger(Events.FRAG_LOADED, {
  frag: this.fragCurrent,
  part: this.partCurrent,
  stats: stats
});
```

---

## 10. 新手入门指南

### 10.1 快速开始

```html
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
<video id="video"></video>
<script>
  const video = document.getElementById('video');
  const hls = new Hls();
  
  // 绑定视频元素
  hls.attachMedia(video);
  
  // 加载 HLS 流
  hls.loadSource('https://example.com/stream.m3u8');
  
  // 自动播放
  video.play();
</script>
```

### 10.2 调试技巧

1. **启用调试日志**：

```typescript
const hls = new Hls({
  debug: true  // 启用所有日志
});
```

2. **检查 buffer 状态**：

```typescript
setInterval(() => {
  const media = videoElement;
  console.log('Video buffered:', media.buffered);
  console.log('Current time:', media.currentTime);
}, 5000);
```

3. **监控事件**：

```typescript
// 监听所有事件
Object.values(Hls.Events).forEach(event => {
  hls.on(event, (eventName, data) => {
    console.log(`Event: ${eventName}`, data);
  });
});
```

### 10.3 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 视频卡住音频正常 | buffer hole | 检查 `nudgeOnVideoHole` 配置 |
| seek 后黑屏 | 片段加载失败 | 检查网络请求和 CORS 配置 |
| 自动切换清晰度 | ABR 策略 | 调整 `abrEwmaDefaultEstimate` |

### 10.4 使用 VSCode 调试 hls.js（详细图解）

本小节将手把手教你如何使用 VSCode 调试 hls.js 源代码，**确保即使是新手也能按步骤实施**。

---

#### 10.4.1 调试方式概览

hls.js 提供两种调试方式：

| 调试方式 | 适用场景 | 难度 |
|----------|----------|------|
| **方式一：调试单元测试** | 调试特定功能、验证代码逻辑 | ⭐⭐ |
| **方式二：调试 demo 页面** | 调试完整播放流程、真实浏览器环境 | ⭐⭐⭐ |

---

#### 10.4.2 准备工作

**步骤 1：克隆项目并安装依赖**

```bash
# 克隆项目
git clone https://github.com/video-dev/hls.js.git
cd hls.js

# 安装依赖（需要 Node.js 16+）
npm install
```

**步骤 2：确认 VSCode 已安装必要扩展**

打开 VSCode，确保已安装以下扩展：
- ✅ **Debugger for Chrome** (已弃用，推荐用 JS Debugger)
- ✅ **JavaScript Debugger** (VSCode 内置，无需安装)

> 💡 **提示**：VSCode 1.50+ 版本已内置 JavaScript Debugger，无需额外安装。

---

#### 10.4.3 方式一：调试单元测试（推荐新手）

**原理**：使用 Karma 启动 Chrome 浏览器运行测试，VSCode 通过 Debugger 附加到 Chrome。

##### 步骤 1：创建 VSCode 调试配置文件

在项目根目录下创建 `.vscode/launch.json` 文件：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug hls.js Unit Tests",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:9876/debug.html",
      "webRoot": "${workspaceFolder}",
      "sourceMaps": true,
      "breakOnLoad": true,
      "sourceMapPathOverrides": {
        "webpack:///./~/*": "${webRoot}/node_modules/*",
        "webpack:///./*": "${webRoot}/*",
        "webpack:///*": "/*"
      }
    }
  ]
}
```

##### 步骤 2：启动 Karma 测试服务器

打开 VSCode 终端（`Ctrl + \``），运行：

```bash
# 启动 Karma 并监听文件变化（调试模式）
npm run test:unit:debug
```

**预期输出**：

```text
> karma start karma.conf.js --auto-watch --no-single-run --browsers Chrome

Start: bolting karma-static-server
09 06 2024 10:00:00.000:INFO [karma-server]: Karma v6.4.4 server started at http://localhost:9876/
09 06 2024 10:00:00.000:INFO [launcher]: Launching browsers Chrome with concurrency unlimited
09 06 2024 10:00:00.000:INFO [Chrome]: Connected on socket ...
```

> ⚠️ **注意**：`test:unit:debug` 会设置环境变量 `DEBUG_UNIT_TESTS=1`，禁用代码覆盖率插桩，便于调试。

##### 步骤 3：设置断点

在 VSCode 中打开你想调试的源文件，例如 `src/hls.ts`，在感兴趣的行号左侧点击设置断点（会出现红色圆点）。

**建议断点位置**（适合新手）：

```text
src/hls.ts                    → line 200: constructor() 方法
src/controller/stream-controller.ts → line 300: doTick() 方法
src/demux/tsdemuxer.ts       → line 150: demux() 方法
```

##### 步骤 4：启动 VSCode 调试

1. 按 `F5` 或点击 VSCode 左侧调试图标 ▶️
2. 选择 **"Debug hls.js Unit Tests"** 配置
3. 点击绿色播放按钮

**此时会发生什么**：
- VSCode 会启动 Chrome 浏览器
- 浏览器会访问 `http://localhost:9876/debug.html`
- Karma 会运行测试，遇到断点会暂停
- VSCode 调试面板会显示变量、调用栈等信息

##### 步骤 5：调试操作

当断点命中时，你可以使用以下调试操作：

| 操作 | 快捷键 | 说明 |
|------|--------|------|
| 继续 | `F5` | 继续执行到下一个断点 |
| 单步跳过 | `F10` | 执行当前行，跳到下一行 |
| 单步进入 | `F11` | 进入函数内部 |
| 单步跳出 | `Shift+F11` | 跳出当前函数 |
| 重启 | `Ctrl+Shift+F5` | 重新开始调试 |
| 停止 | `Shift+F5` | 停止调试 |

---

#### 10.4.4 方式二：调试 Demo 页面（推荐进阶）

**原理**：启动本地 HTTP 服务器，在浏览器中打开 demo 页面，然后用 VSCode 附加到浏览器进行调试。

##### 步骤 1：构建调试版本

```bash
# 构建包含 source map 的调试版本
npm run build:debug
```

**构建输出**：

```text
dist/hls.js        ← 完整版（带 source map）
dist/hls-demo.js   ← demo 专用版（带 source map）
```

##### 步骤 2：启动本地服务器

```bash
# 启动 HTTP 服务器（会自动打开浏览器）
npm run dev
```

**预期效果**：
- 浏览器会自动打开 `http://127.0.0.1:8080/demo/`
- 页面显示 hls.js demo 界面

##### 步骤 3：创建 VSCode 附加调试配置

更新 `.vscode/launch.json`，添加附加配置：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Attach to Chrome (Demo)",
      "type": "chrome",
      "request": "attach",
      "port": 9222,
      "urlFilter": "http://localhost:8080/*",
      "webRoot": "${workspaceFolder}",
      "sourceMaps": true
    }
  ]
}
```

##### 步骤 4：以调试模式启动 Chrome

关闭所有 Chrome 窗口，然后用以下命令重启 Chrome（Windows）：

```bash
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222
```

> 💡 **提示**：也可以创建 Chrome 快捷方式，在目标中添加 `--remote-debugging-port=9222` 参数。

##### 步骤 5：在 demo 页面中操作

1. 在 Chrome 中打开 `http://localhost:8080/demo/`
2. 在页面输入框中输入 HLS 流地址（或使用下拉框选择）
3. 点击播放

**推荐测试流**（可复制到输入框）：
```text
# 测试流 1（点播）
https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8

# 测试流 2（直播）
http://qthttp.apple.com.edgesuite.net/1010qwoeiuryfg/sl.m3u8
```

##### 步骤 6：在 VSCode 中附加调试器

1. 按 `F5` 或打开调试面板
2. 选择 **"Attach to Chrome (Demo)"**
3. 点击绿色播放按钮

现在你可以在源代码中设置断点，demo 页面触发的 hls.js 代码会在 VSCode 中暂停！

---

#### 10.4.5 调试技巧与常见问题

##### 技巧 1：使用 `debugger` 语句

在源代码中直接插入 `debugger;` 语句，浏览器执行到此处会自动暂停：

```typescript
// 文件：src/hls.ts
loadSource(url: string) {
  debugger;  // ← 执行到这里会自动暂停
  this.url = url;
  // ...
}
```

##### 技巧 2：条件断点

右键点击断点 → 选择"编辑断点" → 输入条件：

```text
// 只有满足条件时才暂停
frag.sn === 5       // 只在加载第 5 个片段时暂停
level.height > 720  // 只在分辨率大于 720p 时暂停
```

##### 技巧 3：调试控制台

在 VSCode 调试控制台中，你可以：
- 查看变量值：`this.config`
- 执行表达式：`video.currentTime`
- 调用函数：`hls.destroy()`

##### 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 断点不生效 | Source Map 未生成 | 运行 `npm run build:debug` 重新构建 |
| 无法附加到 Chrome | Chrome 未开启调试端口 | 用 `--remote-debugging-port=9222` 重启 Chrome |
| 变量显示 "not available" | 代码被压缩/优化 | 使用 `build:debug` 构建未压缩版本 |
| 测试不运行 | Karma 未启动 | 先运行 `npm run test:unit:debug` |

---

#### 10.4.6 完整调试流程图

```text
┌─────────────────────────────────────────────────────────────────────┐
│                     VSCode 调试 hls.js 完整流程                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐                                                   │
│  │  1. 准备    │                                                   │
│  │  npm install│                                                   │
│  └──────┬──────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │  选择调试方式                                            │        │
│  │                                                         │        │
│  │  ┌──────────────┐        ┌──────────────┐             │        │
│  │  │ 方式一：      │        │ 方式二：      │             │        │
│  │  │ 调试单元测试  │        │ 调试 Demo 页面│             │        │
│  │  └──────┬───────┘        └──────┬───────┘             │        │
│  └─────────┼─────────────────────────┼─────────────────────┘        │
│            │                         │                              │
│            ▼                         ▼                              │
│  ┌─────────────────┐       ┌─────────────────┐                    │
│  │ npm run         │       │ npm run dev     │                    │
│  │ test:unit:debug │       │ (启动 HTTP 服务)│                    │
│  └────────┬────────┘       └────────┬────────┘                    │
│           │                          │                              │
│           ▼                          ▼                              │
│  ┌─────────────────┐       ┌─────────────────┐                    │
│  │ 创建 launch.json │       │ 用调试模式启动   │                    │
│  │ (launch 配置)   │       │ Chrome (9222端口)│                    │
│  └────────┬────────┘       └────────┬────────┘                    │
│           │                          │                              │
│           ▼                          ▼                              │
│  ┌─────────────────┐       ┌─────────────────┐                    │
│  │ F5 启动调试     │       │ 创建 launch.json │                    │
│  │ Chrome 自动打开 │       │ (attach 配置)   │                    │
│  └────────┬────────┘       └────────┬────────┘                    │
│           │                          │                              │
│           ▼                          ▼                              │
│  ┌─────────────────┐       ┌─────────────────┐                    │
│  │ 设置断点         │       │ F5 附加到 Chrome│                    │
│  │ 开始调试         │       │ 在 demo 中操作  │                    │
│  └─────────────────┘       └─────────────────┘                    │
│                                 │                                  │
│                                 ▼                                  │
│                       ┌─────────────────┐                          │
│                       │ 设置断点         │                          │
│                       │ 开始调试         │                          │
│                       └─────────────────┘                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

#### 10.4.7 推荐的第一个断点练习

如果你是第一次调试 hls.js，建议按以下步骤操作：

**练习：观察 HLS 流加载过程**

1. 打开 `src/hls.ts`，在 `loadSource(url)` 方法设置断点
2. 打开 `src/controller/stream-controller.ts`，在 `doTick()` 方法设置断点
3. 打开 `src/demux/tsdemuxer.ts`，在 `demux()` 方法设置断点
4. 启动调试（选择方式一或方式二）
5. 触发代码执行（运行测试或在 demo 中加载流）
6. 观察调用栈和变量变化

**你会看到**：
- `loadSource()` → 开始加载 HLS 流
- `doTick()` → 开始下载 `.ts` 片段
- `demux()` → 解析 TS 数据

---

### 10.5 调试配置参考：完整的 launch.json

为了方便复制，这里提供完整的 `.vscode/launch.json` 配置：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Unit Tests (Launch)",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:9876/debug.html",
      "webRoot": "${workspaceFolder}",
      "sourceMaps": true,
      "breakOnLoad": true,
      "skipFiles": ["node_modules/**", "dist/**"]
    },
    {
      "name": "Attach to Demo (Chrome)",
      "type": "chrome",
      "request": "attach",
      "port": 9222,
      "urlFilter": "http://localhost:8080/*",
      "webRoot": "${workspaceFolder}",
      "sourceMaps": true,
      "skipFiles": ["node_modules/**"]
    },
    {
      "name": "Debug Demo (Launch Chrome)",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:8080/demo/",
      "webRoot": "${workspaceFolder}",
      "sourceMaps": true,
      "runtimeArgs": ["--remote-debugging-port=9222"]
    }
  ]
}
```

---

## 11. 高手进阶话题

### 11.1 ABR (自适应码率) 算法深度分析

**文件**: `src/controller/abr-controller.ts`

ABR（Adaptive Bitrate）是 hls.js 的核心功能，根据当前网络带宽自动选择最合适的码率级别。

**工作原理**：
1. 通过 `fragmentLoader` 的加载统计计算实时带宽
2. 使用 EWMA（指数加权移动平均）平滑带宽估计
3. 根据估计带宽选择最合适的码率级别

**带宽估计核心类**: `EwmaBandWidthEstimator`

```typescript
// ============================================================================
// 类：EwmaBandWidthEstimator
// 功能：使用 EWMA 算法估计带宽
// 
// 【EWMA 原理】
// EWMA (Exponentially Weighted Moving Average) 指数加权移动平均
// 公式：estimate = α * 当前值 + (1-α) * 历史估计值
//   - α 越大：越看重当前值（反应快，但波动大）
//   - α 越小：越看重历史值（反应慢，但稳定）
//
// hls.js 使用两个 EWMA：
//   - slow: α = 1/slow (默认 3.0 → α ≈ 0.33) 慢速，更稳定
//   - fast: α = 1/fast (默认 3.0 → α ≈ 0.33) 快速，反应更快
// ============================================================================
class EwmaBandWidthEstimator {
  private readonly slow: number;  // 慢速 EWMA 系数（默认 3.0）
  private readonly fast: number;  // 快速 EWMA 系数（默认 3.0）
  private estimate: number;       // 当前带宽估计值（bps）
  
  // ==========================================================================
  // 函数：sample
  // 功能：采样一次带宽测量
  // 参数：
  //   - ms: 加载耗时（毫秒）
  //   - bytes: 加载字节数
  // 计算：bw = (bytes * 8000) / ms
  //        乘以 8000 是因为：
  //         - bytes → bits: * 8
  //         - ms → second: * 1000
  //         - 总系数: 8 * 1000 = 8000
  // ==========================================================================
  sample(ms: number, bytes: number): void {
    const bw = (bytes * 8000) / ms;  // 转换为 bps
    
    // ==========================================================================
    // EWMA 更新公式（这里简化表示）
    // 实际实现使用 slow/fast 系数控制平滑程度
    // ==========================================================================
    this.estimate = this.alpha * bw + (1 - this.alpha) * this.estimate;
  }
}
```

**级别选择算法** (`findBestLevel`):

```typescript
// ============================================================================
// 函数：findBestLevel
// 功能：根据当前带宽估计，找到最合适的码率级别
// 参数：
//   - currentBw: 当前带宽估计（bps）
//   - minAutoLevel: 最小自动级别（用户可选择）
//   - maxAutoLevel: 最大自动级别（用户可选择）
//   - bufferStarvationDelay: 缓冲区饥饿延迟（秒）
//   - maxStarvationDelay: 最大饥饿延迟（秒）
//   - bwFactor: 向下切换时的带宽因子
//   - bwUpFactor: 向上切换时的带宽因子
// 返回：合适的级别索引，或 -1（保持当前级别）
//
// 【选择策略】
// 1. 从高到低遍历所有级别（优先选择高码率）
// 2. 检查条件：
//    a. 调整后的带宽 >= 级别码率
//    b. 预计加载时间 < 最大允许时间
// 3. 第一次满足条件的级别就是最佳选择
// ============================================================================
private findBestLevel(
  currentBw: number,
  minAutoLevel: number,
  maxAutoLevel: number,
  bufferStarvationDelay: number,
  maxStarvationDelay: number,
  bwFactor: number,
  bwUpFactor: number
): number {
  // ==========================================================================
  // 【步骤 1】从高到低遍历所有级别
  // 为什么从高到低？
  //   - 优先保证质量（能播高清就播高清）
  //   - 第一次满足条件的就是最佳（最高码率）
  // ==========================================================================
  for (let i = maxAutoLevel; i >= minAutoLevel; i--) {
    const level = levels[i];
    
    // ==========================================================================
    // 【步骤 2】计算调整后的带宽
    //   - 向上切换 (upSwitch = true): 更保守（避免频繁切换）
    //     使用 bwUpFactor (默认 0.7): 只考虑 70% 的带宽
    //   - 向下切换 (upSwitch = false): 更激进
    //     使用 bwFactor (默认 0.95): 考虑 95% 的带宽
    // ==========================================================================
    const adjustedBw = upSwitch 
      ? bwUpFactor * currentBw    // 向上切换更保守
      : bwFactor * currentBw;     // 向下切换更激进
    
    // ==========================================================================
    // 【步骤 3】检查是否可以在饥饿延迟内加载完成
    // getTimeToLoadFrag(): 预估加载一个片段需要的时间
    // maxFetchDuration: 最大允许加载时间
    //   = maxStarvationDelay - bufferStarvationDelay
    //   如果缓冲区还剩 2 秒，maxStarvationDelay = 5 秒
    //   → maxFetchDuration = 3 秒（必须 3 秒内加载完成）
    // ==========================================================================
    const fetchDuration = this.getTimeToLoadFrag(...);
    const maxFetchDuration = maxStarvationDelay - bufferStarvationDelay;
    
    // ==========================================================================
    // 【步骤 4】满足条件就选择这个级别
    // 条件 A: 调整后的带宽 >= 级别码率（带宽够用）
    // 条件 B: 预计加载时间 < 最大允许时间（不会饿死）
    // ==========================================================================
    if (adjustedBw >= level.bitrate && fetchDuration < maxFetchDuration) {
      return i;  // 找到合适级别
    }
  }
  return -1;  // 没有找到合适级别（保持当前级别）
}
```

**ABR 切换决策示意图**：
```text
带宽估计: 2000 kbps
级别列表:
  - 级别 3: 3000 kbps (1080p)
  - 级别 2: 1500 kbps (720p)  ← 满足条件，选择这个
  - 级别 1: 800 kbps (480p)
  - 级别 0: 400 kbps (360p)

检查过程：
  级别 3: 2000 >= 3000? NO → 跳过
  级别 2: 2000 >= 1500? YES → 检查加载时间
          加载时间 1.5s < maxFetchDuration 3s? YES → 选择！
```

### 11.2 Fragment 跟踪机制

**文件**: `src/controller/fragment-tracker.ts`

**为什么需要 Fragment 跟踪？**
- MSE 的 `SourceBuffer` 会自动管理缓冲区（可能驱逐旧数据）
- hls.js 需要知道哪些片段已经被驱逐，以便重新加载
- 还需要跟踪片段状态（加载中、已缓冲、部分缓冲等）

`FragmentTracker` 负责跟踪每个片段的状态，包括：
- 是否已加载
- 是否已追加到 buffer
- 是否是部分缓冲 (partial)
- 是否存在 gap

**Fragment 状态机**：

```text
NOT_LOADED (未加载)
     │
     │ load() 开始加载
     ▼
LOADING (加载中)
     │
     │ FRAG_LOADED 加载完成
     ▼
APPENDING (追加中) ──────▶ PARTIAL (部分缓冲)
     │                          │
     │ BUFFER_APPENDED         │ 需要补加载剩余部分
     ▼                          │
  OK (完成) ──────────────────┘
```

**状态说明**：
- `NOT_LOADED`: 片段还没开始加载
- `LOADING`: 正在从网络下载
- `APPENDING`: 已下载完成，正在追加到 SourceBuffer
- `OK`: 完全缓冲，可以播放
- `PARTIAL`: 部分缓冲（如只有音频，没有视频）

**关键方法**：

```typescript
// ============================================================================
// 函数：detectEvictedFragments
// 功能：检测被浏览器驱逐的片段 (buffer eviction)
// 参数：
//   - elementaryStream: 'audio' 或 'video'，指定轨道
//   - timeRange: 当前的 TimeRanges（浏览器返回的缓冲区范围）
//   - playlistType: VOD 或 LIVE
//
// 【背景知识】
// 浏览器可能会在缓冲区太大时自动驱逐旧数据
// 这需要 hls.js 重新加载被驱逐的片段
// ============================================================================
detectEvictedFragments(
  elementaryStream: SourceBufferName,
  timeRange: TimeRanges,
  playlistType: PlaylistLevelType
) {
  // ==========================================================================
  // 【步骤 1】遍历所有跟踪的片段
  // this.fragments: Map<key, { body: Fragment, range: TimeRange }>
  // key 通常是片段的 URL 或 SN (sequence number)
  // ==========================================================================
  Object.keys(this.fragments).forEach((key) => {
    const fragmentEntity = this.fragments[key];
    
    // ==========================================================================
    // 【步骤 2】检查片段是否还在 buffer 中
    // isTimeBuffered(): 检查片段的时间范围是否完全在 timeRange 内
    // 
    // 举例：
    //   片段范围: [10s, 20s]
    //   当前 buffer: [0s, 15s] [18s, 30s]
    //   → 10-15s 在 buffer 中，但 15-18s 不在
    //   → isTimeBuffered() 返回 false → 片段被驱逐
    // ==========================================================================
    const isBuffered = this.isTimeBuffered(
      fragmentEntity.range.startPTS,
      fragmentEntity.range.endPTS,
      timeRange
    );
    
    // ==========================================================================
    // 【步骤 3】如果不在 buffer 中，移除跟踪并触发重新加载
    // ==========================================================================
    if (!isBuffered) {
      // 从跟踪列表中移除
      this.removeFragment(fragmentEntity.body);
      
      // 触发 FRAG_BUFFERED 事件（状态 = NEED_RELOAD）
      // StreamController 会收到这个事件并重新加载片段
      this.hls.trigger(Hls.Events.FRAG_BUFFERED, {
        frag: fragmentEntity.body,
        need: true  // 需要重新加载
      });
    }
  });
}
```

**isTimeBuffered 实现逻辑**：
```typescript
// 检查给定时间范围是否完全在 TimeRanges 内
private isTimeBuffered(
  startPTS: number,
  endPTS: number,
  timeRanges: TimeRanges
): boolean {
  // 遍历所有 TimeRange
  for (let i = 0; i < timeRanges.length; i++) {
    const rangeStart = timeRanges.start(i);
    const rangeEnd = timeRanges.end(i);
    
    // 如果 [startPTS, endPTS] 完全在 [rangeStart, rangeEnd] 内
    if (startPTS >= rangeStart && endPTS <= rangeEnd) {
      return true;  // 完全缓冲
    }
  }
  return false;  // 没有完全缓冲（可能被驱逐）
}
```

### 11.3 Transmuxer 深度分析

**文件**: `src/demux/transmuxer.ts`

Transmuxer 是处理音视频数据的核心模块，负责：
1. 检测容器格式 (TS/MP4/AAC/MP3)
2. 解复用 (demux)
3. 转封装 (remux to MP4)

**格式探测与处理链**：

```typescript
const muxConfig: MuxConfig[] = [
  { demux: MP4Demuxer, remux: PassThroughRemuxer },  // MP4 透传
  { demux: TSDemuxer, remux: MP4Remuxer },          // TS → MP4
  { demux: AACDemuxer, remux: MP4Remuxer },          // AAC → MP4
  { demux: MP3Demuxer, remux: MP4Remuxer },          // MP3 → MP4
];

// 自动探测格式
private configureTransmuxer(data: Uint8Array) {
  for (let i = 0; i < muxConfig.length; i++) {
    if (muxConfig[i].demux.probe(data)) {
      // 创建对应的 demuxer 和 remuxer
      this.demuxer = new muxConfig[i].demux(...);
      this.remuxer = new muxConfig[i].remux(...);
      break;
    }
  }
}
```

### 11.4 低延迟 HLS (LL-HLS) 支持

hls.js 支持 HLS 协议的最新扩展，包括：

1. **Partial Segments (Parts)**:

```typescript
// 在 M3U8 解析中处理 #EXT-X-PART
case 'PART': {
  const partAttrs = new AttrList(value1, level);
  const part = new Part(partAttrs, frag, base, index, previousPart);
  level.partList.push(part);
}
```

2. **Blocking Playlist Reload**:

```typescript
// 服务器支持 CAN-BLOCK-RELOAD
if (level.canBlockReload) {
  // 阻塞请求直到新片段可用
  url += `_HLS_msn=${nextMsn}`;
}
```

3. **Delta Playlist Updates**:

```typescript
// 只下载变化的片段
if (level.canSkipUntil > 0) {
  url += `_HLS_skip=YES`;
}
```

### 11.5 性能优化建议

1. **使用 Web Worker**:

```typescript
const hls = new Hls({
  enableWorker: true  // 在 worker 线程中运行转复用
});
```

2. **调整缓冲区策略**:

```typescript
const hls = new Hls({
  maxBufferLength: 60,      // 增加缓冲区长度
  maxMaxBufferLength: 600,  // 允许更大的缓冲区
  backBufferLength: 30,      // 保留后退缓冲区
});
```

3. **优化 ABR 行为**:

```typescript
const hls = new Hls({
  abrEwmaDefaultEstimate: 2000000,  // 设置起始带宽估计
  abrSwitchInterval: 2,             // ABR 切换间隔（秒）
  maxStarvationDelay: 2,            // 最大饥饿延迟
});
```

---

## 附录

### A. 术语表

| 术语 | 解释 |
|------|------|
| HLS | HTTP Live Streaming，Apple 开发的流媒体协议 |
| MSE | MediaSource Extensions，浏览器媒体扩展 API |
| SourceBuffer | MSE 中用于接收媒体数据的缓冲区 |
| Fragment | HLS 中的一个媒体片段 (TS 或 MP4 文件) |
| Segment | 同 Fragment |
| Part | LL-HLS 中的部分片段 |
| PTS | Presentation Time Stamp，显示时间戳 |
| DTS | Decoding Time Stamp，解码时间戳 |
| ABR | Adaptive Bitrate，自适应码率 |
| GOP | Group of Pictures，一组图像 |
| init segment | 初始化段，包含解码器配置 |

### B. 参考资料

- [HLS 协议规范 (RFC 8216)](https://tools.ietf.org/html/rfc8216)
- [MediaSource Extensions 规范](https://www.w3.org/TR/media-source/)
- [hls.js GitHub 仓库](https://github.com/video-dev/hls.js)
- [Can I use MSE?](https://caniuse.com/mediasource)

---

*文档结束*
