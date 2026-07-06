# AI 时代图形学开发知识体系

**作者**：汪亮（bertonwang）  
**邮箱**：<47608843@qq.com>  
**版本**：v1.0 ｜ **最后更新**：2026-07-06

> 转载或引用请保留作者署名与本文链接，欢迎来信交流与勘误。
> 
> **文档说明**：本文档面向希望在 AI 时代进入计算机图形学领域的学习者，涵盖数学基础、渲染管线、光照模型、仿真引擎、AI 辅助图形学等核心知识点。适合小白入门，也适合有经验的工程师了解 AI 带来的新变化。

---

## 目录

- [[#一、AI 时代图形学全景图]]
- [[#二、必备数学基础]]
  - [[#2.1 线性代数（图形学的语言）]]
  - [[#2.2 微积分与微分几何]]
  - [[#2.3 概率论与统计（渲染核心）]]
  - [[#2.4 数值方法]]
  - [[#2.5 信号处理与频域分析]]
- [[#三、渲染管线与光栅化]]
  - [[#3.1 图形渲染管线总览]]
  - [[#3.2 坐标变换系统]]
  - [[#3.3 光栅化算法]]
  - [[#3.4 深度测试与模板测试]]
- [[#四、光照与着色模型]]
  - [[#4.1 光照物理基础]]
  - [[#4.2 经典光照模型]]
  - [[#4.3 基于物理的渲染（PBR）]]
  - [[#4.4 全局光照算法]]
- [[#五、着色器编程]]
  - [[#5.1 GLSL / HLSL 核心语法]]
  - [[#5.2 顶点着色器]]
  - [[#5.3 片元着色器]]
  - [[#5.4 计算着色器（Compute Shader）]]
- [[#六、几何处理]]
  - [[#6.1 网格表示与数据结构]]
    - [[#6.1.1 GPU 渲染与三角形：从网格到屏幕像素]]
    - [[#6.1.2 纹理贴图：把一张 2D 图像贴到三角网格立体上]]
  - [[#6.2 曲线与曲面]]
  - [[#6.3 细分曲面]]
  - [[#6.4 程序化几何生成]]
- [[#七、仿真引擎与渲染框架]]
  - [[#7.1 主流图形 API 对比]]
  - [[#7.2 游戏引擎渲染管线]]
  - [[#7.3 离线渲染引擎]]
  - [[#7.4 实时光线追踪]]
  - [[#7.5 物理仿真引擎]]
- [[#八、AI 在图形学中的应用]]
  - [[#8.1 神经渲染（Neural Rendering）]]
  - [[#8.2 NeRF 与 3D Gaussian Splatting]]
  - [[#8.3 AI 超分辨率（DLSS / FSR）]]
  - [[#8.4 AI 辅助内容生成]]
  - [[#8.5 Shader 自动生成]]
- [[#九、专项方向]]
- [[#十、学习路径建议]]
- [[#十一、参考资源]]

---

## 一、AI 时代图形学全景图

```
计算机图形学知识全景（AI 时代）

  ┌─────────────────────────────────────────────────────────┐
  │                      应用层                              │
  │  游戏渲染 │ 影视特效（VFX）│ 科学可视化 │ AR/VR/XR      │
  │  建筑可视化 │ 数字孪生 │ 自动驾驶感知 │ 医学影像        │
  └─────────────────────────────────────────────────────────┘
                            ↕
  ┌─────────────────────────────────────────────────────────┐
  │                    渲染算法层                             │
  │  光栅化渲染 │ 光线追踪（Ray Tracing）                    │
  │  路径追踪（Path Tracing）│ 辐射度算法                    │
  │  体积渲染 │ 粒子系统 │ 程序化生成                        │
  └─────────────────────────────────────────────────────────┘
                            ↕
  ┌─────────────────────────────────────────────────────────┐
  │                    AI 辅助层（新增）                      │
  │  NeRF / 3DGS │ 神经渲染 │ DLSS/FSR 超分辨率             │
  │  AI 纹理生成 │ AI 动画 │ Shader 自动生成                 │
  │  扩散模型 3D 生成 │ LLM 辅助 Shader 编写                 │
  └─────────────────────────────────────────────────────────┘
                            ↕
  ┌─────────────────────────────────────────────────────────┐
  │                    图形 API 层                            │
  │  OpenGL │ Vulkan │ DirectX 12 │ Metal │ WebGPU           │
  │  CUDA（通用 GPU 计算）│ OptiX（光线追踪）                 │
  └─────────────────────────────────────────────────────────┘
                            ↕
  ┌─────────────────────────────────────────────────────────┐
  │                    数学基础层                             │
  │  线性代数 │ 微积分 │ 微分几何 │ 概率论                   │
  │  数值方法 │ 信号处理 │ 拓扑学                            │
  └─────────────────────────────────────────────────────────┘
```

### 1.1 AI 时代带来的核心变化

| 传统图形学 | AI 时代图形学 |
|-----------|-------------|
| 手写 Shader，经验调参 | AI 辅助生成 Shader，自动优化 |
| 光线追踪需要数小时渲染 | NeRF/3DGS 实时神经渲染 |
| 手工建模（Maya/Blender） | AI 生成 3D 模型（Point-E/Shap-E） |
| 低分辨率实时渲染 | DLSS/FSR AI 超分，4K 实时 |
| 手工制作动画 | AI 驱动角色动画（Motion Diffusion） |
| 传统纹理贴图 | AI 生成无缝纹理（Stable Diffusion） |
| 离线路径追踪 | 实时光线追踪 + AI 降噪（OIDN） |

---

## 二、必备数学基础

> 图形学是应用数学的艺术。以下数学知识是图形学工程师的核心武器。

### 2.1 线性代数（图形学的语言）

线性代数是图形学中使用频率最高的数学工具，几乎所有变换、光照计算都依赖它。

#### 2.1.1 向量运算

```
向量（Vector）：表示方向和大小

  3D 向量：v = (x, y, z)

  点积（Dot Product）：
  a · b = |a||b|cos(θ) = ax·bx + ay·by + az·bz
  
  应用：
  ├── 计算两向量夹角：θ = arccos(a·b / (|a||b|))
  ├── 判断方向关系：a·b > 0（同向）/ < 0（反向）/ = 0（垂直）
  ├── 光照计算：漫反射强度 = max(0, N·L)（N=法线，L=光方向）
  └── 投影：a 在 b 上的投影长度 = a·b̂（b̂ 为单位向量）

  叉积（Cross Product）：
  a × b = (ay·bz - az·by, az·bx - ax·bz, ax·by - ay·bx)
  
  性质：
  ├── 结果垂直于 a 和 b 所在平面
  ├── |a × b| = |a||b|sin(θ)（等于平行四边形面积）
  └── 方向：右手定则
  
  应用：
  ├── 计算面法线：N = (v1-v0) × (v2-v0)
  ├── 判断三角形正反面（背面剔除）
  └── 构建正交坐标系（TBN 矩阵）
```

#### 2.1.2 矩阵变换

```
变换矩阵（4×4 齐次坐标）：

  平移矩阵 T(tx, ty, tz)：
  ┌ 1  0  0  tx ┐
  │ 0  1  0  ty │
  │ 0  0  1  tz │
  └ 0  0  0   1 ┘

  缩放矩阵 S(sx, sy, sz)：
  ┌ sx  0   0  0 ┐
  │  0  sy  0  0 │
  │  0   0  sz 0 │
  └  0   0   0 1 ┘

  绕 Z 轴旋转矩阵 Rz(θ)：
  ┌ cos(θ)  -sin(θ)  0  0 ┐
  │ sin(θ)   cos(θ)  0  0 │
  │    0        0    1  0 │
  └    0        0    0  1 ┘

  变换组合（注意顺序！）：
  M = T × R × S  （先缩放，再旋转，再平移）
  
  顶点变换：v' = M × v
  
  ⚠️ 矩阵乘法不满足交换律：T×R ≠ R×T
```

#### 2.1.3 四元数（Quaternion）

```
四元数：q = w + xi + yj + zk = (w, x, y, z)

  为什么用四元数而不用欧拉角？
  
  欧拉角的问题：
  ├── 万向节死锁（Gimbal Lock）：当某个轴旋转 90° 后，
  │   另外两个轴重合，丢失一个自由度
  └── 插值不平滑（Lerp 插值路径不是最短弧）

  四元数的优势：
  ├── 无万向节死锁
  ├── 球面线性插值（Slerp）：平滑的旋转动画
  └── 计算效率高（比矩阵乘法少）

  单位四元数表示旋转：
  q = cos(θ/2) + sin(θ/2)·(ax·i + ay·j + az·k)
  其中 (ax, ay, az) 是旋转轴（单位向量），θ 是旋转角度

  Slerp 插值（动画关键帧插值）：
  Slerp(q1, q2, t) = q1 · (q1⁻¹ · q2)^t
  t ∈ [0,1]，沿球面最短弧插值
```

#### 2.1.4 特征值与特征向量

```
应用场景：
  ├── PCA（主成分分析）：点云降维、法线估计
  ├── 网格简化：分析曲率主方向
  ├── 物理仿真：惯性张量的主轴
  └── 图像处理：图像压缩（SVD）

SVD（奇异值分解）：
  A = U·Σ·V^T
  
  图形学应用：
  ├── 极分解：将变形梯度分解为旋转 + 拉伸（弹性体仿真）
  ├── 最优旋转估计（ICP 点云配准）
  └── 纹理压缩（BC 格式）
```

### 2.2 微积分与微分几何

#### 2.2.1 微积分在图形学中的应用

```
梯度（Gradient）：
  ∇f = (∂f/∂x, ∂f/∂y, ∂f/∂z)
  
  应用：
  ├── 隐式曲面法线：N = ∇F(x,y,z)（F=0 定义曲面）
  ├── 神经网络训练：反向传播（梯度下降）
  └── 程序化地形：噪声函数的梯度 → 法线贴图

散度（Divergence）与旋度（Curl）：
  ∇·F（散度）：流体仿真中的不可压缩条件（∇·v = 0）
  ∇×F（旋度）：涡旋流场分析

积分：
  渲染方程（The Rendering Equation，Kajiya 1986）：
  
  Lo(x, ωo) = Le(x, ωo) + ∫Ω fr(x, ωi, ωo) Li(x, ωi) (ωi·n) dωi
  
  其中：
  ├── Lo：出射辐射度（我们要求的颜色）
  ├── Le：自发光
  ├── fr：BRDF（双向反射分布函数）
  ├── Li：入射辐射度
  └── (ωi·n)：Lambert 余弦项
  
  这个积分无法解析求解 → 蒙特卡洛数值积分
```

#### 2.2.2 微分几何

```
曲面的微分几何量：

  第一基本形式（度量张量）：
  ds² = E·du² + 2F·du·dv + G·dv²
  用途：计算曲面上的距离、面积、角度

  第二基本形式：
  描述曲面的弯曲程度

  主曲率（κ1, κ2）：
  ├── 曲面在两个主方向上的弯曲率
  └── 用于网格简化（保留高曲率区域）

  高斯曲率：K = κ1 × κ2
  ├── K > 0：椭圆点（球面）
  ├── K = 0：抛物点（柱面）
  └── K < 0：双曲点（马鞍面）

  平均曲率：H = (κ1 + κ2) / 2
  └── 极小曲面（H=0）：肥皂膜形状，用于布料仿真

  法曲率：
  └── 用于各向异性高光（头发、拉丝金属）
```

### 2.3 概率论与统计（渲染核心）

#### 2.3.1 蒙特卡洛积分

```
蒙特卡洛积分（Monte Carlo Integration）：

  核心思想：用随机采样估计积分
  
  ∫f(x)dx ≈ (1/N) Σ f(xi) / p(xi)
  
  其中 xi 按概率密度函数 p(x) 采样

  为什么图形学需要蒙特卡洛？
  └── 渲染方程是高维积分（光线方向 × 光源 × 多次弹射）
      无法解析求解，只能数值估计

  方差（Variance）：
  Var = E[(f(x)/p(x) - I)²]
  方差越大 → 图像噪点越多 → 需要更多采样

  重要性采样（Importance Sampling）：
  └── 让 p(x) ∝ f(x)，使采样集中在贡献大的区域
      可大幅降低方差（减少噪点）
  
  示例：
  ├── 余弦加权半球采样（漫反射）
  ├── GGX 重要性采样（镜面反射）
  └── 多重重要性采样（MIS）：结合多种采样策略

  低差异序列（Low-Discrepancy Sequences）：
  ├── Halton 序列、Sobol 序列
  └── 比纯随机采样收敛更快（准蒙特卡洛）
```

#### 2.3.2 概率分布

```
图形学常用概率分布：

  均匀分布：随机光线方向（半球均匀采样）
  
  余弦分布：漫反射采样
  p(θ) = cos(θ)/π
  
  GGX/Trowbridge-Reitz 分布（镜面高光）：
  D(h) = α² / (π · ((n·h)²(α²-1)+1)²)
  其中 α 是粗糙度，h 是半程向量
  
  高斯分布：
  ├── 图像模糊（高斯滤波）
  ├── 景深（Depth of Field）模糊
  └── 软阴影（PCF 核）

  泊松盘采样（Poisson Disk Sampling）：
  └── 保证采样点之间最小距离
      用于：纹理采样、阴影贴图 PCF、粒子分布
```

### 2.4 数值方法

```
数值积分：
  黎曼和、梯形法则、辛普森法则
  用于：预计算辐照度（IBL 预积分）

数值微分：
  有限差分法：∂f/∂x ≈ (f(x+h) - f(x-h)) / (2h)
  用于：数值法线计算、隐式曲面梯度

线性方程组求解：
  高斯消元、LU 分解、共轭梯度法（CG）
  用于：有限元仿真、光照预计算

常微分方程（ODE）求解：
  欧拉法（Euler Method）：简单但不稳定
  Runge-Kutta 4（RK4）：精度高，物理仿真常用
  Verlet 积分：能量守恒好，布料/粒子仿真常用
  
  示例（粒子运动）：
  // 显式欧拉（简单但可能爆炸）
  v(t+dt) = v(t) + a(t) · dt
  x(t+dt) = x(t) + v(t) · dt
  
  // Verlet 积分（更稳定）
  x(t+dt) = 2·x(t) - x(t-dt) + a(t)·dt²

偏微分方程（PDE）：
  热方程（扩散）：∂u/∂t = α·∇²u
  └── 用于：热传导仿真、图像扩散滤波
  
  波动方程：∂²u/∂t² = c²·∇²u
  └── 用于：水面波纹、声音传播仿真
  
  Navier-Stokes 方程（流体）：
  ρ(∂v/∂t + v·∇v) = -∇p + μ∇²v + f
  └── 用于：烟雾、火焰、水流仿真
```

### 2.5 信号处理与频域分析

```
傅里叶变换（Fourier Transform）：
  F(ω) = ∫f(t)·e^(-iωt)dt
  
  图形学应用：
  ├── 纹理抗锯齿（Mipmap 理论基础）
  ├── 球谐函数（Spherical Harmonics）：低频光照压缩
  ├── 频域滤波（图像锐化/模糊）
  └── 分析渲染算法的收敛性

奈奎斯特采样定理：
  采样频率 ≥ 2 × 信号最高频率
  
  图形学应用：
  ├── 纹理采样：Mipmap 避免摩尔纹（混叠）
  ├── 阴影贴图分辨率选择
  └── 抗锯齿（MSAA/TAA/DLAA）

球谐函数（Spherical Harmonics, SH）：
  定义在球面上的正交基函数
  
  应用：
  ├── 低频环境光照压缩（9 个 SH 系数 ≈ 漫反射环境光）
  ├── 实时全局光照（Precomputed Radiance Transfer, PRT）
  └── NeRF 中的视角相关颜色表示

小波变换（Wavelet）：
  └── 多分辨率分析，用于全局光照预计算（Wavelet Radiance）
```

---

## 三、渲染管线与光栅化

### 3.1 图形渲染管线总览

```
现代 GPU 渲染管线（可编程阶段用 * 标注）：

  CPU 端                    GPU 端
  ─────────────────────────────────────────────────────
  应用阶段                  几何阶段
  ├── 场景管理              ├── 顶点着色器 *（Vertex Shader）
  ├── 视锥剔除              ├── 曲面细分 *（Tessellation）
  ├── 遮挡剔除              ├── 几何着色器 *（Geometry Shader）
  └── Draw Call 提交        └── 图元装配 + 裁剪
                            
                            光栅化阶段
                            ├── 光栅化（三角形 → 像素）
                            ├── 片元着色器 *（Fragment Shader）
                            ├── 深度测试（Z-Test）
                            ├── 模板测试（Stencil Test）
                            └── 混合（Alpha Blending）
                            
                            输出
                            └── 帧缓冲（Framebuffer）→ 显示
```

### 3.2 坐标变换系统

```
坐标空间变换链：

  模型空间（Object Space）
       ↓ 模型矩阵 M（平移/旋转/缩放）
  世界空间（World Space）
       ↓ 视图矩阵 V（相机变换）
  相机空间（View/Eye Space）
       ↓ 投影矩阵 P（透视/正交投影）
  裁剪空间（Clip Space）
       ↓ 透视除法（÷ w）
  NDC 空间（Normalized Device Coordinates，[-1,1]³）
       ↓ 视口变换
  屏幕空间（Screen Space）

透视投影矩阵（OpenGL 约定）：
  ┌ 2n/(r-l)     0      (r+l)/(r-l)    0    ┐
  │    0      2n/(t-b)  (t+b)/(t-b)    0    │
  │    0          0    -(f+n)/(f-n)  -2fn/(f-n) │
  └    0          0         -1          0    ┘

  n=近裁剪面，f=远裁剪面，l/r/t/b=视锥边界

法线变换（重要！）：
  法线不能直接用模型矩阵变换！
  正确做法：法线矩阵 = (M⁻¹)^T（模型矩阵逆的转置）
  原因：非均匀缩放会破坏法线的垂直性
```

### 3.3 光栅化算法

```
三角形光栅化：

  1. 边函数（Edge Function）判断像素是否在三角形内：
     E(P) = (P - V0) × (V1 - V0)
     三个边函数均 ≥ 0 → 像素在三角形内

  2. 重心坐标插值（Barycentric Interpolation）：
     P = α·V0 + β·V1 + γ·V2，其中 α+β+γ=1
     
     用于插值：
     ├── 顶点颜色
     ├── 纹理坐标（UV）
     ├── 法线（Phong 着色）
     └── 深度值（Z 插值）
     
     ⚠️ 透视校正插值：
     屏幕空间插值需要除以 w 进行透视校正，
     否则纹理在透视变换后会出现扭曲

  3. 抗锯齿（Anti-Aliasing）：
     MSAA（多重采样）：每像素多个采样点，硬件支持
     TAA（时间抗锯齿）：利用历史帧信息，现代游戏主流
     DLAA（深度学习抗锯齿）：AI 驱动，质量最高
     FXAA：后处理，快速但质量一般
```

### 3.4 深度测试与模板测试

```
深度缓冲（Z-Buffer）：
  每个像素存储最近的深度值
  新片元深度 < 缓冲区深度 → 通过测试，更新颜色和深度
  
  深度精度问题（Z-Fighting）：
  ├── 原因：透视投影后深度值非线性分布，远处精度低
  ├── 解决：反转深度（Reversed-Z），将 [0,1] 映射为 [1,0]
  └── 效果：远处精度大幅提升

Early-Z（提前深度测试）：
  在片元着色器之前进行深度测试
  剔除被遮挡的片元，节省着色器计算

模板测试（Stencil Test）：
  应用：
  ├── 镜面反射（只在镜面区域渲染反射）
  ├── 阴影体（Shadow Volume）
  └── 轮廓描边（Outline Effect）
```

---

## 四、光照与着色模型

### 4.1 光照物理基础

```
辐射度量学（Radiometry）基本量：

  辐射通量（Radiant Flux）Φ：单位时间的能量，单位 W（瓦特）
  
  辐照度（Irradiance）E：单位面积接收的辐射通量
  E = dΦ/dA，单位 W/m²
  
  辐射强度（Radiant Intensity）I：单位立体角的辐射通量
  I = dΦ/dω，单位 W/sr
  
  辐射率（Radiance）L：单位面积、单位立体角的辐射通量
  L = d²Φ/(dA·cosθ·dω)，单位 W/(m²·sr)
  └── 这是渲染方程中最核心的量，也是相机感知到的量

BRDF（双向反射分布函数）：
  fr(ωi, ωo) = dLo(ωo) / (Li(ωi)·cosθi·dωi)
  
  物理约束：
  ├── 非负性：fr ≥ 0
  ├── 亥姆霍兹互易性：fr(ωi, ωo) = fr(ωo, ωi)
  └── 能量守恒：∫fr·cosθ·dω ≤ 1
```

### 4.2 经典光照模型

```
Lambert 漫反射：
  Ldiffuse = kd · (N · L)
  ├── kd：漫反射系数（材质颜色）
  ├── N：表面法线（单位向量）
  └── L：光源方向（单位向量）

Phong 高光模型：
  Lspecular = ks · (R · V)^n
  ├── R = 2(N·L)N - L（反射方向）
  ├── V：视线方向
  └── n：高光指数（越大越锐利）

Blinn-Phong（改进版，更高效）：
  Lspecular = ks · (N · H)^n
  H = normalize(L + V)（半程向量）
  优势：H 比 R 计算简单，且视觉效果更好

完整 Phong 光照：
  L = La·ka + Ld·kd·max(0, N·L) + Ls·ks·max(0, N·H)^n
  
  其中 La/Ld/Ls 是环境光/漫反射光/镜面光颜色
```

### 4.3 基于物理的渲染（PBR）

```
PBR 核心思想：
  用物理正确的方式描述光与材质的交互
  
  Cook-Torrance BRDF（镜面反射部分）：
  fr_specular = D(h) · F(v,h) · G(l,v,h) / (4·(n·l)·(n·v))
  
  三个核心函数：
  
  D（法线分布函数，NDF）：
  └── 描述微表面法线的统计分布
      GGX/Trowbridge-Reitz：D(h) = α²/(π·((n·h)²(α²-1)+1)²)
      α = roughness²（粗糙度）
  
  F（菲涅尔方程，Fresnel）：
  └── 描述反射率随视角变化
      Schlick 近似：F = F0 + (1-F0)·(1-(v·h))^5
      F0：垂直入射时的反射率（金属：彩色，非金属：0.04）
  
  G（几何遮蔽函数）：
  └── 描述微表面的自遮挡和自阴影
      Smith GGX：G = G1(l)·G1(v)

PBR 材质参数（金属-粗糙度工作流）：
  ├── Albedo（基础色）：漫反射颜色
  ├── Metallic（金属度）：0=非金属，1=金属
  ├── Roughness（粗糙度）：0=镜面，1=完全漫反射
  ├── Normal Map（法线贴图）：增加表面细节
  └── AO（环境光遮蔽）：接触阴影
```

### 4.4 全局光照算法

```
全局光照（Global Illumination, GI）：
  考虑光线在场景中多次弹射的效果

光线追踪（Ray Tracing）：
  从相机发射光线 → 与场景求交 → 递归追踪反射/折射
  
  BVH（层次包围盒）加速结构：
  └── 将场景组织为树形结构，O(log N) 求交
      是实时光线追踪的关键数据结构

路径追踪（Path Tracing）：
  蒙特卡洛估计渲染方程
  每像素发射多条随机光线，统计平均值
  
  优点：物理正确，能处理所有光照效果
  缺点：收敛慢（需要大量采样），有噪点

光子映射（Photon Mapping）：
  双向算法：从光源发射光子 + 从相机追踪
  适合焦散（Caustics）效果

辐射度算法（Radiosity）：
  适合漫反射场景的全局光照
  将场景分为面片，求解能量传递方程

实时 GI 方案：
  ├── SSAO（屏幕空间环境光遮蔽）：近似 AO
  ├── SSGI（屏幕空间全局光照）：近似一次弹射
  ├── DDGI（动态漫反射 GI）：探针网格，UE5 Lumen
  ├── RTXGI（NVIDIA 实时 GI）：硬件光线追踪
  └── Lumen（UE5）：软件光线追踪 + 硬件加速
```

---

## 五、着色器编程

### 5.1 GLSL / HLSL 核心语法

```glsl
// GLSL 片元着色器示例：PBR 材质
#version 450

// 输入
in vec3 fragPos;      // 世界空间位置
in vec3 fragNormal;   // 世界空间法线
in vec2 fragUV;       // 纹理坐标

// Uniform（CPU 传入的参数）
uniform sampler2D albedoMap;
uniform sampler2D normalMap;
uniform sampler2D metallicRoughnessMap;
uniform vec3 camPos;
uniform vec3 lightPos;
uniform vec3 lightColor;

// 输出
out vec4 fragColor;

const float PI = 3.14159265359;

// GGX 法线分布函数
float DistributionGGX(vec3 N, vec3 H, float roughness) {
    float a  = roughness * roughness;
    float a2 = a * a;
    float NdotH  = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;
    float denom = (NdotH2 * (a2 - 1.0) + 1.0);
    return a2 / (PI * denom * denom);
}

// Schlick 菲涅尔近似
vec3 FresnelSchlick(float cosTheta, vec3 F0) {
    return F0 + (1.0 - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

void main() {
    // 采样材质贴图
    vec3  albedo    = pow(texture(albedoMap, fragUV).rgb, vec3(2.2)); // sRGB → Linear
    float metallic  = texture(metallicRoughnessMap, fragUV).b;
    float roughness = texture(metallicRoughnessMap, fragUV).g;
    
    vec3 N = normalize(fragNormal);
    vec3 V = normalize(camPos - fragPos);
    vec3 L = normalize(lightPos - fragPos);
    vec3 H = normalize(V + L);
    
    // F0：垂直入射反射率
    vec3 F0 = mix(vec3(0.04), albedo, metallic);
    
    // Cook-Torrance BRDF
    float NDF = DistributionGGX(N, H, roughness);
    vec3  F   = FresnelSchlick(max(dot(H, V), 0.0), F0);
    
    vec3  kS = F;
    vec3  kD = (1.0 - kS) * (1.0 - metallic);
    
    vec3 numerator   = NDF * F;
    float denominator = 4.0 * max(dot(N,V),0.0) * max(dot(N,L),0.0) + 0.0001;
    vec3 specular = numerator / denominator;
    
    float NdotL = max(dot(N, L), 0.0);
    vec3 Lo = (kD * albedo / PI + specular) * lightColor * NdotL;
    
    // Gamma 校正
    vec3 color = Lo / (Lo + vec3(1.0));  // Tone mapping
    color = pow(color, vec3(1.0/2.2));   // Linear → sRGB
    
    fragColor = vec4(color, 1.0);
}
```

### 5.2 顶点着色器

```glsl
// 顶点着色器：支持法线贴图的 TBN 矩阵计算
#version 450

layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aUV;
layout(location = 3) in vec3 aTangent;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

out vec3 fragPos;
out vec2 fragUV;
out mat3 TBN;  // 切线空间 → 世界空间变换矩阵

void main() {
    fragPos = vec3(model * vec4(aPos, 1.0));
    fragUV  = aUV;
    
    // 构建 TBN 矩阵（用于法线贴图）
    mat3 normalMatrix = transpose(inverse(mat3(model)));
    vec3 T = normalize(normalMatrix * aTangent);
    vec3 N = normalize(normalMatrix * aNormal);
    T = normalize(T - dot(T, N) * N);  // Gram-Schmidt 正交化
    vec3 B = cross(N, T);
    TBN = mat3(T, B, N);
    
    gl_Position = projection * view * vec4(fragPos, 1.0);
}
```

### 5.3 片元着色器

```glsl
// 计算着色器示例：GPU 粒子系统
#version 450
layout(local_size_x = 256) in;

struct Particle {
    vec4 position;   // xyz=位置, w=生命值
    vec4 velocity;   // xyz=速度, w=质量
};

layout(std430, binding = 0) buffer ParticleBuffer {
    Particle particles[];
};

uniform float deltaTime;
uniform vec3  gravity;
uniform float damping;

void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= particles.length()) return;
    
    Particle p = particles[id];
    
    // 物理更新（Verlet 积分）
    vec3 acceleration = gravity / p.velocity.w;
    p.velocity.xyz += acceleration * deltaTime;
    p.velocity.xyz *= (1.0 - damping * deltaTime);  // 阻尼
    p.position.xyz += p.velocity.xyz * deltaTime;
    
    // 生命值递减
    p.position.w -= deltaTime;
    
    // 地面碰撞
    if (p.position.y < 0.0) {
        p.position.y  = 0.0;
        p.velocity.y  = -p.velocity.y * 0.6;  // 弹性系数
    }
    
    particles[id] = p;
}
```

### 5.4 计算着色器（Compute Shader）

计算着色器突破了传统渲染管线的限制，可以做任意 GPU 并行计算：

| 应用场景 | 说明 |
|---------|------|
| 粒子系统 | GPU 上并行更新百万粒子 |
| 布料仿真 | 并行计算约束力 |
| 后处理效果 | 景深、运动模糊、SSAO |
| 光线追踪 | 自定义光线求交 |
| AI 推理 | 在 GPU 上运行神经网络 |
| 预计算 | 辐照度贴图、BRDF LUT |

---

## 六、几何处理

### 6.1 网格表示与数据结构

```
三角网格表示：

  索引网格（Indexed Mesh）：
  ├── 顶点数组：[(x0,y0,z0), (x1,y1,z1), ...]
  └── 索引数组：[0,1,2, 0,2,3, ...]（每3个索引一个三角形）
  
  优点：共享顶点，节省内存；GPU 友好

半边数据结构（Half-Edge）：
  每条边分为两个方向相反的半边
  支持高效的：
  ├── 顶点邻域遍历
  ├── 面邻域遍历
  └── 网格编辑操作（边折叠、边翻转）
  
  用于：网格简化、参数化、细分

点云（Point Cloud）：
  无连接关系的点集合
  用于：3D 扫描数据、NeRF 输出、LiDAR 数据
  
  处理工具：Open3D、PCL（Point Cloud Library）

隐式曲面（Implicit Surface）：
  F(x,y,z) = 0 定义曲面
  
  SDF（有符号距离场）：
  ├── F(p) = 到曲面的有符号距离
  ├── F < 0：内部；F > 0：外部；F = 0：曲面
  └── 应用：碰撞检测、布尔运算、Marching Cubes 提取网格
```

#### 6.1.1 GPU 渲染与三角形：从网格到屏幕像素

> 这一小节回答两个非常常见的疑问：
> ① **GPU 渲染画面，是不是都用三角形拼出来的？**
> ② **GPU 是并发处理的吗？画面太复杂一次跑不完，要 CPU 中转缓存吗？逻辑是什么？**

##### 一、为什么 GPU 渲染都基于三角形？

**结论：是的，主流光栅化 GPU 管线（OpenGL / DirectX / Vulkan / Metal）几乎全部以三角形为最小渲染图元。**

```
为什么偏偏是"三角形"，而不是四边形/多边形？

  1) 三点必共面 —— 三角形天然是"平的"，不会出现非平面四边形那种扭曲歧义；
  2) 凸性恒成立 —— 三角形一定是凸多边形，光栅化（判断像素是否在内部）算法极其简单；
  3) 重心坐标 (α, β, γ) 唯一 —— 顶点属性（颜色/UV/法线）插值有统一公式；
  4) 任意多边形都能被切成三角形 —— 通用性最强；
  5) 硬件友好 —— 固定 3 个顶点，便于 GPU 用统一的 SIMD 单元批量处理。

所以：
  曲面 → 三角网格（建模/导出阶段已离散化）
  曲线 → 描边时也走三角形条带（如线宽 > 1 像素）
  字体 → TrueType 贝塞尔轮廓 → 三角化（CPU 或 Compute Shader 做）
  粒子/精灵 → 两个三角形拼成的 Quad
```

**少数例外**：
- **点光栅化** / **线光栅化**：仍是基本图元（`GL_POINTS` / `GL_LINES`），但实际占比极小。
- **光线追踪管线（RTX / DXR）**：底层加速结构 BVH 仍是按三角形构建（也支持 AABB + 自定义 Intersection Shader 处理隐式曲面）。
- **Compute / 软光栅 / Splat 渲染**（如 3D Gaussian Splatting）：跳过传统三角形管线，但属于研究/特殊场景。

##### 二、GPU 渲染流水线：三角形是怎么被处理的

```
CPU 侧                              GPU 侧（高度并行）
─────────────────────────           ──────────────────────────────────
准备 VertexBuffer / IndexBuffer
       ↓
Draw Call (glDrawElements …)
       ↓
                              ┌──→ ① Vertex Shader（顶点着色器）
                              │      每个顶点一个线程，并行执行
                              │      MVP 变换：模型空间 → 裁剪空间
                              │
                              ├──→ ② Primitive Assembly（图元装配）
                              │      按索引把 3 个顶点组装成三角形
                              │
                              ├──→ ③ Clipping & Culling（裁剪剔除）
                              │      视锥外丢弃、背面剔除
                              │
                              ├──→ ④ Rasterization（光栅化）
                              │      把三角形扫描成一堆 2×2 的像素块
                              │     （Quad，便于求 ddx/ddy 偏导）
                              │
                              ├──→ ⑤ Fragment / Pixel Shader
                              │      每个像素一个线程，并行执行
                              │      纹理采样、光照计算、PBR…
                              │
                              └──→ ⑥ ROP（深度测试、混合、写 Framebuffer）
                                     Z-Test / Alpha Blend / 写入颜色缓冲
```

##### 三、是并发的吗？—— 是，而且是"多层并行"

GPU 是典型的 **SIMT（Single Instruction Multiple Threads）** 架构：

```
并行的层级：

  Draw Call 内的并行：
    • 一次 Draw Call 可能有几十万个顶点 → 几十万个 VS 线程
    • 一帧可能有几百万个像素 → 几百万个 PS 线程
    • NVIDIA：32 线程一个 Warp；AMD：64 线程一个 Wavefront
    • 同一 Warp 内的线程"锁步执行"同一条指令（SIMD）

  SM（Streaming Multiprocessor）级并行：
    • 一颗 GPU 有几十~上百个 SM
    • 每个 SM 同时跑多个 Warp（隐藏访存延迟）
    • RTX 4090：128 个 SM × 数千个 CUDA 核心

  管线阶段并行：
    • 三角形 A 在做 PS 时，三角形 B 同时在做 VS（流水线重叠）
    • 不同 Draw Call 也可能并发（只要无资源依赖）

  CPU/GPU 异步并行：
    • CPU 在准备第 N+1 帧的命令时，GPU 还在渲染第 N 帧
    • 通过 Command Queue + Fence 同步
```

##### 四、画面太复杂一次跑不完，怎么办？需要 CPU 中转缓存吗？

**核心结论**：**绝大多数情况下不需要 CPU 中转**。GPU 自己有完整的"分批 / 缓冲 / 排队"机制；CPU 的角色是**指挥官 + 资源准备**，而不是"中转站"。

###### ① GPU 自己怎么"切片"消化海量三角形？

```
机制 1：Tile-Based / Bin Rasterization（分块光栅化）
  • 移动端 GPU（Mali / Adreno / Apple GPU）几乎全用 TBR/TBDR
  • 把屏幕切成 16×16 或 32×32 的 Tile，每个 Tile 单独渲染
  • 优点：Tile 内的颜色/深度缓冲塞进片上 SRAM，省带宽
  • 桌面 NVIDIA 从 Maxwell 起也用了类似思想（Tiled Caching）

机制 2：Warp/Wavefront 调度
  • 顶点/像素被切成 32 或 64 个一组的小批次
  • SM 上同时驻留几十个 Warp，谁的数据准备好了就跑谁
  • 自动隐藏内存访问延迟，无需 CPU 介入

机制 3：Command Buffer 排队
  • CPU 提交的所有 Draw Call 进入 GPU 命令队列
  • GPU 按队列顺序消费，跑不完就排着 —— 不会"溢出"
  • 单帧太重，结果就是这一帧拉长 → 帧率下降，但不会崩
```

###### ② 真正需要 CPU 配合的场景

CPU 不是"中转缓存"，而是**资源调度者**。下列情况 CPU 必须介入：

```
场景 A：显存不够（资源驻留管理）
  • 总贴图/网格 > 显存（如开放世界游戏 8GB 资源 vs 6GB 显存）
  • 解决方案：
    ├── 流式加载（Streaming）：CPU 监控相机位置，
    │   动态把"快进入视野"的资源从硬盘/内存上传到显存，
    │   把"远离的"资源从显存释放
    ├── Virtual Texture / SVT：纹理切成 Page，按需上传
    └── Mesh LOD：远处用低模，近处用高模

场景 B：单帧太重（分帧 / 异步渲染）
  • 一帧渲染时间 > 16ms（60fps 预算）
  • 解决方案：
    ├── 异步计算（Async Compute）：把阴影/SSAO/粒子放到独立队列，
    │   与主渲染并行
    ├── 时间复用（Temporal Amortization）：
    │   阴影、GI、反射 N 帧更新一次，靠 TAA 抖动平滑
    ├── Checkerboard Rendering：每帧只渲染一半像素，
    │   下一帧补另一半
    └── DLSS / FSR / XeSS：低分辨率渲染 + AI 超分

场景 C：CPU/GPU 必须同步（回读）
  • GPU 渲染结果需要 CPU 读取（截图、像素拾取、物理回读）
  • 关键点：直接 ReadPixels 会强制 GPU 完成所有命令，
    造成"GPU 等 CPU"的气泡 → 严重掉帧
  • 优化：用 Persistent Mapped Buffer + 多缓冲（N 帧后再读）
```

###### ③ CPU/GPU 协作流程图

```
CPU 时间轴       帧 N-1 准备   帧 N 准备     帧 N+1 准备   帧 N+2 准备
                ─────────────────────────────────────────────────────
                  收集场景        收集场景        收集场景
                  剔除/排序       剔除/排序       剔除/排序
                  上传变化资源    上传变化资源    上传变化资源
                  生成 Cmd Buffer 生成 Cmd Buffer 生成 Cmd Buffer
                       │              │              │
                   submit         submit         submit
                       ▼              ▼              ▼
GPU 时间轴       ┄┄┄┄┄┄┄┄┄┄ 渲染帧 N-1 ── 渲染帧 N ── 渲染帧 N+1 ──
                                            ↑
                              这就是为什么"输入延迟"通常有 1~3 帧：
                              CPU 永远在为未来 1-2 帧做准备
                              GPU 在渲染 1-2 帧前 CPU 已提交的命令

同步原语：
  • Fence / Semaphore：GPU 完成时通知 CPU
  • Barrier：保证资源在被读之前已写完
  • Triple Buffering：三个 FrameResource 轮转，CPU 不阻塞等 GPU
```

##### 五、一张图总结：复杂场景的整体处理逻辑

```
                ┌──────────────────────────────────────┐
                │  应用层（CPU）                        │
                │  ├── 视锥剔除 / 遮挡剔除 / LOD 选择     │
                │  ├── 资源流式加载（按距离/可见性）       │
                │  ├── 排序合批（减少 Draw Call）         │
                │  └── 生成 Command Buffer             │
                └──────────────┬───────────────────────┘
                               │ 提交命令（Submit）
                               ▼
                ┌──────────────────────────────────────┐
                │  驱动 + GPU 命令队列（FIFO）            │
                │  Graphics Queue / Compute Queue /     │
                │  Copy Queue 多队列并行                  │
                └──────────────┬───────────────────────┘
                               ▼
                ┌──────────────────────────────────────┐
                │  GPU 硬件                            │
                │  ├── 顶点处理（VS）—— 数十万线程并行     │
                │  ├── 三角形装配 + 光栅化（按 Tile 切片）  │
                │  ├── 像素着色（PS）—— 数百万线程并行     │
                │  └── 写回 Framebuffer                │
                └──────────────────────────────────────┘

  → 跑不完会怎样？
     不会崩，只会"这一帧花的时间变长"，表现为帧率下降。
     超过容忍度时，由 CPU 侧通过 LOD/剔除/降分辨率/异步分帧 来主动减负，
     而不是把数据"中转"到 CPU 内存里再慢慢喂回去。
```

> **一句话总结**：
> - 是的，GPU 渲染就是**海量三角形 + 海量像素的并行处理**；
> - GPU 自带分块/分批/排队机制，**单帧画不完只会掉帧、不会"溢出"**；
> - CPU 不做"中转缓存"，而是做**资源管理 + 命令编排 + 多帧调度**——通过流式加载、LOD、异步计算、分帧摊销等手段，把负载压到 GPU 一帧能吃下的范围内。

#### 6.1.2 纹理贴图：把一张 2D 图像贴到三角网格立体上

> 这一小节回答一个非常具体的问题：
> **一张普通的 PNG/JPG 图像，是怎么"贴"到由几千个三角形拼起来的 3D 模型表面上的？**
>
> 这背后是图形学最核心的概念之一：**UV 映射 + 重心坐标插值 + 纹理采样**。

##### 一、核心思想：建立"3D 三角形 ↔ 2D 图像区域"的映射

```
现实问题：
  ┌─────────────┐       ┌──────────┐
  │ 3D 茶壶模型  │  ❓    │ 一张贴图  │
  │ (1万个三角形)│ ◀───▶ │ (PNG)    │
  └─────────────┘       └──────────┘
        ↑                     ↑
     立体表面              平面图像
     每个三角形             每个像素

  问题：模型表面上的"哪一点" 应该显示 贴图上的"哪一个像素"？

解法：给每个 3D 顶点额外存一个 2D 坐标 (u, v)
  → 这个 (u, v) 叫"纹理坐标"或"UV 坐标"
  → 范围通常是 [0, 1] × [0, 1]
  → (0,0) = 图像左下角，(1,1) = 图像右上角
```

##### 二、UV 映射：把"三角形"复制到 2D 平面上

每个 3D 顶点不仅有位置 `(x, y, z)`、法线 `(nx, ny, nz)`，还要存一对 `(u, v)`：

```
顶点结构（典型 GPU 输入）：
  struct Vertex {
      vec3 position;   // 3D 位置
      vec3 normal;     // 法线
      vec2 uv;         // ★ 纹理坐标（关键）
      vec4 color;      // 可选
  };

每个三角形 = 3 个顶点 = 3 对 (u, v)
  → 在贴图上"圈出"一个对应的 2D 三角形

  3D 空间                       2D 贴图（UV 空间）
  ──────────                    ───────────────
                                v↑
        V1 (0.2, 0.1, 0.5)         │   ●V1 (0.2, 0.8)
       /  \                        │  / \
      /    \                       │ /   \
     /      \                      │/     \
    V0──────V2                     ●───────●
   (0,0,0) (1,0,0)              V0(0.1,0.1) V2(0.5,0.1)
                                   └──────────→ u
```

**关键点**：
- **UV 是预先指定的**——美术在 Maya/Blender/3ds Max 中"展 UV"（Unwrap），把 3D 模型像剥橘子皮一样摊平到 2D；
- **同一个 3D 三角形 ↔ 贴图上的一个 2D 三角形**，但它们的形状/大小**不必相同**（被拉伸/压缩是常态）；
- **UV 可以重叠/平铺**：草地、墙砖等重复纹理用 `u, v > 1` 让 GPU 自动取模平铺。

##### 三、"展 UV"的常见手段

```
① 平面投影（Planar Projection）
   把模型从某个方向"压扁"到平面
   适合：地面、墙面等平整物体

② 立方体投影（Box Projection）
   6 个面分别用平面投影
   适合：箱子、建筑物

③ 球面/柱面投影
   适合：地球仪、瓶身

④ 自动展开（Auto Unwrap / LSCM 算法）
   按"接缝（Seam）"切开模型，最小化拉伸
   适合：复杂角色、有机模型
   接缝痕迹要藏在不显眼处（人物头顶、背后）

⑤ 手工展 UV
   美术逐个面调整，质量最高
```

最终输出：每个顶点都带一个稳定的 (u, v) ——这套数据存在模型文件（FBX / glTF / OBJ）里，运行时直接送 GPU。

##### 四、运行时：GPU 如何为每个像素采样贴图

这是**核心流程**——也就是"贴图究竟怎么贴上去"的真相：

```
流水线（每帧每像素都跑一遍）：

┌─────────────────────────────────────────────────────────┐
│ Step 1: 顶点着色器（VS）—— 输出 3 顶点的 UV             │
│                                                         │
│   对三角形的 3 个顶点，分别输出：                        │
│     gl_Position = MVP * v.position;   // 屏幕坐标       │
│     out.uv      = v.uv;               // 直接透传        │
│                                                         │
│   GPU 拿到 3 顶点的 (u, v) → 准备插值                    │
└──────────────────────────┬──────────────────────────────┘

> **🔑 MVP 是什么？**（顶点着色器最核心的一行）
>
> `MVP` 是三个 4×4 矩阵的连乘积：**`MVP = P · V · M`**，作用是把一个 3D 顶点
> 从"模型自身坐标系"一路变换到"屏幕坐标系"。三个矩阵分别负责一段路：
>
> ---
>   v.position   ──M──▶   世界空间   ──V──▶   相机空间   ──P──▶   裁剪空间
>   (模型空间)            (World)             (View/Eye)           (Clip)
>     局部坐标             绝对坐标            以相机为原点          准备做透视除法
> ---
>
> | 矩阵 | 全名 | 作用 | 由谁决定 |
> |------|------|------|---------|
> | **M** | Model 矩阵 | 把模型放到世界中正确的位置/朝向/大小（平移 T·旋转 R·缩放 S） | 物体在场景中的摆放 |
> | **V** | View 矩阵 | 把世界"反着搬到相机面前"（其实是相机变换的逆） | 摄像机的位置和朝向 |
> | **P** | Projection 矩阵 | 把 3D 视锥压扁成 2D 屏幕（透视投影 / 正交投影） | 相机的 FOV、宽高比、近远裁剪面 |
>
> **为什么必须连乘成 MVP**：
>   • 如果分三步乘，每个顶点要做 3 次矩阵-向量乘法（3×16 = 48 次乘加）；
>   • CPU 端预先算好 `MVP = P*V*M` 一次，每个顶点只做 1 次（16 次乘加）→ 节省 3 倍算力；
>   • 同一个 Draw Call 里几十万个顶点都共享这一个 MVP（uniform 变量），极适合 GPU。
>
> **gl_Position 的特殊身份**：
>   • 它是 GLSL 内置变量，VS 必须给它赋值；
>   • 输出的是**齐次裁剪坐标 `(x, y, z, w)`**，GPU 接下来会自动做"透视除法" `(x/w, y/w, z/w)` → 得到 NDC（归一化设备坐标 [-1,1]³）→ 再映射到屏幕像素。
>
> **同时透传 UV 的原因**：
>   • UV 是顶点自带的 2D 纹理坐标，**不需要任何空间变换**——它只是"贴图上的索引"；
>   • VS 把它原样输出（`out.uv = v.uv;`），交给光栅化阶段去做"按重心坐标插值"（见 Step 2）。
>
> > 📚 关于 M/V/P 三个矩阵的具体形式（透视投影矩阵长什么样、视图矩阵怎么从 lookAt 推出来等），详见 **§5 渲染流水线 / 坐标空间变换** 一节。

                           ▼
┌─────────────────────────────────────────────────────────┐
│ Step 2: 光栅化 + 重心坐标插值                            │
│                                                         │
│   光栅化：把三角形扫描成屏幕上的一堆像素                   │
│   对每个像素 P，算出它相对于 V0/V1/V2 的重心坐标 (α,β,γ) │
│       α + β + γ = 1                                     │
│                                                         │
│   该像素的 UV = α·uv0 + β·uv1 + γ·uv2                   │
│              （★透视正确插值：用 1/w 修正，避免远处贴图扭曲）│
│                                                         │
│   屏幕三角形                              贴图（2D）     │
│      V0                                    uv0          │
│      / \                                    / \          │
│     / P \                  ◀━插值━▶        / P'\         │
│    /  ●  \                                /  ●  \        │
│   V1─────V2                             uv1───uv2       │
│   像素 P 在 3D 三角形里                P 对应贴图上的 P'   │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│ Step 3: 片元着色器（FS）—— 纹理采样                      │
│                                                         │
│   uniform sampler2D uTex;                                │
│   in vec2 vUV;                                           │
│   void main() {                                          │
│       FragColor = texture(uTex, vUV); // 用插值后的 UV 采样│
│   }                                                      │
│                                                         │
│   texture() 内部做了 4 件事：                             │
│     ① 把 (u,v) ∈ [0,1] 映射回像素坐标 (u·W, v·H)         │
│     ② 处理边界：CLAMP / REPEAT / MIRROR                  │
│     ③ 滤波：NEAREST(取最近) / LINEAR(双线性) /           │
│              TRILINEAR(三线性，跨 mipmap)                │
│     ④ 各向异性过滤（Anisotropic）：斜视角下防糊           │
└─────────────────────────────────────────────────────────┘
```

##### 五、Mipmap：为什么需要"贴图金字塔"

```
问题：远处的物体在屏幕上只占几个像素，
      但仍然采样原始 4096×4096 大贴图 → 严重的摩尔纹/闪烁/带宽浪费

Mipmap 解法：
  预先把贴图缩小成一系列层级（每层尺寸 ÷ 2）：

  Level 0: 4096×4096   ← 近距离用
  Level 1: 2048×2048
  Level 2: 1024×1024
  Level 3:  512× 512
  ...
  Level 12:    1×   1   ← 极远距离用

  GPU 根据"屏幕像素覆盖了贴图多大区域"自动选层级
  （由 ddx/ddy 偏导数计算），并在层与层之间插值（Trilinear）。

  代价：内存增加 33%（1 + 1/4 + 1/16 + ... ≈ 4/3 倍）
  收益：远处稳定、采样命中缓存、Bandwidth 暴降
```

##### 六、完整端到端示例：贴一张木箱贴图

```
准备阶段（离线）：
  ① 美术建模一个立方体（12 个三角形，8 个顶点）
  ② 为每个顶点指定 UV（立方体六面展开成"十字图"）
  ③ 烘焙/绘制贴图：把木纹画在十字布局的对应区域
  ④ 导出 .gltf 文件（顶点 + 索引 + UV + 贴图引用）

加载阶段（运行时一次）：
  ⑤ CPU 读 .gltf，把顶点数据上传到 GPU 的 VBO
  ⑥ CPU 把 PNG 解码成像素数组，上传到 GPU 的 Texture Object
  ⑦ 生成 Mipmap 链（glGenerateMipmap 或预先算好上传）

渲染阶段（每帧 60 次）：
  ⑧ CPU 提交 Draw Call：glDrawElements(GL_TRIANGLES, ...)
  ⑨ GPU 顶点着色器：变换每个顶点位置，透传 UV
  ⑩ GPU 光栅化：每个像素插值出 (u, v)
  ⑪ GPU 片元着色器：texture(woodTex, uv) → 采样到颜色
  ⑫ 深度测试 + 写入 Framebuffer
  ⑬ 屏幕看到一个贴着木纹的立方体 ✓
```

##### 七、进阶：除了基础颜色贴图还有什么？

现代 PBR 渲染中，一个材质往往用 4~7 张贴图，**全部用同一套 UV**：

| 贴图类型             | 内容                       | 用途                       |
|---------------------|---------------------------|---------------------------|
| **Albedo / BaseColor** | 物体本色（去掉光影）         | 基础颜色                   |
| **Normal Map**         | 切线空间法线 (R,G,B→x,y,z) | 在不增加三角形的前提下表现凹凸|
| **Roughness**          | 表面粗糙度（0=镜面 1=粗糙）  | PBR 高光形状               |
| **Metallic**           | 金属度（0=非金属 1=金属）    | 区分金属/介电              |
| **AO (Ambient Occlusion)** | 环境光遮蔽            | 缝隙处的暗化               |
| **Emissive**           | 自发光颜色                  | 灯泡、屏幕、岩浆           |
| **Height / Displacement** | 高度图                  | 视差贴图 / 真实顶点位移    |

> 法线贴图的原理（最常被问的"为什么平面看起来凹凸"）：
> Normal Map 在每个像素存储一个**切线空间下的法线方向**，PS 用它替代真正的几何法线参与光照计算 → 视觉上产生凹凸感，但三角形依然是平的。

##### 八、一张图总结：从 PNG 到屏幕像素的完整旅程

```
   美术阶段                    资产阶段                  运行时
 ─────────────                ─────────────              ─────────────
 ① 建模 + 展 UV       →    ④ 导出 glTF/FBX     →   ⑦ 加载到显存
 ② 绘制贴图(PNG)              （顶点+UV+贴图）         (VBO + Texture)
 ③ 烘焙 PBR 贴图组                                        │
                                                          ▼
                                                  ⑧ Draw Call 提交
                                                          │
                                                          ▼
                                ┌───────────────────────────────────────┐
                                │ GPU 流水线（每像素并行）              │
                                │  VS：透传 UV                         │
                                │   ↓                                   │
                                │  光栅化 + 重心坐标透视插值 → 像素 UV  │
                                │   ↓                                   │
                                │  PS：texture(tex, uv) 采样            │
                                │       └─ Mipmap 选层 + 三线性 + 各向异性 │
                                │   ↓                                   │
                                │  ROP：深度测试 + 混合 + 写 Framebuffer│
                                └───────────────────────────────────────┘
                                                          │
                                                          ▼
                                                    ⑨ 屏幕显示
```

> **一句话总结**：
> - **本质**：给每个 3D 顶点存一对 `(u, v)` 坐标，把 3D 三角形和 2D 贴图区域**一一对应**起来；
> - **关键技术**：UV 展开（离线美术）+ 重心坐标透视插值（光栅化）+ 纹理采样与 Mipmap（片元着色器）；
> - **GPU 视角**：贴图就是一张 2D 数组，UV 就是数组下标——把"几何坐标"翻译成"贴图坐标"的过程，就是整套贴图技术的核心。

### 6.2 曲线与曲面

```
贝塞尔曲线（Bézier Curve）：
  B(t) = Σ C(n,i) · (1-t)^(n-i) · t^i · Pi，t∈[0,1]
  
  三次贝塞尔（最常用）：
  B(t) = (1-t)³P0 + 3(1-t)²tP1 + 3(1-t)t²P2 + t³P3
  
  性质：
  ├── 端点插值：B(0)=P0，B(1)=P3
  ├── 凸包性：曲线在控制点凸包内
  └── 变差缩减性：曲线比控制多边形更光滑
  
  应用：字体轮廓（TrueType）、路径动画、UI 动画曲线

B 样条（B-Spline）：
  分段多项式，局部控制（修改一个控制点只影响局部）
  
NURBS（非均匀有理 B 样条）：
  工业 CAD 标准，可精确表示圆锥曲线
  
贝塞尔曲面（Bézier Surface）：
  B(u,v) = ΣΣ C(m,i)·C(n,j)·(1-u)^(m-i)·u^i·(1-v)^(n-j)·v^j·Pij
  
  应用：汽车车身设计、角色建模（细分曲面基础）
```

### 6.3 细分曲面

```
Catmull-Clark 细分（最常用）：
  每次细分将四边形网格细化为 4 倍数量的四边形
  极限曲面是 C² 连续的（除奇异点外）
  
  应用：Pixar 电影角色建模，Maya/Blender 默认细分

Loop 细分：
  适用于三角网格
  极限曲面是 C² 连续的（除奇异点外）

自适应细分（Adaptive Subdivision）：
  根据曲率、屏幕空间大小动态调整细分级别
  DirectX 11 曲面细分着色器（Tessellation Shader）
```

### 6.4 程序化几何生成

```
噪声函数（Noise Functions）：

  Perlin 噪声：
  ├── 梯度噪声，视觉上自然
  ├── 多倍频叠加（fBm）→ 地形、云朵
  └── GLSL 实现：
      float noise = fract(sin(dot(uv, vec2(12.9898,78.233))) * 43758.5453);

  Simplex 噪声（Ken Perlin 改进版）：
  ├── 计算效率更高（O(n²) vs O(2^n)）
  └── 视觉伪影更少

  Worley 噪声（细胞噪声）：
  └── 生成细胞/石头/皮肤纹理

SDF 建模（Inigo Quilez 方法）：
  // 球体 SDF
  float sdSphere(vec3 p, float r) { return length(p) - r; }
  
  // 布尔运算
  float opUnion(float d1, float d2)     { return min(d1, d2); }
  float opSubtract(float d1, float d2)  { return max(-d1, d2); }
  float opIntersect(float d1, float d2) { return max(d1, d2); }
  
  // 光滑并集（避免硬边）
  float opSmoothUnion(float d1, float d2, float k) {
      float h = clamp(0.5 + 0.5*(d2-d1)/k, 0.0, 1.0);
      return mix(d2, d1, h) - k*h*(1.0-h);
  }
```

---

## 七、仿真引擎与渲染框架

### 7.1 主流图形 API 对比

| API | 平台 | 抽象层次 | 学习曲线 | 适用场景 |
|-----|------|---------|---------|---------|
| **OpenGL** | 跨平台 | 高（驱动管理资源） | 低 | 学习入门、跨平台工具 |
| **Vulkan** | 跨平台 | 低（手动管理一切） | 极高 | 高性能游戏、引擎底层 |
| **DirectX 12** | Windows/Xbox | 低 | 极高 | PC/主机游戏 |
| **Metal** | Apple 全平台 | 中 | 中 | iOS/macOS/Apple Silicon |
| **WebGPU** | 浏览器 | 中 | 中 | Web 3D 应用 |

```
Vulkan 渲染循环（简化）：

  初始化：
  VkInstance → VkPhysicalDevice → VkDevice → VkQueue
  → VkSwapchain → VkRenderPass → VkFramebuffer
  → VkCommandPool → VkCommandBuffer
  → VkPipeline（含 Shader 编译）

  每帧渲染：
  vkAcquireNextImageKHR()     // 获取交换链图像
  vkBeginCommandBuffer()      // 开始录制命令
  vkCmdBeginRenderPass()      // 开始渲染通道
  vkCmdBindPipeline()         // 绑定渲染管线
  vkCmdBindVertexBuffers()    // 绑定顶点缓冲
  vkCmdDrawIndexed()          // 绘制调用
  vkCmdEndRenderPass()        // 结束渲染通道
  vkEndCommandBuffer()        // 结束录制
  vkQueueSubmit()             // 提交到 GPU
  vkQueuePresentKHR()         // 呈现到屏幕
```

### 7.2 游戏引擎渲染管线

#### Unreal Engine 5 渲染特性

```
UE5 核心渲染技术：

  Nanite（虚拟化几何体）：
  ├── 原理：将高精度网格（数亿三角形）流式加载
  ├── 自动 LOD：根据屏幕像素大小动态调整细节
  └── 效果：电影级资产直接用于实时渲染

  Lumen（全动态全局光照）：
  ├── 软件光线追踪（Screen Trace + Mesh Distance Fields）
  ├── 硬件光线追踪加速（可选）
  └── 实时间接光照 + 反射

  TSR（时间超分辨率）：
  ├── 类似 DLSS 的 AI 超分
  └── 从低分辨率渲染输出高质量图像

  Virtual Shadow Maps：
  └── 超高分辨率阴影贴图（虚拟化分页）

  Substrate（材质系统）：
  └── 分层材质，物理正确的材质混合
```

#### Unity HDRP 渲染特性

```
Unity HDRP 核心特性：

  Render Graph：
  └── 声明式渲染管线，自动资源管理

  Ray Tracing（DXR）：
  ├── 实时光线追踪阴影、反射、AO
  └── 路径追踪模式（离线质量）

  Adaptive Probe Volumes（APV）：
  └── 自适应探针体积，动态 GI

  DLSS / FSR 集成：
  └── AI 超分辨率内置支持
```

### 7.3 离线渲染引擎

| 引擎 | 算法 | 主要用途 | 特点 |
|-----|------|---------|------|
| **Arnold** | 路径追踪 | 影视 VFX | 工业标准，Maya/Houdini 集成 |
| **RenderMan** | 路径追踪 | Pixar 电影 | 最高质量，支持 OSL |
| **V-Ray** | 路径追踪 | 建筑可视化 | 速度快，3ds Max/SketchUp 集成 |
| **Cycles（Blender）** | 路径追踪 | 开源创作 | 免费，GPU 加速 |
| **PBRT** | 路径追踪 | 学术研究 | 开源，教学标准 |
| **Mitsuba 3** | 可微渲染 | 研究 | 支持梯度计算，NeRF 训练 |

### 7.4 实时光线追踪

```
DXR（DirectX Raytracing）/ VK_KHR_ray_tracing 架构：

  加速结构（Acceleration Structure）：
  ├── BLAS（Bottom-Level AS）：单个网格的 BVH
  └── TLAS（Top-Level AS）：场景中所有 BLAS 的实例

  光线追踪着色器类型：
  ├── Ray Generation Shader：发射光线
  ├── Intersection Shader：自定义求交（用于程序化几何）
  ├── Any-Hit Shader：光线击中时（用于透明物体）
  ├── Closest-Hit Shader：最近交点着色
  └── Miss Shader：光线未击中时（天空盒）

  NVIDIA RTX 硬件加速：
  └── RT Core：专用光线-BVH 求交硬件单元
      性能：比纯 Shader 实现快 10x

  实时光追应用：
  ├── 光追阴影（Ray Traced Shadows）
  ├── 光追反射（Ray Traced Reflections）
  ├── 光追 AO（Ray Traced Ambient Occlusion）
  └── 路径追踪（Path Tracing，需 AI 降噪）
```

### 7.5 物理仿真引擎

```
刚体仿真：
  引擎：PhysX（NVIDIA）、Bullet（开源）、Havok
  
  核心算法：
  ├── 碰撞检测：BVH + GJK/EPA 算法
  ├── 约束求解：Sequential Impulse（SI）
  └── 积分：半隐式欧拉

流体仿真：
  SPH（光滑粒子流体动力学）：
  └── 粒子方法，适合自由液面（水花、飞溅）
  
  FLIP（流体隐式粒子）：
  └── 粒子 + 网格混合，减少数值耗散
      Houdini 流体仿真的核心算法
  
  MPM（物质点法）：
  └── 统一处理固体/流体/雪/沙
      Disney 电影《冰雪奇缘》雪地仿真

布料仿真：
  Position-Based Dynamics（PBD）：
  └── 基于位置约束，稳定，实时友好
      UE5/Unity 布料仿真
  
  FEM（有限元法）：
  └── 物理精确，用于影视级布料

软体仿真：
  FEM 弹性体：
  └── 极分解 + 共旋转 FEM
      用于：肌肉、器官、橡胶

粒子系统：
  GPU 粒子（Compute Shader）：
  └── 百万粒子实时仿真
      烟雾、火焰、爆炸、魔法效果
```

---

## 八、AI 在图形学中的应用

### 8.1 神经渲染（Neural Rendering）

```
神经渲染核心思想：
  用神经网络替代或增强传统渲染管线的某些部分

  传统渲染：场景描述 → 渲染算法 → 图像
  神经渲染：场景描述 → 神经网络 → 图像

主要方向：
  ├── 神经辐射场（NeRF）：隐式场景表示
  ├── 神经纹理：可学习的纹理表示
  ├── 神经材质：数据驱动的 BRDF
  ├── 神经光照：环境光照的神经表示
  └── 可微渲染：支持梯度的渲染器（用于逆渲染）

可微渲染（Differentiable Rendering）：
  ∂L/∂θ：渲染结果对场景参数的梯度
  
  应用：
  ├── 从图像重建 3D 场景（逆渲染）
  ├── 材质估计（从照片恢复 PBR 参数）
  └── 神经网络训练（NeRF、3DGS）
  
  工具：Mitsuba 3、PyTorch3D、nvdiffrast
```

### 8.2 NeRF 与 3D Gaussian Splatting

```
NeRF（Neural Radiance Field，2020）：

  核心思想：
  用 MLP 神经网络隐式表示 3D 场景
  输入：(x,y,z,θ,φ) → 输出：(RGB, σ)
  
  渲染：沿光线积分体密度和颜色
  C(r) = ∫ T(t)·σ(r(t))·c(r(t),d) dt
  
  训练：从多视角图像优化网络参数
  
  优点：高质量新视角合成
  缺点：训练慢（数小时），渲染慢（每帧数秒）

3D Gaussian Splatting（3DGS，2023）：

  核心思想：
  用数百万个 3D 高斯椭球体表示场景
  每个高斯：位置 + 协方差矩阵 + 颜色（SH）+ 不透明度
  
  渲染：将 3D 高斯投影到 2D，按深度排序，alpha 混合
  
  优点：
  ├── 实时渲染（100+ FPS）
  ├── 训练快（数分钟）
  └── 可编辑（直接操作高斯椭球）
  
  缺点：内存占用大（数百 MB）

应用：
  ├── 虚拟制片（LED 背景实时渲染）
  ├── 文化遗产数字化
  ├── 自动驾驶场景重建
  └── 游戏场景快速原型
```

### 8.3 AI 超分辨率（DLSS / FSR）

```
DLSS（Deep Learning Super Sampling，NVIDIA）：

  原理：
  ├── 以低分辨率（如 1080p）渲染
  ├── 输入：当前帧低分辨率 + 历史帧 + 运动向量
  └── 输出：高分辨率（如 4K）图像
  
  网络架构：卷积神经网络（CNN）
  训练数据：超高分辨率离线渲染图像
  
  DLSS 版本：
  ├── DLSS 2.x：质量大幅提升，支持 DLAA
  └── DLSS 3.x：帧生成（Frame Generation），插帧技术

FSR（FidelityFX Super Resolution，AMD）：

  FSR 1.0：空间超分，不依赖运动向量，无需训练
  FSR 2.0：时间超分，类似 DLSS 2.x，开源
  FSR 3.0：帧生成，类似 DLSS 3.x

XeSS（Intel 超分辨率）：
  └── 支持 Intel Arc GPU，也支持其他 GPU（DP4a 模式）

AI 降噪（Denoising）：
  OIDN（Intel Open Image Denoise）：开源，CPU/GPU
  OptiX Denoiser（NVIDIA）：GPU 加速
  用途：路径追踪降噪，将 1spp 提升到接近 1024spp 质量
```

### 8.4 AI 辅助内容生成

```
3D 模型生成：
  Point-E（OpenAI）：文本 → 点云 → 网格
  Shap-E（OpenAI）：文本/图像 → 隐式函数 → 网格
  DreamFusion：文本 → NeRF（SDS 损失）
  Magic3D：文本 → 高分辨率 3D 网格
  One-2-3-45：单张图像 → 3D 模型

纹理生成：
  Text2Tex：文本 → 3D 模型纹理
  TEXTure：交互式 AI 纹理绘制
  Stable Diffusion + ControlNet：图像引导纹理生成

动画生成：
  Motion Diffusion Model（MDM）：文本 → 人体动作
  AnimateDiff：图像 → 动画序列
  DreamPose：图像 + 姿态 → 人物动画

材质生成：
  MatFuse：文本 → PBR 材质贴图（Albedo/Normal/Roughness/Metallic）
  Stable Diffusion + ControlNet：图像 → 无缝纹理
```

### 8.5 Shader 自动生成

```
AI 辅助 Shader 编写：

  工具：
  ├── GitHub Copilot：GLSL/HLSL 代码补全
  ├── ChatGPT/Claude：生成完整 Shader，解释算法
  └── Shadertoy AI：基于 Shadertoy 数据集微调的模型

  典型工作流：
  1. 描述效果："实现一个卡通风格的边缘描边效果"
  2. AI 生成 Shader 代码
  3. 工程师审查、调整参数
  4. 集成到引擎

  注意事项：
  ✅ AI 生成的 Shader 需要验证物理正确性
  ✅ 检查性能（避免过多分支、纹理采样）
  ❌ 不要直接使用未经测试的 AI 代码
```

---

## 九、专项方向

### 9.1 方向选择矩阵

| 方向 | 技术难度 | 市场需求 | 薪资水平 | 推荐度 |
|-----|---------|---------|---------|-------|
| 游戏引擎渲染工程师 | ★★★★ | ★★★★★ | ★★★★★ | ⭐⭐⭐⭐⭐ |
| 影视 VFX 技术总监 | ★★★★★ | ★★★★ | ★★★★★ | ⭐⭐⭐⭐⭐ |
| 神经渲染研究员 | ★★★★★ | ★★★★★ | ★★★★★ | ⭐⭐⭐⭐⭐ |
| 图形 API 底层开发 | ★★★★★ | ★★★ | ★★★★ | ⭐⭐⭐⭐ |
| 可视化工程师 | ★★★ | ★★★★ | ★★★ | ⭐⭐⭐ |
| AR/VR 渲染工程师 | ★★★★ | ★★★★★ | ★★★★ | ⭐⭐⭐⭐⭐ |

### 9.2 各方向核心技术栈

```
游戏引擎渲染方向：
  └── UE5/Unity + Vulkan/DX12 + PBR + 实时 GI + 光线追踪

影视 VFX 方向：
  └── Houdini + Arnold/RenderMan + 流体/布料仿真 + Python

神经渲染研究方向：
  └── PyTorch + NeRF/3DGS + 可微渲染 + CUDA 编程

AR/VR 方向：
  └── OpenXR + 移动端优化 + 注视点渲染 + 延迟渲染
```

---

## 十、学习路径建议

### 10.1 小白入门路径（12-18 个月）

```
Month 1-2：数学基础
  └── 线性代数（向量、矩阵、变换）
  └── 推荐：3Blue1Brown《线性代数的本质》（B站有中文字幕）

Month 3-4：OpenGL 入门
  └── 基本渲染管线 → 着色器 → 纹理 → 光照
  └── 教程：LearnOpenGL.com（有中文版）
  └── 工具：OpenGL + GLFW + GLM

Month 5-6：光照与着色
  └── Phong → Blinn-Phong → PBR 材质系统
  └── 法线贴图、阴影贴图、环境贴图

Month 7-9：引擎实战
  └── 选择 Unity 或 UE5，完成一个完整的渲染场景
  └── 学习 Shader Graph（Unity）或 Material Editor（UE5）

Month 10-12：进阶渲染
  └── 延迟渲染 → 屏幕空间效果（SSAO/SSR）→ 后处理

Month 13-18：专项深入（选一个方向）
  ├── 游戏渲染：Vulkan + 实时光追 + UE5 源码
  ├── 神经渲染：PyTorch + NeRF/3DGS 复现
  └── 物理仿真：Houdini + 流体/布料仿真
```

### 10.2 有经验工程师的 AI 升级路径

```
Week 1-2：AI 工具链
  └── 用 ChatGPT/Copilot 辅助 Shader 编写
  └── 学习 Stable Diffusion 生成纹理/概念图

Week 3-4：NeRF/3DGS 实践
  └── 用手机拍摄物体，训练 3DGS 模型
  └── 工具：Gaussian Splatting（开源）、Luma AI（在线）

Month 2：神经渲染深入
  └── 阅读 NeRF/3DGS 论文，复现关键代码
  └── 学习 PyTorch3D / nvdiffrast

Month 3+：可微渲染与逆渲染
  └── 从图像重建材质参数
  └── 探索 AI 辅助内容生成工作流
```

---

## 十一、参考资源

### 11.1 书籍推荐

| 书名 | 作者 | 适合人群 |
|-----|------|---------|
| 《Real-Time Rendering》第4版 | Akenine-Möller 等 | 图形学圣经，必读 |
| 《Physically Based Rendering》（PBRT）| Pharr 等 | 离线渲染权威，免费在线 |
| 《3D Math Primer for Graphics》 | Dunn & Parberry | 数学基础入门 |
| 《Fundamentals of Computer Graphics》 | Shirley & Marschner | 图形学入门教材 |
| 《GPU Gems 1/2/3》 | NVIDIA | 实战技巧，免费在线 |
| 《Shader X / GPU Pro》系列 | 多位作者 | 高级 Shader 技术 |
| 《Mathematics for 3D Game Programming》 | Lengyel | 游戏数学深入 |

### 11.2 在线学习资源

| 资源 | 类型 | 链接 |
|-----|------|------|
| LearnOpenGL | 入门教程 | https://learnopengl.com |
| Shadertoy | Shader 练习 | https://www.shadertoy.com |
| PBRT 在线版 | 离线渲染 | https://pbrt.org |
| Inigo Quilez 博客 | SDF/程序化 | https://iquilezles.org |
| Two Minute Papers | 论文速览 | YouTube |
| GAMES101/202 | 中文图形学课程 | B站，闫令琪主讲 |
| Scratchapixel | 从零实现 | https://scratchapixel.com |
| 3Blue1Brown | 线性代数可视化 | YouTube/B站 |

### 11.3 开源项目推荐

| 项目 | 用途 | 链接 |
|-----|------|------|
| **PBRT-v4** | 路径追踪学习 | github.com/mmp/pbrt-v4 |
| **Mitsuba 3** | 可微渲染 | github.com/mitsuba-renderer/mitsuba3 |
| **3D Gaussian Splatting** | 神经渲染 | github.com/graphdeco-inria/gaussian-splatting |
| **tiny-cuda-nn** | 神经网络 GPU 加速 | github.com/NVlabs/tiny-cuda-nn |
| **Open3D** | 点云处理 | github.com/isl-org/Open3D |
| **Blender** | 开源 3D 软件 | blender.org |
| **Filament** | PBR 渲染引擎 | github.com/google/filament |
| **bgfx** | 跨平台渲染 | github.com/bkaradzic/bgfx |

### 11.4 免费工具

| 工具 | 用途 | 获取方式 |
|-----|------|---------|
| **Blender** | 3D 建模/渲染/仿真 | blender.org 免费 |
| **RenderDoc** | GPU 调试/帧分析 | renderdoc.org 免费 |
| **NVIDIA Nsight** | GPU 性能分析 | NVIDIA 官网免费 |
| **Shadertoy** | 在线 Shader 编写 | shadertoy.com 免费 |
| **Houdini Apprentice** | 程序化/仿真 | SideFX 免费版 |
| **Unity Personal** | 游戏引擎 | unity.com 免费 |
| **UE5** | 游戏引擎 | unrealengine.com 免费 |
| **OIDN** | AI 降噪 | openimagedenoise.github.io 免费 |

---

> **最后的话**：AI 时代的图形学，核心竞争力在于**扎实的数学基础 + 渲染原理理解 + 善用 AI 工具**。NeRF 和 3DGS 的出现让"从照片重建 3D 场景"变得触手可及；DLSS/FSR 让实时光线追踪成为现实；AI 生成工具让内容创作效率倍增。但这一切的背后，都是线性代数、概率论、微积分的深厚积累。打好数学基础，理解渲染方程，再用 AI 工具放大你的能力，才是正确的学习路径。

---

*文档创建时间：2026-06-22*  
*标签：#图形学 #渲染 #Shader #OpenGL #Vulkan #PBR #光线追踪 #NeRF #3DGS #DLSS #物理仿真 #AI辅助设计 #数学基础*
