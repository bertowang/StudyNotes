# FreeRTOS-Kernel 源码学习指南

> **文档版本**：v1.0 | 2026年6月
> **参考源码**：FreeRTOS-Kernel（DEVELOPMENT BRANCH）
> **适用读者**：了解基本 C 语言和操作系统原理的嵌入式开发者
>
> 本文档基于 FreeRTOS-Kernel 源码，面向希望深入理解 RTOS 内核实现的开发者，将操作系统理论与实际代码实现一一对应，帮助你真正理解 FreeRTOS 是如何工作的。

---

## 一、项目结构总览

```
FreeRTOS-Kernel/
├── tasks.c              ← 任务管理核心（362KB，8878行，最重要！）
├── queue.c              ← 队列/信号量/互斥量实现（130KB）
├── timers.c             ← 软件定时器（57KB）
├── event_groups.c       ← 事件组（36KB）
├── stream_buffer.c      ← 流缓冲区/消息缓冲区（75KB）
├── list.c               ← 链表基础数据结构（10KB）
├── croutine.c           ← 协程（遗留功能，不推荐使用）
│
├── include/             ← 公共头文件
│   ├── FreeRTOS.h       ← 主头文件：所有配置宏、类型定义（107KB）
│   ├── task.h           ← 任务管理API声明（165KB）
│   ├── queue.h          ← 队列API声明
│   ├── semphr.h         ← 信号量API（基于队列实现）
│   ├── timers.h         ← 定时器API
│   ├── event_groups.h   ← 事件组API
│   ├── stream_buffer.h  ← 流缓冲区API
│   ├── list.h           ← 链表数据结构定义
│   └── portable.h       ← 移植层接口声明
│
├── portable/            ← 硬件移植层（与CPU架构相关）
│   ├── GCC/             ← GCC编译器的各平台移植
│   │   ├── ARM_CM3/     ← Cortex-M3（最常用）
│   │   ├── ARM_CM4F/    ← Cortex-M4F（带FPU）
│   │   ├── ARM_CM7/     ← Cortex-M7
│   │   └── ...          ← 其他平台
│   ├── IAR/             ← IAR编译器的各平台移植
│   ├── MemMang/         ← 内存管理方案（heap_1~heap_5）
│   └── ...
│
└── examples/
    ├── cmake_example/   ← 最简单的示例工程
    │   ├── main.c       ← 入门示例代码
    │   └── CMakeLists.txt
    └── template_configuration/
        └── FreeRTOSConfig.h  ← 完整配置模板（含所有配置项说明）
```

### 1.1 代码量分布（复杂度热点）

| 文件 | 大小 | 行数 | 说明 |
|------|------|------|------|
| `tasks.c` | 362 KB | 8878 行 | 任务调度核心，最复杂 |
| `portable/Common/mpu_wrappers_v2.c` | 222 KB | — | MPU 安全封装（可选） |
| `queue.c` | 130 KB | 3390 行 | 队列/信号量/互斥量 |
| `stream_buffer.c` | 75 KB | — | 流缓冲区 |
| `timers.c` | 57 KB | 1344 行 | 软件定时器 |
| `event_groups.c` | 36 KB | 888 行 | 事件组 |
| `list.c` | 10 KB | 249 行 | 链表（最简单，先读这个！） |

**设计洞察**：`tasks.c` 占整个内核代码量的约 40%，这不是偶然——任务调度是 RTOS 的核心，所有其他机制（队列、信号量、定时器）最终都要通过任务调度来体现效果。

### 1.2 源码阅读建议

**推荐阅读顺序**：
1. `list.c` + `include/list.h` — 理解基础数据结构（30分钟）
2. `tasks.c` 前 500 行 — 理解 TCB 结构和全局变量（1小时）
3. `examples/cmake_example/main.c` — 理解最小可运行示例（15分钟）
4. `tasks.c` 中的 `xTaskCreate` 和 `vTaskStartScheduler` — 理解任务创建和启动（2小时）
5. `queue.c` — 理解队列/信号量/互斥量（2小时）
6. `timers.c` 和 `event_groups.c` — 理解高级特性（1小时）

---

## 二、核心概念：FreeRTOS 与 µC/OS-III 的设计差异

### 2.1 两者的核心设计哲学对比

| 对比项 | FreeRTOS | µC/OS-III |
|--------|----------|-----------|
| **优先级数量** | 可配置（`configMAX_PRIORITIES`，默认5级） | 固定64级（可配置） |
| **同优先级任务** | 支持时间片轮转（可选） | 支持时间片轮转 |
| **内存管理** | 5种方案（heap_1~heap_5），可选 | 固定大小内存池 |
| **队列实现** | 信号量/互斥量都基于队列实现 | 信号量、互斥量独立实现 |
| **配置方式** | `FreeRTOSConfig.h` 宏定义 | `os_cfg.h` + `os_cfg_app.h` |
| **移植层** | `portable/` 目录，接口统一 | `Ports/` 目录 |
| **代码风格** | 匈牙利命名法（`pxTask`、`uxPriority`） | 匈牙利命名法（`p_tcb`、`prio`） |
| **许可证** | MIT（完全开源免费） | 商业授权（v3.x 之前） |

**设计洞察**：FreeRTOS 最重要的设计决策是**用队列统一实现所有 IPC 机制**。信号量是 `uxItemSize=0` 的队列，互斥量是带优先级继承的特殊队列。这使得代码量更少，但理解成本更高——你必须先理解队列，才能理解信号量和互斥量。

### 2.2 命名规范（读代码的钥匙）

FreeRTOS 使用严格的匈牙利命名法，掌握前缀规则可以大幅提升阅读速度：

| 前缀 | 含义 | 示例 |
|------|------|------|
| `v` | void 返回值 | `vTaskDelay()` |
| `x` | BaseType_t 返回值（或结构体） | `xTaskCreate()` |
| `ux` | UBaseType_t（无符号基础类型） | `uxTaskGetNumberOfTasks()` |
| `p` | 指针 | `pxCurrentTCB` |
| `pp` | 指针的指针 | `ppxIdleTaskTCBBuffer` |
| `prv` | 私有函数（文件内部使用） | `prvInitialiseNewTask()` |
| `port` | 移植层函数/宏 | `portYIELD()` |
| `config` | 配置宏 | `configMAX_PRIORITIES` |
| `INCLUDE_` | 功能开关宏 | `INCLUDE_vTaskDelete` |
| `TCB` | 任务控制块 | `TCB_t` |

---

## 三、基础数据结构：链表（list.c）

### 3.1 为什么先看链表？

FreeRTOS 的所有核心机制——就绪列表、延时列表、等待列表——都建立在同一套链表实现上。理解链表，就理解了 FreeRTOS 数据流动的"血管"。

### 3.2 链表结构定义（`include/list.h`）

```c
/* 链表节点（ListItem_t） */
struct xLIST_ITEM
{
    TickType_t xItemValue;          /* 排序键值（通常是唤醒时间或优先级） */
    struct xLIST_ITEM * pxNext;     /* 指向下一个节点 */
    struct xLIST_ITEM * pxPrevious; /* 指向上一个节点 */
    void * pvOwner;                 /* 指向拥有此节点的对象（通常是TCB） */
    struct xLIST * pxContainer;     /* 指向所在链表（用于快速判断归属） */
};
typedef struct xLIST_ITEM ListItem_t;

/* 链表头（List_t） */
typedef struct xLIST
{
    UBaseType_t uxNumberOfItems;    /* 链表中的节点数量 */
    ListItem_t * pxIndex;           /* 遍历指针（用于轮转调度） */
    MiniListItem_t xListEnd;        /* 哨兵节点（值为portMAX_DELAY，始终在末尾） */
} List_t;
```

### 3.3 链表结构图

```
List_t（链表头）
┌─────────────────────────────────────────────────────────┐
│  uxNumberOfItems = 3                                    │
│  pxIndex ──────────────────────────────────┐           │
│  xListEnd（哨兵，xItemValue=portMAX_DELAY） │           │
└──────┬──────────────────────────────────────┼───────────┘
       │ pxNext                               │
       ▼                                      │
  ┌──────────┐    ┌──────────┐    ┌──────────┐│
  │ Item A   │───▶│ Item B   │───▶│ Item C   ││
  │ val=10   │◀───│ val=20   │◀───│ val=30   │◀┘
  │ owner=T1 │    │ owner=T2 │    │ owner=T3 │
  └──────────┘    └──────────┘    └──────────┘
       ▲                                    │
       └────────────────────────────────────┘
                  （循环双向链表）
```

**关键设计**：
1. **哨兵节点**（`xListEnd`）：`xItemValue = portMAX_DELAY`（最大值），始终在链表末尾，避免了边界判断，简化了插入逻辑。
2. **`pvOwner` 双向引用**：节点知道自己的主人（TCB），主人（TCB）也包含节点。这使得从链表节点反向找到 TCB 只需 O(1)。
3. **`pxContainer` 快速归属判断**：节点记录自己在哪个链表里，`uxListRemove()` 不需要传入链表指针，只需传入节点本身。

### 3.4 两种插入方式（核心 API）

```c
/* 方式1：按值排序插入（vListInsert）
 * 用途：延时列表（按唤醒时间排序）、事件等待列表（按优先级排序）
 * 时间复杂度：O(n)，n为链表长度
 */
void vListInsert( List_t * const pxList, ListItem_t * const pxNewListItem )
{
    // 从头遍历，找到第一个值 >= 新节点值的位置
    for( pxIterator = &(pxList->xListEnd);
         pxIterator->pxNext->xItemValue <= xValueOfInsertion;
         pxIterator = pxIterator->pxNext )
    {
        /* 遍历到正确位置 */
    }
    // 插入到 pxIterator 之后
    pxNewListItem->pxNext = pxIterator->pxNext;
    pxNewListItem->pxPrevious = pxIterator;
    pxIterator->pxNext = pxNewListItem;
    ...
}

/* 方式2：插入到 pxIndex 之前（vListInsertEnd）
 * 用途：就绪列表（同优先级任务轮转，不需要排序）
 * 时间复杂度：O(1)
 */
void vListInsertEnd( List_t * const pxList, ListItem_t * const pxNewListItem )
{
    ListItem_t * const pxIndex = pxList->pxIndex;
    // 插入到 pxIndex 之前（即成为 pxIndex 的"前一个"）
    pxNewListItem->pxNext = pxIndex;
    pxNewListItem->pxPrevious = pxIndex->pxPrevious;
    pxIndex->pxPrevious->pxNext = pxNewListItem;
    pxIndex->pxPrevious = pxNewListItem;
    ...
}
```

**设计洞察**：两种插入方式对应两种使用场景。就绪列表用 `vListInsertEnd`（O(1)），因为同优先级任务只需要轮转，不需要排序；延时列表用 `vListInsert`（O(n)），因为需要按唤醒时间排序，以便 tick 中断快速找到最早需要唤醒的任务。

### 3.5 轮转遍历宏（调度核心）

```c
/* listGET_OWNER_OF_NEXT_ENTRY：获取下一个节点的 pvOwner
 * 每次调用都会移动 pxIndex，实现轮转效果
 * 这是同优先级任务时间片轮转的底层实现！
 */
#define listGET_OWNER_OF_NEXT_ENTRY( pxTCB, pxList )                    \
do {                                                                     \
    List_t * const pxConstList = ( pxList );                             \
    /* 移动 pxIndex 到下一个节点 */                                       \
    ( pxConstList )->pxIndex = ( pxConstList )->pxIndex->pxNext;         \
    /* 跳过哨兵节点 */                                                    \
    if( ( void * ) ( pxConstList )->pxIndex ==                           \
        ( void * ) &( ( pxConstList )->xListEnd ) )                      \
    {                                                                    \
        ( pxConstList )->pxIndex = ( pxConstList )->xListEnd.pxNext;     \
    }                                                                    \
    /* 返回当前节点的 pvOwner（即 TCB 指针） */                            \
    ( pxTCB ) = ( pxConstList )->pxIndex->pvOwner;                       \
} while( 0 )
```

---

## 四、任务管理（tasks.c）

### 4.1 任务控制块（TCB）：任务的"身份证"

TCB（Task Control Block）是 FreeRTOS 中最重要的数据结构，每个任务对应一个 TCB，记录了任务运行所需的全部信息。

```c
/* tasks.c，约第 400 行 */
typedef struct tskTaskControlBlock
{
    /* ===== 必须是第一个成员！移植层汇编代码依赖此偏移 ===== */
    volatile StackType_t * pxTopOfStack;  /* 栈顶指针（上下文切换时保存/恢复） */

    /* ===== MPU 支持（可选） ===== */
    #if ( portUSING_MPU_WRAPPERS == 1 )
        xMPU_SETTINGS xMPUSettings;       /* MPU 区域配置（必须是第二个成员！） */
    #endif

    /* ===== 链表节点（任务状态管理的关键） ===== */
    ListItem_t xStateListItem;   /* 状态节点：挂在就绪/延时/挂起列表上 */
    ListItem_t xEventListItem;   /* 事件节点：挂在队列/信号量的等待列表上 */

    /* ===== 基本属性 ===== */
    UBaseType_t uxPriority;      /* 当前优先级（可被优先级继承临时修改） */
    StackType_t * pxStack;       /* 栈底指针（用于栈溢出检测） */
    char pcTaskName[ configMAX_TASK_NAME_LEN ]; /* 任务名（调试用） */

    /* ===== 可选特性（通过宏控制是否编译） ===== */
    #if ( configUSE_MUTEXES == 1 )
        UBaseType_t uxBasePriority; /* 基础优先级（优先级继承时保存原始优先级） */
        UBaseType_t uxMutexesHeld;  /* 持有的互斥量数量 */
    #endif

    #if ( configUSE_TASK_NOTIFICATIONS == 1 )
        volatile uint32_t ulNotifiedValue[ configTASK_NOTIFICATION_ARRAY_ENTRIES ];
        volatile uint8_t ucNotifyState[ configTASK_NOTIFICATION_ARRAY_ENTRIES ];
    #endif

    #if ( configGENERATE_RUN_TIME_STATS == 1 )
        configRUN_TIME_COUNTER_TYPE ulRunTimeCounter; /* 运行时间统计 */
    #endif

    /* ===== SMP 多核支持（可选） ===== */
    #if ( configNUMBER_OF_CORES > 1 )
        volatile BaseType_t xTaskRunState; /* 运行状态：在哪个核上运行，或未运行 */
        UBaseType_t uxTaskAttributes;      /* 任务属性（如是否是空闲任务） */
    #endif
} tskTCB;
typedef tskTCB TCB_t;
```

**TCB 结构解读**：
- `pxTopOfStack` **必须是第一个成员**，因为移植层的汇编代码（上下文切换）直接通过 TCB 指针偏移 0 来访问栈顶，不能改变位置。
- 每个任务有**两个链表节点**：`xStateListItem` 用于状态管理（就绪/延时/挂起），`xEventListItem` 用于等待事件（队列满/空、信号量等）。一个任务可以同时在状态列表和事件列表中，这是 FreeRTOS 实现阻塞等待的关键。
- 大量 `#if` 条件编译使 TCB 大小可裁剪，在资源极度受限的 MCU 上可以关闭不需要的特性。

### 4.2 全局状态变量（调度器的"大脑"）

```c
/* tasks.c，约第 490 行 */

/* 就绪列表：每个优先级一个链表，共 configMAX_PRIORITIES 个 */
PRIVILEGED_DATA static List_t pxReadyTasksLists[ configMAX_PRIORITIES ];

/* 延时列表：两个交替使用（处理 tick 计数溢出） */
PRIVILEGED_DATA static List_t xDelayedTaskList1;
PRIVILEGED_DATA static List_t xDelayedTaskList2;
PRIVILEGED_DATA static List_t * volatile pxDelayedTaskList;         /* 当前延时列表 */
PRIVILEGED_DATA static List_t * volatile pxOverflowDelayedTaskList; /* 溢出延时列表 */

/* 其他列表 */
PRIVILEGED_DATA static List_t xPendingReadyList;      /* 调度器挂起时就绪的任务 */
PRIVILEGED_DATA static List_t xTasksWaitingTermination; /* 等待清理的已删除任务 */
PRIVILEGED_DATA static List_t xSuspendedTaskList;     /* 挂起的任务 */

/* 当前运行任务（单核） */
PRIVILEGED_DATA TCB_t * volatile pxCurrentTCB = NULL;

/* 调度器状态 */
PRIVILEGED_DATA static volatile TickType_t xTickCount = 0;          /* 系统 tick 计数 */
PRIVILEGED_DATA static volatile UBaseType_t uxTopReadyPriority = 0; /* 最高就绪优先级 */
PRIVILEGED_DATA static volatile BaseType_t xSchedulerRunning = pdFALSE;
```

**全局变量解读**：
- `pxReadyTasksLists[]` 是调度器的核心数据结构。数组下标就是优先级，每个元素是一个链表，存放该优先级下所有就绪任务。调度时只需找到最高非空链表，取其第一个任务即可。
- 两个延时列表（`xDelayedTaskList1/2`）交替使用，解决 tick 计数溢出问题：当 tick 从 `0xFFFFFFFF` 溢出到 `0` 时，两个列表互换，原来的"溢出列表"变成"当前列表"。
- `uxTopReadyPriority` 记录当前最高就绪优先级，避免每次调度都遍历所有优先级。

### 4.3 任务状态机

```
                    ┌─────────────────────────────────────────┐
                    │                                         │
                    ▼                                         │
              ┌──────────┐   vTaskSuspend()   ┌──────────────┐
              │  就绪态  │──────────────────▶│   挂起态     │
              │  Ready   │◀──────────────────│  Suspended   │
              └──────────┘   vTaskResume()   └──────────────┘
                 │    ▲
    调度器选中   │    │  等待事件超时/事件发生
                 ▼    │
              ┌──────────┐   vTaskDelay()     ┌──────────────┐
              │  运行态  │──────────────────▶│   阻塞态     │
              │  Running │   等待队列/信号量  │   Blocked    │
              └──────────┘◀──────────────────└──────────────┘
                    │         事件发生
                    │  vTaskDelete()
                    ▼
              ┌──────────┐
              │  删除态  │（等待空闲任务清理内存）
              │  Deleted │
              └──────────┘
```

**状态转换说明**：
- **就绪 → 运行**：调度器选中该任务（优先级最高且就绪）
- **运行 → 阻塞**：调用 `vTaskDelay()`、等待队列/信号量/事件组
- **阻塞 → 就绪**：延时到期（tick 中断触发）、等待的事件发生
- **任意 → 挂起**：调用 `vTaskSuspend()`，只有 `vTaskResume()` 能恢复

### 4.4 任务创建：`xTaskCreate()` 全流程

```c
/* tasks.c，约第 1741 行 */
BaseType_t xTaskCreate( TaskFunction_t pxTaskCode,   /* 任务函数指针 */
                        const char * const pcName,   /* 任务名（调试用） */
                        const configSTACK_DEPTH_TYPE uxStackDepth, /* 栈深度（单位：字，非字节！） */
                        void * const pvParameters,   /* 传给任务函数的参数 */
                        UBaseType_t uxPriority,      /* 优先级（0=最低） */
                        TaskHandle_t * const pxCreatedTask ) /* 输出：任务句柄 */
{
    TCB_t * pxNewTCB;
    BaseType_t xReturn;

    /* 第一步：分配内存（TCB + 栈） */
    pxNewTCB = prvCreateTask( pxTaskCode, pcName, uxStackDepth,
                              pvParameters, uxPriority, pxCreatedTask );

    if( pxNewTCB != NULL )
    {
        /* 第二步：加入就绪列表，触发调度 */
        prvAddNewTaskToReadyList( pxNewTCB );
        xReturn = pdPASS;
    }
    else
    {
        xReturn = errCOULD_NOT_ALLOCATE_REQUIRED_MEMORY;
    }
    return xReturn;
}
```

**`prvCreateTask()` 内存分配细节**（`tasks.c`，约第 1641 行）：

```c
/* 注意栈增长方向！
 * 栈向下增长（大多数 ARM）：先分配栈，再分配 TCB（防止栈溢出覆盖 TCB）
 * 栈向上增长（少数架构）：先分配 TCB，再分配栈
 */
#if ( portSTACK_GROWTH > 0 )  /* 栈向上增长 */
    pxNewTCB = pvPortMalloc( sizeof( TCB_t ) );
    pxNewTCB->pxStack = pvPortMallocStack( uxStackDepth * sizeof( StackType_t ) );
#else  /* 栈向下增长（ARM Cortex-M 等） */
    pxStack = pvPortMallocStack( uxStackDepth * sizeof( StackType_t ) );
    pxNewTCB = pvPortMalloc( sizeof( TCB_t ) );
    pxNewTCB->pxStack = pxStack;
#endif
```

**`prvInitialiseNewTask()` 栈初始化**（`tasks.c`，约第 1815 行）：

```c
/* 关键：将栈初始化为"好像任务已经运行过一次，然后被中断"的状态
 * 这样第一次"恢复"任务时，就能正确跳转到任务函数入口
 */
pxTopOfStack = pxPortInitialiseStack( pxTopOfStack, pxTaskCode, pvParameters );
```

> 💡 **关键理解**：`pxPortInitialiseStack()` 是移植层函数（在 `portable/GCC/ARM_CM3/port.c` 等文件中实现）。它在栈上伪造一个"中断现场"，包含 PC（指向任务函数）、LR（指向 `prvTaskExitError`）、以及所有寄存器的初始值。第一次"恢复"这个任务时，就像从中断返回一样，CPU 会跳转到任务函数入口。

### 4.5 静态分配 vs 动态分配

FreeRTOS 同时支持两种内存分配方式，这是它区别于 µC/OS-III 的重要特性：

```c
/* 动态分配（需要 heap_x.c） */
TaskHandle_t xHandle;
xTaskCreate( vTaskCode, "Task", 128, NULL, 1, &xHandle );

/* 静态分配（不需要堆，适合安全关键系统） */
static StaticTask_t xTaskBuffer;           /* TCB 静态存储 */
static StackType_t xStack[ 128 ];          /* 栈静态存储 */
xTaskCreateStatic( vTaskCode, "Task", 128, NULL, 1, xStack, &xTaskBuffer );
```

**为什么提供静态分配？** 动态分配在运行时可能失败（堆不足），对于安全关键系统（汽车、航空）这是不可接受的。静态分配在编译时就确定了所有内存，运行时不会失败，也更容易通过 MISRA-C 等安全标准认证。

---

## 五、调度器启动与运行

### 5.1 最小可运行示例（`examples/cmake_example/main.c`）

```c
#include <FreeRTOS.h>
#include <task.h>

/* 任务函数：必须是无限循环，不能返回 */
static void exampleTask( void * parameters )
{
    ( void ) parameters;  /* 未使用参数 */
    for( ; ; )
    {
        /* 任务代码 */
        vTaskDelay( 100 ); /* 延时 100 个 tick，让出 CPU */
    }
}

int main( void )
{
    /* 静态分配 TCB 和栈 */
    static StaticTask_t exampleTaskTCB;
    static StackType_t exampleTaskStack[ configMINIMAL_STACK_SIZE ];

    /* 创建任务（最高优先级） */
    xTaskCreateStatic( &exampleTask, "example",
                       configMINIMAL_STACK_SIZE, NULL,
                       configMAX_PRIORITIES - 1U,
                       &( exampleTaskStack[ 0 ] ),
                       &( exampleTaskTCB ) );

    /* 启动调度器（不会返回！） */
    vTaskStartScheduler();

    for( ; ; ) { /* 永远不会到这里 */ }
}
```

### 5.2 `vTaskStartScheduler()` 启动流程

```c
/* tasks.c，约第 3704 行 */
void vTaskStartScheduler( void )
{
    BaseType_t xReturn;

    /* 第一步：创建空闲任务（系统必须有，优先级最低） */
    xReturn = prvCreateIdleTasks();

    /* 第二步：创建定时器服务任务（如果启用了软件定时器） */
    #if ( configUSE_TIMERS == 1 )
    {
        if( xReturn == pdPASS )
        {
            xReturn = xTimerCreateTimerTask();
        }
    }
    #endif

    if( xReturn == pdPASS )
    {
        /* 第三步：关中断（防止 tick 在调度器完全启动前触发） */
        portDISABLE_INTERRUPTS();

        /* 第四步：设置调度器状态 */
        xNextTaskUnblockTime = portMAX_DELAY;
        xSchedulerRunning = pdTRUE;
        xTickCount = ( TickType_t ) configINITIAL_TICK_COUNT;

        /* 第五步：调用移植层函数，启动第一个任务
         * xPortStartScheduler() 会：
         *   1. 配置 SysTick（或其他定时器）产生 tick 中断
         *   2. 配置 PendSV 中断（用于上下文切换）
         *   3. 恢复最高优先级任务的上下文，开始运行
         * 此函数不会返回！
         */
        ( void ) xPortStartScheduler();
    }
}
```

### 5.3 调度器核心循环：`xTaskIncrementTick()`

每次 tick 中断触发时，移植层会调用 `xTaskIncrementTick()`，这是调度器的"心跳"：

```c
/* tasks.c，约第 4740 行 */
BaseType_t xTaskIncrementTick( void )
{
    TCB_t * pxTCB;
    TickType_t xItemValue;
    BaseType_t xSwitchRequired = pdFALSE;

    if( uxSchedulerSuspended == 0U )
    {
        /* 第一步：tick 计数加 1 */
        const TickType_t xConstTickCount = xTickCount + 1;
        xTickCount = xConstTickCount;

        /* 第二步：处理 tick 溢出（交换两个延时列表） */
        if( xConstTickCount == 0U )
        {
            taskSWITCH_DELAYED_LISTS();  /* 交换 pxDelayedTaskList 和 pxOverflowDelayedTaskList */
        }

        /* 第三步：检查是否有任务需要唤醒 */
        if( xConstTickCount >= xNextTaskUnblockTime )
        {
            for( ; ; )
            {
                if( listLIST_IS_EMPTY( pxDelayedTaskList ) )
                {
                    xNextTaskUnblockTime = portMAX_DELAY;
                    break;
                }

                /* 取延时列表头部（最早需要唤醒的任务） */
                pxTCB = listGET_OWNER_OF_HEAD_ENTRY( pxDelayedTaskList );
                xItemValue = listGET_ITEM_VALUE_OF_HEAD_ENTRY( pxDelayedTaskList );

                if( xConstTickCount < xItemValue )
                {
                    /* 还没到唤醒时间，更新下次检查时间 */
                    xNextTaskUnblockTime = xItemValue;
                    break;
                }

                /* 从延时列表移除，加入就绪列表 */
                listREMOVE_ITEM( &( pxTCB->xStateListItem ) );
                prvAddTaskToReadyList( pxTCB );

                /* 如果唤醒的任务优先级更高，标记需要切换 */
                if( pxTCB->uxPriority > pxCurrentTCB->uxPriority )
                {
                    xSwitchRequired = pdTRUE;
                }
            }
        }

        /* 第四步：时间片轮转（如果启用） */
        #if ( configUSE_TIME_SLICING == 1 )
        {
            if( listCURRENT_LIST_LENGTH(
                    &( pxReadyTasksLists[ pxCurrentTCB->uxPriority ] ) ) > 1 )
            {
                xSwitchRequired = pdTRUE;  /* 同优先级有多个任务，轮转 */
            }
        }
        #endif
    }
    else
    {
        /* 调度器挂起时，只记录 tick 数，不处理 */
        ++xPendedTicks;
    }

    return xSwitchRequired;  /* 返回 pdTRUE 表示需要上下文切换 */
}
```

**tick 中断处理流程图**：

```
Tick 中断触发
     │
     ▼
xTaskIncrementTick()
     │
     ├─ tick 计数 +1
     │
     ├─ tick 溢出？→ 交换延时列表
     │
     ├─ 遍历延时列表头部
     │   ├─ 到期？→ 移入就绪列表
     │   └─ 未到期？→ 更新 xNextTaskUnblockTime，退出
     │
     ├─ 时间片轮转？→ 标记需要切换
     │
     └─ 返回 xSwitchRequired
          │
          ├─ pdTRUE → 触发 PendSV（上下文切换）
          └─ pdFALSE → 继续当前任务
```

### 5.4 上下文切换：`vTaskSwitchContext()`

```c
/* tasks.c，约第 4900 行 */
void vTaskSwitchContext( void )
{
    /* 选择最高优先级的就绪任务 */
    taskSELECT_HIGHEST_PRIORITY_TASK();
    /* 宏展开后等价于：
     *   找到最高非空就绪列表
     *   调用 listGET_OWNER_OF_NEXT_ENTRY 获取下一个任务（轮转）
     *   更新 pxCurrentTCB
     */
}
```

**`taskSELECT_HIGHEST_PRIORITY_TASK` 宏**（`tasks.c`，约第 200 行）：

```c
/* 通用实现（configUSE_PORT_OPTIMISED_TASK_SELECTION == 0） */
#define taskSELECT_HIGHEST_PRIORITY_TASK()                                    \
do {                                                                          \
    UBaseType_t uxTopPriority = uxTopReadyPriority;                           \
    /* 从最高优先级向下找，直到找到非空就绪列表 */                              \
    while( listLIST_IS_EMPTY( &( pxReadyTasksLists[ uxTopPriority ] ) ) )    \
    {                                                                         \
        --uxTopPriority;                                                      \
    }                                                                         \
    /* 轮转获取该优先级的下一个任务 */                                          \
    listGET_OWNER_OF_NEXT_ENTRY( pxCurrentTCB,                               \
                                 &( pxReadyTasksLists[ uxTopPriority ] ) );   \
    uxTopReadyPriority = uxTopPriority;                                       \
} while( 0 )
```

> 💡 **优化版本**：当 `configUSE_PORT_OPTIMISED_TASK_SELECTION == 1` 时，使用 CPU 的 CLZ（Count Leading Zeros）指令，可以 O(1) 找到最高优先级，而不是 O(n) 遍历。ARM Cortex-M 支持此指令。

---

## 六、队列、信号量与互斥量（queue.c）

### 6.1 统一的底层结构：`Queue_t`

FreeRTOS 最重要的设计决策之一：**信号量和互斥量都是队列的特殊形式**。

```c
/* queue.c，约第 100 行 */
typedef struct QueueDefinition
{
    int8_t * pcHead;       /* 队列存储区起始地址 */
    int8_t * pcWriteTo;    /* 下一个写入位置 */

    union {
        struct {
            int8_t * pcTail;     /* 队列存储区结束地址 */
            int8_t * pcReadFrom; /* 下一个读取位置 */
        } xQueue;                /* 作为队列时使用 */

        struct {
            TaskHandle_t xMutexHolder;        /* 互斥量持有者（优先级继承用） */
            UBaseType_t uxRecursiveCallCount;  /* 递归互斥量计数 */
        } xSemaphore;            /* 作为信号量/互斥量时使用 */
    } u;

    List_t xTasksWaitingToSend;    /* 等待发送的任务列表（队列满时阻塞） */
    List_t xTasksWaitingToReceive; /* 等待接收的任务列表（队列空时阻塞） */

    volatile UBaseType_t uxMessagesWaiting; /* 当前队列中的消息数量 */
    UBaseType_t uxLength;                   /* 队列最大容量（消息数量） */
    UBaseType_t uxItemSize;                 /* 每条消息的大小（字节） */

    volatile int8_t cRxLock;  /* 接收锁（ISR 中使用，防止并发修改等待列表） */
    volatile int8_t cTxLock;  /* 发送锁 */
} xQUEUE;
typedef xQUEUE Queue_t;
```

**不同 IPC 对象的本质**：

| IPC 对象 | `uxItemSize` | `uxLength` | `pcHead` | 说明 |
|----------|-------------|-----------|---------|------|
| 队列 | > 0（消息大小） | > 0 | 指向存储区 | 标准队列 |
| 二值信号量 | 0 | 1 | NULL | 只有计数，无数据 |
| 计数信号量 | 0 | N | NULL | 最大计数为 N |
| 互斥量 | 0 | 1 | NULL | 带优先级继承 |
| 递归互斥量 | 0 | 1 | NULL | 同任务可多次获取 |

这张表说明了一个关键事实：**信号量不存储数据，只存储"计数"**（`uxMessagesWaiting`）。`uxItemSize=0` 意味着发送/接收操作不复制任何数据，只修改计数。

### 6.2 队列发送：`xQueueSend()` 核心逻辑

```c
/* queue.c，简化版 */
BaseType_t xQueueSend( QueueHandle_t xQueue, const void * pvItemToQueue,
                       TickType_t xTicksToWait )
{
    Queue_t * const pxQueue = xQueue;

    for( ; ; )
    {
        taskENTER_CRITICAL();
        {
            /* 队列未满？ */
            if( pxQueue->uxMessagesWaiting < pxQueue->uxLength )
            {
                /* 复制数据到队列（信号量时 uxItemSize=0，不复制） */
                prvCopyDataToQueue( pxQueue, pvItemToQueue, queueSEND_TO_BACK );

                /* 有任务在等待接收？唤醒它 */
                if( listLIST_IS_EMPTY( &( pxQueue->xTasksWaitingToReceive ) ) == pdFALSE )
                {
                    /* 从等待列表取出最高优先级任务，加入就绪列表 */
                    xTaskRemoveFromEventList( &( pxQueue->xTasksWaitingToReceive ) );
                }
                taskEXIT_CRITICAL();
                return pdPASS;
            }
            else
            {
                /* 队列满，且不等待 */
                if( xTicksToWait == 0 )
                {
                    taskEXIT_CRITICAL();
                    return errQUEUE_FULL;
                }
                /* 将当前任务加入等待发送列表，阻塞 */
                vTaskPlaceOnEventList( &( pxQueue->xTasksWaitingToSend ), xTicksToWait );
            }
        }
        taskEXIT_CRITICAL();

        /* 触发上下文切换，让其他任务运行 */
        portYIELD_WITHIN_API();
    }
}
```

### 6.3 互斥量的优先级继承

互斥量是信号量的特殊形式，增加了**优先级继承**机制，用于解决优先级反转问题：

```
优先级反转场景：
  高优先级任务 H（优先级3）等待互斥量
  中优先级任务 M（优先级2）正在运行（不需要互斥量）
  低优先级任务 L（优先级1）持有互斥量

  结果：H 被 M 阻塞，因为 L 无法运行（被 M 抢占）

优先级继承解决方案：
  当 H 等待 L 持有的互斥量时，L 的优先级临时提升到 H 的优先级（3）
  L 现在可以抢占 M，尽快完成并释放互斥量
  L 释放互斥量后，优先级恢复为 1
  H 获得互斥量，继续运行
```

**源码实现**（`queue.c`，互斥量获取时）：

```c
/* 当任务等待互斥量时，提升持有者的优先级 */
if( pxQueue->u.xSemaphore.xMutexHolder != NULL )
{
    /* 如果持有者优先级低于等待者，提升持有者优先级 */
    if( pxQueue->u.xSemaphore.xMutexHolder->uxPriority < pxCurrentTCB->uxPriority )
    {
        /* 临时提升持有者优先级 */
        vTaskPriorityInherit( pxQueue->u.xSemaphore.xMutexHolder );
    }
}
```

### 6.4 ISR 安全的 API

FreeRTOS 为每个可能在中断中使用的 API 提供了 `FromISR` 版本：

```c
/* 任务中使用 */
xQueueSend( xQueue, &data, portMAX_DELAY );

/* 中断中使用 */
BaseType_t xHigherPriorityTaskWoken = pdFALSE;
xQueueSendFromISR( xQueue, &data, &xHigherPriorityTaskWoken );
/* 如果唤醒了更高优先级任务，在中断退出时触发上下文切换 */
portYIELD_FROM_ISR( xHigherPriorityTaskWoken );
```

**为什么需要两套 API？** 任务版本可以阻塞（等待队列有空间），中断版本不能阻塞（中断不能睡眠）。中断版本通过 `xHigherPriorityTaskWoken` 参数通知调用者是否需要在中断退出时切换任务。

---

## 七、软件定时器（timers.c）

### 7.1 设计思路：定时器服务任务

FreeRTOS 的软件定时器不在中断中执行回调，而是通过一个专门的**定时器服务任务**（Timer Service Task，也叫 Daemon Task）来执行：

```
应用任务                    定时器服务任务
    │                            │
    │  xTimerStart()             │
    │──────────────────────────▶│
    │  （发消息到定时器队列）      │
    │                            │  处理命令
    │                            │  检查到期定时器
    │                            │  执行回调函数
    │◀──────────────────────────│
    │                            │
```

**为什么不在 tick 中断中执行回调？** 中断中执行时间不确定的回调会影响系统实时性。将回调放在任务中执行，可以通过优先级控制其对系统的影响，也可以在回调中使用大多数 FreeRTOS API。

### 7.2 定时器数据结构

```c
/* timers.c，约第 90 行 */
typedef struct tmrTimerControl
{
    const char * pcTimerName;              /* 定时器名称（调试用） */
    ListItem_t xTimerListItem;             /* 链表节点（挂在活跃定时器列表上） */
    TickType_t xTimerPeriodInTicks;        /* 定时器周期（tick 数） */
    void * pvTimerID;                      /* 用户自定义 ID（区分多个使用同一回调的定时器） */
    TimerCallbackFunction_t pxCallbackFunction; /* 回调函数 */
    uint8_t ucStatus;                      /* 状态位：活跃/静态分配/自动重载 */
} xTIMER;
typedef xTIMER Timer_t;

/* 活跃定时器列表（按到期时间排序） */
PRIVILEGED_DATA static List_t xActiveTimerList1;
PRIVILEGED_DATA static List_t xActiveTimerList2;  /* 处理溢出 */
PRIVILEGED_DATA static List_t * pxCurrentTimerList;
PRIVILEGED_DATA static List_t * pxOverflowTimerList;

/* 命令队列（应用任务通过此队列控制定时器） */
PRIVILEGED_DATA static QueueHandle_t xTimerQueue = NULL;
```

### 7.3 定时器服务任务主循环

```c
/* timers.c，prvTimerTask() */
static portTASK_FUNCTION( prvTimerTask, pvParameters )
{
    TickType_t xNextExpireTime;
    BaseType_t xListWasEmpty;

    for( ; ; )
    {
        /* 第一步：获取最近的到期时间 */
        xNextExpireTime = prvGetNextExpireTime( &xListWasEmpty );

        /* 第二步：等待到期或收到命令（阻塞在队列上） */
        prvProcessTimerOrBlockTask( xNextExpireTime, xListWasEmpty );

        /* 第三步：处理队列中的命令（启动/停止/重置定时器） */
        prvProcessReceivedCommands();
    }
}
```

### 7.4 单次定时器 vs 自动重载定时器

```c
/* 单次定时器：到期后自动停止 */
TimerHandle_t xTimer = xTimerCreate( "OneShot", pdMS_TO_TICKS(1000),
                                     pdFALSE,  /* 不自动重载 */
                                     NULL, vTimerCallback );

/* 自动重载定时器：到期后自动重新启动 */
TimerHandle_t xTimer = xTimerCreate( "AutoReload", pdMS_TO_TICKS(100),
                                     pdTRUE,   /* 自动重载 */
                                     NULL, vTimerCallback );
```

---

## 八、事件组（event_groups.c）

### 8.1 事件组的本质

事件组是一个**位图**（`EventBits_t`，通常是 32 位），每一位代表一个事件。任务可以等待一个或多个位被置位：

```c
/* event_groups.c，约第 55 行 */
typedef struct EventGroupDef_t
{
    EventBits_t uxEventBits;              /* 事件位图（32位，低24位可用） */
    List_t xTasksWaitingForBits;          /* 等待事件的任务列表 */
} EventGroup_t;
```

### 8.2 等待事件：`xEventGroupWaitBits()`

```c
/* 等待 BIT_0 和 BIT_1 都被置位（AND 等待） */
EventBits_t uxBits = xEventGroupWaitBits(
    xEventGroup,
    BIT_0 | BIT_1,   /* 等待这些位 */
    pdTRUE,          /* 等到后自动清除这些位 */
    pdTRUE,          /* 等待所有位（AND），pdFALSE 为等待任意位（OR） */
    portMAX_DELAY    /* 永久等待 */
);
```

**事件组 vs 信号量的选择**：
- 需要等待**多个事件同时发生**（AND）→ 用事件组
- 需要等待**任意一个事件发生**（OR）→ 用事件组
- 需要**计数**（如资源池）→ 用计数信号量
- 需要**互斥访问**共享资源 → 用互斥量

### 8.3 事件组的同步屏障

`xEventGroupSync()` 实现了多任务同步屏障——所有任务都到达某个点后，才能继续执行：

```c
/* 任务 A */
xEventGroupSync( xEventGroup, BIT_A, BIT_A | BIT_B | BIT_C, portMAX_DELAY );
/* 等待 A、B、C 都置位后继续 */

/* 任务 B */
xEventGroupSync( xEventGroup, BIT_B, BIT_A | BIT_B | BIT_C, portMAX_DELAY );

/* 任务 C */
xEventGroupSync( xEventGroup, BIT_C, BIT_A | BIT_B | BIT_C, portMAX_DELAY );
```

---

## 九、内存管理（portable/MemMang/）

### 9.1 五种方案对比

FreeRTOS 提供 5 种内存管理方案，根据应用需求选择：

| 方案 | 文件 | 特点 | 适用场景 |
|------|------|------|----------|
| heap_1 | `heap_1.c` | 只分配，不释放；最简单 | 任务创建后不删除的系统 |
| heap_2 | `heap_2.c` | 支持释放，但不合并碎片 | 固定大小反复分配/释放 |
| heap_3 | `heap_3.c` | 封装标准 `malloc/free` | 已有 libc 的系统 |
| heap_4 | `heap_4.c` | 支持释放，**合并相邻碎片** | **最常用，推荐** |
| heap_5 | `heap_5.c` | 支持多个不连续内存区域 | 内存不连续的系统 |

### 9.2 heap_4 实现原理（最常用）

heap_4 使用**首次适配算法**（First Fit）+ **相邻块合并**：

```c
/* heap_4.c，核心数据结构 */

/* 空闲块链表节点 */
typedef struct A_BLOCK_LINK
{
    struct A_BLOCK_LINK * pxNextFreeBlock; /* 下一个空闲块 */
    size_t xBlockSize;                     /* 块大小（含头部） */
} BlockLink_t;

/* 全局堆空间（静态数组） */
static uint8_t ucHeap[ configTOTAL_HEAP_SIZE ];

/* 空闲链表的起始和结束哨兵 */
static BlockLink_t xStart;
static BlockLink_t * pxEnd = NULL;
```

**分配流程**（`pvPortMalloc()`）：

```
请求分配 N 字节
     │
     ▼
对齐到 portBYTE_ALIGNMENT（通常8字节）
     │
     ▼
遍历空闲链表，找第一个 >= N 的块
     │
     ├─ 找到 → 从链表移除
     │         如果剩余空间 > 最小块大小，分裂为两块
     │         标记为已分配（设置 MSB）
     │         返回用户指针（跳过头部）
     │
     └─ 未找到 → 返回 NULL（触发 malloc 失败钩子）
```

**释放流程**（`vPortFree()`）：

```
释放指针 p
     │
     ▼
p 向前偏移 sizeof(BlockLink_t)，找到块头部
     │
     ▼
清除已分配标记
     │
     ▼
prvInsertBlockIntoFreeList()
     │
     ├─ 按地址顺序插入空闲链表
     │
     ├─ 与前一个块相邻？→ 合并
     │
     └─ 与后一个块相邻？→ 合并
```

**关键设计**：`xBlockSize` 的最高位（MSB）用于标记块是否已分配（`heapBLOCK_ALLOCATED_BITMASK`）。这是一个巧妙的设计——不需要额外的字段来记录分配状态，只用一个位。代价是可分配的最大单块大小减半（对于 32 位系统，最大 2GB，实际不受影响）。

### 9.3 堆保护（可选）

```c
/* 当 configENABLE_HEAP_PROTECTOR == 1 时，启用堆指针混淆 */
#define heapPROTECT_BLOCK_POINTER( pxBlock ) \
    ( ( BlockLink_t * ) ( ( ( portPOINTER_SIZE_TYPE ) ( pxBlock ) ) ^ xHeapCanary ) )
```

堆保护通过 XOR 随机 canary 值来混淆内部指针，使堆溢出导致的指针损坏更容易被检测到（随机值使损坏后的指针指向随机地址，触发 assert 或 HardFault）。

---

## 十、移植层（portable/）

### 10.1 移植层的职责

移植层是 FreeRTOS 与硬件之间的桥梁，每个平台需要实现以下接口：

| 函数/宏 | 说明 | 实现位置 |
|---------|------|----------|
| `pxPortInitialiseStack()` | 初始化任务栈 | `port.c` |
| `xPortStartScheduler()` | 启动调度器（配置 SysTick/PendSV） | `port.c` |
| `vPortEndScheduler()` | 停止调度器 | `port.c` |
| `portYIELD()` | 触发上下文切换 | `portmacro.h` |
| `portDISABLE_INTERRUPTS()` | 关中断（进入临界区） | `portmacro.h` |
| `portENABLE_INTERRUPTS()` | 开中断（退出临界区） | `portmacro.h` |
| `portSET_INTERRUPT_MASK_FROM_ISR()` | ISR 中进入临界区 | `portmacro.h` |
| `SysTick_Handler` / `xPortSysTickHandler` | tick 中断处理 | `port.c` |
| `PendSV_Handler` / `xPortPendSVHandler` | 上下文切换中断 | `port.c`（汇编） |

### 10.2 ARM Cortex-M 的上下文切换机制

以最常用的 ARM Cortex-M3/M4 为例，上下文切换利用了硬件特性：

```
上下文切换流程（ARM Cortex-M）：

1. 触发 PendSV 中断（最低优先级）
   portYIELD() → 设置 ICSR 寄存器的 PENDSVSET 位

2. 硬件自动保存（进入中断时）：
   xPSR, PC, LR, R12, R3, R2, R1, R0 → 压入当前任务栈

3. PendSV_Handler（汇编）手动保存：
   R11, R10, R9, R8, R7, R6, R5, R4 → 压入当前任务栈
   更新 pxCurrentTCB->pxTopOfStack = SP

4. 调用 vTaskSwitchContext()
   更新 pxCurrentTCB 指向新任务

5. 恢复新任务上下文（汇编）：
   SP = pxCurrentTCB->pxTopOfStack
   弹出 R11-R4

6. 硬件自动恢复（退出中断时）：
   弹出 R0-R3, R12, LR, PC, xPSR
   PC = 新任务的下一条指令地址
```

**设计洞察**：ARM Cortex-M 的硬件自动保存/恢复机制（8个寄存器）大大简化了上下文切换的汇编代码。FreeRTOS 只需手动保存剩余的 8 个寄存器（R4-R11），整个切换过程只需约 12 条汇编指令。

---

## 十一、FreeRTOSConfig.h 配置指南

### 11.1 必须配置的项目

```c
/* 硬件相关 */
#define configCPU_CLOCK_HZ          ( 168000000UL )  /* CPU 主频（Hz） */
#define configTICK_RATE_HZ          ( 1000 )          /* tick 频率（Hz），通常1000=1ms/tick */

/* 任务相关 */
#define configMAX_PRIORITIES        ( 5 )             /* 最大优先级数（0到4） */
#define configMINIMAL_STACK_SIZE    ( 128 )           /* 空闲任务栈大小（字，非字节！） */
#define configMAX_TASK_NAME_LEN     ( 16 )            /* 任务名最大长度 */

/* 内存相关 */
#define configTOTAL_HEAP_SIZE       ( 4096 )          /* 堆大小（字节） */
```

### 11.2 调度策略配置

```c
/* 抢占式调度（推荐） vs 协作式调度 */
#define configUSE_PREEMPTION        1  /* 1=抢占式，0=协作式 */

/* 时间片轮转（同优先级任务轮转） */
#define configUSE_TIME_SLICING      1  /* 1=启用，0=禁用 */

/* 硬件优化的任务选择（使用 CLZ 指令，O(1) 找最高优先级） */
#define configUSE_PORT_OPTIMISED_TASK_SELECTION  1  /* 仅部分平台支持 */

/* 低功耗 tickless 模式 */
#define configUSE_TICKLESS_IDLE     0  /* 1=启用，需要移植层支持 */
```

### 11.3 功能开关（按需裁剪）

```c
/* 软件定时器 */
#define configUSE_TIMERS            1
#define configTIMER_TASK_PRIORITY   ( configMAX_PRIORITIES - 1 )
#define configTIMER_TASK_STACK_DEPTH configMINIMAL_STACK_SIZE
#define configTIMER_QUEUE_LENGTH    10

/* 互斥量 */
#define configUSE_MUTEXES           1
#define configUSE_RECURSIVE_MUTEXES 1

/* 任务通知（轻量级信号量替代品） */
#define configUSE_TASK_NOTIFICATIONS 1
#define configTASK_NOTIFICATION_ARRAY_ENTRIES 1

/* 事件组 */
#define configUSE_EVENT_GROUPS      1

/* 流缓冲区 */
#define configUSE_STREAM_BUFFERS    1

/* 调试辅助 */
#define configCHECK_FOR_STACK_OVERFLOW  2  /* 0=不检查，1=快速检查，2=完整检查 */
#define configUSE_TRACE_FACILITY        0  /* 1=启用追踪（增加TCB大小） */
#define configGENERATE_RUN_TIME_STATS   0  /* 1=统计各任务CPU使用率 */
```

### 11.4 INCLUDE_ 宏（API 裁剪）

```c
/* 只包含需要的 API，减少代码大小 */
#define INCLUDE_vTaskPrioritySet        1
#define INCLUDE_uxTaskPriorityGet       1
#define INCLUDE_vTaskDelete             1
#define INCLUDE_vTaskSuspend            1
#define INCLUDE_xTaskDelayUntil         1
#define INCLUDE_vTaskDelay              1
#define INCLUDE_xTaskGetSchedulerState  1
#define INCLUDE_xTaskGetCurrentTaskHandle 1
#define INCLUDE_uxTaskGetStackHighWaterMark 0  /* 关闭以节省代码 */
```

### 11.5 中断优先级配置（ARM Cortex-M 特别注意）

```c
/* ARM Cortex-M 的中断优先级是"数值越小，优先级越高"！
 * 这与直觉相反，是常见的配置错误来源。
 */

/* 内核中断优先级（tick 和 PendSV）：必须是最低优先级 */
#define configKERNEL_INTERRUPT_PRIORITY         255  /* 最低优先级 */

/* 可以调用 FreeRTOS API 的最高中断优先级
 * 优先级数值 < 此值的中断不能调用 FreeRTOS API！
 * 这些高优先级中断永远不会被 FreeRTOS 屏蔽，延迟最小
 */
#define configMAX_SYSCALL_INTERRUPT_PRIORITY    191  /* 优先级5（共8级时） */
```

> ⚠️ **常见错误**：在优先级高于 `configMAX_SYSCALL_INTERRUPT_PRIORITY` 的中断中调用 FreeRTOS API（非 `FromISR` 版本），会导致系统崩溃。这是 Cortex-M 上最常见的 FreeRTOS 使用错误。

---

## 十二、任务通知（Task Notifications）

### 12.1 为什么需要任务通知？

任务通知是 FreeRTOS v8.2 引入的轻量级通信机制，相比队列/信号量有显著优势：

| 对比项 | 队列/信号量 | 任务通知 |
|--------|------------|---------|
| 内存开销 | 需要单独创建对象 | 内置在 TCB 中（0额外开销） |
| 速度 | 较慢（需要操作队列结构） | 快约 45%（直接操作 TCB） |
| 灵活性 | 多对多通信 | 只能一对一（发给特定任务） |
| 功能 | 完整 | 可模拟信号量、事件组、邮箱 |

### 12.2 任务通知 API

```c
/* 发送通知（可以设置值、增加值、或只通知） */
xTaskNotify( xTaskHandle, ulValue, eAction );
/* eAction 可以是：
 *   eNoAction          - 只通知，不修改值
 *   eSetBits           - 按位 OR（模拟事件组）
 *   eIncrement         - 值加1（模拟信号量）
 *   eSetValueWithOverwrite  - 直接设置值（模拟邮箱，覆盖旧值）
 *   eSetValueWithoutOverwrite - 设置值（如果旧值未读则失败）
 */

/* 等待通知 */
uint32_t ulNotificationValue;
xTaskNotifyWait( ulBitsToClearOnEntry,   /* 进入等待时清除的位 */
                 ulBitsToClearOnExit,    /* 退出等待时清除的位 */
                 &ulNotificationValue,   /* 接收通知值 */
                 xTicksToWait );         /* 超时时间 */

/* 从 ISR 发送通知 */
BaseType_t xHigherPriorityTaskWoken = pdFALSE;
xTaskNotifyFromISR( xTaskHandle, ulValue, eAction, &xHigherPriorityTaskWoken );
portYIELD_FROM_ISR( xHigherPriorityTaskWoken );
```

---

## 十三、SMP 多核支持（FreeRTOS v10.6+）

### 13.1 SMP 扩展

FreeRTOS 从 v10.6 开始支持 SMP（对称多处理），通过 `configNUMBER_OF_CORES` 配置核心数：

```c
/* FreeRTOSConfig.h */
#define configNUMBER_OF_CORES   2  /* 双核 */
```

**SMP 对 TCB 的扩展**：

```c
/* tasks.c，TCB 中的 SMP 相关字段 */
#if ( configNUMBER_OF_CORES > 1 )
    volatile BaseType_t xTaskRunState;  /* 运行状态：
                                         *   >= 0：在第 xTaskRunState 个核上运行
                                         *   taskTASK_NOT_RUNNING (-1)：未运行
                                         *   taskTASK_SCHEDULED_TO_YIELD (-2)：待让出
                                         */
    UBaseType_t uxTaskAttributes;       /* 任务属性（如是否是空闲任务） */
    UBaseType_t uxCoreAffinityMask;     /* 核心亲和性掩码（哪些核可以运行此任务） */
#endif
```

### 13.2 SMP 调度策略

```c
/* 允许不同优先级任务同时在多核上运行 */
#define configRUN_MULTIPLE_PRIORITIES   1

/* 核心亲和性（将任务绑定到特定核） */
#define configUSE_CORE_AFFINITY         1
vTaskCoreAffinitySet( xTask, ( 1 << 0 ) | ( 1 << 1 ) ); /* 允许在核0和核1上运行 */
```

---

## 十四、调试与诊断

### 14.1 栈溢出检测

```c
/* FreeRTOSConfig.h */
#define configCHECK_FOR_STACK_OVERFLOW  2

/* 应用代码中实现回调 */
void vApplicationStackOverflowHook( TaskHandle_t xTask, char * pcTaskName )
{
    /* 栈溢出时调用此函数
     * xTask：溢出的任务句柄
     * pcTaskName：任务名（可能已损坏，使用 pxCurrentTCB 更可靠）
     */
    configASSERT( 0 );  /* 触发断言，停止系统 */
}
```

**两种检测方式**：
- `configCHECK_FOR_STACK_OVERFLOW = 1`：检查栈指针是否越界（快速，但可能漏检）
- `configCHECK_FOR_STACK_OVERFLOW = 2`：检查栈末尾的已知填充值（`0xA5`）是否被覆盖（更可靠）

### 14.2 运行时统计

```c
/* FreeRTOSConfig.h */
#define configGENERATE_RUN_TIME_STATS   1
#define portCONFIGURE_TIMER_FOR_RUN_TIME_STATS()  /* 配置高精度计时器 */
#define portGET_RUN_TIME_COUNTER_VALUE()          /* 读取计时器值 */

/* 获取所有任务的运行时间统计 */
char pcWriteBuffer[512];
vTaskGetRunTimeStats( pcWriteBuffer );
printf( "%s", pcWriteBuffer );
/* 输出示例：
 * Task Name    Abs Time    % Time
 * Task1        12345       45%
 * Task2        8765        32%
 * IDLE         6543        23%
 */
```

### 14.3 任务列表查看

```c
/* 获取所有任务状态 */
char pcWriteBuffer[512];
vTaskList( pcWriteBuffer );
printf( "%s", pcWriteBuffer );
/* 输出示例：
 * Name         State  Priority  Stack  Num
 * Task1        R      3         128    1
 * Task2        B      2         256    2
 * IDLE         R      0         64     3
 * Tmr Svc      B      4         128    4
 *
 * State: R=就绪, B=阻塞, S=挂起, D=已删除, X=运行中
 */
```

---

## 十五、关键设计洞察汇总

| 设计决策 | FreeRTOS 的选择 | 代价/收益 |
|----------|----------------|-----------|
| **IPC 统一实现** | 信号量/互斥量基于队列实现 | 代码量少，但理解成本高 |
| **链表哨兵节点** | `xListEnd.xItemValue = portMAX_DELAY` | 简化边界判断，O(1) 插入 |
| **双延时列表** | `xDelayedTaskList1/2` 交替使用 | 优雅处理 tick 溢出，无需特殊判断 |
| **TCB 内嵌通知** | 任务通知直接存在 TCB 中 | 零额外内存，速度快 45% |
| **静态+动态双模式** | 同时支持两种内存分配 | 适应安全关键系统需求 |
| **5种内存方案** | heap_1~heap_5 可选 | 灵活适配不同场景 |
| **条件编译裁剪** | 大量 `#if configXXX` | 最小化代码和内存占用 |
| **移植层抽象** | `portable/` 统一接口 | 支持 50+ 平台，移植成本低 |
| **SMP 支持** | v10.6+ 原生支持多核 | 代码复杂度增加，但向前兼容 |

---

## 十六、核心源码文件索引

| 文件 | 关键函数/结构 | 学习重点 |
|------|-------------|---------|
| `list.c` | `vListInsert`, `vListInsertEnd`, `uxListRemove` | 链表操作，调度基础 |
| `include/list.h` | `ListItem_t`, `List_t`, `listGET_OWNER_OF_NEXT_ENTRY` | 数据结构定义 |
| `tasks.c:400` | `TCB_t` 结构体 | 任务控制块字段含义 |
| `tasks.c:490` | `pxReadyTasksLists[]`, `pxDelayedTaskList` | 全局调度数据 |
| `tasks.c:1741` | `xTaskCreate()` | 任务创建流程 |
| `tasks.c:1815` | `prvInitialiseNewTask()` | 栈初始化 |
| `tasks.c:3704` | `vTaskStartScheduler()` | 调度器启动 |
| `tasks.c:4740` | `xTaskIncrementTick()` | tick 中断处理 |
| `tasks.c:4900` | `vTaskSwitchContext()` | 上下文切换选择 |
| `queue.c:100` | `Queue_t` 结构体 | 队列/信号量底层结构 |
| `timers.c:90` | `Timer_t` 结构体 | 定时器数据结构 |
| `event_groups.c:55` | `EventGroup_t` 结构体 | 事件组数据结构 |
| `portable/MemMang/heap_4.c` | `pvPortMalloc`, `vPortFree` | 内存管理实现 |
| `portable/GCC/ARM_CM3/port.c` | `xPortStartScheduler`, `PendSV_Handler` | ARM 移植层 |
| `examples/template_configuration/FreeRTOSConfig.h` | 所有配置宏 | 配置参考 |

---

## 附录：常见问题与陷阱

### A.1 任务函数必须是无限循环

```c
/* ❌ 错误：任务函数返回会导致未定义行为 */
void vBadTask( void * pvParameters )
{
    /* 做一些事情 */
    return;  /* 不能这样！ */
}

/* ✅ 正确：任务函数必须是无限循环 */
void vGoodTask( void * pvParameters )
{
    for( ; ; )
    {
        /* 做一些事情 */
        vTaskDelay( pdMS_TO_TICKS( 100 ) );
    }
    /* 如果确实需要结束，调用 vTaskDelete(NULL) */
}
```

### A.2 栈大小单位是"字"不是"字节"

```c
/* ❌ 错误：以为是字节 */
xTaskCreate( vTask, "Task", 512, NULL, 1, NULL );  /* 实际只有 512 字节！ */

/* ✅ 正确：512 字 = 2048 字节（32位系统） */
xTaskCreate( vTask, "Task", 512, NULL, 1, NULL );  /* 512 * 4 = 2048 字节 */

/* 更清晰的写法 */
#define TASK_STACK_SIZE  ( 512 )  /* 单位：字（StackType_t） */
```

### A.3 中断中只能使用 `FromISR` 版本的 API

```c
/* ❌ 错误：在中断中使用普通 API */
void UART_IRQHandler( void )
{
    xQueueSend( xQueue, &data, 0 );  /* 可能导致崩溃！ */
}

/* ✅ 正确：使用 FromISR 版本 */
void UART_IRQHandler( void )
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    xQueueSendFromISR( xQueue, &data, &xHigherPriorityTaskWoken );
    portYIELD_FROM_ISR( xHigherPriorityTaskWoken );
}
```

### A.4 `vTaskDelay` vs `vTaskDelayUntil`

```c
/* vTaskDelay：从调用时刻开始延时（执行时间影响周期） */
void vTask( void * pvParameters )
{
    for( ; ; )
    {
        doWork();           /* 假设耗时 10ms */
        vTaskDelay( 100 ); /* 再等 100ms，实际周期 = 10 + 100 = 110ms */
    }
}

/* vTaskDelayUntil：精确周期（不受执行时间影响） */
void vTask( void * pvParameters )
{
    TickType_t xLastWakeTime = xTaskGetTickCount();
    for( ; ; )
    {
        doWork();                              /* 耗时 10ms */
        vTaskDelayUntil( &xLastWakeTime, 100 ); /* 精确 100ms 周期 */
    }
}
```

### A.5 `pdMS_TO_TICKS` 宏转换时间

```c
/* 不要硬编码 tick 数，使用宏转换 */
vTaskDelay( 100 );                    /* ❌ 依赖 configTICK_RATE_HZ */
vTaskDelay( pdMS_TO_TICKS( 100 ) );   /* ✅ 始终是 100 毫秒 */
```

---

## 附录 B：调试环境搭建指南

调试 FreeRTOS-Kernel 源码**不需要真实硬件**。内核本身提供了三种无硬件调试方案，从易到难依次推荐：

### B.1 方案总览

| 方案 | 平台 | 移植层 | 难度 | 推荐度 |
|------|------|--------|------|--------|
| **POSIX 仿真** | Linux / macOS | `portable/ThirdParty/GCC/Posix/` | ⭐ | ★★★★★ 首选 |
| **Windows 仿真** | Windows 10/11 | `portable/MSVC-MingW/` | ⭐⭐ | ★★★★ |
| **QEMU + ARM** | 跨平台 | `portable/GCC/ARM_CM3/` 等 | ⭐⭐⭐ | ★★★ 接近真实硬件 |

---

### B.2 方案一：POSIX 仿真（Linux / macOS）——最推荐

#### 原理

`portable/ThirdParty/GCC/Posix/port.c` 将 FreeRTOS 任务映射为 **POSIX 线程（pthread）**，用 `SIGALRM` 信号模拟 tick 中断，用条件变量实现任务切换。每个 FreeRTOS 任务对应一个真实的 pthread，因此 GDB 可以直接查看每个任务的调用栈。

```
FreeRTOS 任务 A  ←→  pthread_A（阻塞在 sigwait）
FreeRTOS 任务 B  ←→  pthread_B（正在运行）
tick 中断        ←→  SIGALRM 信号处理函数
上下文切换       ←→  条件变量 signal/wait
```

#### 环境准备

```bash
# Ubuntu / Debian
sudo apt install gcc cmake gdb make

# macOS（需要 Homebrew）
brew install cmake gcc gdb
```

#### 编译运行

```bash
# 克隆仓库
git clone https://github.com/FreeRTOS/FreeRTOS-Kernel.git
cd FreeRTOS-Kernel

# 配置 CMake，指定 POSIX 移植层
cmake -B build -S . \
    -DFREERTOS_PORT=GCC_POSIX \
    -DFREERTOS_HEAP=heap_4

# 编译
cmake --build build

# 运行（cmake_example 示例）
./build/examples/cmake_example/freertos_cmake_example
```

#### 用 GDB 调试

```bash
# 编译时加入调试信息
cmake -B build -S . -DFREERTOS_PORT=GCC_POSIX -DCMAKE_BUILD_TYPE=Debug
cmake --build build

# 启动 GDB
gdb ./build/examples/cmake_example/freertos_cmake_example
```

**GDB 常用调试命令**：

```gdb
# 在任务创建处打断点
(gdb) break xTaskCreate
(gdb) break prvInitialiseNewTask

# 在 tick 处理函数打断点（观察调度过程）
(gdb) break xTaskIncrementTick
(gdb) break vTaskSwitchContext

# 查看所有线程（每个线程对应一个 FreeRTOS 任务）
(gdb) info threads

# 切换到某个任务线程
(gdb) thread 2

# 查看该任务的调用栈
(gdb) backtrace

# 查看当前 TCB 内容
(gdb) print *pxCurrentTCB

# 查看就绪列表（优先级 1 的就绪链表）
(gdb) print pxReadyTasksLists[1]

# 查看 tick 计数
(gdb) print xTickCount

# 单步执行
(gdb) next
(gdb) step

# 继续运行
(gdb) continue
```

> 💡 **macOS 特别提示**：macOS 默认调试器是 LLDB，需要抑制 `SIGUSR1` 信号干扰（POSIX 移植层用此信号切换任务）：
> ```bash
> # 在 ~/.lldbinit 中添加：
> process handle SIGUSR1 -n true -p false -s false
> ```

#### 用 VS Code 调试（图形界面）

安装 **C/C++ 扩展**后，创建 `.vscode/launch.json`：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FreeRTOS POSIX Debug",
            "type": "cppdbg",
            "request": "launch",
            "program": "${workspaceFolder}/build/examples/cmake_example/freertos_cmake_example",
            "args": [],
            "stopAtEntry": false,
            "cwd": "${workspaceFolder}",
            "environment": [],
            "externalConsole": false,
            "MIMode": "gdb",
            "setupCommands": [
                {
                    "description": "启用整齐打印",
                    "text": "-enable-pretty-printing",
                    "ignoreFailures": true
                }
            ]
        }
    ]
}
```

在 VS Code 中直接点击断点、查看变量、单步调试，体验与调试普通 C 程序完全相同。

---

### B.3 方案二：Windows 仿真（MSVC / MinGW）

#### 原理

`portable/MSVC-MingW/port.c` 将 FreeRTOS 任务映射为 **Windows 线程**，用高精度多媒体定时器（`timeSetEvent`）模拟 tick 中断，用 Windows 事件对象（`CreateEvent`）实现任务切换。

> ⚠️ **注意**：Windows 仿真要求**多核 CPU**（代码中有检查），且定时精度受 Windows 调度影响，不适合测试实时性，但完全够用于源码学习。

#### 环境准备

**方式 A：MinGW-w64（推荐，免费）**

```powershell
# 使用 winget 安装 MinGW
winget install MSYS2.MSYS2

# 在 MSYS2 终端中安装工具链
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-gdb make
```

**方式 B：Visual Studio 2022（功能最强）**

安装 Visual Studio 2022 Community（免费），勾选"使用 C++ 的桌面开发"工作负载。

#### 编译运行（MinGW）

```powershell
# 在 MSYS2 MinGW64 终端中执行
cmake -B build -S . -G "MinGW Makefiles" -DFREERTOS_PORT=MSVC_MINGW -DFREERTOS_HEAP=heap_4
cmake --build build
./build/examples/cmake_example/freertos_cmake_example.exe
```

#### 编译运行（Visual Studio）

```powershell
# 在 PowerShell 中执行
cmake -B build -S . -G "Visual Studio 17 2022" -DFREERTOS_PORT=MSVC_MINGW -DFREERTOS_HEAP=heap_4
# 用 Visual Studio 打开 build/FreeRTOS-Kernel.sln
# 直接 F5 启动调试
```

Visual Studio 调试体验极佳：可以在"线程"窗口看到所有 FreeRTOS 任务对应的线程，在"监视"窗口实时查看 `pxCurrentTCB`、`xTickCount` 等全局变量。

---

### B.4 方案三：QEMU 仿真（接近真实硬件）

当需要验证与硬件相关的行为（中断优先级、上下文切换汇编、MPU 等）时，使用 QEMU 模拟真实 ARM 芯片。

#### 原理

QEMU 完整模拟 ARM Cortex-M 处理器，包括 SysTick、PendSV、NVIC 等外设，使用真实的 ARM 移植层（`portable/GCC/ARM_CM3/` 等），行为与真实硬件完全一致。

#### 环境准备

```bash
# Ubuntu
sudo apt install qemu-system-arm gcc-arm-none-eabi gdb-multiarch cmake

# macOS
brew install qemu arm-none-eabi-gcc arm-none-eabi-gdb cmake

# Windows（推荐在 WSL2 中操作）
# 在 WSL2 Ubuntu 中执行上述 Ubuntu 命令
```

#### 编译（针对 ARM Cortex-M3）

```bash
# 使用 ARM 交叉编译器，指定 ARM_CM3 移植层
cmake -B build -S . \
    -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/arm-none-eabi.cmake \
    -DFREERTOS_PORT=GCC_ARM_CM3 \
    -DFREERTOS_HEAP=heap_4 \
    -DCMAKE_BUILD_TYPE=Debug

cmake --build build
```

> 💡 如果工程没有内置 ARM 工具链文件，可以手动指定：
> ```cmake
> # arm-none-eabi.cmake
> set(CMAKE_SYSTEM_NAME Generic)
> set(CMAKE_C_COMPILER arm-none-eabi-gcc)
> set(CMAKE_C_FLAGS "-mcpu=cortex-m3 -mthumb -specs=nosys.specs")
> ```

#### 用 QEMU 运行并 GDB 调试

```bash
# 终端 1：启动 QEMU，模拟 STM32 Cortex-M3，等待 GDB 连接
qemu-system-arm \
    -machine lm3s6965evb \
    -cpu cortex-m3 \
    -nographic \
    -kernel build/freertos_example.elf \
    -S -gdb tcp::3333
# -S：启动后暂停等待 GDB
# -gdb tcp::3333：在 3333 端口监听 GDB 连接

# 终端 2：启动 GDB 并连接
gdb-multiarch build/freertos_example.elf
(gdb) target remote :3333
(gdb) break main
(gdb) continue
```

#### QEMU 调试的独特优势

```gdb
# 查看 ARM 寄存器（真实 CPU 寄存器状态）
(gdb) info registers

# 查看 PendSV 中断向量（上下文切换入口）
(gdb) x/4x 0xE000ED04   # 查看 ICSR 寄存器（PendSV 状态）

# 在 PendSV_Handler 打断点（观察真实上下文切换）
(gdb) break PendSV_Handler
(gdb) break xPortPendSVHandler

# 查看 SysTick 寄存器（tick 定时器）
(gdb) x/4x 0xE000E010   # SysTick CTRL
(gdb) x/4x 0xE000E014   # SysTick LOAD

# 反汇编当前函数（查看真实 ARM 汇编）
(gdb) disassemble
```

---

### B.5 三种方案的选择建议

```
你的目标是什么？
│
├─ 学习 FreeRTOS 调度逻辑、数据结构、IPC 机制
│   └─ ✅ 用 POSIX 仿真（Linux/macOS）或 Windows 仿真
│       最简单，GDB/VS Code 调试体验最好
│
├─ 验证上下文切换汇编、中断优先级、MPU 行为
│   └─ ✅ 用 QEMU + ARM Cortex-M
│       行为与真实硬件完全一致
│
├─ 在真实项目中调试（已有 STM32/ESP32 等硬件）
│   └─ ✅ 用 OpenOCD + GDB + J-Link/ST-Link
│       连接真实硬件，最终验证
│
└─ 快速验证某个 API 的行为（不想搭环境）
    └─ ✅ 用 POSIX 仿真 + printf 打印
        5 分钟内可以跑起来
```

### B.6 调试时的关键观测点

无论使用哪种方案，以下是调试 FreeRTOS 源码时最有价值的观测点：

```c
/* 1. 观察就绪列表（调度器核心数据） */
pxReadyTasksLists[0]   /* 优先级 0 的就绪任务 */
pxReadyTasksLists[1]   /* 优先级 1 的就绪任务 */
uxTopReadyPriority     /* 当前最高就绪优先级 */

/* 2. 观察当前运行任务 */
pxCurrentTCB           /* 当前 TCB 指针 */
pxCurrentTCB->pcTaskName   /* 任务名 */
pxCurrentTCB->uxPriority   /* 当前优先级 */
pxCurrentTCB->pxTopOfStack /* 栈顶指针 */

/* 3. 观察延时列表（阻塞任务） */
pxDelayedTaskList      /* 当前延时列表 */
xNextTaskUnblockTime   /* 下次唤醒时间 */
xTickCount             /* 当前 tick 计数 */

/* 4. 观察队列状态 */
((Queue_t*)xQueue)->uxMessagesWaiting  /* 队列中的消息数 */
((Queue_t*)xQueue)->xTasksWaitingToReceive  /* 等待接收的任务 */

/* 5. 观察任务栈使用情况 */
uxTaskGetStackHighWaterMark(NULL)  /* 当前任务的栈水位线 */
```

---

*文档基于 FreeRTOS-Kernel DEVELOPMENT BRANCH 源码分析，2026年6月*
