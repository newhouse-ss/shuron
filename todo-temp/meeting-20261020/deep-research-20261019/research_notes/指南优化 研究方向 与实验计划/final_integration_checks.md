# 最终整合时的关键更正

父代理在交付算术一致性及主对照可实施性检查中，直接核对以下现有文件。无模型调用，无历史文件修改。

## 57 不是纯子类型错误

`todo-temp/meeting-20261020/error_breakdown_output.txt` Top-4 节明确输出 `label_mismatch_same_span=41`。strict TP629，span-only TP670，差41，与该数一致。

`reproduction/lib/discrepancy.py` 首先按“有重叠且标签不同”配对，因此 label_mismatch57 中 **41 个同跨度异标签，16 个标签和边界同时不同**。boundary_mismatch45 是同标签异跨度。

现有 `error_breakdown.py` 的 `label mismatch fixed` 模拟将整个预测答案替换成 gold，既修标签也修跨度。故0.8750不是只改子类型可达到的上界；它是修复这57个混合错误对的场景。冻结已有跨度、理想纠正类型的对应参考为 span-only0.8546，注意这仍不是实际模型保证。报告应拆41/16/45，而非“类型错误独占最大损失57”。21对21混淆也不保证都在相同跨度上。

## Rewriter 看见的是不完整的正例证据

`src/llm_guideline_moderation/iterative.py:383` `_build_true_positive_examples` 用 gold/pred 严格相等取 matched，给出全文及 `MATCHED ANNOTATIONS`，每篇最多5条，共前5篇至少有一个TP的文档。`_build_verified_examples`复用该函数。

所以不能笼统说“给全部旧预测，且writer从未见任何gold信息”。准确表述为：**writer已见由gold核验的部分TP，未见完整gold，也未见目标漏标的gold；列表既不是完整gold，也不是完整prediction。**没有列出某个短语，可能因为漏标，也可能因为每篇5条截断，甚至本来是正确预测。

`src/llm_guideline_moderation/prompts.py:96` 把examples统称为正确处理。最小主对照可只改保护承诺的作用域，保留全文、TP列表、文档、原则、模型、token及生成预算。

用户反对“直接给gold”的默认解释应是**不新增目标错误的逐项gold给writer**，保留原方法既有的已核验TP。若用户连现有TP也禁止，应重新定义实验，不能声称原基线已经符合“任何实体级gold都不可见”。整个方法仍用开发gold分析，不能叫gold-free。

## 交付稿主对照收窄

只修改保护承诺，不同时动态选择例子、换模型、加gold或加reviewer。按错误选例、最小patch或抽象checker是候选替代主线，不与主对照打包。对追求全局F1的价值保持条件性，已知局部错误字符串不在valid不能保证增益。先补现存轨迹，再做小机制试验，过门后才做两臂独立轨迹，不把所有阶段总调用变成已批准任务。

## 文献回执已核实

public base Table1 .46/.73/.76为三种条件F1；GPTNER GENIA64.06/64.29/64.42来自全文Table3；GuideNER去验证62.80来自全文Table2。先前source代理把base三值写成P/R/F1的笔误已在回执更正。

## 模型批次

Top1 validation是8月，Top4 validation是10月，使用同名GPT-5.4部署不能称同期同批。表中可同列历史观测，但正式方法对照需要尽可能同期同配置；版本未记录应保留未知。
