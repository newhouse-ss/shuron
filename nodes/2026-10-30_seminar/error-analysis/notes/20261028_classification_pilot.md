# 错误分类：修订编码规则、30 例复码与 14 个新例（v2）

**版本记录**
- v1，2026-10-28：分类初稿六类，30 例试编码。原文保留在本文末尾。
- v2，2026-10-28（同日第二版）：统一编码对象，按同一规则复码 30 例，用 14 个新例检查修订后的定义，撤回或降级若干 v1 结论，更正统计口径。
- v2.1，2026-10-29：四处更正，见下文；五个类别改作当前的工作索引，用于组织结果，不代表错误机制。实际分析见 `20261029_modifier_context_analysis.md`。

**v2.1 更正（2026-10-29）**

1. **P12 撤回"条文竞争"。** top-4 loop08 第 98 至 105 行都属于第 8 条。第 8 条只在名词短语作"表征疾病的谓语"（is characterized by 等）的补足语时适用；第 104 行（mental retardation 为 DiseaseClass）和第 105 行（作主语的不标）都是它的"适用条件"。P12 中 "mental retardation is not severe" 的 mental retardation 是主语，第 8 条整体不适用，两行并不在同一情形下给出相反要求。该指南第 206 行保留了 Example 11，并注明 "(see item 8)"。按这个交叉引用合读，作主语的 mental retardation 要求不标，与预测（漏标）一致、与 gold 相反。这是类推，记为"适用不明"。
2. **N11 的结构记错了。** 原始预测中，局部 gold 有两个：Duarte and Los Angeles variant galactosemia（Composite）和 Duarte enzyme variant of galactosemia（Specific）。30 次运行里，18 次完全正确；9 次只标 galactosemia（Specific）；E1 run09、run10 两次把一个 gold 切成两个预测，Duarte 为 Modifier、galactosemia 为 Specific；1 次标 galactosemia 为 DiseaseClass。这是"一个 gold 被两个预测切开"，不只是前缀边界问题。今后凡是一对多、多对一或重叠的情形，案例视图都列出局部的全部 gold 和全部预测。
3. **N04 不算定义失效。** 允许多标签时，同时触发"提及资格"和"修饰角色"只是维度重叠，不是赋码越界，也不是无法判断。v2 把 A4 收窄为只含动物突变体、基因型、基因座名，这一修改撤回，"符号与基因名同形"仍可同时记入 A4 和 B1。
4. **撤回"都是公认疾病，Dmpk 缺乏不是"这一解释。** 它依据的是我对疾病的一般了解，没有与标注政策相连的证据。X-deficient 的标注差异改为未决：既不说 gold 不一致，也不说有语义解释。

**工作索引的用法。** 三项分开记：原文涉及哪些标注判断；预测有什么可观察的差异；指南文字提出什么要求。例如 gold Modifier 被漏标，记为"修饰语境中的漏标"，不推断为模型的修饰角色判断失败，因为也可能是没有识别出疾病名或漏抽取。保留"其他、未覆盖、未决"。

这是探索性分析：类别在看过 10/24 报告、多轮审阅和 v1 的 30 例之后形成，同一编码者先看文本再看预测，不构成独立盲评。离线进行，没有调用 API，没有读测试文档的 gold 和 .env，没有改原始预测或实验输出。

## 结论

- **v1 的赋码不一致。** 30 例中有 13 例的判断标签与统一规则不符，多是漏编了"具体还是类别"和"并列切分"，原因是 v1 按看到的错误挑标签。v2 把类别定为对每个提及都检查的决策维度，只在原文和 gold 满足触发条件时赋码。
- **新例只部分支持修订后的定义。** 14 个新例中有 2 例使定义失效（缩写与基因中心词重复触发；限定词定义覆盖不了 "X of Y" 前缀），所以 v2 规则不能算已验证。
- **一些结论撤回或降级。** 撤回两项"gold 内部不一致"（另一项改为未决）、P19 的"规范冲突"、四项"波动"归类；"新条文的字面范围决定翻转"降为部分一致、有反例；"已有条文仍错"降为候选模式。
- **保留的结论。** P12 在 top-4 loop08 中两条明文条文竞争；原指南的 Modifier 规则与 Composite 例子在 P05、P22 上竞争，没有优先规则；P30 的陈述首次出现记录。
- **可扩展程度。** 修饰角色和并列切分可以用字符串条件初筛；限定词、提及资格、具体还是类别还需要先澄清定义。

## 1. 编码规则（v2）

编码对象分三种，分开记录：

1. 一个提及涉及哪些标注判断：只看原文和 gold（多标只看预测跨度本身的文字），不随预测改变；
2. 某次预测错在哪个判断：看预测；
3. 指定指南中的指定条文，对这个实例提出什么要求：按"提及 × 指南 × 条文"一行一条记录。

**五个类别都是决策维度，不是只针对特定表达的语言类别。** 每个提及都对照全部五类检查，满足触发条件才赋码，允许多标签。这样赋码规则对所有提及相同，与模型标对还是标错无关。v1 的"临床表现"和"非疾病指称"合并为提及资格，因为二者是同一个决定（标不标），区别记为子类。

| 类别 | 触发（纳入） | 排除 | 未决 |
| --- | --- | --- | --- |
| A 提及资格（标不标） | A1 体征、症状、器官病变或表现词；A2 可读作生物或病理过程；A3 中心词是泛称（disease、disorder、deficiency、symptoms、changes、manifestations 等，带或不带修饰语）；A4 动物突变体名、基因型描述、没有中心名词的基因座名 | 具名疾病及其公认缩写 | 一个词既可读作具名疾病又可读作表现（atrophy）；表现与过程之间（metastasis） |
| B 修饰角色 | B1 疾病词（含缩写、人名词）直接位于不指疾病的名词前，可隔一个括号缩写；属性记中心名词、是否隔括号、符号是否与基因名同形、是否人名词。B2 疾病短语作关系名词的补足语：risk of/for、history of、case(s) of、patients/carriers/families/individuals with、frequency/incidence/prevalence of | 后面是疾病中心词、合起来构成病名；不在列表中的关系（百分比 of、causes of） | 后面只有数字（基因座名）；两张列表是否完整 |
| C 具体还是类别 | 只对 gold 为 Specific 或 DiseaseClass 的提及检查。C1 已标注的 A1 或 A3；C2 中心词为 cancer、tumor、carcinoma，或为复数；C3 跨度内有 D 类限定词；C4 句子陈述疾病的人群性质（risk、frequency、proportion、cases of） | 单数具名疾病且不满足以上条件 | C4 需要语义判断 |
| D 限定词与跨度 | 跨度首词或紧邻跨度之前是：familial、hereditary、inherited、sporadic；adult、adult onset、childhood、juvenile、early-onset；severe、mild；classical、classic；stage N；primary、congenital、genetic | 公认病名的一部分（familial Mediterranean fever）；解剖或组织学修饰（renal cell、globoid cell） | "X of Y" 前缀（forms of、variant of）；描述性修饰（fibre-type dependent）；genetic 是限定词还是类名的一部分 |
| E 并列切分 | 跨度内有 and、or、逗号或斜线；或该提及与另一疾病词以并列相连；或并列的修饰语共享一个疾病中心词 | 并列项都不是疾病词或其修饰语 | 并列中隔着数词 |

**"错在哪个判断"的对照：**
- 漏标记为 A（若 A 已触发）或 B（gold 为 Modifier）；
- Specific 与 DiseaseClass 互换记为 C；
- 涉及 Modifier 的标签错记为 B；
- Composite 与其他标签之间记为 E，Modifier 与 Composite 之间记为 B×E；
- 边界差在限定词记为 D，差在并列范围记为 E，其他记为"其他边界"。

**条文评价分五项记录：**
- 适用性：适用、不适用、适用不明；
- 与 gold 的一致性：一致、相反、不涉及；
- 与其他条文的关系：单独、竞争、有例外；
- 证据：明文、类推、未定；
- 查找程度：通读、关键词检索、未查。

"确认无适用条文"只用于通读过的指南，目前只有原指南。修改后指南都只做过关键词检索，没找到时记"检索未找到"，没有检索过的记"未查"。

## 2. 复码 30 例：13 例的判断标签改了

v1 的问题是按每例看到的错误挑选相关标签，没有对每个提及逐类检查。v2 用第 1 节的触发条件逐例重查，结果见 `outputs/pilot_recoding_v2.csv`，旧判断和修改理由都保留。

**P03 为什么没有编"句法角色"：** v1 已写明 classical galactosemia 后接 alleles，却只按"边界错"编了限定词。这是 v1 的遗漏，v2 补编 B1。

**P19 有"具体还是类别"，P12、P16 没有：** v1 没有统一条件，只在 gold 标签看起来特殊时才编。v2 按 C1（已标注的表现词都检查 C），三例都编 C。

| 例 | v1 | v2 新增 | 依据 |
| --- | --- | --- | --- |
| P01 | 临床表现 | C | C1 |
| P03 | 限定词 | B | B1（后接 alleles） |
| P04 | 限定词 | A、C | A3（中心词 disease）、C1 |
| P07 | 并列 | A、C | A3、C1 |
| P11 | 句法角色 | C | C2、C4 |
| P12 | 临床表现 | C | C1 |
| P14 | 并列 | C | C2（复数） |
| P16 | 临床表现 | C、E | C1；三项并列列表 |
| P19 | 临床表现、具体还是类别 | E | 四项并列列表 |
| P25 | 非疾病指称 | B | B1（后接 tissue samples） |
| P27 | 临床表现 | E | 两项并列 |
| P28 | 非疾病指称 | B | B1（隔括号后接 mice） |
| P30 | 句法角色 | C | C2 |

另有 P09、P20 只是把"符号与基因同形""人名词"改记为 B 的属性，P24、P26 只是类别改名，判断本身没有变。

## 3. 重新审查规范冲突与 gold 不一致：多数降为未决

每项都列出原文、适用条件和推论，区分明文、类推和未定。逐条条文评价见 `outputs/pilot_clause_eval_v2.csv`。

1. **Example 11 能否推出 atrophy 应标 DiseaseClass（P19）。** 原文是 "These are 'grey area' terms: they may not correspond to a single Specific Disease, so they are annotated as Disease Class category if appropriate"，点名的是 convulsive disorders、motor retardation、mental retardation。may not 和 if appropriate 都是保留措辞，atrophy 没有被点名，推到 atrophy 只是类推。P19 不再记为规范冲突，改为未决。
2. **不同表现词标签不同，是否违反同一判定条件（P19 对 P12、P16）。** 原指南第 7、8 行的定义是：DiseaseClass 指可以描述为一族具体疾病的提及，Specific 指能对应一个不再细分的定义。cataract、atrophy 可以读成单一概念，mental retardation、cerebellar degeneration 可以读成一族，用同一个定义能分别解释这些标签。没有证据表明 gold 违反了同一条件，撤回"gold 内部不一致"。
3. **Dmpk deficient 与其他 X-deficient（P28）。** 验证集 gold 标 Modifier 的 PAH、C9、G6PD、HPRT、Atm 缺乏，按我对这些疾病的了解都对应公认疾病：苯丙酮尿症一类、C9 缺乏症、G6PD 缺乏症、Lesch-Nyhan 综合征、共济失调毛细血管扩张症。Dmpk 缺乏不是公认疾病，强直性肌营养不良由重复序列扩增引起。差别可以用语义解释，撤回"gold 不一致"。**限定词边界（P04 对 P06、P10）：** P04 是两个限定词连用、处在 "form of" 结构里，P06、P10 是单个限定词，语境差别没有排除，改为未决。
4. **P01 能否算明确的规范冲突。** 原文 "may regulate tumor cell invasion and metastasis through interactions at focal adhesions" 中，metastasis 与 invasion 并列、作 regulate 的宾语，读成过程说得通，读成病理结局也说得通。含义未定，不能计入明确冲突，改为疑似。
5. **"拆开不丢信息就必须分开"是不是明文（P07、P14）。** What to Annotate 2 原文只说一个字符串可能指两个以上疾病，这时标 Composite；Duchenne 例子说明拆开会丢信息时不拆。"不丢信息就必须拆"是从例子反推的，属于类推。P07、P14 的条文状况改为"类推适用、与 gold 一致"。
6. **P03 保留为疑似冲突，证据较强。** Example 15 明文写 Classical galactosemia "includes classical"，但例子没有限定语境，P03 处在修饰位置，gold 只标 galactosemia。修饰位置是否另有惯例，现有材料判断不了。

## 4. 撤回、降级和保留

| v1 的发现 | v2 的处理 | 理由 |
| --- | --- | --- |
| 已有适用且与 gold 一致的条文，预测仍错（P02、P07、P09、P20、P21） | 降为候选模式 | 明文条文只有 P09（以 VHL 是疾病缩写为前提）和 P21（明文例子，但这里隔着括号）；P02 只有通用条文；P07 是类推；P20 的前提未定。新例 N09 也属类推 |
| 新条文的字面范围与翻转对得上（P11，11 份中 9 份一致） | 降为部分一致、有反例 | P11 中三份条文的适用性改为"不明"（类推）。新例 N02 中，loop07、loop10 的条文字面适用却标对，loop06 字面不适用却标错 |
| 规范与 gold 冲突（P01、P03、P19） | P03 疑似（较强），P01 疑似，P19 撤回 | 见第 3 节 |
| gold 自身不一致（表现词标签、X-deficient、限定词） | 前两项撤回，第三项未决 | 见第 3 节 |
| 条文竞争（P05、P12、P22、P27） | P12、P05、P22 保留；P27 降为类推 | P12：loop08 的两条都是明文。P05、P22：原指南明文 Modifier 规则与明文 Composite 例子都适用，没有优先规则 |
| 没有条文的多标（P24、P25、P28） | 保留，但限定查找范围 | 原指南通读，确认没有；修改后指南只检索了 4 份，其余 7 份未查 |
| 翻转在波动范围内、不需要条文解释（P14、P16、P27、P29） | 撤回，改为尚未解释 | 19 次原指南重复与 11 份不同指南比较，频数相近不能区分波动与指南影响。P29 只核对了关键词相关的条文，没有比较候选与改写前的全部差异 |
| P30：家族史 Modifier 陈述第一次出现在候选指南 | 保留 | 已核对该轮分析输出、原则和候选指南：前两者没有提到 Modifier 或家族史，候选第 53 行出现 |

**统计口径的更正**（都已写进 `pilot_cases_output.txt`）：
- **开发集退化：** 114 个"提及 × 轮"来自全部 18 个被拒轮次。9 个第一轮就被拒的循环只贡献其中 77 个；v1 写成"9 个循环第一次改写被拒时的 114 个"，是错的。
- **368 个不在任何层的提及**，条件是原指南至少 15 次标对、修改后至多 1 份标错，不等于始终正确。30 次全对的是 256 个。
- **预测侧的未配对重叠** v1 漏了：37 行，8 个不同的预测，不在 89 个多标之内。
- **层名只是条件的简称。** "改善"层不保证修改后标对的比例更高，103 个中有 1 个不升；"退化"层 100 个都下降。下文用条件描述代替这两个名称，层的人数不代表方法效果。

## 5. 新例检查：14 例中 2 例使定义失效

**选例。** 用 7 个只看原文和 gold 的边界查找条件，在不含 v1 那 30 例所在文档的提及里各抽 1 至 2 例，种子 20261029（`scripts/pilot_recheck.py`）。另加 1 个只出现一次的多标、1 个预测侧未配对重叠、3 个随机对照。"并列修饰语"条件没有找到候选，这一边界本轮没有覆盖。

**先编后看。** 先只看原文和 gold 编码，存为 `outputs/pilot_recheck_textcodes.csv`，再读预测（`pilot_recheck_pred.txt`），最后记输出错误和条文评价（`pilot_recheck_codes.csv`）。

| 例 | 文本（gold） | 判断（只看原文和 gold） | 结果 | 对定义的检查 |
| --- | --- | --- | --- | --- |
| N01 | adenomatous polyposis coli ( APC ) gene（Modifier） | B1 隔括号 | 几乎全漏 | 符合 |
| N02 | a strong family history of breast , ovarian , or other cancers（Composite） | B2；E | top-4 loop06、08 标 Modifier | 符合；B2 与 E 同时触发时 gold 取 Composite，前置修饰时（P05、P22）取 Modifier |
| N03 | patients with familial Mediterranean fever（Specific） | B2 | 30 次全对 | 对照例，符合 |
| N04 | the HD gene product（Modifier） | B1；A4 | 原指南 10/19，修改后 11/11 | **失效**：所有基因中心词前的缩写都会同时触发 A4，与 B1 重复 |
| N05 | severe autoimmune manifestations（Class） | A1、A3；C；D | 原指南全漏；修改后另有带上 severe、标 Specific 两种错法 | 符合；一个提及在三个判断上都出过错 |
| N06 | splenomegaly and lymphadenopathy（Class） | A1；C；E | 漏标、标 Specific、与 splenomegaly 合成 Composite | 符合；同上 |
| N07 | severe enzyme deficiency（Class） | A3；C；D | 29/30 漏标 | 符合；原指南 What NOT 4 排除 deficiency，只管裸词还是也管带修饰语，判断不了 |
| N08 | Adult onset globoid cell leukodystrophy（Specific） | D；C | 30 次全对 | 对照例，符合 |
| N09 | the human genetic disorder ataxia-telangiectasia（Class） | A3；C；D 未决 | 30 次全漏 | genetic 的归属再次未决；Example 10 类推适用、一致，仍错 |
| N10 | mild skeletal changes（多标 Class） | A1、A3；D | 仅 1 份修改后指南 | 符合 |
| N11 | Duarte enzyme variant of [galactosemia]（预测只标 galactosemia） | D 未决 | 原指南 2 次 | **失效**：D 只列出形容词限定词，覆盖不了 "X variant of" 这类前缀（P08 同类） |
| N12 | primary colorectal cancer specimens（Modifier） | B1；D | 30 次全对 | 对照例，符合 |
| N13 | HPRT-deficiency in mice（Specific） | A3；C | 原指南 13/19，修改后 7/11 | 符合 |
| N14 | families with ataxia-telangiectasia（Specific） | B2 | 30 次全对 | 对照例，符合 |

**定义修改：**
- **N04 之后，** A4 只留给动物突变体、基因型、基因座名，"符号与基因名同形"改为 B1 的属性。
- **N11 之后，** "X of Y" 前缀仍列为 D 的未决情形，没有修订，因为还没有足够的例子决定它归 D 还是另立一类。

这两处修改都由新例触发，所以这批新例不能再用来证明修订后的定义好用。

**对照例的作用。** N03、N08、N12、N14 在 30 次运行中全对，按触发条件照样赋码，说明类别成员资格与对错无关；同时也说明，这些触发条件选出的提及并不都难。

## 6. 哪些类别可以逐步扩展

- **修饰角色、并列切分：** 触发条件基本是字符串，可以先用脚本初筛，再人工核对误收和漏收。需要先补全中心名词和关系名词两张列表；修饰角色与并列同时触发时 gold 的取向，目前只有 3 例。
- **限定词与跨度：** 先要决定 "X of Y" 前缀、描述性修饰和 genetic 的归属。
- **提及资格：** A3、A4 可以用字符串初筛；A1、A2 要靠语义判断，需要写出更具体的判定说明。
- **具体还是类别：** C1 至 C3 可执行；C4 要靠语义判断，而且 C 触发得很宽，是否有区分力还没有检验。

## 核查记录

- `scripts/pilot_cases.py`（ea76e88539ce）→ `outputs/pilot_cases_output.txt`（0c4171549401）、`outputs/pilot_cases.json`（6fafecb9be15，与 v1 相同，抽样没有变）。v2 只在输出中追加了口径说明和计数。
- `scripts/pilot_recheck.py`（174dc3617883）→ `outputs/pilot_recheck_text.txt`（349081379df8）、`outputs/pilot_recheck_pred.txt`（2c25602aa03d）。种子 20261029。
- 人工编码：`outputs/pilot_recoding_v2.csv`（b7eb6f69e097）、`outputs/pilot_clause_eval_v2.csv`（e9472c13ed32，49 行）、`outputs/pilot_recheck_textcodes.csv`（ef34bb1806b3）、`outputs/pilot_recheck_codes.csv`（20b8fd41a78b）。v1 的 `outputs/pilot_coding.csv` 保留不动。
- 读过的指南：原指南全文；修改后指南只按关键词检索并读了命中的行（行号见条文评价表）；top-1 loop02 第 1 轮、top-4 loop09 第 3 轮的快照与提示。
- 写完后读回了本文 v2 部分全文；四个 CSV 的行数为 30、49、14、14，与正文一致。

---

# 附：v1 原文（2026-10-28 第一版；已被上文 v2 修订，撤回和降级见 v2 第 4 节）

2026-10-28。探索性分析：类别是在看过 10/24 报告、多轮审阅和本次 30 例之后形成的，没有预注册。离线进行，没有调用 API，没有读测试文档的 gold，没有读 .env。逐例编码见 `outputs/pilot_coding.csv`，抽样见 `outputs/pilot_cases_output.txt`。

### 结论

- 这次要解释的是验证集上每个 gold 提及和每个多标，在原指南和修改后指南下的全部状态：持续错误、改善、退化、错误形式改变、原指南下不稳定，以及开发集上被拒的改写改坏了什么。
- 分类的核心维度是"标注判断"，即标注者在这个位置必须做出的决定。初稿有六类，成员资格只看原文和 gold，不看模型对错。错误类型、指南条文状况、流程记录作为另外三个维度分开记录。
- 30 例试编码里，反复出现的情况不是"指南缺条文"，而是四种：条文已经适用且与 gold 一致，预测仍然错；新条文的字面范围与翻转对得上；指南规范与 gold 冲突，或 gold 自身不一致；条文之间竞争。没有任何条文的情况只出现在多标里。
- 试编码迫使定义改了六处，最重要的是：关系名词补足语并入"疾病名的句法角色"，让同一现象的收益和损失留在同一类；"临床表现是否标注"只管标不标，标签判断移到"具体还是类别"。
- 下一项最必要的工作是普查：用只依赖原文和 gold 的条件，把 791 个 gold 提及和多标按六类判断全部编码一次，再与 30 次运行的结果交叉。试编码不能估计各类占比。

### 1. 要解释的结果不只是修改后指南的稳定翻转

研究目标要求两件事：10/20 会上後藤教授要求建立覆盖全部错误的分类，Track 1 再按分类一次改一处；10/09 seminar 要求逐例解释新规则为什么没有修好目标错误。所以分类要覆盖原指南下就有的错误，也要覆盖改写带来的变化。

下面用"状态"指一个 gold 提及在一次运行中的结果：严格标对，或标签错、边界错、漏标、未配对重叠（一个预测吞掉两个 gold 提及时多出的那个）。按 19 次原指南运行和 11 份修改后指南的状态，791 个 gold 提及可以分成下面几层。层之间有重叠，这是普查数，不是估计。

| 结果层 | 定义 | gold 提及数 |
| --- | --- | --- |
| 持续错误 | 原指南至多 4 次标对，修改后至多 1 份标对 | 132 |
| 改善 | 原指南至多 4 次标对，修改后至少 2 份标对 | 103 |
| 退化 | 原指南至少 15 次标对，修改后至少 2 份标错 | 100 |
| 错误形式改变 | 原指南至少 15 次错成同一种类型，修改后有错成别的类型 | 59 |
| 原指南下不稳定 | 原指南 5 至 14 次标对 | 88 |
| 不在以上任何一层 | 原指南稳定标对，修改后至多 1 份标错 | 368 |

多标另算：原指南 19 次中至少 15 次都出现的多标有 5 个，原指南从未出现、修改后至少 2 份出现的有 12 个。

还有一类结果不在验证集上：9 个循环的第一次改写被拒，循环停在原指南。被拒的候选指南只在开发集上标注过，开发集上改写前标对、候选标错的 gold 提及共 114 个（按"提及 × 轮"计）。

**范围和理由。** 分析对象是验证集 30 次运行的全部 gold 提及和多标，加上被拒轮次在开发集上的变化。这足以回答"哪些标注判断出错、改写怎样改变它们"：上表各层覆盖了一个 gold 提及在不同指南下可能出现的全部结果。范围之外有三样：中间轮次的指南从未标注过验证集，所以一个验证集错误最早在哪一轮出现无法知道；被拒候选在验证集上的表现无法知道；BC5CDR 和 BioRED 没有纳入。

这些层的门槛（4 次、15 次、2 份）只用于抽样，不是分类的一部分。

### 2. 分类分四个维度，核心是"标注判断"

四个维度回答不同的问题，所以分开记录，不合成一层。

| 维度 | 记录什么 | 取决于预测吗 |
| --- | --- | --- |
| 输出状态 | 论文的错误类型：严格对、标签错、边界错、漏标、未配对重叠、多标 | 是 |
| 标注判断 | 这个位置要求标注者做出的决定（六类，见下） | 否：只看原文和 gold；多标只看预测跨度本身的文字 |
| 指南条文状况 | 原指南和相关修改后指南里，有没有条文、是否适用、是否与 gold 一致 | 否 |
| 流程记录 | 一条陈述第一次出现在分析输出、原则还是候选指南，那一轮提示展示了什么 | 否 |

**为什么以"标注判断"为粒度。** 原指南的条文本身就是按判断写的：要不要标、Specific 还是 Class、Composite 怎么切、Modifier 何时用、跨度多长。改写步骤修改的也是这些判断。比它粗的分法（如"标签错"）会把受不同条文管辖的决定混在一起；比它细的分法（如按触发词）会把同一判断的收益和损失拆进不同类。触发词这类细节作为属性记录。

一个提及可以同时要求几个判断，例如 "familial breast cancer gene" 同时涉及限定词和句法角色，所以允许多标签。某次运行"错在哪个判断"取决于预测，作为输出状态的一部分另记，不影响类别成员资格。

**六类标注判断（试编码后的版本）**

| 类别 | 针对的判断 | 纳入 | 排除 | 真实例子（gold） | 能帮助区分什么 |
| --- | --- | --- | --- | --- | --- |
| 临床表现是否算疾病提及 | 体征、症状、病理过程、泛称词组要不要标 | 字符串指临床表现、过程或泛称，不是具名疾病 | 具名疾病；标哪个标签（归"具体还是类别"） | mental retardation（标）；metastasis（标）；cardiac and muscle symptoms（不标） | 指南排除条文过宽，还是 gold 与规范冲突 |
| 疾病名的句法角色 | 疾病名是被修饰的指称对象，还是修饰别的名词 | 疾病名（含缩写、人名词）直接位于非疾病中心名词前；或作 risk、history、case 等关系名词的补足语 | 疾病名本身是中心名词且无关系名词 | the VHL gene（Modifier）；one case of ovarian cancer（Specific）；HNPCC ) kindreds（Modifier） | Modifier 条文的范围是否过宽；条文前提（这是不是疾病名）是否被识别 |
| 具体疾病还是疾病类别 | 指称的是一种疾病还是一类疾病 | 指称疾病的提及，尤其是泛指用法、带遗传限定词、类名中心词 | 不指称疾病的提及 | breast cancer 泛指人群风险（Specific）；neuromuscular disease（Class） | 指南把"泛指"误当成"类别"，还是 gold 本身不一致 |
| 限定词是否纳入跨度 | familial、sporadic、classical、stage II、adult 等是否算进疾病名 | 限定词紧邻疾病名 | 不改变疾病指称的冠词、数词 | familial breast cancer（纳入）；classical [galactosemia] alleles（不纳入） | 规则能否统一，还是 gold 逐文档不同 |
| 并列疾病名的切分 | 一个 Composite，还是分开的几个提及 | 两个以上疾病名或疾病修饰语在候选跨度内并列 | 只有一个疾病名 | renal hamartomas or cystic kidney disease（分开）；sporadic breast and ovarian cancers（Composite）；classical and connatal forms of [PMD] | 信息丢失标准是否被执行；与 Modifier 的优先顺序 |
| 非疾病指称中的疾病样词语 | 动物突变体、基因型、基因座名里的疾病样词要不要标 | 字符串指动物模型、基因型或没有中心名词的基因座名 | 有 gene、protein 等中心名词的疾病修饰语（归"句法角色"） | Small eye in mice（不标）；Dmpk deficient mice（不标）；prostate adenocarcinoma 1（不标） | 指南完全没有条文的缺口 |

**指南条文状况的取值。** 条文点名某个字符串，不等于它适用于当前语境，所以每例都核对条件、标注方向、例外和竞争条文。

- 适用且与 gold 一致；
- 适用但与 gold 相反；
- 有条文，但判断不了如何适用（条件含糊，或前提取决于对名称的识别）；
- 条文相互竞争；
- 规范与 gold 冲突（原指南条文或例子与 gold 不一致）；
- 有通用条文，但前提不满足，等于没有适用条文；
- 没有找到条文。

### 3. 试编码：30 例中失败和争议与成功一样多

样本按第 1 节的结果层定额抽取，种子 20261028：持续错误 5、改善 5、退化 6、错误形式改变 4、原指南下不稳定 3、持续多标 2、新增多标 3，再从开发集被拒轮次中抽 2。涉及修改后指南的层，至少有一例与 top-1 有关。样本只用于检验分类，不用于估计占比。条文状况由我逐条阅读原指南和相关修改后指南判断，行号见 CSV。

| 例 | 文本（gold） | 标注判断 | 结果 | 条文状况（要点） |
| --- | --- | --- | --- | --- |
| P01 | metastasis（DiseaseClass） | 临床表现 | 30 次全漏 | 原指南排除过程词，与 gold 冲突 |
| P02 | TSG101 tumor susceptibility gene 中的 tumor（Modifier） | 句法角色 | 30 次全漏 | 原指南适用且一致；loop01 的基因条文要求疾病词在最左，字面不适用 |
| P03 | classical [galactosemia] alleles（Modifier） | 限定词 | 30 次都带 classical | 原指南例子点名 classical galactosemia 要纳入：规范与 gold 冲突 |
| P04 | hereditary adult [neuromuscular disease]（Class） | 限定词 | 30 次都带限定词 | 交给标注者，判断不了 |
| P05 | breast or ovarian cancer risk（Modifier） | 句法角色、并列 | 原指南全为 Composite；仅 1 份修改后标对 | Modifier 与 Composite 竞争 |
| P06 | familial breast cancer gene（Modifier） | 限定词、句法角色 | 原指南多去掉 familial；3 份改对 | 没有决定性条文 |
| P07 | renal hamartomas or cystic kidney disease（分开） | 并列 | 原指南多合成一处；3 份改对 | 原指南信息丢失标准适用且一致，仍错 |
| P08 | classical and connatal forms of [PMD] | 并列、限定词 | 原指南多标整段；4 份改对 | Example 17 可类比读成整段 Composite，判断不了 |
| P09 | the VHL gene（Modifier） | 句法角色 | 原指南全漏；3 份改对 | 原指南与 loop01 条文都适用且一致，loop01 仍漏 |
| P10 | sporadic breast and ovarian cancers（Composite） | 限定词、并列 | 原指南多去掉 sporadic；2 份改对 | 没有决定性条文 |
| P11 | one case of ovarian cancer in a first-degree relative（Specific） | 句法角色 | 原指南全对；4 份改成 Modifier | 3 份的新条文字面适用且与 gold 相反；1 份字面不适用却也改错 |
| P12 | mental retardation is not severe（Class） | 临床表现 | 原指南全对；2 份漏标 | loop08 两条条文竞争，预测与"主语不标"一条一致 |
| P13 | at increased risk for breast cancer（Specific） | 具体还是类别、句法角色 | 原指南全对；2 份以两种方式改错 | 两条不同新条文各自适用且与 gold 相反 |
| P14 | papillary renal cell tumours and ten renal oncocytomas | 并列 | 2 份未配对重叠 | 与原指南 3/19 相近，可能在波动范围内 |
| P15 | 80 % risk of breast cancer（Specific） | 具体还是类别、句法角色 | 原指南全对；3 份改错 | 2 份条文适用且相反；loop10 措辞宽，是解读 |
| P16 | characterized by cerebellar degeneration（Class） | 临床表现 | 4 份漏标 | 与原指南 4/19 相近；只有 1 至 2 份可能由条文解释 |
| P17 | familial breast cancer（Specific） | 限定词、具体还是类别 | 原指南去掉 familial；4 份带上 familial 却标 Class | 两份新条文适用且与 gold 相反 |
| P18 | inherited breast cancer（Specific） | 同 P17 | 同 P17 | 同一文档同一模式，不算独立证据 |
| P19 | fibre-type dependent [atrophy]（Specific） | 临床表现、具体还是类别 | 原指南多漏标；5 份标成 Class | 规范（Example 11）与 gold 冲突；gold 内部也不一致 |
| P20 | von Willebrand factor 中的 von Willebrand（Modifier） | 句法角色 | 30 次中 29 次漏 | 人名词算不算疾病名，判断不了 |
| P21 | colorectal cancer ( HNPCC ) kindreds（Modifier） | 句法角色 | 原指南 14 次标 Specific；2 份改对 | 原指南例子正是 HNPCC kindreds，适用且一致，仍错 |
| P22 | hereditary breast and ovarian cancer gene（Modifier） | 句法角色、并列、限定词 | 原指南一半对；修改后错成三种形式 | Modifier 与 Composite 竞争 |
| P23 | stage II colorectal carcinomas（Specific） | 限定词、具体还是类别 | 原指南一半去掉 stage II | 原指南 Example 19 类比适用且一致 |
| P24 | Small eye in mice（无 gold） | 非疾病指称 | 30 次都多标 | 没有找到条文 |
| P25 | sf tissue samples（无 gold） | 非疾病指称 | 原指南 15 次多标 | 没有找到条文 |
| P26 | PAC1, for prostate adenocarcinoma 1（无 gold） | 非疾病指称、句法角色 | 6 份新增 Modifier | loop01 条文"带或不带数字后缀"可读成覆盖，判断不了 |
| P27 | cardiac and muscle symptoms（无 gold） | 临床表现 | 2 份新增 Composite | 泛称排除与"列表中症状为 Class"竞争 |
| P28 | Dmpk deficient mice（无 gold） | 非疾病指称 | 4 份新增 Modifier | 通用 Modifier 条文前提不满足；没有专门条文 |
| P29 | breast cancer susceptibility gene 1（Modifier，开发集） | 句法角色 | 被拒候选漏标 | 相关条文没有变化，可能是单次波动 |
| P30 | a family history of cancer（Class，开发集） | 句法角色 | 被拒候选标 Modifier | 候选新增 "family history of ovarian cancer → Modifier"，类比适用且相反 |

**原定义失效的例子。**

- **P02、P20：** 初稿要求疾病词位于名词短语最左，这两例的疾病词在基因名或蛋白名内部，gold 仍标 Modifier。
- **P19：** 初稿让"临床表现"类同时管标不标和标什么标签，但 gold 给 atrophy 标 Specific，给 mental retardation（P12）、cerebellar degeneration（P16）标 Class，同一类内部标签不一致。
- **P17：** 初稿要求单标签，但这个提及在原指南下错在跨度，在修改后指南下错在标签，只记一类就会丢掉"错误形式改变"。
- **P11、P13、P15：** 初稿打算把"关系名词补足语"单列一类，但同一提及在不同指南下随条文范围（history、case、risk）翻转，单列会把同一现象的收益和损失拆开。

**仍然判断不了的例子。**

- **P26：** 没有中心名词的基因座名算不算"句法角色"。
- **P08：** "X and Y forms of Z" 该怎么切。
- **P01：** metastasis 是过程还是病理结局。
- **P04：** 两个限定词连用时 gold 为什么只去掉一个。

**条文状况的分布。** 这只是 30 例里的数，不代表总体。"已有条文适用且与 gold 一致、预测仍错"在 P02、P07、P09、P20、P21 出现；"规范与 gold 冲突"在 P01、P03、P19 出现；"条文竞争"在 P05、P12、P22、P27 出现；"没有找到条文"只在多标 P24、P25 出现，P28 是通用条文前提不满足。另有三例（P14、P16、P29）的翻转与原指南自身的波动相近，不需要条文来解释。

### 4. 试编码后改了六处定义

每处修改都由第 3 节的例子触发。

1. **句法角色**：从"疾病名在最左修饰非疾病名词"改为"疾病词直接位于非疾病中心名词之前，不论在名词短语中的位置"（P02、P20）。加一个属性："这个名称同时是基因符号或人名"（P09、P20），因为条文前提在这里最容易落空。
2. **关系名词补足语**并入句法角色，作为子类，关系名词（history、case、risk）记为属性（P11、P13、P15、P30）。
3. **临床表现**一类只管"标不标"；标签判断归"具体还是类别"，并记录 gold 内部不一致（P19）。
4. **允许多标签**，"这次运行错在哪个判断"作为输出状态的一部分另记（P17、P18）。
5. **非疾病指称**一类与句法角色的分界改为"有没有 gene、protein 等中心名词"（P26 对照 P29）；P26 本身仍判断不了。
6. **条文状况**增加"条文竞争"和"规范与 gold 冲突"两个值，并把"没有找到条文"与"有通用条文但前提不满足"分开（P28）。**输出状态**增加"在原指南波动范围内"的标记（P14、P16、P29）。

### 5. 现在能支持什么，不能支持什么

**能支持的描述性发现（只限这 30 例）。**

- 一部分错误不是缺条文。原指南或修改后指南已有适用且与 gold 一致的条文，预测仍然错，而且集中在条文前提要靠识别名称才能成立的地方：VHL 是疾病缩写还是基因符号，von Willebrand 算不算疾病名，括号把 HNPCC 和 kindreds 隔开（P09、P20、P21）。
- 新条文的字面范围与翻转对得上。P11 在 11 份指南中，9 份的结果与各自条文的字面范围一致：只写 family history 的条文没有改动 "case of"，写到 cases 或补足语的条文改动了。P13 被两条不同的新条文以两种方式改错。
- 有些持续错误来自规范与 gold 的冲突（P01、P03、P19）。照指南做就会和 gold 不一致，单靠改写指南的措辞修不好。
- gold 自身在几处不一致：表现词的标签（P19 对 P12、P16），X-deficient 是否标注（P28 对验证集中的 PAH-、C9-、Atm-deficient），遗传限定词是否纳入（P04 对 P06、P10）。
- 流程记录一例（P30）：top-1 loop02 第 1 轮的目标是 Specific 与 DiseaseClass 混淆，分析输出和原则都没有提到 Modifier 或家族史，"family history of ovarian cancer → Modifier" 第一次出现在改写出的候选指南里；同一改写提示把该文档的五个 "ovarian cancer" 列为 Modifier。

**不能支持的解释。**

- 各类占比：样本按结果层定额抽取，不代表总体。
- 条文导致了翻转：没有删掉条文再标注的对照，"对得上"只是相容。
- 哪个改进方向最好，以及"不得破坏"清单的上限是否重要：P30 只说明这条陈述出现在改写步骤，不说明为什么。
- 条文状况的判断只有我一人做出，没有第二人核对。

**这些类别各自指向的改进方向（候选，未检验）。**

- 条文已有却没用对：补条文前提的例子（基因符号、人名词、括号缩写），而不是新增规则。
- 规范与 gold 冲突：改写需要看到 gold 证据，或者在评价时承认 gold 的不一致。
- 条文竞争：写明优先顺序，例如 Modifier 与 Composite。
- 新条文范围过宽：写入时核对条文范围是否越过了证据。
- 没有条文的多标：补动物模型、基因型、基因座名的条文。

**下一项最必要的工作：普查。**

把六类标注判断的成员资格，在 791 个 gold 提及和多标上全部编码一次，再与 30 次运行的状态交叉。句法角色、限定词和并列可以用只依赖原文和 gold 的字符串条件初筛，先人工核对随机抽取的一批，看误收和漏收；临床表现、具体还是类别、非疾病指称需要人工判断。30 次运行中至少错过一次的 gold 提及有 535 个，不同的多标预测有 89 个，人工部分优先覆盖这些。理由是：教授要的是覆盖全部错误的分类，试编码只能检验定义，不能给出分布。

### 6. 探索和选择偏差的记录

- 六类判断和条文状况的取值，是在看过 10/24 报告、外部审阅和这 30 例之后形成的。这 30 例也用来修改定义，所以不能再用它们证明定义好用；普查时要用新的核对样本。
- 结果层的门槛（4 次、15 次）沿用了旧的筛查门槛，只用于抽样。
- 10/28 规格（`20261028_posthoc_analysis_spec.md`）第 5 节的数值筛选（贡献前五、至少 3 份、超过一半就降级）已撤回：案例选择先要说明服务于什么目标；净收益接近零的现象可能同时有大量修正和破坏；11 份修改后指南中只有 2 份来自 top-1，"至少 3 份"会排除所有 top-1 独有的现象。

### 核查记录

- `scripts/pilot_cases.py`（0c908068be43）→ `outputs/pilot_cases_output.txt`（a0e04e386414）、`outputs/pilot_cases.json`（6fafecb9be15）。读 `error_rows.csv`（由 `error_table.py` 生成，已断言与 30 次运行的 `valid_metrics.json` 一致）、验证集 gold、`rounds.json` 和被拒轮次的 `snapshot.json`。种子 20261028。
- `outputs/pilot_coding.csv`（45fe78fb7a8d）：30 例的人工编码，每例含文档、位置、gold、标注判断、属性、条文状况（含指南与行号）、结果和不确定性。
- 读过的指南：原指南全文；修改后指南中与各例有关的条文（行号见 CSV）；top-1 loop02 第 1 轮与 top-4 loop09 第 3 轮的 `snapshot.json`、`refine_guidelines.txt`、`infer_discrepancy_patterns.txt`。
- 层的人数（132、103、100、59、88、368；多标 5、12；开发集 114）以及 535、89，都在 `pilot_cases_output.txt` 中。
- 没有调用 API，没有读测试文档的 gold，没有读 .env。
