# 依赖与 CUDA 验收记录

范围：`implement.md` 步骤 1。工作分支 `codex/backbone-adapters`，起点 `3bb3a92`。本记录不代表 AC1–AC6 已完成。

## 依赖声明与解析

- 通过 `uv add --frozen` 写入 PRD R1 的 7 项依赖。该命令只修改声明；随后单独执行 `uv lock`。
- `torch` 使用 `pytorch-cu128` 显式索引；源标记为 `sys_platform == 'win32' or sys_platform == 'linux'`。
- `requires-python` 保持 `>=3.13`。首次 `uv lock` 成功，未出现 Python 上限导致的解析错误，未修改现有 Python 约束。
- `uv lock`：退出码 0；命令总耗时 4.17 s；解析 101 个包，解析器报告 4.05 s。锁文件由 uv 生成。

| 包 | 锁定版本 |
| --- | --- |
| torch（Windows / Linux） | 2.11.0+cu128 |
| transformers | 5.17.0 |
| peft | 0.21.0 |
| chronos-forecasting | 2.3.2 |
| granite-tsfm | 0.3.9 |
| scikit-learn | 1.7.2 |
| huggingface-hub | 1.33.0 |

## 安装过程

### 首次 `uv sync`：中断，未完成

- 2026-09-28，America/Chicago（UTC−05:00）。命令已运行至少 10.00 s，工具返回运行中 session 65087。
- 输出包含 `Resolved 101 packages in 1ms`，项目构建完成，torch 下载大小 2.6 GiB。networkx、granite-tsfm、scikit-learn、pandas、transformers、scipy 已报告下载完成。
- 任务被中断后，23:22:16 恢复检查显示 session 65087 已不存在；首次日志最后写入时间为 22:12:24。日志没有完成信息或退出码。完整耗时未知。
- 恢复时 `.venv` 的 Python 为 3.13.11，`importlib.metadata.version('torch')` 报 `PackageNotFoundError`。安装未完成。
- 当前唯一 uv 进程 PID 76324 不执行 `sync` 且命令不指向本项目；未终止该进程。
- 首次日志保留在已忽略的 `cache/backbone-dependency-sync-first.log`；解析日志为 `cache/backbone-dependency-lock-first.log`。

### 重试 1：通过

- 只重试 `uv sync`；没有重复 `uv add`，没有改动依赖范围或索引。
- 解析器复用锁文件：`Resolved 101 packages in 1ms`；继续下载 torch 2.6 GiB。
- 2026-09-28 23:22:33（UTC−05:00）开始，退出码 0，总耗时 533.08 s。torch 准备耗时 8 min 23 s；安装 56 个包，安装阶段 28.97 s。
- 安装报告 hardlink 失败并改用文件复制；警告保留在日志中。安装成功，依赖版本和 CUDA 构建未改变。未设置 `UV_LINK_MODE` 来隐藏该警告。
- 日志：`cache/backbone-dependency-sync-retry1.log`。
- 安装后 `uv pip check` 退出码 0：`Checked 81 packages in 3ms`，`All installed packages are compatible`。

## 已核验的环境信息

| 项目 | 值 |
| --- | --- |
| Python | CPython 3.13.11，MSC v.1944，64 bit AMD64 |
| OS | Windows-11-10.0.26200-SP0 |
| uv | 0.12.19（bea138450，2026-09-24） |
| GPU | NVIDIA GeForce RTX 5090 Laptop GPU |
| 驱动 | 617.14 |
| GPU 总显存 | 24,463 MiB（`nvidia-smi`） |
| torch 报告的设备内存 | 25,622,413,312 bytes |
| torch CUDA runtime | 12.8 |
| `torch.cuda.is_bf16_supported()` | True |
| AC7 环境进程峰值分配显存 | 0 bytes（未分配模型或测试张量） |

锁文件表中的 7 个版本已通过安装环境的 `importlib.metadata.version` 逐一核对，全部一致。

## AC7：通过

本机在 2026-09-28（UTC−05:00）执行以下原定命令：

```powershell
uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_capability())"
```

输出：

```text
2.11.0+cu128 True (12, 0)
```

退出码 0；命令耗时 9.01 s。首次 AC7 执行通过，无失败重测。日志：`cache/backbone-ac7-first.log`。

本步骤仅核验依赖环境。真实检查点未解析，resolved revision 不适用。未执行真实模型预测、微调或 CUDA + bf16 预测；AC5 与 AC6 仍未执行。

## Python 声明边界

- 已安装的 granite-tsfm 0.3.9 元信息为 `Requires-Python: <3.14,>=3.11`。该值通过 `importlib.metadata.metadata('granite-tsfm')` 读取。
- `uv lock` 在现有项目声明 `requires-python = ">=3.13"` 下成功，不能据此认定 Python 3.14 及以上受支持。本机仅验证 Python 3.13.11。
- 首轮项目声明范围包含 granite-tsfm 不支持的 Python 版本。主会话随后批准按父 PRD 的 Python 3.13 目标收窄为 `>=3.13,<3.14`，该修正已实施。
- 修正后 `uv lock` 与 `uv sync` 均退出 0，总耗时 2.11 s；解析 101 个包，实际库版本未变化。日志为 `cache/backbone-python-bound-lock.log` 与 `cache/backbone-python-bound-sync.log`。

## 检查与边界

- `git diff --check -- pyproject.toml uv.lock .trellis/tasks/09-28-backbone-adapters/research/dependency-validation.md` 通过。
- 首轮依赖差异：`pyproject.toml` 新增 15 行；`uv.lock` 新增 1,944 行。Python 上限修正另由 uv 更新锁文件。
- 步骤 1 交接时未启动步骤 2，未执行本子任务 AC1 的四项最终质量检查。后续实施结果见 `implementation-evidence.md`。

## 提交边界

依赖提交仅包含 `pyproject.toml` 与 uv 生成的 `uv.lock`，按执行计划保持可独立回退。验收记录与任务文档由主会话规划提交。本次未提交、归档或推送；未读取数据文件或报告正文。所有诊断日志位于已忽略的 `cache/`。
