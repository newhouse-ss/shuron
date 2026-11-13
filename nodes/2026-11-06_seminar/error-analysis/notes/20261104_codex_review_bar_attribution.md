# 柱状图条文归因的独立审查

2026-11-04。审查对象为正文第 151 至 188 行及其离线实现。

**总判定：部分能。它可以精确描述这批运行的分类别 TP 差异，并产生一些有原文和理由支持的机制假设；现有 CREDITED 规则不能可靠找出造成正负号组合的条文，也不能确定“好的指南写法”。最小改法是先离线重做条文适用范围与逐提及状态转移核查，撤掉自动归因和重复投票，再对一个明确假设开展有同期未改指南对照的重复删改实验。**

本审查不修改正文或分析代码，不执行新增标注，不提交或推送。唯一新增的仓库文件为本记录。复现产生的临时重写全部逐字节相同。

## 证据与术语

仓库根为 `H:/Git/research/修論/llm-guideline-moderation-source`。下文 `EA/` 指 `todo-temp/error-analysis/`；`R` 指正文 `EA/reports/20261024_error_analysis_report_zh.md`，`P` 指同目录附录 `20261024_error_analysis_appendix_zh.md`。`O:L40` 表示 `EA/outputs/bar_attribution_output.txt` 第 40 行。

指南简称 `4-08` 表示 `outputs/ncbi_disease/20261022_haiku-xhigh_topk4_loop08/final/final_guidelines.txt`，`1-05` 同理为 topk1。指南行号均指当前文件的一基行号。S、D、M、C 分别表示 SpecificDisease、DiseaseClass、Modifier、CompositeMention。TP 是跨度和标签同时正确的预测数。这里的“相容”只表示条文条件、文本和已存理由可以连起来，不表示已经证明因果。

## 按严重程度排列的问题

### 致命 1：同一份指南只标一次，整篇同时改写，无法识别某条条文的作用

**问题。** 研究问题使用“由哪些写法造成”，需要比较同一指南有这条规则和没有这条规则时会怎样。当前只有 11 个整体改写结果，每份一次；条文、例子、长度、优先级和其他规则共同改变。原指南的 19 次运行只提供原指南的输出分布，不能估计每份新指南的运行方差，更不能隔离某条规则。盲编码和事后理由均不能补出这个比较。

**证据。** O:L2 至 L5：同为 `-++`，4-02 的 S/D/M 差值为 −0.2/+8.2/+3.7，三根均在范围内；4-06 为 −35.2/+13.2/+26.7，三根均在范围外。4-01、4-04 的 `+++` 与 4-09、1-07 的 `-++`，S 和 D 都在原范围内。相同符号不代表相同机制，符号不同也不证明规则不同。O:L147 至 L149 的 1-07 两项超范围变化均为 UNEXPLAINED，而该指南 M 整根柱子 +15.7 超范围，所以 R:L151 的“超出的那些都对得上”甚至没有被当前算法完整实现。

**影响。** R:L151、L165、L171 至 L184 的因果读法。“再标 2 次就把分组坐实”也没有样本量或精度保证，增加重复本身不隔离条文。

**最小改法。** 现有结果统一称“本次运行差异”和“待检验的机制假设”。先选一个条文与明确作用范围，再比较未改指南与删改后指南的同期独立重复。反向插入原指南可以进一步检查充分性。不能用完整指南间相关性替代该比较。

### 致命 2：OPT 丢掉适用条件，能够把不适用的条文归给实际变化

**问题。** 编码 CSV 保存了 `scope`，实现却只取 `(question, option)`。不同指南的条件、例外与优先级被压成同一个类别集合。类别精确相加不意味着类别恰好是条文的适用域。

**明确反例。** `bar_attribution.py:256-261,279-290` 把 Q4 的列表例外一律作用到两个 D 症状类别。4-08:L104 只排除“bare, single-word”且“member of a coordinated list”的症状，并明确多词表型保留 D；但 O:L128 把 **D sign/state elsewhere −4.5** 归给它。对应的列表类别只有 −1.7，未超范围（O:L16-17）。抽查的 8929413:210-217 `anxiety` 是普通句子中的宾语，不在列举中，原指南 13/19 标对，4-08 漏标；8929413:15-37 `anxiety-related traits` 是多词标题提及，原指南本就 0/19 标对，4-08 仍错误。两者都不支持用 L104 解释该类别的 TP 下降。

4-05 的 Q7 编码范围为“bare unmodified heads only”（CSV:L52；指南 L19），但 OPT 包含三个 D 大类。第一个抽查项 `adrenal insufficiency` 的理由是“named endocrine condition”，没有患者特定谓词，不是无修饰中心词。该条仍随全局 D→S +6.6 和类别下降获得 CREDITED（O:L66）。并非措辞不同造成错误，而是可执行条件不同。

**影响。** R:L172、L180、L182、L186 及附录 P 的逐类“对上”表；“受条文管辖”的对照域也受同一映射错误影响。

Q6的反向选项也只排除official designation，当前33个full-name提及没有官方名称与普通指称的提及级区分，不能把两者视为同一个适用域。

**最小改法。** 为每份指南逐条记录触发条件、例外、优先级和输出动作，再在提及层面判断适用、不适用或不确定。Q4 至少分开列表与非列表、单词与多词；Q7 必须核对患者指代、中心词和其他许可分支。不能继续让一个全局 OPT 代替这些条件。

### 主要 1：三条取二会把同一计数当成两份证据

**证据。** `bar_attribution.py:159-174,256-263`：Q6 正向的 `fullname right` 就是该类的 TP；Q8a 的 `deficient right` 也是同一类 TP；Q8b 同理。Q4 正向的 `sign right` 是两个症状类别 TP 的和，并非另一种错误。O:L48 的 4-01 Q6 两项都是 +6.9；O:L44 的 1-05 Q8a 两项都是 +8.4；O:L52 的 4-02 Q4 两项都是 +6.8，引用为 **0/9**，照样 CREDITED。39 条 CREDITED 中，Q4 正向 5 条、Q6 正向 5 条、Q8a 7 条，共 17 条存在这种相同或直接汇总计数的双重投票。

另外，两票可以完全不要求类别按预言方向超范围。4-01 Q7 的类别和为 +8.9，4-04 Q7 为 +11.9，预言为下降，两者均靠错误计数和引用获得 CREDITED；4-08 Q1 的 S 类别 −1.8 未超范围，也获得 CREDITED（O:L49、L60、L80）。它们未写入 F 的类别归因，说明 D 的 CREDITED 与“解释某个超范围类别”含义并不一致。

**影响。** R:L167 的证据门槛，以及 R:L173、L174、L179、L183。判据可以用作人工筛查规则，但没有经校准的可靠性，不能解释为两个独立证据来源的确认。

**最小改法。** 取消投票。分别报告类别效应、具体错误转移、语义相容性、引用证据和未知项。要求变化发生在条文适用的同一批提及上。即便改成必须同时满足前两项，当前 39 条会剩 34 条，重复计数和范围错误仍然存在，不能作为充分修复。

### 主要 2：最大最小范围只是探索性筛查，“范围内就是噪声”与“超范围就是条文效应”都不成立

**证据。** O:L24 的 63/165 和 O:L2-4 的 16/33 可复现。若 20 次观察可交换且没有并列，第 20 次是严格最大或最小的概率为 2/20，即 10%。这是双侧预测范围的性质，不是 5% 显著性检验；整数计数有并列时，严格越界概率还会降低。165 次筛查的 16.5 是相应理想零假设下的期望，不能说已观测的 63 个里“有 16 个是纯波动”。各类别和指南之间相关，不能套独立二项分布；条目相关不影响期望线性相加，但会影响不确定性。

本次辅助检查用每个原运行对其余 18 个的范围做留一比较，15 类合计 16/285 次严格越界。这是离散性与并列的敏感性描述，既不是 19 对 1 的同一个校准，也不是新的显著性结论。17 根未越界柱子仍可有规则变化互相抵消，R:L176 自己就给出了 4-09 的例子。

**影响。** R:L151 的“只有一半超出了单次运行的波动”、L165 的确定性表述、L167 的“纯靠波动约 16 个”。

**最小改法。** 保留范围作为描述性标记，不用它判定机制。报告实际差值、文档聚集、重复运行的不确定性与筛查次数；若做检验，应先固定比较和整体错误控制方式，按文档保留配对关系，并另估运行随机性。对已看过结果的本批数据，只作探索。

### 主要 3：引用节号既有解析错误，也不是条文级机制证据

**实现反例。** `bar_attribution.py:194-209` 把最近编号列表项当成节号：4-02:L152 返回 `2`，实际是无编号的 “Pathological-state spans in characterization frames” 小节，最近的 `2. **Frame test**` 在 L150，并非指南第 2 节。4-09:L158 返回 `4`，实际是 3.1 节内的第 4 个步骤；其抽查 FAP 理由明确写 cohort，但引用 `3; 3.1` 被漏算。4-09:L271 返回 `5`，实际是无编号 “Principle Precedence” 下第 5 项。4-02:L141、L198 返回 None，真实小节有标题，且仍有父节；这只说明不能靠当前数字函数匹配，不说明不存在条文引用。

`cites():213-218` 的确让 `3` 配上 `3.1`、`3.1` 配上 `3.1.2`，也让 `3` 配上 `3c`；不会把 `3` 配上 `13`，不会把 `3.1` 配上 `3.10`。普通数字还会命中 `What NOT to Annotate 1` 中的 1；NOT 分支会把 `NOT8` 配上任何 “item 8”，也会配上 “item 8.1”。数字处在哪个章节命名空间没有被保存。

我以“精确数字或字母节号，允许其后的句点标点，不把子节当同一个 token”为敏感性口径重算所有当前纳入的引用。仅 4-09 Q7 的一次实际命中改变，1/3 变 0/3，39 个 CREDITED 状态均不变。这个事实限制了正则缺陷在本批结果中的影响，不能夸大为正则修好就推翻结果。若希望父节覆盖子节，需要显式规定层级关系，不能由正则偶然实现。

**语义反例。** 1-05 Q2 为 34/34 引用 1.2（O:L41），但样本 `breast cancer` 理由是 unframed list，对应 L64，不是 L46 中部位词条件。4-04 Q7 样本引用 1b(b)(i) 的同义名解释，编码条文却是 1b(c) 的患者条件；同在 1b 就被算成引用。4-09 Q2 的 1/1 理由是 “forms of” 的类别指代，不是部位词导致。

**影响。** R:L167、L171、L176、L180、L184 中把“引用所在节”进一步读成“由此条文导致”。

**最小改法。** 给条文使用文件行区间和稳定 ID；同时保存正式章节、标题、局部列表项、交叉引用与重复表述。机器引用匹配只负责检索，再人工核对理由所用的是哪一个条件。父节引用不能自动算命中其中任意一条。

### 主要 4：cited_share 的分母偏向预言相符的输出，未证明它们贡献了 TP 变化

**证据。** `bar_attribution.py:227-249` 实际筛选为：本次恰处于预言状态、原 19 次至多 9 次处于该状态、该 gold 有重叠预测。遗漏项完全排除，拿不到重叠预测也排除；再取重叠字符最多的一条理由。这个实现确实符合修订后的“只看预言状态”，但它不是全部改变提及的遵循率，也不记录反向变化。

例如 4-08 Q4 中 `anxiety-related traits` 原指南 12 次误标 M、7 次漏标，本次漏标，满足“新预言状态”，却没有造成任何 TP 损失。4-06 Q2 的 `prostate carcinomas` 原指南 19/19 都边界错，本次是更长的 `androgen-dependent prostate carcinomas`、D 标签，能够进入预言的错误计数和引用分母，却同样不贡献新的 TP 损失。全部 CREDITED 行的引用候选中有 12 个“条文行×提及”取到非精确跨度的最大重叠预测。

**影响。** R:L167、L171 的引用率，及全部从计数变化推断 TP 变化原因的段落。

**最小改法。** 每个提及列出原指南正确比例、本次状态、对 TP 差值的精确贡献、适用条文与匹配到的实际预测。区分正确→预言错误、其他错误→预言错误、预言错误→正确以及反向回归。跨度不同时保留边界变化，不把相交理由视为同一跨度的决定。漏标的理由标为不可观察，不能补写原因。

### 主要 5：冻结的是一个说明文件，最终判据并非全部在首次重算前确定

**证据。** P:L491-492 明确承认首次运行后改了两处：引用只看预言状态；只给方向一致的超范围类别记账。正文 R:L167、L188 仍不加限定地说规则重算前写定。`bar_attribution_rules.json:42` 没有“至少一半”的数值阈值，也没有完整最终筛选；代码 L38 只校验文件 SHA-256 的前 12 位，并不加载其内容来构造类别、OPT 或门槛。最终行为由重复写在 Python 中的代码决定。文件哈希证明当前内容可被核对，不能证明时间先后或分析未适应结果。

两处修订本身有合理动机，第二处尤其是排除方向相反的归因，不能因此认定结果造假。但“最终全部预先写定”不成立。P:L492 还说这些偏离“都已在输出 D 节注明”，实际 O:L39-99 只有行号、节号和分数，没有该修订说明。

**影响。** R:L167、L188 的预先性说法，及对规则客观性的信任程度。

**最小改法。** 改称“基于已见结果制定并修订的探索性规则，当前版本可复现”。保存问卷原文、各版本规则与代码及修改时间、初版和修订版结果。把机器规则放在同一份可加载配置，校验代码、编码和输入的完整哈希。新的独立比较开始前再冻结。

### 次要 1：盲编码的引文可靠，编码的完整性与语义没有因此得到保证

99 行引用全部在标明的原文行内，行号均有效。这一点通过了独立逐行字符串核对。可是其中 97 行属于 11 份新指南，原指南只有 2 行；不能说已有完整的“12 份指南×同一套问题”对照。1-07 缺 Q8a，4-05、4-06、4-07 缺 Q8b，4-08、4-10 的 Q4 各两行。空白、不适用、无条文应显式区分。原样继承、反向规则、含歧义规则也不应仅因不在 OPT 就消失。

CSV 的 `scope` 已记录若干重要区别，错误主要发生在后续压缩。另如 4-09 Q7（CSV:L86，指南 L271）引用的是 “A patient-level role does not promote them to Specific Disease”，却编码为 Specific；scope 又限制 disease-denoting heads，支持 Specific 的正面规定实际在 L272。当前未被 CREDITED，但会影响所谓受管辖类别。不能拿“引文存在”当“选项和作用域正确”。盲编码者是否确实没看过结果，只能依据 P:L490 的过程记述，现有 CSV 和哈希无法独立证明。

最小改法：补齐固定矩阵和完整问卷，为每一项保存正面规则、例外与歧义；结果盲编码保留，分析者已见错误的事实也保留。无需为了本次离线审查再调用模型。

### 次要 2：训练集惯例支持范围有限，history 的来源和分母表述错误

O:L190 的 118/125、`dc_loss_clauses_output.txt:56` 的肿瘤词名称 S213、D50 均与读取 heldout50 名单后排除这些文件的独立计数相符。但是肿瘤词统计还包括 M97、C59，且不是专门的“仅靠部位词”的条件比较，不能推出部位词充分。118/125 支持反对无条件排除 bare cancer/tumor，不支持所有语境都标注。history 不能自动代表 risk、patients with。

R:L179、L188 和 P:L1018 所指 `history_tally_output.txt` 没有训练集 21 的统计。实际来源为 `rule_chain_output.txt:61-62`，实现 `rule_chain.py:239-247`，统计的是 history/histories of 的语境数：S9、D3、C5、未标注4，共21；gold 提及为17处，没有 M。条件还允许 gold 起点在介词结束后 0 至 3 字符内，并非严格“紧跟”。这些数字已独立按原实现重算。因此应改为“21 个匹配语境中17个有邻近 gold，均不是 M”，并给出正确来源。

最小改法：按真正的候选条件统计训练惯例，明确语境分母、未标注项和其他标签；只把它当 corpus convention 的外部相容性核查，不能代替指南干预。用大量已有 gold 选择规则，也应与最终独立评价分开。

## 第 1 至 10 题逐条回答

本次请求显式列出的题号从 7 开始。为覆盖要求，第 1 至 6 项按所给方法概要拆成下列六个审查问题，不假定存在未提供的题目原文。

1. **拆柱子的定义与精确性。** 算术严谨，语义归因不随之成立。100 篇共有791个gold，S409、D127、M218、C37。S四类、D五类、M六类为互斥完备划分。33 个未四舍五入的和全部成立，最大浮点残差 `7.11e-15`；165 类别变化中的63个越界也一致。展示为一位小数后的各项之和偶尔会差0.1，这是舍入而非漏项。类别由原文/gold计算，但词表的形成不是纯粹独立于预测，`modifier_subset.py:41-42` 已承认补词时用过子集外误标反馈。肿瘤词、关系结构和并列的先后优先级也使其不等于条文适用范围。

2. **盲编码是否消除了结果驱动。** 没有。可避免编码员对具体指南随分数迎合，但题目和候选机制已经由看过错误的分析者选择；类别与判据也经过已有结果反馈。其角色是减少某一阶段的偏差，而不是给整套分析提供独立验证。99行引文存在不等于99项语义都对，原指南仅2行也不足以完整比较继承关系。

3. **字面映射是否正确。** 部分正确，不能统一套全类别。Q1 对 history 与人群、Q2 对病理中心词、Q4 对列表/单词/疾病主语、Q6 对官方名与普通修饰、Q7 对患者和词形都有不同条件。OPT丢掉scope，Q4存在已定位的错误对应。规则 JSON 的错误种类与 MEAS 的11个方向定义基本相符，但“按字面”不保证适用条件或条文所作用的提及集合正确。

4. **三条取二是否严谨。** 不足以确认归因。多项判据一、二重复，聚合指标还可能由另一批提及驱动。D区39条 CREDITED 中3条没有预言方向的类别越界，2条预言错误没有越界；F区另过滤方向，并给后两条标 weak。至少两票不是经过校准的可靠性门槛，也不排除其他条文。

5. **理由引用是否支持机制。** 具体理由与可执行条件相容时，可以支持“模型公开理由与此机制相容”。不能把自述当真实内部因果，也不能把大节号当具体条件。当前还存在列表号/节号混淆、预言状态筛选、非精确重叠和漏标不可观察。4-02 Q4 引用0/9却被 CREDITED，1-05 Q2的34/34亦不足以特指部位词条款。

6. **跨指南与训练惯例能否推出好写法。** 能提供候选与反例，不能确定有效写法。11份指南不是只有该条文不同的对照，未被标成 CREDITED 也不代表没有作用。训练惯例应按候选的真实条件分层，不能把“肿瘤词名称多数为S”推成“部位词充分”，也不能把“history语境无M”推成所有关系名词都不能M。

7. **事后两处修改是否推翻预先写定。** 推翻不加限定的“最终规则全在首次重算前写定”。它们不使数据和复现失效，也不自动使改法不合理；需要把版本、首次结果和改动披露为探索性分析过程。附录已披露，正文和冻结说明仍不一致；当前产物不能恢复初版的全部结果，故本审查不猜测两处改动分别改变了多少个 CREDITED。

8. **实现复现与核对。** 原脚本退出0，stderr为空；198文件哈希完全相同。另以只执行原函数及配置的AST摘取方式重建内存数据，绕开runpy上游与输出写入，产生的完整 `rec` 与保存JSON完全相等。全部30次×791 gold的right状态与保存预测直接比较，23,730项零差异。99行行号/引文零不符。section、cites和cited_share的缺陷及影响见上；没有观察到把3配上13。逐项核对11个OPT选项，其预言事件与JSON中相应11个事件一致，包括Q3的merge下降；PRED_STATE把该项引用候选设为right，其余按相应事件状态筛选。JSON另外两个“不预期上升”的Q1 not Modifier与Q2 enough选项未纳入OPT，不能将其解释为已经验证过的反向对照。最终门槛及逐指南作用域没有单一机器配置来源。没有读取heldout50 gold。

9. **每条 CREDITED 的最多5项抽查。** 已覆盖全部39条。每条先取预言状态候选池按(doc,start,end,label)排序的首项，阅读原文、gold、预测、理由及条文邻近条件；另外对3条Q4排除和4-05 Q7，扩展为同一候选池已生成的前5项。合计55个“条文×提及”检查，单条不超过5个，不是55个不同gold。扩展是针对发现的范围问题，不用于估计总体比例。完整表见下。所有相容项仍缺反事实证据；明确不适用和引用其他条件的样本足以否定当前规则总能正确对应写法。

10. **正文逐条处置。** 见下表。数字均为当前输出的已观测差值，不能把它们直接重命名为条文效应。

## 正文第 151 至 188 行的处置

| 原文位置与结论 | 判断及必要修改 | 当前输出数字 |
| --- | --- | --- |
| L151，16/33且超出者都对应条文 | 保留16/33；改为超出已观察的原指南范围；删除“超出的那些都对得上” | O:A 16/33；1-07 M +15.7，F的M缩写+21.4为UNEXPLAINED |
| L153-163，正负号分组和越界表 | 作为本次样本描述成立，不能解释组别机制 | O:A，+++两份；+-+一份；-++五份；--+两份；---一份，逐项与表一致 |
| L165，+++与-++分不开，再标2次坐实 | 前半改为当前证据不能区分这些特定指南的S/D期望；删去重复2次即足够的保证 | 4-01 S/D +10.8/+8.2；4-04 +7.8/+6.2；4-09 −0.2/+7.2；1-07 −3.2/+6.2，全在范围内 |
| L167，拆分、盲编码、63/165和三条取二 | 保留算术和编码过程记述；“约16”限定为理想零假设期望；删去规则有效且全部预先固定的暗示 | O:B 63/165；D39条CREDITED；4-02 Q4 +6.8/+6.8、引用0/9 |
| L171，四份S下降由关系名词及部位词写法解释 | 降为候选机制；关系补足语有较直接实例，部位词不能仅凭节号确认 | 整根S：1-05 −39.2、4-06 −35.2、4-07 −34.2、4-10 −16.2；Q1对应类别−14.8/−12.8/−18.8/−11.8；Q2的D误标+32.3/+11.3，引用34/34和3/12 |
| L172，三份D下降由症状排除、裸cancer及患者升S解释 | 症状排除对应需重做，尤其删除4-08 L104解释列举外类别−4.5；患者升S需逐分支，不能整类归因 | 整根D 4-08 −11.8、4-05 −21.8、4-10 −38.8；Q4漏标+5.8/+8.8/+11.8；Q7 D→S 4-08 +8.6、4-05 +6.6 |
| L173，4-06症状规则解释D上升 | 保留语义相容假设，取消确认效果的表述 | 整根D +13.2；症状两类+6.5/+4.3，和+10.8；sign right也+10.8，引用4/11 |
| L174，8份M上升，deficient六份、全名五份对上 | 数量作为算法筛查结果成立，不能当成因果支持份数；最大缩写块仍未解释 | M越界8份；其中deficient6份，所有11份中Q8a实际CREDITED7份；Q6正向CREDITED5份；4-08缩写+19.4、其他M+12.7均UNEXPLAINED |
| L176，4-09抵消与并列分开标 | 抵消成立；分别对应条文仍须按具体理由；并列规则可以列为有明确样例的候选 | S总−0.2=关系−9.8+并列12.5+其他4.6−肿瘤词7.5；merge−24.5，引用13/16 |
| L178，候选只是共现、未消融 | 保留，且应同样约束前面逐柱归因措辞 | D的CREDITED是筛查39项，F仍列出大量UNEXPLAINED，不是完整因果解释 |
| L179，不把history/risk/patients之后病名定M | 缩小为按每份条文实际条件检验的候选；7份CREDITED并非7份S类别越界；更正训练来源和分母 | Q1七份；4-08类别−1.8未越界但误标+6.9、引用3/3；history训练数不在本输出，正确来源为rule_chain D的S9/D3/C5/O4 |
| L180，部位词足以让病名具体 | 删除“足以”的普遍规则；保留部位与语境如何共同决定S/D的待测假设 | 五份not enough中仅1-05、4-06预言D误标越界+32.3/+11.3；4-09为−0.7，弱对应；训练S213/D50并非部位词充分性实验 |
| L181，裸cancer/tumor照原指南 | 可保留为避免无条件排除的候选；必须明确普通、修饰和家族史语境差别 | 三份Q5，bare missed 4-02 +10.2、4-05 +11.2、4-10 +29.2；4-02 D类仅−0.8，真正越界的是M类−6.1；G为118/125 |
| L182，症状标D且列表不设例外 | 暂撤出已获支持的好写法清单，完成作用域核查后重提；原文已说明gold不一，应保留 | 正向sign right在4-01/04/02/06/09为+7.8/+11.8/+6.8/+10.8/+9.8；负向漏标4-05/08/10为+8.8/+5.8/+11.8，但4-08被归因的越界类别不满足例外条件 |
| L183，官方全名中的病名也标M | 保留语义相容候选，不能把5/7当条文效果证明；反向三份也有漏标变化 | 正向TP为+6.9/+5.9/+7.9/+7.9/+6.9；反向1-07、4-05、4-10全名TP为−1.1/−3.1/+1.9，漏标为+3.6*/+5.6*/−1.4 |
| L184，完整病名分开、共用中心词合成 | 保留单指南候选及证据弱的限定；“只有一份写明”需与编码区分 | 4-09 S并列+12.5、merge−24.5、引用13/16；4-02也编码separate，但含隐含完整病名读法，S并列−4.5、merge−1.5、引用0/0，不是只有一份被编码为separate |
| L186，未解释变化、没有对照域 | 未解释数保留；“无管辖域”只在当前OPT下成立，不能当真正负对照已经审核 | 4-04/07 D裸cancer −5.8/−4.8；4-09为−8.8；4-06/07其他S −11.4/−7.4；E的4-05/10 not governed为空 |
| L188，来源与预先写定 | 删除不加限定的预先性；更正history来源 | O的A至G可复现；rules哈希固定未覆盖最终实现，history数实际在rule_chain_output而非history_tally_output |

## CREDITED 条文的逐例抽查表

抽样先按输出的预言状态选候选，不要求原来多数正确，这与原引用判据一致，因而表中保留“错误变另一种错误”的反例。为每条取字典序首项，再对指定四条扩展前五项，未按理由是否漂亮挑案例。临时脚本生成过187个候选样本，但人工逐条阅读和本表仅覆盖以下55项，不声称其余132项已获语义核查。

原状态记法：R=跨度标签均对，O=漏标，B=边界错，U=未配对重叠；S/D/M/C是错误预测标签。计数分母均为19。当前预测用实际跨度与标签表示，O没有可观察理由。理由证据中的 `I:L数字` 是 `EA/outputs/20261030_rationale_audit/prediction_index.jsonl` 的物理行号，预测序号在表内为零基。没有理由的提及由gold键及保存预测中无重叠项确认。

“相容”不是“确实造成”；在没有删改对照时，所有行的因果结论均为未验证。“不支持本条”具体指出适用条件或理由不符，而不是因为文字表面不同。

| 样本 | CREDITED条文及输出行 | 原文片段与gold位置 | 原19次状态 → 本次预测 | 已存理由、节号及判断 |
| --- | --- | --- | --- | --- |
| T01 | 1-05 Q1 L63，O:L40 | `9012404:819:833`，gold S；d a family history of cancer , with one case of [[ovarian cancer]] in a first-degree relative . The remaining eight cases ( 89  | R19 → M | I:L9634，预测#8，引用 `Section 1.2(d); Section 3`。相容。亲属中的case明确落在L63排除内；理由直接说明relative frame，不是患者本人。 |
| T02 | 1-05 Q2 L46，O:L41 | `8589723:742:755`，gold S；ed risk of certain types of cancers , including [[breast cancer]] ( 2-4 ) . To investigate whether the presence of rare HRAS1  | R19 → D | I:L9167，预测#5，引用 `Section 1.2 (negative constraint e)`。不支持特指部位词。理由使用unframed list，对应L64；大节1.2匹配不能定位L46。 |
| T03 | 1-05 Q8a L93，O:L44 | `8828602:480:493`，gold M；lex can efficiently transduce the PAH cDNA into [[PAH-deficient]] hepatocytes in vitro , but the application of these vector s | O18/R1 → M | I:L9458，预测#6，引用 `Section 1.1(a); Section 3`。相容。deficient形容词修饰hepatocytes，理由明确区分形容词与缺乏状态名词。 |
| T04 | 4-01 Q4 L72，O:L47 | `8636252:187:230`，gold D；hy ( ALD ) is a genetic disease associated with [[demyelination of the central nervous system]] , adrenal insufficiency , and accumulation of very long chai | O19 → D | I:L13172，预测#5，引用 `1.3`。相容。ALD的associated with列表，理由为病理状态和疾病描述框架，L64-73有规则。 |
| T05 | 4-01 Q6 L343，O:L48 | `8673132:17:35`，gold M；Mice lacking the [[myotonic dystrophy]] protein kinase develop a late onset progressive myopathy. My | R6/O12/S1 → M | I:L13281，预测#0，引用 `Section 3.1`。相容。疾病名作protein kinase前置修饰，理由和L343条件一致。 |
| T06 | 4-01 Q7 L130，O:L49 | `8636252:658:679`，gold D；nd peripheral nerves in young adults ( 35 % ) . [[Adrenal insufficiency]] ( Addisons disease ) is frequently associated with AMN or ce | R16/S2/O1 → S | I:L13179，预测#12，引用 `1.8`。不支持患者分支。理由明确采用Addisons disease同义名路线1.8，不是所编码L130的患者条件。 |
| T07 | 4-01 Q8a L358，O:L50 | `8828602:480:493`，gold M；lex can efficiently transduce the PAH cDNA into [[PAH-deficient]] hepatocytes in vitro , but the application of these vector s | O18/R1 → M | I:L13441，预测#6，引用 `Section 3.2; Section 1.2 (adjectival exception)`。相容。实验细胞样本前的缺乏形容词，理由直接引用3.2与形容词例外。 |
| T08 | 4-02 Q4 L152，O:L52 | `8636252:187:230`，gold D；hy ( ALD ) is a genetic disease associated with [[demyelination of the central nervous system]] , adrenal insufficiency , and accumulation of very long chai | O19 → D | I:L13872，预测#5，引用 `Section 1 - Pathological-state spans in characterization frames; Compositional pathological-state phrases`。相容，但节号解析错。理由引用Section 1与小节标题；输出却找最近列表号2而得到0/9。 |
| T09 | 4-02 Q5 L141，O:L53 | `8589723:613:619`，gold M；11p15 . 5 ) is one possible genetic modifier of [[cancer]] penetrance . Individuals who have rare alleles of the VNTR h | R18/O1 → O，未见重叠预测 | 无可观察理由。范围相容但原因不可观察。cancer在penetrance前作前置修饰，可落L140；漏标无理由，不能证明由此造成。 |
| T10 | 4-04 Q4 L70，O:L58 | `8636252:187:230`，gold D；hy ( ALD ) is a genetic disease associated with [[demyelination of the central nervous system]] , adrenal insufficiency , and accumulation of very long chai | O19 → D | I:L15194，预测#4，引用 `Rule 1c (characterization/etiology predicate; abnormal pathological state)`。相容。疾病特征列表，理由采用characterization与abnormal state，对应1c。 |
| T11 | 4-04 Q6 L120，O:L59 | `8673132:17:35`，gold M；Mice lacking the [[myotonic dystrophy]] protein kinase develop a late onset progressive myopathy. My | R6/O12/S1 → M | I:L15302，预测#0，引用 `Rule 3: Adjacency-based attributive test`。与通用邻接规则相容。理由采用L113的adjacency test；不能单独确认L120的官方名补充作用。 |
| T12 | 4-04 Q7 L57，O:L60 | `8636252:658:679`，gold D；nd peripheral nerves in young adults ( 35 % ) . [[Adrenal insufficiency]] ( Addisons disease ) is frequently associated with AMN or ce | R16/S2/O1 → S | I:L15201，预测#11，引用 `Rule 1b(b)(i) parenthetical co-reference; rule 3 adjacency test`。不支持本分支。理由明确是1b(b)(i)同义名/共指，编码引用却是L57的1b(c)患者分支。 |
| T13 | 4-04 Q8a L38，O:L61 | `8828602:480:493`，gold M；lex can efficiently transduce the PAH cDNA into [[PAH-deficient]] hepatocytes in vitro , but the application of these vector s | O18/R1 → M | I:L15459，预测#5，引用 `Rule 1a (attributive use); Rule 3; Example 25`。相容。deficiency形容词修饰另一名词，理由明确指1a attributive use。 |
| T14 | 4-05 Q1 L161，O:L62 | `9145677:507:520`，gold S； DNA analysis were obtained from 263 women with [[breast cancer]] . Conformation-sensitive gel electrophoresis and DNA sequenc | R19 → M | I:L16401，预测#2，引用 `What NOT 8; 3 Modifier`。相容。263 women with构成研究人群；理由明确采用cohort descriptor和NOT8。 |
| T15 | 4-05 Q4 L157，O:L63 | `8929413:15:37`，gold D；Association of [[anxiety-related traits]] with a polymorphism in the serotonin transporter gene regula | O7/M12 → O，未见重叠预测 | 无可观察理由。不适用。标题中的多词traits不在syndrome feature list，且原来就0/19正确，未贡献新增TP损失。 |
| T16 | 4-05 Q4 L157，O:L63 | `8929413:210:217`，gold D；roxytryptamine or 5-HT ) has been implicated in [[anxiety]] in humans and animal models and is the site of action of wid | O6/R13 → O，未见重叠预测 | 无可观察理由。不适用。implicated in anxiety的普通句子不是syndrome feature list；原13/19正确，新增漏标确实存在，但不能归L157。 |
| T17 | 4-05 Q4 L157，O:L63 | `8929413:850:884`，gold D；ion and 7 to 9 percent of inherited variance in [[anxiety-related personality traits]] in individuals as well as sibships . .  | O7/M12 → O，未见重叠预测 | 无可观察理由。不适用。多词traits是个体差异研究对象，不在syndrome feature list；原本0/19正确。 |
| T18 | 4-05 Q4 L157，O:L63 | `8931709:284:302`，gold D；er characterized by the development of numerous [[adenomatous polyps]] predominantly in the colorectal region . Germline mutations  | R5/S14 → O，未见重叠预测 | 无可观察理由。不支持L157。development of后的病理状态，未形成该条所说的列举；当前无理由。 |
| T19 | 4-05 Q4 L157，O:L63 | `8968760:178:201`，gold D；taxia-telangiectasia ( A-T ) , characterized by [[cerebellar degeneration]] , immunodeficiency and cancer predisposition . A-T carriers  | R15/O4 → O，未见重叠预测 | 无可观察理由。适用性不定。位于characterized by列表，但cerebellar degeneration可能是应保留D的condition-level项；无理由无法裁决。 |
| T20 | 4-05 Q5 L160，O:L64 | `8637912:176:182`，gold M；tate cancer is the second leading cause of male [[cancer]] deaths in the United States . Yet , despite a large internat | D2/O2/R15 → O，未见重叠预测 | 无可观察理由。不支持本条。cancer deaths不是该条的study population或family history；漏标没有理由。 |
| T21 | 4-05 Q7 L19，O:L66 | `8636252:233:254`，gold D；h demyelination of the central nervous system , [[adrenal insufficiency]] , and accumulation of very long chain fatty acids in tissue  | R16/S2/O1 → S | I:L15881，预测#4，引用 `What to Annotate §1 (Specific Disease); §1b(f) not applicable because it is a condition`。不支持本条。adrenal insufficiency不是bare unmodified head，理由说named endocrine condition，引用一般1与1b(f)。 |
| T22 | 4-05 Q7 L19，O:L66 | `8636252:658:679`，gold D；nd peripheral nerves in young adults ( 35 % ) . [[Adrenal insufficiency]] ( Addisons disease ) is frequently associated with AMN or ce | R16/S2/O1 → S | I:L15886，预测#9，引用 `What to Annotate §1 (Specific Disease); §6 Synonymous mentions`。不支持bare/patient条件。句子主语+Addisons同义名，理由用named disease和Section 6。 |
| T23 | 4-05 Q7 L19，O:L66 | `8892662:156:166`，gold D；ith recurrent bacterial infections , especially [[meningitis]] caused by Neisseria meningitidis . We report in this work th | R19 → S | I:L16172，预测#4，引用 `1a`。与L19-21相容。meningitis有明确病因Neisseria，理由提1a；支持病因许可分支，不单独支持患者谓词分支。 |
| T24 | 4-05 Q7 L19，O:L66 | `8929264:1478:1495`，gold D；group of patients with lesions that behave like [[stage III cancers]] . These findings may thus have therapeutic implications in t | B7/S5/R7 → S | I:L16212，预测#7，引用 `§1 Specific Disease; What NOT to Annotate #4`。不适用bare unmodified条件。stage III cancers带修饰，理由采用stage-defined category而非L19。 |
| T25 | 4-05 Q7 L19，O:L66 | `9056547:760:768`，gold D； retardation is not severe , some patients show [[dementia]] or personality disorders , the disease is progressive rather | U12/R7 → S | I:L16331，预测#6，引用 `1a. Patient-anchored bare disease nouns`。相容。bare dementia是some patients show的患者条件，理由明确引用1a；原多为未配对，不能把它算成全额新增TP损失。 |
| T26 | 4-05 Q8a L56，O:L67 | `8828602:480:493`，gold M；lex can efficiently transduce the PAH cDNA into [[PAH-deficient]] hepatocytes in vitro , but the application of these vector s | O18/R1 → M | I:L16136，预测#6，引用 `What to Annotate 1c(a) (adjectival deficit term is Modifier); What to Annotate 3 (Modifiers)`。相容。缺乏形容词修饰hepatocytes，理由明确采用1c(a)形容词例外。 |
| T27 | 4-06 Q1 L150，O:L68 | `8636252:839:842`，gold S；ion of ALD ( 8 % of cases ) . The prevalence of [[ALD]] among adults with Addisons disease remains unknown . To eval | R19 → M | I:L16529，预测#16，引用 `Section 3`。与广义修饰规则相容，存在类推。理由把prevalence类推到risk/population，不能缩写成仅family-history句的效果。 |
| T28 | 4-06 Q2 L29，O:L69 | `8637912:405:424`，gold S；cretory epithelial cells and androgen-dependent [[prostate carcinomas]] undergo apoptosis in response to androgen deprivation and ,  | B19 → D，实际跨度386:424 `androgen-dependent prostate carcinomas` | I:L16539，预测#2，引用 `Section 1.5(c) plural/family heads; Section 1.4 Head-driven condition labeling`。不支持本条造成TP下降。原19次全部边界错；本次更长跨度+D，理由用1.5(c)复数/类别和1.4，不是L29。 |
| T29 | 4-06 Q4 L76，O:L70 | `8931709:284:302`，gold D；er characterized by the development of numerous [[adenomatous polyps]] predominantly in the colorectal region . Germline mutations  | R5/S14 → D | I:L16901，预测#4，引用 `Section 1.3 (characterizing signs, symptoms, and abnormalities)`。相容。FAP characterized by的病理状态，理由明确采用1.3；TP恢复和条文条件能对齐。 |
| T30 | 4-06 Q6 L161，O:L71 | `8673132:17:35`，gold M；Mice lacking the [[myotonic dystrophy]] protein kinase develop a late onset progressive myopathy. My | R6/O12/S1 → M | I:L16630，预测#0，引用 `3.1`。相容。蛋白名内前置疾病名，理由明确为3.1 nomenclature内modifier。 |
| T31 | 4-06 Q8a L68，O:L73 | `8828602:480:493`，gold M；lex can efficiently transduce the PAH cDNA into [[PAH-deficient]] hepatocytes in vitro , but the application of these vector s | O18/R1 → M | I:L16796，预测#6，引用 `Section 1.2(c); Example 29`。相容。缺乏形容词修饰细胞状态，理由明确采用1.2(c)。 |
| T32 | 4-07 Q1 L65，O:L74 | `8589723:202:215`，gold S； ( on chromosome 17q21 ) , have an 80 % risk of [[breast cancer]] and a 40 % risk of ovarian cancer by the age of 70 ( ref . 1 | R19 → M | I:L17180，预测#1，引用 `Section 3 - Context and population frames`。相容。risk of补足语，L65明确包含risk，理由直接采用context-noun complement规则。 |
| T33 | 4-07 Q6 L69，O:L77 | `8673132:17:35`，gold M；Mice lacking the [[myotonic dystrophy]] protein kinase develop a late onset progressive myopathy. My | R6/O12/S1 → M | I:L17318，预测#0，引用 `§3 Disease premodifier within a gene or protein designation`。相容。蛋白名中疾病前置修饰，理由与L69对齐。 |
| T34 | 4-08 Q1 L48，O:L80 | `9145677:714:727`，gold S；in 16 percent of women with a family history of [[breast cancer]] . Only 7 percent of women from families with a history of br | R19 → M | I:L18456，预测#3，引用 `What to Annotate 3 - Modifier (complement of a history frame)`。相容。history of补足语，理由直接采用L48的history frame。 |
| T35 | 4-08 Q4 L104，O:L82 | `8929413:15:37`，gold D；Association of [[anxiety-related traits]] with a polymorphism in the serotonin transporter gene regula | O7/M12 → O，未见重叠预测 | 无可观察理由。不适用。多词标题、非并列列表；原来0/19正确，此变化是M错误变漏标而非新增TP损失。 |
| T36 | 4-08 Q4 L104，O:L82 | `8929413:210:217`，gold D；roxytryptamine or 5-HT ) has been implicated in [[anxiety]] in humans and animal models and is the site of action of wid | O6/R13 → O，未见重叠预测 | 无可观察理由。不适用。单词但不在列表，原13/19正确；不能因同属症状就解释为单词列表例外。 |
| T37 | 4-08 Q4 L104，O:L82 | `8929413:850:884`，gold D；ion and 7 to 9 percent of inherited variance in [[anxiety-related personality traits]] in individuals as well as sibships . .  | O7/M12 → O，未见重叠预测 | 无可观察理由。不适用。多词、非列表，原0/19正确。 |
| T38 | 4-08 Q4 L104，O:L82 | `8931709:284:302`，gold D；er characterized by the development of numerous [[adenomatous polyps]] predominantly in the colorectal region . Germline mutations  | R5/S14 → O，未见重叠预测 | 无可观察理由。不适用。adenomatous polyps是多词，文本也非并列列表；L104明确保留多词表型。 |
| T39 | 4-08 Q4 L104，O:L82 | `8968760:204:220`，gold D； ) , characterized by cerebellar degeneration , [[immunodeficiency]] and cancer predisposition . A-T carriers were reported to be | R16/O2/C1 → O，未见重叠预测 | 无可观察理由。范围相容。单词、列表、疾病描述吻合L104；但无理由，且仍须核对命名疾病/condition例外，不能确认原因。 |
| T40 | 4-08 Q6 L52，O:L83 | `8673132:17:35`，gold M；Mice lacking the [[myotonic dystrophy]] protein kinase develop a late onset progressive myopathy. My | R6/O12/S1 → M | I:L18007，预测#0，引用 `3. Annotate disease mentions that are used as Modifiers for other concepts; Narrower condition and Disease expression inside a nomenclature span`。相容。protein kinase前的疾病名，理由与nomenclature内疾病子串规则相容。 |
| T41 | 4-08 Q7 L11，O:L84 | `8636252:233:254`，gold D；h demyelination of the central nervous system , [[adrenal insufficiency]] , and accumulation of very long chain fatty acids in tissue  | R16/S2/O1 → S | I:L17897，预测#5，引用 `What to Annotate - Item 1 (Specific Disease) and Item 8 (Symptom-level convention)`。不支持患者分支。泛指ALD特征列表，理由是named disorder、后来同义为Addison，不是specific individual。 |
| T42 | 4-08 Q8a L89，O:L85 | `8828602:480:493`，gold M；lex can efficiently transduce the PAH cDNA into [[PAH-deficient]] hepatocytes in vitro , but the application of these vector s | O18/R1 → M | I:L18177，预测#6，引用 `7. Negative Constraint 1 (adjectival [enzyme]-deficient form); 3. Modifiers`。相容。缺乏形容词修饰hepatocytes，理由明确采用酶缺乏形容词规则。 |
| T43 | 4-09 Q1 L158，O:L86 | `8931709:444:447`，gold S； ( APC ) gene are responsible for most cases of [[FAP]] . Mutations at the 5 end of APC are known to be associated w | R19 → M | I:L18966，预测#5，引用 `3; 3.1`。相容。most cases of是cohort descriptor，理由直接说明；引用3/3.1而算法错误要求列表项4。 |
| T44 | 4-09 Q2 L35，O:L87 | `8751855:107:120`，gold S；BRCA1 and BRCA2. The common hereditary forms of [[breast cancer]] have been largely attributed to the inheritance of mutations | R16/D3 → D | I:L18747，预测#1，引用 `1.1`。不支持部位词归因。理由明确采用forms of的种类指代；同节1.1而已，预言D误标总量还下降0.7。 |
| T45 | 4-09 Q3 L105，O:L88 | `8636252:731:734`，gold S；ddisons disease ) is frequently associated with [[AMN]] or cerebral ALD and may remain the only clinical expression  | U13/R6 → S | I:L18592，预测#15，引用 `2; 1.1`。相容。AMN与cerebral ALD各自能独立成病名，理由明确说明stands alone，符合L105。 |
| T46 | 4-09 Q4 L41，O:L89 | `8636252:187:230`，gold D；hy ( ALD ) is a genetic disease associated with [[demyelination of the central nervous system]] , adrenal insufficiency , and accumulation of very long chai | O19 → D | I:L18582，预测#5，引用 `1.2; Principle rule 5`。相容。ALD定义中的病理状态特征，理由明确为generic feature且无固定病名。 |
| T47 | 4-09 Q8a L48，O:L92 | `8828602:480:493`，gold M；lex can efficiently transduce the PAH cDNA into [[PAH-deficient]] hepatocytes in vitro , but the application of these vector s | O18/R1 → M | I:L18852，预测#6，引用 `Section 3; Section 3.1 step 1; Section 1.2 negative constraints; Example 26`。相容。理由明确类比G6PD deficient修饰phenotype，并引用1.2 negative constraints。 |
| T48 | 4-10 Q1 L146，O:L93 | `8589723:202:215`，gold S； ( on chromosome 17q21 ) , have an 80 % risk of [[breast cancer]] and a 40 % risk of ovarian cancer by the age of 70 ( ref . 1 | R19 → M | I:L19233，预测#1，引用 `Section 3c`。相容。risk of关系补足语，理由明确采用3c。不同关系名词仍应分开报告。 |
| T49 | 4-10 Q4 L84，O:L95 | `8636252:233:254`，gold D；h demyelination of the central nervous system , [[adrenal insufficiency]] , and accumulation of very long chain fatty acids in tissue  | R16/S2/O1 → O，未见重叠预测 | 无可观察理由。范围可能相容，不能定因。列表条件吻合，但1c(ii)稳定表型/其他例外未排除；漏标没有理由。 |
| T50 | 4-10 Q4 L84，O:L95 | `8929413:15:37`，gold D；Association of [[anxiety-related traits]] with a polymorphism in the serotonin transporter gene regula | O7/M12 → O，未见重叠预测 | 无可观察理由。不支持本条。标题多词、非manifestation list或multi-step cascade，原0/19正确。 |
| T51 | 4-10 Q4 L84，O:L95 | `8929413:210:217`，gold D；roxytryptamine or 5-HT ) has been implicated in [[anxiety]] in humans and animal models and is the site of action of wid | O6/R13 → O，未见重叠预测 | 无可观察理由。不支持本条。普通implicated in句子，非列表或多步病理链；原13/19正确但新增漏标不能归L84。 |
| T52 | 4-10 Q4 L84，O:L95 | `8929413:850:884`，gold D；ion and 7 to 9 percent of inherited variance in [[anxiety-related personality traits]] in individuals as well as sibships . .  | O7/M12 → O，未见重叠预测 | 无可观察理由。不支持本条。个体traits研究中的多词宾语，没有列表或多步病理链条件，原0/19正确。 |
| T53 | 4-10 Q4 L84，O:L95 | `8931709:284:302`，gold D；er characterized by the development of numerous [[adenomatous polyps]] predominantly in the colorectal region . Germline mutations  | R5/S14 → O，未见重叠预测 | 无可观察理由。未找到L84的列表或多步病理链条件，存在其他许可和例外；漏标无理由，不能定因。 |
| T54 | 4-10 Q5 L191，O:L96 | `8589723:613:619`，gold M；11p15 . 5 ) is one possible genetic modifier of [[cancer]] penetrance . Individuals who have rare alleles of the VNTR h | R18/O1 → O，未见重叠预测 | 无可观察理由。范围相容但原因不可观察。泛称cancer作penetrance前置修饰，L191排除premodifier；遗漏无理由。 |
| T55 | 4-10 Q7 L53，O:L98 | `8636252:658:679`，gold D；nd peripheral nerves in young adults ( 35 % ) . [[Adrenal insufficiency]] ( Addisons disease ) is frequently associated with AMN or ce | R16/S2/O1 → S | I:L19270，预测#10，引用 `1b; 1a(ii)(d); 6`。不支持专指患者分支。理由采用named condition、句子主语和同义名，并引用其他规则；预言D→S仅+0.6。 |

## 第 11 题：能回答什么，最小如何修正

**部分能。** 可以回答“这11次输出的三个标签及所定义类别分别变了多少”“哪些条文和一些具体预测理由相容”；不能可靠回答“某种符号组合由哪种写法造成”“这些就是好的写法”。某一条有清楚实例，不等于足以解释整根柱子，更不等于能识别整组三根柱子的原因。

**先离线，最少完成以下工作。**

1. 保留精确拆分和全部现象，把本批valid100明确当作已用于探索的数据；停止用正负号分组寻找统一原因，撤掉CREDITED自动确认措辞。
2. 从一个最明确的假设开始，例如限定的history补足语。逐指南核实所有重复规则、例外和交叉引用，建立提及级适用/不适用/不确定表。人工编码者可继续不看分数，但问卷的事后来源必须披露。
3. 每个gold保留原19次正确比例、本次实际预测、精确TP贡献以及全部状态转移。正确变预言错误与错误变错误分开；解释新增TP损失的证据必须来自贡献损失的提及。全体相反变化和未解释量一起报告。
4. 用稳定条文ID修正节号和列表号，不把引用率当归因得分。训练惯例按真实适用条件计数，修正history来源，并把unknown和无理由项保留。
5. 冻结一份实际可执行的协议、作用域编码和后续删改diff，记录完整输入与代码哈希。当前数据只作生成假设和查错，不因离线重跑稳定就升级为确认性证据。

**后付费，最小实验是一个条文假设的一对干预。** 选一份确有该条规则的指南，同期运行原样臂与删除/限定该规则臂，删净重复赋值而保留其他内容；预先从文本条件确定目标文档和不应变化的对照类别。每个文档在两臂使用完整原文，重复调用并随机交错，使用新run ID，确认没有缓存复用。记录目标S→M等错误、TP、边界以及FP/FN，避免只看修好的提及。额外反向插入原指南是检查充分性的下一步，不是当前关联分析的替代品。

重复次数须按预期效应、需排除的损失界限和预算事先决定，“再2次”不能保证判清；先用小规模同期重复估方差，再按预定停止条件执行。检验和区间要保留文档配对与运行重复结构。若要得出泛化的“好写法”，还需在从未用于选择写法的材料上，按冻结协议评价目标收益和副作用。本次没有读取heldout50的gold，也没有给出或执行任何付费调用预算。

## 核查记录与边界

### 实际执行

- 在仓库根记录 `git -c safe.directory=H:/Git/research/修論/llm-guideline-moderation-source status --porcelain=v1 --untracked-files=all`。初始有5个已跟踪文件修改和25个未跟踪文件记录，全部作为既有状态保留。没有git restore，因为没有文件内容变化需要恢复。
- 备份 `EA/outputs/` 全部198个文件，合计110,024,673字节。逐文件SHA-256及大小保存在下述仓库外清单，备份保存在同一临时目录的 `backup/`。
- 先检查 `bar_attribution.py → modifier_subset.py → pilot_cases.py` 的调用与读写路径。`pilot_cases.py`读取已有error_rows，不会自动重跑error_table.py；实际重写的是六个分析输出。原脚本读取heldout50文件名名单，以文件名先排除相应训练文件，再读训练gold。
- 在 `H:/Git/research/修論/llm-guideline-moderation-source/todo-temp/error-analysis` 下，以子进程环境变量 `PYTHONHASHSEED=0`、`PYTHONDONTWRITEBYTECODE=1` 执行 `python scripts/bar_attribution.py`，stdout/stderr重定向到仓库外。退出0，stderr 0字节。
- 对198个输出重新计算SHA-256，新增0、删除0、内容变化0。复现前后Git状态逐字相同。无需恢复任何已跟踪或未跟踪文件。
- 外部 `audit.py` 只读取数据，从源文件AST抽取原函数与配置执行，跳过runpy及仓库输出写语句。独立重建的完整rec与保存JSON相等；30×791项严格正确状态直接与3,000份保存预测比较，零不符；99行引文/行号核对零不符；抽查39条CREDITED；复核分类加和、节号测试、引用边界敏感性和训练惯例。
- 所有辅助脚本和中间文件均在仓库外授权暂存目录。最初尝试系统TEMP，写入被沙箱拒绝，随后改用以下已授权路径；没有请求扩大权限或修改执行策略。

暂存目录：`C:/Users/zhouh/.codex/visualizations/2026/11/04/01a1a428-96f0-7ed3-a577-c5708c5f29cf/bar_review_temp/`。

[全部文件的前哈希清单](C:/Users/zhouh/.codex/visualizations/2026/11/04/01a1a428-96f0-7ed3-a577-c5708c5f29cf/bar_review_temp/manifest_before.json)，[后哈希清单](C:/Users/zhouh/.codex/visualizations/2026/11/04/01a1a428-96f0-7ed3-a577-c5708c5f29cf/bar_review_temp/manifest_after.json)，[内容变化列表，空](C:/Users/zhouh/.codex/visualizations/2026/11/04/01a1a428-96f0-7ed3-a577-c5708c5f29cf/bar_review_temp/hash_changes.json)，[初始Git状态](C:/Users/zhouh/.codex/visualizations/2026/11/04/01a1a428-96f0-7ed3-a577-c5708c5f29cf/bar_review_temp/status_before.txt)。

清单按键排序、无额外空白JSON序列化后的SHA-256，前后同为 `4fe84af9a89c1c9b6e0c070af08b18c52de6daf40ac5d1eb17cf84b601125e99`。下列文件的前后哈希均相同，全部198项以完整清单为准。

| 输出文件（EA/outputs下） | 前后相同的SHA-256 |
| --- | --- |
| pilot_cases.json | `6fafecb9be1504fb1e74c3fa6cdaa3f1e9b8533ae06cc466ceab3866a795d2ac` |
| pilot_cases_output.txt | `0c4171549401fc963018852db2d6f437ddebb7c906df8d7514d6632bef726b66` |
| modifier_subset.json | `ea2cbc4029521b604da024972e9f2bcc030e53162476dad36c9b2fa29850610a` |
| modifier_subset_output.txt | `7dd64a6a538b08cb6ffcfc3ee7b87b32c8b503a85f63b86f15a4bbac331b1c98` |
| bar_attribution.json | `6d375eb1a53a7ac7d78813e843744532bd45f7a894d40a70e280fcfc2132f5ff` |
| bar_attribution_output.txt | `cc0b61f9c06ae7f9eff6875dfef6461985daf1eed9587f344b0ab6b0aa0812b4` |
| bar_attribution_rules.json | `6fc87d4c82e24b42602f3c3f16ce67098a1e06de732ead845965116800f2d641` |
| blind_clause_coding.csv | `66929fed1bf39c9d1dbb4db3dfde41d311e0bf8e5731d9dee431ac0045e57743` |

### 未核查或不能从现有材料确认的事项

- 未调用任何付费API或模型，未新增标注，未读 `.env` 或凭据，未读取heldout50 gold，未提交或推送；只读取heldout50的文档文件名名单用于排除。
- 未重新生成3,000条请求或核实提供商内部推理过程；本次核查的是保存预测、已存理由索引与当前分析的一致性。未把模型自述当成内部因果证据。
- 未独立证明编码员的历史盲态、规则首次冻结的真实时间或首次运行后的完整变化数量；当前记录和哈希不能替代原始问卷、代码版本和首次输出。没有据此揣测动机。
- 未对11份指南的全部例子和所有交叉引用做穷尽的人工语义审计；已核查99行引文定位、39条CREDITED相关条件和55项抽查。未给盲编码一致率或算法归因准确率。
- 未打开10/30 PPTX，也未读取相邻项目；核查范围是本仓库保存的柱值定义、正文表格和输出A，不声称已核验幻灯片实际绘制的数据系列与视觉呈现。
- 未做显著性或功效宣告，未执行付费对照，未把训练惯例计数当成推荐写法的效果估计。

最终状态检查：相较初始Git状态，只新增本审查记录；198个既有输出文件仍全部逐字节相同。
