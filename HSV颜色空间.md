---
tags:
  - computer-vision
  - image-processing
  - color-space
  - opencv
aliases:
  - HSV色彩空间
  - Hue Saturation Value
created: 2026-06-20
updated: 2026-06-20
---

# HSV 颜色空间

---

## 一、概述

**HSV**（Hue, Saturation, Value）是一种基于人类颜色感知的颜色空间模型，将颜色信息分解为三个直观的维度，比 RGB 更接近人对颜色的主观描述。

广泛应用于计算机视觉、图像处理和图形设计。

---

## 二、三个分量

### 2.1 色相（Hue, H）

表示颜色的基本属性（如红、绿、蓝等），取值范围通常为 **0°～360°**（环形角度）。

| 角度 | 颜色 |
|:---|:---|
| 0° | 红色 |
| 60° | 黄色 |
| 120° | 绿色 |
| 180° | 青色 |
| 240° | 蓝色 |
| 300° | 品红 |

### 2.2 饱和度（Saturation, S）

表示颜色的**鲜艳程度**，范围 0%～100%：
- 0%：灰色（完全没有色彩）
- 100%：纯色（最鲜艳）

低饱和度的颜色接近白色或灰色。

### 2.3 明度（Value, V）

表示颜色的**亮度**，范围 0%～100%：
- 0%：纯黑
- 100%：最亮颜色

与 RGB 中的亮度不同，HSV 的明度是颜色的整体明暗程度。

---

## 三、HSV vs RGB

| 维度 | HSV | RGB |
|:---|:---|:---|
| **直观性** | 贴近人类描述（如"深蓝色"对应调整 H、S、V） | 基于红绿蓝通道混合，不直观 |
| **色彩独立性** | 色相/饱和度与亮度分离，可独立调整 | 三通道互相耦合 |
| **图像分割** | 可直接按颜色阈值提取对象 | 需要复杂组合条件 |
| **数学计算** | 非线性，不适合直接混合计算 | 线性空间，适合数学运算 |

---

## 四、OpenCV 代码示例

```python
import cv2
import numpy as np

# 读取图像（BGR 格式）
image_bgr = cv2.imread("image.jpg")

# 转换为 HSV
image_hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

# 定义红色范围（红色在 HSV 中跨越 0° 边界，需两段）
lower_red1 = np.array([0, 50, 50])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([160, 50, 50])
upper_red2 = np.array([180, 255, 255])

mask1 = cv2.inRange(image_hsv, lower_red1, upper_red1)
mask2 = cv2.inRange(image_hsv, lower_red2, upper_red2)
mask = cv2.bitwise_or(mask1, mask2)

# 显示结果
cv2.imshow("Original", image_bgr)
cv2.imshow("Mask", mask)
cv2.waitKey(0)
cv2.destroyAllWindows()
```

> [!note] OpenCV 中的 HSV 范围
> OpenCV 的 HSV 范围为 H: 0~180, S: 0~255, V: 0~255（H 做了缩半处理，实际角度除以 2）。

---

## 五、典型应用

| 应用 | 说明 |
|:---|:---|
| **颜色检测** | 根据 H 值阈值提取特定颜色物体（如红色交通标志） |
| **图像分割** | 按颜色区域分离前景与背景 |
| **颜色过滤** | 滤除或保留特定色调，用于预处理 |
| **UI 调色板** | 在图形设计工具中按 HSV 维度调节颜色 |

---

## 六、局限性

| 局限 | 说明 |
|:---|:---|
| **对光照敏感** | V 变化会影响 S 的表现，强光下颜色失真 |
| **非线性** | 不适合直接用于颜色混合等需要线性空间的操作 |
| **H 在低 S 下不稳定** | 当饱和度极低（接近灰色）时，色相无意义 |

---

## 七、相关色彩空间

| 空间 | 特点 | 用途 |
|:---|:---|:---|
| **HSL** | 用 Lightness 代替 Value，明度定义不同 | 设计软件（Photoshop 等） |
| **HSB** | 与 HSV 基本相同，名称不同 | 部分图形工具 |
| **YUV/YCbCr** | 亮度与色度分离，更高效 | 视频压缩、传输 |
| **Lab** | 感知均匀，色差计算 | 高精度颜色比较 |

---

## 八、何时使用 HSV

```
需要按颜色分割图像           → HSV（直观设阈值）
需要检测特定颜色物体         → HSV（H 通道直接过滤）
需要调整图像的亮度/饱和度     → HSV（V/S 独立可调）
需要做颜色混合/数学计算       → RGB/Lab
需要视频传输/压缩             → YUV
```

> [!tip] 实践建议
> 在 OpenCV 中进行颜色检测时，先转换到 HSV，再用 `cv2.inRange()` 设置阈值范围，比直接在 BGR 空间操作更稳定、更直观。
