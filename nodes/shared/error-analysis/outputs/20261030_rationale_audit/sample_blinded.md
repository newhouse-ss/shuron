# Rationale 审核案例

请先独立核对原文、实际指南和预测。完整文档与完整指南均为不含 gold 的文本副本。评分状态与 gold 单独保存。

## R01

文档：8808605。完整原文：[text](documents/8808605.txt)。

实际预测：`SpecificDisease`，字符区间 `[363, 431)`，文本 "red-blood-cell glucose-6-phosphate dehydrogenase ( G6PD ) deficiency"。

完整实际指南：[guideline](guidelines/9547c3d2ffbaf89cc82a1f5a36c903935c018e35d4445c56e9f595e25f25e301.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_topk1_loop05/final/final_guidelines.txt`。文本 SHA256：`9547c3d2ffbaf89cc82a1f5a36c903935c018e35d4445c56e9f595e25f25e301`。

上下文起点：263。

```text
e resulting somatic-cell mosaicism creates the opportunity for cell selection . In most people with red-blood-cell glucose-6-phosphate dehydrogenase ( G6PD ) deficiency , the enzyme-deficient phenotype is only moderately expressed in nucleated cells . However , in a s
```

原始预测版本：

```json
{
  "start": 363,
  "end": 431,
  "text": "red-blood-cell glucose-6-phosphate dehydrogenase ( G6PD ) deficiency",
  "entity": "SpecificDisease",
  "rationale": "Named enzyme (G6PD) argument with state noun 'deficiency' is presented as a condition of a patient group ('people with'), so the whole chain is one Specific Disease span.",
  "guideline_section": "Section 1.1"
}
```

对齐后的预测版本：

```json
{
  "start": 363,
  "end": 431,
  "text": "red-blood-cell glucose-6-phosphate dehydrogenase ( G6PD ) deficiency",
  "entity": "SpecificDisease",
  "rationale": "Named enzyme (G6PD) argument with state noun 'deficiency' is presented as a condition of a patient group ('people with'), so the whole chain is one Specific Disease span.",
  "guideline_section": "Section 1.1",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

Named enzyme (G6PD) argument with state noun 'deficiency' is presented as a condition of a patient group ('people with'), so the whole chain is one Specific Disease span.

模型引用：

Section 1.1

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/9ccf9217bc4f8498bc179cd54f7239a62ac7f9df225ce1a4.json`，raw item index `0`，custom_id `9ccf9217bc4f8498bc179cd54f7239a62ac7f9df225ce1a4`。

## R02

文档：8968760。完整原文：[text](documents/8968760.txt)。

实际预测：`Modifier`，字符区间 `[225, 231)`，文本 "cancer"。

完整实际指南：[guideline](guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_e1_run07/inputs/initial_guidelines.txt`。文本 SHA256：`e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d`。

上下文起点：125。

```text
der ataxia-telangiectasia ( A-T ) , characterized by cerebellar degeneration , immunodeficiency and cancer predisposition . A-T carriers were reported to be moderately cancer-prone . A wide variety of A-T m
```

原始预测版本：

```json
{
  "start": 225,
  "end": 231,
  "text": "cancer",
  "entity": "Modifier",
  "rationale": "'Cancer' is a disease mention that modifies the noun phrase 'predisposition', so it is annotated as a Modifier.",
  "guideline_section": "3. Annotate disease mentions that are used as Modifiers for other concepts"
}
```

对齐后的预测版本：

```json
{
  "start": 225,
  "end": 231,
  "text": "cancer",
  "entity": "Modifier",
  "rationale": "'Cancer' is a disease mention that modifies the noun phrase 'predisposition', so it is annotated as a Modifier.",
  "guideline_section": "3. Annotate disease mentions that are used as Modifiers for other concepts",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

'Cancer' is a disease mention that modifies the noun phrase 'predisposition', so it is annotated as a Modifier.

模型引用：

3. Annotate disease mentions that are used as Modifiers for other concepts

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/cc03ab672cb133510aef0a4bb2f94765bf87570814725205.json`，raw item index `6`，custom_id `cc03ab672cb133510aef0a4bb2f94765bf87570814725205`。

## R03

文档：9050868。完整原文：[text](documents/9050868.txt)。

实际预测：`DiseaseClass`，字符区间 `[500, 514)`，文本 "aortic rupture"。

完整实际指南：[guideline](guidelines/0702a16394a0d9c09940086f7d6647b8392ba676ba073d6a76e2fe8820be48ce.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_topk4_loop08/final/final_guidelines.txt`。文本 SHA256：`0702a16394a0d9c09940086f7d6647b8392ba676ba073d6a76e2fe8820be48ce`。

上下文起点：400。

```text
OL3A1 gene have been implicated as a cause of type IV Ehlers-Danlos syndrome , a disease leading to aortic rupture in early adult life . To directly study the role of Col3a1 in development and disease , we have ina
```

原始预测版本：

```json
{
  "start": 500,
  "end": 514,
  "text": "aortic rupture",
  "entity": "DiseaseClass",
  "rationale": "Discrete clinical/structural finding (aortic rupture) that is the complement of a causal predicate ('leading to') whose subject is the disease, so it is a generic manifestation tagged as Disease Class.",
  "guideline_section": "8. Annotate generic manifestations and pathological states as Disease Class"
}
```

对齐后的预测版本：

```json
{
  "start": 500,
  "end": 514,
  "text": "aortic rupture",
  "entity": "DiseaseClass",
  "rationale": "Discrete clinical/structural finding (aortic rupture) that is the complement of a causal predicate ('leading to') whose subject is the disease, so it is a generic manifestation tagged as Disease Class.",
  "guideline_section": "8. Annotate generic manifestations and pathological states as Disease Class",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

Discrete clinical/structural finding (aortic rupture) that is the complement of a causal predicate ('leading to') whose subject is the disease, so it is a generic manifestation tagged as Disease Class.

模型引用：

8. Annotate generic manifestations and pathological states as Disease Class

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/546a73458f14705755fcf8affd94442f8ebc5db84963e45a.json`，raw item index `1`，custom_id `546a73458f14705755fcf8affd94442f8ebc5db84963e45a`。

## R04

文档：9144439。完整原文：[text](documents/9144439.txt)。

实际预测：`Modifier`，字符区间 `[1125, 1129)`，文本 "IDDM"。

完整实际指南：[guideline](guidelines/d2677c7f422d5b823b28b9f57876b77316ca55ca9e872fc636c6c18fe2167889.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_topk4_loop07/final/final_guidelines.txt`。文本 SHA256：`d2677c7f422d5b823b28b9f57876b77316ca55ca9e872fc636c6c18fe2167889`。

上下文起点：1025。

```text
eles in the general population suggest that IDDM2 locus is not responsible for the low incidence of IDDM in Japanese . 
```

原始预测版本：

```json
{
  "start": 1126,
  "end": 1130,
  "text": "IDDM",
  "entity": "Modifier",
  "rationale": "Disease abbreviation is the complement of the context noun 'incidence' in 'low incidence of IDDM in Japanese', a population-frame use, so it is labeled Modifier.",
  "guideline_section": "3 Context and population frames"
}
```

对齐后的预测版本：

```json
{
  "start": 1125,
  "end": 1129,
  "text": "IDDM",
  "entity": "Modifier",
  "rationale": "Disease abbreviation is the complement of the context noun 'incidence' in 'low incidence of IDDM in Japanese', a population-frame use, so it is labeled Modifier.",
  "guideline_section": "3 Context and population frames",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

Disease abbreviation is the complement of the context noun 'incidence' in 'low incidence of IDDM in Japanese', a population-frame use, so it is labeled Modifier.

模型引用：

3 Context and population frames

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/93cbb4057d02b9f949f166522e0d69d13fd5f91eb103f72e.json`，raw item index `8`，custom_id `93cbb4057d02b9f949f166522e0d69d13fd5f91eb103f72e`。

## R05

文档：9272171。完整原文：[text](documents/9272171.txt)。

实际预测：`SpecificDisease`，字符区间 `[1710, 1724)`，文本 "infantile form"。

完整实际指南：[guideline](guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_topk1_loop02/final/final_guidelines.txt`。文本 SHA256：`e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d`。

上下文起点：1610。

```text
D , 535-573del ) or C-terminus ( L618S ) of the GALC enzyme , whereas the reported mutations in the infantile form ( IF-GLD ) are in the central domain . This difference in mutation sites may affect the clinical fe
```

原始预测版本：

```json
{
  "start": 1700,
  "end": 1714,
  "text": "infantile form",
  "entity": "SpecificDisease",
  "rationale": "Long form of IF-GLD, referring to the infantile form of globoid cell leukodystrophy, a specific disease form. Annotated separately from the abbreviation.",
  "guideline_section": "1. Specific Disease / 6. Synonymous mentions"
}
```

对齐后的预测版本：

```json
{
  "start": 1710,
  "end": 1724,
  "text": "infantile form",
  "entity": "SpecificDisease",
  "rationale": "Long form of IF-GLD, referring to the infantile form of globoid cell leukodystrophy, a specific disease form. Annotated separately from the abbreviation.",
  "guideline_section": "1. Specific Disease / 6. Synonymous mentions",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

Long form of IF-GLD, referring to the infantile form of globoid cell leukodystrophy, a specific disease form. Annotated separately from the abbreviation.

模型引用：

1. Specific Disease / 6. Synonymous mentions

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/80c70eb829294c93aad9d46a2ba65f84a191b692cba0da56.json`，raw item index `7`，custom_id `80c70eb829294c93aad9d46a2ba65f84a191b692cba0da56`。

## R06

文档：8649785。完整原文：[text](documents/8649785.txt)。

实际预测：`SpecificDisease`，字符区间 `[774, 788)`，文本 "leiomyosarcoma"。

完整实际指南：[guideline](guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_topk1_loop01/final/final_guidelines.txt`。文本 SHA256：`e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d`。

上下文起点：674。

```text
appear to be remarkable in the spectrum of tumours , and there is loss of the wild-type allele in a leiomyosarcoma from the proband . A cell line has been established from the tumour of the proband and cytogenetic 
```

原始预测版本：

```json
{
  "start": 774,
  "end": 788,
  "text": "leiomyosarcoma",
  "entity": "SpecificDisease",
  "rationale": "Names a specific malignant tumour type (a sarcoma) that can be linked to one definition, so it is a Specific Disease mention.",
  "guideline_section": "1. Annotate all Specific Disease mentions"
}
```

对齐后的预测版本：

```json
{
  "start": 774,
  "end": 788,
  "text": "leiomyosarcoma",
  "entity": "SpecificDisease",
  "rationale": "Names a specific malignant tumour type (a sarcoma) that can be linked to one definition, so it is a Specific Disease mention.",
  "guideline_section": "1. Annotate all Specific Disease mentions",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

Names a specific malignant tumour type (a sarcoma) that can be linked to one definition, so it is a Specific Disease mention.

模型引用：

1. Annotate all Specific Disease mentions

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/32b85637363bf182d715f475a8a15654066469c5701ace9b.json`，raw item index `2`，custom_id `32b85637363bf182d715f475a8a15654066469c5701ace9b`。

## R07

文档：8751855。完整原文：[text](documents/8751855.txt)。

实际预测：`SpecificDisease`，字符区间 `[107, 120)`，文本 "breast cancer"。

完整实际指南：[guideline](guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_e1_run06/inputs/initial_guidelines.txt`。文本 SHA256：`e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d`。

上下文起点：7。

```text
 heterogeneity in hereditary breast cancer: role of BRCA1 and BRCA2.
The common hereditary forms of breast cancer have been largely attributed to the inheritance of mutations in the BRCA1 or BRCA2 genes . However 
```

原始预测版本：

```json
{
  "start": 107,
  "end": 120,
  "text": "breast cancer",
  "entity": "SpecificDisease",
  "rationale": "Breast cancer is a named disease that can be linked to one specific definition without further categorization in the phrase 'forms of breast cancer'. Annotated as Specific Disease.",
  "guideline_section": "What to Annotate 1 - Specific Disease"
}
```

对齐后的预测版本：

```json
{
  "start": 107,
  "end": 120,
  "text": "breast cancer",
  "entity": "SpecificDisease",
  "rationale": "Breast cancer is a named disease that can be linked to one specific definition without further categorization in the phrase 'forms of breast cancer'. Annotated as Specific Disease.",
  "guideline_section": "What to Annotate 1 - Specific Disease",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

Breast cancer is a named disease that can be linked to one specific definition without further categorization in the phrase 'forms of breast cancer'. Annotated as Specific Disease.

模型引用：

What to Annotate 1 - Specific Disease

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/e3916bfc02242b05d23abb059e5599b6d6a13362a86caed1.json`，raw item index `1`，custom_id `e3916bfc02242b05d23abb059e5599b6d6a13362a86caed1`。

## R08

文档：8845838。完整原文：[text](documents/8845838.txt)。

实际预测：`CompositeMention`，字符区间 `[1310, 1337)`，文本 "cardiac and muscle symptoms"。

完整实际指南：[guideline](guidelines/8834ea8307a07ffe54f8f6f6c611563513a94e624656d9a445e878f5c6a24345.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_topk4_loop04/final/final_guidelines.txt`。文本 SHA256：`8834ea8307a07ffe54f8f6f6c611563513a94e624656d9a445e878f5c6a24345`。

上下文起点：1210。

```text
owed that VLCAD is most abundant in heart and skeletal muscle . This agrees well with the fact that cardiac and muscle symptoms are characteristic for patients with VLCAD deficiency . Northern blot analysis and sequencing of cl
```

原始预测版本：

```json
{
  "start": 1310,
  "end": 1337,
  "text": "cardiac and muscle symptoms",
  "entity": "CompositeMention",
  "rationale": "Coordinated premodifiers 'cardiac' and 'muscle' share one finding head 'symptoms' and act as the argument of the characterization predicate 'characteristic for' in a clause describing VLCAD deficiency, so the coordinated shared-head span is a Composite Mention rather than a Disease Class.",
  "guideline_section": "Section 2 Composite Mention (coordinated premodifiers over a non-disease head); Section 1c exclusion (i)"
}
```

对齐后的预测版本：

```json
{
  "start": 1310,
  "end": 1337,
  "text": "cardiac and muscle symptoms",
  "entity": "CompositeMention",
  "rationale": "Coordinated premodifiers 'cardiac' and 'muscle' share one finding head 'symptoms' and act as the argument of the characterization predicate 'characteristic for' in a clause describing VLCAD deficiency, so the coordinated shared-head span is a Composite Mention rather than a Disease Class.",
  "guideline_section": "Section 2 Composite Mention (coordinated premodifiers over a non-disease head); Section 1c exclusion (i)",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

Coordinated premodifiers 'cardiac' and 'muscle' share one finding head 'symptoms' and act as the argument of the characterization predicate 'characteristic for' in a clause describing VLCAD deficiency, so the coordinated shared-head span is a Composite Mention rather than a Disease Class.

模型引用：

Section 2 Composite Mention (coordinated premodifiers over a non-disease head); Section 1c exclusion (i)

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/e4d2c51a2d9f2435961a3bf36f4da10cb9d8d99d54ae5476.json`，raw item index `0`，custom_id `e4d2c51a2d9f2435961a3bf36f4da10cb9d8d99d54ae5476`。

## R09

文档：8828602。完整原文：[text](documents/8828602.txt)。

实际预测：`DiseaseClass`，字符区间 `[74, 102)`，文本 "autosomal recessive disorder"。

完整实际指南：[guideline](guidelines/a094230a404147d3aa7e3ab2e06659c744db8e4e9453dcb58dff17a64043939f.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_topk4_loop01/final/final_guidelines.txt`。文本 SHA256：`a094230a404147d3aa7e3ab2e06659c744db8e4e9453dcb58dff17a64043939f`。

上下文起点：0。

```text
Gene therapy for phenylketonuria.
Classical phenylketonuria ( PKU ) is an autosomal recessive disorder caused by a deficiency of hepatic phenylalanine hydroxylase ( PAH ) . Limitations of the current di
```

原始预测版本：

```json
{
  "start": 74,
  "end": 102,
  "text": "autosomal recessive disorder",
  "entity": "DiseaseClass",
  "rationale": "Inheritance-pattern category denoting a family of disorders; the inheritance modifier does not anchor it to one condition.",
  "guideline_section": "Section 1.1 (Example 10)"
}
```

对齐后的预测版本：

```json
{
  "start": 74,
  "end": 102,
  "text": "autosomal recessive disorder",
  "entity": "DiseaseClass",
  "rationale": "Inheritance-pattern category denoting a family of disorders; the inheritance modifier does not anchor it to one condition.",
  "guideline_section": "Section 1.1 (Example 10)",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

Inheritance-pattern category denoting a family of disorders; the inheritance modifier does not anchor it to one condition.

模型引用：

Section 1.1 (Example 10)

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/1cf86e6ab55efa441d5d535615db25f922c616258c7aec69.json`，raw item index `3`，custom_id `1cf86e6ab55efa441d5d535615db25f922c616258c7aec69`。

## R10

文档：8666397。完整原文：[text](documents/8666397.txt)。

实际预测：`DiseaseClass`，字符区间 `[943, 966)`，文本 "lymphoreticular disease"。

完整实际指南：[guideline](guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_e1_run09/inputs/initial_guidelines.txt`。文本 SHA256：`e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d`。

上下文起点：843。

```text
sf ) . This localization makes Wasp a candidate for involvement in scurfy , a T cell-mediated fatal lymphoreticular disease of mice that has previously been proposed as a mouse homolog of Wiskott-Aldrich syndrome . Northern
```

原始预测版本：

```json
{
  "start": 942,
  "end": 965,
  "text": "lymphoreticular disease",
  "entity": "DiseaseClass",
  "rationale": "Lymphoreticular disease denotes a family of multiple lymphoreticular disorders rather than one specific disease, so it is a Disease Class mention.",
  "guideline_section": "What to Annotate > 1. Specific Disease mentions (Disease Class definition)"
}
```

对齐后的预测版本：

```json
{
  "start": 943,
  "end": 966,
  "text": "lymphoreticular disease",
  "entity": "DiseaseClass",
  "rationale": "Lymphoreticular disease denotes a family of multiple lymphoreticular disorders rather than one specific disease, so it is a Disease Class mention.",
  "guideline_section": "What to Annotate > 1. Specific Disease mentions (Disease Class definition)",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

Lymphoreticular disease denotes a family of multiple lymphoreticular disorders rather than one specific disease, so it is a Disease Class mention.

模型引用：

What to Annotate > 1. Specific Disease mentions (Disease Class definition)

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/8c5d111719a5c8818060fb0c7e8c4e0fbe3ba2ce3d9df8b3.json`，raw item index `3`，custom_id `8c5d111719a5c8818060fb0c7e8c4e0fbe3ba2ce3d9df8b3`。

## R11

文档：8931695。完整原文：[text](documents/8931695.txt)。

实际预测：`CompositeMention`，字符区间 `[1701, 1711)`，文本 "AO2 or DTD"。

完整实际指南：[guideline](guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_topk1_loop10/final/final_guidelines.txt`。文本 SHA256：`e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d`。

上下文起点：1601。

```text
codons reduce mRNA levels . The presence of the DTDST R279W mutation in a total of 11 patients with AO2 or DTD emphasizes the overlap between these conditions . This mutation has not been found so far in 8 anal
```

原始预测版本：

```json
{
  "start": 1704,
  "end": 1714,
  "text": "AO2 or DTD",
  "entity": "CompositeMention",
  "rationale": "Contiguous string with two separate specific diseases (AO2 or DTD) joined by a coordinating conjunction, annotated as one Composite Mention",
  "guideline_section": "2. Annotate contiguous text strings (Composite Mention)"
}
```

对齐后的预测版本：

```json
{
  "start": 1701,
  "end": 1711,
  "text": "AO2 or DTD",
  "entity": "CompositeMention",
  "rationale": "Contiguous string with two separate specific diseases (AO2 or DTD) joined by a coordinating conjunction, annotated as one Composite Mention",
  "guideline_section": "2. Annotate contiguous text strings (Composite Mention)",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

Contiguous string with two separate specific diseases (AO2 or DTD) joined by a coordinating conjunction, annotated as one Composite Mention

模型引用：

2. Annotate contiguous text strings (Composite Mention)

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/be17aea25d2bb2dd4d6abc3570797ae9e88d0816030e06ba.json`，raw item index `17`，custom_id `be17aea25d2bb2dd4d6abc3570797ae9e88d0816030e06ba`。

## R12

文档：8640236。完整原文：[text](documents/8640236.txt)。

实际预测：`CompositeMention`，字符区间 `[469, 494)`，文本 "breast and ovarian cancer"。

完整实际指南：[guideline](guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_topk1_loop04/final/final_guidelines.txt`。文本 SHA256：`e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d`。

上下文起点：369。

```text
he familial forms . An exception is BRCA1 , which contributes to a significant fraction of familial breast and ovarian cancer , but undergoes mutation at very low rates in sporadic breast and ovarian cancers . This finding su
```

原始预测版本：

```json
{
  "start": 469,
  "end": 494,
  "text": "breast and ovarian cancer",
  "entity": "CompositeMention",
  "rationale": "The contiguous string contains two separate specific diseases (breast cancer and ovarian cancer) and must be annotated as one Composite Mention.",
  "guideline_section": "What to Annotate 2 - Contiguous text strings (Composite Mention)"
}
```

对齐后的预测版本：

```json
{
  "start": 469,
  "end": 494,
  "text": "breast and ovarian cancer",
  "entity": "CompositeMention",
  "rationale": "The contiguous string contains two separate specific diseases (breast cancer and ovarian cancer) and must be annotated as one Composite Mention.",
  "guideline_section": "What to Annotate 2 - Contiguous text strings (Composite Mention)",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

The contiguous string contains two separate specific diseases (breast cancer and ovarian cancer) and must be annotated as one Composite Mention.

模型引用：

What to Annotate 2 - Contiguous text strings (Composite Mention)

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/a77f24e99362135be7f48eb4048317fc4bd6efca7c1a9e8b.json`，raw item index `5`，custom_id `a77f24e99362135be7f48eb4048317fc4bd6efca7c1a9e8b`。

## R13

文档：8968716。完整原文：[text](documents/8968716.txt)。

实际预测：`Modifier`，字符区间 `[1389, 1395)`，文本 "cancer"。

完整实际指南：[guideline](guidelines/8893b2fb9b8c95539b9fc5d35e47b0b570f3ee3a310bbbea71971fa6d05be91e.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_topk4_loop06/final/final_guidelines.txt`。文本 SHA256：`8893b2fb9b8c95539b9fc5d35e47b0b570f3ee3a310bbbea71971fa6d05be91e`。

上下文起点：1289。

```text
hism detected one additional instance in a woman with breast cancer diagnosed at age 77 years , and cancer in one parent . R841W is likely to be an etiologically significant lesion with involvement in close
```

原始预测版本：

```json
{
  "start": 1390,
  "end": 1396,
  "text": "cancer",
  "entity": "Modifier",
  "rationale": "'cancer in one parent' is a family-history construction that assigns the condition to a relative, so the disease term is a Modifier.",
  "guideline_section": "Section 3 and Section 1.4(c)"
}
```

对齐后的预测版本：

```json
{
  "start": 1389,
  "end": 1395,
  "text": "cancer",
  "entity": "Modifier",
  "rationale": "'cancer in one parent' is a family-history construction that assigns the condition to a relative, so the disease term is a Modifier.",
  "guideline_section": "Section 3 and Section 1.4(c)",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

'cancer in one parent' is a family-history construction that assigns the condition to a relative, so the disease term is a Modifier.

模型引用：

Section 3 and Section 1.4(c)

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/7f4bca1846ed85d07b5c3d960704c2e3f345f120a1363508.json`，raw item index `8`，custom_id `7f4bca1846ed85d07b5c3d960704c2e3f345f120a1363508`。

## R14

文档：9012409。完整原文：[text](documents/9012409.txt)。

实际预测：`Modifier`，字符区间 `[307, 313)`，文本 "Duarte"。

完整实际指南：[guideline](guidelines/e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_topk1_loop03/final/final_guidelines.txt`。文本 SHA256：`e6232d944d68e9e98c6012328add622486a743f5978e48a5a56c77ac2743002d`。

上下文起点：207。

```text
cusing and 50 % reduction in galactose-1-phosphate uridyltransferase ( GALT ) enzyme activity . The Duarte biochemical phenotype has a molecular genotype of N314D / N314D . The characteristic Duarte isoform
```

原始预测版本：

```json
{
  "start": 307,
  "end": 313,
  "text": "Duarte",
  "entity": "Modifier",
  "rationale": "Disease name used as a modifier of the noun phrase biochemical phenotype.",
  "guideline_section": "3. Annotate disease mentions used as Modifiers"
}
```

对齐后的预测版本：

```json
{
  "start": 307,
  "end": 313,
  "text": "Duarte",
  "entity": "Modifier",
  "rationale": "Disease name used as a modifier of the noun phrase biochemical phenotype.",
  "guideline_section": "3. Annotate disease mentions used as Modifiers",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

Disease name used as a modifier of the noun phrase biochemical phenotype.

模型引用：

3. Annotate disease mentions used as Modifiers

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/04339970d7e1f70634408703e633e66bd5fb997e3dd14dea.json`，raw item index `2`，custom_id `04339970d7e1f70634408703e633e66bd5fb997e3dd14dea`。

## R15

文档：8841191。完整原文：[text](documents/8841191.txt)。

实际预测：`CompositeMention`，字符区间 `[367, 390)`，文本 "breast / ovarian cancer"。

完整实际指南：[guideline](guidelines/8635714314660d4a8438714d0144aca92997ad015286208a7556398cde35afe5.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_topk1_loop07/final/final_guidelines.txt`。文本 SHA256：`8635714314660d4a8438714d0144aca92997ad015286208a7556398cde35afe5`。

上下文起点：267。

```text
. Mutations in BRCA1 account for approximately 45 % of familial breast cancer and 90 % of inherited breast / ovarian cancer , whereas mutations in BRCA2 account for a comparable percentage of inherited breast cancer cases .
```

原始预测版本：

```json
{
  "start": 367,
  "end": 390,
  "text": "breast / ovarian cancer",
  "entity": "CompositeMention",
  "rationale": "The contiguous string 'breast / ovarian cancer' refers to two separate diseases (breast cancer and ovarian cancer), so it is annotated as one Composite Mention rather than as separate strings.",
  "guideline_section": "What to Annotate Section 2 (Composite Mention)"
}
```

对齐后的预测版本：

```json
{
  "start": 367,
  "end": 390,
  "text": "breast / ovarian cancer",
  "entity": "CompositeMention",
  "rationale": "The contiguous string 'breast / ovarian cancer' refers to two separate diseases (breast cancer and ovarian cancer), so it is annotated as one Composite Mention rather than as separate strings.",
  "guideline_section": "What to Annotate Section 2 (Composite Mention)",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

The contiguous string 'breast / ovarian cancer' refers to two separate diseases (breast cancer and ovarian cancer), so it is annotated as one Composite Mention rather than as separate strings.

模型引用：

What to Annotate Section 2 (Composite Mention)

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/4312553ada97527732c5dca641c340c53e9ee000afc4b786.json`，raw item index `3`，custom_id `4312553ada97527732c5dca641c340c53e9ee000afc4b786`。

## R16

文档：8636252。完整原文：[text](documents/8636252.txt)。

实际预测：`DiseaseClass`，字符区间 `[155, 170)`，文本 "genetic disease"。

完整实际指南：[guideline](guidelines/dbca220f1e3148d187b71f3997537495a841d4402a9492be06ec9faeb6f6c2a7.txt)。原路径：`outputs/ncbi_disease/20261022_haiku-xhigh_topk4_loop09/final/final_guidelines.txt`。文本 SHA256：`dbca220f1e3148d187b71f3997537495a841d4402a9492be06ec9faeb6f6c2a7`。

上下文起点：55。

```text
iopathic Addison's disease in young adult male patients.
X-Linked adrenoleukodystrophy ( ALD ) is a genetic disease associated with demyelination of the central nervous system , adrenal insufficiency , and accumulat
```

原始预测版本：

```json
{
  "start": 155,
  "end": 170,
  "text": "genetic disease",
  "entity": "DiseaseClass",
  "rationale": "Class-membership frame ('is a genetic disease') that refers to a category of diseases rather than one specific condition.",
  "guideline_section": "1.1"
}
```

对齐后的预测版本：

```json
{
  "start": 155,
  "end": 170,
  "text": "genetic disease",
  "entity": "DiseaseClass",
  "rationale": "Class-membership frame ('is a genetic disease') that refers to a category of diseases rather than one specific condition.",
  "guideline_section": "1.1",
  "uncertain": false,
  "raw_entity": null
}
```

理由：

Class-membership frame ('is a genetic disease') that refers to a category of diseases rather than one specific condition.

模型引用：

1.1

来源：`outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/1fdeaf26f6efe292a395d9ebc1cf70ddf5cd270919d811db.json`，raw item index `4`，custom_id `1fdeaf26f6efe292a395d9ebc1cf70ddf5cd270919d811db`。

