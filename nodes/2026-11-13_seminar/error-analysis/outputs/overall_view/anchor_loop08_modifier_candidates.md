# Modifier 柱高差的条文候选：以 top-4 loop08 为锚点，三类条文差别在大多数指南里反复出现

2026-11-12，离线，未调用 API。Codex 先按指南给出一版候选；这一版逐份重做并复核，Codex 引用的行号和实例全部核对属实，标"（补）"的是复核时补上的候选。以下都是候选，没有删改条文后重标的对照，不说明因果。

**差异位置的定义：** gold 为 Modifier 的位置上，top-4 loop08 标成 Modifier（范围和类型都对），另一份没有。逐条读这些位置，再到两份指南里找管它的条文。位置清单见 `anchor_loop08_modifier_diff_output.txt`，行号是 `../bar_clause_pilot/codex_locate/inputs/guidelines/` 下纯文本指南的行号。

**反复出现的三类：** 病名缩写同时是基因符号（实例都在 VHL 那一篇摘要）；病名和名词之间隔着括号缩写；并列病名先判 CompositeMention。

1. **top-4 loop04**
   - **病名缩写同时是基因符号。** top-4 loop08 第 17、52、259 行规定，定义过的病名缩写修饰 gene 时标 Modifier（例："the DTD gene"）。top-4 loop04 第 120 行前半句也给 Modifier，但同行末句和第 191 行规定基因符号不标。实例：`VHL gene`、`VHL mRNA`，top-4 loop08 标 Modifier，top-4 loop04 没标。
   - **括号挡住修饰关系。** top-4 loop04 第 113、114 行要求紧挨，隔着括号就标 Specific；top-4 loop08 第 46、47 行只看修饰功能。实例：`myotonic dystrophy ( DM ) locus`、`Emery-Dreifuss muscular dystrophy ( EMDM ) patient`，top-4 loop04 标 SpecificDisease。
   - **CompositeMention、DiseaseClass 先判（较弱）。** top-4 loop04 第 117 行规定这两类先按各自定义判，不进入 Modifier 判断；top-4 loop08 没有这种排除，第 159 行规定 Modifier 先于 DiseaseClass。实例：`breast-ovarian cancer families`，top-4 loop04 标 CompositeMention。反例：`breast / ovarian cancer susceptibility gene`，两边标法正好相反。

2. **top-4 loop01**
   - **并列病名先判 CompositeMention。** 第 375、398、425 行；top-4 loop08 没有这条优先级。实例：`breast and ovarian cancer cases`，top-4 loop01 标 CompositeMention。
   - **后面跟着括号缩写的病名标 Specific（补）。** 第 369 行 (iv)，第 371 行规定括号缩写跟全称走。实例：`Emery-Dreifuss muscular dystrophy ( EMDM ) patient`、`hereditary nonpolyposis colorectal cancer ( HNPCC ) kindreds`，top-4 loop01 标 SpecificDisease。
   - **病名缩写同时是基因符号（补）。** 第 355 行：最左边是基因符号而不是病名时，基因前修饰规则不适用。实例：`VHL gene`，top-4 loop01 没标。

3. **top-1 loop07**
   - **正式基因名称里的病名不标。** 第 85、151 至 154 行；top-4 loop08 第 52 行要求单独判断名称里的病名。实例：`myotonic dystrophy protein kinase`、`retinoblastoma gene ( RB1 )`，top-1 loop07 没标。
   - **病名必须直接修饰分子名词。** 第 76 行：中间隔着 susceptibility 就不算。实例：`breast and ovarian cancer susceptibility gene`，top-1 loop07 没标。这个实例同时是并列（第 84 行 (e)），也能被正式基因名称的排除解释，三条分不开。
   - **括号里定义的缩写算单独指称（补）。** 第 80 行 (a)。实例：`myotonic dystrophy ( DM ) locus` 里的 DM，top-1 loop07 标 SpecificDisease。
   - **-deficient 形容词（补，较弱）。** top-4 loop08 第 89、165 行明确规定 `[enzyme]-deficient` 标 Modifier；top-1 loop07 没有对应条文。实例：`HPRT-deficient mice`，top-1 loop07 没标。

4. **top-4 loop09**
   - **只含一个疾病概念才标 Modifier，并列病名先判 CompositeMention。** 第 104、135、267 行。实例：`breast-ovarian cancer families`、`breast-ovarian cancer susceptibility gene`，top-4 loop09 标 CompositeMention。
   - **括号挡住修饰关系（补）。** 第 143 行要求中间不能有括号，第 149 行 (c) 规定括号缩写标 Specific，第 167 行再次强调。实例：`myotonic dystrophy ( DM ) locus`、`Huntington disease (HD) gene` 里的病名，top-4 loop09 标 SpecificDisease。
   - **VHL 不算单独定义的缩写（补，较弱）。** 第 153 行把 "von Hippel-Lindau (VHL) disease" 里的 VHL 算作同一个提及的一部分，而 top-4 loop08 第 52 行只对文中定义过的缩写给 Modifier。实例：`VHL gene`，top-4 loop09 没标。这是间接推测，条文没有直接规定 VHL gene。

5. **top-4 loop02**
   - **括号挡住修饰关系。** 第 231 行 (b)。实例：`Emery-Dreifuss muscular dystrophy ( EMDM ) patient`，top-4 loop02 标 SpecificDisease。
   - **单独的 cancer、tumor 不能标 Modifier。** 第 245、295 行；top-4 loop08 第 137 行保留这两个词。实例：`increased cancer risk`、`cancer penetrance`，top-4 loop02 没标。
   - **并列病名先判 CompositeMention（补）。** 第 227 行规定只有不并列才适用，第 238 行规定 CompositeMention 先按自己的定义判。实例：`breast-ovarian cancer families`，top-4 loop02 标 CompositeMention。
   - **病名缩写同时是基因符号（补）。** 第 233 行 (d)：只是长得像病名缩写、上下文没有确立疾病全称的基因符号不适用。实例：`VHL gene`，top-4 loop02 没标。

6. **top-4 loop05**
   - **正式基因名称里的病名不标。** 第 98、170、171 行。实例：`diastrophic dysplasia sulfate transporter gene`、`myotonic dystrophy protein kinase`，top-4 loop05 没标。
   - **病名缩写同时是基因符号（补）。** 第 95 行：上下文里没有疾病含义的基因或蛋白符号不适用。实例：`VHL gene`，top-4 loop05 没标。
   - **单独的 cancer 描述人群、家族史、风险时不标（补）。** 第 31、159、160 行。实例：`increased cancer risk`、`heritable cancer predisposition`，top-4 loop05 没标。

7. **top-4 loop07**
   - **-deficient 形容词没有明确通则（较弱）。** top-4 loop08 第 89、165 行有通则；top-4 loop07 只有第 252、253 行 `G6PD deficient phenotype` 一个例子。实例：修饰 hepatocytes、mice 的 `PAH-deficient`，top-4 loop07 都没标。
   - 括号（`( EMDM ) patient`、`( DM ) locus`）和并列（`breast-ovarian cancer families`）在这一对里也不同，但 top-4 loop07 没有管这两种情况的条文，找不到来源。

8. **top-4 loop06**
   - **纯符号排除（较弱）。** 第 167 行；第 161 行本身允许缩写。实例：`VHL gene`，top-4 loop06 没标。
   - `pancreatic tumour cell line`、`prostate adenocarcinoma cell line` 里的病名，top-4 loop06 标 SpecificDisease，但两份指南都没写 cell line 怎么处理，找不到来源。

9. **top-1 loop05**
   - **没有明确规定分子名称里的病名要单独判断（较弱）。** top-1 loop05 只有第 84、95 行的一般修饰规则；top-4 loop08 第 52、259 行明确要求单独判断。实例：`myotonic dystrophy protein kinase`、`ND gene`，top-1 loop05 没标。这是写得明确与否的差别，两份没有相反的规定。

10. **top-4 loop10**
    - **正式基因名称里的病名不标。** 第 143、345 行。实例：`diastrophic dysplasia sulfate transporter gene`，top-4 loop10 没标。Codex 用的 `breast-ovarian cancer susceptibility gene BRCA1` 同时受第 135 行（susceptibility 隔开）和第 136 行（并列）管，分不开，所以换了实例。
    - **单独的 cancer、tumor 不标。** 第 139 行 (f)、第 191 行；top-4 loop08 第 137 行。实例：`cancer penetrance`、`tumor foci`，top-4 loop10 没标。
    - **括号挡住修饰关系（补）。** 第 134 行 (a) 规定括号里的定义缩写标 Specific，第 135 行 (b) 规定隔着标点不算修饰。实例：`hereditary nonpolyposis colorectal cancer ( HNPCC ) kindreds`、`myotonic dystrophy ( DM ) locus`，top-4 loop10 标 SpecificDisease。
    - **病名缩写同时是基因符号（补）。** 第 137 行 (d)。实例：`VHL gene`，top-4 loop10 没标。
    - **并列病名先判 CompositeMention（补）。** 第 136 行 (c)。实例：`breast-ovarian cancer families`，top-4 loop10 标 CompositeMention。

## 柱高相近的指南：条文相同的落在同一批提及上，条文不同的只是得失凑巧相近

2026-11-13，离线，未调用 API，没有新脚本。用到上面的候选和位置清单、各指南的逐提及表、11/08 的余弦矩阵，以及报告第 3、4.2、5.1 节。仍是候选，没有删改条文后重标的对照。

**判断方法：** 两份柱高相近的指南，如果在同一批 gold 提及上标得与原指南不同，而且两份都有管这些提及的同一类条文，算同一模式；如果各自变了的提及不同，管它们的条文也不同，柱高相近只是不同提及的得失正好抵消。例子只挑原指南 19 次运行几乎全对（至少 15 次）或从没标对的提及，一次运行的偶然出入不太可能造成这样的差别。余弦取自 11/08 的矩阵：把一份指南在该类每个 gold 提及上的结果减去原指南 19 次的平均，两份指南的这列数方向越一致越接近 1；它没有噪声参照，只比较同一行里的先后。

**Modifier +26.7（top-4 loop04、loop01、loop06，标对数都是 137）：top-4 loop04 与 loop01 是同一模式，top-4 loop06 只是凑巧同高。**
- top-4 loop04、loop01 都写了"-deficient 修饰别的名词标 Modifier"（第 38 行；第 56、358 行），`Atm-deficient mice` 都标对，原指南 19 次从没标对；都写了"并列病名先判 CompositeMention"（第 117 行；第 375 行），`BRCA1 breast and ovarian cancer susceptibility gene` 都标 CompositeMention。两份的余弦 0.65，在各自那一行最高。
- top-4 loop06 在这两处正相反。它的 -deficient 条文只管 phenotype、activity（第 65 行），`Atm-deficient mice` 没标；它没有并列先判，按第 161 行"基因、蛋白名称里的病名标 Modifier"把 susceptibility gene 那一处标对，原指南 19 次从没标对。它少标对的在别处：`prostate adenocarcinoma cell line` 标成 SpecificDisease，原指南 19 次全对；理由写 "not a gene or protein designation"，它的 Modifier 一节只列了人或临床名词（第 150 行）和基因、蛋白名称（第 161 行）两类中心词，这一条是较弱的候选。
- 标对数一样，错标不一样：top-4 loop06 的 Modifier 错标比原指南平均多 32.3 个，另两份只差 −0.7、+1.3 个。top-4 loop06 与这两份的余弦（0.54）在它那一行也最高：三份共有的主体是病名在基因、蛋白名词前这一块（报告第 4.1 节），差别在上面这些地方。

**Modifier +16 左右（top-1 loop07 +15.7、top-4 loop09 +16.7、top-1 loop05 +17.7）：三份各有各的得失，柱高相近是凑巧。**
- 三份里只有 top-1 loop07 把 VHL 那一篇的 13 个全部标对，原指南 19 次一个也没标对。
- 只有 top-4 loop09 写了"病名和名词之间隔着括号就不算修饰"（第 143、149 行），`myotonic dystrophy ( DM ) locus` 中的病名标成 SpecificDisease；原指南 19 次全对，另两份也标对。
- 只有 top-1 loop05 把 `Atm-deficient mice` 标对，它的第 28 行规定描述 phenotype 或 patient 的 -deficient 形容词标 Modifier。
- 三份两两的余弦是 0.21 至 0.22，在各自那一行都排在后半。

**Modifier 接近 0（top-4 loop02 +3.7、loop05 +8.7、loop10 −3.3）：单独 cancer 一块是同一条文、同一批提及。** 三根柱子都在原指南范围内，高低本身可能是波动，但下面这块变化是三份共有的。
- 三份都规定单独的 cancer、tumor 不标 Modifier（top-4 loop02 第 245、295 行，loop05 第 160 行，loop10 第 139、191 行）。8968716 的 `cancer incidence`、`age of cancer onset`，原指南 19 次中分别 16、17 次标对，11 份改后指南里只有这三份没标。
- top-4 loop02 与 loop10 还都写了括号挡住修饰（第 231 行；第 134、135 行），`myotonic dystrophy ( DM ) locus` 中的病名都标 SpecificDisease。两份的余弦 0.66，是整张 Modifier 矩阵里最高的一对。

**SpecificDisease −35 左右（top-1 loop05 −39.2、top-4 loop06 −35.2、top-4 loop07 −34.2）：共有一块，最大的一块不同。** 数字取自报告第 3、4.2、5.1 节。
- 共有：三份都把 history of 这类短语后的病名写成 Modifier（top-1 loop05 第 63 行，top-4 loop06 第 120、150 行，top-4 loop07 第 65 行）；9145677 的 `women with a family history of breast cancer` 三份都标 Modifier，原指南从不标错。
- 不同：top-1 loop05、top-4 loop06 规定部位词不足以让病名算具体疾病，以肿瘤词结尾的 124 个 Specific 中分别有 54、24 个被标成 DiseaseClass，原指南平均 13.0 个。top-4 loop07 第 34 行字面上也这样写，这类错误却只有 14 个，只读条文预测不了这一块。三份两两的余弦 0.26 至 0.28，都不是彼此最近的。

**DiseaseClass：没有柱高相近又超出原指南范围的组。降得最多的 top-4 loop10（−38.8）和 loop05（−21.8）条文相同，是同一模式、程度不同。** 两份都规定列举中的症状不自动标注（第 84 行；第 157 行）、单独的 cancer、tumor 不标（第 191 行；第 160 行）（报告第 3 节）；两份的余弦 0.67，是整张 DiseaseClass 矩阵里最高的一对。

**合起来：** 柱高相近不能当作条文相似的证据，要看变化落在哪些提及上。Modifier 矩阵最高的两对（top-4 loop02 与 loop10、top-4 loop04 与 loop01）和 DiseaseClass 矩阵最高的一对（top-4 loop05 与 loop10），都是写了同一类排除条文的指南。

## 核查记录

- 柱高相近一节（2026-11-13）：逐提及表 `nodes/2026-11-06_seminar/error-analysis/outputs/bar_clause_pilot/<指南>_instances.csv`，按 doc、text、gold_label 查 `n_orig_of_19`（原指南 19 次运行中标对的次数）、`target_state`、`target_pred_label`、`raw_rationale`；某份指南的表里没有这个提及，表示它与原指南 19 次一致（19 次全对且这次也对，或 19 次全错且这次也错）。top-4 loop07、loop08 没有用逐提及表，按位置清单核对。余弦：同目录 `similarity_Modifier.csv`（SHA-256 前 12 位 `3361473ca62f`）、`similarity_DiseaseClass.csv`（`ad5ebf5a9995`）、`similarity_SpecificDisease.csv`（`5500cce78cdc`）。柱高与 Modifier 错标的变化取自 `overall_view_output.txt`。条文行号用 `sed -n` 读 `nodes/2026-11-06_seminar/error-analysis/outputs/bar_clause_pilot/codex_locate/inputs/guidelines/` 下的纯文本指南核对。
- 位置清单：`python nodes/2026-11-13_seminar/error-analysis/scripts/anchor_loop08_modifier_diff.py > nodes/2026-11-13_seminar/error-analysis/outputs/overall_view/anchor_loop08_modifier_diff_output.txt`，输出 SHA-256 前 12 位 `57cf0ce6d396`。输入为 `data/datasets/ncbi_disease/valid/` 的 gold 和 `outputs/ncbi_disease/20261022_haiku-xhigh_*/valid_predictions/`。
- 每一对"只有 top-4 loop08 标对"减"只有另一份标对"的个数，与 `nodes/shared/error-analysis/outputs/loop_label_tables.json` 中两根 Modifier 柱的高度差一致（例如 top-4 loop04：33 减 9 等于 50.74 减 26.74）。
- 条文行号用 `sed -n` 逐条读取核对；实例逐条在位置清单中核对。
