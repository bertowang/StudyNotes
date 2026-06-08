> **作者**：汪亮 (bertonwang)  
> **邮箱**：47608843@qq.com  
> **源码仓库**：https://github.com/FFmpeg/FFmpeg.git  
> **源码版本**：FFmpeg master 分支（基于当前工程树分析）  
> **分析基准 commit**：`6028720d70d0f50512c66df43f7c9e05d6797463`（2026-06-06）  
> **文档版本**：v2.0  
> **更新日期**：2026-06-08  
> **适用读者**：从编程初学者到高级开发者  
> **许可证**：LGPL v2.1+ / GPL v2+
> 
> 🔗 **Replay 说明**：本文档所有源码行号、结构体定义均基于上述 commit。  
> 若需对照阅读，请执行：`git clone https://github.com/FFmpeg/FFmpeg.git && git checkout 6028720d70d0f50512c66df43f7c9e05d6797463`

# FFmpeg 源码学习指南

> 本文档不是 API 手册的翻译，而是对 FFmpeg **设计决策**的深度解析。  
> 每个关键点都对应到具体源码位置（文件名 + 行号），方便读者对照阅读。

---

## 📚 目录

1. [项目概述](#1-项目概述)
2. [目录结构总览](#2-目录结构总览)
3. [核心概念与设计哲学](#3-核心概念与设计哲学)
4. [基础数据结构与工具层](#4-基础数据结构与工具层)
5. [核心库深入解析](#5-核心库深入解析)
6. [ffmpeg 工具的调度器架构](#6-ffmpeg-工具的调度器架构)
7. [完整转码流程分析](#7-完整转码流程分析)
8. [滤镜系统深度解析](#8-滤镜系统深度解析)
9. [硬件加速机制](#9-硬件加速机制)
10. [自定义滤镜开发实战](#10-自定义滤镜开发实战)
11. [调试与诊断](#11-调试与诊断)
12. [设计洞察汇总](#12-设计洞察汇总)
13. [学习路径建议](#13-学习路径建议)
14. [源码文件索引](#14-源码文件索引)
15. [附录：常见陷阱与最佳实践](#15-附录常见陷阱与最佳实践)
16. [附录：插件开发实战指南](#16-附录插件开发实战指南)

---

## 1. 项目概述

### 1.1 什么是 FFmpeg？

FFmpeg 是一个完整的跨平台多媒体处理框架，诞生于 2000 年，由 Fabrice Bellard 创建。它包含：

- **7 个核心库**：覆盖编解码、封装/解封装、滤镜、设备、重采样、缩放等
- **3 个命令行工具**：`ffmpeg`（转码）、`ffplay`（播放）、`ffprobe`（分析）
- **数百个编解码器**：支持几乎所有主流音视频格式

### 1.2 核心库一览

| 库名 | 功能 | 初学者理解 | 高手关注点 |
|------|------|-----------|-----------|
| **libavcodec** | 编解码 | 压缩/解压缩音视频数据 | 硬件加速、编解码器优化、码率控制 |
| **libavformat** | 封装/解封装 | 读写各种音视频格式文件 | 自定义格式、流媒体协议、索引构建 |
| **libavutil** | 通用工具 | 基础工具函数和数据结构 | 内存管理、引用计数、数学运算 |
| **libavfilter** | 滤镜处理 | 音视频特效和格式转换 | 自定义滤镜、滤镜图优化、切片多线程 |
| **libavdevice** | 设备访问 | 摄像头、麦克风等硬件 | 跨平台设备采集、实时流 |
| **libswresample** | 音频重采样 | 转换采样率、声道布局 | 高质量重采样算法、延迟控制 |
| **libswscale** | 视频缩放 | 像素格式转换、缩放 | SIMD 优化、色彩空间转换精度 |

### 1.3 命令行工具

| 工具 | 功能 | 核心源文件 |
|------|------|-----------|
| **ffmpeg** | 音视频转码器 | `fftools/ffmpeg.c`（主入口，1059 行） |
| **ffplay** | 简单播放器 | `fftools/ffplay.c`（145KB，SDL2 渲染） |
| **ffprobe** | 媒体分析器 | `fftools/ffprobe.c`（154KB，多格式输出） |

### 1.4 许可证说明

```
FFmpeg 双许可证策略：

LGPL v2.1+（默认）：
  ✅ 允许在闭源商业软件中动态链接使用
  ✅ 修改 FFmpeg 本身需要开源
  ❌ 不能静态链接到闭源软件

GPL v2+（启用 --enable-gpl 后）：
  ✅ 可使用 x264、x265 等 GPL 编解码器
  ❌ 你的软件也必须以 GPL 开源
```

> **商业开发建议**：使用 LGPL 版本，动态链接，避免引入 GPL 组件。

---

## 2. 目录结构总览

### 2.1 顶层目录树

```
FFmpeg/
├── libavcodec/          # 编解码库（~1700+ 文件，最大的库）
├── libavformat/         # 封装/解封装库（~500+ 文件）
├── libavutil/           # 通用工具库（~200+ 文件）
├── libavfilter/         # 滤镜库（~800+ 文件）
├── libavdevice/         # 设备库（~50+ 文件）
├── libswresample/       # 音频重采样库（~30 文件）
├── libswscale/          # 视频缩放库（~30 文件）
├── fftools/             # 命令行工具源码（~30 文件）
│   ├── ffmpeg.c         # ffmpeg 主程序入口（1059 行）
│   ├── ffmpeg.h         # 核心数据结构定义（992 行）
│   ├── ffmpeg_sched.h   # 调度器 API（514 行）★ 新架构核心
│   ├── ffmpeg_sched.c   # 调度器实现（~79KB）
│   ├── ffmpeg_dec.c     # 解码模块（~57KB）
│   ├── ffmpeg_enc.c     # 编码模块（~32KB）
│   ├── ffmpeg_filter.c  # 滤镜模块（~115KB，最复杂）
│   ├── ffmpeg_demux.c   # 解封装模块（~83KB）
│   ├── ffmpeg_mux.c     # 封装模块（~26KB）
│   ├── ffmpeg_mux_init.c# 封装初始化（~122KB）
│   ├── ffmpeg_opt.c     # 选项解析（~90KB）
│   ├── ffmpeg_hw.c      # 硬件加速（~9KB）
│   ├── sync_queue.c     # 同步队列（~23KB）
│   ├── thread_queue.c   # 线程队列（~7KB）
│   ├── ffplay.c         # ffplay 播放器（~146KB）
│   └── ffprobe.c        # ffprobe 分析器（~155KB）
├── doc/
│   ├── examples/        # 官方示例代码（28 个示例）★ 必读
│   └── writing_filters.txt  # 滤镜开发指南
├── compat/              # 跨平台兼容代码
├── configure            # 配置脚本（315KB！）
└── Makefile             # 主构建文件
```

### 2.2 推荐阅读顺序

| 阶段 | 文件 | 预计时间 | 目标 |
|------|------|---------|------|
| 入门 | `libavutil/avutil.h` | 1h | 理解基础类型和时间系统 |
| 入门 | `libavutil/frame.h` | 2h | 理解 AVFrame 数据结构 |
| 入门 | `libavutil/buffer.h` | 1h | 理解引用计数机制 |
| 基础 | `libavcodec/avcodec.h` | 4h | 理解编解码 API |
| 基础 | `libavformat/avformat.h` | 4h | 理解封装/解封装 API |
| 基础 | `doc/examples/demux_decode.c` | 2h | 完整解码示例 |
| 进阶 | `fftools/ffmpeg.h` | 3h | 理解 ffmpeg 工具数据结构 |
| 进阶 | `fftools/ffmpeg_sched.h` | 3h | 理解调度器架构 |
| 进阶 | `libavfilter/avfilter.h` | 4h | 理解滤镜系统 |
| 高级 | `fftools/ffmpeg_filter.c` | 8h | 滤镜图完整实现 |
| 高级 | `fftools/ffmpeg_sched.c` | 8h | 调度器完整实现 |

---

## 3. 核心概念与设计哲学

### 3.1 三层抽象模型

FFmpeg 的整体设计遵循三层抽象：

```
┌─────────────────────────────────────────────────┐
│              应用层（命令行工具）                  │
│   ffmpeg / ffplay / ffprobe / 你的应用程序        │
└──────────────────┬──────────────────────────────┘
                   │ 调用
┌──────────────────▼──────────────────────────────┐
│              API 层（公共头文件）                  │
│  avformat.h / avcodec.h / avfilter.h / ...       │
└──────────────────┬──────────────────────────────┘
                   │ 实现
┌──────────────────▼──────────────────────────────┐
│              实现层（.c 文件）                     │
│  具体编解码器 / 格式解析器 / 滤镜实现 / ...         │
└─────────────────────────────────────────────────┘
```

### 3.2 数据流模型

FFmpeg 的数据流是一个有向无环图（DAG）：

```
输入文件                                    输出文件
   │                                           ▲
   ▼                                           │
[解封装器]──AVPacket──▶[解码器]──AVFrame──▶[滤镜图]──AVFrame──▶[编码器]──AVPacket──▶[封装器]
   │                                                                                    │
   └──────────────────────────────AVPacket（流复制）──────────────────────────────────▶┘
```

**关键数据类型**：
- `AVPacket`：压缩数据（编码后的码流）
- `AVFrame`：原始数据（解码后的 YUV/PCM）

### 3.3 命名规范解读

理解 FFmpeg 的命名规范，能大幅提升阅读源码的效率：

| 前缀 | 含义 | 示例 |
|------|------|------|
| `av_` | libavutil 通用函数 | `av_malloc()`, `av_frame_alloc()` |
| `avcodec_` | libavcodec 函数 | `avcodec_open2()`, `avcodec_send_packet()` |
| `avformat_` | libavformat 函数 | `avformat_open_input()` |
| `avfilter_` | libavfilter 函数 | `avfilter_graph_alloc()` |
| `swr_` | libswresample 函数 | `swr_convert()` |
| `sws_` | libswscale 函数 | `sws_scale()` |
| `ff_` | 内部函数（不对外暴露） | `ff_filter_frame()` |
| `AV_` | 宏/枚举常量 | `AV_CODEC_ID_H264`, `AV_PIX_FMT_YUV420P` |
| `AVERROR` | 错误码宏 | `AVERROR(ENOMEM)`, `AVERROR_EOF` |

**结构体命名规律**：
- `AVCodecContext` → 编解码器**上下文**（运行时状态）
- `AVCodec` → 编解码器**描述**（静态信息）
- `AVCodecParameters` → 编解码器**参数**（流参数，不含运行时状态）

### 3.4 关键设计决策

| 决策 | 选择 | 代价 | 收益 |
|------|------|------|------|
| 引用计数缓冲区 | `AVBufferRef` | 代码复杂度增加 | 零拷贝数据传递，线程安全 |
| 有理数时间戳 | `AVRational` | 需要显式转换 | 精确表示任意帧率，无浮点误差 |
| 推模型解码 API | send/receive | 状态机复杂 | 支持 B 帧重排序，解耦输入输出 |
| 调度器架构 | `Scheduler` | 实现复杂 | 多线程流水线，各组件解耦 |
| 滤镜图 DAG | `AVFilterGraph` | 配置复杂 | 任意拓扑的处理管线 |

---

## 4. 基础数据结构与工具层

### 4.1 AVBufferRef — 引用计数缓冲区

**定义位置**：`libavutil/buffer.h`（323 行）

这是 FFmpeg 中**最重要的基础设施**，理解它是理解 AVFrame/AVPacket 的前提。

```c
/* libavutil/buffer.h */

// AVBuffer 是不透明的，只能通过 AVBufferRef 访问
typedef struct AVBuffer AVBuffer;

// 引用 = 指向同一块内存的"票据"
typedef struct AVBufferRef {
    AVBuffer *buffer;   // 指向实际的缓冲区对象（含引用计数）

    uint8_t  *data;     // 数据指针（可能指向 buffer 内部的某个偏移位置）
    size_t    size;     // 数据大小（字节）
} AVBufferRef;
```

**引用计数工作原理**：

```
初始状态：
  AVBuffer（引用计数=1）
       ▲
       │
  AVBufferRef A（data 指向 buffer 内存）

调用 av_buffer_ref(A) 后：
  AVBuffer（引用计数=2）
       ▲         ▲
       │         │
  AVBufferRef A  AVBufferRef B（共享同一块内存，零拷贝！）

调用 av_buffer_unref(&A) 后：
  AVBuffer（引用计数=1）
               ▲
               │
          AVBufferRef B（A 已释放，但内存未释放）

调用 av_buffer_unref(&B) 后：
  内存被释放（引用计数降为 0）
```

**核心 API**：

```c
// 分配新缓冲区（引用计数=1）
AVBufferRef *av_buffer_alloc(size_t size);

// 增加引用（引用计数+1，零拷贝）
AVBufferRef *av_buffer_ref(const AVBufferRef *buf);

// 释放引用（引用计数-1，为0时释放内存）
void av_buffer_unref(AVBufferRef **buf);

// 检查是否可写（引用计数==1 时才可写）
int av_buffer_is_writable(const AVBufferRef *buf);

// 确保可写（如果引用计数>1，则复制一份）
int av_buffer_make_writable(AVBufferRef **buf);
```

> **设计洞察**：写时复制（Copy-on-Write）策略。只要引用计数 > 1，数据就是只读的。
> 这使得多个滤镜可以安全地共享同一帧数据，而不需要复制。

**缓冲区池（AVBufferPool）**：

```c
// 创建缓冲区池（避免频繁 malloc/free）
AVBufferPool *pool = av_buffer_pool_init(frame_size, NULL);

// 从池中获取缓冲区（优先复用已释放的）
AVBufferRef *buf = av_buffer_pool_get(pool);

// 释放引用（引用计数为0时，缓冲区归还池而非释放）
av_buffer_unref(&buf);

// 销毁池（所有缓冲区归还后才真正释放）
av_buffer_pool_uninit(&pool);
```

### 4.2 AVFrame — 原始媒体帧

**定义位置**：`libavutil/frame.h`（1209 行）

`AVFrame` 是 FFmpeg 中传递**原始（未压缩）**音视频数据的核心结构。

```c
/* libavutil/frame.h（关键字段，含注释） */
typedef struct AVFrame {
    // ===== 数据存储 =====
    #define AV_NUM_DATA_POINTERS 8
    uint8_t *data[AV_NUM_DATA_POINTERS];    // 各平面数据指针
    int linesize[AV_NUM_DATA_POINTERS];      // 各平面每行字节数（含对齐填充）
    uint8_t **extended_data;                 // 音频多声道时指向扩展数组

    // ===== 视频属性 =====
    int width, height;                       // 视频宽高（像素）
    enum AVPixelFormat format;               // 像素格式（如 AV_PIX_FMT_YUV420P）
    int key_frame;                           // 是否为关键帧（1=是）
    enum AVPictureType pict_type;            // 帧类型（AV_PICTURE_TYPE_I/P/B）
    AVRational sample_aspect_ratio;          // 像素宽高比

    // ===== 音频属性 =====
    int nb_samples;                          // 每声道采样数
    int sample_rate;                         // 采样率（Hz）
    AVChannelLayout ch_layout;               // 声道布局（如立体声）

    // ===== 时间信息 =====
    int64_t pts;                             // 显示时间戳（Presentation Timestamp）
    int64_t pkt_dts;                         // 来自 AVPacket 的解码时间戳
    int64_t duration;                        // 帧持续时间（时间基单位）
    AVRational time_base;                    // 时间基（如 {1, 90000}）

    // ===== 引用计数缓冲区 =====
    AVBufferRef *buf[AV_NUM_DATA_POINTERS];  // 各平面的缓冲区引用
    AVBufferRef **extended_buf;              // 音频扩展缓冲区引用

    // ===== 附加数据 =====
    AVFrameSideData **side_data;             // 附加数据（HDR、运动向量等）
    int nb_side_data;
    AVDictionary *metadata;                  // 元数据字典
    AVBufferRef *opaque_ref;                 // 用户自定义附加数据（ffmpeg 工具用于传递 FrameData）
} AVFrame;
```

**视频数据内存布局（YUV420P 格式）**：

```
data[0] ──▶ Y 平面（亮度）
            ┌──────────────────────────────────┬──────┐
            │  Y Y Y Y Y Y Y Y Y Y Y Y Y Y Y Y │ 填充 │ ← linesize[0]（≥ width）
            │  Y Y Y Y Y Y Y Y Y Y Y Y Y Y Y Y │      │
            │  ...（height 行）                 │      │
            └──────────────────────────────────┴──────┘

data[1] ──▶ U 平面（色度，宽高各为 Y 的一半）
            ┌────────────────┬──────┐
            │  U U U U U U U │ 填充 │ ← linesize[1]（≥ width/2）
            │  ...（height/2 行）   │
            └────────────────┴──────┘

data[2] ──▶ V 平面（色度，同 U）
```

> **⚠️ 常见错误**：`linesize[0]` 不等于 `width`！因为内存对齐，`linesize` 可能更大。
> 遍历像素时必须用 `linesize` 作为行步长，而不是 `width`。

**音频数据内存布局**：

```
交错格式（AV_SAMPLE_FMT_S16）：
data[0] ──▶ L R L R L R L R ...（左右声道交错）

平面格式（AV_SAMPLE_FMT_S16P）：
data[0] ──▶ L L L L L L L L ...（左声道）
data[1] ──▶ R R R R R R R R ...（右声道）
```

**正确的 AVFrame 使用模式**：

```c
// ✅ 正确：分配帧
AVFrame *frame = av_frame_alloc();

// ✅ 正确：分配数据缓冲区
frame->format = AV_PIX_FMT_YUV420P;
frame->width  = 1920;
frame->height = 1080;
av_frame_get_buffer(frame, 0);  // 自动分配并设置 data[] 和 linesize[]

// ✅ 正确：引用另一帧（零拷贝）
AVFrame *ref = av_frame_alloc();
av_frame_ref(ref, frame);       // ref 和 frame 共享数据，引用计数+1

// ✅ 正确：释放引用
av_frame_unref(frame);          // 引用计数-1，不一定释放内存
av_frame_free(&frame);          // 释放 AVFrame 结构体本身
```

### 4.3 AVPacket — 压缩数据包

**定义位置**：`libavcodec/packet.h`

```c
typedef struct AVPacket {
    AVBufferRef *buf;       // 数据缓冲区引用（管理 data 的生命周期）
    int64_t pts;            // 显示时间戳（Presentation Timestamp）
    int64_t dts;            // 解码时间戳（Decoding Timestamp）
    uint8_t *data;          // 压缩数据指针（指向 buf->data）
    int   size;             // 压缩数据大小（字节）
    int   stream_index;     // 所属流的索引
    int   flags;            // 标志（AV_PKT_FLAG_KEY = 关键帧）
    int64_t duration;       // 持续时间（流时间基单位）
    int64_t pos;            // 在文件中的字节偏移（-1 表示未知）
    AVBufferRef *opaque_ref;// 用户自定义附加数据
} AVPacket;
```

**PTS vs DTS 的区别**：

```
B 帧场景（编码顺序 vs 显示顺序不同）：

编码顺序（DTS）：  I  P  B  P  B  B  P ...
显示顺序（PTS）：  I  B  B  P  B  B  P ...

DTS（Decoding Timestamp）：解码器按 DTS 顺序解码
PTS（Presentation Timestamp）：播放器按 PTS 顺序显示

对于没有 B 帧的流（如 H.264 Baseline），DTS == PTS
```

### 4.4 AVRational — 有理数时间系统

**定义位置**：`libavutil/rational.h`

```c
typedef struct AVRational {
    int num;  // 分子（numerator）
    int den;  // 分母（denominator）
} AVRational;
```

**为什么用分数而不是浮点数？**

```c
// 问题：浮点数无法精确表示 1/3
double fps = 1.0 / 3.0;  // 实际是 0.3333333333333333...

// 解决：用分数精确表示
AVRational fps = {1, 3};  // 精确的 1/3

// 常见时间基
AVRational tb_mpeg_ts = {1, 90000};  // MPEG-TS：1/90000 秒
AVRational tb_codec   = {1, 25};     // 25fps 编解码器时间基
AVRational tb_ffmpeg  = {1, 1000000};// FFmpeg 内部：微秒
```

**时间戳转换（最常用操作）**：

```c
// 将 pts 从流时间基转换为秒
double pts_seconds = frame->pts * av_q2d(stream->time_base);

// 将 pts 从一个时间基转换到另一个时间基（精确整数运算）
int64_t pts_new = av_rescale_q(pts_old, src_time_base, dst_time_base);

// 示例：将解码器时间基的 pts 转换为流时间基
int64_t pts_stream = av_rescale_q(frame->pts,
                                   codec_ctx->time_base,   // 源：编解码器时间基
                                   stream->time_base);      // 目标：流时间基
```

---

## 5. 核心库深入解析

### 5.1 libavcodec — 编解码库

#### 5.1.1 核心数据结构关系

```
AVCodec（静态描述，全局唯一）
  │
  │ avcodec_alloc_context3()
  ▼
AVCodecContext（运行时状态，每个流一个）
  │
  │ avcodec_parameters_to_context()
  │ ← AVCodecParameters（流参数，来自 AVStream）
  │
  │ avcodec_open2()
  ▼
已初始化的编解码器（可以 send/receive）
```

**AVCodecContext 关键字段**：

```c
/* libavcodec/avcodec.h（简化版，含注释） */
typedef struct AVCodecContext {
    const AVCodec *codec;           // 指向编解码器描述（只读）
    enum AVMediaType codec_type;    // AVMEDIA_TYPE_VIDEO / AUDIO / SUBTITLE
    enum AVCodecID codec_id;        // AV_CODEC_ID_H264 / AAC / ...

    // ===== 视频参数 =====
    int width, height;              // 视频分辨率
    enum AVPixelFormat pix_fmt;     // 像素格式
    AVRational time_base;           // 编解码器时间基（注意：不同于流时间基！）
    AVRational framerate;           // 帧率
    int gop_size;                   // GOP 大小（关键帧间隔）
    int max_b_frames;               // 最大 B 帧数

    // ===== 音频参数 =====
    int sample_rate;                // 采样率（Hz）
    enum AVSampleFormat sample_fmt; // 采样格式（AV_SAMPLE_FMT_S16P 等）
    AVChannelLayout ch_layout;      // 声道布局

    // ===== 通用参数 =====
    int64_t bit_rate;               // 目标比特率（bps）
    int thread_count;               // 解码线程数（0=自动）
    int thread_type;                // FF_THREAD_FRAME | FF_THREAD_SLICE

    // ===== 硬件加速 =====
    AVBufferRef *hw_device_ctx;     // 硬件设备上下文
    AVBufferRef *hw_frames_ctx;     // 硬件帧上下文
    enum AVPixelFormat (*get_format)(struct AVCodecContext*, const enum AVPixelFormat*);
                                    // 格式协商回调（硬件加速时使用）
} AVCodecContext;
```

#### 5.1.2 推模型（Push Model）解码 API

FFmpeg 4.0 引入了新的 send/receive API，替代了旧的 `avcodec_decode_video2()`：

```
旧 API（已废弃）：
  avcodec_decode_video2(ctx, frame, &got_frame, pkt)
  问题：一次调用只能处理一个包，无法处理 B 帧重排序

新 API（推模型）：
  avcodec_send_packet(ctx, pkt)    ← 推入压缩数据
  avcodec_receive_frame(ctx, frame) ← 拉出解码帧（可能需要多次调用）
  优势：解耦输入和输出，支持 B 帧、多线程
```

**完整解码循环**：

```c
// 发送一个压缩包
int ret = avcodec_send_packet(codec_ctx, pkt);
if (ret == AVERROR(EAGAIN)) {
    // 解码器缓冲区满，需要先 receive_frame
} else if (ret == AVERROR_EOF) {
    // 解码器已关闭
} else if (ret < 0) {
    // 真正的错误
}

// 接收所有可用的解码帧（一个包可能产生多帧，或需要多个包才能产生一帧）
while (1) {
    ret = avcodec_receive_frame(codec_ctx, frame);
    if (ret == AVERROR(EAGAIN)) {
        break;  // 需要更多输入包，退出循环
    } else if (ret == AVERROR_EOF) {
        break;  // 解码器已刷新完毕
    } else if (ret < 0) {
        // 解码错误
        break;
    }
    // 处理 frame...
    av_frame_unref(frame);  // 处理完后必须 unref！
}
```

**刷新解码器（处理文件末尾的 B 帧）**：

```c
// 发送 NULL 包触发刷新
avcodec_send_packet(codec_ctx, NULL);

// 继续接收剩余帧
while (avcodec_receive_frame(codec_ctx, frame) == 0) {
    // 处理最后几帧...
    av_frame_unref(frame);
}
```

### 5.2 libavformat — 封装/解封装库

#### 5.2.1 核心数据结构关系

```
AVFormatContext（总控制器）
  ├── AVInputFormat / AVOutputFormat（格式描述，如 mp4、mkv）
  ├── AVIOContext（I/O 上下文，抽象文件/网络读写）
  └── AVStream[]（流数组）
        ├── AVCodecParameters（编解码器参数）
        ├── AVRational time_base（流时间基）
        └── AVDictionary *metadata（流元数据）
```

**AVStream 关键字段**：

```c
typedef struct AVStream {
    int index;                      // 流索引（0, 1, 2...）
    int id;                         // 容器内的流 ID（可能不连续）
    AVCodecParameters *codecpar;    // 编解码器参数（不含运行时状态）

    AVRational time_base;           // 流时间基（★ 重要：每个流可能不同！）
    int64_t start_time;             // 流开始时间（流时间基单位）
    int64_t duration;               // 流时长（流时间基单位）
    int64_t nb_frames;              // 总帧数（估计值，可能为 0）

    AVRational avg_frame_rate;      // 平均帧率（如 {25, 1}）
    AVRational r_frame_rate;        // 真实帧率（可变帧率时与 avg 不同）

    AVDictionary *metadata;         // 流元数据（语言、标题等）
} AVStream;
```

#### 5.2.2 解封装完整流程

```c
/* 参考：doc/examples/demux_decode.c */

AVFormatContext *fmt_ctx = NULL;

// 步骤1：打开输入（支持文件、URL、RTSP 等）
if (avformat_open_input(&fmt_ctx, "input.mp4", NULL, NULL) < 0) {
    // 错误处理
}

// 步骤2：探测流信息（读取部分数据，分析流参数）
// 注意：这会消耗一些数据，对于某些格式必须调用
if (avformat_find_stream_info(fmt_ctx, NULL) < 0) {
    // 错误处理
}

// 步骤3：打印媒体信息（调试用）
av_dump_format(fmt_ctx, 0, "input.mp4", 0);

// 步骤4：找到最佳视频流（推荐使用 av_find_best_stream）
int video_idx = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_VIDEO,
                                     -1, -1, &codec, 0);

// 步骤5：读取数据包循环
AVPacket *pkt = av_packet_alloc();
while (av_read_frame(fmt_ctx, pkt) >= 0) {
    if (pkt->stream_index == video_idx) {
        // 处理视频包...
    }
    av_packet_unref(pkt);  // ★ 必须 unref，否则内存泄漏！
}

// 步骤6：清理
avformat_close_input(&fmt_ctx);
av_packet_free(&pkt);
```

#### 5.2.3 AVIOContext — I/O 抽象层

`AVIOContext` 是 FFmpeg 的 I/O 抽象层，支持：

```c
// 打开本地文件
avio_open(&fmt_ctx->pb, "output.mp4", AVIO_FLAG_WRITE);

// 自定义 I/O（内存缓冲区、加密流等）
unsigned char *buffer = av_malloc(4096);
AVIOContext *avio = avio_alloc_context(
    buffer, 4096,
    1,          // write_flag
    user_data,  // opaque
    read_packet,  // 自定义读函数
    write_packet, // 自定义写函数
    seek          // 自定义 seek 函数
);
fmt_ctx->pb = avio;
```

> **设计洞察**：通过自定义 `AVIOContext`，可以让 FFmpeg 读写任意数据源（内存、加密文件、网络流等），而无需修改上层代码。

---

## 6. ffmpeg 工具的调度器架构

> 这是 FFmpeg 工具（非库）的核心架构，理解它能让你看懂 `fftools/` 下的所有代码。

### 6.1 为什么需要调度器？

在 FFmpeg 7.x 之前，`ffmpeg` 工具使用单线程循环处理所有流。这导致：
- 多路输入时，一路卡顿会阻塞其他路
- 无法充分利用多核 CPU
- 代码耦合严重，难以维护

**新架构（Scheduler）**：每个组件运行在独立线程，通过调度器通信：

```
                    ┌─────────────────────────────────────────┐
                    │              Scheduler（调度器）          │
                    │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐│
输入文件 ──▶ [解封装线程] │      │  │      │  │      │  │      ││
                    │  │ 队列 │  │ 队列 │  │ 队列 │  │ 队列 ││
输入文件 ──▶ [解封装线程] │      │  │      │  │      │  │      ││
                    │  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘│
                    │     │         │          │          │    │
                    │  [解码线程] [解码线程] [滤镜线程] [编码线程]│
                    │     │         │          │          │    │
                    │     └─────────┴──────────┴──────────┘    │
                    │                    │                      │
                    │              [封装线程] ──▶ 输出文件       │
                    └─────────────────────────────────────────┘
```

### 6.2 调度器节点类型

**定义位置**：`fftools/ffmpeg_sched.h`（第 68-76 行）

```c
/* fftools/ffmpeg_sched.h */
enum SchedulerNodeType {
    SCH_NODE_TYPE_NONE = 0,
    SCH_NODE_TYPE_DEMUX,       // 解封装器
    SCH_NODE_TYPE_MUX,         // 封装器
    SCH_NODE_TYPE_DEC,         // 解码器
    SCH_NODE_TYPE_ENC,         // 编码器
    SCH_NODE_TYPE_FILTER_IN,   // 滤镜图输入
    SCH_NODE_TYPE_FILTER_OUT,  // 滤镜图输出
};

// 节点标识符（类型 + 索引）
typedef struct SchedulerNode {
    enum SchedulerNodeType  type;
    unsigned                idx;         // 组件索引
    unsigned                idx_stream;  // 流索引（用于 DEMUX/MUX）
} SchedulerNode;
```

### 6.3 调度器连接模型

```c
/* fftools/ffmpeg_sched.h（第 100-120 行）*/

// 便捷宏：创建节点标识符
#define SCH_DSTREAM(file, stream)   // 解封装器的某个流
#define SCH_MSTREAM(file, stream)   // 封装器的某个流
#define SCH_DEC_IN(decoder)         // 解码器输入
#define SCH_DEC_OUT(decoder, idx)   // 解码器输出
#define SCH_ENC(encoder)            // 编码器
#define SCH_FILTER_IN(fg, input)    // 滤镜图输入
#define SCH_FILTER_OUT(fg, output)  // 滤镜图输出

// 连接两个节点（建立数据流路径）
int sch_connect(Scheduler *sch, SchedulerNode src, SchedulerNode dst);

// 示例：连接解封装器流0 → 解码器0
sch_connect(sch, SCH_DSTREAM(0, 0), SCH_DEC_IN(0));

// 示例：连接解码器0 → 滤镜图0的输入0
sch_connect(sch, SCH_DEC_OUT(0, 0), SCH_FILTER_IN(0, 0));

// 示例：连接滤镜图0的输出0 → 编码器0
sch_connect(sch, SCH_FILTER_OUT(0, 0), SCH_ENC(0));
```

### 6.4 ffmpeg 主程序流程

**定义位置**：`fftools/ffmpeg.c`（`main()` 函数，第 1000-1059 行）

```
main()
  │
  ├── init_dynload()              # 动态加载初始化
  ├── parse_loglevel()            # 解析日志级别
  ├── avdevice_register_all()     # 注册所有设备
  ├── avformat_network_init()     # 初始化网络
  ├── sch_alloc()                 # 创建调度器
  ├── ffmpeg_parse_options()      # 解析命令行，打开所有输入/输出
  │     ├── ifile_open()          # 打开每个输入文件
  │     └── of_open()             # 打开每个输出文件
  │
  └── transcode(sch)              # 开始转码
        ├── print_stream_maps()   # 打印流映射信息
        ├── sch_start(sch)        # 启动所有线程
        │
        └── 主循环：
              while (!sch_wait(sch, stats_period, &ts))
                ├── check_keyboard_interaction()  # 处理键盘输入（q/+/-/c）
                └── print_report()                # 打印进度报告
```

### 6.5 核心数据结构层次

**定义位置**：`fftools/ffmpeg.h`（992 行）

```
InputFile（输入文件）
  └── InputStream[]（输入流）
        ├── AVStream *st
        ├── AVCodecParameters *par
        ├── Decoder *decoder
        └── InputFilter *filters[]  ──▶ FilterGraph（滤镜图）
                                              └── OutputFilter *outputs[]
                                                    └── OutputStream（输出流）
                                                          ├── Encoder *enc
                                                          └── OutputFile（输出文件）
```

**FrameData — 帧附加数据**：

```c
/* fftools/ffmpeg.h（第 430-450 行）*/
// 通过 frame->opaque_ref 附加到每一帧，在整个流水线中传递元数据
typedef struct FrameData {
    int64_t dts_est;            // 解封装器估计的 DTS
    struct {
        uint64_t   frame_num;   // 解码帧序号
        int64_t    pts;         // 解码器输出的 PTS
        AVRational tb;          // 解码器时间基
    } dec;
    AVRational frame_rate_filter; // 滤镜处理后的帧率
    int64_t wallclock[LATENCY_PROBE_NB]; // 各阶段的墙钟时间（用于延迟分析）
} FrameData;
```

---

## 7. 完整转码流程分析

### 7.1 视频解码完整示例

**参考源文件**：`doc/examples/demux_decode.c`（386 行）

```c
#include <libavutil/imgutils.h>
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>

// 解码一个包，并处理所有输出帧
static int decode_packet(AVCodecContext *dec, const AVPacket *pkt,
                          AVFrame *frame, FILE *out_file)
{
    // 1. 发送压缩包（NULL 表示刷新）
    int ret = avcodec_send_packet(dec, pkt);
    if (ret < 0) return ret;

    // 2. 循环接收所有解码帧
    while (ret >= 0) {
        ret = avcodec_receive_frame(dec, frame);
        if (ret == AVERROR_EOF || ret == AVERROR(EAGAIN))
            return 0;  // 正常情况：需要更多输入或已结束
        if (ret < 0) return ret;

        // 3. 处理帧（这里写入 YUV 文件）
        // ★ 注意：必须用 linesize，不能用 width！
        for (int y = 0; y < frame->height; y++)
            fwrite(frame->data[0] + y * frame->linesize[0],
                   1, frame->width, out_file);  // Y 平面
        for (int y = 0; y < frame->height / 2; y++)
            fwrite(frame->data[1] + y * frame->linesize[1],
                   1, frame->width / 2, out_file);  // U 平面
        for (int y = 0; y < frame->height / 2; y++)
            fwrite(frame->data[2] + y * frame->linesize[2],
                   1, frame->width / 2, out_file);  // V 平面

        av_frame_unref(frame);  // ★ 必须 unref！
    }
    return ret;
}

int main(int argc, char *argv[])
{
    AVFormatContext *fmt_ctx = NULL;
    AVCodecContext  *dec_ctx = NULL;
    const AVCodec   *dec     = NULL;
    AVFrame         *frame   = av_frame_alloc();
    AVPacket        *pkt     = av_packet_alloc();
    int video_idx;

    // 1. 打开输入文件
    avformat_open_input(&fmt_ctx, argv[1], NULL, NULL);
    avformat_find_stream_info(fmt_ctx, NULL);

    // 2. 找到最佳视频流并获取解码器
    video_idx = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_VIDEO,
                                     -1, -1, &dec, 0);

    // 3. 分配并初始化解码器上下文
    dec_ctx = avcodec_alloc_context3(dec);
    avcodec_parameters_to_context(dec_ctx, fmt_ctx->streams[video_idx]->codecpar);
    avcodec_open2(dec_ctx, dec, NULL);

    // 4. 解码循环
    while (av_read_frame(fmt_ctx, pkt) >= 0) {
        if (pkt->stream_index == video_idx)
            decode_packet(dec_ctx, pkt, frame, stdout);
        av_packet_unref(pkt);
    }

    // 5. 刷新解码器（处理 B 帧缓冲区中的剩余帧）
    decode_packet(dec_ctx, NULL, frame, stdout);

    // 6. 清理
    av_frame_free(&frame);
    av_packet_free(&pkt);
    avcodec_free_context(&dec_ctx);
    avformat_close_input(&fmt_ctx);
    return 0;
}
```

**编译命令**：

```bash
gcc -o demux_decode demux_decode.c \
    -lavcodec -lavformat -lavutil \
    $(pkg-config --cflags --libs libavcodec libavformat libavutil)
```

### 7.2 视频编码完整示例

**参考源文件**：`doc/examples/encode_video.c`（6.69KB）

```c
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/opt.h>

int encode_video(const char *output_file)
{
    // 1. 查找 H.264 编码器
    const AVCodec *codec = avcodec_find_encoder(AV_CODEC_ID_H264);
    AVCodecContext *enc_ctx = avcodec_alloc_context3(codec);

    // 2. 设置编码参数
    enc_ctx->codec_id   = AV_CODEC_ID_H264;
    enc_ctx->width      = 1920;
    enc_ctx->height     = 1080;
    enc_ctx->time_base  = (AVRational){1, 25};   // 25fps
    enc_ctx->framerate  = (AVRational){25, 1};
    enc_ctx->pix_fmt    = AV_PIX_FMT_YUV420P;
    enc_ctx->bit_rate   = 2000000;               // 2 Mbps
    enc_ctx->gop_size   = 10;                    // 每 10 帧一个关键帧
    enc_ctx->max_b_frames = 2;

    // 3. 设置 H.264 特定参数（通过 AVOption）
    av_opt_set(enc_ctx->priv_data, "preset", "slow", 0);
    av_opt_set(enc_ctx->priv_data, "crf", "23", 0);

    // 4. 打开编码器
    avcodec_open2(enc_ctx, codec, NULL);

    // 5. 创建输出文件
    AVFormatContext *fmt_ctx = NULL;
    avformat_alloc_output_context2(&fmt_ctx, NULL, NULL, output_file);
    AVStream *stream = avformat_new_stream(fmt_ctx, codec);
    stream->time_base = enc_ctx->time_base;
    avcodec_parameters_from_context(stream->codecpar, enc_ctx);

    // 如果格式需要全局头（如 MP4）
    if (fmt_ctx->oformat->flags & AVFMT_GLOBALHEADER)
        enc_ctx->flags |= AV_CODEC_FLAG_GLOBAL_HEADER;

    avio_open(&fmt_ctx->pb, output_file, AVIO_FLAG_WRITE);
    avformat_write_header(fmt_ctx, NULL);

    // 6. 编码循环
    AVFrame *frame = av_frame_alloc();
    frame->format = AV_PIX_FMT_YUV420P;
    frame->width  = enc_ctx->width;
    frame->height = enc_ctx->height;
    av_frame_get_buffer(frame, 0);

    AVPacket *pkt = av_packet_alloc();

    for (int i = 0; i < 250; i++) {  // 编码 250 帧（10 秒）
        // 填充测试图案（实际应用中替换为真实视频数据）
        av_frame_make_writable(frame);
        for (int y = 0; y < frame->height; y++)
            for (int x = 0; x < frame->width; x++)
                frame->data[0][y * frame->linesize[0] + x] = x + y + i * 3;
        frame->pts = i;

        // 发送帧到编码器
        avcodec_send_frame(enc_ctx, frame);

        // 接收编码后的包
        while (avcodec_receive_packet(enc_ctx, pkt) == 0) {
            // 时间戳转换：从编解码器时间基 → 流时间基
            av_packet_rescale_ts(pkt, enc_ctx->time_base, stream->time_base);
            pkt->stream_index = stream->index;
            av_interleaved_write_frame(fmt_ctx, pkt);
            av_packet_unref(pkt);
        }
    }

    // 7. 刷新编码器
    avcodec_send_frame(enc_ctx, NULL);
    while (avcodec_receive_packet(enc_ctx, pkt) == 0) {
        av_packet_rescale_ts(pkt, enc_ctx->time_base, stream->time_base);
        pkt->stream_index = stream->index;
        av_interleaved_write_frame(fmt_ctx, pkt);
        av_packet_unref(pkt);
    }

    // 8. 写文件尾（MP4 的 moov atom 在这里写入）
    av_write_trailer(fmt_ctx);

    // 9. 清理
    av_packet_free(&pkt);
    av_frame_free(&frame);
    avcodec_free_context(&enc_ctx);
    avio_closep(&fmt_ctx->pb);
    avformat_free_context(fmt_ctx);
    return 0;
}
```

### 7.3 流复制（Stream Copy）

流复制是最高效的"转码"方式——直接复制压缩数据，不经过解码/编码：

```bash
# 命令行：将 MP4 重新封装为 MKV（不重新编码）
ffmpeg -i input.mp4 -c copy output.mkv
```

```c
// 代码实现（参考 doc/examples/remux.c）
// 关键：直接复制 AVPacket，只需调整时间戳

while (av_read_frame(in_fmt_ctx, pkt) >= 0) {
    AVStream *in_stream  = in_fmt_ctx->streams[pkt->stream_index];
    AVStream *out_stream = out_fmt_ctx->streams[pkt->stream_index];

    // 时间戳转换（从输入流时间基 → 输出流时间基）
    av_packet_rescale_ts(pkt, in_stream->time_base, out_stream->time_base);
    pkt->pos = -1;  // 重置文件位置

    av_interleaved_write_frame(out_fmt_ctx, pkt);
    av_packet_unref(pkt);
}
```

---

## 8. 滤镜系统深度解析

### 8.1 滤镜图（FilterGraph）架构

```
滤镜图（AVFilterGraph）
  │
  ├── buffersrc（输入源）──▶ [scale] ──▶ [overlay] ──▶ buffersink（输出汇）
  │                                          ▲
  └── buffersrc（第二路输入）────────────────┘

每个滤镜（AVFilterContext）通过 AVFilterLink 连接
```

**核心数据结构**：

```c
/* libavfilter/avfilter.h */

// 滤镜描述（静态，全局唯一）
typedef struct AVFilter {
    const char *name;           // 滤镜名称（如 "scale", "overlay"）
    const char *description;    // 描述
    const AVFilterPad *inputs;  // 输入 pad 描述
    const AVFilterPad *outputs; // 输出 pad 描述
    const AVClass *priv_class;  // 私有选项类
    int flags;                  // AVFILTER_FLAG_*
} AVFilter;

// 滤镜实例（运行时）
typedef struct AVFilterContext {
    const AVFilter *filter;     // 指向滤镜描述
    char *name;                 // 实例名称（如 "scale0"）

    AVFilterLink **inputs;      // 输入链接数组
    unsigned nb_inputs;
    AVFilterLink **outputs;     // 输出链接数组
    unsigned nb_outputs;

    void *priv;                 // 滤镜私有数据（如 ScaleContext）
    struct AVFilterGraph *graph;// 所属滤镜图
} AVFilterContext;

// 滤镜链接（连接两个滤镜）
struct AVFilterLink {
    AVFilterContext *src;       // 源滤镜
    AVFilterPad *srcpad;        // 源 pad
    AVFilterContext *dst;       // 目标滤镜
    AVFilterPad *dstpad;        // 目标 pad

    enum AVMediaType type;      // 媒体类型
    int format;                 // 协商后的格式
    int w, h;                   // 视频：宽高
    int sample_rate;            // 音频：采样率
    AVChannelLayout ch_layout;  // 音频：声道布局
    AVRational time_base;       // 时间基
};
```

### 8.2 使用字符串描述滤镜图

```bash
# 视频滤镜链（串联）
-vf "scale=1280:720,unsharp=5:5:1.0,drawtext=text='Hello':x=10:y=10"

# 复杂滤镜图（并联 + 合并）
-filter_complex "[0:v][1:v]overlay=10:10[out]" -map "[out]"

# 音频滤镜
-af "volume=2.0,aresample=44100,aecho=0.8:0.88:60:0.4"
```

### 8.3 代码中使用滤镜图

**参考源文件**：`doc/examples/decode_filter_video.c`（10.45KB）

```c
// 创建滤镜图
AVFilterGraph *graph = avfilter_graph_alloc();

// 使用 avfilter_graph_parse_ptr 解析滤镜字符串（推荐方式）
AVFilterInOut *inputs  = avfilter_inout_alloc();
AVFilterInOut *outputs = avfilter_inout_alloc();

// 创建 buffersrc（输入源）
char args[512];
snprintf(args, sizeof(args),
    "video_size=%dx%d:pix_fmt=%d:time_base=%d/%d:pixel_aspect=%d/%d",
    dec_ctx->width, dec_ctx->height, dec_ctx->pix_fmt,
    stream->time_base.num, stream->time_base.den,
    dec_ctx->sample_aspect_ratio.num, dec_ctx->sample_aspect_ratio.den);

AVFilterContext *buffersrc_ctx;
avfilter_graph_create_filter(&buffersrc_ctx,
    avfilter_get_by_name("buffer"), "in", args, NULL, graph);

// 创建 buffersink（输出汇）
AVFilterContext *buffersink_ctx;
avfilter_graph_create_filter(&buffersink_ctx,
    avfilter_get_by_name("buffersink"), "out", NULL, NULL, graph);

// 设置输出格式约束
enum AVPixelFormat pix_fmts[] = { AV_PIX_FMT_YUV420P, AV_PIX_FMT_NONE };
av_opt_set_int_list(buffersink_ctx, "pix_fmts", pix_fmts,
                    AV_PIX_FMT_NONE, AV_OPT_SEARCH_CHILDREN);

// 解析滤镜字符串并连接
outputs->name       = av_strdup("in");
outputs->filter_ctx = buffersrc_ctx;
outputs->pad_idx    = 0;
outputs->next       = NULL;

inputs->name        = av_strdup("out");
inputs->filter_ctx  = buffersink_ctx;
inputs->pad_idx     = 0;
inputs->next        = NULL;

avfilter_graph_parse_ptr(graph, "scale=320:240,vflip",
                          &inputs, &outputs, NULL);

// 配置滤镜图（协商格式、分配缓冲区）
avfilter_graph_config(graph, NULL);

// 使用滤镜图处理帧
// 推入帧
av_buffersrc_add_frame_flags(buffersrc_ctx, frame, AV_BUFFERSRC_FLAG_KEEP_REF);

// 拉出处理后的帧
AVFrame *filt_frame = av_frame_alloc();
while (av_buffersink_get_frame(buffersink_ctx, filt_frame) >= 0) {
    // 处理 filt_frame...
    av_frame_unref(filt_frame);
}
av_frame_free(&filt_frame);

// 清理
avfilter_graph_free(&graph);
```

---

## 9. 硬件加速机制

### 9.1 支持的硬件加速 API

| API | 平台 | 典型用途 | 命令行参数 |
|-----|------|---------|-----------|
| **CUDA/NVENC/NVDEC** | NVIDIA GPU | 高性能转码 | `-hwaccel cuda -c:v h264_nvenc` |
| **VAAPI** | Linux（Intel/AMD） | 低功耗转码 | `-hwaccel vaapi` |
| **DXVA2/D3D11VA** | Windows | 硬件解码 | `-hwaccel dxva2` |
| **VideoToolbox** | macOS/iOS | Apple 芯片加速 | `-hwaccel videotoolbox` |
| **MediaCodec** | Android | 移动端加速 | `-hwaccel mediacodec` |
| **QSV** | Intel Quick Sync | Intel 平台转码 | `-hwaccel qsv` |

### 9.2 硬件解码代码实现

**参考源文件**：`doc/examples/hw_decode.c`（264 行）

```c
/* 核心步骤（来自 hw_decode.c） */

// 1. 查找支持硬件加速的解码器配置
for (int i = 0; ; i++) {
    const AVCodecHWConfig *config = avcodec_get_hw_config(decoder, i);
    if (!config) break;  // 不支持该硬件类型
    if (config->methods & AV_CODEC_HW_CONFIG_METHOD_HW_DEVICE_CTX &&
        config->device_type == AV_HWDEVICE_TYPE_CUDA) {
        hw_pix_fmt = config->pix_fmt;  // 记录硬件像素格式（如 AV_PIX_FMT_CUDA）
        break;
    }
}

// 2. 创建硬件设备上下文
AVBufferRef *hw_device_ctx = NULL;
av_hwdevice_ctx_create(&hw_device_ctx, AV_HWDEVICE_TYPE_CUDA, NULL, NULL, 0);

// 3. 将硬件设备上下文绑定到解码器
decoder_ctx->hw_device_ctx = av_buffer_ref(hw_device_ctx);

// 4. 设置格式协商回调（告诉解码器优先使用硬件格式）
decoder_ctx->get_format = get_hw_format;  // 自定义回调

// get_hw_format 实现：
static enum AVPixelFormat get_hw_format(AVCodecContext *ctx,
                                         const enum AVPixelFormat *pix_fmts)
{
    for (const enum AVPixelFormat *p = pix_fmts; *p != -1; p++)
        if (*p == hw_pix_fmt)
            return *p;  // 返回硬件格式
    return AV_PIX_FMT_NONE;  // 回退到软件解码
}

// 5. 解码后，将硬件帧传输到 CPU 内存
if (frame->format == hw_pix_fmt) {
    AVFrame *sw_frame = av_frame_alloc();
    av_hwframe_transfer_data(sw_frame, frame, 0);  // GPU → CPU
    // 现在 sw_frame 包含 CPU 可访问的数据
    av_frame_free(&sw_frame);
}
```

### 9.3 硬件帧上下文（AVHWFramesContext）

对于零拷贝硬件处理（解码 → 滤镜 → 编码全程在 GPU 上）：

```c
// 创建硬件帧上下文（描述 GPU 帧池）
AVBufferRef *hw_frames_ref = av_hwframe_ctx_alloc(hw_device_ctx);
AVHWFramesContext *frames_ctx = (AVHWFramesContext*)hw_frames_ref->data;
frames_ctx->format    = AV_PIX_FMT_CUDA;      // 硬件格式
frames_ctx->sw_format = AV_PIX_FMT_NV12;      // 软件格式（GPU 内部存储）
frames_ctx->width     = width;
frames_ctx->height    = height;
frames_ctx->initial_pool_size = 20;            // 预分配 20 帧的 GPU 内存池
av_hwframe_ctx_init(hw_frames_ref);

// 将帧上下文绑定到编码器（零拷贝编码）
enc_ctx->hw_frames_ctx = av_buffer_ref(hw_frames_ref);
```

---

## 10. 自定义滤镜开发实战

**参考文档**：`doc/writing_filters.txt`（422 行）

### 10.1 开发步骤

```bash
# 1. 复制一个类似的滤镜作为模板
sed 's/edgedetect/myfilter/g;s/EdgeDetect/MyFilter/g' \
    libavfilter/vf_edgedetect.c > libavfilter/vf_myfilter.c

# 2. 注册滤镜
# 编辑 libavfilter/allfilters.c，添加：
# extern const AVFilter ff_vf_myfilter;

# 3. 添加编译规则
# 编辑 libavfilter/Makefile，添加：
# OBJS-$(CONFIG_MYFILTER_FILTER) += vf_myfilter.o

# 4. 重新配置和编译
./configure ...
make -j8
```

### 10.2 滤镜代码结构

```c
/* libavfilter/vf_myfilter.c */
#include "avfilter.h"
#include "formats.h"
#include "video.h"
#include "libavutil/opt.h"

// 1. 私有上下文（存储滤镜状态和用户选项）
typedef struct MyFilterContext {
    const AVClass *class;   // ★ 必须是第一个字段！
    int intensity;          // 用户选项：强度
    float threshold;        // 用户选项：阈值
    // 内部状态...
} MyFilterContext;

// 2. 选项定义
static const AVOption myfilter_options[] = {
    { "intensity", "set intensity", OFFSET(intensity),
      AV_OPT_TYPE_INT, {.i64=1}, 0, 10, FLAGS },
    { "threshold", "set threshold", OFFSET(threshold),
      AV_OPT_TYPE_FLOAT, {.dbl=0.5}, 0.0, 1.0, FLAGS },
    { NULL }
};

// 3. 格式协商（声明支持的像素格式）
static int query_formats(AVFilterContext *ctx)
{
    static const enum AVPixelFormat pix_fmts[] = {
        AV_PIX_FMT_YUV420P,
        AV_PIX_FMT_YUV422P,
        AV_PIX_FMT_NONE
    };
    return ff_set_common_formats(ctx, ff_make_format_list(pix_fmts));
}

// 4. 初始化（用户选项已填充，但还不知道输入格式）
static int init(AVFilterContext *ctx)
{
    MyFilterContext *s = ctx->priv;
    // 验证选项、预分配资源...
    return 0;
}

// 5. 核心处理函数
static int filter_frame(AVFilterLink *inlink, AVFrame *in)
{
    AVFilterContext *ctx = inlink->dst;
    MyFilterContext *s = ctx->priv;
    AVFilterLink *outlink = ctx->outputs[0];

    // 方案A：原地修改（如果帧可写）
    if (av_frame_is_writable(in)) {
        // 直接修改 in->data[...]
        return ff_filter_frame(outlink, in);
    }

    // 方案B：分配新帧（如果需要读取原始数据同时写入新数据）
    AVFrame *out = ff_get_video_buffer(outlink, outlink->w, outlink->h);
    if (!out) {
        av_frame_free(&in);
        return AVERROR(ENOMEM);
    }
    av_frame_copy_props(out, in);  // 复制时间戳、元数据等

    // 处理像素数据
    for (int plane = 0; plane < 3; plane++) {
        int h = plane == 0 ? in->height : in->height / 2;
        int w = plane == 0 ? in->width  : in->width  / 2;
        for (int y = 0; y < h; y++) {
            uint8_t *src = in->data[plane]  + y * in->linesize[plane];
            uint8_t *dst = out->data[plane] + y * out->linesize[plane];
            for (int x = 0; x < w; x++) {
                // 你的处理逻辑
                dst[x] = FFMIN(src[x] * s->intensity, 255);
            }
        }
    }

    av_frame_free(&in);
    return ff_filter_frame(outlink, out);
}

// 6. 清理
static void uninit(AVFilterContext *ctx)
{
    MyFilterContext *s = ctx->priv;
    // 释放在 init 中分配的资源
}

// 7. Pad 定义
static const AVFilterPad myfilter_inputs[] = {
    {
        .name         = "default",
        .type         = AVMEDIA_TYPE_VIDEO,
        .filter_frame = filter_frame,
    }
};

// 8. 滤镜注册
AVFILTER_DEFINE_CLASS(myfilter);

const AVFilter ff_vf_myfilter = {
    .name          = "myfilter",
    .description   = NULL_IF_CONFIG_SMALL("My custom video filter."),
    .priv_size     = sizeof(MyFilterContext),
    .priv_class    = &myfilter_class,
    .init          = init,
    .uninit        = uninit,
    FILTER_INPUTS(myfilter_inputs),
    FILTER_OUTPUTS(ff_video_default_filterpad),
    FILTER_QUERY_FORMATS(query_formats),
    .flags         = AVFILTER_FLAG_SUPPORT_TIMELINE_GENERIC,
};
```

### 10.3 切片多线程（Slice Threading）

对于逐行处理的滤镜，可以轻松添加多线程支持：

```c
// 线程数据结构
typedef struct ThreadData {
    AVFrame *in, *out;
} ThreadData;

// 切片处理函数（每个线程处理一段行）
static int filter_slice(AVFilterContext *ctx, void *arg,
                         int jobnr, int nb_jobs)
{
    ThreadData *td = arg;
    MyFilterContext *s = ctx->priv;

    // 计算本线程负责的行范围
    int slice_start = (td->in->height *  jobnr   ) / nb_jobs;
    int slice_end   = (td->in->height * (jobnr+1)) / nb_jobs;

    for (int y = slice_start; y < slice_end; y++) {
        uint8_t *src = td->in->data[0]  + y * td->in->linesize[0];
        uint8_t *dst = td->out->data[0] + y * td->out->linesize[0];
        // 处理这一行...
    }
    return 0;
}

// 在 filter_frame 中调用多线程
static int filter_frame(AVFilterLink *inlink, AVFrame *in)
{
    AVFilterContext *ctx = inlink->dst;
    AVFrame *out = ff_get_video_buffer(ctx->outputs[0], in->width, in->height);
    av_frame_copy_props(out, in);

    ThreadData td = { .in = in, .out = out };
    // 分发到多个线程
    ff_filter_execute(ctx, filter_slice, &td, NULL,
                      FFMIN(in->height, ff_filter_get_nb_threads(ctx)));

    av_frame_free(&in);
    return ff_filter_frame(ctx->outputs[0], out);
}

// 在 AVFilter 定义中添加标志
.flags = AVFILTER_FLAG_SUPPORT_TIMELINE_GENERIC | AVFILTER_FLAG_SLICE_THREADS,
```

---

## 11. 调试与诊断

### 11.1 调试环境搭建

#### 方案一：GDB 调试（Linux/macOS）

```bash
# 1. 编译 Debug 版本
./configure \
    --enable-debug=3 \
    --disable-optimizations \
    --disable-stripping \
    --enable-gpl \
    --prefix=/usr/local/ffmpeg-debug
make -j8
make install

# 2. GDB 调试
gdb --args ./ffmpeg -i input.mp4 output.mp4

# GDB 常用命令
(gdb) break avcodec_send_packet    # 在函数入口设断点
(gdb) break avfilter.c:123         # 在文件行号设断点
(gdb) run                          # 运行
(gdb) bt                           # 查看调用栈
(gdb) p frame->pts                 # 打印变量
(gdb) p *codec_ctx                 # 打印结构体
(gdb) watch frame->format          # 监视变量变化
```

#### 方案二：VS Code 调试配置

创建 `.vscode/launch.json`：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug ffmpeg",
            "type": "cppdbg",
            "request": "launch",
            "program": "${workspaceFolder}/ffmpeg",
            "args": ["-i", "input.mp4", "-vf", "scale=640:480", "output.mp4"],
            "stopAtEntry": false,
            "cwd": "${workspaceFolder}",
            "environment": [],
            "externalConsole": false,
            "MIMode": "gdb",
            "setupCommands": [
                {
                    "description": "Enable pretty-printing",
                    "text": "-enable-pretty-printing",
                    "ignoreFailures": true
                }
            ]
        }
    ]
}
```

### 11.2 日志系统

```c
// 日志级别（从高到低）
AV_LOG_QUIET   = -8   // 完全静默
AV_LOG_PANIC   = 0    // 致命错误
AV_LOG_FATAL   = 8    // 严重错误
AV_LOG_ERROR   = 16   // 错误
AV_LOG_WARNING = 24   // 警告
AV_LOG_INFO    = 32   // 信息（默认）
AV_LOG_VERBOSE = 40   // 详细
AV_LOG_DEBUG   = 48   // 调试
AV_LOG_TRACE   = 56   // 追踪（最详细）
```

**命令行控制日志级别**：

```bash
# 显示详细日志
ffmpeg -loglevel verbose -i input.mp4 output.mp4

# 显示调试信息（非常详细）
ffmpeg -loglevel debug -i input.mp4 output.mp4

# 只显示错误
ffmpeg -loglevel error -i input.mp4 output.mp4
```

**代码中设置日志级别**：

```c
// 设置全局日志级别
av_log_set_level(AV_LOG_DEBUG);

// 自定义日志回调
av_log_set_callback(my_log_callback);

static void my_log_callback(void *avcl, int level, const char *fmt, va_list vl)
{
    if (level <= AV_LOG_WARNING) {
        // 只处理警告及以上级别
        vfprintf(stderr, fmt, vl);
    }
}
```

### 11.3 调试时间戳问题

```bash
# 打印每个包的时间戳（调试 PTS/DTS 问题）
ffmpeg -debug_ts -i input.mp4 -f null -

# 输出示例：
# demuxer -> ist_index:0 type:video pkt_pts:0 pkt_pts_time:0 pkt_dts:0 ...
# decoder -> ist_index:0 type:video frame_pts:0 frame_pts_time:0 ...
```

```c
// 代码中打印时间戳
av_log(NULL, AV_LOG_DEBUG,
       "pts=%s pts_time=%s dts=%s dts_time=%s duration=%s\n",
       av_ts2str(pkt->pts),
       av_ts2timestr(pkt->pts, &stream->time_base),
       av_ts2str(pkt->dts),
       av_ts2timestr(pkt->dts, &stream->time_base),
       av_ts2str(pkt->duration));
```

### 11.4 常用诊断命令

```bash
# 查看文件详细信息
ffprobe -v quiet -print_format json -show_streams -show_format input.mp4

# 查看所有支持的编解码器
ffmpeg -codecs | grep -i h264

# 查看所有支持的滤镜
ffmpeg -filters | grep scale

# 查看编解码器详细信息
ffmpeg -h encoder=libx264

# 查看滤镜详细信息
ffmpeg -h filter=scale

# 性能基准测试
ffmpeg -benchmark -i input.mp4 -f null -

# 查看硬件加速设备
ffmpeg -hwaccels
```

### 11.5 关键观测点（断点位置）

| 观测目标 | 推荐断点位置 | 观察变量 |
|---------|------------|---------|
| 解码输出帧 | `avcodec_receive_frame()` 返回后 | `frame->pts`, `frame->format`, `frame->width` |
| 编码输出包 | `avcodec_receive_packet()` 返回后 | `pkt->pts`, `pkt->dts`, `pkt->size`, `pkt->flags` |
| 滤镜处理 | `filter_frame()` 入口 | `in->pts`, `in->format` |
| 时间戳异常 | `av_rescale_q()` 调用处 | 输入输出时间基和时间戳值 |
| 内存泄漏 | `av_frame_unref()` / `av_packet_unref()` | 确认每次 receive 后都有 unref |

---

## 12. 设计洞察汇总

### 12.1 架构设计亮点

**1. 引用计数 + 写时复制**

```
问题：多个滤镜共享同一帧数据时，如何避免不必要的内存复制？
解决：AVBufferRef 引用计数 + av_frame_make_writable() 写时复制
效果：零拷贝数据传递，只在真正需要修改时才复制
```

**2. 推模型解码 API（send/receive）**

```
问题：B 帧导致解码顺序和显示顺序不同，如何优雅处理？
解决：send_packet 和 receive_frame 解耦，解码器内部管理重排序缓冲区
效果：调用者无需关心 B 帧细节，API 更简洁
```

**3. 调度器 DAG 架构**

```
问题：多路输入/输出时，如何避免一路卡顿阻塞其他路？
解决：每个组件独立线程 + 调度器统一管理 + 线程队列缓冲
效果：充分利用多核，各组件解耦，延迟可控
```

**4. AVOption 统一选项系统**

```
问题：数百个编解码器各有不同参数，如何统一管理？
解决：AVOption 系统，通过字符串 key-value 设置任意参数
效果：命令行 -x264opts、代码中 av_opt_set() 统一接口
```

### 12.2 性能优化技巧

| 技巧 | 实现方式 | 效果 |
|------|---------|------|
| SIMD 加速 | `libavutil/cpu.h` 检测 CPU 特性，汇编实现热点函数 | 像素处理速度提升 4-16x |
| 内存对齐 | `av_malloc()` 保证 16/32 字节对齐 | SIMD 指令效率最大化 |
| 缓冲区池 | `AVBufferPool` 复用已分配内存 | 减少 malloc/free 开销 |
| 多线程解码 | `FF_THREAD_FRAME` / `FF_THREAD_SLICE` | 解码速度提升 2-8x |
| 硬件加速 | `AVHWFramesContext` 零拷贝 GPU 处理 | 转码速度提升 10-50x |

### 12.3 关键设计决策表

| 决策 | 选择 | 代价 | 收益 |
|------|------|------|------|
| 时间戳精度 | 有理数（AVRational）而非浮点数 | 需要显式转换 | 精确表示任意帧率 |
| 内存管理 | 引用计数而非 GC | 需要手动 ref/unref | 可预测的内存释放时机 |
| 解码 API | 推模型（send/receive）而非回调 | 状态机复杂 | 支持 B 帧、多线程 |
| 滤镜连接 | 字符串描述而非代码 | 解析开销 | 运行时动态配置 |
| 多线程 | 调度器 + 线程队列而非共享状态 | 实现复杂 | 各组件完全解耦 |

### 12.4 可迁移的设计原则

1. **引用计数 + 写时复制**：适用于任何需要共享大块数据的场景
2. **有向无环图（DAG）处理管线**：适用于多阶段数据处理
3. **推模型 API**：适用于输入输出不一一对应的场景（如压缩/解压缩）
4. **统一选项系统（AVOption）**：适用于有大量可配置参数的组件
5. **调度器模式**：适用于多线程流水线，避免组件间直接通信

---

## 13. 学习路径建议

### 13.1 初学者路径（0-3 个月）

**第 1 个月：命令行工具**
- 安装 FFmpeg，学习 `ffmpeg`、`ffplay`、`ffprobe` 命令
- 理解基本概念：容器、编解码器、帧率、比特率、采样率
- 完成 10 个常用转码命令练习

**第 2 个月：基础 API**
- 阅读 `libavutil/avutil.h`、`libavutil/frame.h`
- 运行并理解 `doc/examples/demux_decode.c`
- 编写第一个解码程序（保存 YUV 文件）

**第 3 个月：编码和封装**
- 阅读 `libavcodec/avcodec.h`、`libavformat/avformat.h`
- 运行并理解 `doc/examples/encode_video.c`
- 完成一个简单的转码程序

**初学者检查清单**：
- [ ] 能使用 ffmpeg 命令行进行格式转换
- [ ] 理解 `AVPacket`（压缩数据）和 `AVFrame`（原始数据）的区别
- [ ] 理解 PTS/DTS 和时间基的概念
- [ ] 能编写简单的解码程序
- [ ] 知道 `av_frame_unref()` 和 `av_packet_unref()` 的重要性

### 13.2 中级开发者路径（3-12 个月）

**第 4-6 个月：深入核心**
- 深入阅读 `fftools/ffmpeg.h`，理解 `InputFile`、`OutputStream` 等结构
- 理解 `AVBufferRef` 引用计数机制
- 学习滤镜系统，运行 `doc/examples/decode_filter_video.c`

**第 7-9 个月：实践项目**
- 开发一个自定义滤镜（参考 `doc/writing_filters.txt`）
- 实现硬件加速解码（参考 `doc/examples/hw_decode.c`）
- 开发一个简单的视频播放器

**第 10-12 个月：架构理解**
- 深入阅读 `fftools/ffmpeg_sched.h`，理解调度器架构
- 分析 `fftools/ffmpeg_filter.c`（最复杂的模块）
- 理解多线程同步机制（`sync_queue.c`、`thread_queue.c`）

**中级检查清单**：
- [ ] 能开发自定义滤镜
- [ ] 理解引用计数和写时复制
- [ ] 能实现硬件加速解码
- [ ] 理解调度器架构
- [ ] 能调试时间戳问题

### 13.3 高级开发者路径（1 年以上）

**深入方向一：编解码器优化**
- 研究具体编解码器实现（`libavcodec/h264dec.c`、`libavcodec/aacenc.c`）
- 学习 SIMD 优化（`libavcodec/x86/`）
- 研究码率控制算法

**深入方向二：格式支持**
- 研究容器格式解析（`libavformat/mov.c`、`libavformat/matroska.c`）
- 实现自定义输入/输出格式
- 研究流媒体协议（RTSP、HLS、DASH）

**深入方向三：贡献社区**
- 订阅 `ffmpeg-devel` 邮件列表
- 提交 bug 修复或新功能
- 参与代码审查

**高级检查清单**：
- [ ] 能优化 FFmpeg 性能（SIMD、多线程）
- [ ] 理解硬件加速的完整实现
- [ ] 能修复 FFmpeg 的 bug
- [ ] 能贡献代码到 FFmpeg 社区

### 13.4 推荐资源

| 资源 | 类型 | 适合阶段 |
|------|------|---------|
| [FFmpeg 官方文档](https://ffmpeg.org/documentation.html) | 文档 | 所有阶段 |
| [FFmpeg 官方示例](https://github.com/FFmpeg/FFmpeg/tree/master/doc/examples) | 代码 | 入门 |
| [雷霄骅的 CSDN 博客](https://blog.csdn.net/leixiaohua1020) | 博客（中文） | 入门/中级 |
| [FFmpeg 源码](https://github.com/FFmpeg/FFmpeg) | 源码 | 所有阶段 |
| [FFmpeg Wiki](https://trac.ffmpeg.org/wiki) | Wiki | 所有阶段 |
| [《FFmpeg 从入门到精通》](https://book.douban.com/subject/30178432/) | 书籍（中文） | 入门/中级 |
| [FFmpeg 开发者邮件列表](https://ffmpeg.org/contact.html#MailingLists) | 社区 | 高级 |

---

## 14. 源码文件索引

### 14.1 关键函数定位表

| 函数/结构 | 文件 | 说明 |
|---------|------|------|
| `AVFrame` 定义 | `libavutil/frame.h:~700` | 原始帧数据结构 |
| `AVPacket` 定义 | `libavcodec/packet.h:~350` | 压缩包数据结构 |
| `AVBufferRef` 定义 | `libavutil/buffer.h:~75` | 引用计数缓冲区 |
| `AVCodecContext` 定义 | `libavcodec/avcodec.h:~400` | 编解码器上下文 |
| `AVFormatContext` 定义 | `libavformat/avformat.h:~1200` | 封装/解封装上下文 |
| `AVFilterGraph` 定义 | `libavfilter/avfilter.h:~900` | 滤镜图 |
| `avcodec_send_packet()` | `libavcodec/decode.c` | 推入压缩包 |
| `avcodec_receive_frame()` | `libavcodec/decode.c` | 拉出解码帧 |
| `avformat_open_input()` | `libavformat/demux.c` | 打开输入文件 |
| `av_read_frame()` | `libavformat/demux.c` | 读取数据包 |
| `avfilter_graph_parse_ptr()` | `libavfilter/graphparser.c` | 解析滤镜字符串 |
| `sch_alloc()` | `fftools/ffmpeg_sched.c` | 创建调度器 |
| `sch_connect()` | `fftools/ffmpeg_sched.c` | 连接调度器节点 |
| `transcode()` | `fftools/ffmpeg.c:~950` | 转码主循环 |
| `main()` | `fftools/ffmpeg.c:~1000` | ffmpeg 程序入口 |

### 14.2 核心头文件速查

| 头文件 | 大小 | 核心内容 |
|--------|------|---------|
| `libavutil/avutil.h` | ~5KB | 基础类型、时间常量、版本信息 |
| `libavutil/frame.h` | 43KB | AVFrame、AVFrameSideData |
| `libavutil/buffer.h` | 12KB | AVBufferRef、AVBufferPool |
| `libavutil/rational.h` | ~5KB | AVRational、时间戳转换 |
| `libavutil/opt.h` | ~30KB | AVOption 选项系统 |
| `libavcodec/avcodec.h` | ~110KB | AVCodec、AVCodecContext、编解码 API |
| `libavcodec/packet.h` | ~20KB | AVPacket |
| `libavformat/avformat.h` | ~122KB | AVFormatContext、AVStream、封装 API |
| `libavfilter/avfilter.h` | 46KB | AVFilter、AVFilterGraph、滤镜 API |
| `fftools/ffmpeg.h` | 28KB | ffmpeg 工具内部数据结构 |
| `fftools/ffmpeg_sched.h` | 22KB | 调度器 API |

---

## 15. 附录：常见陷阱与最佳实践

### 15.1 内存管理陷阱

**陷阱1：忘记 unref**

```c
// ❌ 错误：内存泄漏
while (av_read_frame(fmt_ctx, pkt) >= 0) {
    process(pkt);
    // 忘记 av_packet_unref(pkt)！
}

// ✅ 正确
while (av_read_frame(fmt_ctx, pkt) >= 0) {
    process(pkt);
    av_packet_unref(pkt);  // ★ 必须！
}
```

**陷阱2：混淆 free 和 unref**

```c
// ❌ 错误：应该用 unref 而不是 free
AVFrame *frame = av_frame_alloc();
// ... 使用 frame ...
av_frame_free(&frame);   // 这是对的，释放 AVFrame 结构体

// ❌ 错误：在循环中用 free 而不是 unref
while (avcodec_receive_frame(ctx, frame) == 0) {
    process(frame);
    av_frame_free(&frame);  // 错！frame 指针变为 NULL，下次循环崩溃
}

// ✅ 正确：循环中用 unref
while (avcodec_receive_frame(ctx, frame) == 0) {
    process(frame);
    av_frame_unref(frame);  // 释放数据，但保留 AVFrame 结构体
}
av_frame_free(&frame);      // 循环结束后释放结构体
```

**陷阱3：直接修改只读帧**

```c
// ❌ 错误：帧可能是只读的（引用计数 > 1）
frame->data[0][0] = 255;  // 可能崩溃或数据损坏！

// ✅ 正确：先确保可写
av_frame_make_writable(frame);
frame->data[0][0] = 255;  // 安全
```

### 15.2 时间戳陷阱

**陷阱4：忘记时间基转换**

```c
// ❌ 错误：直接比较不同时间基的时间戳
if (frame->pts > pkt->pts) { ... }  // 可能是错的！

// ✅ 正确：转换到同一时间基再比较
int64_t frame_pts_us = av_rescale_q(frame->pts,
                                     codec_ctx->time_base,
                                     AV_TIME_BASE_Q);
int64_t pkt_pts_us   = av_rescale_q(pkt->pts,
                                     stream->time_base,
                                     AV_TIME_BASE_Q);
if (frame_pts_us > pkt_pts_us) { ... }
```

**陷阱5：编码时忘记时间戳转换**

```c
// ❌ 错误：直接写入，时间戳单位不对
av_interleaved_write_frame(fmt_ctx, pkt);

// ✅ 正确：先转换时间戳
av_packet_rescale_ts(pkt, enc_ctx->time_base, stream->time_base);
pkt->stream_index = stream->index;
av_interleaved_write_frame(fmt_ctx, pkt);
```

### 15.3 像素数据陷阱

**陷阱6：用 width 而不是 linesize 遍历像素**

```c
// ❌ 错误：linesize 可能大于 width（内存对齐填充）
for (int y = 0; y < frame->height; y++) {
    uint8_t *row = frame->data[0] + y * frame->width;  // 错！
    // ...
}

// ✅ 正确：使用 linesize
for (int y = 0; y < frame->height; y++) {
    uint8_t *row = frame->data[0] + y * frame->linesize[0];  // 正确
    // ...
}
```

### 15.4 编解码器陷阱

**陷阱7：忘记刷新编解码器**

```c
// ❌ 错误：文件末尾的 B 帧丢失
while (av_read_frame(fmt_ctx, pkt) >= 0) {
    avcodec_send_packet(dec_ctx, pkt);
    while (avcodec_receive_frame(dec_ctx, frame) == 0) {
        process(frame);
        av_frame_unref(frame);
    }
    av_packet_unref(pkt);
}
// 结束，但 B 帧缓冲区中还有帧！

// ✅ 正确：发送 NULL 包刷新
avcodec_send_packet(dec_ctx, NULL);  // 触发刷新
while (avcodec_receive_frame(dec_ctx, frame) == 0) {
    process(frame);
    av_frame_unref(frame);
}
```

**陷阱8：编码器参数设置顺序错误**

```c
// ❌ 错误：在 avcodec_open2 之后设置参数（无效）
avcodec_open2(enc_ctx, codec, NULL);
enc_ctx->bit_rate = 2000000;  // 无效！

// ✅ 正确：在 avcodec_open2 之前设置所有参数
enc_ctx->bit_rate = 2000000;
enc_ctx->width    = 1920;
enc_ctx->height   = 1080;
avcodec_open2(enc_ctx, codec, NULL);  // 然后打开
```

### 15.5 术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| 编解码器 | Codec | 编码器（Encoder）和解码器（Decoder）的统称 |
| 容器/封装格式 | Container | 存储多个流的文件格式（MP4、MKV、AVI 等） |
| 帧 | Frame | 视频的一幅图像（AVFrame）或音频的一段采样 |
| 数据包 | Packet | 压缩后的数据单元（AVPacket） |
| 像素格式 | Pixel Format | 图像像素的存储方式（YUV420P、RGB24 等） |
| 采样格式 | Sample Format | 音频采样的存储方式（S16、FLTP 等） |
| 显示时间戳 | PTS | Presentation Timestamp，播放器按此顺序显示 |
| 解码时间戳 | DTS | Decoding Timestamp，解码器按此顺序解码 |
| 时间基 | Time Base | 时间戳的单位（如 1/90000 秒） |
| 关键帧 | Keyframe / I-Frame | 可以独立解码的帧，不依赖其他帧 |
| 预测帧 | P-Frame | 参考前面的帧进行预测编码 |
| 双向预测帧 | B-Frame | 参考前后帧进行预测编码，压缩率最高 |
| GOP | Group of Pictures | 从一个关键帧到下一个关键帧之间的帧组 |
| 比特率 | Bitrate | 每秒的数据量（bps、kbps、Mbps） |
| 帧率 | Framerate | 每秒的视频帧数（fps） |
| 采样率 | Sample Rate | 每秒的音频采样数（Hz，如 44100Hz） |
| 声道布局 | Channel Layout | 音频声道的排列方式（立体声、5.1 声道等） |
| 滤镜图 | Filter Graph | 由多个滤镜连接而成的处理管线 |
| 流复制 | Stream Copy | 不重新编码，直接复制压缩数据 |
| 硬件加速 | Hardware Acceleration | 使用 GPU/专用芯片进行编解码 |
| 引用计数 | Reference Counting | 通过计数管理共享内存的生命周期 |
| 写时复制 | Copy-on-Write | 只在需要修改时才复制数据 |

---

## 16. 附录：插件开发实战指南

> FFmpeg 的强大之处在于其高度可扩展的插件架构。本章覆盖三类最常见的插件开发：
> **自定义解封装器（Demuxer）**、**自定义封装器（Muxer）**、**自定义编解码器（Codec）**。
> 每类插件都有完整的代码骨架和注册流程。

### 16.1 FFmpeg 插件体系概览

```
FFmpeg 插件类型
  │
  ├── 格式插件（libavformat）
  │     ├── 解封装器（Demuxer）── FFInputFormat  ── 读取/解析容器格式
  │     └── 封装器（Muxer）──── FFOutputFormat ── 写入/生成容器格式
  │
  ├── 编解码器插件（libavcodec）
  │     ├── 解码器（Decoder）── FFCodec ── 压缩数据 → 原始帧
  │     └── 编码器（Encoder）── FFCodec ── 原始帧 → 压缩数据
  │
  └── 滤镜插件（libavfilter）
        ├── 视频滤镜（vf_*.c）── AVFilter ── 视频帧处理
        └── 音频滤镜（af_*.c）── AVFilter ── 音频帧处理
```

**插件注册流程**（以解封装器为例）：

```
1. 在 libavformat/myformat.c 中定义 FFInputFormat ff_myformat_demuxer
2. 在 libavformat/allformats.c 中添加 extern 声明
3. 在 libavformat/Makefile 中添加编译规则
4. 重新 ./configure && make
```

> **注意**：FFmpeg 7.x 使用内部结构 `FFInputFormat`/`FFOutputFormat`/`FFCodec`（含函数指针），
> 而公开 API 头文件中暴露的是 `AVInputFormat`/`AVOutputFormat`/`AVCodec`（只含公开字段）。
> 内部结构的第一个字段就是对应的公开结构体，因此可以安全地相互转换。

---

### 16.2 开发自定义解封装器（Demuxer）

**目标**：让 FFmpeg 能够读取一种自定义的二进制媒体格式。

#### 16.2.1 自定义格式协议设计

本例实现一个简单的自定义格式 `myformat`，文件扩展名 `.myfmt`，格式如下：

```
文件结构：
┌─────────────────────────────────────────────────────┐
│  Magic（4字节）：0x4D 0x59 0x46 0x4D（"MYFM"）       │
│  版本（1字节）：0x01                                  │
│  视频宽度（2字节，大端）                               │
│  视频高度（2字节，大端）                               │
│  帧率分子（2字节，大端）                               │
│  帧率分母（2字节，大端）                               │
├─────────────────────────────────────────────────────┤
│  数据块循环：                                         │
│    块类型（1字节）：0x01=视频帧，0x02=音频帧           │
│    块大小（4字节，大端）                               │
│    块数据（块大小字节）                                │
└─────────────────────────────────────────────────────┘
```

#### 16.2.2 解封装器完整实现

**文件路径**：`libavformat/myformatdec.c`

```c
/*
 * MyFormat demuxer
 * 自定义格式解封装器示例
 */
#include "libavutil/intreadwrite.h"  // AV_RB16, AV_RB32 等大端读取宏
#include "libavutil/avassert.h"
#include "avformat.h"
#include "demux.h"                   // FFInputFormat 定义
#include "internal.h"

// 魔数定义
#define MYFMT_MAGIC     0x4D59464D   // "MYFM"
#define MYFMT_HDR_SIZE  13           // 文件头总大小（字节）

// 私有上下文（存储解封装器运行时状态）
typedef struct MyFormatContext {
    int video_stream_idx;   // 视频流索引
    int audio_stream_idx;   // 音频流索引（本例暂不使用）
    int width;
    int height;
    AVRational framerate;
} MyFormatContext;

// ─────────────────────────────────────────────
// 步骤1：格式探测（probe）
// FFmpeg 在打开文件前会调用此函数，判断文件是否属于本格式
// 返回值：0-100，越高表示越确定（AVPROBE_SCORE_MAX=100）
// ─────────────────────────────────────────────
static int myformat_probe(const AVProbeData *p)
{
    // 检查文件头魔数
    if (p->buf_size < 4)
        return 0;
    if (AV_RB32(p->buf) == MYFMT_MAGIC)
        return AVPROBE_SCORE_MAX;   // 100分：完全确定
    return 0;
}

// ─────────────────────────────────────────────
// 步骤2：读取文件头（read_header）
// 解析格式头，创建流（AVStream），设置流参数
// ─────────────────────────────────────────────
static int myformat_read_header(AVFormatContext *s)
{
    MyFormatContext *mctx = s->priv_data;  // 私有上下文（已由框架分配）
    AVIOContext *pb = s->pb;               // I/O 上下文
    AVStream *st;
    uint32_t magic;
    uint8_t  version;

    // 读取并验证魔数
    magic = avio_rb32(pb);  // 读取 4 字节大端整数
    if (magic != MYFMT_MAGIC) {
        av_log(s, AV_LOG_ERROR, "Invalid magic number: 0x%08X\n", magic);
        return AVERROR_INVALIDDATA;
    }

    // 读取版本
    version = avio_r8(pb);
    if (version != 1) {
        av_log(s, AV_LOG_ERROR, "Unsupported version: %d\n", version);
        return AVERROR_PATCHWELCOME;
    }

    // 读取视频参数
    mctx->width          = avio_rb16(pb);  // 宽度
    mctx->height         = avio_rb16(pb);  // 高度
    mctx->framerate.num  = avio_rb16(pb);  // 帧率分子
    mctx->framerate.den  = avio_rb16(pb);  // 帧率分母

    if (mctx->width <= 0 || mctx->height <= 0 ||
        mctx->framerate.num <= 0 || mctx->framerate.den <= 0) {
        av_log(s, AV_LOG_ERROR, "Invalid stream parameters\n");
        return AVERROR_INVALIDDATA;
    }

    // 创建视频流
    st = avformat_new_stream(s, NULL);  // 创建新流（NULL=不指定编解码器）
    if (!st)
        return AVERROR(ENOMEM);

    mctx->video_stream_idx = st->index;

    // 设置流参数
    st->codecpar->codec_type = AVMEDIA_TYPE_VIDEO;
    st->codecpar->codec_id   = AV_CODEC_ID_RAWVIDEO;  // 原始视频（实际项目中替换为真实编解码器）
    st->codecpar->width      = mctx->width;
    st->codecpar->height     = mctx->height;
    st->codecpar->format     = AV_PIX_FMT_YUV420P;    // 像素格式

    // 设置流时间基（由帧率推导）
    avpriv_set_pts_info(st, 64,                        // pts_wrap_bits
                        mctx->framerate.den,           // 时间基分子
                        mctx->framerate.num);          // 时间基分母
    // 例如 25fps → time_base = {1, 25}，每帧 pts 递增 1

    st->avg_frame_rate = mctx->framerate;

    av_log(s, AV_LOG_VERBOSE,
           "MyFormat: %dx%d @ %d/%d fps\n",
           mctx->width, mctx->height,
           mctx->framerate.num, mctx->framerate.den);
    return 0;
}

// ─────────────────────────────────────────────
// 步骤3：读取数据包（read_packet）
// 每次调用读取一个数据块，填充 AVPacket
// 返回 0 成功，AVERROR_EOF 文件结束，< 0 错误
// ─────────────────────────────────────────────
static int myformat_read_packet(AVFormatContext *s, AVPacket *pkt)
{
    MyFormatContext *mctx = s->priv_data;
    AVIOContext *pb = s->pb;
    uint8_t  block_type;
    uint32_t block_size;
    int ret;

    // 检查是否到达文件末尾
    if (avio_feof(pb))
        return AVERROR_EOF;

    // 读取块头
    block_type = avio_r8(pb);
    if (avio_feof(pb))
        return AVERROR_EOF;  // 读取块类型后遇到 EOF

    block_size = avio_rb32(pb);
    if (block_size == 0 || block_size > INT_MAX / 2) {
        av_log(s, AV_LOG_ERROR, "Invalid block size: %u\n", block_size);
        return AVERROR_INVALIDDATA;
    }

    // 分配 AVPacket 数据缓冲区并读取块数据
    ret = av_get_packet(pb, pkt, block_size);
    if (ret < 0)
        return ret;

    // 根据块类型设置流索引
    switch (block_type) {
    case 0x01:  // 视频帧
        pkt->stream_index = mctx->video_stream_idx;
        pkt->flags |= AV_PKT_FLAG_KEY;  // 本例所有帧都是关键帧（原始视频）
        break;
    case 0x02:  // 音频帧（本例暂不支持）
        av_packet_unref(pkt);
        return FFERROR_REDO;  // 告诉框架跳过此包，重新调用 read_packet
    default:
        av_log(s, AV_LOG_WARNING, "Unknown block type: 0x%02X, skipping\n", block_type);
        av_packet_unref(pkt);
        return FFERROR_REDO;
    }

    return 0;
}

// ─────────────────────────────────────────────
// 步骤4（可选）：Seek 支持
// 如果格式支持随机访问，实现此函数
// ─────────────────────────────────────────────
static int myformat_read_seek(AVFormatContext *s, int stream_index,
                               int64_t timestamp, int flags)
{
    // 简单格式可以使用通用二分查找
    // return ff_seek_frame_binary(s, stream_index, timestamp, flags);

    // 本例不支持 seek
    return AVERROR(ENOSYS);
}

// ─────────────────────────────────────────────
// 步骤5（可选）：关闭
// 释放 read_header 中分配的资源
// ─────────────────────────────────────────────
static int myformat_read_close(AVFormatContext *s)
{
    // MyFormatContext 由框架自动释放（priv_data_size 指定了大小）
    // 如果在 read_header 中分配了额外资源，在这里释放
    return 0;
}

// ─────────────────────────────────────────────
// 步骤6：注册解封装器
// ─────────────────────────────────────────────
const FFInputFormat ff_myformat_demuxer = {
    .p.name         = "myformat",                          // 格式名（ffmpeg -f myformat 使用）
    .p.long_name    = NULL_IF_CONFIG_SMALL("My Custom Format"),
    .p.extensions   = "myfmt",                             // 文件扩展名（逗号分隔多个）
    .p.flags        = AVFMT_GENERIC_INDEX,                 // 使用通用索引
    .priv_data_size = sizeof(MyFormatContext),             // 私有上下文大小
    .read_probe     = myformat_probe,
    .read_header    = myformat_read_header,
    .read_packet    = myformat_read_packet,
    .read_seek      = myformat_read_seek,
    .read_close     = myformat_read_close,
};
```

#### 16.2.3 注册解封装器

**第一步**：在 `libavformat/allformats.c` 中添加声明：

```c
// libavformat/allformats.c（按字母顺序插入）
extern const FFInputFormat  ff_myformat_demuxer;
```

**第二步**：在 `libavformat/Makefile` 中添加编译规则：

```makefile
# libavformat/Makefile（按字母顺序插入）
OBJS-$(CONFIG_MYFORMAT_DEMUXER)          += myformatdec.o
```

**第三步**：重新配置并编译：

```bash
./configure --enable-demuxer=myformat
make -j$(nproc)

# 验证注册成功
./ffmpeg -formats | grep myformat
# 输出：D  myformat         My Custom Format
```

**测试解封装器**：

```bash
# 使用自定义格式打开文件
./ffmpeg -f myformat -i test.myfmt -f null -

# 查看文件信息
./ffprobe -f myformat test.myfmt
```

---

### 16.3 开发自定义封装器（Muxer）

**目标**：让 FFmpeg 能够将音视频数据写入自定义格式文件。

**文件路径**：`libavformat/myformatenc.c`

```c
/*
 * MyFormat muxer
 * 自定义格式封装器示例
 */
#include "libavutil/intreadwrite.h"
#include "libavcodec/codec_id.h"
#include "libavcodec/codec_par.h"
#include "avformat.h"
#include "mux.h"                     // FFOutputFormat 定义
#include "internal.h"

#define MYFMT_MAGIC  0x4D59464D

// 私有上下文
typedef struct MyMuxContext {
    int64_t frame_count;    // 已写入的帧数
} MyMuxContext;

// ─────────────────────────────────────────────
// 步骤1：初始化（init）
// 在 write_header 之前调用，可以在此验证流参数
// ─────────────────────────────────────────────
static int mymux_init(AVFormatContext *s)
{
    // 验证：本格式只支持一路视频流
    if (s->nb_streams != 1 ||
        s->streams[0]->codecpar->codec_type != AVMEDIA_TYPE_VIDEO) {
        av_log(s, AV_LOG_ERROR,
               "MyFormat only supports exactly one video stream\n");
        return AVERROR(EINVAL);
    }
    return 0;
}

// ─────────────────────────────────────────────
// 步骤2：写文件头（write_header）
// 写入格式头部信息
// ─────────────────────────────────────────────
static int mymux_write_header(AVFormatContext *s)
{
    AVIOContext *pb = s->pb;
    AVStream *st = s->streams[0];
    AVCodecParameters *par = st->codecpar;
    AVRational fps = st->avg_frame_rate;

    if (!fps.num || !fps.den) {
        av_log(s, AV_LOG_ERROR, "Frame rate not set\n");
        return AVERROR(EINVAL);
    }

    // 写入文件头
    avio_wb32(pb, MYFMT_MAGIC);         // 魔数（4字节大端）
    avio_w8(pb, 0x01);                  // 版本
    avio_wb16(pb, par->width);          // 宽度
    avio_wb16(pb, par->height);         // 高度
    avio_wb16(pb, fps.num);             // 帧率分子
    avio_wb16(pb, fps.den);             // 帧率分母

    // 刷新缓冲区（确保头部立即写入）
    avio_flush(pb);

    av_log(s, AV_LOG_VERBOSE,
           "MyFormat muxer: %dx%d @ %d/%d fps\n",
           par->width, par->height, fps.num, fps.den);
    return 0;
}

// ─────────────────────────────────────────────
// 步骤3：写数据包（write_packet）
// 每次调用写入一个数据块
// ─────────────────────────────────────────────
static int mymux_write_packet(AVFormatContext *s, AVPacket *pkt)
{
    MyMuxContext *mctx = s->priv_data;
    AVIOContext *pb = s->pb;

    if (!pkt) {
        // pkt == NULL 表示刷新（仅当 FF_OFMT_FLAG_ALLOW_FLUSH 设置时才会收到）
        return 0;
    }

    // 写入块头
    avio_w8(pb, 0x01);                  // 块类型：视频帧
    avio_wb32(pb, pkt->size);           // 块大小

    // 写入块数据
    avio_write(pb, pkt->data, pkt->size);

    mctx->frame_count++;
    return 0;
}

// ─────────────────────────────────────────────
// 步骤4：写文件尾（write_trailer）
// 写入索引、总帧数等尾部信息
// ─────────────────────────────────────────────
static int mymux_write_trailer(AVFormatContext *s)
{
    MyMuxContext *mctx = s->priv_data;
    av_log(s, AV_LOG_INFO,
           "MyFormat: wrote %"PRId64" frames\n", mctx->frame_count);
    // 如果格式需要在文件尾写入索引（如 MP4 的 moov atom），在这里写入
    return 0;
}

// ─────────────────────────────────────────────
// 步骤5：注册封装器
// ─────────────────────────────────────────────
const FFOutputFormat ff_myformat_muxer = {
    .p.name           = "myformat",
    .p.long_name      = NULL_IF_CONFIG_SMALL("My Custom Format"),
    .p.extensions     = "myfmt",
    .p.video_codec    = AV_CODEC_ID_RAWVIDEO,   // 默认视频编解码器
    .p.audio_codec    = AV_CODEC_ID_NONE,       // 不支持音频
    .p.subtitle_codec = AV_CODEC_ID_NONE,
    .flags_internal   = FF_OFMT_FLAG_MAX_ONE_OF_EACH,  // 最多一路视频
    .priv_data_size   = sizeof(MyMuxContext),
    .init             = mymux_init,
    .write_header     = mymux_write_header,
    .write_packet     = mymux_write_packet,
    .write_trailer    = mymux_write_trailer,
};
```

**注册封装器**（在 `libavformat/allformats.c` 中添加）：

```c
extern const FFOutputFormat ff_myformat_muxer;
```

**在 Makefile 中添加**：

```makefile
OBJS-$(CONFIG_MYFORMAT_MUXER)            += myformatenc.o
```

**测试封装器**：

```bash
# 将 MP4 转换为自定义格式
./ffmpeg -i input.mp4 -f myformat -vcodec rawvideo output.myfmt

# 验证输出
./ffprobe -f myformat output.myfmt
```

---

### 16.4 开发自定义编解码器（Codec）

**目标**：实现一个简单的自定义视频编解码器插件。

> **注意**：编解码器插件使用内部结构 `FFCodec`（定义在 `libavcodec/codec_internal.h`），
> 其公开部分是 `AVCodec`。

#### 16.4.1 核心数据结构

```c
/* libavcodec/codec_internal.h（简化版）*/
typedef struct FFCodec {
    AVCodec p;              // 公开部分（第一个字段，可安全转换）
    int priv_data_size;     // 私有上下文大小

    // 编解码器初始化
    int (*init)(AVCodecContext *);

    // 解码：新 API（推荐）
    int (*cb.decode)(AVCodecContext *, AVFrame *, int *got_frame, AVPacket *);
    // 编码：新 API（推荐）
    int (*cb.encode)(AVCodecContext *, AVPacket *, const AVFrame *, int *got_packet);

    // 清理
    int (*close)(AVCodecContext *);

    // 刷新（处理 B 帧等缓冲数据）
    void (*flush)(AVCodecContext *);
} FFCodec;
```

#### 16.4.2 自定义解码器实现

**文件路径**：`libavcodec/mycodecdec.c`

```c
/*
 * MyCodec decoder
 * 自定义视频解码器示例（简单的 RLE 行程编码解码器）
 */
#include "libavutil/imgutils.h"
#include "avcodec.h"
#include "codec_internal.h"     // FFCodec 定义
#include "decode.h"

// 私有上下文
typedef struct MyCodecDecContext {
    int frame_num;          // 解码帧计数
} MyCodecDecContext;

// ─────────────────────────────────────────────
// 初始化解码器
// ─────────────────────────────────────────────
static av_cold int mydec_init(AVCodecContext *avctx)
{
    MyCodecDecContext *ctx = avctx->priv_data;
    ctx->frame_num = 0;

    // 验证像素格式
    avctx->pix_fmt = AV_PIX_FMT_YUV420P;

    av_log(avctx, AV_LOG_VERBOSE,
           "MyCodec decoder initialized: %dx%d\n",
           avctx->width, avctx->height);
    return 0;
}

// ─────────────────────────────────────────────
// 解码一帧
// pkt：输入压缩包
// frame：输出解码帧（框架已分配，但数据缓冲区需要在这里分配）
// got_frame：输出是否成功解码了一帧（1=是，0=否）
// ─────────────────────────────────────────────
static int mydec_decode(AVCodecContext *avctx, AVFrame *frame,
                         int *got_frame, AVPacket *pkt)
{
    MyCodecDecContext *ctx = avctx->priv_data;
    const uint8_t *src = pkt->data;
    int src_size = pkt->size;
    int ret;

    // 分配输出帧缓冲区
    frame->format = avctx->pix_fmt;
    frame->width  = avctx->width;
    frame->height = avctx->height;
    ret = av_frame_get_buffer(frame, 0);
    if (ret < 0)
        return ret;

    // 确保帧可写
    ret = av_frame_make_writable(frame);
    if (ret < 0)
        return ret;

    // ★ 这里实现你的解码逻辑 ★
    // 本例：简单地将压缩数据复制到 Y 平面（实际应实现 RLE 解码等）
    int y_size = avctx->width * avctx->height;
    if (src_size < y_size) {
        av_log(avctx, AV_LOG_ERROR,
               "Packet too small: %d < %d\n", src_size, y_size);
        return AVERROR_INVALIDDATA;
    }

    // 逐行复制（注意使用 linesize，不是 width）
    for (int y = 0; y < avctx->height; y++) {
        memcpy(frame->data[0] + y * frame->linesize[0],
               src + y * avctx->width,
               avctx->width);
    }
    // U/V 平面填充为 128（灰色）
    for (int y = 0; y < avctx->height / 2; y++) {
        memset(frame->data[1] + y * frame->linesize[1], 128, avctx->width / 2);
        memset(frame->data[2] + y * frame->linesize[2], 128, avctx->width / 2);
    }

    // 设置时间戳
    frame->pts = pkt->pts;
    frame->pkt_dts = pkt->dts;

    ctx->frame_num++;
    *got_frame = 1;     // ★ 必须设置为 1，表示成功解码了一帧
    return pkt->size;   // 返回消耗的字节数
}

// ─────────────────────────────────────────────
// 清理解码器
// ─────────────────────────────────────────────
static av_cold int mydec_close(AVCodecContext *avctx)
{
    MyCodecDecContext *ctx = avctx->priv_data;
    av_log(avctx, AV_LOG_VERBOSE,
           "MyCodec: decoded %d frames total\n", ctx->frame_num);
    return 0;
}

// ─────────────────────────────────────────────
// 注册解码器
// ─────────────────────────────────────────────
const FFCodec ff_mycodec_decoder = {
    .p.name         = "mycodec",
    CODEC_LONG_NAME("My Custom Video Codec"),
    .p.type         = AVMEDIA_TYPE_VIDEO,
    .p.id           = AV_CODEC_ID_MYCODEC,      // 需要在 codec_id.h 中添加
    .priv_data_size = sizeof(MyCodecDecContext),
    .init           = mydec_init,
    FF_CODEC_DECODE_CB(mydec_decode),           // 注册解码回调
    .close          = mydec_close,
    .p.capabilities = AV_CODEC_CAP_DR1,         // 支持直接渲染（框架分配帧缓冲区）
};
```

#### 16.4.3 自定义编码器实现

**文件路径**：`libavcodec/mycodecenc.c`

```c
/*
 * MyCodec encoder
 * 自定义视频编码器示例
 */
#include "libavutil/opt.h"
#include "avcodec.h"
#include "codec_internal.h"
#include "encode.h"

// 私有上下文（含用户可配置选项）
typedef struct MyCodecEncContext {
    const AVClass *class;   // ★ 必须是第一个字段（AVOption 系统要求）
    int quality;            // 用户选项：质量（1-10）
    int64_t frame_num;
} MyCodecEncContext;

// 选项定义（用户可通过 -mycodec_quality 5 设置）
#define OFFSET(x) offsetof(MyCodecEncContext, x)
#define VE AV_OPT_FLAG_VIDEO_PARAM | AV_OPT_FLAG_ENCODING_PARAM
static const AVOption mycodec_enc_options[] = {
    { "quality", "encoding quality (1=fastest, 10=best)",
      OFFSET(quality), AV_OPT_TYPE_INT, {.i64=5}, 1, 10, VE },
    { NULL }
};

static const AVClass mycodec_enc_class = {
    .class_name = "mycodec encoder",
    .item_name  = av_default_item_name,
    .option     = mycodec_enc_options,
    .version    = LIBAVUTIL_VERSION_INT,
};

// 初始化编码器
static av_cold int myenc_init(AVCodecContext *avctx)
{
    MyCodecEncContext *ctx = avctx->priv_data;

    // 验证像素格式
    if (avctx->pix_fmt != AV_PIX_FMT_YUV420P) {
        av_log(avctx, AV_LOG_ERROR,
               "Only YUV420P is supported, got %s\n",
               av_get_pix_fmt_name(avctx->pix_fmt));
        return AVERROR(EINVAL);
    }

    av_log(avctx, AV_LOG_VERBOSE,
           "MyCodec encoder: quality=%d\n", ctx->quality);
    return 0;
}

// 编码一帧
static int myenc_encode(AVCodecContext *avctx, AVPacket *pkt,
                         const AVFrame *frame, int *got_packet)
{
    MyCodecEncContext *ctx = avctx->priv_data;
    int y_size = avctx->width * avctx->height;
    int ret;

    // 分配输出包缓冲区
    ret = ff_get_encode_buffer(avctx, pkt, y_size, 0);
    if (ret < 0)
        return ret;

    // ★ 这里实现你的编码逻辑 ★
    // 本例：简单地将 Y 平面数据复制到输出包（实际应实现压缩算法）
    for (int y = 0; y < avctx->height; y++) {
        memcpy(pkt->data + y * avctx->width,
               frame->data[0] + y * frame->linesize[0],
               avctx->width);
    }

    // 设置关键帧标志（本例每帧都是关键帧）
    pkt->flags |= AV_PKT_FLAG_KEY;

    ctx->frame_num++;
    *got_packet = 1;    // ★ 必须设置为 1，表示成功编码了一个包
    return 0;
}

static av_cold int myenc_close(AVCodecContext *avctx)
{
    MyCodecEncContext *ctx = avctx->priv_data;
    av_log(avctx, AV_LOG_VERBOSE,
           "MyCodec: encoded %"PRId64" frames\n", ctx->frame_num);
    return 0;
}

// 声明支持的像素格式列表（NULL 结尾）
static const enum AVPixelFormat mycodec_pix_fmts[] = {
    AV_PIX_FMT_YUV420P,
    AV_PIX_FMT_NONE
};

// 注册编码器
const FFCodec ff_mycodec_encoder = {
    .p.name         = "mycodec",
    CODEC_LONG_NAME("My Custom Video Codec"),
    .p.type         = AVMEDIA_TYPE_VIDEO,
    .p.id           = AV_CODEC_ID_MYCODEC,
    .p.priv_class   = &mycodec_enc_class,
    .priv_data_size = sizeof(MyCodecEncContext),
    .init           = myenc_init,
    FF_CODEC_ENCODE_CB(myenc_encode),
    .close          = myenc_close,
    .p.pix_fmts     = mycodec_pix_fmts,
    .p.capabilities = AV_CODEC_CAP_ENCODER_REORDERED_OPAQUE,
};
```

#### 16.4.4 注册编解码器

**第一步**：在 `libavcodec/codec_id.h` 中添加编解码器 ID：

```c
/* libavcodec/codec_id.h（在 AV_CODEC_ID_NONE 之前添加）*/
enum AVCodecID {
    // ... 已有编解码器 ...
    AV_CODEC_ID_MYCODEC = 0x1FFFF,  // 选择一个未使用的 ID
    AV_CODEC_ID_NONE,
};
```

**第二步**：在 `libavcodec/allcodecs.c` 中添加声明：

```c
extern const FFCodec ff_mycodec_decoder;
extern const FFCodec ff_mycodec_encoder;
```

**第三步**：在 `libavcodec/Makefile` 中添加编译规则：

```makefile
OBJS-$(CONFIG_MYCODEC_DECODER)           += mycodecdec.o
OBJS-$(CONFIG_MYCODEC_ENCODER)           += mycodecenc.o
```

**第四步**：重新配置并编译：

```bash
./configure --enable-decoder=mycodec --enable-encoder=mycodec
make -j$(nproc)

# 验证注册成功
./ffmpeg -codecs | grep mycodec
# 输出：DEV.LS mycodec              My Custom Video Codec
```

---

### 16.5 插件开发完整工作流

```
┌─────────────────────────────────────────────────────────────────┐
│                    插件开发完整工作流                              │
└─────────────────────────────────────────────────────────────────┘

1. 确定插件类型
   ├── 读取新格式？         → 开发 Demuxer（FFInputFormat）
   ├── 写入新格式？         → 开发 Muxer（FFOutputFormat）
   ├── 解压缩新编码？       → 开发 Decoder（FFCodec）
   ├── 压缩为新编码？       → 开发 Encoder（FFCodec）
   └── 处理音视频帧？       → 开发 Filter（AVFilter）

2. 复制最相似的现有实现作为模板
   ├── 简单 Demuxer 参考：  libavformat/aacdec.c（6.3KB）
   ├── 简单 Muxer 参考：    libavformat/a64.c（2.3KB）
   ├── 简单 Decoder 参考：  libavcodec/rawdec.c
   ├── 简单 Encoder 参考：  libavcodec/rawenc.c
   └── 简单 Filter 参考：   libavfilter/vf_negate.c

3. 实现核心回调函数
   ├── Demuxer：probe → read_header → read_packet → read_close
   ├── Muxer：  init → write_header → write_packet → write_trailer
   └── Codec：  init → decode/encode → close

4. 注册插件
   ├── 在 allformats.c / allcodecs.c 添加 extern 声明
   └── 在 Makefile 添加编译规则

5. 编译测试
   ├── ./configure --enable-demuxer=xxx
   ├── make -j$(nproc)
   └── ./ffmpeg -formats / -codecs 验证注册

6. 调试
   ├── 使用 -loglevel verbose 查看详细日志
   ├── 使用 GDB 在 probe/read_header/read_packet 设断点
   └── 使用 Valgrind 检查内存泄漏
```

### 16.6 插件开发关键注意事项

| 注意点 | 说明 |
|--------|------|
| **私有上下文** | `priv_data_size` 指定大小，框架自动分配/释放，通过 `s->priv_data` 访问 |
| **AVOption 第一字段** | 编解码器私有上下文的第一个字段必须是 `const AVClass *class` |
| **NULL_IF_CONFIG_SMALL** | 长名称用此宏包裹，可在精简构建中省略字符串 |
| **FFERROR_REDO** | `read_packet` 返回此值表示跳过当前块，框架会重新调用 |
| **got_frame/got_packet** | 旧式 decode/encode API 必须正确设置此标志 |
| **av_cold** | 标记 init/close 函数为冷路径，提示编译器优化 |
| **线程安全** | `read_packet`/`decode`/`encode` 可能被多线程调用，注意保护共享状态 |
| **错误码** | 始终返回 `AVERROR(errno)` 或 `AVERROR_xxx`，不要返回原始 errno |

---

## 结语

FFmpeg 是一个经过 20 多年演进的工程杰作。它的代码库庞大而复杂，但其中蕴含着许多值得学习的设计智慧：

- **引用计数缓冲区**解决了多线程数据共享问题
- **有理数时间系统**解决了浮点精度问题
- **推模型 API** 解决了 B 帧重排序问题
- **调度器架构**解决了多路流水线同步问题

学习 FFmpeg 不仅是学习一个工具，更是学习如何设计一个高性能、高可扩展性的多媒体处理系统。

**学习建议**：
1. 从命令行工具开始，建立直觉
2. 运行官方示例（`doc/examples/`），理解 API 用法
3. 对照本文档阅读源码，理解设计决策
4. 动手写代码，遇到问题查源码
5. 加入社区，与其他开发者交流

祝学习愉快！🎉

---

**文档版本**：v2.0  
**最后更新**：2026-06-08  
**作者**：汪亮 (bertonwang) | 47608843@qq.com  
**基于源码**：FFmpeg master 分支
