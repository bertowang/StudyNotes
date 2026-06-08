# Nginx 源码学习指南

---

> **作者**：汪亮（bertonwang）
> **联系邮箱**：47608843@qq.com
>
> **源码仓库**https://github.com/nginx/nginx 
> 
> > 本文档基于 **nginx 1.31.2** 源码（`src/core/nginx.h` 中 `NGINX_VERSION "1.31.2"`）进行学习分析，
> 分析时同步的最新 commit 为 `ac4bedfafe5ae2f688c4f54cb1f99ce275110186`> 。
> 由于 nginx 仍在持续迭代，若阅读时源码已有更新，请以最新源码为准。欢迎参考 nginx 官方文档或源码注释。
>
> **适用读者**：对 C 语言有基本了解，希望深入理解高性能服务器设计的开发者。
>
> **文档版本**：v1.3 
> **最后更新**：2026-06-08

---

## 目录

1. [项目概述](#1-项目概述)
2. [项目结构总览](#2-项目结构总览)
3. [核心概念与设计哲学](#3-核心概念与设计哲学)
4. [基础数据结构与工具层](#4-基础数据结构与工具层)
5. [内存池机制（ngx_pool）](#5-内存池机制ngx_pool)
6. [模块系统（ngx_module）](#6-模块系统ngx_module)
   - [6.1 模块是什么](#61-模块是什么)
   - [6.2 模块结构体（ngx_module_t）](#62-模块结构体ngx_module_t)
   - [6.3 模块类型与对应的 ctx 结构体](#63-模块类型与对应的-ctx-结构体)
   - [6.4 如何新增一个 HTTP 模块（完整步骤）](#64-如何新增一个-http-模块完整步骤)
   - [6.5 模块如何融入 nginx 服务（生命周期全景）](#65-模块如何融入-nginx-服务生命周期全景)
   - [6.6 HTTP 模块如何"起作用"：Phase Handler 机制](#66-http-模块如何起作用phase-handler-机制)
   - [6.7 模块间如何协调工作](#67-模块间如何协调工作)
   - [6.8 模块协调工作全景图](#68-模块协调工作全景图)
   - [6.9 静态模块 vs 动态模块](#69-静态模块-vs-动态模块)
7. [配置解析系统（ngx_conf）](#7-配置解析系统ngx_conf)
8. [运行时核心（ngx_cycle）](#8-运行时核心ngx_cycle)
9. [进程模型（Master-Worker）](#9-进程模型master-worker)
10. [事件驱动引擎（ngx_event）](#10-事件驱动引擎ngx_event)
11. [连接管理（ngx_connection）](#11-连接管理ngx_connection)
12. [HTTP 请求处理流水线](#12-http-请求处理流水线)
13. [过滤器链（Filter Chain）](#13-过滤器链filter-chain)
14. [Upstream 反向代理机制](#14-upstream-反向代理机制)
15. [日志系统（ngx_log）](#15-日志系统ngx_log)
16. [调试与诊断](#16-调试与诊断)
17. [设计洞察汇总](#17-设计洞察汇总)
18. [学习路径建议](#18-学习路径建议)
19. [源码文件索引](#19-源码文件索引)
20. [附录：常见陷阱与最佳实践](#20-附录常见陷阱与最佳实践)
21. [附录：内置模块大全](#21-附录内置模块大全)


---

## 1. 项目概述

### 1.1 简介

Nginx（发音 "engine-x"）是由 Igor Sysoev 于 2002 年开始开发、2004 年公开发布的高性能 HTTP 服务器和反向代理服务器。它以极低的内存占用和超高的并发处理能力著称，目前是全球使用最广泛的 Web 服务器之一。

**核心功能**：
- HTTP/HTTPS 静态文件服务
- 反向代理与负载均衡（HTTP、TCP、UDP）
- FastCGI/uWSGI/SCGI 代理
- HTTP/2、HTTP/3（QUIC）支持
- 邮件代理（SMTP、POP3、IMAP）
- 流媒体代理（Stream 模块）

### 1.2 核心特点

| 特性 | 说明 |
|------|------|
| **事件驱动** | 基于 epoll/kqueue 的非阻塞 I/O，单进程可处理数万并发连接 |
| **Master-Worker 架构** | 主进程管理，工作进程处理请求，天然支持热重载 |
| **内存池** | 请求级内存池，避免频繁 malloc/free，减少内存碎片 |
| **模块化设计** | 所有功能均以模块形式实现，可静态编译或动态加载 |
| **零拷贝** | 使用 sendfile() 系统调用直接从内核发送文件 |
| **配置继承** | main → server → location 三级配置继承机制 |

### 1.3 版本信息

```c
// src/core/nginx.h
#define nginx_version      1031002      // 数字版本号：1.31.2
#define NGINX_VERSION      "1.31.2"     // 字符串版本号
#define NGINX_VER          "nginx/" NGINX_VERSION
```

---

## 2. 项目结构总览

### 2.1 目录树

```
nginx/
├── auto/                   # 构建系统脚本（configure 脚本的辅助文件）
│   ├── configure           # 主配置脚本入口
│   ├── options             # 编译选项定义（27KB，所有 --with-xxx 选项）
│   ├── modules             # 模块列表（45KB，所有内置模块的源文件列表）
│   ├── make                # Makefile 生成脚本
│   ├── sources             # 核心源文件列表
│   ├── cc/                 # 各编译器（gcc/clang/msvc/icc）的编译选项
│   └── os/                 # 各操作系统（linux/darwin/freebsd）的特性检测
│
├── conf/                   # 默认配置文件
│   ├── nginx.conf          # 主配置文件模板
│   ├── mime.types          # MIME 类型映射表
│   ├── fastcgi.conf        # FastCGI 参数配置
│   └── fastcgi_params      # FastCGI 参数（旧版）
│
├── src/                    # 核心源代码
│   ├── core/               # 核心基础库（内存池、字符串、数据结构、日志等）
│   ├── event/              # 事件驱动引擎（epoll/kqueue/select 等）
│   │   ├── modules/        # 各平台事件模块（epoll、kqueue、poll、select）
│   │   └── quic/           # QUIC/HTTP3 实现
│   ├── http/               # HTTP 协议处理
│   │   ├── modules/        # HTTP 功能模块（proxy、gzip、rewrite 等）
│   │   ├── v2/             # HTTP/2 实现
│   │   └── v3/             # HTTP/3 实现
│   ├── mail/               # 邮件代理模块（SMTP/POP3/IMAP）
│   ├── stream/             # TCP/UDP 流代理模块
│   ├── misc/               # 杂项（Google PerfTools 集成、C++ 测试）
│   └── os/
│       ├── unix/           # Unix/Linux 平台相关实现（进程、文件、socket）
│       └── win32/          # Windows 平台相关实现
│
└── docs/                   # 文档（XML 格式，用于生成官网文档）
```

### 2.2 核心文件代码量分布

| 文件 | 大小 | 说明 |
|------|------|------|
| `src/http/ngx_http_upstream.c` | 190 KB | 反向代理核心，最复杂的文件 |
| `src/http/ngx_http_core_module.c` | 152 KB | HTTP 核心模块，location 匹配等 |
| `src/http/ngx_http_request.c` | 106 KB | HTTP 请求生命周期管理 |
| `src/core/ngx_string.c` | 48 KB | 字符串处理工具库 |
| `src/core/ngx_connection.c` | 46 KB | 连接管理 |
| `src/core/nginx.c` | 41 KB | 程序入口，main 函数 |
| `src/core/ngx_cycle.c` | 39 KB | 运行时核心，ngx_init_cycle |
| `src/os/unix/ngx_process_cycle.c` | 33 KB | Master-Worker 进程管理 |
| `src/event/ngx_event.c` | 35 KB | 事件模块核心 |
| `src/event/modules/ngx_epoll_module.c` | 26 KB | epoll 事件驱动实现 |

### 2.3 推荐阅读顺序

| 阶段 | 文件 | 预计时间 | 目标 |
|------|------|----------|------|
| **第一步** | `src/core/nginx.h` + `src/core/ngx_core.h` | 30 分钟 | 了解版本和全局头文件 |
| **第二步** | `src/core/ngx_palloc.h/.c` | 1 小时 | 掌握内存池机制 |
| **第三步** | `src/core/ngx_string.h` | 30 分钟 | 了解 ngx_str_t 字符串 |
| **第四步** | `src/core/ngx_module.h` | 1 小时 | 理解模块系统 |
| **第五步** | `src/core/ngx_conf_file.h/.c` | 2 小时 | 配置解析机制 |
| **第六步** | `src/core/ngx_cycle.h/.c` | 2 小时 | 运行时核心 |
| **第七步** | `src/core/nginx.c` | 1 小时 | 启动流程 |
| **第八步** | `src/os/unix/ngx_process_cycle.c` | 2 小时 | 进程模型 |
| **第九步** | `src/event/ngx_event.h/.c` | 2 小时 | 事件驱动 |
| **第十步** | `src/event/modules/ngx_epoll_module.c` | 2 小时 | epoll 实现 |
| **第十一步** | `src/http/ngx_http_request.h/.c` | 3 小时 | HTTP 请求处理 |
| **第十二步** | `src/http/ngx_http_upstream.c` | 4 小时 | 反向代理 |

---

## 3. 核心概念与设计哲学

### 3.1 设计理念

Nginx 的设计哲学可以用三个词概括：**高效**、**简洁**、**可扩展**。

**高效**：
- 使用事件驱动而非线程模型，避免线程切换开销
- 内存池减少系统调用次数
- sendfile 零拷贝传输文件
- 连接池复用，避免频繁创建/销毁

**简洁**：
- 代码风格统一，命名规范清晰（`ngx_` 前缀）
- 模块接口简单，只需实现几个回调函数
- 配置语法直观，层级清晰

**可扩展**：
- 模块化架构，功能完全解耦
- 钩子机制（phase handler），允许模块在请求处理的任意阶段介入
- 动态模块支持（`load_module` 指令）

### 3.2 命名规范

```
ngx_          → nginx 核心命名空间前缀
ngx_http_     → HTTP 模块前缀
ngx_stream_   → Stream 模块前缀
ngx_mail_     → Mail 模块前缀
ngx_event_    → 事件模块前缀

_t            → 类型定义（typedef）后缀，如 ngx_pool_t
_s            → 结构体定义后缀，如 ngx_pool_s
_pt           → 函数指针类型后缀，如 ngx_event_handler_pt
_e            → 枚举类型后缀，如 ngx_http_state_e
_n            → 数字版本的字段，如 content_length_n（对应 content_length 字符串）
```

### 3.3 关键设计决策

| 决策 | 选择 | 代价/收益 |
|------|------|-----------|
| 并发模型 | 事件驱动（非阻塞 I/O）而非多线程 | 收益：极低内存占用，无锁竞争；代价：编程复杂度高 |
| 内存管理 | 请求级内存池而非 malloc/free | 收益：无内存泄漏风险，分配速度快；代价：内存不能提前释放 |
| 进程模型 | Master-Worker 而非单进程 | 收益：热重载、故障隔离；代价：进程间通信复杂 |
| 配置解析 | 静态编译模块而非运行时插件 | 收益：性能最优；代价：需要重新编译添加模块（动态模块是后来补充的） |
| 字符串 | `{len, data}` 结构而非 C 字符串 | 收益：O(1) 长度获取，支持二进制数据；代价：不能直接用 printf |

### 3.4 整体架构图

```
                    ┌─────────────────────────────────┐
                    │         Master Process           │
                    │  (管理配置、信号、子进程生命周期)   │
                    └──────────────┬──────────────────┘
                                   │ fork()
              ┌────────────────────┼────────────────────┐
              │                    │                    │
    ┌─────────▼──────┐   ┌─────────▼──────┐   ┌────────▼───────┐
    │  Worker Process │   │  Worker Process │   │  Cache Manager │
    │                 │   │                 │   │    Process     │
    │  ┌───────────┐  │   │  ┌───────────┐  │   └────────────────┘
    │  │ Event Loop│  │   │  │ Event Loop│  │
    │  │  (epoll)  │  │   │  │  (epoll)  │  │
    │  └─────┬─────┘  │   │  └─────┬─────┘  │
    │        │        │   │        │        │
    │  ┌─────▼─────┐  │   │  ┌─────▼─────┐  │
    │  │Connection │  │   │  │Connection │  │
    │  │   Pool    │  │   │  │   Pool    │  │
    │  └───────────┘  │   │  └───────────┘  │
    └─────────────────┘   └─────────────────┘
```

---

## 4. 基础数据结构与工具层

### 4.1 ngx_str_t —— nginx 字符串

这是 nginx 中最基础的数据类型，**几乎所有字符串都用它表示**。

```c
// src/core/ngx_string.h:14
typedef struct {
    size_t      len;    // 字符串长度（不含 '\0'）
    u_char     *data;   // 指向字符串数据的指针（不保证以 '\0' 结尾！）
} ngx_str_t;
```

**常用宏**：

```c
// 从字面量创建 ngx_str_t（编译期计算长度）
#define ngx_string(str)     { sizeof(str) - 1, (u_char *) str }

// 示例：
ngx_str_t s = ngx_string("hello");
// 等价于：ngx_str_t s = { 5, (u_char *) "hello" };

// 设置字符串
#define ngx_str_set(str, text)  \
    (str)->len = sizeof(text) - 1; (str)->data = (u_char *) text

// 清空字符串
#define ngx_null_string     { 0, NULL }
```

> **⚠️ 注意**：`ngx_str_t.data` 指向的内存**不一定以 `\0` 结尾**！
> 不能直接用 `printf("%s", s.data)` 打印，必须用 `printf("%.*s", (int)s.len, s.data)`。

### 4.2 ngx_array_t —— 动态数组

```c
// src/core/ngx_array.h
typedef struct {
    void        *elts;      // 数组元素起始地址
    ngx_uint_t   nelts;     // 当前元素个数
    size_t       size;      // 每个元素的大小（字节）
    ngx_uint_t   nalloc;    // 已分配的元素槽位数
    ngx_pool_t  *pool;      // 所属内存池
} ngx_array_t;
```

**使用示例**：

```c
// 初始化一个存放 ngx_str_t 的数组，初始容量 10
ngx_array_t arr;
ngx_array_init(&arr, pool, 10, sizeof(ngx_str_t));

// 追加元素（返回新元素的指针）
ngx_str_t *s = ngx_array_push(&arr);
ngx_str_set(s, "hello");

// 访问元素
ngx_str_t *elts = arr.elts;
for (ngx_uint_t i = 0; i < arr.nelts; i++) {
    // 使用 elts[i]
}
```

### 4.3 ngx_list_t —— 链式列表

与 `ngx_array_t` 不同，`ngx_list_t` 是**分块链表**，适合元素数量不确定的场景（如 HTTP 头部列表）。

```c
// src/core/ngx_list.h
typedef struct ngx_list_part_s  ngx_list_part_t;

struct ngx_list_part_s {
    void             *elts;     // 本块元素起始地址
    ngx_uint_t        nelts;    // 本块已用元素数
    ngx_list_part_t  *next;     // 下一块
};

typedef struct {
    ngx_list_part_t  *last;     // 最后一块（追加时使用）
    ngx_list_part_t   part;     // 第一块（内嵌，避免额外分配）
    size_t            size;     // 每个元素大小
    ngx_uint_t        nalloc;   // 每块容量
    ngx_pool_t       *pool;     // 所属内存池
} ngx_list_t;
```

**内存布局**：

```
ngx_list_t
  ├── part (第一块，内嵌)
  │     ├── elts → [elem0][elem1][elem2]...[elemN]
  │     └── next → part2
  └── last → part2
              ├── elts → [elem0][elem1]...
              └── next → NULL
```

### 4.4 ngx_queue_t —— 双向循环链表

```c
// src/core/ngx_queue.h
typedef struct ngx_queue_s  ngx_queue_t;

struct ngx_queue_s {
    ngx_queue_t  *prev;
    ngx_queue_t  *next;
};
```

> **设计洞察**：`ngx_queue_t` 不存储数据，而是**嵌入到宿主结构体中**。
> 通过 `ngx_queue_data(q, type, link)` 宏（类似 Linux 内核的 `container_of`）从队列节点获取宿主结构体指针。

```c
// 典型用法：
typedef struct {
    ngx_queue_t   queue;    // 队列节点（嵌入）
    ngx_str_t     name;
    int           value;
} my_item_t;

// 从队列节点获取宿主结构体
ngx_queue_t *q = ngx_queue_head(&head);
my_item_t *item = ngx_queue_data(q, my_item_t, queue);
```

### 4.5 ngx_rbtree_t —— 红黑树

用于定时器管理、共享内存中的数据索引等需要有序存储的场景。

```c
// src/core/ngx_rbtree.h
typedef struct ngx_rbtree_node_s  ngx_rbtree_node_t;

struct ngx_rbtree_node_s {
    ngx_rbtree_key_t       key;     // 排序键（通常是时间戳或哈希值）
    ngx_rbtree_node_t     *left;
    ngx_rbtree_node_t     *right;
    ngx_rbtree_node_t     *parent;
    u_char                 color;   // 红(1) 或 黑(0)
    u_char                 data;    // 1字节用户数据（通常不够用，嵌入到宿主结构体）
};

typedef struct {
    ngx_rbtree_node_t     *root;
    ngx_rbtree_node_t     *sentinel;    // 哨兵节点（代替 NULL）
    ngx_rbtree_insert_pt   insert;      // 插入函数（支持自定义，处理相同 key）
} ngx_rbtree_t;
```

**定时器就是红黑树**：`ngx_event_timer.h` 中，定时器事件按超时时间排序存储在红黑树中，每次事件循环取最小值检查是否超时。

---

## 5. 内存池机制（ngx_pool）

### 5.1 为什么需要内存池？

传统 `malloc/free` 的问题：
1. 每次调用都有系统调用开销
2. 容易产生内存碎片
3. 容易忘记 `free`，导致内存泄漏

Nginx 的解决方案：**请求级内存池**。每个 HTTP 请求创建一个内存池，请求结束时整体销毁，无需逐一释放。

### 5.2 内存池数据结构

```c
// src/core/ngx_palloc.h

// 内存池数据块头部
typedef struct {
    u_char               *last;     // 当前可用内存的起始位置
    u_char               *end;      // 当前块的结束位置
    ngx_pool_t           *next;     // 下一个内存块
    ngx_uint_t            failed;   // 分配失败次数（超过4次则跳过此块）
} ngx_pool_data_t;

// 大块内存节点（超过 pool->max 的分配）
struct ngx_pool_large_s {
    ngx_pool_large_t     *next;     // 下一个大块
    void                 *alloc;    // 实际分配的内存指针
};

// 内存池主结构
struct ngx_pool_s {
    ngx_pool_data_t       d;        // 当前数据块信息（last/end/next/failed）
    size_t                max;      // 小块分配的最大尺寸（通常是 pagesize-1）
    ngx_pool_t           *current;  // 当前活跃的数据块（跳过 failed 多的块）
    ngx_chain_t          *chain;    // 缓冲区链（用于 output chain）
    ngx_pool_large_t     *large;    // 大块内存链表
    ngx_pool_cleanup_t   *cleanup;  // 清理回调链表
    ngx_log_t            *log;      // 日志对象
};
```

**内存布局图**：

```
ngx_pool_t（第一块）
┌──────────────────────────────────────────┐
│ ngx_pool_data_t d                        │
│   last ──────────────────────────────►   │
│   end  ──────────────────────────────►   │
│   next ──────────────────────────────►  ngx_pool_t（第二块）
│   failed = 0                             │
│ max = 4095                               │
│ current ─────────────────────────────►  （指向当前活跃块）
│ large ───────────────────────────────►  ngx_pool_large_t
│ cleanup ─────────────────────────────►  ngx_pool_cleanup_t
│ log                                      │
├──────────────────────────────────────────┤
│ [已分配的小块数据区域]                     │
│ [可用空间 last..end]                      │
└──────────────────────────────────────────┘
```

### 5.3 核心分配逻辑

```c
// src/core/ngx_palloc.c:96
void *
ngx_palloc(ngx_pool_t *pool, size_t size)
{
    // 小块分配（size <= pool->max，通常 <= 4095 字节）
    if (size <= pool->max) {
        return ngx_palloc_small(pool, size, 1);  // 1 表示需要对齐
    }
    // 大块分配（直接 malloc，挂到 large 链表）
    return ngx_palloc_large(pool, size);
}

// 小块分配：在现有块中找空间，找不到就新建块
static ngx_inline void *
ngx_palloc_small(ngx_pool_t *pool, size_t size, ngx_uint_t align)
{
    u_char      *m;
    ngx_pool_t  *p;

    p = pool->current;  // 从当前活跃块开始找

    do {
        m = p->d.last;

        if (align) {
            m = ngx_align_ptr(m, NGX_ALIGNMENT);  // 内存对齐（通常 16 字节）
        }

        if ((size_t) (p->d.end - m) >= size) {
            p->d.last = m + size;  // 移动 last 指针，完成分配
            return m;
        }

        p = p->d.next;  // 当前块空间不足，尝试下一块

    } while (p);

    return ngx_palloc_block(pool, size);  // 所有块都满了，新建一块
}
```

> **设计洞察**：`failed` 计数器是一个精妙的优化。当一个块分配失败超过 4 次，说明它剩余空间很小，后续分配大概率也会失败。通过将 `pool->current` 推进到下一块，避免每次都从头遍历所有块，将分配的平均时间复杂度保持在 O(1)。

### 5.4 清理机制

```c
// 注册清理回调（在池销毁时自动调用）
ngx_pool_cleanup_t *c = ngx_pool_cleanup_add(pool, 0);
c->handler = my_cleanup_handler;
c->data = my_data;

// 典型用法：注册文件关闭回调
ngx_pool_cleanup_t *cln = ngx_pool_cleanup_add(pool, sizeof(ngx_pool_cleanup_file_t));
ngx_pool_cleanup_file_t *cf = cln->data;
cf->fd = fd;
cf->name = filename;
cf->log = log;
cln->handler = ngx_pool_cleanup_file;  // 池销毁时自动关闭文件
```

### 5.5 API 速查

| 函数 | 说明 |
|------|------|
| `ngx_create_pool(size, log)` | 创建内存池，`size` 是第一块的大小 |
| `ngx_destroy_pool(pool)` | 销毁内存池，释放所有内存，调用所有 cleanup |
| `ngx_reset_pool(pool)` | 重置内存池（保留结构，清空数据，释放大块） |
| `ngx_palloc(pool, size)` | 分配内存（对齐） |
| `ngx_pnalloc(pool, size)` | 分配内存（不对齐，用于字符串） |
| `ngx_pcalloc(pool, size)` | 分配并清零 |
| `ngx_pfree(pool, p)` | 释放大块内存（小块无法单独释放） |
| `ngx_pool_cleanup_add(pool, size)` | 注册清理回调 |

---

## 6. 模块系统（ngx_module）

### 6.1 模块是什么？

Nginx 的所有功能都以**模块**形式实现，包括核心功能（HTTP、事件、日志）。模块系统是 nginx 可扩展性的基础。

> **一句话理解**：nginx 本身只是一个"空壳框架"，所有真正干活的逻辑都在模块里。模块通过**注册钩子**的方式告诉框架"在什么时机调用我"。

---

### 6.2 模块结构体（ngx_module_t）

```c
// src/core/ngx_module.h
struct ngx_module_s {
    ngx_uint_t   ctx_index;   // 在同类型模块中的序号（如第3个HTTP模块）
    ngx_uint_t   index;       // 在全局模块数组 ngx_modules[] 中的序号

    char        *name;        // 模块名称字符串（如 "ngx_http_limit_req_module"）

    ngx_uint_t   version;     // nginx 版本号，动态模块加载时做兼容性检查
    const char  *signature;   // 编译特性签名（35位bit串），防止ABI不兼容

    void        *ctx;         // ★ 类型特定上下文，不同模块类型指向不同结构体
    ngx_command_t *commands;  // ★ 该模块支持的配置指令数组（以 ngx_null_command 结尾）
    ngx_uint_t   type;        // 模块类型（CORE / EVENT / HTTP / MAIL / STREAM）

    // ★ 生命周期钩子（不需要的填 NULL）
    ngx_int_t  (*init_master)(ngx_log_t *log);      // master进程启动时
    ngx_int_t  (*init_module)(ngx_cycle_t *cycle);  // 配置解析完成后（所有进程共享）
    ngx_int_t  (*init_process)(ngx_cycle_t *cycle); // 每个worker进程fork后
    ngx_int_t  (*init_thread)(ngx_cycle_t *cycle);  // 线程启动时
    void       (*exit_thread)(ngx_cycle_t *cycle);  // 线程退出时
    void       (*exit_process)(ngx_cycle_t *cycle); // worker进程退出时
    void       (*exit_master)(ngx_cycle_t *cycle);  // master进程退出时

    uintptr_t    spare_hook0;  // 保留扩展钩子 × 8
    // ... spare_hook1 ~ spare_hook7
};
```

**两个关键字段详解：**

| 字段 | 作用 |
|------|------|
| `ctx` | 指向类型特定的上下文结构体。HTTP模块指向 `ngx_http_module_t`，事件模块指向 `ngx_event_module_t`，核心模块指向 `ngx_core_module_t` |
| `commands` | 声明本模块能识别哪些配置指令（如 `limit_req`），nginx 解析配置文件时按此数组匹配并回调 |

---

### 6.3 模块类型与对应的 ctx 结构体

```
模块类型                ctx 结构体              主要用途
─────────────────────────────────────────────────────────
NGX_CORE_MODULE    →  ngx_core_module_t      全局配置（worker_processes等）
NGX_EVENT_MODULE   →  ngx_event_module_t     I/O多路复用实现（epoll/kqueue）
NGX_HTTP_MODULE    →  ngx_http_module_t      HTTP请求处理（最常用）
NGX_STREAM_MODULE  →  ngx_stream_module_t    TCP/UDP代理
NGX_MAIL_MODULE    →  ngx_mail_module_t      邮件代理
```

**HTTP 模块的 ctx 结构体（最重要）：**

```c
// src/http/ngx_http_config.h
typedef struct {
    // ① 配置解析阶段的钩子
    ngx_int_t  (*preconfiguration)(ngx_conf_t *cf);   // 解析 http{} 块之前
    ngx_int_t  (*postconfiguration)(ngx_conf_t *cf);  // 解析 http{} 块之后 ★注册handler的时机

    // ② 配置结构体的创建与合并
    void      *(*create_main_conf)(ngx_conf_t *cf);   // 创建 http{} 级别配置
    char      *(*init_main_conf)(ngx_conf_t *cf, void *conf);

    void      *(*create_srv_conf)(ngx_conf_t *cf);    // 创建 server{} 级别配置
    char      *(*merge_srv_conf)(ngx_conf_t *cf, void *prev, void *conf);

    void      *(*create_loc_conf)(ngx_conf_t *cf);    // 创建 location{} 级别配置
    char      *(*merge_loc_conf)(ngx_conf_t *cf, void *prev, void *conf);
} ngx_http_module_t;
```

> **配置三级继承**：nginx 配置有 main/srv/loc 三个层级。`merge_loc_conf` 负责将上层配置合并到下层，实现"子 location 继承父 server 配置"的效果。

---

### 6.4 如何新增一个 HTTP 模块（完整步骤）

以实现一个"给所有响应加自定义 Header"的模块为例，演示完整流程：

#### 第一步：编写模块源文件

```c
// ngx_http_myheader_module.c

#include <ngx_config.h>
#include <ngx_core.h>
#include <ngx_http.h>

/* ① 模块私有配置结构体 */
typedef struct {
    ngx_str_t  header_value;   // 对应配置指令 my_header 的值
} ngx_http_myheader_loc_conf_t;

/* ② 前向声明 */
static ngx_int_t ngx_http_myheader_handler(ngx_http_request_t *r);
static void     *ngx_http_myheader_create_loc_conf(ngx_conf_t *cf);
static char     *ngx_http_myheader_merge_loc_conf(ngx_conf_t *cf,
                     void *parent, void *child);
static ngx_int_t ngx_http_myheader_init(ngx_conf_t *cf);

/* ③ 配置指令定义 */
static ngx_command_t ngx_http_myheader_commands[] = {
    {
        ngx_string("my_header"),              // 指令名
        NGX_HTTP_LOC_CONF | NGX_CONF_TAKE1,   // 作用域：location块，接受1个参数
        ngx_conf_set_str_slot,                // 内置解析函数：把参数存入字符串字段
        NGX_HTTP_LOC_CONF_OFFSET,             // 配置结构体偏移基准
        offsetof(ngx_http_myheader_loc_conf_t, header_value), // 字段偏移
        NULL
    },
    ngx_null_command   // 数组必须以此结尾
};

/* ④ HTTP 模块上下文（ctx） */
static ngx_http_module_t ngx_http_myheader_module_ctx = {
    NULL,                                  /* preconfiguration */
    ngx_http_myheader_init,                /* postconfiguration ★ 注册handler */
    NULL,                                  /* create main configuration */
    NULL,                                  /* init main configuration */
    NULL,                                  /* create server configuration */
    NULL,                                  /* merge server configuration */
    ngx_http_myheader_create_loc_conf,     /* create location configuration */
    ngx_http_myheader_merge_loc_conf       /* merge location configuration */
};

/* ⑤ 模块本体定义 */
ngx_module_t ngx_http_myheader_module = {
    NGX_MODULE_V1,
    &ngx_http_myheader_module_ctx,   /* module context */
    ngx_http_myheader_commands,      /* module directives */
    NGX_HTTP_MODULE,                 /* module type */
    NULL, NULL, NULL, NULL, NULL, NULL, NULL,
    NGX_MODULE_V1_PADDING
};

/* ⑥ postconfiguration：把 handler 注册到 CONTENT 阶段 */
static ngx_int_t
ngx_http_myheader_init(ngx_conf_t *cf)
{
    ngx_http_handler_pt       *h;
    ngx_http_core_main_conf_t *cmcf;

    cmcf = ngx_http_conf_get_module_main_conf(cf, ngx_http_core_module);

    // 向 NGX_HTTP_CONTENT_PHASE 阶段追加一个 handler 函数指针
    h = ngx_array_push(&cmcf->phases[NGX_HTTP_CONTENT_PHASE].handlers);
    if (h == NULL) { return NGX_ERROR; }
    *h = ngx_http_myheader_handler;

    return NGX_OK;
}

/* ⑦ 实际处理函数：在响应头中追加自定义字段 */
static ngx_int_t
ngx_http_myheader_handler(ngx_http_request_t *r)
{
    ngx_http_myheader_loc_conf_t *lcf;
    ngx_table_elt_t              *h;

    // 读取当前 location 的配置
    lcf = ngx_http_get_module_loc_conf(r, ngx_http_myheader_module);

    if (lcf->header_value.len == 0) {
        return NGX_DECLINED;  // 未配置，跳过本模块，交给下一个 handler
    }

    // 向响应头链表追加一个 header
    h = ngx_list_push(&r->headers_out.headers);
    if (h == NULL) { return NGX_ERROR; }

    h->hash = 1;
    ngx_str_set(&h->key, "X-My-Header");
    h->value = lcf->header_value;

    return NGX_DECLINED;  // 继续执行后续 handler（不独占响应）
}

/* ⑧ 配置结构体的创建与合并 */
static void *
ngx_http_myheader_create_loc_conf(ngx_conf_t *cf)
{
    ngx_http_myheader_loc_conf_t *conf;
    conf = ngx_pcalloc(cf->pool, sizeof(ngx_http_myheader_loc_conf_t));
    if (conf == NULL) { return NULL; }
    return conf;
}

static char *
ngx_http_myheader_merge_loc_conf(ngx_conf_t *cf, void *parent, void *child)
{
    ngx_http_myheader_loc_conf_t *prev = parent;
    ngx_http_myheader_loc_conf_t *conf = child;
    // 子 location 未配置时，继承父级配置
    ngx_conf_merge_str_value(conf->header_value, prev->header_value, "");
    return NGX_CONF_OK;
}
```

#### 第二步：注册到编译系统

**静态编译**（修改 `auto/modules` 脚本，或直接修改 `objs/ngx_modules.c`）：

```c
// objs/ngx_modules.c（由 ./configure 自动生成）
// 在数组中加入你的模块：
extern ngx_module_t ngx_http_myheader_module;

ngx_module_t *ngx_modules[] = {
    // ... 其他模块 ...
    &ngx_http_myheader_module,   // ← 加在这里
    NULL
};
```

**动态模块**（推荐，无需重新编译 nginx 主程序）：

```bash
# 1. 编写 config 文件（与 .c 文件同目录）
# config 文件内容：
ngx_addon_name=ngx_http_myheader_module
HTTP_MODULES="$HTTP_MODULES ngx_http_myheader_module"
NGX_ADDON_SRCS="$NGX_ADDON_SRCS $ngx_addon_dir/ngx_http_myheader_module.c"

# 2. 编译为动态模块 .so
./configure --add-dynamic-module=/path/to/mymodule
make modules
# 生成 objs/ngx_http_myheader_module.so

# 3. nginx.conf 中加载
load_module modules/ngx_http_myheader_module.so;
```

#### 第三步：在 nginx.conf 中使用

```nginx
location /api/ {
    my_header "hello-from-mymodule";
    proxy_pass http://backend;
}
```

---

### 6.5 模块如何融入 nginx 服务（生命周期全景）

从 nginx 启动到处理第一个请求，模块经历以下完整生命周期：

```
┌─────────────────────────────────────────────────────────────────┐
│                      nginx 启动流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  main()                                                          │
│   │                                                              │
│   ├─① ngx_preinit_modules()                                     │
│   │     遍历 ngx_modules[] 数组，为每个模块分配全局 index         │
│   │     （index = 模块在数组中的位置，从0开始）                   │
│   │                                                              │
│   └─② ngx_init_cycle()                                          │
│         │                                                        │
│         ├─ ngx_cycle_modules()                                   │
│         │   把静态 ngx_modules[] 复制到 cycle->modules[]         │
│         │   （为动态模块预留 128 个槽位）                         │
│         │                                                        │
│         ├─ 遍历所有 CORE 模块，调用 ctx->create_conf()           │
│         │   为每个核心模块分配配置内存                            │
│         │                                                        │
│         ├─ ngx_conf_parse()  ← 解析 nginx.conf                  │
│         │   遇到指令时，在所有模块的 commands[] 中查找匹配项      │
│         │   找到后调用对应的 set() 回调，把配置值写入配置结构体   │
│         │   遇到 http{} 块时，触发所有 HTTP 模块的：              │
│         │     preconfiguration() → 解析 http 块 → postconfiguration()│
│         │                                                        │
│         ├─ ngx_init_modules()                                    │
│         │   遍历所有模块，调用 init_module() 钩子                 │
│         │   （在 master 进程中执行，适合全局初始化）              │
│         │                                                        │
│         └─ fork() worker 进程                                    │
│               │                                                  │
│               └─ 每个 worker 调用所有模块的 init_process()       │
│                   （在 worker 进程中执行，适合进程级初始化）      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**关键源码（`src/core/ngx_module.c`）：**

```c
// ① 预初始化：给每个模块分配 index
ngx_int_t ngx_preinit_modules(void)
{
    for (i = 0; ngx_modules[i]; i++) {
        ngx_modules[i]->index = i;           // 全局序号
        ngx_modules[i]->name = ngx_module_names[i];
    }
    ngx_modules_n = i;
    ngx_max_module = ngx_modules_n + NGX_MAX_DYNAMIC_MODULES; // 预留128个动态模块槽
    return NGX_OK;
}

// ② 初始化：调用每个模块的 init_module 钩子
ngx_int_t ngx_init_modules(ngx_cycle_t *cycle)
{
    for (i = 0; cycle->modules[i]; i++) {
        if (cycle->modules[i]->init_module) {
            if (cycle->modules[i]->init_module(cycle) != NGX_OK) {
                return NGX_ERROR;
            }
        }
    }
    return NGX_OK;
}
```

---

### 6.6 HTTP 模块如何"起作用"：Phase Handler 机制

HTTP 模块最核心的工作方式是**向请求处理阶段（Phase）注册 Handler**。

#### HTTP 请求处理的 11 个阶段

```c
// src/http/ngx_http_core_module.h
typedef enum {
    NGX_HTTP_POST_READ_PHASE = 0,   // 读取请求头完成后（realip模块在此工作）
    NGX_HTTP_SERVER_REWRITE_PHASE,  // server级别的rewrite
    NGX_HTTP_FIND_CONFIG_PHASE,     // 查找匹配的location（框架内部，不可注册）
    NGX_HTTP_REWRITE_PHASE,         // location级别的rewrite
    NGX_HTTP_POST_REWRITE_PHASE,    // rewrite后处理（框架内部，不可注册）
    NGX_HTTP_PREACCESS_PHASE,       // 访问控制前（limit_req/limit_conn在此工作）
    NGX_HTTP_ACCESS_PHASE,          // 访问控制（access/auth_basic在此工作）
    NGX_HTTP_POST_ACCESS_PHASE,     // 访问控制后（框架内部，不可注册）
    NGX_HTTP_PRECONTENT_PHASE,      // 内容生成前（try_files在此工作）
    NGX_HTTP_CONTENT_PHASE,         // 内容生成（proxy/fastcgi/static在此工作）★最常用
    NGX_HTTP_LOG_PHASE              // 请求日志（access_log在此工作）
} ngx_http_phases;
```

#### 注册 Handler 的时机：postconfiguration

```c
// 以 limit_req 模块为例（src/http/modules/ngx_http_limit_req_module.c:1087）
static ngx_int_t
ngx_http_limit_req_init(ngx_conf_t *cf)   // 这就是 postconfiguration 回调
{
    ngx_http_handler_pt       *h;
    ngx_http_core_main_conf_t *cmcf;

    // 获取 HTTP 核心模块的 main 配置（phases 数组存在这里）
    cmcf = ngx_http_conf_get_module_main_conf(cf, ngx_http_core_module);

    // 向 PREACCESS 阶段的 handlers 数组追加一个函数指针
    h = ngx_array_push(&cmcf->phases[NGX_HTTP_PREACCESS_PHASE].handlers);
    if (h == NULL) { return NGX_ERROR; }

    *h = ngx_http_limit_req_handler;  // 注册处理函数

    return NGX_OK;
}
```

#### Handler 返回值的含义

```c
// handler 函数的返回值决定请求的走向：
NGX_OK       // 处理完成，结束请求（发送响应）
NGX_DECLINED // 本模块不处理，交给同阶段的下一个 handler
NGX_AGAIN    // 需要等待（异步操作未完成），挂起请求
NGX_ERROR    // 发生错误，返回 500
NGX_DONE     // 请求已被接管（如子请求），不再继续
// 返回 HTTP 状态码（如 403）：直接返回该状态码给客户端
```

#### 阶段执行流程图

```
请求到达
   │
   ▼
POST_READ ──→ [realip_handler] ──→ NGX_DECLINED ──→ 下一阶段
   │
   ▼
SERVER_REWRITE ──→ [rewrite_handler]
   │
   ▼
FIND_CONFIG ──→ 框架匹配 location（不可注册）
   │
   ▼
REWRITE ──→ [rewrite_handler]
   │
   ▼
PREACCESS ──→ [limit_req_handler] ──→ NGX_DECLINED
          ──→ [limit_conn_handler] ──→ NGX_DECLINED
   │
   ▼
ACCESS ──→ [access_handler] ──→ NGX_DECLINED
       ──→ [auth_basic_handler] ──→ NGX_DECLINED
   │
   ▼
CONTENT ──→ [proxy_handler] ──→ NGX_OK（找到处理者，结束）
        ──→ [static_handler] ──→ NGX_OK
   │
   ▼
LOG ──→ [log_handler]（无论成功失败都执行）
```

---

### 6.7 模块间如何协调工作

nginx 模块之间**没有直接调用关系**，而是通过以下三种机制协调：

#### 机制一：共享配置结构体（最常用）

每个模块的配置存储在 `cycle->conf_ctx` 中，任何模块都可以通过宏读取其他模块的配置：

```c
// 读取 HTTP 核心模块的 main 配置（获取 phases 数组、server 列表等）
ngx_http_core_main_conf_t *cmcf =
    ngx_http_get_module_main_conf(r, ngx_http_core_module);

// 读取 upstream 模块的配置（proxy 模块读取 upstream 定义）
ngx_http_upstream_conf_t *ucf =
    ngx_http_get_module_loc_conf(r, ngx_http_upstream_module);

// 读取自己的 location 配置
ngx_http_myheader_loc_conf_t *lcf =
    ngx_http_get_module_loc_conf(r, ngx_http_myheader_module);
```

**配置索引原理：**

```
cycle->conf_ctx[module.index]          ← 核心模块配置
  └── ngx_http_conf_ctx_t
        ├── main_conf[module.ctx_index]  ← HTTP main 级配置
        ├── srv_conf[module.ctx_index]   ← HTTP server 级配置
        └── loc_conf[module.ctx_index]   ← HTTP location 级配置
```

#### 机制二：过滤器链（Filter Chain）

响应过滤模块通过**链表**串联，每个模块保存"下一个过滤器"的指针：

```c
// 每个 filter 模块在 postconfiguration 中"插入"到链表头部
static ngx_http_output_header_filter_pt  ngx_http_next_header_filter;

static ngx_int_t
ngx_http_gzip_header_filter(ngx_http_request_t *r)
{
    // ... 处理响应头 ...

    // 调用链中的下一个 filter
    return ngx_http_next_header_filter(r);
}

// postconfiguration 中注册：
static ngx_int_t ngx_http_gzip_filter_init(ngx_conf_t *cf)
{
    // 把自己插到链表头，同时保存原来的头（即下一个filter）
    ngx_http_next_header_filter = ngx_http_top_header_filter;
    ngx_http_top_header_filter  = ngx_http_gzip_header_filter;
    return NGX_OK;
}
```

**过滤器链示意（后注册的在外层先执行）：**

```
ngx_http_top_header_filter
    → headers_filter（add_header/expires）
        → gzip_filter（压缩）
            → chunked_filter（分块编码）
                → not_modified_filter（304判断）
                    → [最终发送给客户端]
```

#### 机制三：请求上下文（Per-request Context）

每个模块可以在请求对象 `ngx_http_request_t` 上挂载私有数据，模块间通过请求对象传递状态：

```c
// 在请求上挂载模块私有数据
ngx_http_set_ctx(r, my_ctx, ngx_http_myheader_module);

// 在后续 handler 中读取
my_ctx_t *ctx = ngx_http_get_module_ctx(r, ngx_http_myheader_module);
if (ctx == NULL) {
    // 首次进入，创建上下文
    ctx = ngx_palloc(r->pool, sizeof(my_ctx_t));
    ngx_http_set_ctx(r, ctx, ngx_http_myheader_module);
}
```

#### 机制四：变量系统（Variable System）

模块可以注册变量，供其他模块（如 log_format、map）使用：

```c
// limit_req 模块注册 $limit_req_status 变量
static ngx_http_variable_t ngx_http_limit_req_vars[] = {
    { ngx_string("limit_req_status"), NULL,
      ngx_http_limit_req_status_variable, 0, NGX_HTTP_VAR_NOCACHEABLE, 0 },
    ngx_http_null_variable
};

// preconfiguration 中注册变量
static ngx_int_t ngx_http_limit_req_add_variables(ngx_conf_t *cf)
{
    ngx_http_variable_t *var = ngx_http_add_variable(cf, &name, flags);
    var->get_handler = ngx_http_limit_req_status_variable;
    return NGX_OK;
}
```

---

### 6.8 模块协调工作全景图

```
┌──────────────────────────────────────────────────────────────┐
│                    一次 HTTP 请求的处理                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  [realip模块]  POST_READ阶段                                  │
│      ↓ 修改 r->connection->addr_text（真实IP）                │
│                                                               │
│  [rewrite模块] REWRITE阶段                                    │
│      ↓ 修改 r->uri（URL重写）                                 │
│                                                               │
│  [limit_req模块] PREACCESS阶段                                │
│      ↓ 检查令牌桶，超限返回503                                │
│                                                               │
│  [access模块]  ACCESS阶段                                     │
│      ↓ 检查IP白名单，拒绝返回403                              │
│                                                               │
│  [proxy模块]   CONTENT阶段                                    │
│      ↓ 转发请求到后端，获取响应                               │
│                                                               │
│  ←←←←←←←←←←←← 响应返回 ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←  │
│                                                               │
│  [headers模块] Header Filter                                  │
│      ↓ 添加 Cache-Control、Expires 等响应头                   │
│                                                               │
│  [gzip模块]    Body Filter                                    │
│      ↓ 压缩响应体                                             │
│                                                               │
│  [chunked模块] Body Filter                                    │
│      ↓ 分块编码                                               │
│                                                               │
│  [log模块]     LOG阶段                                        │
│      ↓ 写入 access.log                                        │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

### 6.9 静态模块 vs 动态模块

| 对比项 | 静态模块 | 动态模块（.so） |
|--------|----------|-----------------|
| 编译方式 | `--add-module=path` | `--add-dynamic-module=path` |
| 加载时机 | 编译进 nginx 二进制 | 运行时 `load_module` 指令加载 |
| 兼容性检查 | 无需（同一次编译） | 检查 `version` 和 `signature` |
| 热更新 | 需重新编译 nginx | 替换 .so 文件后 reload 即可 |
| 性能 | 略优（无动态链接开销） | 几乎无差异 |
| 适用场景 | 核心功能、高频模块 | 第三方模块、频繁迭代的模块 |

**动态模块加载流程（`ngx_add_module` 函数）：**

```c
// src/core/ngx_module.c
ngx_int_t ngx_add_module(ngx_conf_t *cf, ngx_str_t *file,
    ngx_module_t *module, char **order)
{
    // 1. 版本检查
    if (module->version != nginx_version) { /* 报错 */ }

    // 2. 签名检查（35个编译特性位必须完全匹配）
    if (ngx_strcmp(module->signature, NGX_MODULE_SIGNATURE) != 0) { /* 报错 */ }

    // 3. 重复加载检查
    for (m = 0; cf->cycle->modules[m]; m++) {
        if (ngx_strcmp(cf->cycle->modules[m]->name, module->name) == 0) { /* 报错 */ }
    }

    // 4. 分配 index，插入 cycle->modules[] 数组
    module->index = ngx_module_index(cf->cycle);
    cf->cycle->modules[before] = module;
    cf->cycle->modules_n++;

    // 5. 如果是 CORE 模块，立即调用 create_conf
    if (module->type == NGX_CORE_MODULE) {
        core_module = module->ctx;
        rv = core_module->create_conf(cf->cycle);
        cf->cycle->conf_ctx[module->index] = rv;
    }
    return NGX_OK;
}
```

> **小结**：模块系统是 nginx 可扩展性的核心。掌握 `ngx_module_t` 结构体、Phase Handler 注册机制、过滤器链和配置共享这四个要点，就能读懂任意 nginx 模块的源码，也能独立开发自定义模块。

---

## 7. 配置解析系统（ngx_conf）

> 配置解析是 nginx 启动的第一步。理解配置指令如何被解析、如何存储、如何在三级层次间继承，是读懂所有模块代码的前提。

### 7.1 配置指令定义

每个模块通过 `ngx_command_t` 数组声明自己支持的配置指令：

```c
// src/core/ngx_conf_file.h:72
struct ngx_command_s {
    ngx_str_t             name;    // 指令名称，如 "worker_processes"
    ngx_uint_t            type;    // 指令类型标志（在哪里有效、接受几个参数）
    char               *(*set)(ngx_conf_t *cf, ngx_command_t *cmd, void *conf);
                                   // 解析回调函数
    ngx_uint_t            conf;    // 配置存储位置（NGX_HTTP_MAIN_CONF_OFFSET 等）
    ngx_uint_t            offset;  // 在配置结构体中的字段偏移量
    void                 *post;    // 后处理回调（可选）
};
```

**type 标志位说明**：

```c
// 参数数量（可组合）
NGX_CONF_NOARGS   // 无参数，如 "daemon;"
NGX_CONF_TAKE1    // 1个参数，如 "worker_processes 4;"
NGX_CONF_TAKE2    // 2个参数
NGX_CONF_TAKE12   // 1或2个参数
NGX_CONF_BLOCK    // 块指令，如 "http { ... }"
NGX_CONF_FLAG     // on/off 标志，如 "sendfile on;"

// 有效范围
NGX_MAIN_CONF     // 只在主配置块有效
NGX_HTTP_MAIN_CONF// 只在 http {} 块有效
NGX_HTTP_SRV_CONF // 只在 server {} 块有效
NGX_HTTP_LOC_CONF // 只在 location {} 块有效
```

### 7.2 配置继承机制

Nginx 的配置有三级：`main → server → location`。

```c
// 配置合并宏（在 init_conf 中使用）
// 如果当前级别没有设置，则继承上级的值；如果上级也没有，则使用默认值
#define ngx_conf_merge_value(conf, prev, default)   \
    if (conf == NGX_CONF_UNSET) {                   \
        conf = (prev == NGX_CONF_UNSET) ? default : prev;  \
    }

// 示例：keepalive_timeout 的继承
// location 没设置 → 继承 server 的值
// server 没设置 → 继承 http 的值
// http 没设置 → 使用默认值 75s
```

**配置上下文结构**：

```c
// src/http/ngx_http_config.h
typedef struct {
    void        **main_conf;    // http {} 级别的配置（每个模块一个指针）
    void        **srv_conf;     // server {} 级别的配置
    void        **loc_conf;     // location {} 级别的配置
} ngx_http_conf_ctx_t;
```

### 7.3 配置解析流程

```
ngx_conf_parse(cf, filename)
  │
  ├── 打开配置文件
  │
  └── 循环读取 token
        │
        ├── 识别指令名
        │
        ├── 在所有模块的 commands 数组中查找匹配的指令
        │
        ├── 检查 type 标志（参数数量、有效范围）
        │
        └── 调用 cmd->set(cf, cmd, conf)
              │
              ├── 内置 set 函数（如 ngx_conf_set_flag_slot）
              │     直接将值写入配置结构体的对应字段
              │
              └── 自定义 set 函数（模块自己实现）
```

> **小结**：配置解析系统将 nginx.conf 中的文本指令转化为内存中的配置结构体，三级继承机制（main→server→location）保证了配置的灵活性和一致性。

---

## 8. 运行时核心（ngx_cycle）

### 8.1 ngx_cycle_t —— nginx 的"世界"

`ngx_cycle_t` 是 nginx 运行时的核心数据结构，代表一个完整的运行实例。热重载时会创建新的 `ngx_cycle_t`，成功后替换旧的。

```c
// src/core/ngx_cycle.h:34
struct ngx_cycle_s {
    void                  ****conf_ctx;     // 所有模块的配置上下文（四级指针！）
                                            // conf_ctx[module.index] = 该模块的配置
    ngx_pool_t               *pool;         // cycle 级别的内存池

    ngx_log_t                *log;          // 日志对象
    ngx_log_t                 new_log;      // 新日志（重载时使用）

    ngx_connection_t        **files;        // fd → connection 的映射表
    ngx_connection_t         *free_connections;  // 空闲连接链表
    ngx_uint_t                free_connection_n; // 空闲连接数

    ngx_module_t            **modules;      // 模块数组
    ngx_uint_t                modules_n;    // 模块数量

    ngx_queue_t               reusable_connections_queue; // 可复用连接队列
    ngx_uint_t                reusable_connections_n;

    ngx_array_t               listening;    // 监听套接字数组（ngx_listening_t）
    ngx_array_t               paths;        // 路径数组（用于创建目录）

    ngx_list_t                open_files;   // 已打开的文件列表
    ngx_list_t                shared_memory;// 共享内存区域列表

    ngx_uint_t                connection_n; // 最大连接数（worker_connections）
    ngx_connection_t         *connections;  // 连接池数组
    ngx_event_t              *read_events;  // 读事件数组（与 connections 一一对应）
    ngx_event_t              *write_events; // 写事件数组

    ngx_cycle_t              *old_cycle;    // 旧的 cycle（热重载时使用）

    ngx_str_t                 conf_file;    // 配置文件路径
    ngx_str_t                 prefix;       // nginx 安装前缀路径
    ngx_str_t                 hostname;     // 主机名
};
```

> **设计洞察**：`conf_ctx` 是四级指针 `void ****`，这是 nginx 中最令人困惑的设计之一。
> 理解它的关键：`conf_ctx[module.index]` 是一个 `void *`，对于 HTTP 模块，这个 `void *` 实际上是 `ngx_http_conf_ctx_t *`，它里面又有 `main_conf/srv_conf/loc_conf` 三个指针数组。

### 8.2 ngx_init_cycle —— 初始化流程

```c
// src/core/ngx_cycle.c:37
ngx_cycle_t *
ngx_init_cycle(ngx_cycle_t *old_cycle)
{
    // 1. 创建新的内存池
    pool = ngx_create_pool(NGX_CYCLE_POOL_SIZE, log);

    // 2. 分配 cycle 结构体
    cycle = ngx_pcalloc(pool, sizeof(ngx_cycle_t));

    // 3. 为所有模块分配配置上下文
    cycle->conf_ctx = ngx_pcalloc(pool, ngx_max_module * sizeof(void *));

    // 4. 调用所有 CORE 模块的 create_conf()
    for (i = 0; cycle->modules[i]; i++) {
        if (cycle->modules[i]->type != NGX_CORE_MODULE) { continue; }
        module = cycle->modules[i]->ctx;
        if (module->create_conf) {
            rv = module->create_conf(cycle);
            cycle->conf_ctx[cycle->modules[i]->index] = rv;
        }
    }

    // 5. 解析配置文件（触发所有模块的 set 回调）
    ngx_conf_parse(&conf, &cycle->conf_file);

    // 6. 调用所有 CORE 模块的 init_conf()（设置默认值）
    for (i = 0; cycle->modules[i]; i++) {
        if (cycle->modules[i]->type != NGX_CORE_MODULE) { continue; }
        module = cycle->modules[i]->ctx;
        if (module->init_conf) {
            module->init_conf(cycle, cycle->conf_ctx[cycle->modules[i]->index]);
        }
    }

    // 7. 打开监听套接字
    ngx_open_listening_sockets(cycle);

    // 8. 初始化所有模块
    ngx_init_modules(cycle);

    return cycle;
}
```

> **小结**：`ngx_cycle_t` 是 nginx 的“世界”——所有运行时状态都在这里。热重载时创建新的 `ngx_cycle_t` 并在成功后替换旧的，这个设计保证了配置更新的原子性。四级指针 `conf_ctx` 是最令人困惑的设计，但理解它是读懂所有模块配置访问代码的关键。

---

## 9. 进程模型（Master-Worker）

> nginx 的进程模型是实现高可用和热重载的基础。本章介绍 Master/Worker 进程的职责分工、信号处理机制和热重载流程。

```c
// src/os/unix/ngx_process_cycle.h
#define NGX_PROCESS_SINGLE     0  // 单进程模式（调试用）
#define NGX_PROCESS_MASTER     1  // 主进程
#define NGX_PROCESS_SIGNALLER  2  // 信号发送进程（nginx -s reload）
#define NGX_PROCESS_WORKER     3  // 工作进程
#define NGX_PROCESS_HELPER     4  // 辅助进程（cache manager/loader）
```

### 9.2 Master 进程职责

Master 进程**不处理任何请求**，只负责：
1. 读取和验证配置
2. 创建/管理 Worker 进程
3. 处理信号（SIGHUP 热重载、SIGTERM 停止等）
4. 维护 PID 文件

```c
// src/os/unix/ngx_process_cycle.c:63
void
ngx_master_process_cycle(ngx_cycle_t *cycle)
{
    // 1. 屏蔽信号（在 sigsuspend 期间统一处理）
    sigemptyset(&set);
    sigaddset(&set, SIGCHLD);   // 子进程退出
    sigaddset(&set, SIGALRM);   // 定时器
    // ... 添加其他信号
    sigprocmask(SIG_BLOCK, &set, NULL);

    // 2. 启动 Worker 进程
    ngx_start_worker_processes(cycle, ccf->worker_processes, NGX_PROCESS_RESPAWN);
    ngx_start_cache_manager_processes(cycle, 0);

    // 3. 主循环：等待信号
    for ( ;; ) {
        sigsuspend(&set);  // 阻塞等待信号

        // 处理各种信号标志
        if (ngx_reap) {          // SIGCHLD：子进程退出，重新拉起
            live = ngx_reap_children(cycle);
        }
        if (ngx_reconfigure) {   // SIGHUP：热重载配置
            cycle = ngx_init_cycle(cycle);  // 创建新 cycle
            ngx_start_worker_processes(cycle, ...);
        }
        if (ngx_terminate) {     // SIGTERM：快速停止
            ngx_signal_worker_processes(cycle, SIGTERM);
        }
        if (ngx_quit) {          // SIGQUIT：优雅停止
            ngx_signal_worker_processes(cycle, SIGQUIT);
        }
    }
}
```

### 9.3 Worker 进程职责

Worker 进程是真正处理请求的进程：

```c
// src/os/unix/ngx_process_cycle.c（简化版）
static void
ngx_worker_process_cycle(ngx_cycle_t *cycle, void *data)
{
    // 1. 初始化（设置 CPU 亲和性、优先级、信号处理等）
    ngx_worker_process_init(cycle, worker);

    // 2. 设置进程标题
    ngx_setproctitle("worker process");

    // 3. 事件循环（永不退出，除非收到退出信号）
    for ( ;; ) {
        if (ngx_exiting) {
            // 优雅退出：等待所有连接关闭
            if (ngx_event_no_timers_left() == NGX_OK) {
                ngx_worker_process_exit(cycle);
            }
        }

        // 核心：处理事件和定时器
        ngx_process_events_and_timers(cycle);

        // 处理信号标志
        if (ngx_terminate || ngx_quit) {
            ngx_worker_process_exit(cycle);
        }
        if (ngx_reopen) {
            ngx_reopen_files(cycle, -1);  // 重新打开日志文件
        }
    }
}
```

### 9.4 热重载流程

```
用户执行: nginx -s reload
  │
  ├── 新 nginx 进程发送 SIGHUP 给 master
  │
  └── master 收到 SIGHUP
        │
        ├── ngx_init_cycle()  // 创建新 cycle，解析新配置
        │
        ├── 新 cycle 成功 → 启动新 Worker 进程（使用新配置）
        │
        ├── 向旧 Worker 进程发送 SIGQUIT（优雅停止）
        │
        └── 旧 Worker 处理完当前请求后退出
```

> **设计洞察**：热重载期间，新旧 Worker 进程**同时存在**，共享同一组监听套接字（通过 `SO_REUSEPORT` 或 accept mutex 协调）。这保证了服务的零中断。

### 9.5 进程间通信

Master 和 Worker 之间通过 **Unix Domain Socket（socketpair）** 通信：

```c
// src/os/unix/ngx_channel.h
typedef struct {
    ngx_uint_t  command;    // 命令类型（NGX_CMD_OPEN_CHANNEL 等）
    ngx_pid_t   pid;        // 目标进程 PID
    ngx_int_t   slot;       // 进程槽位
    ngx_fd_t    fd;         // 传递的文件描述符（用于传递监听 socket）
} ngx_channel_t;
```

> **小结**：Master-Worker 架构实现了配置管理与请求处理的职责分离。Master 进程永不处理请求，只管理子进程生命周期；Worker 进程专注于事件循环，互不干扰。热重载时新旧 Worker 并存，保证服务零中断。

---

## 10. 事件驱动引擎（ngx_event）

### 10.1 事件抽象层

Nginx 通过 `ngx_event_actions_t` 抽象了不同平台的 I/O 多路复用接口：

```c
// src/event/ngx_event.h:118
typedef struct {
    ngx_int_t  (*add)(ngx_event_t *ev, ngx_int_t event, ngx_uint_t flags);
    ngx_int_t  (*del)(ngx_event_t *ev, ngx_int_t event, ngx_uint_t flags);
    ngx_int_t  (*enable)(ngx_event_t *ev, ngx_int_t event, ngx_uint_t flags);
    ngx_int_t  (*disable)(ngx_event_t *ev, ngx_int_t event, ngx_uint_t flags);
    ngx_int_t  (*add_conn)(ngx_connection_t *c);
    ngx_int_t  (*del_conn)(ngx_connection_t *c, ngx_uint_t flags);
    ngx_int_t  (*notify)(ngx_event_handler_pt handler);
    ngx_int_t  (*process_events)(ngx_cycle_t *cycle, ngx_msec_t timer, ngx_uint_t flags);
    ngx_int_t  (*init)(ngx_cycle_t *cycle, ngx_msec_t timer);
    void       (*done)(ngx_cycle_t *cycle);
} ngx_event_actions_t;

// 全局事件操作表（运行时指向具体实现，如 epoll）
extern ngx_event_actions_t   ngx_event_actions;

// 便捷宏（直接调用全局操作表）
#define ngx_add_event        ngx_event_actions.add
#define ngx_del_event        ngx_event_actions.del
#define ngx_process_events   ngx_event_actions.process_events
```

### 10.2 事件结构体

```c
// src/event/ngx_event.h:26
struct ngx_event_s {
    void            *data;          // 关联的连接对象（ngx_connection_t *）

    // 状态标志位（使用位域节省内存）
    unsigned         write:1;       // 是写事件（否则是读事件）
    unsigned         accept:1;      // 是 accept 事件
    unsigned         instance:1;    // 用于检测过期事件（stale event）
    unsigned         active:1;      // 已注册到内核
    unsigned         disabled:1;    // 已禁用
    unsigned         ready:1;       // 事件就绪（可以读/写）
    unsigned         eof:1;         // 对端关闭连接
    unsigned         error:1;       // 发生错误
    unsigned         timedout:1;    // 已超时
    unsigned         timer_set:1;   // 已设置定时器
    unsigned         posted:1;      // 已加入延迟处理队列

    int              available;     // 可读字节数（-1 表示未知）

    ngx_event_handler_pt  handler;  // 事件处理回调函数

    ngx_rbtree_node_t   timer;      // 定时器节点（嵌入红黑树）
    ngx_queue_t      queue;         // 延迟队列节点
};
```

### 10.3 epoll 实现详解

```c
// src/event/modules/ngx_epoll_module.c:289
static ngx_int_t
ngx_epoll_init(ngx_cycle_t *cycle, ngx_msec_t timer)
{
    // 创建 epoll 实例
    ep = epoll_create(cycle->connection_n / 2);

    // 分配事件数组（用于 epoll_wait 返回结果）
    event_list = ngx_alloc(sizeof(struct epoll_event) * epcf->events, cycle->log);

    // 设置全局事件操作表为 epoll 实现
    ngx_event_actions = ngx_epoll_module_ctx.actions;

    // 设置事件标志（ET 模式）
    ngx_event_flags = NGX_USE_CLEAR_EVENT  // ET（边缘触发）
                      | NGX_USE_GREEDY_EVENT
                      | NGX_USE_EPOLL_EVENT;
    return NGX_OK;
}

// 核心事件处理循环
static ngx_int_t
ngx_epoll_process_events(ngx_cycle_t *cycle, ngx_msec_t timer, ngx_uint_t flags)
{
    // 等待事件（timer 是最近定时器的超时时间）
    events = epoll_wait(ep, event_list, (int) nevents, timer);

    // 更新时间缓存
    if (flags & NGX_UPDATE_TIME || ngx_event_timer_alarm) {
        ngx_time_update();
    }

    // 遍历就绪事件
    for (i = 0; i < events; i++) {
        c = event_list[i].data.ptr;

        // 检测过期事件（stale event）
        // 技巧：将 instance 位编码到指针的最低位
        instance = (uintptr_t) c & 1;
        c = (ngx_connection_t *) ((uintptr_t) c & (uintptr_t) ~1);

        rev = c->read;
        if (c->fd == -1 || rev->instance != instance) {
            // 过期事件（fd 已关闭并重新分配），跳过
            continue;
        }

        revents = event_list[i].events;

        // 处理读事件
        if ((revents & EPOLLIN) && rev->active) {
            rev->ready = 1;
            if (flags & NGX_POST_EVENTS) {
                // 延迟处理（先处理 accept 事件，再处理普通读事件）
                ngx_post_event(rev, rev->accept ? &ngx_posted_accept_events
                                                : &ngx_posted_events);
            } else {
                rev->handler(rev);  // 立即处理
            }
        }

        // 处理写事件
        wev = c->write;
        if ((revents & EPOLLOUT) && wev->active) {
            wev->ready = 1;
            if (flags & NGX_POST_EVENTS) {
                ngx_post_event(wev, &ngx_posted_events);
            } else {
                wev->handler(wev);
            }
        }
    }
    return NGX_OK;
}
```

> **设计洞察**：`instance` 位是一个精妙的 ABA 问题解决方案。
> 当一个 fd 关闭后，内核可能将同一个 fd 号分配给新连接。如果 epoll 中还有旧 fd 的事件，就会错误地触发新连接的处理。
> nginx 通过在 `epoll_data.ptr` 的最低位存储 `instance` 标志（每次关闭连接时翻转），来检测这种过期事件。

### 10.4 定时器机制

```c
// src/event/ngx_event_timer.h
// 添加定时器（timer 毫秒后超时）
#define ngx_add_timer(ev, timer)    ngx_event_add_timer(ev, timer)

// 内部实现：将事件插入红黑树
static ngx_inline void
ngx_event_add_timer(ngx_event_t *ev, ngx_msec_t timer)
{
    ngx_msec_t      key;
    key = (ngx_msec_t) ngx_current_msec + timer;  // 绝对超时时间
    ev->timer.key = key;
    ngx_rbtree_insert(&ngx_event_timer_rbtree, &ev->timer);
    ev->timer_set = 1;
}
```

事件循环中，`epoll_wait` 的超时时间 = 红黑树中最小 key（最近超时时间）- 当前时间。

> **小结**：事件驱动引擎是 nginx 高并发的核心。epoll 的边缘触发模式、`instance` 位的过期事件检测、红黑树定时器——这三个机制共同保证了事件循环的高效和正确性。

---

## 11. 连接管理（ngx_connection）

### 11.1 连接池

Nginx 在 Worker 进程启动时，一次性分配 `worker_connections` 个连接对象，形成**连接池**：

```c
// src/core/ngx_cycle.h 中的 cycle 字段
ngx_connection_t         *connections;   // 连接池数组
ngx_event_t              *read_events;   // 读事件数组（与 connections 一一对应）
ngx_event_t              *write_events;  // 写事件数组
ngx_connection_t         *free_connections; // 空闲连接链表（通过 data 字段串联）
```

**获取连接**：

```c
// src/core/ngx_connection.c
ngx_connection_t *
ngx_get_connection(ngx_socket_t s, ngx_log_t *log)
{
    // 从空闲链表取一个连接
    c = ngx_cycle->free_connections;
    ngx_cycle->free_connections = c->data;  // data 字段复用为链表 next 指针
    ngx_cycle->free_connection_n--;

    // 绑定读写事件
    rev = c->read;
    wev = c->write;

    // 将 fd 与连接绑定
    c->fd = s;

    return c;
}
```

### 11.2 连接结构体

```c
// src/core/ngx_connection.h:117
struct ngx_connection_s {
    void               *data;           // 上层协议数据（如 ngx_http_request_t *）
    ngx_event_t        *read;           // 读事件
    ngx_event_t        *write;          // 写事件

    ngx_socket_t        fd;             // 文件描述符

    // I/O 函数指针（可被 SSL 等替换）
    ngx_recv_pt         recv;           // 接收数据
    ngx_send_pt         send;           // 发送数据
    ngx_recv_chain_pt   recv_chain;     // 链式接收
    ngx_send_chain_pt   send_chain;     // 链式发送

    ngx_listening_t    *listening;      // 关联的监听套接字

    off_t               sent;           // 已发送字节数

    ngx_log_t          *log;            // 日志
    ngx_pool_t         *pool;           // 连接级内存池

    struct sockaddr    *sockaddr;       // 客户端地址
    ngx_str_t           addr_text;      // 客户端地址文本

    // SSL、QUIC 扩展
    ngx_ssl_connection_t  *ssl;

    // 状态标志
    unsigned            timedout:1;
    unsigned            error:1;
    unsigned            idle:1;         // 空闲连接（keepalive 等待中）
    unsigned            reusable:1;     // 可被复用（当连接数不足时）
    unsigned            sendfile:1;     // 使用 sendfile
    unsigned            tcp_nodelay:2;  // TCP_NODELAY 状态
};
```

### 11.3 Accept 互斥锁

多个 Worker 进程同时监听同一端口，会产生**惊群问题**（一个连接到来，所有 Worker 都被唤醒，但只有一个能 accept）。

Nginx 的解决方案：**accept mutex**（接受互斥锁）

```c
// 每次事件循环开始时，尝试获取 accept mutex
ngx_int_t
ngx_trylock_accept_mutex(ngx_cycle_t *cycle)
{
    if (ngx_shmtx_trylock(&ngx_accept_mutex)) {
        // 获取到锁：将监听 fd 加入 epoll
        ngx_enable_accept_events(cycle);
        ngx_accept_mutex_held = 1;
        return NGX_OK;
    }

    // 没获取到锁：从 epoll 中移除监听 fd（不参与 accept）
    if (ngx_accept_mutex_held) {
        ngx_disable_accept_events(cycle);
        ngx_accept_mutex_held = 0;
    }
    return NGX_OK;
}
```

> **注意**：Linux 3.9+ 支持 `SO_REUSEPORT`，允许多个进程绑定同一端口，内核负责负载均衡，彻底解决惊群问题。nginx 通过 `reuseport` 指令启用此特性，此时不再需要 accept mutex。

> **小结**：连接池预分配避免了频繁的内存分配，accept mutex 解决了多 Worker 的惊群问题，`SO_REUSEPORT` 则是更现代的解决方案。理解连接管理是理解 nginx 并发模型的最后一块拼图。

---

## 12. HTTP 请求处理流水线

> **说明**：HTTP 请求处理的 11 个阶段已在 [6.6 节](#66-http-模块如何起作用phase-handler-机制) 详细介绍，本章重点关注请求对象的数据结构和状态机驱动机制。

### 12.1 ngx_http_request_t
这是 HTTP 处理的核心结构体，贯穿整个请求生命周期：

```c
// src/http/ngx_http_request.h:300（简化版）
struct ngx_http_request_s {
    uint32_t                          signature;    // "HTTP" 魔数，用于调试

    ngx_connection_t                 *connection;   // 底层 TCP 连接

    // 各级配置上下文
    void                            **ctx;          // 模块私有数据（每模块一个槽）
    void                            **main_conf;    // http {} 级配置
    void                            **srv_conf;     // server {} 级配置
    void                            **loc_conf;     // location {} 级配置

    // 事件处理回调（状态机驱动）
    ngx_http_event_handler_pt         read_event_handler;
    ngx_http_event_handler_pt         write_event_handler;

    ngx_pool_t                       *pool;         // 请求级内存池

    // 请求行解析结果
    ngx_uint_t                        method;       // GET/POST/... 位标志
    ngx_uint_t                        http_version; // HTTP/1.0=1000, HTTP/1.1=1001
    ngx_str_t                         request_line; // 完整请求行
    ngx_str_t                         uri;          // 请求 URI
    ngx_str_t                         args;         // 查询参数
    ngx_str_t                         exten;        // 文件扩展名

    // 请求头和响应头
    ngx_http_headers_in_t             headers_in;   // 请求头
    ngx_http_headers_out_t            headers_out;  // 响应头

    // 请求体
    ngx_http_request_body_t          *request_body;

    // 子请求支持
    ngx_http_request_t               *main;         // 主请求（子请求时指向主请求）
    ngx_http_request_t               *parent;       // 父请求

    // 阶段处理
    ngx_int_t                         phase_handler;// 当前处理阶段的 handler 索引

    // 状态标志（大量位域）
    unsigned                          keepalive:1;
    unsigned                          header_sent:1;
    unsigned                          done:1;
    // ... 更多标志
};
```

### 12.2 请求处理状态机

HTTP 请求处理是一个**事件驱动的状态机**：

```
客户端连接到达
  │
  ▼
ngx_http_init_connection()
  │ 设置 read_event_handler = ngx_http_wait_request_handler
  ▼
等待数据到来（epoll 触发）
  │
  ▼
ngx_http_wait_request_handler()
  │ 读取请求数据
  │ 设置 read_event_handler = ngx_http_process_request_line
  ▼
ngx_http_process_request_line()
  │ 解析请求行（GET /path HTTP/1.1）
  │ 成功后设置 read_event_handler = ngx_http_process_request_headers
  ▼
ngx_http_process_request_headers()
  │ 解析所有请求头
  │ 完成后调用 ngx_http_process_request()
  ▼
ngx_http_process_request()
  │ 进入阶段处理引擎
  ▼
ngx_http_core_run_phases()
  │ 依次执行各阶段的 handler
  ▼
CONTENT_PHASE handler（如 ngx_http_proxy_handler）
  │ 生成响应
  ▼
过滤器链（Filter Chain）
  │ gzip → header_filter → write_filter
  ▼
发送响应给客户端
```

> **小结**：HTTP 请求处理是一个事件驱动的状态机。每次 epoll 触发都推进状态机向前一步，直到响应发送完毕。`ngx_http_request_t` 贯穿整个请求生命周期，是模块间共享状态的核心载体。

---

## 13. 过滤器链（Filter Chain）

### 13.1 过滤器的作用

过滤器（Filter）是对响应内容进行处理的模块，形成一个**链式处理管道**。

两类过滤器：
- **Header Filter**：处理响应头（`ngx_http_send_header`）
- **Body Filter**：处理响应体（`ngx_http_output_filter`）

### 13.2 过滤器链的构建

过滤器链在配置解析阶段通过**函数指针链**构建：

```c
// 每个过滤器模块在 postconfiguration 中注册自己
// 通过保存上一个过滤器的指针，形成链表

// 示例：gzip 过滤器注册
static ngx_int_t
ngx_http_gzip_filter_init(ngx_conf_t *cf)
{
    // 将自己插入到 header filter 链的头部
    ngx_http_next_header_filter = ngx_http_top_header_filter;
    ngx_http_top_header_filter = ngx_http_gzip_header_filter;

    // 将自己插入到 body filter 链的头部
    ngx_http_next_body_filter = ngx_http_top_body_filter;
    ngx_http_top_body_filter = ngx_http_gzip_body_filter;

    return NGX_OK;
}
```

**过滤器链（从外到内）**：

```
ngx_http_top_header_filter
  → not_modified_filter
  → range_header_filter
  → gzip_header_filter
  → headers_filter（添加 Server、Date 等头）
  → chunked_filter
  → header_filter（最终发送响应头）

ngx_http_top_body_filter
  → copy_filter（处理 sendfile）
  → range_body_filter
  → gzip_body_filter
  → chunked_body_filter
  → write_filter（最终写入 socket）
```

> **小结**：过滤器链是 nginx 响应处理的“流水线工厂”。每个过滤器模块在 `postconfiguration` 中把自己插入链表头部，后注册的在外层先执行。理解这个机制是开发响应处理模块（如压缩、加密、内容替换）的基础。

---

## 14. Upstream 反向代理机制

> Upstream 模块是 nginx 作为反向代理服务器的核心。proxy_pass、fastcgi_pass、grpc_pass 等指令背后都是这一套框架在运作。

`ngx_http_upstream_t` 是 nginx 反向代理的核心，proxy_pass、fastcgi、uwsgi 等模块都基于它实现。

```c
// src/http/ngx_http_upstream.h（简化版）
struct ngx_http_upstream_s {
    ngx_http_upstream_handler_pt   read_event_handler;
    ngx_http_upstream_handler_pt   write_event_handler;

    ngx_peer_connection_t          peer;        // 到后端的连接

    ngx_http_upstream_conf_t      *conf;        // upstream 配置

    // 回调函数（由具体模块实现）
    ngx_int_t                    (*create_request)(ngx_http_request_t *r);
    ngx_int_t                    (*reinit_request)(ngx_http_request_t *r);
    ngx_int_t                    (*process_header)(ngx_http_request_t *r);
    void                         (*abort_request)(ngx_http_request_t *r);
    void                         (*finalize_request)(ngx_http_request_t *r, ngx_int_t rc);

    ngx_buf_t                     *header_in;   // 后端响应头缓冲区
    ngx_http_upstream_headers_in_t headers_in;  // 解析后的后端响应头

    ngx_event_pipe_t              *pipe;        // 数据管道（用于缓冲/流式传输）

    ngx_chain_t                   *request_bufs;// 发往后端的请求数据

    unsigned                       buffering:1; // 是否缓冲后端响应
    unsigned                       cacheable:1; // 是否可缓存
};
```

### 14.2 反向代理流程

```
ngx_http_proxy_handler(r)
  │
  ├── 创建 upstream 对象
  ├── 设置回调（create_request/process_header 等）
  │
  └── ngx_http_upstream_init(r)
        │
        ├── 解析后端地址（DNS 解析或直接 IP）
        │
        ├── ngx_http_upstream_connect(r, u, peer)
        │     │
        │     └── 建立到后端的 TCP 连接（非阻塞）
        │
        ├── 连接成功后：ngx_http_upstream_send_request()
        │     │
        │     └── 将客户端请求转发给后端
        │
        ├── 后端响应到来：ngx_http_upstream_process_header()
        │     │
        │     └── 解析后端响应头
        │
        └── ngx_http_upstream_send_response()
              │
              └── 将后端响应转发给客户端（通过过滤器链）
```

### 14.3 负载均衡

Nginx 内置多种负载均衡算法：

| 算法 | 模块 | 说明 |
|------|------|------|
| 轮询（Round Robin） | `ngx_http_upstream_round_robin` | 默认，按顺序分配 |
| 加权轮询 | `ngx_http_upstream_round_robin` | `weight` 参数 |
| IP Hash | `ngx_http_upstream_ip_hash_module` | 同一 IP 固定到同一后端 |
| 最少连接 | `ngx_http_upstream_least_conn_module` | 分配给连接数最少的后端 |
| 一致性哈希 | `ngx_http_upstream_hash_module` | 自定义 key 的哈希 |

> **小结**：Upstream 是 nginx 最复杂的模块（190KB 源码）。它抽象了与后端通信的全部细节：连接建立、请求转发、响应解析、错误重试、负载均衡。proxy_pass、fastcgi、grpc 等模块都是在它的基础上实现的。

---

## 15. 日志系统（ngx_log）

> 日志系统看似简单，却包含了多个精妙的工程设计决策。理解它对于调试 nginx 问题至关重要。

### 15.1 日志级别
```c
// src/core/ngx_log.h
#define NGX_LOG_STDERR            0   // 直接输出到 stderr
#define NGX_LOG_EMERG             1   // 紧急（系统不可用）
#define NGX_LOG_ALERT             2   // 警报（需要立即处理）
#define NGX_LOG_CRIT              3   // 严重错误
#define NGX_LOG_ERR               4   // 错误
#define NGX_LOG_WARN              5   // 警告
#define NGX_LOG_NOTICE            6   // 通知
#define NGX_LOG_INFO              7   // 信息
#define NGX_LOG_DEBUG             8   // 调试

// 调试子级别（需要 --with-debug 编译）
#define NGX_LOG_DEBUG_CORE        0x010  // 核心模块调试
#define NGX_LOG_DEBUG_ALLOC       0x020  // 内存分配调试
#define NGX_LOG_DEBUG_EVENT       0x080  // 事件模块调试
#define NGX_LOG_DEBUG_HTTP        0x100  // HTTP 模块调试
```

### 15.2 日志使用

```c
// 普通日志
ngx_log_error(NGX_LOG_ERR, log, ngx_errno, "connect() to %V failed", &addr);

// 调试日志（非 DEBUG 编译时被宏替换为空，零开销）
ngx_log_debug2(NGX_LOG_DEBUG_HTTP, r->connection->log, 0,
               "http process request: %V %V", &r->method_name, &r->uri);
```

### 15.3 ngx_log_t 结构

```c
// src/core/ngx_log.h:47
struct ngx_log_s {
    ngx_uint_t           log_level;     // 当前日志级别
    ngx_open_file_t     *file;          // 日志文件
    ngx_atomic_uint_t    connection;    // 当前连接号（用于日志前缀）
    ngx_log_handler_pt   handler;       // 自定义日志前缀生成函数
    void                *data;          // handler 的参数
    char                *action;        // 当前操作描述（出错时显示）
    ngx_log_t           *next;          // 下一个日志对象（支持多目标）
};
```

> **小结**：nginx 日志系统设计精妙——调试日志在非 DEBUG 编译时被宏替换为空操作，生产环境零开销；多目标日志链支持同时写入多个文件。

---

## 16. 调试与诊断

### 16.1 编译调试版本

```bash
# 编译带调试信息的版本
./configure --with-debug --prefix=/tmp/nginx-debug
make && make install

# 启用所有调试日志
# 在 nginx.conf 中：
error_log /tmp/nginx-debug.log debug;
```

### 16.2 GDB 调试

```bash
# 以单进程模式启动（方便调试）
# nginx.conf 中添加：
# master_process off;
# daemon off;

# 启动 nginx
/tmp/nginx-debug/sbin/nginx -c /tmp/nginx-debug/conf/nginx.conf

# 另一个终端 attach
gdb -p $(cat /tmp/nginx-debug/logs/nginx.pid)

# 常用断点
(gdb) b ngx_http_process_request
(gdb) b ngx_http_core_run_phases
(gdb) b ngx_epoll_process_events
(gdb) b ngx_palloc

# 查看请求信息
(gdb) p r->uri
(gdb) p r->method_name
(gdb) p r->headers_in.host->value
```

### 16.3 关键观测点

| 断点位置 | 观测目标 |
|----------|----------|
| `ngx_http_process_request` | 请求开始处理，查看 `r->uri`、`r->method` |
| `ngx_http_core_find_config_phase` | location 匹配过程 |
| `ngx_http_upstream_connect` | 反向代理连接后端 |
| `ngx_epoll_process_events` | 事件循环，查看 `events` 数量 |
| `ngx_palloc_block` | 内存池扩容，查看内存使用 |
| `ngx_log_error_core` | 所有错误日志 |

### 16.4 常用诊断命令

```bash
# 查看 nginx 进程状态
ps aux | grep nginx

# 查看连接数
ss -s
netstat -an | grep :80 | wc -l

# 实时查看错误日志
tail -f /var/log/nginx/error.log

# 测试配置文件
nginx -t

# 查看编译参数
nginx -V

# 热重载
nginx -s reload

# 优雅停止
nginx -s quit

# 快速停止
nginx -s stop

# 重新打开日志文件（日志切割后使用）
nginx -s reopen
```

### 16.5 stub_status 模块

```nginx
# nginx.conf
location /nginx_status {
    stub_status;
    allow 127.0.0.1;
    deny all;
}
```

```bash
curl http://localhost/nginx_status
# 输出：
# Active connections: 291
# server accepts handled requests
#  16630948 16630948 31070465
# Reading: 6 Writing: 179 Waiting: 106
```

| 字段 | 说明 |
|------|------|
| Active connections | 当前活跃连接数 |
| accepts | 总接受连接数 |
| handled | 总处理连接数（通常等于 accepts） |
| requests | 总请求数 |
| Reading | 正在读取请求头的连接数 |
| Writing | 正在发送响应的连接数 |
| Waiting | keepalive 等待中的连接数 |

---

## 17. 设计洞察汇总

> 本章汇总全文中散落的设计洞察，帮助读者从更高视角理解 nginx 的架构哲学。

### 17.1 架构设计亮点

1. **事件驱动 + 非阻塞 I/O**：单个 Worker 进程可处理数万并发连接，内存占用极低（每个连接约 1KB）。

2. **内存池的生命周期绑定**：请求级内存池与请求生命周期完全绑定，彻底消除内存泄漏风险，同时提升分配速度。

3. **模块化 + 钩子机制**：所有功能模块化，通过阶段钩子（phase handler）和过滤器链（filter chain）实现功能的无侵入扩展。

4. **热重载零中断**：新旧 Worker 进程并存，通过 accept mutex 或 SO_REUSEPORT 协调，实现配置更新零停机。

5. **过期事件检测**：通过 `instance` 位解决 epoll 中的 ABA 问题，避免处理已关闭 fd 的过期事件。

### 17.2 性能优化技巧

| 技巧 | 位置 | 说明 |
|------|------|------|
| 内存对齐 | `ngx_palloc_small` | 按 CPU 缓存行对齐，减少 cache miss |
| 位域压缩 | `ngx_event_s`、`ngx_connection_s` | 大量状态标志用位域存储，节省内存 |
| 延迟处理 | `ngx_posted_events` | accept 事件优先处理，普通 I/O 事件延迟，减少锁竞争 |
| 时间缓存 | `ngx_time_update()` | 缓存当前时间，避免频繁 gettimeofday 系统调用 |
| sendfile | `ngx_linux_sendfile_chain.c` | 零拷贝发送文件，减少内核/用户空间数据复制 |
| 连接复用 | `reusable_connections_queue` | 连接数不足时，复用 keepalive 空闲连接 |

### 17.3 常见设计模式

| 模式 | 应用场景 |
|------|----------|
| **策略模式** | `ngx_event_actions_t`：运行时切换 epoll/kqueue/select |
| **责任链模式** | 过滤器链（Filter Chain）：响应头/体的链式处理 |
| **模板方法模式** | `ngx_http_upstream_t`：定义代理框架，具体协议实现回调 |
| **观察者模式** | 阶段处理引擎（Phase Engine）：模块注册到特定阶段 |
| **对象池模式** | 连接池（Connection Pool）：预分配，避免频繁创建销毁 |
| **侵入式链表** | `ngx_queue_t`：节点嵌入宿主结构体，避免额外内存分配 |

### 17.4 关键设计决策表

| 决策 | 选择 | 原因 |
|------|------|------|
| 并发模型 | 事件驱动 | C10K 问题的最优解，内存效率极高 |
| 进程 vs 线程 | 多进程 | 进程间隔离好，崩溃不影响其他 Worker |
| 内存管理 | 内存池 | 请求结束批量释放，无泄漏，分配快 |
| 字符串 | `{len, data}` | 支持二进制，O(1) 长度，避免 strlen |
| 配置解析 | 递归下降 | 简单直接，支持 include 嵌套 |
| 定时器 | 红黑树 | O(log n) 插入/删除，O(1) 获取最小值 |

---

## 18. 学习路径建议

### 18.1 初学者路径（2-4 周）

**目标**：理解 nginx 的基本工作原理，能够阅读简单模块的代码。

1. **第 1 周**：阅读 `src/core/ngx_palloc.h/.c`（内存池），理解 nginx 的内存管理哲学
2. **第 2 周**：阅读 `src/core/ngx_module.h` 和 `src/core/nginx.c`（启动流程）
3. **第 3 周**：阅读 `src/event/ngx_event.h` 和 `src/event/modules/ngx_epoll_module.c`
4. **第 4 周**：阅读 `src/http/ngx_http_request.h` 和 HTTP 处理阶段

**推荐资源**：
- 《深入理解 Nginx》（陶辉著）
- nginx 官方文档：https://nginx.org/en/docs/dev/development_guide.html

### 18.2 高级开发者路径（4-8 周）

**目标**：能够开发 nginx 模块，深入理解性能优化原理。

1. **第 1-2 周**：深入阅读 `src/core/ngx_cycle.c`（运行时核心）和 `src/os/unix/ngx_process_cycle.c`（进程管理）
2. **第 3-4 周**：阅读 `src/http/ngx_http_upstream.c`（反向代理，最复杂的文件）
3. **第 5-6 周**：阅读 `src/http/ngx_http_core_module.c`（location 匹配算法）
4. **第 7-8 周**：参考 [第 6.4 节](#64-如何新增一个-http-模块完整步骤) 的完整示例，编写并编译运行自己的第一个 HTTP 模块

> 💡 **编写第一个模块**：完整的模块开发示例（含配置指令定义、handler 注册、响应生成全流程）已在 **第 6.4 节** 详细展示，请直接参考该节内容，此处不再重复。

---

## 19. 源码文件索引

### 19.1 关键函数定位表

| 函数/结构 | 文件 | 行号（约） | 说明 |
|-----------|------|-----------|------|
| `main()` | `src/core/nginx.c` | 182 | 程序入口 |
| `ngx_init_cycle()` | `src/core/ngx_cycle.c` | 37 | 运行时初始化 |
| `ngx_master_process_cycle()` | `src/os/unix/ngx_process_cycle.c` | 63 | Master 主循环 |
| `ngx_worker_process_cycle()` | `src/os/unix/ngx_process_cycle.c` | 约 400 | Worker 主循环 |
| `ngx_process_events_and_timers()` | `src/event/ngx_event.c` | 约 200 | 事件+定时器处理 |
| `ngx_epoll_process_events()` | `src/event/modules/ngx_epoll_module.c` | 约 700 | epoll 事件处理 |
| `ngx_create_pool()` | `src/core/ngx_palloc.c` | 15 | 创建内存池 |
| `ngx_palloc()` | `src/core/ngx_palloc.c` | 96 | 内存分配 |
| `ngx_http_process_request()` | `src/http/ngx_http_request.c` | 约 1900 | HTTP 请求处理入口 |
| `ngx_http_core_run_phases()` | `src/http/ngx_http_core_module.c` | 约 900 | 阶段处理引擎 |
| `ngx_http_upstream_init()` | `src/http/ngx_http_upstream.c` | 约 500 | 反向代理初始化 |
| `ngx_conf_parse()` | `src/core/ngx_conf_file.c` | 约 300 | 配置文件解析 |
| `ngx_get_connection()` | `src/core/ngx_connection.c` | 约 1000 | 获取连接对象 |
| `ngx_trylock_accept_mutex()` | `src/event/ngx_event_accept.c` | 约 300 | accept 互斥锁 |

### 19.2 关键数据结构定位表

| 结构体 | 文件 | 说明 |
|--------|------|------|
| `ngx_cycle_t` | `src/core/ngx_cycle.h:34` | 运行时核心 |
| `ngx_module_t` | `src/core/ngx_module.h:175` | 模块定义 |
| `ngx_pool_t` | `src/core/ngx_palloc.h:55` | 内存池 |
| `ngx_event_t` | `src/event/ngx_event.h:26` | 事件对象 |
| `ngx_connection_t` | `src/core/ngx_connection.h:117` | 连接对象 |
| `ngx_http_request_t` | `src/http/ngx_http_request.h:300` | HTTP 请求 |
| `ngx_http_upstream_t` | `src/http/ngx_http_upstream.h` | 反向代理 |
| `ngx_command_t` | `src/core/ngx_conf_file.h:72` | 配置指令 |
| `ngx_str_t` | `src/core/ngx_string.h:14` | 字符串 |
| `ngx_event_actions_t` | `src/event/ngx_event.h:118` | 事件操作表 |

---

## 20. 附录：常见陷阱与最佳实践

### 20.1 常见错误

**错误 1：直接使用 ngx_str_t.data 作为 C 字符串**

```c
// ❌ 错误：data 不一定以 '\0' 结尾
printf("%s", r->uri.data);

// ✅ 正确：使用 %.*s 格式化
printf("%.*s", (int)r->uri.len, r->uri.data);

// ✅ 或者使用 ngx_log_error
ngx_log_error(NGX_LOG_INFO, log, 0, "uri: %V", &r->uri);
// %V 格式符专门用于 ngx_str_t
```

**错误 2：在内存池中释放小块内存**

```c
// ❌ 错误：小块内存无法单独释放
void *p = ngx_palloc(pool, 100);
ngx_pfree(pool, p);  // 对小块内存无效！

// ✅ 正确：依赖内存池整体销毁，或使用 cleanup 机制
// 如果必须提前释放，使用 ngx_palloc_large（超过 pool->max 的分配）
void *p = ngx_palloc(pool, pool->max + 1);  // 强制走大块分配路径
ngx_pfree(pool, p);  // 大块内存可以单独释放
```

**错误 3：在 Worker 进程中使用阻塞操作**

```c
// ❌ 错误：阻塞整个 Worker 进程
int fd = open("/slow/file", O_RDONLY);
read(fd, buf, size);  // 如果文件在 NFS 上，可能阻塞数秒

// ✅ 正确：使用线程池（thread pool）处理阻塞操作
// 或使用 AIO（异步 I/O）
```

**错误 4：忘记处理 NGX_AGAIN 返回值**

```c
// ❌ 错误：忽略 NGX_AGAIN
n = c->recv(c, buf, size);
if (n < 0) { /* 错误处理 */ }
// 忘记处理 n == NGX_AGAIN（数据未就绪，需要等待下次事件）

// ✅ 正确：
n = c->recv(c, buf, size);
if (n == NGX_AGAIN) {
    // 注册读事件，等待数据到来
    ngx_add_event(c->read, NGX_READ_EVENT, 0);
    return NGX_AGAIN;
}
if (n < 0) { /* 错误处理 */ }
```

**错误 5：在 location 配置中使用 main 级别的配置**

```c
// ❌ 错误：在 location handler 中使用错误的配置级别
ngx_http_core_main_conf_t *cmcf = ngx_http_get_module_main_conf(r, ngx_http_core_module);
// 应该使用 loc_conf，而不是 main_conf

// ✅ 正确：根据需要选择正确的配置级别
ngx_http_core_loc_conf_t *clcf = ngx_http_get_module_loc_conf(r, ngx_http_core_module);
```

### 20.2 最佳实践

1. **始终检查内存分配返回值**：`ngx_palloc` 可能返回 NULL，必须检查。

2. **使用 ngx_log_debug 而非 printf**：调试日志在非 DEBUG 编译时会被优化掉，不影响生产性能。

3. **利用 cleanup 机制管理资源**：文件描述符、外部库资源等，通过 `ngx_pool_cleanup_add` 注册清理回调，确保资源释放。

4. **理解 NGX_AGAIN 的语义**：在非阻塞 I/O 中，`NGX_AGAIN` 表示"操作未完成，需要等待事件"，不是错误。

5. **配置合并要完整**：实现 `merge_loc_conf` 时，必须对所有字段调用 `ngx_conf_merge_*` 宏，确保配置继承正确。

### 20.3 术语表

| 术语 | 说明 |
|------|------|
| **cycle** | nginx 运行时实例，包含所有运行时状态 |
| **pool** | 内存池，按生命周期批量管理内存 |
| **upstream** | 后端服务器，反向代理的目标 |
| **phase** | HTTP 请求处理阶段（共 11 个） |
| **filter** | 响应过滤器，对响应头/体进行处理 |
| **handler** | 内容处理器，生成响应内容 |
| **event** | I/O 事件或定时器事件 |
| **connection** | TCP 连接对象 |
| **listening** | 监听套接字 |
| **module** | nginx 功能模块 |
| **ctx** | 模块上下文（context），模块特定的数据 |
| **conf** | 配置结构体 |
| **ET/LT** | 边缘触发/水平触发（epoll 的两种工作模式） |
| **sendfile** | 零拷贝文件发送系统调用 |
| **keepalive** | HTTP 持久连接 |
| **subrequest** | 子请求（SSI、auth_request 等使用） |

---

## 21. 附录：内置模块大全

nginx 的所有功能均以模块形式实现。以下按类型对源码中的内置模块进行系统梳理，帮助读者快速定位所需功能对应的源文件。

> **编译说明**：标注 `⚙️ 需编译选项` 的模块默认不编译，需在 `./configure` 时显式添加对应的 `--with-xxx` 选项。

---

### 21.1 HTTP 功能模块（Content Handler）

这类模块在 `NGX_HTTP_CONTENT_PHASE` 阶段生成响应内容，是最常用的一类模块。

| 模块名 | 源文件 | 配置指令 | 功能说明 |
|--------|--------|----------|----------|
| `ngx_http_static_module` | `src/http/ngx_http_static.c` | （内置，无独立指令） | **静态文件服务**。处理 `root`/`alias` 指向的本地文件，是最基础的内容模块 |
| `ngx_http_index_module` | `src/http/modules/ngx_http_index_module.c` | `index` | **目录索引文件**。当请求以 `/` 结尾时，尝试返回 `index.html` 等索引文件 |
| `ngx_http_autoindex_module` | `src/http/modules/ngx_http_autoindex_module.c` | `autoindex` | **目录列表**。当没有索引文件时，自动生成目录浏览页面（HTML/JSON/XML 格式） |
| `ngx_http_random_index_module` | `src/http/modules/ngx_http_random_index_module.c` | `random_index` | **随机索引**。从目录中随机选择一个文件作为索引页 ⚙️ `--with-http_random_index_module` |
| `ngx_http_proxy_module` | `src/http/modules/ngx_http_proxy_module.c` | `proxy_pass` | **HTTP 反向代理**。将请求转发给后端 HTTP/HTTPS 服务器，支持缓存、负载均衡 |
| `ngx_http_proxy_v2_module` | `src/http/modules/ngx_http_proxy_v2_module.c` | `proxy_pass`（HTTP/2 后端） | **HTTP/2 后端代理**。支持以 HTTP/2 协议连接后端服务器 ⚙️ `--with-http_v2_module` |
| `ngx_http_fastcgi_module` | `src/http/modules/ngx_http_fastcgi_module.c` | `fastcgi_pass` | **FastCGI 代理**。与 PHP-FPM 等 FastCGI 进程通信，是 PHP 应用的标准接入方式 |
| `ngx_http_uwsgi_module` | `src/http/modules/ngx_http_uwsgi_module.c` | `uwsgi_pass` | **uWSGI 代理**。与 Python uWSGI 服务器通信，是 Django/Flask 的常用接入方式 |
| `ngx_http_scgi_module` | `src/http/modules/ngx_http_scgi_module.c` | `scgi_pass` | **SCGI 代理**。简单通用网关接口协议代理 |
| `ngx_http_grpc_module` | `src/http/modules/ngx_http_grpc_module.c` | `grpc_pass` | **gRPC 代理**。将 HTTP/2 gRPC 请求转发给后端 gRPC 服务 ⚙️ `--with-http_v2_module` |
| `ngx_http_memcached_module` | `src/http/modules/ngx_http_memcached_module.c` | `memcached_pass` | **Memcached 代理**。直接从 Memcached 读取缓存内容作为响应 |
| `ngx_http_empty_gif_module` | `src/http/modules/ngx_http_empty_gif_module.c` | `empty_gif` | **1×1 透明 GIF**。返回一个 1×1 像素的透明 GIF 图片，常用于前端埋点统计 ⚙️ `--with-http_empty_gif_module` |
| `ngx_http_flv_module` | `src/http/modules/ngx_http_flv_module.c` | `flv` | **FLV 伪流媒体**。支持 FLV 视频文件的 `?start=` 参数跳转播放 ⚙️ `--with-http_flv_module` |
| `ngx_http_mp4_module` | `src/http/modules/ngx_http_mp4_module.c` | `mp4` | **MP4 伪流媒体**。支持 MP4/M4V 视频文件的 `?start=` 时间点跳转播放 ⚙️ `--with-http_mp4_module` |
| `ngx_http_dav_module` | `src/http/modules/ngx_http_dav_module.c` | `dav_methods` | **WebDAV 支持**。处理 PUT/DELETE/MKCOL/COPY/MOVE 等 WebDAV 方法 ⚙️ `--with-http_dav_module` |

---

### 21.2 HTTP 访问控制模块

这类模块在 `PREACCESS` 或 `ACCESS` 阶段运行，控制请求是否被允许处理。

| 模块名 | 源文件 | 配置指令 | 功能说明 |
|--------|--------|----------|----------|
| `ngx_http_access_module` | `src/http/modules/ngx_http_access_module.c` | `allow` / `deny` | **IP 黑白名单**。根据客户端 IP 地址允许或拒绝访问，支持 CIDR 格式 |
| `ngx_http_auth_basic_module` | `src/http/modules/ngx_http_auth_basic_module.c` | `auth_basic` | **HTTP Basic 认证**。通过用户名/密码（htpasswd 格式）保护资源 |
| `ngx_http_auth_request_module` | `src/http/modules/ngx_http_auth_request_module.c` | `auth_request` | **子请求认证**。将认证委托给内部子请求，支持 OAuth2/JWT 等外部认证服务 ⚙️ `--with-http_auth_request_module` |
| `ngx_http_limit_conn_module` | `src/http/modules/ngx_http_limit_conn_module.c` | `limit_conn` | **连接数限制**。基于共享内存限制同一 IP 的并发连接数，防止连接耗尽攻击 |
| `ngx_http_limit_req_module` | `src/http/modules/ngx_http_limit_req_module.c` | `limit_req` | **请求速率限制**。基于令牌桶算法限制请求速率（QPS），防止暴力攻击和爬虫 |
| `ngx_http_referer_module` | `src/http/modules/ngx_http_referer_module.c` | `valid_referers` | **防盗链**。检查 `Referer` 请求头，阻止非授权站点引用资源 |
| `ngx_http_secure_link_module` | `src/http/modules/ngx_http_secure_link_module.c` | `secure_link` | **安全链接**。通过 MD5 哈希和过期时间验证 URL 的合法性，防止链接被盗用 ⚙️ `--with-http_secure_link_module` |
| `ngx_http_degradation_module` | `src/http/modules/ngx_http_degradation_module.c` | `degradation` | **降级保护**。当系统内存不足时，返回 204/444 状态码进行服务降级 ⚙️ `--with-http_degradation_module` |

---

### 21.3 HTTP 响应过滤模块（Filter）

过滤模块形成链式管道，对响应头和响应体进行处理。按处理顺序从外到内排列：

| 模块名 | 源文件 | 配置指令 | 功能说明 |
|--------|--------|----------|----------|
| `ngx_http_not_modified_filter_module` | `src/http/modules/ngx_http_not_modified_filter_module.c` | （自动） | **304 缓存协商**。检查 `If-Modified-Since`/`If-None-Match`，命中则返回 304 |
| `ngx_http_range_header_filter_module` | `src/http/modules/ngx_http_range_filter_module.c` | （自动） | **Range 请求头处理**。解析 `Range` 请求头，支持断点续传 |
| `ngx_http_range_body_filter_module` | `src/http/modules/ngx_http_range_filter_module.c` | （自动） | **Range 响应体裁剪**。按 Range 范围截取响应体内容 |
| `ngx_http_slice_filter_module` | `src/http/modules/ngx_http_slice_filter_module.c` | `slice` | **响应分片**。将大文件分割成固定大小的分片分别缓存，提升缓存效率 ⚙️ `--with-http_slice_module` |
| `ngx_http_gzip_filter_module` | `src/http/modules/ngx_http_gzip_filter_module.c` | `gzip` | **Gzip 压缩**。对响应体进行实时 gzip 压缩，减少传输带宽 |
| `ngx_http_gunzip_filter_module` | `src/http/modules/ngx_http_gunzip_filter_module.c` | `gunzip` | **Gzip 解压**。对后端返回的 gzip 内容解压后再发给不支持 gzip 的客户端 ⚙️ `--with-http_gunzip_module` |
| `ngx_http_gzip_static_module` | `src/http/modules/ngx_http_gzip_static_module.c` | `gzip_static` | **预压缩静态文件**。优先发送 `.gz` 预压缩文件，避免实时压缩的 CPU 开销 ⚙️ `--with-http_gzip_static_module` |
| `ngx_http_ssi_filter_module` | `src/http/modules/ngx_http_ssi_filter_module.c` | `ssi` | **服务端包含（SSI）**。解析 HTML 中的 `<!--# include -->` 等 SSI 指令，实现服务端页面组合 |
| `ngx_http_charset_filter_module` | `src/http/modules/ngx_http_charset_filter_module.c` | `charset` | **字符集转换**。在响应头添加 `charset` 声明，并支持 iconv 字符集转换 |
| `ngx_http_addition_filter_module` | `src/http/modules/ngx_http_addition_filter_module.c` | `add_before_body` / `add_after_body` | **响应体追加**。在响应体前后插入子请求的内容 ⚙️ `--with-http_addition_module` |
| `ngx_http_image_filter_module` | `src/http/modules/ngx_http_image_filter_module.c` | `image_filter` | **图片处理**。对图片进行缩放、裁剪、旋转、水印等操作（依赖 libgd）⚙️ `--with-http_image_filter_module` |
| `ngx_http_xslt_filter_module` | `src/http/modules/ngx_http_xslt_filter_module.c` | `xslt_stylesheet` | **XSLT 转换**。使用 XSLT 样式表转换 XML 响应（依赖 libxslt）⚙️ `--with-http_xslt_module` |
| `ngx_http_sub_filter_module` | `src/http/modules/ngx_http_sub_filter_module.c` | `sub_filter` | **响应体替换**。对响应体中的字符串进行查找替换，常用于反向代理时修改页面内容 ⚙️ `--with-http_sub_module` |
| `ngx_http_headers_filter_module` | `src/http/modules/ngx_http_headers_filter_module.c` | `add_header` / `expires` | **响应头管理**。添加自定义响应头、设置 `Expires`/`Cache-Control` 缓存头 |
| `ngx_http_chunked_filter_module` | `src/http/modules/ngx_http_chunked_filter_module.c` | （自动） | **Chunked 编码**。对 HTTP/1.1 响应进行 Transfer-Encoding: chunked 分块编码 |

---

### 21.4 HTTP URL 重写与路由模块

| 模块名 | 源文件 | 配置指令 | 功能说明 |
|--------|--------|----------|----------|
| `ngx_http_rewrite_module` | `src/http/modules/ngx_http_rewrite_module.c` | `rewrite` / `return` / `if` / `set` | **URL 重写**。基于 PCRE 正则表达式重写 URI，支持条件判断和变量赋值，是最常用的路由模块 |
| `ngx_http_map_module` | `src/http/modules/ngx_http_map_module.c` | `map` | **变量映射**。根据一个变量的值映射出另一个变量，支持正则和通配符匹配 |
| `ngx_http_geo_module` | `src/http/modules/ngx_http_geo_module.c` | `geo` | **IP 地理映射**。根据客户端 IP 地址设置变量值（内置 IP 段数据库） |
| `ngx_http_geoip_module` | `src/http/modules/ngx_http_geoip_module.c` | `geoip_country` / `geoip_city` | **MaxMind GeoIP**。使用 MaxMind GeoIP 数据库获取 IP 的国家/城市信息 ⚙️ `--with-http_geoip_module` |
| `ngx_http_split_clients_module` | `src/http/modules/ngx_http_split_clients_module.c` | `split_clients` | **A/B 测试分流**。按百分比将请求分配到不同变量值，实现 A/B 测试 |
| `ngx_http_mirror_module` | `src/http/modules/ngx_http_mirror_module.c` | `mirror` | **流量镜像**。将请求同步镜像到另一个 URI（子请求），用于流量录制和测试 |
| `ngx_http_try_files_module` | `src/http/ngx_http_core_module.c`（内置） | `try_files` | **文件尝试**。按顺序尝试多个文件路径，找不到则跳转到最后一个参数（URI 或状态码） |

---

### 21.5 HTTP 信息获取与变量模块

| 模块名 | 源文件 | 配置指令 | 功能说明 |
|--------|--------|----------|----------|
| `ngx_http_realip_module` | `src/http/modules/ngx_http_realip_module.c` | `set_real_ip_from` / `real_ip_header` | **真实 IP 获取**。从 `X-Forwarded-For` 或自定义头中提取真实客户端 IP，替换 `$remote_addr` ⚙️ `--with-http_realip_module` |
| `ngx_http_browser_module` | `src/http/modules/ngx_http_browser_module.c` | `modern_browser` / `ancient_browser` | **浏览器识别**。解析 `User-Agent`，识别现代/旧版浏览器，设置对应变量 |
| `ngx_http_userid_module` | `src/http/modules/ngx_http_userid_module.c` | `userid` | **用户 ID Cookie**。自动为用户设置唯一标识 Cookie，用于用户追踪统计 |
| `ngx_http_stub_status_module` | `src/http/modules/ngx_http_stub_status_module.c` | `stub_status` | **状态统计页**。暴露 nginx 的连接数、请求数等运行状态信息 ⚙️ `--with-http_stub_status_module` |

---

### 21.6 HTTP 日志模块

| 模块名 | 源文件 | 配置指令 | 功能说明 |
|--------|--------|----------|----------|
| `ngx_http_log_module` | `src/http/modules/ngx_http_log_module.c` | `access_log` / `log_format` | **访问日志**。记录每个请求的详细信息，支持自定义日志格式、条件日志、缓冲写入 |

---

### 21.7 HTTP SSL/TLS 与协议升级模块

| 模块名 | 源文件 | 配置指令 | 功能说明 |
|--------|--------|----------|----------|
| `ngx_http_ssl_module` | `src/http/modules/ngx_http_ssl_module.c` | `ssl` / `ssl_certificate` | **HTTPS 支持**。基于 OpenSSL 提供 TLS 加密，支持 SNI、OCSP Stapling、会话复用 ⚙️ `--with-http_ssl_module` |
| `ngx_http_v2_module` | `src/http/v2/ngx_http_v2_module.c` | `http2` | **HTTP/2 支持**。支持 HTTP/2 多路复用、头部压缩（HPACK）、服务端推送 ⚙️ `--with-http_v2_module` |
| `ngx_http_v3_module` | `src/http/v3/ngx_http_v3_module.c` | `http3` / `quic` | **HTTP/3 + QUIC 支持**。基于 UDP 的 QUIC 协议，实现 0-RTT 连接和无队头阻塞 ⚙️ `--with-http_v3_module` |

---

### 21.8 事件驱动模块（I/O 多路复用）

这类模块实现 `ngx_event_actions_t` 接口，提供跨平台的 I/O 多路复用能力。nginx 在启动时根据操作系统自动选择最优实现。

| 模块名 | 源文件 | 适用平台 | 功能说明 |
|--------|--------|----------|----------|
| `ngx_epoll_module` | `src/event/modules/ngx_epoll_module.c` | Linux 2.6+ | **epoll**。Linux 最高效的 I/O 多路复用，支持边缘触发（ET）模式，**生产首选** |
| `ngx_kqueue_module` | `src/event/modules/ngx_kqueue_module.c` | FreeBSD / macOS | **kqueue**。BSD 系统的高效事件通知机制，功能类似 epoll |
| `ngx_poll_module` | `src/event/modules/ngx_poll_module.c` | POSIX 通用 | **poll**。POSIX 标准接口，无文件描述符数量限制，但性能低于 epoll |
| `ngx_select_module` | `src/event/modules/ngx_select_module.c` | 通用（含 Windows） | **select**。最古老的 I/O 多路复用，fd 数量受 `FD_SETSIZE`（通常 1024）限制，仅用于兼容 |
| `ngx_iocp_module` | `src/event/modules/ngx_iocp_module.c` | Windows | **IOCP**。Windows 完成端口，Windows 平台的高性能异步 I/O 实现 |
| `ngx_aio_module` | `src/event/modules/ngx_aio_module.c` | FreeBSD | **AIO**。FreeBSD 异步文件 I/O，用于异步读取磁盘文件 |

---

### 21.9 Stream（TCP/UDP）代理模块

`stream` 模块（`--with-stream`）提供 TCP/UDP 四层代理能力，结构与 HTTP 模块类似。

| 模块名 | 源文件 | 配置指令 | 功能说明 |
|--------|--------|----------|----------|
| `ngx_stream_core_module` | `src/stream/ngx_stream_core_module.c` | `stream {}` / `server {}` | **Stream 核心**。定义 TCP/UDP 监听端口和基本配置框架 |
| `ngx_stream_proxy_module` | `src/stream/ngx_stream_proxy_module.c` | `proxy_pass` | **TCP/UDP 代理**。将 TCP/UDP 流量转发给后端服务器，支持健康检查 |
| `ngx_stream_ssl_module` | `src/stream/ngx_stream_ssl_module.c` | `ssl` | **Stream SSL/TLS**。为 TCP 代理提供 TLS 加密（如代理 MySQL TLS 连接） |
| `ngx_stream_ssl_preread_module` | `src/stream/ngx_stream_ssl_preread_module.c` | `ssl_preread` | **SSL 预读**。在不解密的情况下读取 TLS ClientHello，提取 SNI/ALPN 信息用于路由 ⚙️ `--with-stream_ssl_preread_module` |
| `ngx_stream_access_module` | `src/stream/ngx_stream_access_module.c` | `allow` / `deny` | **Stream IP 访问控制**。在 TCP/UDP 层面进行 IP 黑白名单过滤 |
| `ngx_stream_limit_conn_module` | `src/stream/ngx_stream_limit_conn_module.c` | `limit_conn` | **Stream 连接限制**。限制同一 IP 的 TCP 并发连接数 |
| `ngx_stream_realip_module` | `src/stream/ngx_stream_realip_module.c` | `set_real_ip_from` | **Stream 真实 IP**。从 PROXY Protocol 头中提取真实客户端 IP |
| `ngx_stream_geo_module` | `src/stream/ngx_stream_geo_module.c` | `geo` | **Stream IP 地理映射** |
| `ngx_stream_geoip_module` | `src/stream/ngx_stream_geoip_module.c` | `geoip_country` | **Stream MaxMind GeoIP** ⚙️ `--with-stream_geoip_module` |
| `ngx_stream_map_module` | `src/stream/ngx_stream_map_module.c` | `map` | **Stream 变量映射** |
| `ngx_stream_split_clients_module` | `src/stream/ngx_stream_split_clients_module.c` | `split_clients` | **Stream A/B 分流** |
| `ngx_stream_return_module` | `src/stream/ngx_stream_return_module.c` | `return` | **Stream 直接返回**。直接向客户端发送指定内容后关闭连接 |
| `ngx_stream_set_module` | `src/stream/ngx_stream_set_module.c` | `set` | **Stream 变量赋值** |
| `ngx_stream_pass_module` | `src/stream/ngx_stream_pass_module.c` | `pass` | **Stream 内部传递**。将连接传递给另一个监听端口处理 |
| `ngx_stream_log_module` | `src/stream/ngx_stream_log_module.c` | `access_log` | **Stream 访问日志** |
| `ngx_stream_upstream_module` | `src/stream/ngx_stream_upstream.c` | `upstream {}` | **Stream 上游管理**。定义后端服务器组，支持健康检查 |
| `ngx_stream_upstream_hash_module` | `src/stream/ngx_stream_upstream_hash_module.c` | `hash` | **Stream 哈希负载均衡** |
| `ngx_stream_upstream_least_conn_module` | `src/stream/ngx_stream_upstream_least_conn_module.c` | `least_conn` | **Stream 最少连接负载均衡** |
| `ngx_stream_upstream_least_time_module` | `src/stream/ngx_stream_upstream_least_time_module.c` | `least_time` | **Stream 最短响应时间负载均衡**（nginx plus 特性，开源版有限支持） |
| `ngx_stream_upstream_random_module` | `src/stream/ngx_stream_upstream_random_module.c` | `random` | **Stream 随机负载均衡** |
| `ngx_stream_upstream_zone_module` | `src/stream/ngx_stream_upstream_zone_module.c` | `zone` | **Stream 共享内存 upstream**。在 Worker 进程间共享 upstream 状态 |

---

### 21.10 负载均衡模块（HTTP Upstream）

这类模块实现 HTTP upstream 的后端选择算法：

| 模块名 | 源文件 | 配置指令 | 功能说明 |
|--------|--------|----------|----------|
| `ngx_http_upstream_round_robin` | `src/http/ngx_http_upstream_round_robin.c` | （默认） | **加权轮询**。默认负载均衡算法，按 `weight` 权重轮流分配请求 |
| `ngx_http_upstream_ip_hash_module` | `src/http/modules/ngx_http_upstream_ip_hash_module.c` | `ip_hash` | **IP 哈希**。同一客户端 IP 固定路由到同一后端，实现会话保持 |
| `ngx_http_upstream_least_conn_module` | `src/http/modules/ngx_http_upstream_least_conn_module.c` | `least_conn` | **最少连接**。将请求分配给当前活跃连接数最少的后端 |
| `ngx_http_upstream_hash_module` | `src/http/modules/ngx_http_upstream_hash_module.c` | `hash` | **自定义哈希**。根据任意变量（如 `$uri`、`$cookie_id`）进行一致性哈希，支持 `consistent` 参数 |
| `ngx_http_upstream_random_module` | `src/http/modules/ngx_http_upstream_random_module.c` | `random` | **随机选择**。随机选择后端，支持 `two` 参数（从两个随机节点中选最优） |
| `ngx_http_upstream_zone_module` | `src/http/modules/ngx_http_upstream_zone_module.c` | `zone` | **共享内存 upstream**。在所有 Worker 进程间共享 upstream 状态，支持动态配置 ⚙️ `--with-http_upstream_zone_module` |
| `ngx_http_upstream_keepalive_module` | `src/http/modules/ngx_http_upstream_keepalive_module.c` | `keepalive` | **upstream 长连接**。维护到后端的连接池，复用 TCP 连接，减少握手开销 |

---

### 21.11 核心基础模块

这类模块提供 nginx 运行的基础设施，通常不直接暴露配置指令给用户：

| 模块名 | 源文件 | 功能说明 |
|--------|--------|----------|
| `ngx_core_module` | `src/core/nginx.c` | **全局核心**。处理 `worker_processes`、`pid`、`user`、`daemon` 等全局指令 |
| `ngx_events_module` | `src/event/ngx_event.c` | **事件框架**。管理 `events {}` 块，选择并初始化具体的事件模块（epoll 等） |
| `ngx_http_module` | `src/http/ngx_http.c` | **HTTP 框架**。管理 `http {}` 块，初始化所有 HTTP 子模块 |
| `ngx_http_core_module` | `src/http/ngx_http_core_module.c` | **HTTP 核心**。处理 `server {}`、`location {}` 块，实现 location 匹配算法 |
| `ngx_http_upstream_module` | `src/http/ngx_http_upstream.c` | **upstream 框架**。管理 `upstream {}` 块，提供反向代理的通用框架 |
| `ngx_stream_module` | `src/stream/ngx_stream.c` | **Stream 框架**。管理 `stream {}` 块，初始化所有 Stream 子模块 |
| `ngx_mail_module` | `src/mail/ngx_mail.c` | **Mail 框架**。管理 `mail {}` 块，提供邮件代理基础框架 |
| `ngx_openssl_module` | `src/event/ngx_event_openssl.c` | **OpenSSL 集成**。提供 TLS/SSL 的底层实现，被 HTTP/Stream SSL 模块共用 |
| `ngx_thread_pool_module` | `src/core/ngx_thread_pool.c` | **线程池**。提供线程池支持，用于将阻塞操作（如磁盘 I/O）卸载到工作线程 ⚙️ `--with-threads` |

---

### 21.12 模块选择速查表

根据使用场景快速找到对应模块：

| 场景 | 推荐模块 | 关键指令 |
|------|----------|----------|
| 部署 PHP 应用 | `ngx_http_fastcgi_module` | `fastcgi_pass 127.0.0.1:9000` |
| 部署 Python/Django | `ngx_http_uwsgi_module` | `uwsgi_pass 127.0.0.1:8000` |
| 部署 gRPC 服务 | `ngx_http_grpc_module` | `grpc_pass grpc://127.0.0.1:50051` |
| 反向代理 HTTP | `ngx_http_proxy_module` | `proxy_pass http://backend` |
| 代理 MySQL/Redis | `ngx_stream_proxy_module` | `proxy_pass 127.0.0.1:3306`（stream 块内） |
| 开启 HTTPS | `ngx_http_ssl_module` | `ssl_certificate` / `ssl_certificate_key` |
| 开启 HTTP/2 | `ngx_http_v2_module` | `listen 443 ssl http2` |
| 开启 HTTP/3 | `ngx_http_v3_module` | `listen 443 quic` |
| 限制请求速率 | `ngx_http_limit_req_module` | `limit_req_zone` + `limit_req` |
| 限制并发连接 | `ngx_http_limit_conn_module` | `limit_conn_zone` + `limit_conn` |
| 防盗链 | `ngx_http_referer_module` | `valid_referers` |
| 获取真实 IP | `ngx_http_realip_module` | `set_real_ip_from` + `real_ip_header` |
| Gzip 压缩 | `ngx_http_gzip_filter_module` | `gzip on` |
| 静态文件缓存头 | `ngx_http_headers_filter_module` | `expires` / `add_header Cache-Control` |
| URL 重写/跳转 | `ngx_http_rewrite_module` | `rewrite` / `return 301` |
| 访问日志 | `ngx_http_log_module` | `access_log` / `log_format` |
| 查看运行状态 | `ngx_http_stub_status_module` | `stub_status` |
| 图片缩放 | `ngx_http_image_filter_module` | `image_filter resize` |
| A/B 测试 | `ngx_http_split_clients_module` | `split_clients` |
| 流量镜像 | `ngx_http_mirror_module` | `mirror` |
| 子请求认证 | `ngx_http_auth_request_module` | `auth_request` |
| SNI 路由（TCP） | `ngx_stream_ssl_preread_module` | `ssl_preread on` + `map $ssl_preread_server_name` |
| 视频点播 | `ngx_http_mp4_module` / `ngx_http_flv_module` | `mp4` / `flv` |

---

### 21.13 模块实例深度分析：`ngx_http_flv_module`

> 📌 **为什么选它作为范例？**
> `ngx_http_flv_module` 源码仅 262 行，却完整覆盖了一个 HTTP 内容模块的全部要素：**指令注册 → handler 挂载 → 请求解析 → 文件读取 → 响应输出**，是学习 nginx 模块机制的最佳切入点。

源文件：`src/http/modules/ngx_http_flv_module.c`

---

#### 21.13.1 模块功能概述

FLV（Flash Video）是早期流媒体的主流格式。播放器在拖动进度条时，会发起带 `?start=<字节偏移>` 参数的 HTTP 请求，跳到视频中间某帧开始播放。

普通静态文件服务（`ngx_http_static_module`）只能从文件头开始发送，无法处理这种"中途起跳"场景。`ngx_http_flv_module` 的核心价值就在于：

1. **识别 `?start=N` 参数**，从文件的第 N 字节开始发送；
2. **在截断内容前自动补上 FLV 文件头**（13 字节），让播放器能正确解析后续数据流；
3. 其余情况退化为普通静态文件服务，行为与 `ngx_http_static_module` 一致。

---

#### 21.13.2 源码结构总览

```
ngx_http_flv_module.c (262 行)
│
├── 静态数据
│   ├── ngx_http_flv_commands[]   — 指令表（只有一条 "flv" 指令）
│   ├── ngx_flv_header[]          — FLV 文件头常量（13 字节）
│   └── ngx_http_flv_module_ctx   — HTTP 模块上下文（全部为 NULL）
│
├── ngx_http_flv_module           — 模块主体（ngx_module_t）
│
├── ngx_http_flv_handler()        — 请求处理核心（~200 行）
│   ├── 方法校验
│   ├── URI 映射到文件路径
│   ├── 打开文件（走缓存）
│   ├── 解析 ?start= 参数
│   ├── 构造响应头
│   └── 构造 buf chain 并输出
│
└── ngx_http_flv()                — 指令回调（挂载 handler）
```

---

#### 21.13.3 关键数据：FLV 文件头

```c
static u_char  ngx_flv_header[] = "FLV\x1\x5\0\0\0\x9\0\0\0\0";
```

这 13 个字节是标准 FLV 格式规范定义的文件头：

| 字节位置 | 值 | 含义 |
|----------|----|------|
| 0–2 | `FLV` | 魔数，标识文件类型 |
| 3 | `\x01` | 版本号（1） |
| 4 | `\x05` | 标志位：`0b00000101`，bit0=有音频，bit2=有视频 |
| 5–8 | `\x00\x00\x00\x09` | 文件头长度（9 字节，大端序） |
| 9–12 | `\x00\x00\x00\x00` | 第一个 PreviousTagSize（固定为 0） |

当播放器从中间字节开始接收数据时，必须先收到这 13 字节才能正确解析后续的 Tag 数据。nginx 在内存中保存这个常量，每次"中途起跳"请求时直接引用，**零拷贝、零分配**。

---

#### 21.13.4 指令注册与 handler 挂载

**第一步：定义指令表**

```c
static ngx_command_t  ngx_http_flv_commands[] = {
    { ngx_string("flv"),
      NGX_HTTP_LOC_CONF | NGX_CONF_NOARGS,  // 只能在 location 块，无参数
      ngx_http_flv,                          // 解析回调
      0, 0, NULL },
    ngx_null_command
};
```

`NGX_CONF_NOARGS` 表示该指令不接受任何参数，用户只需在 `location` 块中写一行 `flv;` 即可激活。

**第二步：指令回调挂载 handler**

```c
static char *
ngx_http_flv(ngx_conf_t *cf, ngx_command_t *cmd, void *conf)
{
    ngx_http_core_loc_conf_t  *clcf;

    clcf = ngx_http_conf_get_module_loc_conf(cf, ngx_http_core_module);
    clcf->handler = ngx_http_flv_handler;  // ← 关键：注册 content handler

    return NGX_CONF_OK;
}
```

这是 nginx 内容模块最常见的挂载方式：**在配置解析阶段**，将自己的 handler 函数指针写入 `ngx_http_core_loc_conf_t.handler`。当请求进入该 `location` 的 `NGX_HTTP_CONTENT_PHASE` 阶段时，框架会直接调用这个函数。

> 💡 **与 Phase Handler 的区别**：通过 `clcf->handler` 注册的是"独占式"内容处理器，一个 location 只能有一个；而通过 `ngx_http_core_module` 的 `phases` 数组注册的 Phase Handler 可以有多个，按顺序执行。

---

#### 21.13.5 请求处理流程（`ngx_http_flv_handler` 逐段解析）

```
请求到达 NGX_HTTP_CONTENT_PHASE
         │
         ▼
┌─────────────────────────────┐
│ 1. 方法校验                  │  只允许 GET / HEAD，否则返回 405
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 2. URI 末尾斜杠检查          │  以 '/' 结尾 → NGX_DECLINED（交给目录模块）
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 3. 丢弃请求体                │  ngx_http_discard_request_body()
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 4. URI → 文件路径映射        │  ngx_http_map_uri_to_path()
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 5. 打开文件（走缓存）        │  ngx_open_cached_file()，复用 fd，避免重复 open()
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 6. 解析 ?start= 参数         │  ngx_http_arg() 提取，ngx_atoof() 转换为 off_t
│   start=0 或无参数 → i=1    │
│   start>0 且合法  → i=0    │  i 决定输出链从哪个 buf 开始
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 7. 构造响应头                │  设置 200、Content-Length、Last-Modified、ETag
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 8. 发送响应头                │  ngx_http_send_header()
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 9. 构造 buf chain 并输出     │  ngx_http_output_filter(r, &out[i])
└─────────────────────────────┘
```

---

#### 21.13.6 核心逻辑：`?start=` 参数处理

这是整个模块最精妙的部分，仅用约 15 行代码实现了"伪流"功能：

```c
start = 0;
len = of.size;   // 默认：从头发送整个文件
i = 1;           // 输出链起始索引：out[1]（跳过 FLV header buf）

if (r->args.len) {
    if (ngx_http_arg(r, (u_char *) "start", 5, &value) == NGX_OK) {

        start = ngx_atoof(value.data, value.len);  // 字符串 → off_t

        if (start == NGX_ERROR || start >= len) {
            start = 0;   // 非法偏移，退化为从头发送
        }

        if (start) {
            len = sizeof(ngx_flv_header) - 1 + len - start;
            // Content-Length = FLV头(13字节) + 文件剩余部分
            i = 0;       // 输出链从 out[0]（FLV header buf）开始
        }
    }
}
```

**两种输出链结构对比：**

```
无 start 参数（i=1）：
  out[1] → [文件 buf: 0 ~ file_size]
                                    → NULL

有 start=N 参数（i=0）：
  out[0] → [内存 buf: FLV header 13字节]
         → out[1] → [文件 buf: N ~ file_size]
                                              → NULL
```

`ngx_http_output_filter(r, &out[i])` 传入链表头，过滤器链会依次处理每个 buf，最终通过 sendfile 系统调用将文件内容零拷贝发送给客户端。

---

#### 21.13.7 文件打开缓存的使用

```c
clcf = ngx_http_get_module_loc_conf(r, ngx_http_core_module);

ngx_memzero(&of, sizeof(ngx_open_file_info_t));
of.read_ahead     = clcf->read_ahead;
of.directio       = clcf->directio;
of.valid          = clcf->open_file_cache_valid;
of.min_uses       = clcf->open_file_cache_min_uses;
of.errors         = clcf->open_file_cache_errors;
of.events         = clcf->open_file_cache_events;

ngx_open_cached_file(clcf->open_file_cache, &path, &of, r->pool);
```

模块**不自己调用 `open()`**，而是通过 `ngx_open_cached_file()` 走 `open_file_cache`：

- 同一文件的 fd、stat 信息、mtime 等被缓存，高并发下大幅减少系统调用；
- `of.directio` 控制是否启用 Direct I/O（大文件绕过 page cache）；
- `of.read_ahead` 控制预读策略；
- 这些参数全部来自 `ngx_http_core_module` 的 location 配置，模块本身**零配置项**，完全复用核心模块的能力。

---

#### 21.13.8 模块上下文为何全是 NULL？

```c
static ngx_http_module_t  ngx_http_flv_module_ctx = {
    NULL,  /* preconfiguration  */
    NULL,  /* postconfiguration */
    NULL,  /* create main conf  */
    NULL,  /* init main conf    */
    NULL,  /* create server conf*/
    NULL,  /* merge server conf */
    NULL,  /* create loc conf   */
    NULL,  /* merge loc conf    */
};
```

`ngx_http_flv_module` **没有自己的配置项**，所有行为参数（文件路径、缓存策略、DirectIO 阈值等）全部借用 `ngx_http_core_module` 的配置。因此：

- 不需要 `create_loc_conf` / `merge_loc_conf`；
- 不需要 `postconfiguration`（无需注册 Phase Handler，handler 在指令回调中直接挂载）；
- 整个模块上下文 8 个回调全为 NULL，是最"轻量"的 HTTP 模块形态。

---

#### 21.13.9 `ngx_module_t` 主体：生命周期钩子全为 NULL

```c
ngx_module_t  ngx_http_flv_module = {
    NGX_MODULE_V1,
    &ngx_http_flv_module_ctx,   /* module context */
    ngx_http_flv_commands,      /* module directives */
    NGX_HTTP_MODULE,            /* module type */
    NULL,  /* init master  */
    NULL,  /* init module  */
    NULL,  /* init process */
    NULL,  /* init thread  */
    NULL,  /* exit thread  */
    NULL,  /* exit process */
    NULL,  /* exit master  */
    NGX_MODULE_V1_PADDING
};
```

该模块无需在任何生命周期节点做初始化或清理工作，所有钩子均为 NULL。这再次印证了 nginx 模块设计的**按需实现**原则：不需要的回调直接置 NULL，框架会跳过。

---

#### 21.13.10 完整工作流程图

```
nginx.conf 解析阶段
─────────────────────────────────────────────────────────
  location /video/ {
      flv;                ← 触发 ngx_http_flv() 回调
  }                         clcf->handler = ngx_http_flv_handler
                                    │
                                    ▼ 写入 location 配置结构体

HTTP 请求处理阶段（运行时）
─────────────────────────────────────────────────────────
  GET /video/test.flv?start=102400 HTTP/1.1

  NGX_HTTP_CONTENT_PHASE
       │
       ▼ 框架调用 clcf->handler
  ngx_http_flv_handler(r)
       │
       ├─ 方法/URI 校验
       ├─ URI → /data/video/test.flv
       ├─ ngx_open_cached_file()  → fd=7, size=5242880
       ├─ 解析 start=102400
       │       len = 13 + (5242880 - 102400) = 5140493
       │       i = 0
       │
       ├─ 响应头：200 OK, Content-Length: 5140493
       ├─ ngx_http_send_header()
       │
       ├─ out[0].buf → 内存: "FLV\x1\x5\0\0\0\x9\0\0\0\0" (13B)
       ├─ out[1].buf → 文件: fd=7, pos=102400, last=5242880
       │
       └─ ngx_http_output_filter(r, &out[0])
              │
              ▼ 过滤器链（gzip/header filter 等）
              ▼ ngx_http_write_filter
              ▼ sendfile(fd, offset=102400, count=5140480)
                 writev(内存buf: 13字节 FLV header)
```

---

#### 21.13.11 举一反三：从 flv 模块学到的设计模式

| 设计模式 | 在 flv 模块中的体现 | 可复用场景 |
|----------|---------------------|------------|
| **指令即激活** | `flv;` 一行指令完成 handler 注册 | 任何"开关型"功能模块 |
| **借用核心配置** | 文件缓存、DirectIO 等全部来自 `clcf` | 避免重复配置项，保持一致性 |
| **buf chain 零拷贝** | 内存 buf + 文件 buf 拼接，sendfile 直发 | 需要在文件内容前插入动态头部的场景 |
| **索引变量控制链表头** | `i=0/1` 决定从哪个 buf 开始输出 | 条件性前置内容注入 |
| **NGX_DECLINED 降级** | URI 以 `/` 结尾时主动放弃，交给其他模块 | 模块职责边界清晰化 |
| **全 NULL 上下文** | 无配置项时 ctx 全置 NULL | 轻量功能模块的标准写法 |

---



