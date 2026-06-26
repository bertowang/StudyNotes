# -*- coding: utf-8 -*-
"""
生成 §4.1 视图1 的3D示意图：绕单位轴 n̂ 旋转角度 θ。
输出： d:/xTest/AI-doc/images/quaternion_axis_rotation_3d.png
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


def add_arrow(ax, start, end, color, lw=2.2, mutation_scale=18, label=None, ls="-"):
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
        ax.text(end[0] * 1.08, end[1] * 1.08, end[2] * 1.05, label, color=color,
                fontsize=13, fontweight="bold")


# ---------- 主图 ----------
def main():
    fig = plt.figure(figsize=(10, 8.5), dpi=150)
    ax = fig.add_subplot(111, projection="3d")

    # 旋转轴 n̂ 沿 +z
    n_hat = np.array([0, 0, 1.0])

    # 起始向量 p （与轴有夹角，以便能转出明显效果）
    p = np.array([1.0, 0.0, 0.6])

    # 旋转角 θ
    theta = np.deg2rad(75)

    # Rodrigues 旋转公式：v' = v cosθ + (n×v) sinθ + n (n·v)(1-cosθ)
    def rotate(v, n, t):
        n = n / np.linalg.norm(n)
        return (
            v * np.cos(t)
            + np.cross(n, v) * np.sin(t)
            + n * np.dot(n, v) * (1 - np.cos(t))
        )

    p_prime = rotate(p, n_hat, theta)

    # ---------- 1) 旋转轴 n̂（黑色长箭头，贯穿原点） ----------
    add_arrow(ax, (0, 0, -0.3), (0, 0, 1.5), color="black", lw=2.6,
              mutation_scale=20, label=r"$\hat{n}$  (单位旋转轴)")
    # 轴的延长虚线（向下）
    ax.plot([0, 0], [0, 0], [-0.8, -0.3], color="black", ls=":", lw=1.2)

    # ---------- 2) 端点扫出的圆（绕 n̂ 的圆盘） ----------
    # 端点高度 = p·n̂ ；圆半径 = |p - (p·n̂)n̂|
    h = float(np.dot(p, n_hat))
    radial = p - h * n_hat
    r = float(np.linalg.norm(radial))

    # 圆周
    phis = np.linspace(0, 2 * np.pi, 200)
    # 在垂直 n̂ 的平面里建两个正交基 (u, v)
    u = radial / r
    v = np.cross(n_hat, u)
    circle_pts = np.array([
        h * n_hat + r * (np.cos(ph) * u + np.sin(ph) * v) for ph in phis
    ])
    ax.plot(circle_pts[:, 0], circle_pts[:, 1], circle_pts[:, 2],
            color="#9b59b6", lw=1.6, ls="--")

    # 半透明圆盘（更直观地体现"垂直 n̂ 的平面"）
    rho = np.linspace(0, r, 20)
    PHI, RHO = np.meshgrid(phis, rho)
    XX = h * n_hat[0] + RHO * (np.cos(PHI) * u[0] + np.sin(PHI) * v[0])
    YY = h * n_hat[1] + RHO * (np.cos(PHI) * u[1] + np.sin(PHI) * v[1])
    ZZ = h * n_hat[2] + RHO * (np.cos(PHI) * u[2] + np.sin(PHI) * v[2])
    ax.plot_surface(XX, YY, ZZ, color="#d6c4ea", alpha=0.18, linewidth=0)

    # ---------- 3) 圆心从 n̂ 上画一个小点 + 中心到 p / p' 的细线（提示半径） ----------
    center = h * n_hat
    ax.scatter(*center, color="#9b59b6", s=35, zorder=5)
    ax.plot([center[0], p[0]], [center[1], p[1]], [center[2], p[2]],
            color="#9b59b6", ls=":", lw=1.0)
    ax.plot([center[0], p_prime[0]], [center[1], p_prime[1]], [center[2], p_prime[2]],
            color="#9b59b6", ls=":", lw=1.0)

    # ---------- 4) θ 圆弧标注 ----------
    arc_phis = np.linspace(0, theta, 60)
    arc_r = r * 0.45
    arc_pts = np.array([
        center + arc_r * (np.cos(ph) * u + np.sin(ph) * v) for ph in arc_phis
    ])
    ax.plot(arc_pts[:, 0], arc_pts[:, 1], arc_pts[:, 2],
            color="#e67e22", lw=2.2)
    # θ 文字位置（弧中点稍外）
    mid = center + arc_r * 1.25 * (np.cos(theta / 2) * u + np.sin(theta / 2) * v)
    ax.text(mid[0], mid[1], mid[2], "θ", color="#e67e22", fontsize=15,
            fontweight="bold")

    # ---------- 5) 起始/结束向量 p, p' ----------
    add_arrow(ax, (0, 0, 0), p, color="#c0392b", lw=2.6, label=r"$\mathbf{p}$")
    add_arrow(ax, (0, 0, 0), p_prime, color="#2980b9", lw=2.6, label=r"$\mathbf{p}\,'$")

    # ---------- 6) 原点 ----------
    ax.scatter(0, 0, 0, color="black", s=40, zorder=6)
    ax.text(0.05, 0.05, -0.12, "O (原点)", fontsize=11)

    # ---------- 7) 视图 / 范围 / 美化 ----------
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.3, 1.3)
    ax.set_zlim(-0.8, 1.6)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.view_init(elev=22, azim=35)

    # 关掉网格背景色板，让图更"干净"
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_edgecolor("#cccccc")

    ax.set_title(r"绕单位轴 $\hat{n}$ 旋转角度 $\theta$：$\mathbf{p}\,\longrightarrow\,\mathbf{p}\,'$  (端点沿圆周移动)",
                 fontsize=14, fontweight="bold", pad=14)

    # 图例（手工组装）
    from matplotlib.lines import Line2D
    legend_handles = [
        Line2D([0], [0], color="black", lw=2.6,
               label=r"旋转轴 $\hat{n}$（单位长度）"),
        Line2D([0], [0], color="#c0392b", lw=2.6,
               label=r"原向量 $\mathbf{p}$"),
        Line2D([0], [0], color="#2980b9", lw=2.6,
               label=r"旋转后向量 $\mathbf{p}\,'$"),
        Line2D([0], [0], color="#9b59b6", lw=1.6, ls="--",
               label=r"端点扫出的圆（所在平面 $\perp\,\hat{n}$）"),
        Line2D([0], [0], color="#e67e22", lw=2.2,
               label=r"旋转角 $\theta$"),
    ]
    ax.legend(handles=legend_handles, loc="upper left",
              fontsize=10, framealpha=0.9)

    out_dir = r"d:\xTest\AI-doc\images"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "quaternion_axis_rotation_3d.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print(f"已生成：{out_path}")


if __name__ == "__main__":
    main()
