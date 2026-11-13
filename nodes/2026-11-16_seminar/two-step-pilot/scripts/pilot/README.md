# 两步标注试跑代码

实现依据为 `../../notes/20261113_codex_pilot_spec.md` 和同目录设计文档。三段说明逐字保留；原有 `src/` 和 `reproduction/` 文件没有修改。

在仓库根目录运行以下命令。离线入口不读取 `.env` 或其他凭据文件，不创建 API 客户端。

```powershell
python -B nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot/run_pilot.py dry-run
python -B nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot/offline_checks.py
```

检查结果保存到 `../../outputs/pilot_offline_checks_output.txt`。检查期间禁止网络连接和 heldout 训练文档读取。原有复现测试在假 API 上运行，其中原有验证集评分测试保留其现成的离线测试数据。临时文件均在本节点 `outputs/` 下，Windows 上继承工作区目录权限。

## 付费运行，尚未执行

仅在用户批准、管理员已收到通知，并且环境中已设置 `ANTHROPIC_API_KEY` 后执行。以下命令启动脱离当前终端的后台进程，日志写入运行目录的 `runner.log`。同一命令恢复同一目录；不要同时启动两个进程操作同一运行目录。

```powershell
python -B nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot/run_pilot.py run --detach --yes --administrator-notified --output-root outputs/ncbi_disease/20261113_haiku-xhigh_pilot_twostep
```

最多 1,600 个原定调用，重试可能增加实际请求数。按每次 JPY 0.634 估算为 JPY 1,014.40，不设花费上限。模型、思考设置、输出上限、BatchQueue、QueueProvider 和最多三次尝试均沿用复现运行器。脚本直接使用环境中的密钥，不加载 `.env`。

提交前保存 manifest，包括 487 篇池的排序文件名、哈希、100 篇正式实验保留文档、200 篇试跑文档，以及指南、schema 和提示的哈希。哈希编码方式写在 manifest 内。恢复时输入必须一致。

每组每次分别保存：`raw_replies/`、`track1_predictions/`、`track2_predictions/`、逐文档状态、`usage.json`。原始 API 消息及全部成功返回的尝试位于 `_batchqueue/replies/`，调用记录通过路径和 ID 引用它们。T 第一步没有候选时跳过第二步。第二步失败或漏判时保留全部第一步候选，Track 1 不收录未定候选，并累计未定数。

## 付费运行完成后的离线评分

以下命令也尚未执行。分析目录必须是新目录。

```powershell
python -B nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot/score_pilot.py --run-root outputs/ncbi_disease/20261113_haiku-xhigh_pilot_twostep --report-dir nodes/2026-11-16_seminar/two-step-pilot/outputs/20261113_pilot_scores
```

评分只读取试跑训练文档。严格 F1 用临时目录中恰好这 200 篇 gold 调用现有评分器。主比较先按文档取两次真正漏标均值，再对 200 篇文档配对重抽样 10,000 次，固定种子 20261113。区间为双侧 95% 百分位区间，分位点用线性插值。两个差值区间上界均小于 0 才通过。

评分保存各组各次的 `metrics.json` 及分析目录中的汇总 `metrics.json`，包含多标、类型别真正漏标、严格 F1、未定数和各次调用的 usage、费用。超过 5% 调用重试后不可用时输出 `inconclusive` 并列出调用。若任何文档缺少必要预测，也输出 `inconclusive`，不把缺失文件当成空预测或缩小 200 篇的比较范围。T 第二步失败仍有完整 Track 2，可在不可用比例不超过 5% 时按设计计算主比较。
