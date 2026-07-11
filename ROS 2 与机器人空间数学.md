---
tags:
  - ros2
  - robotics
  - coordinate-transform
  - 6-dof
  - rotation-matrix
  - slam
aliases:
  - ROS 2 机器人开发
  - 坐标系旋转推导
  - 6自由度
created: 2026-06-20
---

# ROS 2 与机器人空间数学

---

## 一、ROS 2 是什么？

**一句话**：ROS 2 = 分布式通信中间件 + 机器人软件生态。

它不是"操作系统"，而是运行在 Linux / Windows / macOS 上的**机器人软件开发框架**，主要解决：

- 模块之间怎么通信（话题、服务、动作）
- 系统怎么启动和管理（Launch）
- 坐标关系怎么管理（TF）
- 已有算法和工具怎么复用（导航、感知、控制等）

### 1.1 ROS 1 vs ROS 2

| 对比维度 | ROS 1 | ROS 2 |
|:---------|:------|:------|
| 通信底层 | 自定义 TCPROS/UDPROS | DDS（实时、可配置 QoS） |
| 实时性 | 一般 | 支持实时系统（RT kernel） |
| 跨网络 | 需要 master，局域网为主 | 去中心化，更适合多机器人 |
| 生命周期管理 | 弱 | 内置 Managed Node |
| 官方支持 | 已停止长期维护 | 长期支持（Humble、Iron 等） |

---

## 二、ROS 2 核心概念

### 2.1 通信模型

| 通信方式 | 特点 | 典型场景 |
|:---------|:-----|:---------|
| **Topic**（话题） | 异步、一对多 | 传感器数据、里程计 |
| **Service**（服务） | 同步请求-响应 | 开关、参数设置 |
| **Action**（动作） | 目标 + 反馈 + 结果 | 导航、机械臂运动 |
| **Parameter**（参数） | 动态配置 | PID 参数、阈值 |

示例语义：

- `/scan` → Topic：激光雷达数据
- `/move_base` → Action：移动目标
- `/set_pose` → Service：设置初始位姿

### 2.2 NODE（节点）

- 每个 Node 是一个独立进程
- 负责一个功能（驱动、感知、规划、控制）
- 多个 Node 组成完整机器人系统

```
camera_node
lidar_node
localization_node
planning_node
control_node
```

### 2.3 DDS & QoS

ROS 2 基于 DDS，可配置：

- **可靠性**：可靠 / 尽力而为
- **历史深度**：保留多少条消息
- **延迟容忍**、**存活检测**等

这是 ROS 2 适合工业机器人的关键原因。

### 2.4 TF（坐标变换）

解决："激光在 base_link 坐标系下在哪？"

常见链：

```
map → odom → base_link → laser_link
```

### 2.5 Launch 系统

用 Python 编写启动文件：

- 启动多个 Node
- 传参
- 条件启动
- 组合复杂系统

---

## 三、典型机器人系统架构

```
[硬件]
 ├── 底盘
 ├── 激光 / 相机 / IMU
 └── 机械臂 / 执行器

[ROS 2 层]
 ├── 驱动层（hardware interface）
 ├── 感知层（SLAM、检测）
 ├── 规划层（路径、行为树）
 ├── 控制层（速度、关节控制）
 └── 应用层（UI、任务调度）
```

---

## 四、常用发行版与工具链

### 4.1 发行版

| 版本 | 状态 | 推荐度 |
|:-----|:-----|:------|
| **ROS 2 Humble**（LTS） | 支持到 2027 | ★★★★★ |
| Ubuntu 22.04 + Humble | 最稳组合 | 首选 |

> [!warning] 不建议新手用 Rolling（滚动发布）

### 4.2 工具链

| 项目 | 推荐 |
|:-----|:-----|
| 主语言 | C++ / Python |
| 构建系统 | colcon |
| 通信生成 | IDL（`.msg` / `.srv` / `.action`） |
| 仿真 | Gazebo / Ignition |
| 可视化 | RViz2 |
| 调试 | `ros2 topic` / `node` / `bag` |
| 控制框架 | ros2_control |

---

## 五、最小开发流程

```bash
# 1. 安装 ROS 2 + Gazebo

# 2. 创建工作空间
mkdir -p ~/ros2_ws/src

# 3. 创建功能包
ros2 pkg create my_robot --build-type ament_cmake

# 4. 写 Node（发布 /cmd_vel）
# 5. 用 Launch 启动
# 6. 在 RViz / Gazebo 中验证
```

---

## 六、常见机器人应用方向

| 方向 | ROS 2 组件 |
|:-----|:-----------|
| 移动机器人 | Nav2（导航栈） |
| SLAM | Cartographer / SLAM Toolbox |
| 机械臂 | MoveIt 2 |
| 多机协同 | DDS + 多机器人 launch |
| 自动驾驶 | Autoware（基于 ROS 2） |

---

## 七、学习路线

### 阶段 1：基础

- Linux + C++/Python
- ROS 2 通信机制
- Topic / Service / Action

### 阶段 2：仿真

- URDF/XACRO 建模
- Gazebo 仿真
- TF 与 RViz

### 阶段 3：系统

- Nav2 导航
- ros2_control
- Launch + 参数管理

### 阶段 4：实战

- 真实机器人（STM32 + ROS 2）
- 实时控制
- 行为树 / 状态机

---

## 八、空间中对象的 6 个自由度（6-DOF）

### 8.1 什么是自由度？

> 自由度 = 描述一个物体在空间中"完全位姿（位置和姿态）"所需的最少独立参数的个数。

在三维空间中：

- 物体可沿 X / Y / Z 三个轴**平移**
- 物体可绕 X / Y / Z 三个轴**旋转**

$$
\boxed{3\,\text{平移} + 3\,\text{旋转} = 6\,\text{自由度}}
$$

### 8.2 平移自由度（Position）—— 3 个

描述物体质心在空间中的位置：

| 轴 | 含义 |
|:---|:-----|
| X | 前后（前进/后退） |
| Y | 左右（左移/右移） |
| Z | 上下（上升/下降） |

### 8.3 旋转自由度（Orientation）—— 3 个

通常用 **Roll / Pitch / Yaw**（横滚/俯仰/偏航）表示：

| 名称 | 绕轴 | 日常比喻 |
|:-----|:-----|:---------|
| **Roll**（横滚） | 绕 X 轴 | 飞机侧翻/翻滚 |
| **Pitch**（俯仰） | 绕 Y 轴 | 机头抬头/低头 |
| **Yaw**（偏航） | 绕 Z 轴 | 机头左转/右转 |

### 8.4 数学表示（ROS 常用）

一个刚体在三维空间的位姿：

- **位置向量**：$\mathbf{p} = (x, y, z)$
- **姿态**：四元数 $\mathbf{q} = (q_x, q_y, q_z, q_w)$（ROS 2 推荐），或欧拉角 $(\text{roll}, \text{pitch}, \text{yaw})$

ROS 消息格式：

```yaml
geometry_msgs/Pose
 ├── position  : x y z
 └── orientation : quaternion
```

### 8.5 为什么不是更多？

- **刚体**（不变形）→ 内部点相对位置固定 → 只需 6 个参数
- 若物体可变形（软体、柔性结构）→ DOF 无限多
- 平面移动机器人（只在 XY 平面移动 + 绕 Z 旋转）→ **3-DOF** $(x, y, \text{yaw})$

### 8.6 与 ROS 2 / TF 的关系

在 TF 树中：

```
map → base_link
```

`base_link` 相对于 `map` 的变换就是 6-DOF 刚体变换（$SE(3)$）：平移 3DOF + 旋转 3DOF，ROS 用 `tf2` 发布这个变换。

---

## 九、坐标系旋转矩阵推导

> **核心问题**：空间一点 $P$ 固定不动，坐标系 $O$-$XYZ$ 绕 $X$ 轴旋转 $\theta$ 得到新系 $O$-$X'Y'Z'$。已知 $P$ 在新系中的坐标 $(x', y', z')$，求在旧系中的坐标 $(x, y, z)$。

### 9.1 前提约定

1. 点 $P$ 是固定不动的
2. 坐标系绕 $X$ 轴正方向旋转 $\theta$
3. 右手系 + 右手螺旋定则：右手握 $X$ 轴，拇指指向 $+X$，四指弯曲方向 = 正旋转方向

> [!important] 旋转矩阵 $R$ 把**新系坐标 → 老系坐标**
>
> $$
> \mathbf{p} = R \cdot \mathbf{p}'
> $$
>
> 等价地：$\mathbf{p}' = R^\mathsf{T} \cdot \mathbf{p}$（因为旋转矩阵正交，$R^{-1} = R^\mathsf{T}$）

### 9.2 为什么 $x = x'$ 不需要推导？

- 旋转绕 $X$ 轴进行
- $X$ 轴本身没有动
- 点在 $X$ 方向上的投影不变

$$
\boxed{x = x'}
$$

### 9.3 将问题降维到 $YZ$ 平面

绕 $X$ 轴旋转时：

- 只有 $Y$ 和 $Z$ 方向发生变化
- 问题等价于一个**二维平面旋转**

### 9.4 $YZ$ 平面的几何推导

**步骤 1**：在新坐标系中，点 $P$ 的坐标 $(y', z')$，其模长和极角：

$$
r = \sqrt{y'^2 + z'^2}, \qquad y' = r\cos\phi,\; z' = r\sin\phi
$$

> $\phi$ = 点 $P$ 相对于新坐标系 $Y'$ 轴的夹角

**步骤 2**：坐标系绕 $X$ 轴旋转 $\theta$ 后，$Y'$ 轴相对于旧系 $Y$ 轴逆时针转过了 $\theta$。

点 $P$ 在旧系中的极角变为：

$$
\phi_{\text{old}} = \phi + \theta
$$

> [!note] 为什么是 $\phi + \theta$？
> 新系的 $Y'$ 轴 = 旧系的 $Y$ 轴逆时针转 $\theta$；点 $P$ 在旧系中的角度 = 点相对于 $Y'$ 的角度 $+$ $Y'$ 轴相对 $Y$ 轴的角度 $= \phi + \theta$。
>
> **记忆规则**：坐标系往哪边转，点在旧系里的角度就往同方向加。

**步骤 3**：根据三角函数写出旧系坐标：

$$
\begin{aligned}
y &= r\cos(\phi + \theta) \\
z &= r\sin(\phi + \theta)
\end{aligned}
$$

**步骤 4**：使用和角公式展开：

$$
\begin{aligned}
\cos(\phi + \theta) &= \cos\phi\cos\theta - \sin\phi\sin\theta \\
\sin(\phi + \theta) &= \sin\phi\cos\theta + \cos\phi\sin\theta
\end{aligned}
$$

代入 $y' = r\cos\phi,\; z' = r\sin\phi$：

$$
\begin{aligned}
y &= r(\cos\phi\cos\theta - \sin\phi\sin\theta) \\
  &= (r\cos\phi)\cos\theta - (r\sin\phi)\sin\theta \\
  &= y'\cos\theta - z'\sin\theta \\[8pt]
z &= r(\sin\phi\cos\theta + \cos\phi\sin\theta) \\
  &= (r\sin\phi)\cos\theta + (r\cos\phi)\sin\theta \\
  &= z'\cos\theta + y'\sin\theta
\end{aligned}
$$

### 9.5 最终结果：绕 X 轴旋转矩阵

把以上写成矩阵形式：

$$
\begin{bmatrix} x \\ y \\ z \end{bmatrix} =
\begin{bmatrix}
1 & 0 & 0 \\
0 & \cos\theta & -\sin\theta \\
0 & \sin\theta & \cos\theta
\end{bmatrix}
\begin{bmatrix} x' \\ y' \\ z' \end{bmatrix}
$$

即：

$$
\boxed{R_x(\theta) =
\begin{bmatrix}
1 & 0 & 0 \\
0 & \cos\theta & -\sin\theta \\
0 & \sin\theta & \cos\theta
\end{bmatrix}}
$$

### 9.6 $R_x / R_y / R_z$ 完整对照

**绕 X 轴（Roll）**

$$
R_x(\theta) =
\begin{bmatrix}
1 & 0 & 0 \\
0 & \cos\theta & -\sin\theta \\
0 & \sin\theta & \cos\theta
\end{bmatrix}
$$

**绕 Y 轴（Pitch）**

$$
R_y(\theta) =
\begin{bmatrix}
\cos\theta & 0 & \sin\theta \\
0 & 1 & 0 \\
-\sin\theta & 0 & \cos\theta
\end{bmatrix}
$$

> [!warning] Y 轴注意符号！$-\sin\theta$ 在左下角，和 X/Z 不同。

**绕 Z 轴（Yaw）**

$$
R_z(\theta) =
\begin{bmatrix}
\cos\theta & -\sin\theta & 0 \\
\sin\theta & \cos\theta & 0 \\
0 & 0 & 1
\end{bmatrix}
$$

### 9.7 一句话记忆法

> 绕哪个轴旋转 → 该轴坐标不变；其余两轴按 2D 旋转矩阵填入；注意 Y 轴符号与另外两个相反。

---

## 十、ROS / 机器人中的注意要点

### 10.1 顺序很重要

欧拉角 $(\text{roll}, \text{pitch}, \text{yaw})$ 的组合（常见固定轴顺序）：

$$
R = R_z(\text{yaw}) \cdot R_y(\text{pitch}) \cdot R_x(\text{roll})
$$

先绕 X，再 Y，最后 Z（具体看项目约定）。

### 10.2 推荐使用四元数

ROS 2 中 `geometry_msgs/Pose.orientation` 存四元数，避免欧拉角万向锁问题。

### 10.3 tf2 用法本质

```cpp
// 发布 base_link 相对 map 的 6-DOF 变换
tf2::Transform tf(R_q, t_vec);
```

---

## 十一、Python 旋转动画演示

以下代码生成坐标系绕 X 轴旋转的动图：

```python
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def Rx(theta):
    """绕 X 轴旋转矩阵"""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([
        [1, 0,  0],
        [0, c, -s],
        [0, s,  c]
    ])

# 固定点 P（在新系中的坐标）
P_new = np.array([1, 1.5, 1])

# 动画
fig = plt.figure(figsize=(8, 6))
ax = fig.add_subplot(111, projection='3d')
ax.set_xlim([-2, 2])
ax.set_ylim([-2, 2])
ax.set_zlim([-2, 2])
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')

def update(frame):
    ax.cla()
    theta = frame * np.pi / 30
    R = Rx(theta)

    # 旧系（原始）坐标轴
    ax.quiver(0, 0, 0, 1.5, 0, 0, color='blue', alpha=0.5, label='Old X')
    ax.quiver(0, 0, 0, 0, 1.5, 0, color='blue', alpha=0.5, label='Old Y')
    ax.quiver(0, 0, 0, 0, 0, 1.5, color='blue', alpha=0.5, label='Old Z')

    # 新系（旋转后）坐标轴
    x_ax = R @ np.array([1.5, 0, 0])
    y_ax = R @ np.array([0, 1.5, 0])
    z_ax = R @ np.array([0, 0, 1.5])
    ax.quiver(0, 0, 0, *x_ax, color='red', label='New X\'')
    ax.quiver(0, 0, 0, *y_ax, color='red', label='New Y\'')
    ax.quiver(0, 0, 0, *z_ax, color='red', label='New Z\'')

    # 固定点 P 在旧系中的位置
    P_old = R @ P_new
    ax.scatter(*P_old, color='green', s=100, label='Point P')
    ax.text(*P_old, '  P', color='green')

    ax.set_xlim([-2, 2]); ax.set_ylim([-2, 2]); ax.set_zlim([-2, 2])
    ax.set_xlabel('X'); ax.set_ylabel('Y'); ax.set_zlabel('Z')
    ax.set_title(f'Rotation around X-axis: θ = {np.degrees(theta):.0f}°')
    ax.legend(loc='upper left')

ani = FuncAnimation(fig, update, frames=60, interval=50)
plt.show()
# ani.save('rotation_animation.gif')  # 取消注释以保存动图
```

---

## 十二、核心公式速查

| 公式 | 含义 |
|:-----|:-----|
| $R_x(\theta)$ | 绕 X 轴旋转 $\theta$，x 不变，Y-Z 平面 2D 旋转 |
| $R_y(\theta)$ | 绕 Y 轴旋转 $\theta$，y 不变，Z-X 平面 2D 旋转（符号翻转） |
| $R_z(\theta)$ | 绕 Z 轴旋转 $\theta$，z 不变，X-Y 平面 2D 旋转 |
| $R = R_z R_y R_x$ | 欧拉角组合顺序（看约定） |
| $\mathbf{p} = R \cdot \mathbf{p}'$ | 新系坐标 → 老系坐标 |
| $\mathbf{p}' = R^\mathsf{T} \cdot \mathbf{p}$ | 老系坐标 → 新系坐标 |
| 6-DOF = 3平移 + 3旋转 | 刚体在三维空间的完整描述 |
