# OPRO: Large Language Models as Optimizers

本项目用于复现论文 **Large Language Models as Optimizers**（OPRO）中的线性回归、旅行商问题（TSP）和提示词优化实验。

代码、benchmark 数据及提示词历史来自 Google DeepMind 官方仓库 [google-deepmind/opro](https://github.com/google-deepmind/opro)，对应提交 `a76bdce2cbf6d4a0d1e570a6fcfe17be9c2abdd7`。本仓库补充了 `uv` 环境管理、复现约束和中文使用说明。

> 注意：官方代码使用 2023 年的 PaLM/text-bison 和旧版 OpenAI 接口。仓库当前保留原始调用方式，尚未迁移到新的模型 API；运行前需确认账号仍能访问相应模型，或先适配 `opro/prompt_utils.py`。

## 环境要求

- Python 3.10
- [uv](https://docs.astral.sh/uv/)
- 可访问的 optimizer/scorer LLM API

## 快速开始

```bash
git clone https://github.com/hhgzeng/OPRO.git
cd OPRO

# 按 uv.lock 创建 .venv 并安装依赖
uv sync --frozen

# 运行官方测试
uv run pytest
```

当前验证结果：Python `3.10.22`，`uv sync --frozen` 通过，测试 **45/45 通过**。

## 仓库结构

```text
.
├── AGENTS.md                  # 智能体复现行为与实验约束
├── OPRO.md                    # 论文正文及附录
├── README.md                  # 本文件
├── LICENSE                    # Apache-2.0
├── pyproject.toml             # 项目与依赖配置
├── uv.lock                    # 锁定后的完整依赖
├── .python-version            # Python 3.10
│
├── opro/
│   ├── prompt_utils.py        # LLM API 调用封装
│   ├── optimization/
│   │   ├── opt_utils.py       # OPRO 核心优化循环与元提示词
│   │   ├── optimize_linear_regression.py
│   │   ├── optimize_tsp.py
│   │   └── optimize_instructions.py
│   └── evaluation/
│       ├── metrics.py         # 准确率与文本匹配指标
│       ├── eval_utils.py      # 数据读取、答案提取和评测工具
│       ├── eval_utils_test.py # 官方单元测试
│       └── evaluate_instructions.py
│
├── data/
│   ├── gsm_data/              # GSM8K train/test TSV
│   ├── BIG-Bench-Hard-data/   # 27 个 BBH 任务 JSON
│   ├── MMLU-data/test/        # 57 个 MMLU 测试集 CSV
│   ├── AQuA-data/             # AQuA 数据
│   ├── MultiArith-data/       # MultiArith 数据
│   └── README.md              # 官方数据来源说明
│
└── misc/
    └── prompt_history/        # 23 个 BBH 任务的官方提示词优化历史
```

运行实验后还会生成 `outputs/`，其中包含优化结果和评分器输出；该目录已被 `.gitignore` 排除。

## 数据说明

### `data/`

`data/` 是运行 benchmark 实验所需的数据，不是可选示例。官方脚本会根据 `--dataset` 直接读取这里的相对路径。

| 目录 | 内容 | 用途 |
| --- | --- | --- |
| `gsm_data/` | `gsm_train.tsv`（7473 条）、`gsm_test.tsv`（1319 条） | GSM8K 提示词优化与测试 |
| `BIG-Bench-Hard-data/` | 27 个 BBH 任务 JSON | BBH 提示词优化与测试 |
| `MMLU-data/test/` | 57 个 MMLU 测试集 CSV | 官方代码支持的扩展评测；论文未报告 MMLU 主结果 |
| `AQuA-data/` | `AQuA.json` | GSM8K 指令迁移评测 |
| `MultiArith-data/` | `MultiArith.json` | GSM8K 指令迁移评测 |

数据总大小约 **13.5 MiB**。各 benchmark 的版权归原始数据集作者所有，来源见 `data/README.md`。

### `misc/prompt_history/`

该目录保存官方在 BBH 上使用 `text-bison` 作为 scorer、`PaLM 2-L-IT` 作为 optimizer 的提示词优化历史，共 **23 个任务、约 7.9 MiB**。

文件命名为：

```text
BBH-<task>-s-text-bison-o-palm-2-l-it.txt
```

每行记录一步候选指令及其训练准确率，例如：

```text
Step 4, training acc: 0.780, instruction: Find a movie similar to the following movies:
```

该目录**不被运行代码导入**，属于可选的实验档案，用于检查优化轨迹、复现附录图表和对照论文找到的指令。保留它可以避免以后重新调用 API 才能查看原始轨迹。

## 运行实验

以下命令展示官方入口。API Key 不要写入代码或提交到 Git；示例先从终端读入环境变量。

```bash
read -rsp "OpenAI API key: " OPENAI_API_KEY; echo
export OPENAI_API_KEY

read -rsp "PaLM API key: " PALM_API_KEY; echo
export PALM_API_KEY
```

> 官方脚本仍通过命令行参数接收密钥。如果只使用 OpenAI 模型，可以不提供 PaLM Key；如果只使用 text-bison，可以不提供 OpenAI Key。

### 1. 线性回归

```bash
uv run python opro/optimization/optimize_linear_regression.py \
  --optimizer="gpt-4" \
  --openai_api_key="$OPENAI_API_KEY"
```

结果写入 `outputs/optimization-results/linear_regression-o-<model>-<time>/`。

### 2. 旅行商问题

```bash
uv run python opro/optimization/optimize_tsp.py \
  --optimizer="gpt-4" \
  --starting_algorithm="farthest_insertion" \
  --openai_api_key="$OPENAI_API_KEY"
```

结果写入 `outputs/optimization-results/tsp-o-<model>-<time>/`。

### 3. GSM8K 提示词优化

```bash
uv run python opro/optimization/optimize_instructions.py \
  --optimizer="gpt-3.5-turbo" \
  --scorer="text-bison" \
  --instruction_pos="Q_begin" \
  --dataset="gsm8k" \
  --task="train" \
  --openai_api_key="$OPENAI_API_KEY" \
  --palm_api_key="$PALM_API_KEY"
```

结果写入 `outputs/optimization-results/GSM8K-train-s-<scorer>-o-<optimizer>-<time>/`。

### 4. 在测试集上评估指令

待评估指令列表位于 `opro/evaluation/evaluate_instructions.py` 的 `instructions_to_evaluate` 变量中。编辑该列表后运行：

```bash
uv run python opro/evaluation/evaluate_instructions.py \
  --scorer="text-bison" \
  --dataset="gsm8k" \
  --task="test" \
  --instruction_pos="Q_begin" \
  --evaluate_training_fold=false \
  --evaluate_test_fold=true \
  --palm_api_key="$PALM_API_KEY"
```

评分结果写入 `outputs/scorer-outputs/`。

### 5. BBH 提示词优化

将 `--dataset` 改为 `bbh`，并通过 `--task` 指定任务名，例如：

```bash
uv run python opro/optimization/optimize_instructions.py \
  --optimizer="gpt-3.5-turbo" \
  --scorer="text-bison" \
  --instruction_pos="Q_begin" \
  --dataset="bbh" \
  --task="movie_recommendation" \
  --openai_api_key="$OPENAI_API_KEY" \
  --palm_api_key="$PALM_API_KEY"
```

可用的 BBH 任务名对应 `data/BIG-Bench-Hard-data/*.json` 的文件名。

## 关键配置

官方脚本没有单独的配置文件，部分实验参数直接写在入口脚本中：

- `optimize_instructions.py`：`initial_instructions`、`train_ratio`、每步候选数等。
- `optimize_linear_regression.py`：真实参数、数据点数量、初始点、最大步数等。
- `optimize_tsp.py`：节点数、初始解数量、每步候选数和起点算法等。

修改配置时，应同时记录到独立的运行目录或实验日志中。复现实验必须固定数据划分和随机种子，且不能在优化阶段使用测试集分数。

## 测试

```bash
uv run pytest
```

本次对官方源码只做了必要的工程修正：

- 将 `instruction_to_filename` 测试显式设置为 `md5_hashing=False`，使测试与当前实现一致。
- 清理 4 处行尾空格。

OPRO 的算法逻辑未改动。

## 复现顺序

1. 线性回归，验证连续黑盒优化闭环。
2. TSP，验证离散组合优化。
3. GSM8K，复现提示词优化主实验。
4. BBH，先运行单个任务，再扩展到完整任务集。
5. 指令迁移、元提示词排序和每步候选数消融实验。

详细约束见 [AGENTS.md](AGENTS.md)。

## 上游与许可

- 论文：[Large Language Models as Optimizers](https://arxiv.org/abs/2309.03409)
- 官方代码：[google-deepmind/opro](https://github.com/google-deepmind/opro)
- 代码许可：Apache License 2.0，见 [LICENSE](LICENSE)

官方仓库声明该项目不是 Google 官方支持的产品。benchmark 数据的版权归各原始数据集作者所有。
