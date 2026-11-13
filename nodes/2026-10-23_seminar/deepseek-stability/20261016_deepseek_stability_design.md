# 实验设计：DeepSeek 标注稳定性（未运行）

2026-10-16。目的：切换到 DeepSeek 之前，先测出它在同一输入下每次输出差多少，作为后续所有比较的噪声带。准确率实验（valid100）在本实验之后做。

## 1. 已有证据

**8 月的温度对照**（`logs/ncbi_disease/temp-*.log`，dev10，原指南，每组 5 次）：

| 组 | 模型与设置 | dev10 F1（5 次） | 均值 | 样本标准差 |
| --- | --- | --- | --- | --- |
| B1 | deepseek-v4-flash，temperature 0 | 0.8286 0.7647 0.8286 0.8058 0.8088 | 0.8073 | 0.0261 |
| B2 | deepseek-v4-flash，temperature 默认 | 0.7770 0.7914 0.7971 0.7591 0.7794 | 0.7808 | 0.0147 |
| A1 | Azure 4o，temperature 0 | 0.3597 0.3609 0.3611 0.3556 0.3876 | 0.3650 | 0.0128 |
| A2 | Azure 4o，temperature 默认 | 0.4127 0.3433 0.3307 0.3485 0.3566 | 0.3584 | 0.0318 |
| 参照 | GPT-5.4 high（`reproduction/results/size_noise`） | 0.8028 0.8085 0.8252 0.7832 0.8028 | 0.8045 | 0.0150 |

读法：

- temperature 0 没有让 DeepSeek 更稳定，B1 的标准差反而比 B2 大。不过每组只有 5 次，两个标准差要差到大约 3 倍，才能在 5% 水平上分开，所以准确的说法是"没有看到 temperature 0 的好处"。
- DeepSeek 默认设置的波动和 GPT-5.4 high 处在同一水平。
- **记录缺口**：
  - 脚本没有发送任何 thinking 开关（日志里的 `effort=none` 指的是没有发送这个参数），也没有记录推理 token。所以"B1 关闭了 thinking"这一点，在保存的记录里无法确认。
  - 逐条预测的缓存当时写在旧路径 `C:\git\shuron\experiments\...` 下，现在的仓库里没有，只剩日志里的 F1。
  - 模型 ID 当时是 `deepseek-v4-flash`。官方价格页（2026-10-16 读取）写明：推荐的模型名是 `deepseek-flash`；旧名 `deepseek-v4-flash` 仍然可用，但现在由 DeepSeek-V4.1-Flash 提供服务。所以 8 月的结果属于更早的版本，不能直接当作 V4.1 的噪声带，这也是要重新测的原因之一。

**GPT-5.4 的逐条预测稳定性**（`gpt54_reference.py`，离线计算）：dev10 上 5 次重复共出现 73 条不同的预测，其中 63 条（86.3%）在 5 次里都出现；任意两次之间平均有 5 条预测不同。

## 2. 问题

在明确设定 thinking 开关的前提下，DeepSeek 的波动有多大？逐条预测层面是否和 GPT-5.4 相当？后续实验应当用哪种设置？

本实验的目的是测出波动有多大，不是找一个完全确定的设置。你已经验证过，即使 temperature 0 且关闭 thinking，也不能保证每次输出都相同。

## 3. 设计

**固定项**：

- dev10，与 08/02 run 及 GPT-5.4 size_noise 的 10 篇相同，共 74 个 gold。
- 原指南，即 `inputs/initial_guidelines.txt`，7,367 字符。
- `annotate_with_guidelines` 模板，instructions 为空，输出配置含 rationale 和 guideline section。
- 每篇文档单独调用，用 loop 的集合评分。

**组别**：

| 组 | thinking | temperature | 次数 |
| --- | --- | --- | --- |
| A | 关 | 0 | 5 × 10 篇 = 50 |
| B | 开 | 不设置（thinking 模式下可能被忽略，以官方文档为准） | 5 × 10 篇 = 50 |

**先做一次小探针**，每组用 10577908 标 2 次，共 4 次调用。确认三件事：

1. thinking 开关真的生效，看推理 token 是否为 0。
2. 响应里的 `model` 字段，用来记下实际版本。
3. 每次调用的 token 用量，用来推算正式实验的总量。

探针结果给你看过、你确认之后，再跑正式的 100 次。

**每次调用都保存**：完整的原始响应文本、`model` 字段、usage（包括推理 token）、开始和结束时间。

## 4. 指标

1. 每次重复的 dev10 F1 和 5 次的样本标准差。
2. 逐条预测稳定性：5 次里出现过的不同预测中，5 次都出现的比例；任意两次之间平均有多少条预测不同。
3. 附带记录：FALDH、norrin、G6PD、PAH、Tay-Sachs 这几个案例在每次重复中的标签。它们的文档都在 dev10 里，不需要额外调用。

## 5. 判读

- 每组的结果作为该设置的噪声带。以后用 DeepSeek 时，一轮 dev F1 的变化小于约 2 倍标准差，就不算真实变化；单个案例的变化，要重复确认后才能归因于规则。
- 给准确率实验选设置时，先比较逐条预测稳定性，稳定性相近再比较 F1 均值，仍然相近就选更便宜的那组。
- 和 GPT-5.4 并列报告。除非差别很大（比如标准差差到 3 倍左右），否则不说"更稳定"或"更不稳定"。

## 6. 前置工作

- 查 DeepSeek 官方文档，确认 thinking 开关的参数名，以及 thinking 模式下是否接受 temperature。模型名已确认为 `deepseek-flash`（官方价格页，2026-10-16）。
- 设置输出上限（建议与 GPT-5.4 相同的 64000），这样每次调用的费用有硬上限。官方页写的最大输出是 384K。
- 在非高峰时段运行。高峰为工作日 UTC 01:00 至 04:00 和 06:00 至 10:00，即日本时间 10:00 至 13:00 和 15:00 至 19:00，价格是非高峰的 2 倍。
- 修改 provider：明确发送 thinking 开关；每次调用后保存 `model` 和 usage。现有的 `providers/deepseek.py` 和 `probe_size_noise.py` 都不做这两件事。
- 由你本人把 `DEEPSEEK_API_KEY` 写进 `.env`。
- 和管理员确认，DeepSeek 的费用可以走研究室报销。

## 7. 用量

当前模型的 token 用量没有任何保存的记录。8 月的日志只有耗时（每篇 46 至 489 秒）。正式实验的用量，用探针的实测值推算之后再报给你。

探针之前的粗估见 `cost_estimate.py` 和 `cost_estimate_output.txt`：本实验 104 次调用，按非高峰价格合计约 120 至 190 日元。几乎全部来自 B 组，这部分按"思考长度与 GPT-5.4 high 相当"的假设计算；A 组只有几日元。这些是假设下的估计，不是测量。

## 核查记录

- 8 月数据：`logs/ncbi_disease/temp-{A1_4o_temp0,A2_4o_default,B1_ds_temp0-resume,B2_ds_default-resume2}.log` 末尾的汇总表；设置取自 `temp-B1_ds_temp0.log` 和 `temp-B2_ds_default.log` 的第 1 行。均值和标准差由日志里的 5 个 F1 重新计算，与日志里的 SD 一致。
- thinking 开关：`reproduction/probe_size_noise.py` 只有在 `--reasoning-effort` 不为 none 时才发送 `reasoning_effort`，没有其他 thinking 参数。
- GPT-5.4 参照：`nodes/2026-10-23_seminar/deepseek-stability/gpt54_reference.py`，输出在 `gpt54_reference_output.txt`。dev10 划分与 08/02 run 的 10 篇相同（脚本断言为 True）。
- 本文件只是设计，没有调用 API。
