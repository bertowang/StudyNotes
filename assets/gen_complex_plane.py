"""生成复平面矢量图（电容补偿）"""
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

matplotlib.rcParams['font.sans-serif'] = ['Heiti SC', 'PingFang SC', 'STHeiti']
matplotlib.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(figsize=(9, 7))
ax.axhline(0, color='gray', linewidth=0.8)
ax.axvline(0, color='gray', linewidth=0.8)
ax.set_xlim(-4.5, 4.5)
ax.set_ylim(-3.5, 3.5)
ax.set_aspect('equal')
ax.grid(True, alpha=0.3)
ax.set_xlabel('实部 (Re)')
ax.set_ylabel('虚部 (Im)')

R_vec = [3, 0]
XL_vec = [0, 2.5]
XC_vec = [0, -2.5]

ax.quiver(0, 0, *R_vec, color='blue', width=0.015, label='R (实部)',
          angles='xy', scale_units='xy', scale=1)
ax.quiver(0, 0, *XL_vec, color='green', width=0.015, label='+jωL (感性)',
          angles='xy', scale_units='xy', scale=1)
ax.quiver(0, 0, *XC_vec, color='red', width=0.015, label='-j/ωC (容性)',
          angles='xy', scale_units='xy', scale=1)

Z_old = [3, 2.5]
ax.quiver(0, 0, *Z_old, color='purple', width=0.025, linestyle='--',
          label='补偿前 Z=R+jX_L', angles='xy', scale_units='xy', scale=1)

Z_new = [3, 0]
ax.quiver(0, 0, *Z_new, color='orange', width=0.025,
          label='补偿后 Z=R', angles='xy', scale_units='xy', scale=1)

ax.legend(loc='upper right')
ax.set_title('复平面矢量图：电容补偿无功功率')

# 标注
ax.annotate('R', xy=(1.5, 0.2), fontsize=12, color='blue')
ax.annotate('jX_L', xy=(0.1, 1.3), fontsize=12, color='green')
ax.annotate('-jX_C', xy=(0.1, -1.5), fontsize=12, color='red')
ax.annotate('补偿前', xy=(2.5, 2.0), fontsize=11, color='purple')
ax.annotate('补偿后', xy=(2.0, -0.5), fontsize=11, color='orange')

plt.tight_layout()
plt.savefig('assets/complex_plane.png', dpi=150, bbox_inches='tight')
plt.close()
print('complex_plane.png 已生成')
