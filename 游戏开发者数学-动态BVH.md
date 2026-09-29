# 游戏开发者的数学知识：动态边界体积层次结构（Dynamic BVH）

> 从入门到精通：一份面向程序员的完整指南。
> 涵盖直觉理解、数学基础、数据结构、构建/查询/更新算法、工业级实现技巧、性能分析，以及前置数学知识清单。

**作者**：汪亮（bertonwang）
**版本**：v1.0 ｜ **日期**：2026-09-29

---

## 目录

- [一、从直觉开始：为什么需要 BVH](#一从直觉开始为什么需要-bvh)
- [二、基本概念](#二基本概念)
- [三、数学基础](#三数学基础)
- [四、BVH 的数据结构](#四bvh-的数据结构)
- [五、静态 BVH 的构建](#五静态-bvh-的构建)
- [六、BVH 的查询](#六bvh-的查询)
- [七、从静态到动态：核心挑战](#七从静态到动态核心挑战)
- [八、动态 BVH 的四种更新策略](#八动态-bvh-的四种更新策略)
- [九、工业级实现：Fat AABB（膨胀包围盒）](#九工业级实现fat-aabb膨胀包围盒)
- [十、表面积启发式（SAH）](#十表面积启发式sah)
- [十一、完整伪代码](#十一完整伪代码)
- [十二、性能分析与调优](#十二性能分析与调优)
- [十三、实战：各引擎中的动态 BVH](#十三实战各引擎中的动态-bvh)
- [十四、常见问题与陷阱](#十四常见问题与陷阱)
- [十五、前置数学知识清单](#十五前置数学知识清单)

---

## 一、从直觉开始：为什么需要 BVH

### 1.1 朴素碰撞检测的灾难

假设场景里有 \(n\) 个物体，每帧要判断谁和谁碰撞了。

**暴力做法**：两两比较，复杂度 \(O(n^2)\)。

| 物体数 | 比较次数 |
|--------|---------|
| 100 | 4,950 |
| 1,000 | 499,500 |
| 10,000 | 49,995,000 |

1 万个物体，每帧比较近 5000 万次——在 16ms 内完成是不可能的。

### 1.2 生活中的类比

想象你要在一个图书馆里找一本书：

- **暴力法**：从第一本翻到最后一本
- **BVH 法**：先看楼层指引（整栋楼的"包围盒"）→ 再看区域标牌（楼层的"子包围盒"）→ 最后看书架编号 → 精确找到

每一级都在**快速排除大量不可能的候选者**，这就是 BVH 的核心思想：**空间剪枝**。

### 1.3 一句话定义

> **BVH（Bounding Volume Hierarchy）** 是一棵树，每个节点用一个简单几何体（包围盒）包住它管辖的所有物体。查询时自顶向下，不与当前节点包围盒相交的整棵子树一次性跳过。

---

## 二、基本概念

### 2.1 包围体（Bounding Volume）

用一个**简单几何体**紧紧包住复杂物体，使得"是否相交"的判断从"复杂形状 vs 复杂形状"降级为"简单体 vs 简单体"。

常见包围体：

| 类型 | 全称 | 形状 | 求交成本 | 紧密度 |
|------|------|------|---------|--------|
| **AABB** | Axis-Aligned Bounding Box | 各边平行于坐标轴的矩形 | 最低 | 中等 |
| **OBB** | Oriented Bounding Box | 可任意旋转的矩形 | 中等 | 高 |
| **Sphere** | 球 | 球 | 低 | 低（细长物体浪费大） |
| **k-DOP** | k-Discrete Oriented Polytope | k 个方向的板交集 | 较高 | 很高 |

> 🏆 **游戏中 95% 的 BVH 用 AABB**——因为求交只需要 3 对区间的比较（6 次浮点比较），且合并操作只需 min/max。

### 2.2 层次结构（Hierarchy）

把包围体组织成一棵**二叉树**（也有四叉/八叉变体，但二叉最常见）：

```
          [根：整个场景的 AABB]
           /                \
    [左子树 AABB]        [右子树 AABB]
      /      \             /       \
  [叶A]  [叶B+C+D]     [叶E]    [叶F+G]
```

- **叶子节点**：包含实际物体（或三角形）
- **内部节点**：包围盒 = 其所有子节点包围盒的**并集**（最小包围）
- **性质**：父节点的包围盒一定≥子节点的包围盒

### 2.3 "静态"与"动态"

| | 静态 BVH | 动态 BVH |
|---|---|---|
| 场景 | 物体不动 | 物体每帧都在动 |
| 构建 | 一次性，离线 | 需持续更新 |
| 典型应用 | 光线追踪静态场景 | 物理碰撞、AI 视野检测 |

---

## 三、数学基础

### 3.1 AABB 的数学定义

一个 3D 的 AABB 由两个点定义：

\[
\text{AABB} = \{ (x,y,z) \mid x_{\min} \le x \le x_{\max},\; y_{\min} \le y \le y_{\max},\; z_{\min} \le z \le z_{\max} \}
\]

在代码中通常表示为：

```cpp
struct AABB {
    Vec3 min;  // (xmin, ymin, zmin)
    Vec3 max;  // (xmax, ymax, zmax)
};
```

### 3.2 AABB 的核心运算

#### 合并（Union）

两个 AABB 的合并就是每个轴取 min 的 min、max 的 max：

\[
C_{\min} = \min(A_{\min}, B_{\min}), \quad C_{\max} = \max(A_{\max}, B_{\max})
\]

```cpp
AABB merge(AABB a, AABB b) {
    return { min(a.min, b.min), max(a.max, b.max) };
}
```

> 这个操作是构建 BVH 的**最核心运算**——父节点 AABB = merge(左子, 右子)。

#### 相交测试（Overlap）

两个 AABB 相交，当且仅当**三个轴上的区间全部有重叠**：

\[
\text{overlap} = (A_{x\min} \le B_{x\max}) \land (A_{x\max} \ge B_{x\min}) \land (\text{同理 } y, z)
\]

```cpp
bool overlaps(AABB a, AABB b) {
    return (a.min.x <= b.max.x && a.max.x >= b.min.x)
        && (a.min.y <= b.max.y && a.max.y >= b.min.y)
        && (a.min.z <= b.max.z && a.max.z >= b.min.z);
}
```

> 只要**任一轴**没有重叠，就能立刻判定不相交——这就是**分离轴定理（SAT）** 在 AABB 上的特例。

#### 包含测试

A 是否完全包含 B：

\[
\text{contains} = (A_{\min} \le B_{\min}) \land (A_{\max} \ge B_{\max}) \quad \text{（逐分量）}
\]

#### 表面积

\[
S = 2(w \cdot h + w \cdot d + h \cdot d)
\]

其中 \(w = x_{\max} - x_{\min}\)，\(h = y_{\max} - y_{\min}\)，\(d = z_{\max} - z_{\min}\)。

> 表面积在 SAH（表面积启发式）中扮演核心角色——详见第十节。

#### 周长（2D 简化）

Box2D 等 2D 引擎中用**周长**替代表面积：

\[
P = 2(w + h)
\]

数学意义等价：都是衡量包围盒"大小"的代理量。

### 3.3 点/射线与 AABB 的相交

**射线 vs AABB**（Slab Method）：

射线定义为 \(\mathbf{r}(t) = \mathbf{o} + t \cdot \mathbf{d}\)，\(t \ge 0\)。

对每个轴 \(i\)，计算射线进入和离开该轴板的 \(t\) 值：

\[
t_{\min,i} = \frac{\text{AABB}_{\min,i} - o_i}{d_i}, \quad t_{\max,i} = \frac{\text{AABB}_{\max,i} - o_i}{d_i}
\]

如果 \(d_i < 0\)，需交换 \(t_{\min,i}\) 和 \(t_{\max,i}\)。

然后取三个轴的交集：

\[
t_{\text{enter}} = \max(t_{\min,x}, t_{\min,y}, t_{\min,z}), \quad t_{\text{exit}} = \min(t_{\max,x}, t_{\max,y}, t_{\max,z})
\]

相交条件：\(t_{\text{enter}} \le t_{\text{exit}}\) 且 \(t_{\text{exit}} \ge 0\)。

> 这个公式在**光线追踪遍历 BVH** 时每帧要执行数百万次。

---

## 四、BVH 的数据结构

### 4.1 节点定义

```cpp
struct BVHNode {
    AABB    aabb;       // 该节点的包围盒
    int     parent;     // 父节点索引（-1 = 根）
    int     left;       // 左子节点索引（叶子时 = -1）
    int     right;      // 右子节点索引（叶子时 = -1）
    int     height;     // 子树高度（用于平衡检测）
    int     objectId;   // 叶子节点关联的物体 ID（内部节点 = -1）
    bool    isLeaf() const { return left == -1; }
};
```

### 4.2 存储方式

| 方式 | 说明 | 优点 | 缺点 |
|------|------|------|------|
| **节点池 + 索引** | 预分配数组，用整数索引引用 | 缓存友好、可复用 | 需管理空闲列表 |
| 指针链接 | 每个节点存指针 | 直观 | 内存碎片、缓存不友好 |

> 🏆 **工业实践一律用节点池**。Box2D、Bullet、Godot 全是这种方式。

### 4.3 空闲列表（Free List）

删除节点后不释放内存，而是放入空闲链表。下次插入时优先从空闲列表取：

```cpp
int allocateNode() {
    if (freeList != -1) {
        int id = freeList;
        freeList = nodes[id].next;  // next 复用为空闲链
        return id;
    }
    return nodes.size();  // 末尾扩展
}
void freeNode(int id) {
    nodes[id].next = freeList;
    freeList = id;
}
```

---

## 五、静态 BVH 的构建

先理解静态构建，再理解动态更新会容易很多。

### 5.1 自顶向下（Top-Down）

最直观的方式：

```
function buildTopDown(objects):
    if objects.count == 1:
        return createLeaf(objects[0])
    
    axis = chooseSplitAxis(objects)    // 选最长轴
    sort objects along axis
    mid = objects.count / 2
    
    node = createNode()
    node.left  = buildTopDown(objects[0..mid])
    node.right = buildTopDown(objects[mid..end])
    node.aabb  = merge(node.left.aabb, node.right.aabb)
    return node
```

**分割策略**：
- **中位数分割**：按物体中心排序取中间，保证树平衡
- **等距分割**：按空间等分，可能不平衡但某些场景更紧凑
- **SAH 分割**：用表面积启发式找最优分割位置（见第十节）

**复杂度**：\(O(n \log n)\)（排序主导）

### 5.2 自底向上（Bottom-Up）

从叶子开始，每次找到"合并代价最小"的两个节点合并。

**复杂度**：\(O(n^2)\) 朴素，\(O(n \log n)\) 优化后。

### 5.3 增量插入（Incremental Insertion）

逐个插入物体，每次沿树找到最佳位置插入新叶子。

> 这是**动态 BVH 的核心构建方式**——下面重点展开。

---

## 六、BVH 的查询

### 6.1 AABB 查询（区域查询）

"给一个查询 AABB，找出所有与它重叠的物体"——这是物理引擎**宽阶段碰撞检测**的核心操作。

```
function query(node, queryAABB, results):
    if not overlaps(node.aabb, queryAABB):
        return                              // 剪枝！整棵子树跳过
    
    if node.isLeaf():
        results.add(node.objectId)
        return
    
    query(node.left,  queryAABB, results)
    query(node.right, queryAABB, results)
```

**平均复杂度**：\(O(\log n + k)\)，\(k\) 为命中数量。
**最坏复杂度**：\(O(n)\)（所有物体都重叠——但现实中极少发生）。

### 6.2 射线查询（Raycast）

沿射线找最近的物体——用于子弹命中检测、鼠标拾取、AI 视线检测。

```
function rayQuery(node, ray):
    if not rayIntersectsAABB(ray, node.aabb):
        return INF
    
    if node.isLeaf():
        return rayIntersectsObject(ray, node.object)
    
    tLeft  = rayQuery(node.left,  ray)
    tRight = rayQuery(node.right, ray)
    return min(tLeft, tRight)
```

优化：先遍历距射线原点更近的子节点，提前剪枝。

### 6.3 碰撞对查询

物理引擎每帧需要：**所有相互重叠的物体对**。

方法：遍历所有叶子，对每个叶子查询树中与其重叠的其他叶子。使用一个 hashset 去重（每对只报告一次）。

---

## 七、从静态到动态：核心挑战

游戏中物体每帧都在动。一旦物体移动了，它的叶子 AABB 变了，会导致：

1. **父节点 AABB 可能不再包含子节点** → 违反了 BVH 的核心不变量
2. **树的质量退化** → 大量内部节点 AABB 膨胀，包围盒重叠度增大，查询剪枝效率下降

### 核心不变量

> **父节点的 AABB ⊇ 所有子孙节点的 AABB**

一旦违反，查询就会漏检——这是**致命错误**（碰撞检测漏掉 = 穿模）。

### 三种应对思路

| 策略 | 思路 | 代价 |
|------|------|------|
| 每帧重建 | 简单粗暴 | \(O(n \log n)\)，全量开销 |
| 自底向上回弹（Refit） | 只更新 AABB，不改树结构 | 便宜，但树质量只降不升 |
| 选择性重插入 | 脱出 Fat AABB 时才重插 | 均摊最优 |

---

## 八、动态 BVH 的四种更新策略

### 8.1 策略一：每帧全量重建

```
每帧:
    收集所有物体 AABB
    buildTopDown(所有物体)
```

- **优点**：树质量始终最优
- **缺点**：\(O(n \log n)\)，物体多时不可接受
- **适用**：物体少（<500）、或不怕开销的离线场景

### 8.2 策略二：自底向上回弹（Refit）

物体移动后，从叶子向上逐级重新计算父节点 AABB：

```
function refit(leafId):
    id = nodes[leafId].parent
    while id != -1:
        left  = nodes[id].left
        right = nodes[id].right
        nodes[id].aabb = merge(nodes[left].aabb, nodes[right].aabb)
        id = nodes[id].parent
```

- **复杂度**：\(O(h)\)，\(h\) 为树高度（平衡树 \(\approx \log n\)）
- **优点**：极便宜
- **缺点**：只膨胀不收缩——物体全往一个方向跑后，根节点 AABB 会越来越大，但永远不会缩回来。长期运行树质量持续退化

### 8.3 策略三：删除 + 重插入

物体移动后，从树中删除叶子，更新 AABB，再重新插入。

```
function moveObject(leafId, newAABB):
    removeLeaf(leafId)
    nodes[leafId].aabb = newAABB
    insertLeaf(leafId)
```

- **复杂度**：删除 \(O(\log n)\) + 插入 \(O(\log n)\)
- **优点**：树质量有机会恢复
- **缺点**：每个移动的物体都要做一次删+插，开销大于 refit

### 8.4 策略四：Fat AABB + 条件重插入（🏆 工业级方案）

**这是 Box2D、Bullet、Godot 等引擎实际采用的方案**。下一节详细展开。

---

## 九、工业级实现：Fat AABB（膨胀包围盒）

### 9.1 核心思想

给每个叶子的 AABB 加一圈"安全边距"（margin），物体小幅移动时仍在膨胀后的 AABB 内——不需要更新树。只有当物体移出 Fat AABB 时，才触发删除+重插入。

```
真实 AABB:   [===物体===]
Fat AABB:  [----===物体===----]
                              ↑ margin
```

### 9.2 数学定义

给定物体的真实包围盒 \(\text{AABB}_{\text{tight}}\)，膨胀后的 Fat AABB 为：

\[
\text{Fat}_{\min} = \text{AABB}_{\min} - \mathbf{m}, \quad \text{Fat}_{\max} = \text{AABB}_{\max} + \mathbf{m}
\]

其中 \(\mathbf{m} = (m, m, m)\) 是膨胀量。Box2D 的默认值：`m = 0.1`（即 `b2_aabbExtension`）。

### 9.3 速度预测膨胀

更高级的做法：根据物体的速度方向**非对称膨胀**，让 Fat AABB 朝运动方向更大，减少重插入频率：

\[
\text{Fat}_{\min,i} = \text{AABB}_{\min,i} - m + \min(0, k \cdot v_i \cdot \Delta t)
\]
\[
\text{Fat}_{\max,i} = \text{AABB}_{\max,i} + m + \max(0, k \cdot v_i \cdot \Delta t)
\]

- \(v_i\)：物体在轴 \(i\) 上的速度分量
- \(k\)：速度缩放因子（通常 2~4）
- \(\Delta t\)：时间步长

### 9.4 更新流程

```
function updateObject(leafId, newTightAABB, velocity):
    fatAABB = nodes[leafId].aabb   // 当前存储的 Fat AABB
    
    if fatAABB.contains(newTightAABB):
        return                      // 还在安全边距内，什么都不用做！
    
    // 移出了 Fat AABB → 需要重插入
    removeLeaf(leafId)
    
    // 重新计算 Fat AABB（加边距 + 速度预测）
    nodes[leafId].aabb = fatten(newTightAABB, velocity)
    
    insertLeaf(leafId)
```

### 9.5 效果分析

| 场景 | 每帧需重插入的比例 |
|------|------------------|
| 多数物体静止或缓慢移动 | < 5% |
| 所有物体匀速运动 | 10~20% |
| 爆炸/大量高速碰撞 | 可能 > 50%（但持续时间短） |

> 关键指标：**均摊后每个物体每帧的更新成本接近 \(O(1)\)**。这就是为什么 Box2D 能在手机上跑几千个刚体。

---

## 十、表面积启发式（SAH）

### 10.1 问题

插入新叶子时，应该插到树的哪个位置？选择不同位置会导致树的质量差异巨大。

### 10.2 核心思想

一个 AABB 的**表面积**（3D）或**周长**（2D）与"随机射线/查询命中该节点的概率"**成正比**。

直觉：表面积越大的盒子，被随机射线穿过的概率越大——查询时更可能进入这个分支——代价更高。

### 10.3 数学推导

假设父节点 AABB 面积为 \(S_P\)，如果在父节点内均匀随机采一条射线，它命中子节点（面积 \(S_C\)）的条件概率为：

\[
P(\text{命中子} \mid \text{命中父}) = \frac{S_C}{S_P}
\]

BVH 遍历的**期望代价**：

\[
C = C_{\text{trav}} \sum_{\text{内部节点 } i} \frac{S_i}{S_{\text{root}}} + C_{\text{isect}} \sum_{\text{叶子 } j} \frac{S_j}{S_{\text{root}}}
\]

- \(C_{\text{trav}}\)：遍历一个内部节点的代价（包围盒求交）
- \(C_{\text{isect}}\)：与叶子中物体做精确求交的代价
- \(S_i\)：节点 \(i\) 的表面积

### 10.4 插入时的 SAH 代价

当要将新叶子 \(L\) 插入时，对树中每个候选节点 \(N\)，计算"如果在 \(N\) 处新增一个中间节点，把 \(N\) 和 \(L\) 作为子节点"带来的代价增量：

\[
\Delta C = S(\text{merge}(N, L)) - S(N) + \text{向上传递的面积增量}
\]

遍历时贪心选择 \(\Delta C\) 最小的位置插入。

### 10.5 Box2D 的简化实现

Box2D 用**周长**替代表面积（2D 等价），并且不穷举所有位置，而是**沿树向下贪心**：

```
function chooseBestSibling(leafAABB):
    current = root
    while not current.isLeaf():
        combinedArea = perimeter(merge(current.aabb, leafAABB))
        
        // 如果在这里插入，代价是多少
        costHere = combinedArea
        inheritedCost = 0  // 向上传递的面积增量累加
        
        // 如果往左走或往右走，最低代价是多少
        costLeft  = costIfDescend(current.left,  leafAABB, inheritedCost)
        costRight = costIfDescend(current.right, leafAABB, inheritedCost)
        
        if costHere <= min(costLeft, costRight):
            break  // 在这里插入最划算
        
        current = (costLeft < costRight) ? current.left : current.right
    
    return current
```

> 复杂度 \(O(h)\)，实际中 \(h \approx \log n\)。

---

## 十一、完整伪代码

### 11.1 插入叶子

```
function insertLeaf(leafId):
    if tree is empty:
        root = leafId
        return
    
    // 1. 用 SAH 找到最佳兄弟节点
    sibling = chooseBestSibling(nodes[leafId].aabb)
    
    // 2. 创建新的内部节点
    oldParent = nodes[sibling].parent
    newParent = allocateNode()
    nodes[newParent].parent = oldParent
    nodes[newParent].left   = sibling
    nodes[newParent].right  = leafId
    nodes[newParent].aabb   = merge(nodes[sibling].aabb, nodes[leafId].aabb)
    nodes[newParent].height = max(nodes[sibling].height, nodes[leafId].height) + 1
    
    nodes[sibling].parent = newParent
    nodes[leafId].parent  = newParent
    
    // 3. 挂到原来的位置
    if oldParent == -1:
        root = newParent
    else if nodes[oldParent].left == sibling:
        nodes[oldParent].left = newParent
    else:
        nodes[oldParent].right = newParent
    
    // 4. 向上回弹：更新 AABB + 平衡旋转
    refitAndBalance(newParent)
```

### 11.2 删除叶子

```
function removeLeaf(leafId):
    if leafId == root:
        root = -1
        return
    
    parent  = nodes[leafId].parent
    grandpa = nodes[parent].parent
    sibling = (nodes[parent].left == leafId) 
              ? nodes[parent].right 
              : nodes[parent].left
    
    // 用兄弟替代父节点
    if grandpa == -1:
        root = sibling
        nodes[sibling].parent = -1
    else:
        if nodes[grandpa].left == parent:
            nodes[grandpa].left = sibling
        else:
            nodes[grandpa].right = sibling
        nodes[sibling].parent = grandpa
    
    freeNode(parent)
    
    // 向上回弹
    refitAndBalance(grandpa)
```

### 11.3 回弹与平衡旋转

```
function refitAndBalance(nodeId):
    while nodeId != -1:
        nodeId = balance(nodeId)   // AVL 风格旋转
        
        left  = nodes[nodeId].left
        right = nodes[nodeId].right
        
        nodes[nodeId].aabb   = merge(nodes[left].aabb, nodes[right].aabb)
        nodes[nodeId].height = max(nodes[left].height, nodes[right].height) + 1
        
        nodeId = nodes[nodeId].parent
```

### 11.4 AVL 旋转（保持平衡）

当左右子树高度差 > 1 时，执行旋转（与 AVL 树完全相同的逻辑）：

```
function balance(nodeId) -> int:
    A = nodeId
    if nodes[A].isLeaf() or nodes[A].height < 2:
        return A
    
    B = nodes[A].left
    C = nodes[A].right
    balanceFactor = nodes[C].height - nodes[B].height
    
    if balanceFactor > 1:       // 右倾：左旋
        return rotateLeft(A)
    if balanceFactor < -1:      // 左倾：右旋
        return rotateRight(A)
    
    return A
```

> 📌 平衡操作**不是必须的**——Box2D 做了，但 Bullet 的 `btDbvt` 没做。不做旋转只是树可能变高，不影响正确性。

---

## 十二、性能分析与调优

### 12.1 复杂度总结

| 操作 | 复杂度（平衡树） |
|------|----------------|
| 插入 | \(O(\log n)\) |
| 删除 | \(O(\log n)\) |
| 更新（Fat AABB 内） | \(O(1)\) |
| 更新（需重插入） | \(O(\log n)\)（均摊 \(O(1)\)） |
| AABB 查询 | \(O(\log n + k)\) |
| 射线查询 | \(O(\log n)\) |
| 全量碰撞对 | \(O(n \log n)\) |

### 12.2 内存布局优化

- **节点按层序排列**：BFS 顺序存储，连续节点大概率在同一 cache line
- **热/冷分离**：遍历只需 AABB + 子索引 + 是否叶子（24~32 字节），其余信息（objectId、height 等）放另一个数组
- **SIMD**：AABB 相交测试天然适合 SIMD（3 对 min/max → 一条 128-bit 指令）

### 12.3 关键调参

| 参数 | 作用 | 建议值 |
|------|------|--------|
| Fat AABB margin | 膨胀半径 | 物体平均尺寸的 5~10% |
| 速度预测因子 k | 运动方向膨胀倍数 | 2~4 |
| 是否做旋转平衡 | 树高 vs 代码复杂度 | 物体多（>1000）时推荐开启 |
| 节点池初始大小 | 减少扩容 | 预估叶子数 × 2（内部节点约等于叶子数） |

### 12.4 何时退化（需警惕）

| 场景 | 问题 | 对策 |
|------|------|------|
| 所有物体聚在一个点 | 包围盒严重重叠，剪枝失效 | 无解——换空间数据结构（如哈希网格） |
| 物体尺寸差异极大 | 小物体被大物体的 AABB "吞噬" | 对大物体单独处理或多级结构 |
| 高频全量删除+插入 | 树频繁震荡 | 攒一帧的变更批量处理 |

---

## 十三、实战：各引擎中的动态 BVH

| 引擎 | 实现类 | 包围体 | Fat AABB | AVL 平衡 | SAH | 特色 |
|------|-------|--------|----------|---------|-----|------|
| **Box2D** | `b2DynamicTree` | AABB（2D） | ✅ 0.1 单位 + 速度预测 | ✅ | ✅ 周长替代面积 | 教科书级实现，注释极好 |
| **Bullet** | `btDbvt` | AABB（3D） | ✅ | ❌ 不旋转 | ❌ 就近插入 | 两棵树：一棵静态、一棵动态 |
| **Godot** | `DynamicBVH` | AABB（3D） | ✅ | 部分 | ✅ | 基于 Bullet 改进 |
| **PhysX** | `PxBroadPhase` | AABB（3D） | 内部 | — | — | GPU 加速 BVH |
| **Unity** (DOTS) | Havok/自研 | AABB（3D） | ✅ | — | — | 面向 ECS 的批量更新 |

> 📌 **推荐阅读源码**：Box2D 的 `b2DynamicTree.cpp`（约 600 行 C），是最清晰的工业级动态 BVH 实现。

---

## 十四、常见问题与陷阱

### Q1：BVH vs 四叉树 / 八叉树 / 网格，怎么选？

| 结构 | 适合场景 | 不适合场景 |
|------|---------|----------|
| **动态 BVH** | 物体大小不一、分布不均匀 | 物体极度密集且大小均匀 |
| 均匀网格 | 物体大小相近、分布均匀 | 大小差异大（大物体占太多格子） |
| 四叉/八叉树 | 稀疏分布的静态场景 | 频繁移动的动态场景 |

### Q2：为什么用二叉树而不是四叉/八叉？

- 二叉树的合并/分裂操作最简单
- 查询时每层只需 2 次相交测试（四叉/八叉需 4/8 次）
- 二叉树可以通过 SAH 自适应分割，不绑定坐标轴

### Q3：Fat AABB 的 margin 怎么定？

经验公式：

\[
m = \alpha \cdot \bar{r} + \beta \cdot |\mathbf{v}| \cdot \Delta t
\]

- \(\bar{r}\)：场景中物体平均半径
- \(\alpha \approx 0.05 \sim 0.1\)
- \(\beta \approx 2 \sim 4\)

过小 → 频繁重插入；过大 → 包围盒松弛、查询效率下降。需要 profiling 调优。

### Q4：多线程怎么处理？

- **查询**：只读操作，天然线程安全
- **更新**：写操作，不安全。常见做法：
  - 收集所有需要更新的叶子 → 批量处理（单线程执行更新，多线程执行查询）
  - 或使用 lock-free 的延迟更新队列

### Q5：浮点精度问题

AABB 比较用 `<=` 而非 `<`——等号的处理决定了边界上的物体是否被检测到。保守做法：**Fat AABB 自带的 margin 自然覆盖了浮点误差**。

---

## 十五、前置数学知识清单

> 学习动态 BVH 需要以下数学知识。每项给出简述，按优先级从高到低排列。

### 核心（必须掌握）

| 知识 | 简述 | 在 BVH 中的应用 |
|------|------|-----------------|
| **向量运算** | 加减、点积、叉积、分量运算（min/max） | AABB 的合并、膨胀、中心点计算 |
| **区间运算** | 区间的交、并、包含关系 | AABB 本质是三对独立区间的组合；相交测试就是三轴区间的交集判断 |
| **分离轴定理（SAT）** | 两个凸体不相交 ⇔ 存在一条轴使两者的投影不重叠 | AABB 相交测试是 SAT 在轴对齐场景下的特例（只需检查 3 条轴） |
| **二叉树** | 节点、叶子、高度、遍历（前序/后序）、旋转 | BVH 就是一棵二叉树；插入/删除/平衡旋转与 AVL 树同源 |
| **递归与分治** | 问题拆分为子问题、递归求解、合并结果 | 构建（自顶向下）、查询（递归遍历）都是分治 |
| **集合论基础** | 交集、并集、包含、补集 | AABB 运算的数学语言；碰撞检测就是求"包围盒集合的交" |

### 进阶（显著提升理解深度）

| 知识 | 简述 | 在 BVH 中的应用 |
|------|------|-----------------|
| **概率与期望** | 随机事件概率、条件概率、期望值 | SAH 的数学基础：命中概率 ∝ 表面积，代价 = Σ(概率 × 单次代价) |
| **表面积与体积** | 长方体表面积公式、周长公式 | SAH 代价函数的核心度量；膨胀量计算 |
| **排序算法** | 快排、归并排序、\(O(n \log n)\) 复杂度 | 自顶向下构建时沿轴排序 |
| **均摊分析** | 一系列操作的平均代价可能远低于最坏代价 | Fat AABB 方案的核心论据：多数帧 \(O(1)\)，偶尔 \(O(\log n)\)，均摊接近 \(O(1)\) |
| **参数线性方程** | 射线 \(\mathbf{r}(t) = \mathbf{o} + t\mathbf{d}\)，解 \(t\) | 射线-AABB 相交（Slab Method）；光线追踪 BVH 遍历 |
| **矩阵变换** | 平移、旋转、缩放矩阵；仿射变换 | 物体变换后重算 AABB；OBB 与 AABB 的转换 |

### 可选（特定场景需要）

| 知识 | 简述 | 在 BVH 中的应用 |
|------|------|-----------------|
| **凸包与支撑函数** | 凸形体的极端点查询、GJK 算法 | BVH 剪枝后的窄阶段碰撞需要这些 |
| **图论（树的性质）** | 二叉树节点数 = 叶子数 × 2 - 1；深度与节点数的对数关系 | 预估节点池大小、分析复杂度 |
| **信息论 / 熵** | 信息增益、分割的"纯度" | 理解 SAH 为什么有效——它是信息增益的几何版本 |
| **蒙特卡洛方法** | 随机采样估计积分 | 理解 SAH 的概率模型："均匀随机射线"是蒙特卡洛假设 |
| **计算几何** | 凸多边形交、Minkowski 和/差 | 连续碰撞检测（CCD）中的 swept AABB 计算 |
| **数值分析** | 浮点误差、ULP、保守算术 | AABB 边界比较时的精度处理；避免漏检 |
| **并行算法** | 无锁数据结构、原子操作、任务并行 | GPU BVH 构建（Morton 码 + 基数排序）、多线程更新 |

### 优先级路线图

```
Level 1（先学这些，能看懂 Box2D 源码）
    向量运算 → 区间运算 → 二叉树 → 递归与分治

Level 2（能自己实现动态 BVH）
    SAT → 排序 → 集合论 → 均摊分析

Level 3（能优化、能读论文）
    概率/SAH → 参数方程 → 矩阵变换

Level 4（能做 GPU BVH / 写引擎）
    并行算法 → 数值分析 → 计算几何
```

---

## 参考资料

1. **Box2D 源码** `b2DynamicTree.cpp` —— 最清晰的工业级实现（约 600 行 C）
2. **Bullet Physics** `btDbvt` —— 3D 动态 BVH，无旋转平衡的另一种设计哲学
3. **Erin Catto (Box2D 作者) GDC 演讲** "Dynamic AABB Tree" —— 原理讲解
4. **Real-Time Rendering (4th ed.)** Chapter 22 —— BVH 在游戏渲染中的应用
5. **"On fast Construction of SAH-based Bounding Volume Hierarchies"** Ingo Wald, 2007 —— SAH 构建的经典论文
