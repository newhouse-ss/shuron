# Type-text pilot: units judged to affect Modifier (run in working tree; other run = commit df42249)

## original

| line | other run | in pair file | types | text | reason |
| --- | --- | --- | --- | --- | --- |
| 28 | yes |  | Modifier;SpecificDisease;DiseaseClass | A textual string may refer to a disease name, but it may modify a noun phrase (or may not be a noun phrase itself). | 病名修饰其他名词的语法角色会改变疾病标签。 |
| 28 | yes |  | Modifier;SpecificDisease;DiseaseClass | In such cases, annotate using the **Modifier** category. | 上述修饰用法标 Modifier，区别独立的具体疾病或疾病家族。 |
| 31 | yes |  | Modifier;SpecificDisease;DiseaseClass | > Although this mutation was initially detected in four of 33 colorectal cancer families analysed from eastern England, more extensive analysis has reduced the frequency to four of 52 English HNPCC kindreds analysed. | 示范病名修饰 families 和 kindreds 的 Modifier 用法。 |
| 34 | yes |  | Modifier;SpecificDisease;DiseaseClass | - “colorectal cancer” as **Modifier** | colorectal cancer 在 families 前标 Modifier，区别独立疾病。 |
| 35 | yes |  | Modifier;SpecificDisease | - “HNPCC” as **Modifier** | HNPCC 在 kindreds 前标 Modifier，区别具体疾病。 |

## top4_loop08

| line | other run | in pair file | types | text | reason |
| --- | --- | --- | --- | --- | --- |
| 17 | yes | yes | Modifier;SpecificDisease;DiseaseClass | This rule does not apply to a disease-denoting expression that is an attributive premodifier of a non-disease head noun (e.g., "ovarian cancer cases," "the DTD gene"). | 非疾病名词前的病名排除在具体疾病指称测试之外。 |
| 17 | yes | yes | Modifier;SpecificDisease;DiseaseClass | Those spans are **Modifier** mentions under item 3, which takes precedence over the referential test and its gene-defined clause. | 这些定语优先标 Modifier，不能被具体疾病或基因定义规则改标。 |
| 17 | yes | yes | Modifier;CompositeMention | This rule does not alter the boundaries of Modifier or Composite Mention spans. | 限制优先规则不得改变 Modifier 或 CompositeMention 的跨度。 |
| 37 | yes | yes | Modifier;SpecificDisease;DiseaseClass | A textual string may refer to a disease name, but it may modify a noun phrase (or may not be a noun phrase itself). | 病名修饰其他名词的语法角色会改变疾病标签。 |
| 37 | yes | yes | Modifier;SpecificDisease;DiseaseClass | In such cases, annotate using the **Modifier** category. | 上述修饰用法标 Modifier，区别独立的具体疾病或疾病家族。 |
| 40 | yes | no | Modifier;SpecificDisease;DiseaseClass | > Although this mutation was initially detected in four of 33 colorectal cancer families analysed from eastern England, more extensive analysis has reduced the frequency to four of 52 English HNPCC kindreds analysed. | 示范病名修饰 families 和 kindreds 的 Modifier 用法。 |
| 43 | yes | yes | Modifier;SpecificDisease;DiseaseClass | - “colorectal cancer” as **Modifier** | colorectal cancer 在 families 前标 Modifier，区别独立疾病。 |
| 44 | yes | yes | Modifier;SpecificDisease | - “HNPCC” as **Modifier** | HNPCC 在 kindreds 前标 Modifier，区别具体疾病。 |
| 46 | yes | yes | Modifier;SpecificDisease;DiseaseClass | A disease-denoting expression is a **Modifier** when it specifies a non-disease head noun rather than naming the disorder itself. | 限定非疾病中心名词的病名标 Modifier，区别病名独立指称。 |
| 47 | yes | yes | Modifier;SpecificDisease;DiseaseClass | - an attributive premodifier of a case, patient, population, sample, study, family/kindred, series, risk, phenotype, gene, or allele noun (e.g., "ovarian cancer cases," "population-based ovarian cancer study," "ovarian cancer risk," "HNPCC kindreds," "ancient SLS genes," "the DTD gene," "G6PD deficient phenotype"); | 病例、家系、研究、风险、基因等名词前的病名纳入 Modifier。 |
| 48 | yes | yes | Modifier;SpecificDisease;DiseaseClass | - the complement of a history frame (e.g., "a family history of ovarian cancer"). | history 框架补语内的病名也归入 Modifier。 |
| 50 | yes | yes | Modifier;SpecificDisease;DiseaseClass | The Modifier label applies only when the disease expression functions as a modifier. | Modifier 只用于真正充当修饰语的疾病表达。 |
| 50 | yes | yes | Modifier;SpecificDisease;DiseaseClass | If the disease expression is itself the head of the phrase, or stands as a complete entity (e.g., "Coats telangiectasis"), item 1 or item 7 governs. | 病名自身作中心语或独立实体时回到具体疾病或疾病状态规则。 |
| 52 | yes | yes | Modifier;SpecificDisease | When a disease-denoting expression (a full-form name whose head is a disease-category noun, or a short form that the document has explicitly defined as a disease) is an attributive premodifier of a non-disease head, label the disease-denoting substring **Modifier**, even when that head sits inside an out-of-schema nomenclature or proper-name construction (e.g., in "the Norrie disease gene (NDP)," "Norrie disease" is a Modifier). | 即使位于基因命名结构，病名子串仍作为 Modifier 保留。 |
| 52 | yes | yes | Modifier | Assess that substring independently of the enclosing span, so that the span's out-of-scope status does not suppress the label. | 独立判断病名子串，避免整个命名跨度越界而漏掉 Modifier。 |
| 52 | yes | yes | Modifier | Leave non-disease material, such as the head noun or identifier ("gene," "NDP"), unlabelled. | 该 Modifier 跨度不包含 gene 或 NDP 等非疾病成分。 |
| 53 | yes | yes | Modifier;SpecificDisease;DiseaseClass | - Do not apply this rule when (a) the disease expression is itself the head of the phrase or stands as a complete entity, in which case the disease-class or specific-disease labels govern; (b) the enclosing name contains no disease-denoting substring, so the span is simply out of scope and remains O; or (c) a short form has no disease definition in the document, so it is not anchored as a disease reference and cannot be promoted to Modifier by position alone. | 独立病名、无病名子串或无疾病定义的缩写不适用 Modifier 规则。 |
| 55 | yes | yes | Modifier;SpecificDisease | A disease name that follows a non-disease noun through a "with" or "has" frame is not an attributive premodifier and is annotated as **Specific Disease** under item 1 (e.g., "63 kindreds with SLS"). | with 或 has 后的病名用 SpecificDisease，区别前置定语 Modifier。 |
| 55 | no | yes | Modifier;SpecificDisease | A disease name that is the disorder of which a form or variant is described (e.g., "the classical form of Coats disease") names the disorder itself and is **Specific Disease**. | form 或 variant of 中被描述的病名仍为 SpecificDisease，而非 Modifier。 |
| 89 | yes | yes | Modifier;SpecificDisease | 1. The deficiency term is an adjectival modifier that does not head a disease noun phrase (e.g., “[enzyme]-deficient”). Label it **Modifier** (item 3). | 缺乏词仅作定语时改标 Modifier，而非 SpecificDisease。 |
| 159 | yes | yes | Modifier;SpecificDisease;DiseaseClass | 1. **Modifier before Specific Disease / Disease Class (item 3 before item 1).** A disease-denoting expression that is an attributive premodifier of a non-disease head, or that specifies a history frame, is a **Modifier** even when its referent is a concrete individual’s disorder. The referential test and its gene-defined clause in item 1 do not override this. A disease expression that is itself the head of a phrase is never a Modifier. | 前置病名及 history 框架优先标 Modifier，独立病名不标 Modifier。 |
| 165 | yes | yes | Modifier;SpecificDisease | 4. **Adjectival deficiency forms.** An adjectival deficiency form (“[enzyme]-deficient”) is a **Modifier** (item 7, Negative Constraint 1), not a Specific Disease. | 形容词形式的缺乏表达用 Modifier，而非 SpecificDisease。 |
| 233 | no | no | Modifier;SpecificDisease | 20. **“the classical form of Coats disease”** | 示范 form of 后病名作为独立疾病而非 Modifier 的情境。 |
| 234 | no | yes | Modifier;SpecificDisease | - “Coats disease” = **Specific Disease**. The phrase names the disorder whose form is described; “classical form” is not part of the mention. | Coats disease 保留 SpecificDisease，classical form 不进入病名跨度。 |
| 236 | yes | no | Modifier;SpecificDisease;DiseaseClass | 21. **“a family history of ovarian cancer”; “ovarian cancer cases”** | 展示 history 补语及 cases 前病名均用 Modifier 的情境。 |
| 237 | yes | yes | Modifier;SpecificDisease;DiseaseClass | - “ovarian cancer” = **Modifier** in both. In the first it is the complement of a history frame; in the second it is an attributive premodifier of a non-disease head. | 明确两种句法位置的 ovarian cancer 都标 Modifier。 |
| 239 | yes | no | Modifier;SpecificDisease | 22. **“63 kindreds with SLS”** | 展示 with 后病名与前置定语用法的区别。 |
| 240 | yes | yes | Modifier;SpecificDisease | - “SLS” = **Specific Disease**. The “with” frame is post-modification, not an attributive premodifier. | with 后的 SLS 用 SpecificDisease，而非 Modifier。 |
| 242 | yes | no | Modifier;SpecificDisease | 23. **“the Norrie disease gene (NDP)”** | 展示基因名称内仍有疾病名子串的 Modifier 情境。 |
| 243 | yes | yes | Modifier;SpecificDisease | - “Norrie disease” = **Modifier**. “gene” and “NDP” remain unlabelled. | Norrie disease 标 Modifier，同时排除 gene 和 NDP。 |
| 257 | yes | no | Modifier;SpecificDisease | 27. **“diastrophic dysplasia (DTD) … the DTD gene”** | 对照疾病缩写独立出现与修饰 gene 时的类型。 |
| 259 | yes | yes | Modifier;SpecificDisease | - “DTD” as a premodifier of “gene” is **Modifier** (item 3, short form defined in the document). | DTD 修饰 gene 时改标 Modifier，区别独立具体疾病。 |

Pair-file lines with no unit judged Modifier in this run: []

## top4_loop04

| line | other run | in pair file | types | text | reason |
| --- | --- | --- | --- | --- | --- |
| 38 | yes | yes | Modifier;SpecificDisease;DiseaseClass | - *Attributive use.* When the deficiency-type word modifies a different noun, it is attributive and is annotated as **Modifier** (rule 3), not as a Specific Disease. For example, in "G6PD-deficient phenotype," "G6PD deficient" is **Modifier**. The same holds for "deficient patients." A "deficient activity of X" or "deficiency of X" phrase is not attributive, because the deficiency word heads its own phrase; it is governed by rule 1a(i). | 定语缺乏词用 Modifier，名词中心语的分子缺乏短语走排除规则。 |
| 39 | yes | no | Modifier | - *Negated or normal-state adjectives* ("non-deficient," "normal") do not name a disease and remain O. | 否定或正常状态的缺乏形容词不能形成疾病 Modifier。 |
| 44 | yes | yes | Modifier;SpecificDisease;DiseaseClass | Attributive uses are Modifiers (rule 3) and are not tested here. | 定语用法先标 Modifier，排除具体疾病与疾病家族测试。 |
| 53 | yes | yes | Modifier;SpecificDisease | - An attributive premodifier role is a **Modifier** (rule 3), not a Specific Disease. | 定语前置修饰语用 Modifier，而非 SpecificDisease。 |
| 78 | yes | yes | Modifier;DiseaseClass | - (e) It is a standalone severity, onset, or temporal qualifier (e.g., "early onset"). Such a qualifier remains a **Modifier** and is not part of a Disease Class span. | 独立严重度、起病或时间限定语保留 Modifier，不并入 DiseaseClass。 |
| 96 | yes | yes | Modifier;SpecificDisease;DiseaseClass;CompositeMention | - (a) The coordinator joins disease-name or disease-category heads (e.g., organ-site modifiers sharing a disease-name head such as "cancer"). This coordinated-cancer case is not reclassified by this principle. Annotate the disease mention per rules 1b and 3, and keep multi-disease coordinations such as example 7 as Composite Mentions under the first paragraph of this rule. | 疾病中心语并列不受新增复合规则改标，按疾病、修饰及原复合规则处理。 |
| 103 | yes | yes | Modifier;SpecificDisease;DiseaseClass | A textual string may refer to a disease name, but it may modify a noun phrase (or may not be a noun phrase itself). | 病名修饰其他名词的语法角色会改变疾病标签。 |
| 103 | yes | yes | Modifier;SpecificDisease;DiseaseClass | In such cases, annotate using the **Modifier** category. | 上述修饰用法标 Modifier，区别独立的具体疾病或疾病家族。 |
| 103 | yes | yes | Modifier;SpecificDisease | An attributive disease mention is a **Modifier** even if it is anchored in the sense of rule 1b. | 即使病名有具体锚定，作定语时仍标 Modifier。 |
| 103 | yes | yes | Modifier;SpecificDisease;DiseaseClass | The Specific Disease / Disease Class test does not override this role. | 具体疾病与疾病家族测试不得推翻 Modifier 的语法角色判定。 |
| 106 | yes | no | Modifier;SpecificDisease;DiseaseClass | > Although this mutation was initially detected in four of 33 colorectal cancer families analysed from eastern England, more extensive analysis has reduced the frequency to four of 52 English HNPCC kindreds analysed. | 示范病名修饰 families 和 kindreds 的 Modifier 用法。 |
| 109 | yes | yes | Modifier;SpecificDisease;DiseaseClass | - "colorectal cancer" as **Modifier** | colorectal cancer 在 families 前标 Modifier，区别独立疾病。 |
| 110 | yes | yes | Modifier;SpecificDisease | - "HNPCC" as **Modifier** | HNPCC 在 kindreds 前标 Modifier，区别具体疾病。 |
| 113 | yes | yes | Modifier;SpecificDisease | - **IF** a disease-name span (a full name or its short-form alias) is **immediately** followed by a common-noun head that it attributively premodifies, with no intervening punctuation, bracket, participle, finite verb, or preposition, **THEN** label the span **Modifier**. | 紧邻所修饰普通名词的病名用 Modifier，而非 SpecificDisease。 |
| 114 | yes | yes | Modifier;SpecificDisease | - **OTHERWISE**, label the span **Specific Disease**. This covers spans followed by punctuation, a bracket, a participle, a verb, a preposition, or nothing, and spans that head their own noun phrase, complement a preposition, or serve as a subject or verb argument. A parenthetical acronym or alias takes the class of its expanded antecedent, judged by the antecedent's syntactic position, not by the alias's own local context. | 其他病名用 SpecificDisease，括号缩写继承全称的句法类型。 |
| 116 | yes | yes | Modifier;SpecificDisease | - The decision rests on the semantic content of the following noun (e.g., "risk," "mutation," "patients," "genes") or on other occurrences of the same string in the document. The following word may confirm that the next token is a noun head, but it cannot by itself change the label. | 后续词的语义或别处用法不能单独改变当前 Modifier 与 SpecificDisease 判定。 |
| 117 | yes | yes | Modifier;SpecificDisease;DiseaseClass;CompositeMention | - The span is a Disease Class mention or a Composite Mention. Those are resolved by their own definitions before this test is applied. | DiseaseClass 和 CompositeMention 先依自身定义处理，不套用病名修饰测试。 |
| 118 | yes | yes | Modifier;SpecificDisease | - **Example.** In "a family history of ovarian cancer," "ovarian cancer" is **Specific Disease** (complement of "of," followed by punctuation). In "ovarian cancer risk," "ovarian cancer" is **Modifier** (immediately followed by a head noun). | history of 后病名用 SpecificDisease，risk 前病名用 Modifier。 |
| 120 | yes | yes | Modifier;SpecificDisease | A disease-denoting premodifier (a spelled-out disease name, or an acronym that the document has already defined as a disease) in attributive position within a noun phrase whose head denotes a gene or locus is a **Modifier**. | 即使位于基因命名结构，病名子串仍作为 Modifier 保留。 |
| 120 | yes | yes | Modifier | A locus head is "gene," "genes," or "gene" followed by a numeral or symbol. | gene 及其带编号形式可触发疾病前置语的 Modifier。 |
| 120 | yes | yes | Modifier | This rule extends the adjacency test above; it does not restrict it to gene heads. | 位点规则扩展适用情境，不能把 Modifier 测试限于 gene 中心语。 |
| 120 | yes | yes | Modifier | The locus head does not turn the disease span into O. | 位点中心语不能使前面的疾病 Modifier 漏标。 |
| 120 | only other run | yes | general | The locus designator and any bare gene symbol remain O. | 位点指示语及裸基因符号是所有疾病类型共同排除的非疾病名称。 |
| 120 | only other run | yes | SpecificDisease;DiseaseClass | Gene symbols stay outside the schema, and the Specific Disease / Disease Class boundaries are unchanged for non-attributive uses. | 非定语用法仍按原具体疾病与疾病家族定义处理，基因符号不造疾病。 |
| 122 | yes | yes | Modifier;SpecificDisease | - **Example.** In "breast cancer susceptibility gene 1 (BRCA1)," "breast cancer" is **Modifier**, and "BRCA1" is O. In "SLS genes," "SLS" is **Modifier**. | 示范基因命名结构中的病名标 Modifier，蛋白或基因缩写排除。 |
| 124 | yes | yes | Modifier;SpecificDisease | - (a) The disease term is the head of the phrase, or it sits in a postmodifying prepositional phrase and is not immediately followed by a noun it premodifies (e.g., "gene for ___"). The disease is then not attributive, and the adjacency test gives **Specific Disease**. | 病名作中心语或非定语后置介词补语时用 SpecificDisease，区别 Modifier。 |
| 125 | yes | yes | Modifier | - (b) The acronym has no disease definition or established disease referent in the document, so it remains O. | 无疾病定义的缩写不能仅因基因结构而成为 Modifier。 |
| 126 | yes | yes | Modifier | - (c) The span is a gene symbol or locus name containing no disease term. | 没有疾病词的基因或位点名不能触发疾病 Modifier。 |
| 127 | yes | yes | Modifier | - (d) The premodifier is a non-disease attributive noun (e.g., anatomical, drug, or procedure terms). | 解剖、药物及程序等非疾病前置词不能用疾病 Modifier 规则。 |
| 187 | yes | no | Modifier | 7. **Do not annotate negated or normal-state deficiency adjectives** | 否定或正常状态的缺乏形容词不命名疾病，不能形成 Modifier。 |
| 188 | yes | no | Modifier | - e.g., "non-deficient polymorphic variant G6PD A." The word "non-deficient" names no disease, so it remains O. | 否定或正常状态的缺乏形容词不命名疾病，不能形成 Modifier。 |
| 192 | yes | yes | Modifier;SpecificDisease | - The exception is a disease term attributive to them, which is a **Modifier** under rule 3 (locus-designator heads). | 基因结构中真正的病名定语仍标 Modifier，避免随基因名漏掉。 |
| 203 | yes | yes | Modifier;SpecificDisease;DiseaseClass | 1. **Attributive role before label.** A disease mention used attributively is a **Modifier** (rule 3, including locus-designator heads). The Specific Disease / Disease Class test (rule 1b) does not apply to it. For other disease-name spans, the adjacency test in rule 3 is applied first; rule 1b then decides between Specific Disease and Disease Class for non-attributive mentions not already decided by rule 1a or 1a(i). | 先判定定语 Modifier，其余病名再判 SpecificDisease 或 DiseaseClass。 |
| 207 | yes | yes | Modifier;SpecificDisease;DiseaseClass | 5. **Gene-level before disease.** Gene symbols, mutations, polymorphisms, variants, and gene-level dysfunction are O (item 8) unless a disease term is attributive to them (rule 3). A molecule-level deficiency that follows from a gene mutation is governed by rule 1a or 1a(i). If it is not a lexicalized named condition, it is a molecular-defect paraphrase and is not a disease mention. It is also not a rule 1c span (rule 1c, exclusion (b)), and it remains O. | 排除基因状态与分子缺陷，保留命名缺乏病及病名定语的相应标签。 |
| 282 | yes | no | Modifier;SpecificDisease | - "Sjogren-Larsson syndrome" and "SLS" = **Specific Disease** (eponym and defined acronym; the full name is followed by a bracket, and the alias takes its antecedent's class). | 全称后接括号而保留 SpecificDisease，缩写继承该类，区别 Modifier。 |
| 288 | yes | no | Modifier;SpecificDisease | 22. **"Wiskott-Aldrich syndrome protein (WASP) family members"** | 展示蛋白名称中病名作定语，区别独立具体疾病。 |
| 289 | yes | yes | Modifier;SpecificDisease | - "Wiskott-Aldrich syndrome" = **Modifier** (immediately followed by "protein," so the adjacency test in rule 3 applies; attributive role takes precedence over the eponym anchor). | Wiskott-Aldrich syndrome 在 protein 前改标 Modifier，优先于专名锚定。 |
| 292 | yes | no | Modifier;SpecificDisease | 23. **"a family history of ovarian cancer"; "ovarian cancer cases"; "ovarian cancer risk"** | 对照 history 补语与 cases 或 risk 前病名的句法标签。 |
| 293 | yes | yes | Modifier;SpecificDisease | - "ovarian cancer" in "a family history of ovarian cancer" = **Specific Disease** (complement of the preposition "of," followed by punctuation; rule 3 adjacency test). | history of 后的 ovarian cancer 用 SpecificDisease，区别 Modifier。 |
| 294 | yes | yes | Modifier;SpecificDisease | - "ovarian cancer" in "ovarian cancer cases" and "ovarian cancer risk" = **Modifier** (immediately followed by a head noun). | cases 和 risk 前的 ovarian cancer 改标 Modifier。 |
| 296 | yes | no | Modifier;SpecificDisease | 24. **"breast cancer susceptibility gene 1 (BRCA1)"** | 展示基因名称内仍有疾病名子串的 Modifier 情境。 |
| 297 | yes | yes | Modifier;SpecificDisease | - "breast cancer" = **Modifier** (locus-designator head; immediately followed by "susceptibility"). | 位点名词结构中的 breast cancer 标 Modifier，区别独立具体疾病。 |
| 300 | yes | no | Modifier;SpecificDisease | 25. **"the G6PD deficient phenotype"; "non-deficient polymorphic variant G6PD A"** | 对照定语缺乏表达及不命名疾病的正常状态形容词。 |
| 301 | yes | yes | Modifier;SpecificDisease | - "G6PD deficient" = **Modifier** (attributive deficiency word). | 形容词形式的缺乏表达用 Modifier，而非 SpecificDisease。 |
| 302 | yes | no | Modifier | - "non-deficient" = O (negated; no disease named). | 否定形容词 non-deficient 不构成疾病 Modifier。 |
| 309 | yes | no | Modifier;SpecificDisease | - "Coats telangiectasis" = **Specific Disease** (eponym anchor; followed by "is"). | Coats telangiectasis 后接 is，标 SpecificDisease 而非定语 Modifier。 |
| 317 | yes | no | Modifier;SpecificDisease | - "Coats' disease" = **Specific Disease** (eponym anchor; followed by "of"). | Coats' disease 后接 of，仍用 SpecificDisease 而非定语 Modifier。 |
| 322 | yes | no | Modifier;SpecificDisease;DiseaseClass | 30. **"Most fragile X syndrome patients have expansion of a (CGG)(n) sequence … responsible for this condition."** | 展示患者前病名的 Modifier 用法及不能形成疾病提及的泛回指。 |
| 323 | yes | yes | Modifier;SpecificDisease | - "fragile X syndrome" = **Modifier** (immediately followed by "patients"). | fragile X syndrome 紧邻 patients，改标 Modifier 而非具体疾病。 |

Pair-file lines with no unit judged Modifier in this run: [145]
- L145 (general ): Abbreviation definitions such as "Huntington disease" ("HD") are separated into two annotated mentions (one for the long form, one for the abbreviation).
- L145 (general ): The short form takes the class of its expanded antecedent (rule 3).
