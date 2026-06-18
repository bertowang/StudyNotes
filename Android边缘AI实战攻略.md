# Android 边缘AI 实战攻略

> **作者**：汪亮 bertonwang  
> **邮箱**：47608843@qq.com  
> **日期**：2026年6月
> **版本**：V1.0


---

> 目标：在 Android 手机（如 Pixel 8 / 小米14 / 三星 Galaxy S24）上，跑通一个边缘AI Demo（实时物体检测）
> 难度：零基础可完成 | 预计耗时：2~4 小时

---

## 目录

- [一、你的Android手机能跑什么AI？](#一你的android手机能跑什么ai)
- [二、准备工作清单](#二准备工作清单)
- [三、方案选择](#三方案选择)
- [四、方案A：TensorFlow Lite + CameraX（推荐，最简单）](#四方案atensorflow-lite--camerax推荐最简单)
- [五、方案B：ONNX Runtime 部署](#五方案bonnx-runtime-部署)
- [六、方案C：YOLOv8 部署到 Android](#六方案cyolov8-部署到-android)
- [七、模型转换详解](#七模型转换详解)
- [八、性能实测与优化](#八性能实测与优化)
- [九、常见问题排查](#九常见问题排查)
- [十、Android AI 相关框架全景图](#十android-ai-相关框架全景图)
- [十一、进阶玩法](#十一进阶玩法)

---

## 一、你的Android手机能跑什么AI？

### 1.1 硬件对比

| 参数 | Pixel 8 | 小米14 | 三星 Galaxy S24 |
|------|---------|--------|-----------------|
| 芯片 | Tensor G3 | 骁龙8 Gen3 | Exynos 2400 / 骁龙8 Gen3 |
| NPU | Google TPU (10 TOPS) | Hexagon NPU (45 TOPS) | NPU (拟 38 TOPS) |
| GPU | Mali-G715 | Adreno 750 | Xclipse 940 / Adreno 750 |
| RAM | 8GB | 12GB | 8GB / 12GB |
| 支持精度 | FP16 / INT8 | FP16 / INT8 / INT4 | FP16 / INT8 |

> **NPU（神经网络处理器）** = Android 手机里专门跑 AI 的硬件模块，类似独立显卡之于游戏。
> 不同厂商叫法不同：高通叫 Hexagon，联发科叫 APU，Google 叫 TPU，三星叫 NPU。

### 1.2 能跑什么模型？

| 模型类型 | 示例 | 骁龙8 Gen3 | Tensor G3 | 模型大小 |
|----------|------|-----------|-----------|----------|
| 图像分类 | MobileNetV3 | ✅ ~2ms | ✅ ~3ms | 8MB |
| 物体检测 | YOLOv8n | ✅ ~12ms | ✅ ~18ms | 12MB |
| 图像分割 | DeepLabV3 | ✅ ~25ms | ✅ ~35ms | 75MB |
| 姿态估计 | MoveNet | ✅ ~15ms | ✅ ~22ms | 9MB |
| 文字识别 | CRNN | ✅ ~8ms | ✅ ~12ms | 15MB |
| 大语言模型 | Gemma 2B (4bit) | ✅ ~15 tok/s | ✅ ~12 tok/s | 1.5GB |

### 1.3 Android 的 AI 技术栈

```
你的 App
    │
    ▼
┌─────────────────────────────────────┐
│         高层 API（最简单）            │
│  ML Kit / MediaPipe                  │
│  （Google 内置模型，几行代码调用）     │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│         推理引擎（核心）              │
│  TensorFlow Lite / ONNX Runtime      │
│  加载 .tflite/.onnx 模型文件         │
│  支持 GPU/NPU/CPU 加速               │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│      硬件加速层（Delegate 机制）      │
│  NPU (NNAPI) │ GPU │ CPU            │
└─────────────────────────────────────┘
```

---

## 二、准备工作清单

### 2.1 必备条件

| 序号 | 项目 | 说明 | 如何获取 |
|------|------|------|----------|
| 1 | 电脑 | Windows / Mac / Linux 均可 | 任意电脑 |
| 2 | Android Studio | Google 官方开发工具 | 官网免费下载 |
| 3 | Android 手机 | 系统 Android 8.0+ | 推荐 Android 12+ |
| 4 | USB 数据线 | 连接电脑和手机 | 原装线即可 |
| 5 | Python 3.8+ | 模型转换需要（方案C） | python.org 下载 |

### 2.2 软件安装步骤

```
步骤1：安装 Android Studio
━━━━━━━━━━━━━━━━━━━━━━━━━━
下载地址：https://developer.android.com/studio
安装后首次启动会自动下载 SDK（约 3~5GB）

步骤2：安装 SDK 和 NDK
━━━━━━━━━━━━━━━━━━━━━━
打开 Android Studio → Settings → Languages & Frameworks → Android SDK
  - SDK Platforms：勾选 Android 13 (API 33) 或更高
  - SDK Tools：勾选 NDK、CMake

步骤3：安装 Python 环境（方案C需要）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  pip install tensorflow tflite-model-maker
  pip install ultralytics onnx onnxruntime

步骤4：配置 Gradle 镜像（国内用户加速）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
在项目的 settings.gradle 中添加阿里云镜像：
  maven { url 'https://maven.aliyun.com/repository/google' }
  maven { url 'https://maven.aliyun.com/repository/central' }
```

### 2.3 Android 手机开启开发者模式

```
操作步骤（通用）：
1. 设置 → 关于手机 → 连续点击"版本号" 7 次
2. 返回设置 → 系统 → 开发者选项 → 打开
3. 开启 "USB 调试"
4. 用 USB 线连接电脑，手机弹出授权框 → 点击"允许"

不同品牌的差异：
- 小米：设置 → 我的设备 → 全部参数 → 点击 MIUI 版本 7 次
- 华为：设置 → 关于手机 → 点击版本号 7 次
- 三星：设置 → 关于手机 → 软件信息 → 点击编译编号 7 次
- OPPO/vivo：设置 → 关于手机 → 点击版本号 7 次
```

---

## 三、方案选择

| 方案 | 难度 | 耗时 | 适合谁 | 效果 |
|------|------|------|--------|------|
| **A：TFLite + CameraX** | ⭐ | 30分钟 | 纯小白，第一次接触 | 实时物体检测 |
| **B：ONNX Runtime** | ⭐⭐ | 1.5小时 | 想用跨平台方案 | 灵活部署 |
| **C：YOLOv8 部署** | ⭐⭐⭐ | 3小时 | 有一点编程基础 | 高性能检测 |

> 💡 **建议**：先跑方案A感受一下，再尝试方案C获得最佳性能。

---

## 四、方案A：TensorFlow Lite + CameraX（推荐，最简单）

### 4.1 原理说明

```
这个方案做什么：
  打开摄像头 → 每一帧送入AI模型 → 画出检测框 → 实时显示

用到的技术：
  - CameraX：Google 的摄像头 API（简化版）
  - TensorFlow Lite：轻量级推理引擎
  - NNAPI Delegate：调用 NPU 硬件加速
```

### 4.2 下载预训练模型

```
方式1：从 TensorFlow Hub 下载
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
访问：https://tfhub.dev/
搜索 "object detection" → 选择 "TFLite" 格式
推荐下载：ssd_mobilenet_v2（轻量、速度快）

方式2：从 Kaggle Models 下载
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
访问：https://www.kaggle.com/models
搜索 "tflite object detection"

方式3：使用 Google 的 MediaPipe 模型
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
访问：https://developers.google.com/mediapipe/solutions/vision/object_detector#models
下载 EfficientDet-Lite0（推荐入门）
```

### 4.3 创建 Android Studio 项目

```
操作步骤：
1. 打开 Android Studio
2. File → New → New Project
3. 选择 "Empty Views Activity" → Next
4. 填写信息：
   - Name: EdgeAIDemo
   - Package name: com.example.edgeaidemo
   - Language: Kotlin
   - Minimum SDK: API 24 (Android 7.0)
5. 点击 Finish
```

### 4.4 添加依赖

在 `app/build.gradle` 中添加：

```groovy
dependencies {
    // TensorFlow Lite 核心库
    implementation 'org.tensorflow:tensorflow-lite:2.14.0'
    // GPU 加速
    implementation 'org.tensorflow:tensorflow-lite-gpu:2.14.0'
    // NNAPI 加速（调用 NPU）
    implementation 'org.tensorflow:tensorflow-lite-support:0.4.4'
    // 图像处理辅助
    implementation 'org.tensorflow:tensorflow-lite-task-vision:0.4.4'

    // CameraX（摄像头）
    def camerax_version = "1.3.1"
    implementation "androidx.camera:camera-core:$camerax_version"
    implementation "androidx.camera:camera-camera2:$camerax_version"
    implementation "androidx.camera:camera-lifecycle:$camerax_version"
    implementation "androidx.camera:camera-view:$camerax_version"
}

android {
    // 防止模型文件被压缩
    aaptOptions {
        noCompress "tflite"
    }
}
```

### 4.5 添加模型文件

```
操作步骤：
1. 在 app/src/main/ 目录下创建 assets 文件夹
2. 将下载的 .tflite 模型文件放入 assets 文件夹
3. 如果有标签文件（labels.txt），也放入 assets

目录结构：
app/
└── src/
    └── main/
        ├── assets/
        │   ├── detect.tflite        ← 模型文件
        │   └── labels.txt           ← 类别标签
        ├── java/
        └── res/
```

### 4.6 添加权限

在 `AndroidManifest.xml` 中添加：

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <!-- 摄像头权限 -->
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-feature android:name="android.hardware.camera" android:required="true" />
    
    <application ...>
        ...
    </application>
</manifest>
```

### 4.7 编写代码

#### 布局文件 `activity_main.xml`：

```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <!-- 摄像头预览 -->
    <androidx.camera.view.PreviewView
        android:id="@+id/previewView"
        android:layout_width="match_parent"
        android:layout_height="match_parent" />

    <!-- 检测框绘制层 -->
    <com.example.edgeaidemo.OverlayView
        android:id="@+id/overlayView"
        android:layout_width="match_parent"
        android:layout_height="match_parent" />

    <!-- 底部信息栏 -->
    <TextView
        android:id="@+id/tvInfo"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:background="#80000000"
        android:textColor="#00FF00"
        android:padding="8dp"
        android:text="FPS: 0 | 检测到 0 个物体"
        app:layout_constraintBottom_toBottomOf="parent" />

</androidx.constraintlayout.widget.ConstraintLayout>
```

#### 核心检测器 `ObjectDetectorHelper.kt`：

```kotlin
package com.example.edgeaidemo

import android.content.Context
import android.graphics.Bitmap
import org.tensorflow.lite.support.image.ImageProcessor
import org.tensorflow.lite.support.image.TensorImage
import org.tensorflow.lite.support.image.ops.ResizeOp
import org.tensorflow.lite.task.vision.detector.ObjectDetector

/**
 * TFLite 物体检测封装类
 */
class ObjectDetectorHelper(
    private val context: Context,
    private val modelName: String = "detect.tflite",
    private val maxResults: Int = 5,
    private val scoreThreshold: Float = 0.5f
) {
    private var detector: ObjectDetector? = null

    init {
        setupDetector()
    }

    private fun setupDetector() {
        val options = ObjectDetector.ObjectDetectorOptions.builder()
            .setMaxResults(maxResults)
            .setScoreThreshold(scoreThreshold)
            .setNumThreads(4)  // CPU 线程数
            .build()

        detector = ObjectDetector.createFromFileAndOptions(
            context,
            modelName,
            options
        )
    }

    /**
     * 对一帧图像执行检测
     */
    fun detect(bitmap: Bitmap): List<DetectionResult> {
        val tensorImage = TensorImage.fromBitmap(bitmap)
        val results = detector?.detect(tensorImage) ?: return emptyList()

        return results.map { detection ->
            DetectionResult(
                label = detection.categories.firstOrNull()?.label ?: "未知",
                confidence = detection.categories.firstOrNull()?.score ?: 0f,
                boundingBox = detection.boundingBox
            )
        }
    }

    fun close() {
        detector?.close()
    }
}

/**
 * 检测结果数据类
 */
data class DetectionResult(
    val label: String,
    val confidence: Float,
    val boundingBox: android.graphics.RectF
)
```

#### 主 Activity `MainActivity.kt`：

```kotlin
package com.example.edgeaidemo

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {

    private lateinit var previewView: PreviewView
    private lateinit var overlayView: OverlayView
    private lateinit var cameraExecutor: ExecutorService
    private lateinit var detector: ObjectDetectorHelper

    private var frameCount = 0
    private var lastFpsTime = System.currentTimeMillis()
    private var currentFps = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        previewView = findViewById(R.id.previewView)
        overlayView = findViewById(R.id.overlayView)

        // 初始化检测器
        detector = ObjectDetectorHelper(this)

        // 初始化相机线程
        cameraExecutor = Executors.newSingleThreadExecutor()

        // 请求摄像头权限
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), 100)
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            // 预览
            val preview = Preview.Builder()
                .setTargetResolution(android.util.Size(1280, 720))
                .build()
                .also { it.setSurfaceProvider(previewView.surfaceProvider) }

            // 图像分析（每一帧送入AI）
            val imageAnalyzer = ImageAnalysis.Builder()
                .setTargetResolution(android.util.Size(640, 480))
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST) // 丢弃来不及处理的帧
                .build()
                .also { analysis ->
                    analysis.setAnalyzer(cameraExecutor) { imageProxy ->
                        processImage(imageProxy)
                    }
                }

            // 绑定到生命周期
            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
            cameraProvider.unbindAll()
            cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageAnalyzer)

        }, ContextCompat.getMainExecutor(this))
    }

    private fun processImage(imageProxy: ImageProxy) {
        val bitmap = imageProxy.toBitmap()  // 需要扩展函数，见下方

        // 执行AI推理
        val startTime = System.currentTimeMillis()
        val results = detector.detect(bitmap)
        val inferenceTime = System.currentTimeMillis() - startTime

        // 更新FPS
        frameCount++
        val now = System.currentTimeMillis()
        if (now - lastFpsTime >= 1000) {
            currentFps = frameCount
            frameCount = 0
            lastFpsTime = now
        }

        // 更新UI（必须在主线程）
        runOnUiThread {
            overlayView.setResults(results)
            findViewById<android.widget.TextView>(R.id.tvInfo).text =
                "FPS: $currentFps | 推理: ${inferenceTime}ms | 检测到 ${results.size} 个物体"
        }

        imageProxy.close()
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
        detector.close()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 100 && grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        }
    }
}
```

#### 检测框绘制 `OverlayView.kt`：

```kotlin
package com.example.edgeaidemo

import android.content.Context
import android.graphics.*
import android.util.AttributeSet
import android.view.View

/**
 * 在摄像头预览上绘制检测框
 */
class OverlayView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null
) : View(context, attrs) {

    private var results: List<DetectionResult> = emptyList()

    private val boxPaint = Paint().apply {
        color = Color.GREEN
        style = Paint.Style.STROKE
        strokeWidth = 4f
    }

    private val textPaint = Paint().apply {
        color = Color.WHITE
        textSize = 40f
        typeface = Typeface.DEFAULT_BOLD
    }

    private val bgPaint = Paint().apply {
        color = Color.argb(160, 0, 0, 0)
        style = Paint.Style.FILL
    }

    fun setResults(detections: List<DetectionResult>) {
        results = detections
        invalidate()  // 触发重绘
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        for (result in results) {
            // 将归一化坐标转为屏幕坐标
            val rect = RectF(
                result.boundingBox.left * width,
                result.boundingBox.top * height,
                result.boundingBox.right * width,
                result.boundingBox.bottom * height
            )

            // 画检测框
            canvas.drawRect(rect, boxPaint)

            // 画标签背景
            val label = "${result.label} ${(result.confidence * 100).toInt()}%"
            val textWidth = textPaint.measureText(label)
            canvas.drawRect(rect.left, rect.top - 50f, rect.left + textWidth + 16f, rect.top, bgPaint)

            // 画标签文字
            canvas.drawText(label, rect.left + 8f, rect.top - 12f, textPaint)
        }
    }
}
```

### 4.8 运行测试

```
操作步骤：
1. 用 USB 线连接手机和电脑
2. 手机弹出 "允许 USB 调试" → 点击允许
3. Android Studio 顶部工具栏选择你的手机
4. 点击绿色三角形 ▶ 运行
5. 首次运行会弹出摄像头权限请求 → 允许
6. 对准物体，观察检测框和 FPS

预期效果：
  - 实时显示检测框和类别名称
  - FPS 在 15~30 之间（取决于手机性能）
  - 能识别 COCO 数据集的 80 类物体
```

---

## 五、方案B：ONNX Runtime 部署

### 5.1 为什么选 ONNX Runtime？

| 对比项 | TensorFlow Lite | ONNX Runtime |
|--------|----------------|--------------|
| 开发者 | Google | 微软 |
| 模型格式 | .tflite | .onnx |
| 跨平台 | Android/iOS/嵌入式 | Android/iOS/Windows/Linux/Web |
| NPU 支持 | NNAPI Delegate | NNAPI EP / QNN EP |
| 模型来源 | TF Hub | HuggingFace / ONNX Model Zoo |
| 优势 | 生态成熟，文档丰富 | 跨平台一致性好，PyTorch 模型直接导出 |

### 5.2 添加依赖

```groovy
dependencies {
    // ONNX Runtime 核心库
    implementation 'com.microsoft.onnxruntime:onnxruntime-android:1.16.3'
    // 如需 NNAPI 加速
    implementation 'com.microsoft.onnxruntime:onnxruntime-extensions-android:0.9.0'
}
```

### 5.3 ONNX Runtime 推理代码

```kotlin
package com.example.edgeaidemo

import ai.onnxruntime.*
import android.content.Context
import android.graphics.Bitmap
import java.nio.FloatBuffer
import java.util.Collections

/**
 * ONNX Runtime 推理封装
 */
class OnnxDetector(context: Context, modelName: String = "model.onnx") {

    private val session: OrtSession
    private val env: OrtEnvironment = OrtEnvironment.getEnvironment()

    init {
        // 从 assets 加载模型
        val modelBytes = context.assets.open(modelName).readBytes()

        // 配置 Session（可选 NNAPI 加速）
        val options = OrtSession.SessionOptions().apply {
            // 使用 NNAPI（调用 NPU）
            addNnapi()
            // 或使用 CPU 多线程
            // setIntraOpNumThreads(4)
        }

        session = env.createSession(modelBytes, options)
    }

    /**
     * 执行推理
     */
    fun detect(bitmap: Bitmap): List<DetectionResult> {
        // 1. 图像预处理：Bitmap → Float 数组
        val inputArray = preprocessImage(bitmap, 640, 640)

        // 2. 创建输入 Tensor
        val inputTensor = OnnxTensor.createTensor(
            env,
            FloatBuffer.wrap(inputArray),
            longArrayOf(1, 3, 640, 640)  // NCHW 格式
        )

        // 3. 执行推理
        val inputName = session.inputNames.first()
        val results = session.run(Collections.singletonMap(inputName, inputTensor))

        // 4. 解析输出
        val output = results[0].value as Array<Array<FloatArray>>
        return postProcess(output)
    }

    /**
     * 图像预处理：缩放 + 归一化 + HWC→CHW
     */
    private fun preprocessImage(bitmap: Bitmap, width: Int, height: Int): FloatArray {
        val resized = Bitmap.createScaledBitmap(bitmap, width, height, true)
        val pixels = IntArray(width * height)
        resized.getPixels(pixels, 0, width, 0, 0, width, height)

        val floatArray = FloatArray(3 * width * height)
        for (i in pixels.indices) {
            val pixel = pixels[i]
            // RGB 归一化到 0~1，并转为 CHW 格式
            floatArray[i] = ((pixel shr 16) and 0xFF) / 255.0f              // R
            floatArray[width * height + i] = ((pixel shr 8) and 0xFF) / 255.0f  // G
            floatArray[2 * width * height + i] = (pixel and 0xFF) / 255.0f      // B
        }
        return floatArray
    }

    /**
     * 后处理：解析检测结果
     */
    private fun postProcess(output: Array<Array<FloatArray>>): List<DetectionResult> {
        // 具体解析逻辑取决于模型输出格式
        // 这里是通用示例
        val results = mutableListOf<DetectionResult>()
        // ... 解析 bounding box、class、confidence
        return results
    }

    fun close() {
        session.close()
        env.close()
    }
}
```

---

## 六、方案C：YOLOv8 部署到 Android

### 6.1 为什么选 YOLOv8？

| 对比项 | SSD MobileNet | YOLOv8n | YOLOv8s |
|--------|--------------|---------|---------|
| 精度 (mAP) | ~22% | ~37% | ~45% |
| 速度 (骁龙8 Gen3) | ~8ms | ~12ms | ~25ms |
| 模型大小 | ~6MB | ~12MB | ~44MB |
| 可定制性 | 低 | 高 | 高 |

### 6.2 导出 TFLite 格式

```bash
# 步骤1：安装依赖
pip install ultralytics

# 步骤2：导出为 TFLite 格式
python -c "
from ultralytics import YOLO

# 加载预训练模型
model = YOLO('yolov8n.pt')

# 导出为 TFLite 格式
model.export(
    format='tflite',        # 目标格式
    imgsz=640,              # 输入尺寸
    half=True,              # FP16 精度
    int8=False              # INT8 量化（需要校准数据）
)
print('✅ 导出完成！文件：yolov8n_float16.tflite')
"

# 也可以导出为 ONNX 格式（用于 ONNX Runtime）
python -c "
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
model.export(format='onnx', imgsz=640, half=True)
print('✅ 导出完成！文件：yolov8n.onnx')
"
```

### 6.3 集成到 Android 项目

```
操作步骤：
1. 将 yolov8n_float16.tflite 放入 app/src/main/assets/
2. 创建标签文件 labels.txt（COCO 80类），放入 assets/
3. 修改 ObjectDetectorHelper 加载新模型
```

### 6.4 YOLOv8 专用推理代码

```kotlin
package com.example.edgeaidemo

import android.content.Context
import android.graphics.Bitmap
import android.graphics.RectF
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.gpu.GpuDelegate
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel

/**
 * YOLOv8 TFLite 推理器
 */
class YOLOv8Detector(
    private val context: Context,
    private val modelName: String = "yolov8n_float16.tflite",
    private val labelName: String = "labels.txt",
    private val inputSize: Int = 640,
    private val confidenceThreshold: Float = 0.4f,
    private val iouThreshold: Float = 0.5f
) {
    private var interpreter: Interpreter? = null
    private var labels: List<String> = emptyList()
    private var gpuDelegate: GpuDelegate? = null

    init {
        setupInterpreter()
        loadLabels()
    }

    private fun setupInterpreter() {
        val options = Interpreter.Options().apply {
            setNumThreads(4)

            // 尝试使用 GPU 加速
            try {
                gpuDelegate = GpuDelegate()
                addDelegate(gpuDelegate)
            } catch (e: Exception) {
                // GPU 不可用，回退到 CPU
                android.util.Log.w("YOLOv8", "GPU 不可用，使用 CPU: ${e.message}")
            }
        }

        val model = loadModelFile()
        interpreter = Interpreter(model, options)
    }

    private fun loadModelFile(): MappedByteBuffer {
        val fileDescriptor = context.assets.openFd(modelName)
        val inputStream = FileInputStream(fileDescriptor.fileDescriptor)
        val fileChannel = inputStream.channel
        return fileChannel.map(
            FileChannel.MapMode.READ_ONLY,
            fileDescriptor.startOffset,
            fileDescriptor.declaredLength
        )
    }

    private fun loadLabels() {
        labels = context.assets.open(labelName).bufferedReader().readLines()
    }

    /**
     * 执行检测
     */
    fun detect(bitmap: Bitmap): List<DetectionResult> {
        val inputBuffer = preprocessImage(bitmap)
        val outputBuffer = Array(1) { Array(84) { FloatArray(8400) } }

        // 执行推理
        interpreter?.run(inputBuffer, outputBuffer)

        // 后处理：解析 YOLOv8 输出
        return postProcess(outputBuffer[0], bitmap.width, bitmap.height)
    }

    /**
     * 图像预处理
     */
    private fun preprocessImage(bitmap: Bitmap): ByteBuffer {
        val resized = Bitmap.createScaledBitmap(bitmap, inputSize, inputSize, true)
        val buffer = ByteBuffer.allocateDirect(1 * 3 * inputSize * inputSize * 4)
        buffer.order(ByteOrder.nativeOrder())

        val pixels = IntArray(inputSize * inputSize)
        resized.getPixels(pixels, 0, inputSize, 0, 0, inputSize, inputSize)

        for (pixel in pixels) {
            // 归一化到 0~1
            buffer.putFloat(((pixel shr 16) and 0xFF) / 255.0f)  // R
            buffer.putFloat(((pixel shr 8) and 0xFF) / 255.0f)   // G
            buffer.putFloat((pixel and 0xFF) / 255.0f)            // B
        }

        buffer.rewind()
        return buffer
    }

    /**
     * YOLOv8 后处理：转置 + NMS
     */
    private fun postProcess(output: Array<FloatArray>, imgWidth: Int, imgHeight: Int): List<DetectionResult> {
        val results = mutableListOf<DetectionResult>()
        val numDetections = output[0].size  // 8400

        for (i in 0 until numDetections) {
            // YOLOv8 输出格式：[x_center, y_center, width, height, class_scores...]
            val cx = output[0][i]
            val cy = output[1][i]
            val w = output[2][i]
            val h = output[3][i]

            // 找到最高置信度的类别
            var maxScore = 0f
            var maxIdx = 0
            for (c in 4 until output.size) {
                if (output[c][i] > maxScore) {
                    maxScore = output[c][i]
                    maxIdx = c - 4
                }
            }

            if (maxScore > confidenceThreshold) {
                // 转换为 [left, top, right, bottom]
                val left = (cx - w / 2) / inputSize
                val top = (cy - h / 2) / inputSize
                val right = (cx + w / 2) / inputSize
                val bottom = (cy + h / 2) / inputSize

                results.add(DetectionResult(
                    label = labels.getOrElse(maxIdx) { "class_$maxIdx" },
                    confidence = maxScore,
                    boundingBox = RectF(left, top, right, bottom)
                ))
            }
        }

        // NMS（非极大值抑制）去除重叠框
        return nms(results)
    }

    /**
     * 非极大值抑制
     */
    private fun nms(detections: List<DetectionResult>): List<DetectionResult> {
        val sorted = detections.sortedByDescending { it.confidence }.toMutableList()
        val selected = mutableListOf<DetectionResult>()

        while (sorted.isNotEmpty()) {
            val best = sorted.removeAt(0)
            selected.add(best)
            sorted.removeAll { iou(best.boundingBox, it.boundingBox) > iouThreshold }
        }

        return selected
    }

    private fun iou(a: RectF, b: RectF): Float {
        val intersection = RectF()
        if (!intersection.setIntersect(a, b)) return 0f
        val intersectionArea = intersection.width() * intersection.height()
        val unionArea = a.width() * a.height() + b.width() * b.height() - intersectionArea
        return if (unionArea > 0) intersectionArea / unionArea else 0f
    }

    fun close() {
        interpreter?.close()
        gpuDelegate?.close()
    }
}
```

### 6.5 自定义训练（检测你自己的物体）

```bash
# 和 iPhone 版本一样，训练过程在电脑上完成，只是导出格式不同

# 步骤1：准备数据（YOLO格式）
# dataset/
# ├── images/
# │   ├── train/
# │   └── val/
# └── labels/
#     ├── train/
#     └── val/

# 步骤2：创建数据配置文件 data.yaml
cat > data.yaml << EOF
path: ./dataset
train: images/train
val: images/val
names:
  0: 类别A
  1: 类别B
  2: 类别C
EOF

# 步骤3：训练
python -c "
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
model.train(data='data.yaml', epochs=50, imgsz=640, batch=16)
"

# 步骤4：导出为 Android 可用格式
python -c "
from ultralytics import YOLO
model = YOLO('runs/detect/train/weights/best.pt')

# 导出 TFLite（推荐）
model.export(format='tflite', imgsz=640, half=True)

# 或导出 ONNX
model.export(format='onnx', imgsz=640, half=True)
"
```

---

## 七、模型转换详解

### 7.1 底层原理：为什么需要转换？

```
🤔 核心问题：PyTorch/TensorFlow 训练出来的模型，Android 为什么不能直接用？

答案：训练框架的模型格式包含大量冗余信息（梯度、优化器状态等），
     手机端推理引擎需要精简、高效的格式。

┌─────────────────────────────────────────────────────────────────────┐
│                     模型转换的本质                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PyTorch (.pt/.pth)  ──┐                                           │
│                        │                                            │
│  TensorFlow (.pb)    ──┼──▶ .tflite（TensorFlow Lite 格式）         │
│                        │                                            │
│  Keras (.h5)         ──┘                                           │
│                                                                     │
│  PyTorch (.pt/.pth)  ──┐                                           │
│                        ├──▶ .onnx（ONNX 格式）                      │
│  TensorFlow (.pb)    ──┘                                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 Android 支持的模型格式

| 格式 | 后缀 | 推理引擎 | 特点 |
|------|------|---------|------|
| **TensorFlow Lite** | `.tflite` | TFLite Interpreter | Google 官方，生态最好，NNAPI 支持最完善 |
| **ONNX** | `.onnx` | ONNX Runtime | 微软主导，跨平台一致性好，PyTorch 直接导出 |
| **NCNN** | `.param` + `.bin` | ncnn | 腾讯开源，国内生态好，极致优化 |
| **MNN** | `.mnn` | MNN | 阿里开源，支持混合调度 |
| **TNN** | `.tnnproto` + `.tnnmodel` | TNN | 腾讯优图开源 |
| **Paddle Lite** | `.nb` | Paddle Lite | 百度开源，中文模型丰富 |

```
💡 小白选择建议：

  ┌─────────────────────────────────────────────────────────────┐
  │  刚入门 / Google 生态    → TensorFlow Lite (.tflite)        │
  │  跨平台 / PyTorch 模型   → ONNX Runtime (.onnx)            │
  │  极致性能 / 国内项目     → ncnn (.param + .bin)             │
  │  百度模型 / 中文NLP      → Paddle Lite (.nb)                │
  └─────────────────────────────────────────────────────────────┘
```

### 7.3 PyTorch → TFLite 转换

```python
import torch
import tensorflow as tf

# 方法1：PyTorch → ONNX → TFLite（推荐）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 步骤1：PyTorch → ONNX
model = torch.load("model.pt")
model.eval()
dummy_input = torch.randn(1, 3, 224, 224)
torch.onnx.export(model, dummy_input, "model.onnx", opset_version=13)

# 步骤2：ONNX → TFLite
# 需要安装：pip install onnx2tf
import onnx2tf
onnx2tf.convert(
    input_onnx_file_path="model.onnx",
    output_folder_path="output",
    output_signaturedefs=True
)
# 输出文件在 output/ 目录下

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 方法2：TensorFlow/Keras → TFLite（直接转换）
# 如果你的模型本身就是 TensorFlow/Keras 训练的

model = tf.keras.models.load_model("my_model.h5")

# 转换为 TFLite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]  # 自动优化
converter.target_spec.supported_types = [tf.float16]  # FP16 量化

tflite_model = converter.convert()

# 保存
with open("model_fp16.tflite", "wb") as f:
    f.write(tflite_model)
print("✅ 转换完成！")
```

### 7.4 PyTorch → ONNX 转换

```python
import torch
import torchvision

# 加载模型
model = torchvision.models.mobilenet_v3_small(pretrained=True)
model.eval()

# 创建示例输入
dummy_input = torch.randn(1, 3, 224, 224)

# 导出 ONNX
torch.onnx.export(
    model,
    dummy_input,
    "mobilenet_v3.onnx",
    opset_version=13,
    input_names=["input"],
    output_names=["output"],
    dynamic_axes={
        "input": {0: "batch_size"},
        "output": {0: "batch_size"}
    }
)
print("✅ ONNX 导出完成！")

# 验证 ONNX 模型
import onnx
model = onnx.load("mobilenet_v3.onnx")
onnx.checker.check_model(model)
print("✅ ONNX 模型验证通过！")
```

### 7.5 量化压缩（减小模型体积）

```python
import tensorflow as tf

# ========== TFLite 量化 ==========

# 方式1：动态范围量化（最简单，无需校准数据）
converter = tf.lite.TFLiteConverter.from_saved_model("saved_model/")
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()
# 效果：模型体积减小 ~4x，速度提升 ~2x

# 方式2：FP16 量化（精度损失极小）
converter.target_spec.supported_types = [tf.float16]
tflite_model = converter.convert()
# 效果：模型体积减小 ~2x，GPU 推理更快

# 方式3：INT8 全量化（需要校准数据，效果最好）
def representative_dataset():
    """提供 100~500 张代表性图片用于校准"""
    for i in range(100):
        image = load_and_preprocess_image(f"calibration_images/{i}.jpg")
        yield [image]

converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_dataset
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.uint8
converter.inference_output_type = tf.uint8
tflite_model = converter.convert()
# 效果：模型体积减小 ~4x，NPU 推理最快
```

### 7.6 各框架对比（同 iPhone 版）

| 框架/格式 | 是什么 | 开发者 | 模型文件格式 | 特点 | 适用场景 |
|-----------|--------|--------|-------------|------|---------|
| **PyTorch** | 深度学习训练框架 | Meta (Facebook) | `.pt` / `.pth` | 动态计算图，学术界主流 | 研究、原型开发 |
| **TensorFlow** | 深度学习训练+部署框架 | Google | `.pb` (SavedModel) | 生态完整，部署工具链成熟 | 工业部署 |
| **Keras** | TensorFlow 的高级 API | Google | `.h5` / `.keras` | 代码极简 | 入门学习 |
| **ONNX** | 通用模型交换格式 | 微软+Meta | `.onnx` | 跨框架"中间语言" | 跨平台部署 |

```
💡 Android 部署路径总结：

  PyTorch 模型 (.pt)
       │
       ├──▶ torch.onnx.export() ──▶ .onnx ──▶ ONNX Runtime (Android)
       │
       ├──▶ ultralytics export  ──▶ .tflite ──▶ TFLite (Android)
       │
       └──▶ ncnn 转换工具       ──▶ .param/.bin ──▶ ncnn (Android)

  TensorFlow 模型 (.pb/.h5)
       │
       └──▶ tf.lite.TFLiteConverter ──▶ .tflite ──▶ TFLite (Android)
```

---

## 八、性能实测与优化

### 8.1 性能测量代码

```kotlin
/**
 * 推理性能测量工具
 */
class PerformanceMonitor {
    private var startTime = 0L
    private val inferenceTimes = mutableListOf<Long>()

    fun startMeasure() {
        startTime = System.nanoTime()
    }

    fun endMeasure(): Long {
        val elapsed = (System.nanoTime() - startTime) / 1_000_000  // 转为毫秒
        inferenceTimes.add(elapsed)
        if (inferenceTimes.size > 100) inferenceTimes.removeAt(0)
        return elapsed
    }

    fun getAverageMs(): Long = if (inferenceTimes.isNotEmpty()) inferenceTimes.average().toLong() else 0
    fun getFps(): Int = if (getAverageMs() > 0) (1000 / getAverageMs()).toInt() else 0
}

// 使用方式：
val monitor = PerformanceMonitor()
monitor.startMeasure()
val results = detector.detect(bitmap)
val elapsed = monitor.endMeasure()
Log.d("AI", "推理耗时: ${elapsed}ms, 平均FPS: ${monitor.getFps()}")
```

### 8.2 实测数据参考

| 模型 | 骁龙8 Gen3 (CPU) | 骁龙8 Gen3 (GPU) | 骁龙8 Gen3 (NPU) | 模型大小 |
|------|-----------------|-----------------|------------------|----------|
| YOLOv8n (FP16) | ~25ms | ~15ms | ~10ms | 12MB |
| YOLOv8s (FP16) | ~55ms | ~30ms | ~20ms | 44MB |
| MobileNetV3 分类 | ~5ms | ~3ms | ~2ms | 8MB |
| EfficientDet-Lite0 | ~30ms | ~18ms | ~12ms | 15MB |

### 8.3 硬件加速 Delegate 选择

```kotlin
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.gpu.GpuDelegate
import org.tensorflow.lite.nnapi.NnApiDelegate

/**
 * 不同硬件加速方式
 */
fun createInterpreter(model: MappedByteBuffer, accelerator: String): Interpreter {
    val options = Interpreter.Options()

    when (accelerator) {
        "cpu" -> {
            // CPU 模式：兼容性最好
            options.setNumThreads(4)
        }
        "gpu" -> {
            // GPU 模式：适合大模型
            val gpuDelegate = GpuDelegate(
                GpuDelegate.Options().apply {
                    setPrecisionLossAllowed(true)  // 允许 FP16，速度更快
                    setInferencePreference(GpuDelegate.Options.INFERENCE_PREFERENCE_FAST_SINGLE_ANSWER)
                }
            )
            options.addDelegate(gpuDelegate)
        }
        "npu" -> {
            // NPU 模式：速度最快（通过 NNAPI）
            val nnApiDelegate = NnApiDelegate(
                NnApiDelegate.Options().apply {
                    setAllowFp16(true)
                    setUseNnapiCpu(false)  // 不回退到 CPU
                    // setAcceleratorName("google-edgetpu")  // 指定加速器（可选）
                }
            )
            options.addDelegate(nnApiDelegate)
        }
    }

    return Interpreter(model, options)
}
```

### 8.4 优化技巧

| 优化项 | 方法 | 效果 |
|--------|------|------|
| **降低输入分辨率** | 640→416 或 320 | 速度提升 40%~60% |
| **使用 FP16** | 导出时 `half=True` | 速度提升 ~30%，精度几乎不变 |
| **使用 INT8** | 需要校准数据 | 速度提升 ~50%，精度降 1%~2% |
| **GPU Delegate** | `GpuDelegate()` | 比 CPU 快 2~5 倍 |
| **NNAPI (NPU)** | `NnApiDelegate()` | 比 GPU 快 1.5~3 倍 |
| **跳帧处理** | 每 2~3 帧推理一次 | 降低功耗，肉眼无感 |
| **限制检测区域** | 只对 ROI 区域推理 | 大幅降低计算量 |
| **模型剪枝** | 移除不重要的通道 | 体积减小 30%~50% |

### 8.5 跳帧策略示例

```kotlin
// 不是每一帧都跑AI，节省电量
private var frameCounter = 0
private val inferenceInterval = 2  // 每2帧推理一次

override fun analyze(imageProxy: ImageProxy) {
    frameCounter++
    if (frameCounter % inferenceInterval != 0) {
        imageProxy.close()
        return
    }
    // 执行推理...
}
```

### 8.6 内存优化

```kotlin
/**
 * 内存优化最佳实践
 */
class MemoryOptimizedDetector(context: Context) {
    // 1. 复用 ByteBuffer，避免每帧都分配内存
    private val inputBuffer: ByteBuffer = ByteBuffer.allocateDirect(1 * 3 * 640 * 640 * 4).apply {
        order(ByteOrder.nativeOrder())
    }

    // 2. 复用输出数组
    private val outputBuffer = Array(1) { Array(84) { FloatArray(8400) } }

    // 3. 复用 Bitmap
    private var reusableBitmap: Bitmap? = null

    fun detect(imageProxy: ImageProxy): List<DetectionResult> {
        // 复用 Bitmap
        if (reusableBitmap == null) {
            reusableBitmap = Bitmap.createBitmap(640, 640, Bitmap.Config.ARGB_8888)
        }

        // 填充 inputBuffer（复用，不重新分配）
        inputBuffer.rewind()
        fillInputBuffer(imageProxy)

        // 推理（复用 outputBuffer）
        interpreter?.run(inputBuffer, outputBuffer)

        return postProcess(outputBuffer[0])
    }
}
```

---

## 九、常见问题排查

### 9.1 编译/运行错误

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| "Failed to install APK" | 手机存储不足或签名冲突 | 清理手机空间，卸载旧版本 |
| "INSTALL_FAILED_USER_RESTRICTED" | 小米/OPPO 限制了 USB 安装 | 开发者选项 → 开启"USB安装" |
| Gradle sync 失败 | 网络问题或版本冲突 | 配置镜像源，检查 Gradle 版本 |
| "Model file not found" | assets 路径错误 | 确认文件在 app/src/main/assets/ 下 |
| "Cannot resolve symbol" | 依赖未正确添加 | Sync Gradle，检查 build.gradle |

### 9.2 性能问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| FPS 很低 (<10) | 模型太大或未使用加速 | 换 nano 模型，启用 GPU/NPU Delegate |
| 手机发烫 | 持续满负荷推理 | 加跳帧策略，降低帧率 |
| 内存溢出 (OOM) | 模型占用内存过大 | 用更小的模型，或 INT8 量化 |
| GPU Delegate 崩溃 | 模型有不支持的算子 | 回退到 CPU，或用 NNAPI |
| NNAPI 比 CPU 还慢 | 部分算子不支持 NPU | 检查日志，排除不支持的算子 |

### 9.3 模型转换问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| TFLite 转换报错 | 不支持的算子 | 用 `tf.lite.OpsSet.SELECT_TF_OPS` 或简化模型 |
| ONNX 导出失败 | 动态控制流 | 用 `torch.jit.script` 或固定输入尺寸 |
| 推理结果全错 | 预处理不匹配 | 检查归一化方式（0~1 vs -1~1 vs ImageNet标准化） |
| 量化后精度暴降 | 校准数据不足或不代表 | 增加校准数据量，确保覆盖各种场景 |

### 9.4 摄像头问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 摄像头黑屏 | 权限未授予 | 检查 AndroidManifest.xml 和运行时权限 |
| 预览画面旋转 | 未处理设备方向 | CameraX 自动处理，或手动设置 rotation |
| 画面卡顿 | 主线程阻塞 | 确保推理在子线程执行 |
| 图像颜色异常 | YUV→RGB 转换错误 | 使用 ImageProxy.toBitmap() 或正确的转换代码 |

---

## 十、Android AI 相关框架全景图

> Android 生态中有丰富的 AI/ML 框架可供选择，从 Google 官方到第三方开源，覆盖了各种场景。

### 10.1 框架层级总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        你的 App                                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│              高层「开箱即用」框架                                     │
│                                                                     │
│  ML Kit          MediaPipe        Google AI Client                  │
│  (视觉/语言)     (视觉/手势/姿态)  (Gemini API)                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│              中层「推理引擎」框架                                     │
│                                                                     │
│  TensorFlow Lite    ONNX Runtime    ncnn    MNN    Paddle Lite      │
│  (Google)           (微软)          (腾讯)  (阿里)  (百度)           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│              底层「硬件加速」层                                       │
│                                                                     │
│  NNAPI (NPU)    OpenCL/Vulkan (GPU)    CPU (NEON/SVE)              │
└─────────────────────────────────────────────────────────────────────┘
```

### 10.2 各框架详解

#### 📦 TensorFlow Lite —— Android AI 的「标配引擎」

| 项目 | 说明 |
|------|------|
| **定位** | Google 官方的移动端/嵌入式推理引擎 |
| **支持格式** | `.tflite` |
| **核心能力** | 模型推理 + 多种硬件加速 Delegate |
| **最低版本** | Android 5.0+ (API 21) |

```kotlin
// 最基本的用法
import org.tensorflow.lite.Interpreter

val model = loadModelFile("model.tflite")
val interpreter = Interpreter(model)

// 准备输入
val input = ByteBuffer.allocateDirect(...)
// 执行推理
val output = Array(1) { FloatArray(1000) }
interpreter.run(input, output)
```

**Delegate（硬件加速）机制：**

| Delegate | 硬件 | 适用场景 |
|----------|------|---------|
| CPU (默认) | ARM CPU | 兼容性最好，所有手机都支持 |
| GPU Delegate | GPU (OpenCL/OpenGL) | 大模型、浮点运算密集 |
| NNAPI Delegate | NPU/DSP | 速度最快，但兼容性因厂商而异 |
| Hexagon Delegate | 高通 DSP | 高通芯片专用，INT8 极快 |
| XNNPACK | CPU (优化) | 浮点模型的 CPU 加速 |

**📚 继续学习：**
- [TensorFlow Lite 官方文档](https://www.tensorflow.org/lite) — 完整指南
- [TFLite Model Maker](https://www.tensorflow.org/lite/models/modify/model_maker) — 快速训练自定义模型
- [TFLite 模型库](https://tfhub.dev/) — 现成模型下载
- [TFLite Android 示例](https://github.com/tensorflow/examples/tree/master/lite/examples) — 官方示例代码

---

#### 🎯 ML Kit —— Google 的「AI 万能工具箱」

| 项目 | 说明 |
|------|------|
| **定位** | Google 提供的高层 AI API，开箱即用 |
| **核心能力** | 文字识别、人脸检测、条码扫描、图像标注、姿态检测等 |
| **特点** | 无需自己训练模型，几行代码搞定 |
| **最低版本** | Android 5.0+ |

```kotlin
// 示例：文字识别（OCR）
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.chinese.ChineseTextRecognizerOptions

val recognizer = TextRecognition.getClient(ChineseTextRecognizerOptions.Builder().build())
val image = InputImage.fromBitmap(bitmap, 0)

recognizer.process(image)
    .addOnSuccessListener { result ->
        for (block in result.textBlocks) {
            println("识别到文字: ${block.text}")
        }
    }
```

```kotlin
// 示例：人脸检测
import com.google.mlkit.vision.face.FaceDetection
import com.google.mlkit.vision.face.FaceDetectorOptions

val options = FaceDetectorOptions.Builder()
    .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_FAST)
    .setLandmarkMode(FaceDetectorOptions.LANDMARK_MODE_ALL)
    .build()

val detector = FaceDetection.getClient(options)
detector.process(image)
    .addOnSuccessListener { faces ->
        for (face in faces) {
            println("人脸位置: ${face.boundingBox}")
            println("微笑概率: ${face.smilingProbability}")
        }
    }
```

**ML Kit 支持的功能：**

| 功能 | 是否需要网络 | 说明 |
|------|-------------|------|
| 文字识别 (OCR) | ❌ 离线 | 支持中文、英文等多语言 |
| 人脸检测 | ❌ 离线 | 支持表情、关键点 |
| 条码扫描 | ❌ 离线 | 支持各种条码/二维码 |
| 图像标注 | ❌ 离线 | 识别图片中的物体类别 |
| 物体检测 | ❌ 离线 | 实时检测+追踪 |
| 姿态检测 | ❌ 离线 | 人体关键点 |
| 自拍分割 | ❌ 离线 | 人像背景分离 |
| 翻译 | ✅ 在线 | 多语言互译 |
| 智能回复 | ✅ 在线 | 自动生成回复建议 |

**📚 继续学习：**
- [ML Kit 官方文档](https://developers.google.com/ml-kit) — 完整指南
- [ML Kit Android 快速入门](https://developers.google.com/ml-kit/guides) — 各功能教程
- [ML Kit 示例代码](https://github.com/googlesamples/mlkit) — 官方示例

---

#### 🖐️ MediaPipe —— 实时视觉 AI 的「瑞士军刀」

| 项目 | 说明 |
|------|------|
| **定位** | Google 的跨平台实时 AI 框架 |
| **核心能力** | 手势识别、人脸网格、姿态估计、物体检测、图像分割 |
| **特点** | 性能极高，专为实时场景优化 |
| **最低版本** | Android 5.0+ |

```kotlin
// 示例：手势识别
import com.google.mediapipe.tasks.vision.gesturerecognizer.GestureRecognizer

val options = GestureRecognizer.GestureRecognizerOptions.builder()
    .setBaseOptions(BaseOptions.builder().setModelAssetPath("gesture_recognizer.task").build())
    .setRunningMode(RunningMode.LIVE_STREAM)
    .setResultListener { result, _ ->
        val gesture = result.gestures().firstOrNull()?.firstOrNull()
        println("手势: ${gesture?.categoryName()}")  // "Thumbs_Up", "Victory" 等
    }
    .build()

val recognizer = GestureRecognizer.createFromOptions(context, options)
```

**MediaPipe 支持的解决方案：**

| 解决方案 | 功能 | 典型应用 |
|---------|------|---------|
| Hand Landmark | 21个手部关键点 | 手势控制、手语识别 |
| Face Mesh | 468个面部关键点 | AR滤镜、表情捕捉 |
| Pose Landmark | 33个身体关键点 | 健身指导、动作分析 |
| Object Detection | 物体检测 | 实时识别 |
| Image Segmentation | 图像分割 | 背景替换、人像抠图 |
| Text Classification | 文本分类 | 情感分析 |
| Audio Classification | 音频分类 | 环境声音识别 |

**📚 继续学习：**
- [MediaPipe 官方文档](https://developers.google.com/mediapipe) — 完整指南
- [MediaPipe Solutions](https://developers.google.com/mediapipe/solutions) — 各解决方案详解
- [MediaPipe Android 示例](https://github.com/google-ai-edge/mediapipe-samples) — 官方示例代码

---

#### ⚡ ONNX Runtime —— 跨平台的「万能推理器」

| 项目 | 说明 |
|------|------|
| **定位** | 微软开源的高性能推理引擎 |
| **支持格式** | `.onnx` |
| **核心优势** | 跨平台一致性（Android/iOS/Windows/Linux/Web 同一套代码） |
| **最低版本** | Android 5.0+ |

```kotlin
import ai.onnxruntime.*

val env = OrtEnvironment.getEnvironment()
val session = env.createSession(modelBytes)

// 推理
val inputTensor = OnnxTensor.createTensor(env, inputData)
val results = session.run(mapOf("input" to inputTensor))
val output = results[0].value as Array<FloatArray>
```

**Execution Provider（硬件加速）：**

| EP | 硬件 | 说明 |
|----|------|------|
| CPU EP | CPU | 默认，兼容性最好 |
| NNAPI EP | NPU | 通过 Android NNAPI 调用 NPU |
| QNN EP | 高通 NPU | 高通芯片专用，性能最佳 |
| XNNPACK EP | CPU (优化) | 浮点模型加速 |

**📚 继续学习：**
- [ONNX Runtime 官方文档](https://onnxruntime.ai/) — 完整指南
- [ONNX Runtime Android](https://onnxruntime.ai/docs/get-started/with-java.html) — Android 集成教程
- [ONNX Model Zoo](https://github.com/onnx/models) — 现成 ONNX 模型

---

#### 🐧 ncnn —— 国产极致性能的「轻量引擎」

| 项目 | 说明 |
|------|------|
| **定位** | 腾讯开源的高性能神经网络推理框架 |
| **支持格式** | `.param` + `.bin` |
| **核心优势** | 极致优化，无第三方依赖，体积极小 |
| **最低版本** | Android 4.0+ |

```cpp
// ncnn 使用 C++ API（通过 JNI 调用）
#include "net.h"

ncnn::Net net;
net.load_param("model.param");
net.load_model("model.bin");

ncnn::Mat input = ncnn::Mat::from_pixels_resize(pixels, ncnn::Mat::PIXEL_BGR, w, h, 640, 640);
input.substract_mean_normalize(mean_vals, norm_vals);

ncnn::Extractor ex = net.create_extractor();
ex.set_vulkan_compute(true);  // GPU 加速
ex.input("input", input);

ncnn::Mat output;
ex.extract("output", output);
```

**📚 继续学习：**
- [ncnn GitHub](https://github.com/Tencent/ncnn) — 源码和文档
- [ncnn Android 示例](https://github.com/nihui/ncnn-android-yolov5) — YOLOv5 Android 部署
- [ncnn 模型转换工具](https://github.com/Tencent/ncnn/wiki/use-ncnn-with-pytorch-or-onnx) — 转换教程

---

#### 📷 CameraX —— 摄像头的「简化版 API」

| 项目 | 说明 |
|------|------|
| **定位** | Google Jetpack 的摄像头库 |
| **核心能力** | 预览、拍照、录像、图像分析 |
| **与 AI 关系** | 提供实时摄像头画面供 AI 模型处理 |
| **最低版本** | Android 5.0+ (API 21) |

```kotlin
// CameraX 的 ImageAnalysis 是连接摄像头和 AI 的桥梁
val imageAnalysis = ImageAnalysis.Builder()
    .setTargetResolution(Size(640, 480))
    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
    .build()

imageAnalysis.setAnalyzer(executor) { imageProxy ->
    // imageProxy 包含摄像头的每一帧画面
    // 转为 Bitmap 后送入 AI 模型
    val bitmap = imageProxy.toBitmap()
    val results = detector.detect(bitmap)
    imageProxy.close()
}
```

**📚 继续学习：**
- [CameraX 官方文档](https://developer.android.com/training/camerax) — 完整指南
- [CameraX 代码实验室](https://developer.android.com/codelabs/camerax-getting-started) — 手把手教程

---

#### 🧠 NNAPI —— 硬件加速的「统一接口」

| 项目 | 说明 |
|------|------|
| **定位** | Android 系统级的神经网络加速 API |
| **核心能力** | 统一调用各厂商的 NPU/DSP/GPU |
| **特点** | 你不直接调用它，而是通过 TFLite/ONNX Runtime 的 Delegate 间接使用 |
| **最低版本** | Android 8.1+ (API 27) |

```
NNAPI 的作用：

  你的 App
      │
      ▼
  TFLite / ONNX Runtime
      │
      ▼ (通过 NNAPI Delegate)
  ┌─────────────────────────────────────┐
  │           Android NNAPI              │
  │    (系统级统一硬件加速接口)           │
  └──────────────┬──────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
  高通 NPU    联发科 APU    三星 NPU
  (Hexagon)   (APU)        (Exynos NPU)
```

**📚 继续学习：**
- [NNAPI 官方文档](https://developer.android.com/ndk/guides/neuralnetworks) — 完整指南
- [NNAPI 支持的算子列表](https://developer.android.com/ndk/guides/neuralnetworks#operations) — 兼容性参考

---

### 10.3 框架选择速查表

| 你想做什么？ | 用哪个框架？ | 难度 |
|-------------|-------------|------|
| 文字识别 (OCR) | ML Kit | ⭐ |
| 人脸检测 | ML Kit | ⭐ |
| 条码/二维码扫描 | ML Kit | ⭐ |
| 手势识别 | MediaPipe | ⭐⭐ |
| 人体姿态估计 | MediaPipe | ⭐⭐ |
| 实时物体检测 | TFLite + CameraX | ⭐⭐ |
| 自定义模型部署 | TFLite / ONNX Runtime | ⭐⭐ |
| 跨平台部署 | ONNX Runtime | ⭐⭐ |
| 极致性能优化 | ncnn | ⭐⭐⭐ |
| 端侧大模型 | MediaPipe LLM / llama.cpp | ⭐⭐⭐ |

### 10.4 框架之间的协作关系

```
典型的「实时摄像头物体检测」数据流：

  CameraX              ImageProxy          TFLite            NNAPI
 ┌──────────┐      ┌──────────────┐     ┌──────────┐     ┌──────────┐
 │ 摄像头   │ ───▶ │ YUV 图像帧   │ ──▶ │ 模型推理  │ ──▶ │ NPU 加速  │
 │ 采集画面 │      │ → Bitmap     │     │ 输出结果  │     │ 硬件执行  │
 └──────────┘      └──────────────┘     └──────────┘     └──────────┘
                                                               │
                                                               ▼
                                                        ┌──────────┐
                                                        │ 检测框    │
                                                        │ 类别+置信度│
                                                        └──────────┘
```

```
典型的「多模态 AI 应用」数据流：

  CameraX              ML Kit              MediaPipe         自定义模型
 ┌──────────┐      ┌──────────────┐     ┌──────────────┐   ┌──────────┐
 │ 摄像头   │ ───▶ │ 文字识别     │     │ 手势识别     │   │ 业务逻辑  │
 │ 采集画面 │      │ "打开灯"    │ ──▶ │ 竖大拇指 👍  │ ──▶│ 执行命令  │
 └──────────┘      └──────────────┘     └──────────────┘   └──────────┘
```

> 💡 **小白记忆口诀**：
> - **开箱即用** → ML Kit / MediaPipe
> - **自定义模型** → TFLite / ONNX Runtime
> - **极致性能** → ncnn / MNN
> - **拍摄画面** → CameraX
> - **硬件加速** → NNAPI (自动调用)
> - **大语言模型** → MediaPipe LLM / llama.cpp

---

## 十一、进阶玩法

### 11.1 端侧大语言模型

```kotlin
// 方法1：使用 MediaPipe LLM Inference API
import com.google.mediapipe.tasks.genai.llminference.LlmInference

val options = LlmInference.LlmInferenceOptions.builder()
    .setModelPath("/path/to/gemma-2b-it-gpu-int4.bin")
    .setMaxTokens(1024)
    .setTemperature(0.8f)
    .build()

val llm = LlmInference.createFromOptions(context, options)
val response = llm.generateResponse("请用一句话解释什么是机器学习")
println(response)  // "机器学习是让计算机从数据中自动学习规律的技术。"

// 方法2：使用 llama.cpp 的 Android 版本
// 支持 Llama 3.2、Phi-3、Qwen 等模型
// 参考：https://github.com/ggerganov/llama.cpp/tree/master/examples/llama.android
```

### 11.2 实时姿态估计

```kotlin
// 使用 MediaPipe Pose Landmark
import com.google.mediapipe.tasks.vision.poselandmarker.PoseLandmarker

val options = PoseLandmarker.PoseLandmarkerOptions.builder()
    .setBaseOptions(BaseOptions.builder().setModelAssetPath("pose_landmarker.task").build())
    .setRunningMode(RunningMode.LIVE_STREAM)
    .setNumPoses(1)
    .setResultListener { result, _ ->
        val landmarks = result.landmarks().firstOrNull() ?: return@setResultListener
        // 33 个关键点
        val nose = landmarks[0]
        val leftShoulder = landmarks[11]
        val rightShoulder = landmarks[12]
        println("鼻子: (${nose.x()}, ${nose.y()})")
    }
    .build()

val poseLandmarker = PoseLandmarker.createFromOptions(context, options)
```

### 11.3 文字识别（OCR）

```kotlin
// ML Kit 内置 OCR，支持中文
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.chinese.ChineseTextRecognizerOptions

val recognizer = TextRecognition.getClient(
    ChineseTextRecognizerOptions.Builder().build()
)

val image = InputImage.fromBitmap(bitmap, 0)
recognizer.process(image)
    .addOnSuccessListener { result ->
        println("识别结果: ${result.text}")
        // 还可以获取每个文字块的位置
        for (block in result.textBlocks) {
            println("文字块: ${block.text}, 位置: ${block.boundingBox}")
        }
    }
```

### 11.4 图像分割（背景替换）

```kotlin
// 使用 MediaPipe Image Segmentation
import com.google.mediapipe.tasks.vision.imagesegmenter.ImageSegmenter

val options = ImageSegmenter.ImageSegmenterOptions.builder()
    .setBaseOptions(BaseOptions.builder().setModelAssetPath("selfie_segmenter.tflite").build())
    .setOutputCategoryMask(true)
    .setRunningMode(RunningMode.LIVE_STREAM)
    .setResultListener { result, _ ->
        val mask = result.categoryMask().get()
        // mask 中每个像素的值表示类别（0=背景，1=人物）
        // 可以用来实现背景虚化、背景替换等效果
    }
    .build()

val segmenter = ImageSegmenter.createFromOptions(context, options)
```

### 11.5 完整项目结构参考

```
EdgeAIDemo/
├── app/
│   ├── build.gradle                    ← 依赖配置
│   ├── src/
│   │   └── main/
│   │       ├── AndroidManifest.xml     ← 权限声明
│   │       ├── assets/
│   │       │   ├── yolov8n_float16.tflite  ← AI模型
│   │       │   └── labels.txt              ← 类别标签
│   │       ├── java/com/example/edgeaidemo/
│   │       │   ├── MainActivity.kt         ← 主界面
│   │       │   ├── ObjectDetectorHelper.kt ← 检测器封装
│   │       │   ├── YOLOv8Detector.kt       ← YOLOv8 专用
│   │       │   └── OverlayView.kt          ← 检测框绘制
│   │       └── res/
│   │           └── layout/
│   │               └── activity_main.xml   ← 布局文件
├── build.gradle                        ← 项目级配置
├── settings.gradle                     ← 仓库配置
└── gradle.properties                   ← Gradle 属性
```

---

## 十二、Android vs iPhone 边缘AI 对比

| 对比维度 | Android | iPhone |
|---------|---------|--------|
| 开发工具 | Android Studio (全平台) | Xcode (仅 Mac) |
| 开发语言 | Kotlin / Java / C++ | Swift / Objective-C |
| 推理引擎 | TFLite / ONNX Runtime / ncnn | Core ML |
| 模型格式 | .tflite / .onnx / .param+.bin | .mlmodel / .mlpackage |
| NPU 调用 | NNAPI (各厂商实现不同) | Neural Engine (统一) |
| 硬件碎片化 | 高（各品牌芯片不同） | 低（苹果统一） |
| 性能一致性 | 因设备而异 | 非常一致 |
| 开箱即用 API | ML Kit / MediaPipe | Vision / NaturalLanguage |
| 模型训练 | TFLite Model Maker | Create ML |
| 生态丰富度 | ⭐⭐⭐⭐⭐ 极丰富 | ⭐⭐⭐ 较丰富 |
| 部署难度 | ⭐⭐⭐ 中等（碎片化） | ⭐⭐ 较简单（统一） |

```
💡 选择建议：

  ┌─────────────────────────────────────────────────────────────┐
  │  追求最简单的开发体验      → iPhone (Core ML + Vision)      │
  │  追求最广泛的设备覆盖      → Android (TFLite)               │
  │  追求跨平台一致性          → ONNX Runtime (两端通用)        │
  │  追求极致性能              → 各平台原生方案                  │
  └─────────────────────────────────────────────────────────────┘
```

---

## 附录：一键验证清单

完成所有步骤后，对照检查：

- [ ] Android Studio 安装成功，能创建新项目
- [ ] 手机开启了开发者模式和 USB 调试
- [ ] 项目能编译通过（无红色错误）
- [ ] App 能安装到手机上
- [ ] 摄像头权限已授予，预览画面正常
- [ ] AI 模型加载成功（无崩溃）
- [ ] 能看到实时检测框和类别标签
- [ ] FPS 显示正常（>10 即可）

---

## 附录：推荐学习资源

| 资源 | 链接 | 说明 |
|------|------|------|
| TFLite 官方示例 | https://github.com/tensorflow/examples/tree/master/lite | 各种场景的完整代码 |
| MediaPipe 示例 | https://github.com/google-ai-edge/mediapipe-samples | 手势/姿态/检测等 |
| ML Kit 示例 | https://github.com/googlesamples/mlkit | OCR/人脸/条码等 |
| ncnn 示例 | https://github.com/nihui/ncnn-android-yolov5 | 高性能检测 |
| Ultralytics Android | https://docs.ultralytics.com/guides/android/ | YOLOv8 官方 Android 指南 |
| ONNX Runtime Android | https://onnxruntime.ai/docs/get-started/with-java.html | ONNX 集成教程 |
| Android AI Codelab | https://developer.android.com/codelabs | Google 官方代码实验室 |

---

> 📝 **最后提醒**：Android 设备碎片化严重，同一个模型在不同手机上的表现可能差异很大。
> 建议在目标设备上实际测试性能，并准备好 CPU 回退方案（当 GPU/NPU 不可用时）。
> 
> 祝你在 Android 边缘AI 的世界里玩得开心！🚀
