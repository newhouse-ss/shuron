# 已保存理由的逐例语义核查

固定16条实际预测，按四种既有评分状态及原/修改指南各取两条，覆盖16篇文档、9份不同指南文本。两组只读助手各审8例，主助手逐条复核引用和关键适用条件。第一组报告未读取评分材料；第二组先读过含历史gold的项目记录，主助手也已知评分状态，因此本轮不称严格盲审或双人独立编码。本轮未经人工专家复核。语义判断冻结后再合入逐例gold，不以gold反推规则适用。

下列判断分别检查原文、规则应用、标签和边界。gold 只在每例末尾展示，不用来反推理由是否成立。

| 核查关系 | 支持 | 不支持 | 无法确定 | 未说明 |
| --- | ---: | ---: | ---: | ---: |
| 原文与理由 | 12 | 0 | 4 | 0 |
| 指南与理由 | 11 | 0 | 5 | 0 |
| 理由与标签 | 16 | 0 | 0 | 0 |
| 理由与边界 | 4 | 0 | 2 | 10 |
| 指南与预测 | 9 | 0 | 7 | 0 |

## R01：red-blood-cell glucose-6-phosphate dehydrogenase ( G6PD ) deficiency

文档 8808605，运行 `20261022_haiku-xhigh_topk1_loop05`。预测 `SpecificDisease`，字符区间 [363, 431)。

原句上下文：

> e resulting somatic-cell mosaicism creates the opportunity for cell selection . In most people with red-blood-cell glucose-6-phosphate dehydrogenase ( G6PD ) deficiency , the enzyme-deficient phenotype is only moderately expressed in nucleated cells . However , in a s

模型理由：

> Named enzyme (G6PD) argument with state noun 'deficiency' is presented as a condition of a patient group ('people with'), so the whole chain is one Specific Disease span.

模型引用：Section 1.1。

判断：整链规则适用，理由同时解释标签和跨度。

- 原文与理由：支持。原文是 people with 后接完整酶缺乏短语，支持人群病状指称。
- 指南与理由：支持。§1.1 的基因产物参数、患者或人群病状条件及病状与分子属性的裁决条款均适用。
- 理由与标签：支持。理由由酶参数、缺乏状态和人群病状推出 SpecificDisease，与输出一致。
- 理由与边界：支持。whole chain 明确支持整条短语，包括前置修饰、括号简称与末尾 deficiency。
- 指南与预测：支持。整链跨度规则及病状裁决条件支持当前标签与范围；未见分子测量排除项适用。

条文证据：

[原文第 18 至 18 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/9547c3d2ffbaf89cc82a1f5a36c903935c018e35d4445c56e9f595e25f25e301.txt:18)

> A noun phrase headed by a state noun of absence or insufficiency (“deficiency,” “deficiencies,” or “absence”) that takes a gene-product argument (a protein, enzyme, or complement component, named in full or abbreviated form) is annotated as one **Specific Disease** span, including the state noun, when the clause presents the lack as a condition of a patient or population: as its cause, its manifestation, or a genotype-linked state.

[原文第 25 至 25 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/9547c3d2ffbaf89cc82a1f5a36c903935c018e35d4445c56e9f595e25f25e301.txt:25)

> The span covers the whole chain from its first token to its last, including any determiner or ordinal inside the chain. Leading articles outside the chain are not included (see Section 5).

[原文第 29 至 29 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/9547c3d2ffbaf89cc82a1f5a36c903935c018e35d4445c56e9f595e25f25e301.txt:29)

> - **(b) Molecular or biochemical state.** The phrase describes a property of a protein, enzyme, or complement component rather than a condition of the patient: its activity level, catalytic yield, thermal stability, kinetics, or abundance within a cell or tissue. This includes a mechanistic consequence of a mutation stated at the molecular level, and applies to purified or recombinant proteins as well as patient-derived material. Phrases such as “deficient activity of [enzyme]” fall under this sub-case, even when listed among a disease’s features. Such phrases remain **O**; the disease is labeled by its own mention.

[原文第 33 至 33 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/9547c3d2ffbaf89cc82a1f5a36c903935c018e35d4445c56e9f595e25f25e301.txt:33)

> **Tie-breaker.** When a phrase could be read either as a named condition of the patient or as a measured molecular state, annotate it as a condition only if the text uses it to name the patient’s or population’s disorder (e.g., “patients with C7 deficiency,” “G6PD deficiency in African populations”). Otherwise, leave it **O**.

按指南允许的结果：SpecificDisease：red-blood-cell glucose-6-phosphate dehydrogenase ( G6PD ) deficiency，范围 [363, 431)。

与 gold 的独立比较：`boundary`。对应 gold：'glucose-6-phosphate dehydrogenase ( G6PD ) deficiency' (SpecificDisease, [378, 431))。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/9ccf9217bc4f8498bc179cd54f7239a62ac7f9df225ce1a4.json`，原始条目序号 0。

## R02：cancer

文档 8968760，运行 `20261022_haiku-xhigh_e1_run07`。预测 `Modifier`，字符区间 [225, 231)。

原句上下文：

> der ataxia-telangiectasia ( A-T ) , characterized by cerebellar degeneration , immunodeficiency and cancer predisposition . A-T carriers were reported to be moderately cancer-prone . A wide variety of A-T m

模型理由：

> 'Cancer' is a disease mention that modifies the noun phrase 'predisposition', so it is annotated as a Modifier.

模型引用：3. Annotate disease mentions that are used as Modifiers for other concepts。

判断：原指南支持这项修饰语预测；理由没有另行解释边界。

- 原文与理由：支持。原句 cancer predisposition 中 cancer 确实修饰 predisposition。
- 指南与理由：支持。§3 覆盖疾病名修饰其他名词的用法，未限制为示例中的家系；一般词排除项明确保留 cancer。
- 理由与标签：支持。理由由修饰关系推出 Modifier，与预测一致。
- 理由与边界：未说明。理由没有说明跨度边界。
- 指南与预测：支持。§3 与最小跨度原则支持标注 cancer 而不纳入被修饰的 predisposition。

条文证据：

[原文第 28 至 28 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:28)

> A textual string may refer to a disease name, but it may modify a noun phrase (or may not be a noun phrase itself). In such cases, annotate using the **Modifier** category.

[原文第 45 至 45 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:45)

> Use the smallest span necessary to include all tokens expressing the most specific form of the disease.

[原文第 77 至 77 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:77)

>    - However, the terms “cancer” and “tumor” were retained.

按指南允许的结果：Modifier：cancer，范围 [225, 231)。

与 gold 的独立比较：`label`。对应 gold：'cancer predisposition' (DiseaseClass, [225, 246))。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/cc03ab672cb133510aef0a4bb2f94765bf87570814725205.json`，原始条目序号 6。

## R03：aortic rupture

文档 9050868，运行 `20261022_haiku-xhigh_topk4_loop08`。预测 `DiseaseClass`，字符区间 [500, 514)。

原句上下文：

> OL3A1 gene have been implicated as a cause of type IV Ehlers-Danlos syndrome , a disease leading to aortic rupture in early adult life . To directly study the role of Col3a1 in development and disease , we have ina

模型理由：

> Discrete clinical/structural finding (aortic rupture) that is the complement of a causal predicate ('leading to') whose subject is the disease, so it is a generic manifestation tagged as Disease Class.

模型引用：8. Annotate generic manifestations and pathological states as Disease Class。

判断：通用疾病表现条文、理由和预测一致。

- 原文与理由：支持。原文以疾病为 leading to 的主语，aortic rupture 是其临床后果，理由描述与原句相符。
- 指南与理由：支持。§8 包括疾病支配谓词的离散临床或结构异常补足语；病因突变作主语、单词症状列表和主语位置等排除项不适用。
- 理由与标签：支持。理由按通用表现规则推出 DiseaseClass，与输出一致。
- 理由与边界：未说明。理由没有说明完整短语的起止取舍。
- 指南与预测：支持。§8 要求标注完整表现名词短语，包括前置修饰语，支持 aortic rupture。

条文证据：

[原文第 98 至 98 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/0702a16394a0d9c09940086f7d6647b8392ba676ba073d6a76e2fe8820be48ce.txt:98)

> IF a noun phrase’s head denotes a generic clinical manifestation (a sign, symptom, or discrete structural/developmental abnormality) or a generic pathological state (such as a deficiency or dysfunction of a biomolecule expressed through a prepositional complement), with no disease-type head noun and no proper-name disease label, AND the phrase is the complement of a predicate that characterizes a disease or causally links it to a disease-governed subject (e.g., “is characterized by,” “results in,” “is caused by”), THEN tag the full noun phrase, including its premodifiers and prepositional complement, as one **Disease Class** span rather than O.

[原文第 101 至 101 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/0702a16394a0d9c09940086f7d6647b8392ba676ba073d6a76e2fe8820be48ce.txt:101)

> - **Predicate subject.** The predicate’s subject must be the disease, or a finding already attributed to the disease. A predicate whose subject is an etiological lesion that causes the disease (e.g., “a mutation in the NDP gene, which results in a deficiency of X”) does not license the label.

[原文第 103 至 103 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/0702a16394a0d9c09940086f7d6647b8392ba676ba073d6a76e2fe8820be48ce.txt:103)

> - **Processes excluded.** Developmental and pathophysiological process descriptions (e.g., “abnormal retinal vascular development,” or accumulation described as a mechanism step) are biological processes under What NOT to Annotate, item 5. Only discrete clinical findings are tagged.

[原文第 105 至 105 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/0702a16394a0d9c09940086f7d6647b8392ba676ba073d6a76e2fe8820be48ce.txt:105)

> - **Complement position only.** The noun phrase must be a complement of the characterizing predicate. A noun phrase that is the subject of a predicate (e.g., “WT1 dysfunction is implicated in …”) is not tagged.

按指南允许的结果：DiseaseClass：aortic rupture，范围 [500, 514)。

与 gold 的独立比较：`extra`。对应 gold：无重叠 gold。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/546a73458f14705755fcf8affd94442f8ebc5db84963e45a.json`，原始条目序号 1。

## R04：IDDM

文档 9144439，运行 `20261022_haiku-xhigh_topk4_loop07`。预测 `Modifier`，字符区间 [1125, 1129)。

原句上下文：

> eles in the general population suggest that IDDM2 locus is not responsible for the low incidence of IDDM in Japanese . 

模型理由：

> Disease abbreviation is the complement of the context noun 'incidence' in 'low incidence of IDDM in Japanese', a population-frame use, so it is labeled Modifier.

模型引用：3 Context and population frames。

判断：incidence 条文及优先顺序明确支持预测。

- 原文与理由：支持。目标处是 low incidence of IDDM in Japanese，IDDM 确为 incidence 的 of 补足语。
- 指南与理由：支持。§3 点名 incidence 并包含补足语；只对 prevalence 暂缓处理的例外不适用。
- 理由与标签：支持。理由按 context and population frames 推出 Modifier，与输出一致。
- 理由与边界：未说明。理由没有独立讨论跨度。
- 指南与预测：支持。§3 及其相对 §1b 的优先规则支持 Modifier；不需纳入 incidence 或人群词。

条文证据：

[原文第 65 至 65 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/d2677c7f422d5b823b28b9f57876b77316ca55ca9e872fc636c6c18fe2167889.txt:65)

> **Context and population frames.** A disease name that premodifies, or is the complement of, a context or population noun (such as *cases*, *population*, *history*, *risk*, or *incidence*) is annotated **Modifier**. This holds even when the context noun carries its own premodifier, as in *family history of*.

[原文第 67 至 67 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/d2677c7f422d5b823b28b9f57876b77316ca55ca9e872fc636c6c18fe2167889.txt:67)

> - “prevalence of [disease]” frames are not added to this list pending review (see Pending Annotation Review).

[原文第 94 至 94 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/d2677c7f422d5b823b28b9f57876b77316ca55ca9e872fc636c6c18fe2167889.txt:94)

>   - the governing noun is a context or population noun (history, risk, incidence, cases, family, population). Such frames are **Modifier** under §3;

[原文第 112 至 112 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/d2677c7f422d5b823b28b9f57876b77316ca55ca9e872fc636c6c18fe2167889.txt:112)

> 3. §3 context and population frames take precedence over §1b. Cohort, history, risk, and population phrases are **Modifier**.

按指南允许的结果：Modifier：IDDM，范围 [1125, 1129)。

与 gold 的独立比较：`label`。对应 gold：'IDDM' (SpecificDisease, [1125, 1129))。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/93cbb4057d02b9f949f166522e0d69d13fd5f91eb103f72e.json`，原始条目序号 8。

## R05：infantile form

文档 9272171，运行 `20261022_haiku-xhigh_topk1_loop02`。预测 `SpecificDisease`，字符区间 [1710, 1724)。

原句上下文：

> D , 535-573del ) or C-terminus ( L618S ) of the GALC enzyme , whereas the reported mutations in the infantile form ( IF-GLD ) are in the central domain . This difference in mutation sites may affect the clinical fe

模型理由：

> Long form of IF-GLD, referring to the infantile form of globoid cell leukodystrophy, a specific disease form. Annotated separately from the abbreviation.

模型引用：1. Specific Disease / 6. Synonymous mentions。

判断：文内指代可追踪，但省略式名称是否属于可标疾病仍未明确。

- 原文与理由：支持。infantile form 与 IF-GLD 括号配对并和前文成人型对照，支持其在本篇中指向 GLD 婴儿型。
- 指南与理由：无法确定。§6 允许同义长短形式分别标注，但未说明省略疾病名称的 form 短语如何满足疾病提及条件或与一般词排除项衔接。
- 理由与标签：支持。若接受其为 specific disease form 的前提，理由能够推出 SpecificDisease；这不确认该前提被指南许可。
- 理由与边界：支持。理由明确要求与缩写分别标注，解释了止于 form 并排除括号缩写。
- 指南与预测：无法确定。省略式疾病称谓与一般形式描述的准入范围未明确，不能无条件判为应标或不标。

条文证据：

[原文第 6 至 6 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:6)

> A textual string referring to a disease name may refer to a **Specific Disease** or a **Disease Class**.  

[原文第 53 至 53 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:53)

> Abbreviation definitions such as “Huntington disease” (“HD”) are separated into two annotated mentions (one for the long form, one for the abbreviation).

[原文第 76 至 76 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:76)

>    - Very general terms such as “disease,” “syndrome,” “deficiency,” “complications,” “abnormalities,” etc. were excluded.  

按指南允许的结果：若有明确疾病指代、与缩写配对的省略式名称也属于同义提及，可标 SpecificDisease：[1710, 1724)；该准入条件未被原指南直接裁定。

与 gold 的独立比较：`extra`。对应 gold：无重叠 gold。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/80c70eb829294c93aad9d46a2ba65f84a191b692cba0da56.json`，原始条目序号 7。

## R06：leiomyosarcoma

文档 8649785，运行 `20261022_haiku-xhigh_topk1_loop01`。预测 `SpecificDisease`，字符区间 [774, 788)。

原句上下文：

> appear to be remarkable in the spectrum of tumours , and there is loss of the wild-type allele in a leiomyosarcoma from the proband . A cell line has been established from the tumour of the proband and cytogenetic 

模型理由：

> Names a specific malignant tumour type (a sarcoma) that can be linked to one definition, so it is a Specific Disease mention.

模型引用：1. Annotate all Specific Disease mentions。

判断：疾病类别前提未被现有材料独立确认，不能因此直接判错。

- 原文与理由：无法确定。原文支持这是先证者的肿瘤名称，但没有给出恶性属性或无需进一步分类的定义依据。
- 指南与理由：无法确定。理由准确复述 §1 的 SpecificDisease 判据，但尚未独立确认该词满足此判据。 此项同时检查适用前提，不能仅因准确复述定义而判为得到指南支持。
- 理由与标签：支持。接受单一定义的前提后可以推出 SpecificDisease，理由与标签内部一致。
- 理由与边界：未说明。理由只讨论类别，没有说明跨度。
- 指南与预测：无法确定。指南未提供该词的分类定位；肿瘤类型的 SpecificDisease 示例提供类比，但不足以唯一裁定这里的分类粒度。

条文证据：

[原文第 7 至 7 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:7)

> - **Disease Class**: Mentions that could be described as a family of multiple specific diseases.  

[原文第 8 至 8 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:8)

> - **Specific Disease**: Mentions that can be linked to one specific definition that does not include further categorization.

[原文第 45 至 45 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:45)

> Use the smallest span necessary to include all tokens expressing the most specific form of the disease.

[原文第 113 至 113 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:113)

> 7. **“colorectal, endometrial, and ovarian cancers”**  

[原文第 114 至 114 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:114)

>    - Considered one **Composite Mention** of several Specific Diseases.

按指南允许的结果：leiomyosarcoma 的词项范围 [774, 788) 可识别；现有材料未唯一裁定 SpecificDisease 与 DiseaseClass 的粒度。

与 gold 的独立比较：`correct`。对应 gold：'leiomyosarcoma' (SpecificDisease, [774, 788))。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/32b85637363bf182d715f475a8a15654066469c5701ace9b.json`，原始条目序号 2。

复核说明：主助手复核收窄：初判的“支持”仅针对正确转述规则；本项还要求确认当前实例满足该规则，因此改为“无法确定”。此调整在合入本轮逐例 gold 前完成。

## R07：breast cancer

文档 8751855，运行 `20261022_haiku-xhigh_e1_run06`。预测 `SpecificDisease`，字符区间 [107, 120)。

原句上下文：

>  heterogeneity in hereditary breast cancer: role of BRCA1 and BRCA2.
> The common hereditary forms of breast cancer have been largely attributed to the inheritance of mutations in the BRCA1 or BRCA2 genes . However 

模型理由：

> Breast cancer is a named disease that can be linked to one specific definition without further categorization in the phrase 'forms of breast cancer'. Annotated as Specific Disease.

模型引用：What to Annotate 1 - Specific Disease。

判断：标签与理由一致，但分类及修饰结构的规则应用仍有未决前提。

- 原文与理由：无法确定。原文确有 hereditary forms of breast cancer，但没有证明 breast cancer 满足无需进一步分类的条件；forms 也不自动意味着多个独立疾病。
- 指南与理由：无法确定。理由复述 §1 判据，未解决分类粒度；§3 的宽泛修饰描述是否涉及 forms of 的补足语，也没有在此被明确裁定。
- 理由与标签：支持。理由所声称的具体定义前提可以推出 SpecificDisease，标签与该前提相符。
- 理由与边界：未说明。理由没有说明是否纳入 hereditary forms of。
- 指南与预测：无法确定。疾病分类层级、of 补足语与形式限定的跨度均未被指南唯一裁定；不能仅凭 forms 宣布预测违反规则。

条文证据：

[原文第 7 至 7 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:7)

> - **Disease Class**: Mentions that could be described as a family of multiple specific diseases.  

[原文第 8 至 8 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:8)

> - **Specific Disease**: Mentions that can be linked to one specific definition that does not include further categorization.

[原文第 28 至 28 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:28)

> A textual string may refer to a disease name, but it may modify a noun phrase (or may not be a noun phrase itself). In such cases, annotate using the **Modifier** category.

[原文第 45 至 45 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:45)

> Use the smallest span necessary to include all tokens expressing the most specific form of the disease.

[原文第 113 至 113 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:113)

> 7. **“colorectal, endometrial, and ovarian cancers”**  

[原文第 114 至 114 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:114)

>    - Considered one **Composite Mention** of several Specific Diseases.

按指南允许的结果：不能唯一确认标签或范围。breast cancer 为 [107, 120)，是否纳入 hereditary forms of 仍待裁定，不能把替代范围当作已确认答案。

与 gold 的独立比较：`correct`。对应 gold：'breast cancer' (SpecificDisease, [107, 120))。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/e3916bfc02242b05d23abb059e5599b6d6a13362a86caed1.json`，原始条目序号 1。

## R08：cardiac and muscle symptoms

文档 8845838，运行 `20261022_haiku-xhigh_topk4_loop04`。预测 `CompositeMention`，字符区间 [1310, 1337)。

原句上下文：

> owed that VLCAD is most abundant in heart and skeletal muscle . This agrees well with the fact that cardiac and muscle symptoms are characteristic for patients with VLCAD deficiency . Northern blot analysis and sequencing of cl

模型理由：

> Coordinated premodifiers 'cardiac' and 'muscle' share one finding head 'symptoms' and act as the argument of the characterization predicate 'characteristic for' in a clause describing VLCAD deficiency, so the coordinated shared-head span is a Composite Mention rather than a Disease Class.

模型引用：Section 2 Composite Mention (coordinated premodifiers over a non-disease head); Section 1c exclusion (i)。

判断：标签竞争已有明确优先规则，预测有完整条文支持。

- 原文与理由：支持。cardiac 和 muscle 由 and 连接、共享 symptoms，并被描述为 VLCAD deficiency 患者的特征。
- 指南与理由：支持。§2 明确覆盖共享非疾病性病理或表现中心词的并列前置修饰语，§1c(i) 与优先规则又让 Composite 优先。
- 理由与标签：支持。理由按共享中心词结构推出 CompositeMention，并引用 DiseaseClass 规则的排除项。
- 理由与边界：支持。理由明确选取整个共享中心词结构，解释保留两个修饰语、连接词和 symptoms。
- 指南与预测：支持。完整短语直接满足 §2；与 DiseaseClass 的标签竞争已由优先条款解决。

条文证据：

[原文第 82 至 82 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/8834ea8307a07ffe54f8f6f6c611563513a94e624656d9a445e878f5c6a24345.txt:82)

>   - (i) The phrase is a coordinated set of premodifiers over one shared pathological head, which is a **Composite Mention** under rule 2.

[原文第 92 至 92 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/8834ea8307a07ffe54f8f6f6c611563513a94e624656d9a445e878f5c6a24345.txt:92)

> **Coordinated premodifiers over a non-disease head.** If a span contains a coordinating conjunction ("and," "or") that joins two or more premodifiers which together modify one shared head noun, and that head denotes a pathological process, finding, or change rather than a disease name or disease category, the full coordinated span is one **Composite Mention**, not Disease Class. An adjacent Disease Class mention or a parenthetical does not change this label.

[原文第 171 至 171 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/8834ea8307a07ffe54f8f6f6c611563513a94e624656d9a445e878f5c6a24345.txt:171)

>    - A bare general term stays excluded even inside a characterizing clause or as an anaphor (e.g., "this condition"). "Deficiency" and "abnormalities" qualify only as part of a specific nominal under rule 1a or rule 1c (e.g., "C7 deficiency" or "abnormal retinal vascular development"), never on their own.

[原文第 209 至 209 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/8834ea8307a07ffe54f8f6f6c611563513a94e624656d9a445e878f5c6a24345.txt:209)

> 7. **Coordinated shared-head premodifiers before manifestations.** A coordinated set of premodifiers over one shared pathological head is a **Composite Mention** under rule 2 and is excluded from rule 1c (exclusion (i)). A coordinated set joining disease-name heads is not reclassified by this item (rule 2, exclusion (a)).

按指南允许的结果：CompositeMention：cardiac and muscle symptoms，范围 [1310, 1337)。

与 gold 的独立比较：`extra`。对应 gold：无重叠 gold。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/e4d2c51a2d9f2435961a3bf36f4da10cb9d8d99d54ae5476.json`，原始条目序号 0。

## R09：autosomal recessive disorder

文档 8828602，运行 `20261022_haiku-xhigh_topk4_loop01`。预测 `DiseaseClass`，字符区间 [74, 102)。

原句上下文：

> Gene therapy for phenylketonuria.
> Classical phenylketonuria ( PKU ) is an autosomal recessive disorder caused by a deficiency of hepatic phenylalanine hydroxylase ( PAH ) . Limitations of the current di

模型理由：

> Inheritance-pattern category denoting a family of disorders; the inheritance modifier does not anchor it to one condition.

模型引用：Section 1.1 (Example 10)。

判断：适用条件明确，高置信度。预测有指南依据，边界理由未陈述。

- 原文与理由：支持。原文在概括 PKU 的疾病属性，并非描述某位患者的诊断；autosomal recessive 表示遗传方式，理由的类别解释与此相符。
- 指南与理由：支持。§1.1 明确规定遗传方式限定词不把类别限定为一个具体疾病，Example 31 还直接将相同词组标为 DiseaseClass。
- 理由与标签：支持。理由将该词组解释为疾病家族，能够推出所给 DiseaseClass 标签。
- 理由与边界：未说明。理由讨论类别和遗传限定词，没有说明跨度为何在 disorder 后结束。
- 指南与预测：支持。该处符合遗传类别表述，没有患者诊断、分子修饰或并列结构触发更优先规则；完整类别词组可标为 DiseaseClass。

条文证据：

[原文第 2 至 2 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/documents/8828602.txt:2)

> Classical phenylketonuria ( PKU ) is an autosomal recessive disorder caused by a deficiency of hepatic phenylalanine hydroxylase ( PAH ) .

[原文第 24 至 24 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/a094230a404147d3aa7e3ab2e06659c744db8e4e9453dcb58dff17a64043939f.txt:24)

> An inheritance pattern such as "autosomal recessive" or "X-linked" narrows the class but does not pick out one condition, and it is not a subtype qualifier.

[原文第 629 至 629 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/a094230a404147d3aa7e3ab2e06659c744db8e4e9453dcb58dff17a64043939f.txt:629)

> "autosomal recessive disorder" as **Disease Class** (Example 10).

按指南允许的结果：DiseaseClass：autosomal recessive disorder，范围 [74, 102)。

与 gold 的独立比较：`correct`。对应 gold：'autosomal recessive disorder' (DiseaseClass, [74, 102))。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/1cf86e6ab55efa441d5d535615db25f922c616258c7aec69.json`，原始条目序号 3。

## R10：lymphoreticular disease

文档 8666397，运行 `20261022_haiku-xhigh_e1_run09`。预测 `DiseaseClass`，字符区间 [943, 966)。

原句上下文：

> sf ) . This localization makes Wasp a candidate for involvement in scurfy , a T cell-mediated fatal lymphoreticular disease of mice that has previously been proposed as a mouse homolog of Wiskott-Aldrich syndrome . Northern

模型理由：

> Lymphoreticular disease denotes a family of multiple lymphoreticular disorders rather than one specific disease, so it is a Disease Class mention.

模型引用：What to Annotate > 1. Specific Disease mentions (Disease Class definition)。

判断：适用前提未决，中等置信度。不能把理由中的类别断言直接当作文本证据，也不能仅因出现 scurfy 就否定类别读法。

- 原文与理由：无法确定。原文用该短语描述 scurfy，但没有证明 lymphoreticular disease 涵盖多个疾病；这个同位语既可能分类，也可能重述具体疾病。
- 指南与理由：无法确定。理由准确使用了§1的疾病家族定义，但指南没有直接确认该词组满足这个前提。 此项同时检查适用前提，不能仅因准确复述定义而判为得到指南支持。
- 理由与标签：支持。若接受理由所述的多疾病家族前提，DiseaseClass 随之成立；这是内部一致性判断。
- 理由与边界：未说明。理由没有解释为何不包含前置的 T cell-mediated 或其他限定成分。
- 指南与预测：无法确定。仅凭指定材料不能确定这里是上位类别还是单一疾病称谓；§5也没有直接解决 T cell-mediated 是否属于最具体疾病形式。

条文证据：

[原文第 2 至 2 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/documents/8666397.txt:2)

> This localization makes Wasp a candidate for involvement in scurfy , a T cell-mediated fatal lymphoreticular disease of mice that has previously been proposed as a mouse homolog of Wiskott-Aldrich syndrome .

[原文第 7 至 7 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:7)

> Mentions that could be described as a family of multiple specific diseases.

[原文第 8 至 8 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:8)

> Mentions that can be linked to one specific definition that does not include further categorization.

[原文第 45 至 45 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:45)

> Use the smallest span necessary to include all tokens expressing the most specific form of the disease.

按指南允许的结果：分类粒度及限定词边界均未唯一确定，不提出确定更正。

与 gold 的独立比较：`boundary`。对应 gold：'fatal lymphoreticular disease' (DiseaseClass, [937, 966))。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/8c5d111719a5c8818060fb0c7e8c4e0fbe3ba2ce3d9df8b3.json`，原始条目序号 3。

复核说明：主助手复核收窄：初判的“支持”仅针对正确转述规则；本项还要求确认当前实例满足该规则，因此改为“无法确定”。此调整在合入本轮逐例 gold 前完成。

## R11：AO2 or DTD

文档 8931695，运行 `20261022_haiku-xhigh_topk1_loop10`。预测 `CompositeMention`，字符区间 [1701, 1711)。

原句上下文：

> codons reduce mRNA levels . The presence of the DTDST R279W mutation in a total of 11 patients with AO2 or DTD emphasizes the overlap between these conditions . This mutation has not been found so far in 8 anal

模型理由：

> Contiguous string with two separate specific diseases (AO2 or DTD) joined by a coordinating conjunction, annotated as one Composite Mention

模型引用：2. Annotate contiguous text strings (Composite Mention)。

判断：正文支持，中高置信度。示例说明共享词头的一种情况，不构成排除完整疾病缩写的规则。

- 原文与理由：支持。全文分别定义 AO2 和 DTD，目标句也将二者作为由 or 连接的两种情况，符合理由所述结构。
- 指南与理由：支持。§2正文广泛覆盖包含两个或更多疾病提及的字符串，没有明文要求必须共享词头；不能仅凭 Duchenne 示例添加这一必要条件。
- 理由与标签：支持。两个疾病组成连续并列字符串，按所引正文可以推出 CompositeMention。
- 理由与边界：支持。理由明确说明把 AO2、or 和 DTD 合并成一个连续提及，对实际合并边界给出了依据。
- 指南与预测：支持。AO2 or DTD 满足§2正文，既不是两个同义名称，也没有嵌套内容打断；指南未明确排除完整缩写之间的并列。

条文证据：

[原文第 2 至 2 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/documents/8931695.txt:2)

> diastrophic dysplasia ( DTD ) , atelosteogenesis type 2 ( AO2 )

[原文第 2 至 2 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/documents/8931695.txt:2)

> The presence of the DTDST R279W mutation in a total of 11 patients with AO2 or DTD emphasizes the overlap between these conditions .

[原文第 20 至 20 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:20)

> A textual string may refer to two or more separate disease mentions. Such mentions are annotated with the **Composite Mention** category.

[原文第 23 至 23 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:23)

> because the word “Duchenne” on its own is not a disease mention.

按指南允许的结果：CompositeMention：AO2 or DTD，范围 [1701, 1711)。此为指南正文允许的合并读法，不代表与 gold 一致。

与 gold 的独立比较：`label`。对应 gold：'AO2' (SpecificDisease, [1701, 1704))。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/be17aea25d2bb2dd4d6abc3570797ae9e88d0816030e06ba.json`，原始条目序号 17。

## R12：breast and ovarian cancer

文档 8640236，运行 `20261022_haiku-xhigh_topk1_loop04`。预测 `CompositeMention`，字符区间 [469, 494)。

原句上下文：

> he familial forms . An exception is BRCA1 , which contributes to a significant fraction of familial breast and ovarian cancer , but undergoes mutation at very low rates in sporadic breast and ovarian cancers . This finding su

模型理由：

> The contiguous string contains two separate specific diseases (breast cancer and ovarian cancer) and must be annotated as one Composite Mention.

模型引用：What to Annotate 2 - Contiguous text strings (Composite Mention)。

判断：外边界歧义，中等置信度。标签依据成立，不能把未解释 familial 的处理直接判为推理错误。

- 原文与理由：支持。breast 和 ovarian 共享 cancer，理由对两个癌症概念的展开符合原句。
- 指南与理由：支持。§2及其共享词头示例支持把这两个疾病概念合并标为 CompositeMention。
- 理由与标签：支持。理由能够推出 CompositeMention 类型，没有把该并列表达误说成一个疾病概念。
- 理由与边界：无法确定。理由说明了为何合并并列项，但未处理紧邻的 familial，不能据此单独确认完整外边界。
- 指南与预测：无法确定。合并类型有依据；§5要求保留最具体形式的必要词，而全文又对照 familial 和 sporadic，是否应纳入 familial 尚未由指南唯一确定。

条文证据：

[原文第 2 至 2 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/documents/8640236.txt:2)

> An exception is BRCA1 , which contributes to a significant fraction of familial breast and ovarian cancer , but undergoes mutation at very low rates in sporadic breast and ovarian cancers .

[原文第 20 至 20 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:20)

> A textual string may refer to two or more separate disease mentions. Such mentions are annotated with the **Composite Mention** category.

[原文第 45 至 45 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:45)

> Use the smallest span necessary to include all tokens expressing the most specific form of the disease.

[原文第 143 至 143 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:143)

> May or may not include “inherited,” depending on the annotator.

按指南允许的结果：CompositeMention 标签得到支持；是否纳入 familial 未被唯一裁定，不把两种跨度认作无条件可互换。

与 gold 的独立比较：`boundary`。对应 gold：'familial breast and ovarian cancer' (CompositeMention, [460, 494))。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/a77f24e99362135be7f48eb4048317fc4bd6efca7c1a9e8b.json`，原始条目序号 5。

## R13：cancer

文档 8968716，运行 `20261022_haiku-xhigh_topk4_loop06`。预测 `Modifier`，字符区间 [1389, 1395)。

原句上下文：

> hism detected one additional instance in a woman with breast cancer diagnosed at age 77 years , and cancer in one parent . R841W is likely to be an etiologically significant lesion with involvement in close

模型理由：

> 'cancer in one parent' is a family-history construction that assigns the condition to a relative, so the disease term is a Modifier.

模型引用：Section 3 and Section 1.4(c)。

判断：不同适用条件已由例外与优先规则区分，中高置信度。未发现此处与 DiseaseClass 规则构成冲突。

- 原文与理由：支持。目标 cancer 明确发生在该女性的一位父母身上，理由关于亲属病史归属的解释符合原文。
- 指南与理由：支持。§3一般性包含家族史结构，§1.4(c)又排除已属 Modifier 的家族史词组；其适用范围不限于字面出现 family history of 的示例。
- 理由与标签：支持。按该指南的家族史约定，所述亲属疾病归属能够支持 Modifier 标签。
- 理由与边界：未说明。理由说明为什么使用 Modifier，没有独立讨论癌症词与 in one parent 的跨度边界。
- 指南与预测：支持。该癌症提及承担亲属病史功能，§3与§1.4(c)适用；§1.6明确排除用较宽的疾病类别规则重标 Modifier。

条文证据：

[原文第 2 至 2 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/documents/8968716.txt:2)

> a woman with breast cancer diagnosed at age 77 years , and cancer in one parent

[原文第 150 至 150 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/8893b2fb9b8c95539b9fc5d35e47b0b570f3ee3a310bbbea71971fa6d05be91e.txt:150)

> A textual string may refer to a disease name, but it may modify a noun phrase (or may not be a noun phrase itself). In such cases, annotate using the **Modifier** category.

[原文第 150 至 150 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/8893b2fb9b8c95539b9fc5d35e47b0b570f3ee3a310bbbea71971fa6d05be91e.txt:150)

> and disease names in family-history constructions (e.g., “a family history of ovarian cancer”).

[原文第 102 至 102 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/8893b2fb9b8c95539b9fc5d35e47b0b570f3ee3a310bbbea71971fa6d05be91e.txt:102)

> The span is already **Specific Disease** (a named disease) or **Modifier** (a disease term used attributively inside a larger named disease, or inside a case, population, or family-history phrase; see Section 3).

[原文第 135 至 135 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/8893b2fb9b8c95539b9fc5d35e47b0b570f3ee3a310bbbea71971fa6d05be91e.txt:135)

> Modifier spans (Section 3) are excluded from steps 5 to 9.

按指南允许的结果：Modifier：cancer，范围 [1389, 1395)。家族史规定按含义适用，不要求出现字面的 family history of。

与 gold 的独立比较：`label`。对应 gold：'cancer' (DiseaseClass, [1389, 1395))。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/7f4bca1846ed85d07b5c3d960704c2e3f345f120a1363508.json`，原始条目序号 8。

## R14：Duarte

文档 9012409，运行 `20261022_haiku-xhigh_topk1_loop03`。预测 `Modifier`，字符区间 [307, 313)。

原句上下文：

> cusing and 50 % reduction in galactose-1-phosphate uridyltransferase ( GALT ) enzyme activity . The Duarte biochemical phenotype has a molecular genotype of N314D / N314D . The characteristic Duarte isoform

模型理由：

> Disease name used as a modifier of the noun phrase biochemical phenotype.

模型引用：3. Annotate disease mentions used as Modifiers。

判断：疾病指称前提未决，中等置信度。句法修饰关系清楚，不能用它替代疾病身份判断。

- 原文与理由：无法确定。Duarte 修饰 biochemical phenotype 的句法关系明确，但全文也将其用于 enzyme variant；单独 Duarte 是否确实指称疾病仍有解释空间。
- 指南与理由：无法确定。§3确实要求将修饰其他概念的疾病名称标为 Modifier，但它以该词首先属于疾病提及为前提。 此项同时检查适用前提，不能仅因准确复述定义而判为得到指南支持。
- 理由与标签：支持。若 Duarte 是疾病名称，理由中的修饰关系足以推出 Modifier；理由与输出标签内部一致。
- 理由与边界：未说明。理由没有解释为何只有 Duarte 构成疾病跨度。
- 指南与预测：无法确定。原文支持 Duarte 与 galactosemia 变体相关，但关联本身尚不能排除其只是酶变体名称；原版指南未给出这种缩略名称的明确消歧条件。

条文证据：

[原文第 1 至 1 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/documents/9012409.txt:1)

> Molecular basis for Duarte and Los Angeles variant galactosemia.

[原文第 2 至 2 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/documents/9012409.txt:2)

> the Duarte enzyme variant of galactosemia ( D / D )

[原文第 2 至 2 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/documents/9012409.txt:2)

> The Duarte biochemical phenotype has a molecular genotype of N314D / N314D .

[原文第 28 至 28 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt:28)

> A textual string may refer to a disease name, but it may modify a noun phrase (or may not be a noun phrase itself). In such cases, annotate using the **Modifier** category.

按指南允许的结果：若 Duarte 在此指疾病变体简称，Modifier 有条件成立；若只指酶变体则不标。现有指南未充分裁定这一前提。

与 gold 的独立比较：`extra`。对应 gold：无重叠 gold。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/04339970d7e1f70634408703e633e66bd5fb997e3dd14dea.json`，原始条目序号 2。

复核说明：主助手复核收窄：初判的“支持”仅针对正确转述规则；本项还要求确认当前实例满足该规则，因此改为“无法确定”。此调整在合入本轮逐例 gold 前完成。

## R15：breast / ovarian cancer

文档 8841191，运行 `20261022_haiku-xhigh_topk1_loop07`。预测 `CompositeMention`，字符区间 [367, 390)。

原句上下文：

> . Mutations in BRCA1 account for approximately 45 % of familial breast cancer and 90 % of inherited breast / ovarian cancer , whereas mutations in BRCA2 account for a comparable percentage of inherited breast cancer cases .

模型理由：

> The contiguous string 'breast / ovarian cancer' refers to two separate diseases (breast cancer and ovarian cancer), so it is annotated as one Composite Mention rather than as separate strings.

模型引用：What to Annotate Section 2 (Composite Mention)。

判断：外边界歧义，中等置信度。合并解释成立，未说明 inherited 的处理不等于已经证明边界错误。

- 原文与理由：支持。breast / ovarian 共享 cancer，原文没有明确把整个表达定义为一个固定综合征名称，理由的两个疾病概念读法有文本依据。
- 指南与理由：支持。§2正文支持把包含两个疾病概念的连续字符串标为 CompositeMention，相关新增规则也未改变此处的合并类别。
- 理由与标签：支持。按理由所述的两个独立疾病概念，CompositeMention 与其推论一致。
- 理由与边界：无法确定。理由明确反对拆开并列项，但没有说明为何排除前置 inherited，因而没有完整解决外边界。
- 指南与预测：无法确定。CompositeMention 类型有支持；§5要求最具体形式，Example 16 又允许某些 inherited 限定词留取，因此本处边界不能唯一裁定。

条文证据：

[原文第 2 至 2 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/documents/8841191.txt:2)

> Mutations in BRCA1 account for approximately 45 % of familial breast cancer and 90 % of inherited breast / ovarian cancer , whereas mutations in BRCA2 account for a comparable percentage of inherited breast cancer cases .

[原文第 54 至 54 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/8635714314660d4a8438714d0144aca92997ad015286208a7556398cde35afe5.txt:54)

> A textual string may refer to two or more separate disease mentions. Such mentions are annotated with the **Composite Mention** category.

[原文第 96 至 96 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/8635714314660d4a8438714d0144aca92997ad015286208a7556398cde35afe5.txt:96)

> Use the smallest span necessary to include all tokens expressing the most specific form of the disease.

[原文第 213 至 213 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/8635714314660d4a8438714d0144aca92997ad015286208a7556398cde35afe5.txt:213)

> May or may not include "inherited," depending on the annotator.

按指南允许的结果：CompositeMention 标签得到支持；是否纳入 inherited 未被唯一裁定，不提出确定更正。

与 gold 的独立比较：`boundary`。对应 gold：'inherited breast / ovarian cancer' (CompositeMention, [357, 390))。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/4312553ada97527732c5dca641c340c53e9ee000afc4b786.json`，原始条目序号 3。

## R16：genetic disease

文档 8636252，运行 `20261022_haiku-xhigh_topk4_loop09`。预测 `DiseaseClass`，字符区间 [155, 170)。

原句上下文：

> iopathic Addison's disease in young adult male patients.
> X-Linked adrenoleukodystrophy ( ALD ) is a genetic disease associated with demyelination of the central nervous system , adrenal insufficiency , and accumulat

模型理由：

> Class-membership frame ('is a genetic disease') that refers to a category of diseases rather than one specific condition.

模型引用：1.1。

判断：适用条件明确，高置信度。类别规则与诊断目标规则已有明确分界，边界理由未陈述。

- 原文与理由：支持。原文以 ALD is a genetic disease 说明疾病的类别归属，目标词组没有在该句中承担个体患者的诊断角色。
- 指南与理由：支持。§1.1明确把类别归属框架列入 DiseaseClass；§1.4排除条款也阻止将这类表述提升为诊断目标。
- 理由与标签：支持。所述类别归属解释能直接推出 DiseaseClass。
- 理由与边界：未说明。理由只讨论类别归属，没有单独解释 genetic disease 的边界。
- 指南与预测：支持。目标是带 genetic 限定的类别表述，符合§1.1；SpecificDisease 的诊断目标规则在此被§1.4明确排除。

条文证据：

[原文第 2 至 2 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/documents/8636252.txt:2)

> X-Linked adrenoleukodystrophy ( ALD ) is a genetic disease associated with demyelination of the central nervous system , adrenal insufficiency , and accumulation of very long chain fatty acids in tissue and body fluids .

[原文第 30 至 30 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/dbca220f1e3148d187b71f3997537495a841d4402a9492be06ec9faeb6f6c2a7.txt:30)

> the phrase is a superordinate category reference that enumerates or classifies kinds of disease (introduced by “such as,” “including,” “types of,” or a class-membership frame, e.g., “is an autosomal recessive disease”); or

[原文第 89 至 89 行](H:/Git/research/修論/llm-guideline-moderation-source/nodes/shared/error-analysis/outputs/20261030_rationale_audit/guidelines/dbca220f1e3148d187b71f3997537495a841d4402a9492be06ec9faeb6f6c2a7.txt:89)

> The span belongs to a class-membership or enumerating frame (“is an autosomal recessive disorder,” “is a syndromal X-linked mental retardation,” “such as,” “types of”). These are **Disease Class** under Section 1.1 (Examples 10 and 12).

按指南允许的结果：DiseaseClass：genetic disease，范围 [155, 170)。

与 gold 的独立比较：`correct`。对应 gold：'genetic disease' (DiseaseClass, [155, 170))。

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/1fdeaf26f6efe292a395d9ebc1cf70ddf5cd270919d811db.json`，原始条目序号 4。
