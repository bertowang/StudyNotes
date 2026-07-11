---
tags:
  - python
  - conda
  - venv
  - macos
  - vscode
  - xcode
  - homebrew
  - arm
  - mps
  - metal
  - pytorch
  - m4-chip
aliases:
  - Mac Python 环境管理
  - Conda 操作指南
  - VS Code 配置 Conda
  - Mac M4 AI 训练环境
  - MPS 加速配置
created: 2026-06-20
updated: 2026-06-20
---

# Python 与 Conda 环境管理（macOS / ARM）

---

## 一、Mac 上安装 Python 环境

### 1.1 Homebrew 安装 Python3

```bash
brew install python3
```

验证：

```bash
python3 --version
pip3 --version
```

> Homebrew 的 Python 自带 `venv` 模块，不需要额外装 `virtualenv`。

---

## 二、venv 虚拟环境（Python 内置）

### 2.1 什么是 venv？

`venv` = Python 3.3+ 自带的轻量级虚拟环境工具。为每个项目创建独立的 Python 解释器副本 + 独立 `site-packages`，项目依赖互不干扰。

### 2.2 创建与激活

```bash
# 创建项目文件夹
mkdir -p ~/dev/yolo-coreml
cd ~/dev/yolo-coreml

# 创建虚拟环境
python3 -m venv .venv

# 激活（macOS/Linux）
source .venv/bin/activate
```

激活后终端提示符变为 `(.venv) user@Mac project %`。

### 2.3 在虚拟环境中装依赖

```bash
pip install --upgrade pip
pip install coremltools torch ultralytics
```

验证是否装对地方：

```bash
which python
# 应指向 .../yolo-coreml/.venv/bin/python

pip list
```

### 2.4 导出与复现

```bash
# 导出
pip freeze > requirements.txt

# 别人复现
source .venv/bin/activate
pip install -r requirements.txt
```

### 2.5 常用操作

| 操作 | 命令 |
|:-----|:-----|
| 退出环境 | `deactivate` |
| 删除环境 | `rm -rf .venv` |
| 查找所有 venv | `find ~ -maxdepth 5 -type d \( -name ".venv" -o -name "venv" \) 2>/dev/null` |

> [!warning] 不要用 `sudo pip install`——`sudo` 会绕过虚拟环境；不要把 `.venv/` 提交到 Git，在 `.gitignore` 中添加 `.venv/`。

---

## 三、Conda 环境管理（Miniforge3）

### 3.1 Conda vs venv：什么时候用哪个？

| | venv | Conda |
|:---|:-----|:------|
| Python 版本管理 | 不可（依赖系统 Python） | 可（`conda create -n env python=3.10`） |
| 非 Python 依赖 | 不支持 | 支持（CUDA、C 库等） |
| 轻量 | ★★★★★ | ★★★★ |
| 深度学习项目 | 不一定够 | 更稳 |

> 纯 Python 项目 → `venv` 够用；深度学习复杂依赖 → **Conda 更稳**。

### 3.2 创建环境

```bash
# 创建空白环境
conda create -n myenv python=3.10 -y

# 激活
conda activate myenv

# 验证
which python
# 应输出：/Users/berton/miniforge3/envs/myenv/bin/python
```

### 3.3 创建时一步到位装包

```bash
conda create -n myenv python=3.10 numpy pandas matplotlib -y
conda activate myenv
```

> [!warning] `torch` / `ultralytics` / `coremltools` 这类包建议用 `pip` 装（Conda 仓库版本滞后），见 3.7 节。

### 3.4 从 YAML 声明式构建（推荐团队协作）

`environment.yaml`：

```yaml
name: myenv
channels:
  - defaults
  - conda-forge
dependencies:
  - python=3.10
  - numpy
  - pandas
  - matplotlib
  - pip
  - pip:
      - torch
      - torchvision
      - ultralytics
      - coremltools
```

一键构建：

```bash
conda env create -f environment.yaml
conda activate myenv
```

### 3.5 日常管理命令

```bash
# 查看所有环境
conda env list

# 退出当前环境
conda deactivate

# 删除环境
conda remove -n myenv --all -y

# 克隆环境
conda create -n pytorch_m4_v2 --clone pytorch_m4 -y

# 导出环境
conda env export > environment.yaml
conda env export --from-history > environment-minimal.yaml  # 更干净

# 清缓存
conda clean --all
```

### 3.6 更新组件

```bash
# 更新单个包
conda update numpy

# 更新所有 conda 包（先 dry-run）
conda update --all --dry-run
conda update --all -y

# 更新 pip 包
pip install --upgrade ultralytics

# 查看过期包
conda update --dry-run
pip list --outdated
```

### 3.7 M 系列 Mac 推荐安装顺序（PyTorch → CoreML）

```bash
conda create -n pt_m4 python=3.10 -y
conda activate pt_m4

# 先装 conda 管的科学包
conda install numpy pandas pillow -y

# PyTorch（PyPI 版对 M 芯片支持更好）
pip install --upgrade pip
pip install torch torchvision

# YOLO + CoreML
pip install ultralytics coremltools

# 验证
python -c "
import torch, ultralytics, coremltools
print('✅ torch', torch.__version__)
print('✅ MPS available:', torch.backends.mps.is_available())
print('✅ ultralytics', ultralytics.__version__)
"
```

### 3.8 Conda 和 pip 混用原则

> [!important] 核心原则：**能用 conda 的优先 conda，conda 没有的用 pip，别交替装同一包的不同版本。**

| 包来源 | 优先级 | 说明 |
|:-------|:-------|:-----|
| 能用 conda 装的 | ✅ 优先 | 尤其是有 C/C++ 扩展的（numpy, scipy 等） |
| conda 没有的 | 用 pip | 如 ultralytics, coremltools 最新版 |
| PyTorch | 跟官方走 | ARM Mac 推荐 `pip install torch` |

### 3.9 环境损坏救急

```bash
# 回滚到上次正常状态
conda list --revisions
conda install --revision N  # N 是 revision 编号

# 重建（最干净）
conda deactivate
conda remove -n 环境名 --all
conda create -n 环境名 python=3.10
conda activate 环境名
pip install -r requirements.txt
```

### 3.10 常见问题

| 问题 | 解决 |
|:-----|:-----|
| `conda activate` 报 "shell not configured" | `conda init zsh` → 重启终端 |
| `pip install torch` 太慢 | 加镜像：`-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| 删环境报 "Cannot remove current" | 先 `conda deactivate` |
| `python` vs `python3` 是同一个吗？ | 在 conda 环境里两者通常指向同一解释器，可以用 `readlink -f` 验证 |
| 想锁定某包不升级 | `conda pin 包名`；解锁 `conda unpin 包名` |

### 3.11 Miniforge3 vs Miniconda3 对比

| 特性 | Miniconda3 | Miniforge3 |
|:---|:---|:---|
| **维护方** | Anaconda Inc. 商业公司 | Conda-Forge 开源社区 |
| **默认 Channel** | `defaults`（Anaconda 官方） | `conda-forge`（社区） |
| **Apple Silicon 支持** | 仅 x86_64（需 Rosetta 转译） | **原生 ARM64** |
| **安装大小** | ~70 MB | ~50-60 MB |
| **许可证** | 部分包受商业条款约束 | 100% 开源 |
| **数学库** | Intel MKL（闭源） | OpenBLAS（开源） |

> [!important] **M1/M2/M3/M4 Mac 用户优先选 Miniforge3**：原生 ARM 架构，NumPy/Pandas/PyTorch 性能比 Miniconda3 (Rosetta) 快 38%-75%。

混合使用注意：
- Miniconda3 可添加 `conda-forge` 源，Miniforge3 也可搭配 `defaults`
- 但建议保持**单一仓库策略**，避免优先级混乱

### 3.12 Conda 查看命令速查

#### 环境查看

| 操作 | 命令 |
|:---|:---|
| 列出所有环境 | `conda env list` 或 `conda info --envs` |
| 当前激活环境 | `conda info \| grep "active environment"` |
| 环境完整路径 | `conda info --base` |
| 环境详细信息 | `conda info` |
| 导出环境配置 | `conda env export -n 环境名` |

#### 包查看

| 操作 | 命令 |
|:---|:---|
| 当前环境所有包 | `conda list` |
| 指定环境的包 | `conda list -n 环境名` |
| 显示包来源频道 | `conda list --show-channel-urls` |
| 搜索某包版本 | `conda search 包名` |
| 查看可更新包 | `conda list --outdated` 或 `conda outdated` |
| 查看历史 revision | `conda list --revisions` |

#### 配置查看

| 操作 | 命令 |
|:---|:---|
| 所有配置项 | `conda config --show` |
| 频道优先级 | `conda config --show channels` |
| 查看源配置 | `conda config --get channels` |
| 查看全部信息 | `conda info --all` |
| 查看历史操作 | `conda history` |

### 3.13 `conda init` 错误修复

**错误**：`CondaError: Run 'conda init' before 'conda activate'`

**原因**：Shell 未正确初始化 Conda。

**解决**：

```bash
# 自动检测 Shell 类型
conda init

# 或手动指定（macOS 默认 zsh）
conda init zsh

# 重新加载配置
source ~/.zshrc
```

若 `conda init` 不可用（conda 命令本身未找到），手动添加初始化代码到 `~/.zshrc`：

```bash
# 替换 ~/miniforge3 为你的 conda 安装路径
__conda_setup="$('~/miniforge3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "~/miniforge3/etc/profile.d/conda.sh" ]; then
        . "~/miniforge3/etc/profile.d/conda.sh"
    else
        export PATH="~/miniforge3/bin:$PATH"
    fi
fi
unset __conda_setup
```

**临时替代方案**：`source activate base`

### 3.14 Conda Channels & Config 管理

#### 添加源（国内镜像加速）

```bash
# 清华镜像
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/

# 设置严格优先级
conda config --set channel_priority strict

# 显示 URL
conda config --set show_channel_urls yes
```

#### 删除源

```bash
# 删除单个频道（URL 必须完全匹配）
conda config --remove channels 'http://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/pytorch/'

# 一次性恢复默认频道
conda config --remove-key channels
```

#### 常用配置

| 操作 | 命令 |
|:---|:---|
| 禁用自动激活 base | `conda config --set auto_activate_base false` |
| 查看当前 channels | `conda config --show channels` |
| 搜索特定频道中的包 | `conda search -c conda-forge 包名` |

### 3.15 Python Pin 版本锁定冲突

**问题**：安装包时提示 `Pins seem to be involved in the conflict. Currently pinned specs: - python=3.12`

**原因**：Conda 的 pin 机制（版本锁定）强制固定了 Python 版本，导致无法安装依赖更旧/更新 Python 的包。

**解决**：

```bash
# 1. 查看固定配置
cat ~/.conda/pinned            # 全局 pin
cat conda-meta/pinned          # 当前环境 pin（在环境目录下）

# 2. 删除 pin 文件中的对应行即可

# 3. 或安装时临时忽略 pin
conda install 包名 --no-pin

# 4. 或创建新环境避开冲突
conda create -n myenv python=3.11 包名
```

> [!note] **建议**：Python 3.12 较新，部分第三方包尚未完全适配。优先使用 3.10 或 3.11 更稳定。

---

## 四、Homebrew 与 Conda 对比

### 4.1 Homebrew 更新组件

```bash
# 更新索引（不动软件）
brew update

# 查看过期
brew outdated
brew outdated --cask

# 升级全部
brew upgrade
brew upgrade --cask

# 升级指定
brew upgrade python3

# 清理旧版本
brew cleanup
```

> [!note] `brew upgrade python3` 升级的是 Homebrew 自己的 Python，管不到 Conda 环境里的 Python —— 两者平行无关。

### 4.2 Brew vs Conda 系统对比

| 特性 | Brew (Homebrew) | Conda |
|:---|:---|:---|
| **定位** | macOS/Linux 系统级包管理器 | 跨平台科学计算环境管理器 |
| **虚拟环境** | 不支持（需借助 venv 等） | **原生支持** |
| **依赖管理** | 简单，适合通用工具 | 复杂 SAT 求解器，适合科学计算 |
| **跨平台** | macOS / Linux 为主 | Windows / macOS / Linux |
| **安装大小** | 极轻量 | 基础 ~80 MB（Miniforge） |
| **典型用途** | `git`, `node`, `ffmpeg`, `wget` | `numpy`, `pytorch`, `pandas` |
| **Python 管理** | 安装系统级 Python | 管理多个独立 Python 版本 |

**推荐混合使用**：

| 场景 | 工具 |
|:---|:---|
| 系统工具（git, htop, tmux, mysql） | `brew` |
| Python 环境 & 科学计算包 | `conda` |
| conda 没有的 Python 包 | `pip`（在 conda 环境内） |

> [!tip] 三者互补：**brew** 管系统 → **conda** 管环境 → **pip** 补漏缺包。

---

## 五、Python 版本选择建议

| 版本 | 状态 | 建议 |
|:-----|:-----|:-----|
| 3.11 / 3.12 | bugfix/security | **最稳甜点区间** — PyTorch/ultralytics/coremltools 全系验证最充分 |
| 3.13 | bugfix 维护中 | 能用但 free-threading 等新特性可能引发 C 扩展兼容问题 |
| 3.14 | 最新稳定（2025.10） | 太新，部分包 wheels 未全覆盖 |

> YOLO → CoreML 工作流：**3.11 或 3.12 最省心**，除非有明确理由要新语法特性。

---

## 六、VS Code 配置 Conda 环境

### 6.1 前提：确保 conda 可用

```bash
conda init zsh
# 完全退出 VS Code 再重开
```

### 6.2 选择解释器（核心操作）

打开 VS Code → 打开项目文件夹 → `Cmd+Shift+P` → `Python: Select Interpreter` → 选 `Python 3.x.x ('pytorch_m4': conda)`

或手动指定路径：

```
/Users/berton/miniforge3/envs/pytorch_m4/bin/python
```

### 6.3 固化到项目设置

`.vscode/settings.json`：

```json
{
    "python.defaultInterpreterPath": "/Users/berton/miniforge3/envs/pytorch_m4/bin/python",
    "python.terminal.activateEnvironment": true
}
```

### 6.4 验证

在 VS Code 里跑：

```python
import sys
print(sys.executable)
# 必须输出 .../envs/pytorch_m4/bin/python
```

### 6.5 多环境切换

> VS Code 不会自动追踪终端里 `conda activate` 了哪个环境。推荐做法：**每个项目 `.vscode/settings.json` 钉死一个环境**——打开哪个文件夹就自动落哪个环境。

| 场景 | 做法 |
|:-----|:-----|
| 项目 A 用 env-A | `Project-A/.vscode/settings.json` → env-A |
| 项目 B 用 env-B | `Project-B/.vscode/settings.json` → env-B |
| 终端手动切换 | 爱 `conda activate` 啥就啥，不打架 |

---

## 七、Xcode 使用 Conda 环境

> Xcode 不会（也不能）像终端一样 `conda activate`。正确做法：**直接用绝对路径**。

### 7.1 确认环境 Python 路径

```bash
conda activate pytorch_m4
which python
# 输出示例：/Users/berton/miniforge3/envs/pytorch_m4/bin/python
```

### 7.2 Build Phase Run Script

```
#!/bin/zsh -l
CONDA_PYTHON="/Users/berton/miniforge3/envs/pytorch_m4/bin/python"
"$CONDA_PYTHON" "${SRCROOT}/scripts/preprocess.py"
```

### 7.3 App 运行时调用（Swift）

```swift
let pythonPath = "/Users/berton/miniforge3/envs/pytorch_m4/bin/python"
let task = Process()
task.executableURL = URL(fileURLWithPath: pythonPath)
task.arguments = [scriptPath, "--image", "input.jpg"]

var env = ProcessInfo.processInfo.environment
env["PYTHONHOME"] = "/Users/berton/miniforge3/envs/pytorch_m4"
task.environment = env
try? task.run()
```

> [!warning] 分发 App 时不要嵌整个 Conda 环境。正式交付走 **CoreML `.mlpackage` / ONNX Runtime**。

---

## 八、依赖冲突实战：pip 混装警告

日志中出现：

```
ERROR: pip's dependency resolver does not currently take into account...
jupyterlab-server 2.27.3 requires jupyter-server<3,>=1.21, which is not installed.
```

这是 **Jupyter 组件的依赖冲突**，不影响 `ultralytics` / `coremltools` / `torch`。

### 处理方案

**不需要 JupyterLab**（推荐）：

```bash
conda remove jupyterlab jupyterlab-server --force -y 2>/dev/null
pip uninstall jupyterlab-server jupyter-server notebook -y 2>/dev/null
pip check
```

**需要 JupyterLab**：

```bash
pip uninstall jupyterlab jupyterlab-server jupyter-server notebook -y 2>/dev/null
conda install -c conda-forge jupyterlab
```

### 根本避免

- 新建干净 conda 环境
- `conda` 管底层（numpy/scipy），`pip` 只装 PyPI 独有的（ultralytics/coremltools）
- 安装完跑一次 `pip check`

---

## 九、Mac M4 PyTorch GPU 加速专题

> Mac M4（Apple Silicon）**没有 NVIDIA GPU**，无法使用 CUDA。需通过 Apple 的 **Metal Performance Shaders (MPS)** 后端调用 GPU。

### 9.1 核心认知：Mac 上不能用 CUDA

```python
# 在 Mac M4 上这段代码永远为 False
print(torch.cuda.is_available())  # False（正常！Mac 没有 NVIDIA GPU）

# Mac 上应该检查 MPS
print(torch.backends.mps.is_available())  # 应为 True
```

**错误示例**：`AssertionError("Torch not compiled with CUDA enabled")` → 说明代码写了 `.cuda()` 或 `device='cuda'`，需要改为 MPS。

### 9.2 安装支持 MPS 的 PyTorch

```bash
# Conda（推荐）
conda install pytorch::pytorch torchvision torchaudio -c pytorch-nightly

# 或 pip
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cpu
```

> [!important] 系统要求：macOS ≥ 12.3（推荐 13.3+），PyTorch ≥ 2.0。

### 9.3 代码中正确使用 MPS

```python
import torch

# 设备选择
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

# 模型 & 数据全部移到 MPS
model = YourModel().to(device)
inputs = inputs.to(device)
labels = labels.to(device)

# 替换所有 .cuda() / .to('cuda') 为 .to(device)
```

### 9.4 验证脚本

```python
import torch

print(f"PyTorch: {torch.__version__}")          # ≥ 2.0
print(f"MPS available: {torch.backends.mps.is_available()}")   # True
print(f"MPS built: {torch.backends.mps.is_built()}")           # True

# 快速测试
x = torch.randn(3, 3).to("mps")
y = x @ x.t()
print(f"Device: {y.device}")  # mps:0
```

### 9.5 常见问题排查

#### `import torch` 报 `ModuleNotFoundError`

```bash
# 确保环境激活
conda activate pytorch_env

# 检查是否安装
pip list | grep torch
# 或
conda list | grep torch

# 检查 Python 解释器路径
which python  # 应指向 conda 环境
python -c "import platform; print(platform.uname()[4])"  # 应为 arm64
```

#### `Library not loaded: libomp.dylib`

```bash
brew install libomp
```

#### 部分操作不支持 MPS

```python
# 临时回退 CPU
x = x.to("cpu").some_unsupported_op().to("mps")
```

#### Python 架构不匹配（x86 vs ARM）

```bash
python -c "import platform; print(platform.uname()[4])"
# 如果输出不是 arm64，说明安装了 x86 版 Conda
# 需要重新下载 ARM 版 Miniforge：curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh
```

### 9.6 性能优化技巧

#### 内存管理

```python
# 限制显存占用比例
torch.mps.set_per_process_memory_fraction(0.8)

# 精度与速度平衡
torch.backends.mps.matmul_precision = 'medium'

# 每个 epoch 结束清理缓存
torch.mps.empty_cache()
```

#### 混合精度训练

```python
from torch.cuda.amp import GradScaler, autocast

scaler = GradScaler()
with autocast(device_type='mps', dtype=torch.float16):
    outputs = model(inputs)
    loss = criterion(outputs, labels)

scaler.scale(loss).backward()
scaler.step(optimizer)
scaler.update()
```

#### 线程优化

```bash
# 根据 CPU 核心数调整（M4 Pro 有 12-14 核）
export OMP_NUM_THREADS=8
```

#### 性能基准测试

```python
import time

def benchmark(device):
    x = torch.randn(10000, 10000, device=device)
    start = time.time()
    _ = x @ x.t()
    return time.time() - start

print(f"CPU: {benchmark('cpu'):.2f}s")
print(f"MPS: {benchmark('mps'):.2f}s")
# MPS 通常比 CPU 快 5-20x（矩阵运算）
```

> 实测参考：M4 Pro 在 ResNet-50 训练中可达 NVIDIA RTX 3060 约 75% 的性能，适合中小型模型本地训练。

### 9.7 torch.distributed 在 M4 上

Mac M4 不支持 NCCL，需使用 **Gloo**（CPU 多进程）或实验性 **MPS** 后端。

#### Gloo 后端（稳定，CPU 多进程）

```python
import torch
import torch.distributed as dist
import torch.multiprocessing as mp

def train(rank, world_size):
    dist.init_process_group(
        backend="gloo",
        init_method="tcp://127.0.0.1:12345",
        rank=rank,
        world_size=world_size
    )
    tensor = torch.tensor([rank], dtype=torch.float32)
    dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
    print(f"Rank {rank}: {tensor}")
    dist.destroy_process_group()

if __name__ == "__main__":
    world_size = 2
    mp.spawn(train, args=(world_size,), nprocs=world_size)
```

#### 分布式后端对比

| 后端 | 设备 | 功能完整度 | 性能 | 稳定性 |
|:---|:---|:---|:---|:---|
| `gloo` | CPU | 完整 | 低 | **高** |
| `mps` (实验性) | GPU | 部分操作 | 中高 | 中低 |
| `nccl` | GPU | — | — | ❌ Mac 不支持 |

> [!tip] 建议先用 `gloo` 验证功能完整性，再尝试 `mps` 后端探索性能。

### 9.8 Mac M4 安装 Conda 完整流程

```bash
# 1. 下载 ARM 版 Miniforge
curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh

# 2. 安装
chmod +x Miniforge3-MacOSX-arm64.sh
./Miniforge3-MacOSX-arm64.sh
# 按提示：yes 同意协议，yes 初始化 Shell

# 3. 激活
source ~/.zshrc

# 4. 创建 PyTorch 环境
conda create -n pytorch_m4 python=3.10 -y
conda activate pytorch_m4

# 5. 安装 PyTorch（MPS 版）
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cpu

# 6. 验证
python -c "import torch; print(torch.backends.mps.is_available())"
# 输出 True 即成功
```

### 9.9 无法使用 MPS 的替代方案

| 方案 | 说明 |
|:---|:---|
| **CPU 多线程** | `torch.set_num_threads(8)` |
| **云 GPU** | AWS/AutoDL 租用 NVIDIA GPU |
| **Apple MLX** | Apple 专为 Silicon 优化的 DL 框架 |

---

## 十、在 Conda 环境中安装常用工具

### 10.1 安装 JRE（Java 运行环境）

```bash
conda activate your_env
conda install -c conda-forge openjdk

# 验证
java -version
```

若 `/usr/libexec/java_home` 找不到路径（macOS 只识别 `/Library/Java/JavaVirtualMachines/` 下的 JDK），手动设置：

```bash
# 找到真实路径
which java
# 示例输出：/opt/homebrew/opt/openjdk/bin/java

# 设置 JAVA_HOME（去掉末尾 /bin/java）
export JAVA_HOME=/opt/homebrew/opt/openjdk
echo 'export JAVA_HOME=/opt/homebrew/opt/openjdk' >> ~/.zshrc
source ~/.zshrc
```

### 10.2 安装 matplotlib

```bash
conda activate your_env
conda install matplotlib

# macOS 图形不显示时，指定后端
# import matplotlib
# matplotlib.use('macosx')
# import matplotlib.pyplot as plt
```

### 10.3 安装 torchinfo

```bash
pip install torchinfo

# 使用
from torchinfo import summary
summary(model, input_size=(1, 100))
```
