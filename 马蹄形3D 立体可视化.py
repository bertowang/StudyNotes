# -*- coding: utf-8 -*-
"""
CIE 1931 色度图（马蹄形）3D 立体可视化
- 横纵轴：CIE xy 色度坐标
- 竖轴：亮度 Y（这里用 0~1 表示）
- 颜色：将 xyY -> XYZ -> sRGB 后填充
- 交互：matplotlib 默认窗口支持鼠标左键拖动旋转视角
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.tri import Triangulation

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


# ---------------------------------------------------------------
# 1. CIE 1931 2° 标准观察者 色匹配函数 (380nm ~ 780nm, 步长5nm)
#    数据来源：CIE 官方标准（节选常用版）
# ---------------------------------------------------------------
# 波长 (nm)
wavelengths = np.arange(380, 781, 5)

# x_bar, y_bar, z_bar (CIE 1931 2°)
cmf = np.array([
    [0.001368, 0.000039, 0.006450],
    [0.002236, 0.000064, 0.010550],
    [0.004243, 0.000120, 0.020050],
    [0.007650, 0.000217, 0.036210],
    [0.014310, 0.000396, 0.067850],
    [0.023190, 0.000640, 0.110200],
    [0.043510, 0.001210, 0.207400],
    [0.077630, 0.002180, 0.371300],
    [0.134380, 0.004000, 0.645600],
    [0.214770, 0.007300, 1.039050],
    [0.283900, 0.011600, 1.385600],
    [0.328500, 0.016840, 1.622960],
    [0.348280, 0.023000, 1.747060],
    [0.348060, 0.029800, 1.782600],
    [0.336200, 0.038000, 1.772110],
    [0.318700, 0.048000, 1.744100],
    [0.290800, 0.060000, 1.669200],
    [0.251100, 0.073900, 1.528100],
    [0.195360, 0.090980, 1.287640],
    [0.142100, 0.112600, 1.041900],
    [0.095640, 0.139020, 0.812950],
    [0.057950, 0.169300, 0.616200],
    [0.032010, 0.208020, 0.465180],
    [0.014700, 0.258600, 0.353300],
    [0.004900, 0.323000, 0.272000],
    [0.002400, 0.407300, 0.212300],
    [0.009300, 0.503000, 0.158200],
    [0.029100, 0.608200, 0.111700],
    [0.063270, 0.710000, 0.078250],
    [0.109600, 0.793200, 0.057250],
    [0.165500, 0.862000, 0.042160],
    [0.225750, 0.914850, 0.029840],
    [0.290400, 0.954000, 0.020300],
    [0.359700, 0.980300, 0.013400],
    [0.433450, 0.994950, 0.008750],
    [0.512050, 1.000000, 0.005750],
    [0.594500, 0.995000, 0.003900],
    [0.678400, 0.978600, 0.002750],
    [0.762100, 0.952000, 0.002100],
    [0.842500, 0.915400, 0.001800],
    [0.916300, 0.870000, 0.001650],
    [0.978600, 0.816300, 0.001400],
    [1.026300, 0.757000, 0.001100],
    [1.056700, 0.694900, 0.001000],
    [1.062200, 0.631000, 0.000800],
    [1.045600, 0.566800, 0.000600],
    [1.002600, 0.503000, 0.000340],
    [0.938400, 0.441200, 0.000240],
    [0.854450, 0.381000, 0.000190],
    [0.751400, 0.321000, 0.000100],
    [0.642400, 0.265000, 0.000050],
    [0.541900, 0.217000, 0.000030],
    [0.447900, 0.175000, 0.000020],
    [0.360800, 0.138200, 0.000010],
    [0.283500, 0.107000, 0.000000],
    [0.218700, 0.081600, 0.000000],
    [0.164900, 0.061000, 0.000000],
    [0.121200, 0.044580, 0.000000],
    [0.087400, 0.032000, 0.000000],
    [0.063600, 0.023200, 0.000000],
    [0.046770, 0.017000, 0.000000],
    [0.032900, 0.011920, 0.000000],
    [0.022700, 0.008210, 0.000000],
    [0.015840, 0.005723, 0.000000],
    [0.011359, 0.004102, 0.000000],
    [0.008111, 0.002929, 0.000000],
    [0.005790, 0.002091, 0.000000],
    [0.004109, 0.001484, 0.000000],
    [0.002899, 0.001047, 0.000000],
    [0.002049, 0.000740, 0.000000],
    [0.001440, 0.000520, 0.000000],
    [0.001000, 0.000361, 0.000000],
    [0.000690, 0.000249, 0.000000],
    [0.000476, 0.000172, 0.000000],
    [0.000332, 0.000120, 0.000000],
    [0.000235, 0.000085, 0.000000],
    [0.000166, 0.000060, 0.000000],
    [0.000117, 0.000042, 0.000000],
    [0.000083, 0.000030, 0.000000],
    [0.000059, 0.000021, 0.000000],
    [0.000042, 0.000015, 0.000000],
])

X = cmf[:, 0]
Y = cmf[:, 1]
Z = cmf[:, 2]
denom = X + Y + Z
x_chrom = X / denom
y_chrom = Y / denom


# ---------------------------------------------------------------
# 2. XYZ -> sRGB 转换（用于给马蹄形上色）
# ---------------------------------------------------------------
def xyz_to_srgb(xyz):
    """xyz: shape (..., 3), 范围一般 0~1；返回 0~1 的 sRGB"""
    M = np.array([
        [ 3.2404542, -1.5371385, -0.4985314],
        [-0.9692660,  1.8760108,  0.0415560],
        [ 0.0556434, -0.2040259,  1.0572252],
    ])
    rgb_lin = xyz @ M.T
    # gamma 校正
    rgb_lin = np.clip(rgb_lin, 0, None)
    a = 0.055
    rgb = np.where(
        rgb_lin <= 0.0031308,
        12.92 * rgb_lin,
        (1 + a) * np.power(np.maximum(rgb_lin, 1e-12), 1 / 2.4) - a,
    )
    return np.clip(rgb, 0, 1)


def xy_to_rgb(x, y, Y_lum=1.0):
    """给定 xy 色度坐标 + 亮度 Y，返回 sRGB"""
    x = np.asarray(x)
    y = np.asarray(y)
    eps = 1e-12
    Xc = (x / np.maximum(y, eps)) * Y_lum
    Yc = np.full_like(Xc, Y_lum, dtype=float)
    Zc = ((1 - x - y) / np.maximum(y, eps)) * Y_lum
    xyz = np.stack([Xc, Yc, Zc], axis=-1)
    rgb = xyz_to_srgb(xyz)
    # 对色域外的点做最大值归一，保留色相
    mx = np.max(rgb, axis=-1, keepdims=True)
    mx = np.where(mx > 1, mx, 1)
    rgb = rgb / mx
    return rgb


# ---------------------------------------------------------------
# 3. 生成马蹄形内部网格（在 xy 平面内三角化）
# ---------------------------------------------------------------
# 马蹄形外轮廓（光谱轨迹 + 紫线）
boundary_x = np.concatenate([x_chrom, [x_chrom[0]]])
boundary_y = np.concatenate([y_chrom, [y_chrom[0]]])

# 在 xy 包围盒内撒规则网格点，再保留落在多边形内部的点
from matplotlib.path import Path as MplPath
poly_path = MplPath(np.column_stack([boundary_x, boundary_y]))

n_grid = 120
gx = np.linspace(0.0, 0.75, n_grid)
gy = np.linspace(0.0, 0.85, n_grid)
GX, GY = np.meshgrid(gx, gy)
pts = np.column_stack([GX.ravel(), GY.ravel()])
inside = poly_path.contains_points(pts)
inside_pts = pts[inside]

# 把边界点也加进来，让三角化覆盖整条光谱轨迹
all_pts = np.vstack([inside_pts, np.column_stack([x_chrom, y_chrom])])
tri = Triangulation(all_pts[:, 0], all_pts[:, 1])

# 用三角形重心是否在多边形内来过滤掉外面的三角形
centroids = np.column_stack([
    all_pts[tri.triangles, 0].mean(axis=1),
    all_pts[tri.triangles, 1].mean(axis=1),
])
mask = ~poly_path.contains_points(centroids)
tri.set_mask(mask)


# ---------------------------------------------------------------
# 4. 绘图：3D 马蹄形立体（xy 平面 + Y 高度）
# ---------------------------------------------------------------
fig = plt.figure(figsize=(11, 8))
ax = fig.add_subplot(111, projection='3d')

# --- 4.1 顶部彩色马蹄形（Y = 1） ---
Y_top = 1.0
verts_top = np.column_stack([
    all_pts[:, 0],
    all_pts[:, 1],
    np.full(all_pts.shape[0], Y_top),
])
face_colors_top = []
valid_tri_top = tri.triangles[~tri.mask] if tri.mask is not None else tri.triangles
for t in valid_tri_top:
    cx = all_pts[t, 0].mean()
    cy = all_pts[t, 1].mean()
    rgb = xy_to_rgb(np.array([cx]), np.array([cy]), Y_lum=1.0)[0]
    face_colors_top.append(rgb)

poly_top = Poly3DCollection(
    [verts_top[t] for t in valid_tri_top],
    facecolors=face_colors_top,
    edgecolors='none',
    linewidths=0,
)
ax.add_collection3d(poly_top)

# --- 4.2 底部黑色马蹄形（Y = 0），形成"立体马蹄"的底面 ---
Y_bot = 0.0
verts_bot = np.column_stack([
    all_pts[:, 0],
    all_pts[:, 1],
    np.full(all_pts.shape[0], Y_bot),
])
poly_bot = Poly3DCollection(
    [verts_bot[t] for t in valid_tri_top],
    facecolors=(0.05, 0.05, 0.05, 1.0),
    edgecolors='none',
)
ax.add_collection3d(poly_bot)

# --- 4.3 侧面：沿光谱轨迹做"立柱"墙面，从 Y=0 渐变到 Y=1 ---
n_layers = 14
Y_layers = np.linspace(0.0, 1.0, n_layers)

side_polys = []
side_colors = []
n_b = len(x_chrom)
for li in range(n_layers - 1):
    y0, y1 = Y_layers[li], Y_layers[li + 1]
    for i in range(n_b):
        j = (i + 1) % n_b
        p1 = (x_chrom[i], y_chrom[i], y0)
        p2 = (x_chrom[j], y_chrom[j], y0)
        p3 = (x_chrom[j], y_chrom[j], y1)
        p4 = (x_chrom[i], y_chrom[i], y1)
        side_polys.append([p1, p2, p3, p4])
        # 颜色：xy 处的色相 * 当前层亮度
        cx_mid = (x_chrom[i] + x_chrom[j]) / 2
        cy_mid = (y_chrom[i] + y_chrom[j]) / 2
        y_mid = (y0 + y1) / 2
        rgb = xy_to_rgb(np.array([cx_mid]), np.array([cy_mid]), Y_lum=1.0)[0]
        side_colors.append(rgb * y_mid + (1 - y_mid) * 0.05)

side_collection = Poly3DCollection(
    side_polys,
    facecolors=side_colors,
    edgecolors='none',
)
ax.add_collection3d(side_collection)

# --- 4.4 顶部光谱轨迹描边 ---
ax.plot(x_chrom, y_chrom, np.full_like(x_chrom, Y_top),
        color='black', lw=1.2, alpha=0.8)
ax.plot(x_chrom, y_chrom, np.full_like(x_chrom, Y_bot),
        color='black', lw=0.8, alpha=0.5)

# 紫线（连接光谱两端）
ax.plot([x_chrom[0], x_chrom[-1]], [y_chrom[0], y_chrom[-1]],
        [Y_top, Y_top], color='black', lw=1.0, alpha=0.7)

# --- 4.5 标注若干关键波长 ---
label_wls = [400, 460, 480, 500, 520, 540, 560, 580, 600, 620, 700]
for wl in label_wls:
    idx = np.argmin(np.abs(wavelengths - wl))
    ax.text(x_chrom[idx], y_chrom[idx], Y_top + 0.03,
            f'{wl}nm', fontsize=8, color='black', ha='center')

# --- 4.6 标注 D65 白点 ---
d65 = (0.3127, 0.3290)
ax.scatter([d65[0]], [d65[1]], [Y_top], color='white',
           edgecolors='black', s=60, zorder=5)
ax.text(d65[0] + 0.02, d65[1], Y_top + 0.05, 'D65', fontsize=9, color='black')

# ---------------------------------------------------------------
# 5. 坐标轴与视图设置
# ---------------------------------------------------------------
ax.set_xlabel('CIE x', fontsize=11, labelpad=8)
ax.set_ylabel('CIE y', fontsize=11, labelpad=8)
ax.set_zlabel('亮度 Y', fontsize=11, labelpad=8)
ax.set_title('CIE 1931 色度图 - 马蹄形立体可视化\n(按住鼠标左键拖动可旋转视角)',
             fontsize=13, pad=15)

ax.set_xlim(0, 0.8)
ax.set_ylim(0, 0.9)
ax.set_zlim(0, 1.1)

# 初始视角
ax.view_init(elev=25, azim=-60)

plt.tight_layout()
plt.show()
