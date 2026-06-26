# -*- coding: utf-8 -*-
"""
生成 §4.1 视图2 的俯视示意图：从 n̂ 的"箭头方向"往下看，圆周变成一个 2D 圆。
输出： d:/xTest/AI-doc/images/quaternion_axis_rotation_top.png
"""

import os
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Arc


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


def add_arrow(ax, start, end, color, lw=2.4, mutation_scale=20, ls="-"):
    arr = FancyArrowPatch(
        start, end,
        arrowstyle="-|>",
        mutation_scale=mutation_scale,
        color=color,
        lw=lw,
        linestyle=ls,
        zorder=5,
    )
    ax.add_patch(arr)


def main():
    fig, ax = plt.subplots(figsize=(9, 9), dpi=150)

    R = 1.0   # 圆半径
    cx, cy = 0.0, 0.0
    theta = np.deg2rad(75)  # 与视图1保持一致

    # ---------- 1) 大圆（端点扫出的圆） ----------
    big_circle = Circle((cx, cy), R, fill=True,
                        facecolor="#f3ebfa", edgecolor="#9b59b6",
                        lw=1.8, ls="--", zorder=1)
    ax.add_patch(big_circle)

    # ---------- 2) 圆心标注 n̂（轴垂直于纸面、指向读者：⊙ 符号） ----------
    # 外圈
    ax.add_patch(Circle((cx, cy), 0.05, fill=False,
                        edgecolor="black", lw=2.2, zorder=6))
    # 中心点
    ax.add_patch(Circle((cx, cy), 0.012, color="black", zorder=7))
    ax.annotate(
        r"$\hat{n}$  (轴 $\perp$ 纸面，指向读者)",
        xy=(cx, cy - 0.06),
        xytext=(cx + 0.45, cy - 0.42),
        fontsize=12, fontweight="bold", color="black",
        arrowprops=dict(arrowstyle="-", color="black", lw=0.8),
    )

    # ---------- 3) p（起点在圆周上，朝右） ----------
    p_angle = 0.0  # p 沿 +x 方向
    p_end = (cx + R * np.cos(p_angle), cy + R * np.sin(p_angle))
    add_arrow(ax, (cx, cy), p_end, color="#c0392b", lw=2.6)
    ax.text(p_end[0] + 0.06, p_end[1] - 0.02,
            r"$\mathbf{p}$", color="#c0392b",
            fontsize=16, fontweight="bold")

    # ---------- 4) p'（绕轴逆时针转 θ） ----------
    pp_angle = p_angle + theta
    pp_end = (cx + R * np.cos(pp_angle), cy + R * np.sin(pp_angle))
    add_arrow(ax, (cx, cy), pp_end, color="#2980b9", lw=2.6)
    ax.text(pp_end[0] - 0.04, pp_end[1] + 0.07,
            r"$\mathbf{p}\,'$", color="#2980b9",
            fontsize=16, fontweight="bold")

    # ---------- 5) θ 圆弧（橙色） ----------
    arc_r = 0.32
    arc = Arc((cx, cy), 2 * arc_r, 2 * arc_r,
              angle=0,
              theta1=np.rad2deg(p_angle),
              theta2=np.rad2deg(pp_angle),
              color="#e67e22", lw=2.6, zorder=4)
    ax.add_patch(arc)
    # 在弧的中点处加一个小箭头，体现"逆时针方向"
    arc_tip_angle = pp_angle - 0.02
    tip = (cx + arc_r * np.cos(arc_tip_angle),
           cy + arc_r * np.sin(arc_tip_angle))
    tan = (-np.sin(arc_tip_angle), np.cos(arc_tip_angle))
    tip_end = (tip[0] + tan[0] * 0.001, tip[1] + tan[1] * 0.001)
    add_arrow(ax, tip, tip_end, color="#e67e22", lw=2.6, mutation_scale=18)
    # θ 文字（弧中点稍外）
    mid_a = (p_angle + pp_angle) / 2
    label_r = arc_r + 0.13
    ax.text(cx + label_r * np.cos(mid_a),
            cy + label_r * np.sin(mid_a),
            r"$\theta$", color="#e67e22",
            fontsize=18, fontweight="bold",
            ha="center", va="center")

    # ---------- 6) 端点扫出的圆周（再加一段动感箭头：逆时针正方向） ----------
    sweep_r = R * 1.08
    sweep = Arc((cx, cy), 2 * sweep_r, 2 * sweep_r,
                angle=0, theta1=200, theta2=340,
                color="#9b59b6", lw=1.4, ls=":")
    ax.add_patch(sweep)
    # 在末端加一个小箭头表示方向（逆时针 = 角度递增方向）
    a0 = np.deg2rad(338)
    a1 = np.deg2rad(340)
    add_arrow(ax,
              (cx + sweep_r * np.cos(a0), cy + sweep_r * np.sin(a0)),
              (cx + sweep_r * np.cos(a1), cy + sweep_r * np.sin(a1)),
              color="#9b59b6", lw=1.6, mutation_scale=14)
    ax.text(cx + sweep_r * np.cos(np.deg2rad(270)) - 0.1,
            cy + sweep_r * np.sin(np.deg2rad(270)) - 0.15,
            "端点沿圆周移动\n（逆时针为正方向，右手定则）",
            fontsize=11, color="#7d3c98", ha="center", va="top")

    # ---------- 7) 半径辅助线（圆心 → p 端 / 圆心 → p' 端 已经被箭头表示了，这里加圆周上的小点） ----------
    ax.add_patch(Circle(p_end, 0.025, color="#c0392b", zorder=6))
    ax.add_patch(Circle(pp_end, 0.025, color="#2980b9", zorder=6))

    # ---------- 8) 标题 / 范围 / 美化 ----------
    ax.set_title(
        r"视图 2：从 $\hat{n}$ 的上方俯视  ——  $\mathbf{p}\,\longrightarrow\,\mathbf{p}\,'$  (端点在 2D 圆上转 $\theta$)",
        fontsize=13, fontweight="bold", pad=14,
    )

    ax.set_xlim(-1.6, 1.7)
    ax.set_ylim(-1.7, 1.6)
    ax.set_aspect("equal")
    ax.axis("off")  # 俯视图不需要坐标轴

    # ---------- 9) 图例 ----------
    from matplotlib.lines import Line2D
    legend_handles = [
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor="white", markeredgecolor="black",
               markersize=12, lw=0,
               label=r"$\hat{n}$（轴垂直纸面、指向读者，⊙ 符号）"),
        Line2D([0], [0], color="#c0392b", lw=2.6,
               label=r"原向量 $\mathbf{p}$"),
        Line2D([0], [0], color="#2980b9", lw=2.6,
               label=r"旋转后向量 $\mathbf{p}\,'$"),
        Line2D([0], [0], color="#9b59b6", lw=1.8, ls="--",
               label=r"端点扫出的圆（直径 = $2|\mathbf{p}_\perp|$）"),
        Line2D([0], [0], color="#e67e22", lw=2.6,
               label=r"旋转角 $\theta$（逆时针为正）"),
    ]
    ax.legend(handles=legend_handles, loc="upper left",
              fontsize=10, framealpha=0.92,
              bbox_to_anchor=(0.0, 1.0))

    # ---------- 10) 右手定则提示 ----------
    ax.text(
        1.55, -1.55,
        "右手定则：\n  大拇指指向 $\\hat{n}$\n  四指弯曲方向 = $\\theta>0$ 的旋转方向",
        fontsize=10, color="#555555",
        ha="right", va="bottom",
        bbox=dict(boxstyle="round,pad=0.5",
                  facecolor="#fffbe6", edgecolor="#f0c36d", lw=1),
    )

    out_dir = r"d:\xTest\AI-doc\images"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "quaternion_axis_rotation_top.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print(f"已生成：{out_path}")


if __name__ == "__main__":
    main()
