# -*- coding: utf-8 -*-
"""
生成 §4.1 视图 1b 的 3D 示意图：单位旋转轴 n̂ 与底面有倾角（一般情形）。
在视图 1（轴沿 +z 竖直）的基础上，把轴换成倾斜方向，更直观地体现：
  · 旋转轴可以是空间中任意方向；
  · 端点扫出的圆所在平面始终 ⊥ n̂（不再与 xy 底面平行）；
  · 倾角 α 通过"轴 vs. 它在 xy 平面的投影"标注出来。
输出： d:/xTest/AI-doc/images/quaternion_axis_rotation_3d_tilted.png
"""

import os
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import proj3d


# ---------- 中文字体 ----------
def setup_chinese_font():
    candidates = [
        "Microsoft YaHei",
        "SimHei",
        "Microsoft JhengHei",
        "DengXian",
        "Source Han Sans CN",
        "Noto Sans CJK SC",
    ]
    from matplotlib import font_manager

    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False


setup_chinese_font()


# ---------- 3D 箭头 ----------
class Arrow3D(FancyArrowPatch):
    def __init__(self, xs, ys, zs, *args, **kwargs):
        super().__init__((0, 0), (0, 0), *args, **kwargs)
        self._verts3d = xs, ys, zs

    def do_3d_projection(self, renderer=None):
        xs3d, ys3d, zs3d = self._verts3d
        xs, ys, zs = proj3d.proj_transform(xs3d, ys3d, zs3d, self.axes.M)
        self.set_positions((xs[0], ys[0]), (xs[1], ys[1]))
        return np.min(zs)


def add_arrow(ax, start, end, color, lw=2.2, mutation_scale=18, label=None,
              ls="-", label_offset=(0.05, 0.05, 0.03)):
    a = Arrow3D(
        [start[0], end[0]],
        [start[1], end[1]],
        [start[2], end[2]],
        mutation_scale=mutation_scale,
        lw=lw,
        arrowstyle="-|>",
        color=color,
        linestyle=ls,
    )
    ax.add_artist(a)
    if label:
        ox, oy, oz = label_offset
        ax.text(end[0] + ox, end[1] + oy, end[2] + oz, label, color=color,
                fontsize=13, fontweight="bold")


def main():
    fig = plt.figure(figsize=(10.5, 8.8), dpi=150)
    ax = fig.add_subplot(111, projection="3d")

    # ---------- 旋转轴 n̂：明显倾斜（与 xy 平面成 ~50°） ----------
    # 用方向向量再归一化，避免输错
    n_raw = np.array([0.55, 0.30, 0.78])
    n_hat = n_raw / np.linalg.norm(n_raw)

    # 倾角 α = n̂ 与 xy 平面的夹角（= asin(n_z)）
    alpha = np.arcsin(n_hat[2])

    # ---------- 起始向量 p（与 n̂ 不共线，便于扫出明显的圆） ----------
    # 让 p 带明显 z 分量，同时偏中轴一侧，避免与 n̂ 投影重叠
    p = np.array([1.10, 0.55, -0.30])

    # 旋转角 θ
    theta = np.deg2rad(95)
    def rotate(v, n, t):
        n = n / np.linalg.norm(n)
        return (
            v * np.cos(t)
            + np.cross(n, v) * np.sin(t)
            + n * np.dot(n, v) * (1 - np.cos(t))
        )

    p_prime = rotate(p, n_hat, theta)

    # ---------- 1) 画一片 xy 底面参考网格（让"倾斜"显而易见） ----------
    grid_extent = 1.4
    gx = np.linspace(-grid_extent, grid_extent, 9)
    gy = np.linspace(-grid_extent, grid_extent, 9)
    GX, GY = np.meshgrid(gx, gy)
    GZ = np.zeros_like(GX)
    ax.plot_wireframe(GX, GY, GZ, color="#bbbbbb", lw=0.5, alpha=0.6)
    # 底面四角围出的浅色面，进一步强化"地板"感
    floor_pts = np.array([
        [-grid_extent, -grid_extent, 0],
        [ grid_extent, -grid_extent, 0],
        [ grid_extent,  grid_extent, 0],
        [-grid_extent,  grid_extent, 0],
    ])
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    floor = Poly3DCollection([floor_pts], alpha=0.06,
                             facecolor="#888888", edgecolor="none")
    ax.add_collection3d(floor)
    ax.text(grid_extent * 0.7, -grid_extent * 0.95, 0.02,
            "xy 底面（参考）", fontsize=10, color="#666666")

    # ---------- 2) 旋转轴 n̂（黑色长箭头，贯穿原点；含负向延长虚线） ----------
    axis_len_pos = 1.55
    axis_len_neg = 0.55
    add_arrow(ax,
              tuple(-axis_len_neg * n_hat),
              tuple(axis_len_pos * n_hat),
              color="black", lw=2.6, mutation_scale=20,
              label=r"$\hat{n}$  (单位旋转轴)")
    # 轴负向继续画一段虚线，强化"穿过原点的直线"
    far_neg = -1.0 * n_hat
    ax.plot(
        [-axis_len_neg * n_hat[0], far_neg[0]],
        [-axis_len_neg * n_hat[1], far_neg[1]],
        [-axis_len_neg * n_hat[2], far_neg[2]],
        color="black", ls=":", lw=1.2,
    )

    # ---------- 3) n̂ 在 xy 底面上的投影 + 倾角 α 标注 ----------
    n_proj = np.array([n_hat[0], n_hat[1], 0.0])
    n_proj_len = np.linalg.norm(n_proj)
    n_proj_unit = n_proj / n_proj_len
    # 画"轴端点 ↓ 投影到底面"的竖直虚线
    tip = axis_len_pos * n_hat
    ax.plot([tip[0], tip[0]], [tip[1], tip[1]], [tip[2], 0],
            color="#888888", ls="--", lw=1.0)
    # 画"原点 → 投影方向"在底面上的灰色实线（长度等于轴端点投影长度）
    proj_end = np.array([tip[0], tip[1], 0.0])
    ax.plot([0, proj_end[0]], [0, proj_end[1]], [0, 0],
            color="#888888", ls="-", lw=1.4)
    ax.text(proj_end[0] * 1.05, proj_end[1] * 1.05 + 0.05, 0.02,
            r"$\hat{n}$ 在 xy 上的投影", fontsize=10, color="#555555")

    # 画倾角 α 的圆弧（在 n̂ 与其投影方向所在的竖直平面内）
    # 该平面的两正交基：u_h = n_proj_unit (水平方向), e_z = (0,0,1)
    arc_phis = np.linspace(0, alpha, 50)
    arc_r_alpha = 0.45
    arc_pts_alpha = np.array([
        arc_r_alpha * (np.cos(ph) * n_proj_unit + np.sin(ph) * np.array([0, 0, 1]))
        for ph in arc_phis
    ])
    ax.plot(arc_pts_alpha[:, 0], arc_pts_alpha[:, 1], arc_pts_alpha[:, 2],
            color="#16a085", lw=2.4)
    # α 标签放在 α 弧外侧、靠
    mid_alpha = (
        arc_r_alpha * 1.85
        * (np.cos(alpha / 2) * n_proj_unit + np.sin(alpha / 2) * np.array([0, 0, 1]))
    )
    ax.text(mid_alpha[0], mid_alpha[1], mid_alpha[2],
            rf"$\alpha\approx{np.rad2deg(alpha):.0f}^\circ$",
            color="#16a085", fontsize=12, fontweight="bold")

    # ---------- 4) 端点扫出的圆 / 半透明圆盘（垂直 n̂ 的平面） ----------
    h = float(np.dot(p, n_hat))
    radial = p - h * n_hat
    r = float(np.linalg.norm(radial))

    u = radial / r
    v = np.cross(n_hat, u)
    phis = np.linspace(0, 2 * np.pi, 240)
    circle_pts = np.array([
        h * n_hat + r * (np.cos(ph) * u + np.sin(ph) * v) for ph in phis
    ])
    ax.plot(circle_pts[:, 0], circle_pts[:, 1], circle_pts[:, 2],
            color="#9b59b6", lw=1.8, ls="--")

    rho = np.linspace(0, r, 22)
    PHI, RHO = np.meshgrid(phis, rho)
    XX = h * n_hat[0] + RHO * (np.cos(PHI) * u[0] + np.sin(PHI) * v[0])
    YY = h * n_hat[1] + RHO * (np.cos(PHI) * u[1] + np.sin(PHI) * v[1])
    ZZ = h * n_hat[2] + RHO * (np.cos(PHI) * u[2] + np.sin(PHI) * v[2])
    ax.plot_surface(XX, YY, ZZ, color="#d6c4ea", alpha=0.22, linewidth=0)

    # ---------- 5) 圆心 + 半径辅助线 ----------
    center = h * n_hat
    ax.scatter(*center, color="#9b59b6", s=38, zorder=5)
    ax.plot([center[0], p[0]], [center[1], p[1]], [center[2], p[2]],
            color="#9b59b6", ls=":", lw=1.0)
    ax.plot([center[0], p_prime[0]], [center[1], p_prime[1]], [center[2], p_prime[2]],
            color="#9b59b6", ls=":", lw=1.0)

    # ---------- 6) θ 圆弧 ----------
    arc_phis = np.linspace(0, theta, 90)
    arc_r = r * 0.55
    arc_pts = np.array([
        center + arc_r * (np.cos(ph) * u + np.sin(ph) * v) for ph in arc_phis
    ])
    ax.plot(arc_pts[:, 0], arc_pts[:, 1], arc_pts[:, 2],
            color="#e67e22", lw=2.6)
    mid = center + arc_r * 1.35 * (np.cos(theta / 2) * u + np.sin(theta / 2) * v)
    ax.text(mid[0], mid[1], mid[2], r"$\theta$", color="#e67e22",
            fontsize=16, fontweight="bold")

    # ---------- 7) p / p' ----------
    add_arrow(ax, (0, 0, 0), p, color="#c0392b", lw=2.6,
              label=r"$\mathbf{p}$",
              label_offset=(0.06, -0.05, -0.02))
    add_arrow(ax, (0, 0, 0), p_prime, color="#2980b9", lw=2.6,
              label=r"$\mathbf{p}\,'$",
              label_offset=(-0.10, 0.06, 0.06))

    # ---------- 8) 原点 ----------
    ax.scatter(0, 0, 0, color="black", s=42, zorder=6)
    ax.text(0.04, 0.04, -0.18, "O (原点)", fontsize=11)

    # ---------- 9) 视图 / 范围 / 美化 ----------
    ax.set_xlim(-1.4, 1.4)
    ax.set_ylim(-1.4, 1.4)
    ax.set_zlim(-0.8, 1.6)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.view_init(elev=18, azim=-72)

    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_edgecolor("#cccccc")

    ax.set_title(
        r"一般情形：旋转轴 $\hat{n}$ 与底面有倾角 $\alpha$ —— "
        r"$\mathbf{p}\,\longrightarrow\,\mathbf{p}\,'$  (圆所在平面仍 $\perp\,\hat{n}$)",
        fontsize=13, fontweight="bold", pad=14,
    )

    # 图例
    from matplotlib.lines import Line2D
    legend_handles = [
        Line2D([0], [0], color="black", lw=2.6,
               label=r"旋转轴 $\hat{n}$（单位长度，方向任意）"),
        Line2D([0], [0], color="#888888", lw=1.4,
               label=r"$\hat{n}$ 在 xy 底面上的投影"),
        Line2D([0], [0], color="#16a085", lw=2.2,
               label=r"轴与底面的倾角 $\alpha$"),
        Line2D([0], [0], color="#c0392b", lw=2.6,
               label=r"原向量 $\mathbf{p}$"),
        Line2D([0], [0], color="#2980b9", lw=2.6,
               label=r"旋转后向量 $\mathbf{p}\,'$"),
        Line2D([0], [0], color="#9b59b6", lw=1.8, ls="--",
               label=r"端点扫出的圆（所在平面 $\perp\,\hat{n}$）"),
        Line2D([0], [0], color="#e67e22", lw=2.4,
               label=r"旋转角 $\theta$"),
    ]
    ax.legend(handles=legend_handles, loc="upper left",
              fontsize=9.5, framealpha=0.92,
              bbox_to_anchor=(0.0, 1.0))

    out_dir = r"d:\xTest\AI-doc\images"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "quaternion_axis_rotation_3d_tilted.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print(f"已生成：{out_path}")


if __name__ == "__main__":
    main()
