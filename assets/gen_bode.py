"""生成 RC 低通/高通波特图"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.sans-serif'] = ['Heiti SC', 'PingFang SC', 'STHeiti']
matplotlib.rcParams['axes.unicode_minus'] = False

f = np.logspace(-2, 2, 500)
f_3db = 1

# 低通
mag_LP = 1 / np.sqrt(1 + (f / f_3db) ** 2)
phase_LP = -np.arctan(f / f_3db) * 180 / np.pi

# 高通
mag_HP = (f / f_3db) / np.sqrt(1 + (f / f_3db) ** 2)
phase_HP = 90 - np.arctan(f / f_3db) * 180 / np.pi

fig, axes = plt.subplots(2, 2, figsize=(12, 10), sharex='col')

# 低通 - 幅频
ax = axes[0, 0]
ax.semilogx(f, 20 * np.log10(mag_LP), 'b', linewidth=1.5)
ax.axvline(f_3db, color='gray', ls=':', label=f'$f_c$ (归一化=1)')
ax.axhline(-3, color='red', ls='--', alpha=0.5, label='-3 dB')
ax.set_ylabel('增益 (dB)')
ax.set_title('RC 低通滤波器 — 幅频响应')
ax.grid(True, alpha=0.3)
ax.legend(fontsize=9)

# 低通 - 相频
ax = axes[1, 0]
ax.semilogx(f, phase_LP, 'b', linewidth=1.5)
ax.axvline(f_3db, color='gray', ls=':')
ax.axhline(-45, color='red', ls='--', alpha=0.5, label='-45°')
ax.set_ylabel('相位 (度)')
ax.set_xlabel('归一化频率 f / f_c')
ax.set_title('RC 低通滤波器 — 相频响应')
ax.grid(True, alpha=0.3)
ax.legend(fontsize=9)

# 高通 - 幅频
ax = axes[0, 1]
ax.semilogx(f, 20 * np.log10(mag_HP), 'r', linewidth=1.5)
ax.axvline(f_3db, color='gray', ls=':', label=f'$f_c$ (归一化=1)')
ax.axhline(-3, color='red', ls='--', alpha=0.5, label='-3 dB')
ax.set_ylabel('增益 (dB)')
ax.set_title('RC 高通滤波器 — 幅频响应')
ax.grid(True, alpha=0.3)
ax.legend(fontsize=9)

# 高通 - 相频
ax = axes[1, 1]
ax.semilogx(f, phase_HP, 'r', linewidth=1.5)
ax.axvline(f_3db, color='gray', ls=':')
ax.axhline(45, color='red', ls='--', alpha=0.5, label='+45°')
ax.set_ylabel('相位 (度)')
ax.set_xlabel('归一化频率 f / f_c')
ax.set_title('RC 高通滤波器 — 相频响应')
ax.grid(True, alpha=0.3)
ax.legend(fontsize=9)

plt.tight_layout()
plt.savefig('assets/bode_plot.png', dpi=150, bbox_inches='tight')
plt.close()
print('bode_plot.png 已生成')
