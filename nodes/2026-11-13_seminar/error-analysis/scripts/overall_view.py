"""Offline overall view with frozen text-first Modifier judgments.

Run with python -I. PAIRS was written after reading both complete guidelines,
before opening prediction, instance, or item aggregate files for this task.
The directions are fixed text-only judgments, not inferred from outcomes.

The revised 2026-11-08 specification permits replacing this script and its
own outputs. Reconstruct d from integer counts, validate all required checks
before making figures, and reuse the existing label-counting code verbatim.
"""

from __future__ import annotations

import ast
import csv
import json
import math
import os
import statistics
import sys
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


@dataclass(frozen=True)
class Clause:
    line: int
    text: str


@dataclass(frozen=True)
class Pair:
    loop08: tuple[Clause, ...]
    loop04: tuple[Clause, ...]
    status: str
    difference: str = ""
    direction: str = ""
    affected: str = ""


# Each quotation is one sentence or one list item. Related units may share a
# comparison row; repeated statements at different locations remain separate.
# All line numbers refer to the plain guideline copies, starting at one.
PAIRS = (
    Pair(
        (Clause(17, '**Precedence.** This rule does not apply to a disease-denoting expression that is an attributive premodifier of a non-disease head noun (e.g., "ovarian cancer cases," "the DTD gene").'),),
        (Clause(44, 'Attributive uses are Modifiers (rule 3) and are not tested here.'),),
        'worded differently',
        'loop08 明说非疾病中心词之前的疾病修饰语不进入指称测试，loop04 用 attributive uses 概括这一排除。',
        'unclear', '非疾病中心词前的疾病表达，两处都把这种用法交给 Modifier 规则。',
    ),
    Pair(
        (Clause(17, 'Those spans are **Modifier** mentions under item 3, which takes precedence over the referential test and its gene-defined clause.'),),
        (Clause(103, 'An attributive disease mention is a **Modifier** even if it is anchored in the sense of rule 1b.'),
         Clause(103, 'The Specific Disease / Disease Class test does not override this role.')),
        'same content',
    ),
    Pair(
        (Clause(17, 'This rule does not alter the boundaries of Modifier or Composite Mention spans.'),),
        (), 'only in loop08',
        'loop08 在指称测试处明说不改变 Modifier 或 Composite Mention 的跨度，loop04 此处没有对应声明。',
        'unclear', '受指称测试影响的 Modifier 跨度，这句话本身没有指定新增或移除哪类提及。',
    ),
    Pair(
        (Clause(37, 'A textual string may refer to a disease name, but it may modify a noun phrase (or may not be a noun phrase itself).'),),
        (Clause(103, 'A textual string may refer to a disease name, but it may modify a noun phrase (or may not be a noun phrase itself).'),),
        'same content',
    ),
    Pair(
        (Clause(37, 'In such cases, annotate using the **Modifier** category.'),),
        (Clause(103, 'In such cases, annotate using the **Modifier** category.'),),
        'same content',
    ),
    Pair(
        (Clause(43, '  - “colorectal cancer” as **Modifier**  '),),
        (Clause(109, '  - "colorectal cancer" as **Modifier**  '),),
        'same content',
    ),
    Pair(
        (Clause(44, '  - “HNPCC” as **Modifier**'),),
        (Clause(110, '  - "HNPCC" as **Modifier**'),),
        'same content',
    ),
    Pair(
        (Clause(46, '**Narrower condition (takes precedence over items 1 and 7).** A disease-denoting expression is a **Modifier** when it specifies a non-disease head noun rather than naming the disorder itself.'),),
        (Clause(113, '- **IF** a disease-name span (a full name or its short-form alias) is **immediately** followed by a common-noun head that it attributively premodifies, with no intervening punctuation, bracket, participle, finite verb, or preposition, **THEN** label the span **Modifier**.'),),
        'worded differently',
        'loop08 按疾病表达是否限定非疾病中心词判断，loop04 另外要求中心词紧随其后并排除列出的间隔成分。',
        'more', '限定非疾病中心词但与该中心词之间有其他成分的疾病表达。',
    ),
    Pair(
        (Clause(47, '- an attributive premodifier of a case, patient, population, sample, study, family/kindred, series, risk, phenotype, gene, or allele noun (e.g., "ovarian cancer cases," "population-based ovarian cancer study," "ovarian cancer risk," "HNPCC kindreds," "ancient SLS genes," "the DTD gene," "G6PD deficient phenotype");'),),
        (Clause(116, '  - The decision rests on the semantic content of the following noun (e.g., "risk," "mutation," "patients," "genes") or on other occurrences of the same string in the document. The following word may confirm that the next token is a noun head, but it cannot by itself change the label.'),),
        'worded differently',
        'loop08 列出可被疾病表达限定的非疾病中心词及实例，loop04 禁止仅凭后续名词的语义或同字符串在别处的用法改变标签。',
        'unclear', 'risk、patients、genes 等中心词前的疾病表达，列举适用对象与禁止单凭词义判定不能单独确定标注数量。',
    ),
    Pair(
        (Clause(48, '- the complement of a history frame (e.g., "a family history of ovarian cancer").'),),
        (Clause(118, '- **Example.** In "a family history of ovarian cancer," "ovarian cancer" is **Specific Disease** (complement of "of," followed by punctuation). In "ovarian cancer risk," "ovarian cancer" is **Modifier** (immediately followed by a head noun).'),),
        'worded differently',
        'loop08 把 history 框架的补语纳入 Modifier，loop04 的例子把相同 history of 病名标为 Specific Disease。',
        'more', 'history of 后作为补语出现的疾病名称。',
    ),
    Pair(
        (Clause(50, 'The Modifier label applies only when the disease expression functions as a modifier.'),),
        (), 'only in loop08',
        'loop08 单独重申 Modifier 必须具有修饰功能，loop04 没有这一独立句子。',
        'unclear', '具有或不具有修饰功能的疾病表达，loop04 其他条款也规定了修饰角色。',
    ),
    Pair(
        (Clause(50, 'If the disease expression is itself the head of the phrase, or stands as a complete entity (e.g., "Coats telangiectasis"), item 1 or item 7 governs.'),),
        (Clause(124, '  - (a) The disease term is the head of the phrase, or it sits in a postmodifying prepositional phrase and is not immediately followed by a noun it premodifies (e.g., "gene for ___"). The disease is then not attributive, and the adjacency test gives **Specific Disease**.'),),
        'worded differently',
        'loop08 把独立实体或中心词交给疾病规则，loop04 在 locus 规则的排除项中还明确列出 gene for 等后置介词短语。',
        'unclear', '独立疾病名称及 gene for 后的病名，两份文字均未把这些用法直接分配为 Modifier。',
    ),
    Pair(
        (Clause(52, '**Disease expression inside a nomenclature span.** When a disease-denoting expression (a full-form name whose head is a disease-category noun, or a short form that the document has explicitly defined as a disease) is an attributive premodifier of a non-disease head, label the disease-denoting substring **Modifier**, even when that head sits inside an out-of-schema nomenclature or proper-name construction (e.g., in "the Norrie disease gene (NDP)," "Norrie disease" is a Modifier).'),),
        (Clause(120, '**Locus-designator heads.** A disease-denoting premodifier (a spelled-out disease name, or an acronym that the document has already defined as a disease) in attributive position within a noun phrase whose head denotes a gene or locus is a **Modifier**.'),),
        'worded differently',
        'loop08 明说范围外命名或专名内部的非疾病中心词也适用，loop04 在对应段落明确说明 gene 或 locus 中心词。',
        'unclear', '范围外命名内部的疾病子串，loop04 另说 locus 条款不把通用邻接测试限于 gene 中心词。',
    ),
    Pair(
        (Clause(52, "Assess that substring independently of the enclosing span, so that the span's out-of-scope status does not suppress the label."),),
        (Clause(120, 'The locus head does not turn the disease span into O.'),),
        'worded differently',
        'loop08 要求独立评估所有这类外层命名中的疾病子串，loop04 明说 locus 中心词不让疾病跨度变为 O。',
        'unclear', '外层命名中的疾病子串，两处都阻止外层名词压掉疾病标签但表述范围不同。',
    ),
    Pair(
        (Clause(52, 'Leave non-disease material, such as the head noun or identifier ("gene," "NDP"), unlabelled.'),),
        (Clause(120, 'The locus designator and any bare gene symbol remain O.'),),
        'worded differently',
        'loop08 把非疾病中心词和标识符概括为不标注，loop04 明确不标注 locus 名称及裸 gene symbol。',
        'unclear', 'gene、NDP 等非疾病部分，两处都不据此增加 Modifier。',
    ),
    Pair(
        (Clause(53, '- Do not apply this rule when (a) the disease expression is itself the head of the phrase or stands as a complete entity, in which case the disease-class or specific-disease labels govern; (b) the enclosing name contains no disease-denoting substring, so the span is simply out of scope and remains O; or (c) a short form has no disease definition in the document, so it is not anchored as a disease reference and cannot be promoted to Modifier by position alone.'),),
        (Clause(125, '  - (b) The acronym has no disease definition or established disease referent in the document, so it remains O.'),
         Clause(126, '  - (c) The span is a gene symbol or locus name containing no disease term.'),
         Clause(127, '  - (d) The premodifier is a non-disease attributive noun (e.g., anatomical, drug, or procedure terms).')),
        'worded differently',
        'loop08 排除没有文内疾病定义的短形式，loop04 允许文内定义或已确立的疾病指称，并另列非疾病修饰名词等排除项。',
        'fewer', '文内已有疾病指称但未被明确定义为疾病的短形式，按 loop08 的这一限制不能仅凭位置升为 Modifier。',
    ),
    Pair(
        (Clause(55, '**Specification versus post-modification.** A disease name that follows a non-disease noun through a "with" or "has" frame is not an attributive premodifier and is annotated as **Specific Disease** under item 1 (e.g., "63 kindreds with SLS").'),
         Clause(55, 'A disease name that is the disorder of which a form or variant is described (e.g., "the classical form of Coats disease") names the disorder itself and is **Specific Disease**.')),
        (Clause(114, "- **OTHERWISE**, label the span **Specific Disease**. This covers spans followed by punctuation, a bracket, a participle, a verb, a preposition, or nothing, and spans that head their own noun phrase, complement a preposition, or serve as a subject or verb argument. A parenthetical acronym or alias takes the class of its expanded antecedent, judged by the antecedent's syntactic position, not by the alias's own local context."),),
        'worded differently',
        'loop08 具体说明 with、has 和 form of 的疾病补语不属前置修饰，loop04 的否则分支还规定括号缩写继承展开形式标签。',
        'unclear', '后置疾病补语与括号缩写，这一组条款同时包含共同排除和 loop04 独有的继承条件。',
    ),
    Pair(
        (), (Clause(117, '  - The span is a Disease Class mention or a Composite Mention. Those are resolved by their own definitions before this test is applied.'),),
        'only in loop04',
        'loop04 明确让 Disease Class 和 Composite Mention 先于邻接测试决定，loop08 的 Modifier 规则没有同样的标签排除项。',
        'more', '本已符合 Disease Class 定义但又前置限定非疾病中心词的疾病表达。',
    ),
    Pair(
        (), (Clause(120, 'A locus head is "gene," "genes," or "gene" followed by a numeral or symbol.'),
             Clause(120, 'This rule extends the adjacency test above; it does not restrict it to gene heads.')),
        'only in loop04',
        'loop04 定义 locus 中心词的具体形式并说明通用邻接测试不局限于 gene，loop08 没有对应的独立句子。',
        'unclear', 'gene、genes 或其他非疾病中心词前的疾病名称，这些补充未单独给出相反的 Modifier 分配。',
    ),
    Pair(
        (), (Clause(120, 'Gene symbols stay outside the schema, and the Specific Disease / Disease Class boundaries are unchanged for non-attributive uses.'),),
        'only in loop04',
        'loop04 在 locus 段落补充 gene symbol 不属标签范围且不改变非修饰用法的疾病类别边界，loop08 此处没有这句。',
        'unclear', 'gene symbol 与非修饰用法，这句话没有指定新增 Modifier。',
    ),
    Pair(
        (Clause(89, '1. The deficiency term is an adjectival modifier that does not head a disease noun phrase (e.g., “[enzyme]-deficient”). Label it **Modifier** (item 3).'),),
        (Clause(38, '  - *Attributive use.* When the deficiency-type word modifies a different noun, it is attributive and is annotated as **Modifier** (rule 3), not as a Specific Disease. For example, in "G6PD-deficient phenotype," "G6PD deficient" is **Modifier**. The same holds for "deficient patients." A "deficient activity of X" or "deficiency of X" phrase is not attributive, because the deficiency word heads its own phrase; it is governed by rule 1a(i).'),),
        'worded differently',
        'loop08 简述形容词式 deficiency 修饰语应标 Modifier，loop04 还用 deficient patients 及 deficiency 短语中心词作正反说明。',
        'unclear', '形容词式 deficiency 表达，两处共有的修饰条件未给出统一的数量差异。',
    ),
    Pair(
        (), (Clause(53, '    - An attributive premodifier role is a **Modifier** (rule 3), not a Specific Disease.'),),
        'only in loop04',
        'loop04 在 generic pathology 指称测试的限制中单独重申前置修饰角色应标 Modifier，loop08 没有这一位置的重复项。',
        'unclear', '前置修饰的病理表达，loop08 在其他位置已有相同角色优先规定。',
    ),
    Pair(
        (), (Clause(78, '  - (e) It is a standalone severity, onset, or temporal qualifier (e.g., "early onset"). Such a qualifier remains a **Modifier** and is not part of a Disease Class span.'),),
        'only in loop04',
        'loop04 明确把独立的严重度、起病和时间限定语保留为 Modifier，loop08 没有对应的独立赋标条款。',
        'fewer', 'early onset 等单独出现且不构成疾病名称的严重度、起病或时间限定语。',
    ),
    Pair(
        (), (Clause(96, '  - (a) The coordinator joins disease-name or disease-category heads (e.g., organ-site modifiers sharing a disease-name head such as "cancer"). This coordinated-cancer case is not reclassified by this principle. Annotate the disease mention per rules 1b and 3, and keep multi-disease coordinations such as example 7 as Composite Mentions under the first paragraph of this rule.'),),
        'only in loop04',
        'loop04 在共享中心词的并列规则中把疾病名称中心词的情形交回规则 1b 与 3，loop08 没有这一独立条件。',
        'unclear', '共享 cancer 等疾病中心词的并列表达，交回多个规则不能单独确定 Modifier 数量。',
    ),
    Pair(
        (), (Clause(145, "The short form takes the class of its expanded antecedent (rule 3)."),),
        'only in loop04',
        'loop04 在同义提及条款中要求短形式继承展开形式的标签，loop08 的对应条款只要求长短形式分别标注。',
        'unclear', '疾病缩写，loop04 的继承规则既可能保留 Modifier 也可能保留其他标签。',
    ),
    Pair(
        (), (Clause(192, '   - The exception is a disease term attributive to them, which is a **Modifier** under rule 3 (locus-designator heads).'),),
        'only in loop04',
        'loop04 在 gene-level 排除项下重复规定修饰这些对象的疾病词应标 Modifier，loop08 没有同一位置的重复项。',
        'unclear', '修饰 gene-level 对象的疾病词，loop08 的非疾病中心词规则也涵盖这类用法。',
    ),
    Pair(
        (Clause(159, '1. **Modifier before Specific Disease / Disease Class (item 3 before item 1).** A disease-denoting expression that is an attributive premodifier of a non-disease head, or that specifies a history frame, is a **Modifier** even when its referent is a concrete individual’s disorder. The referential test and its gene-defined clause in item 1 do not override this. A disease expression that is itself the head of a phrase is never a Modifier.'),),
        (Clause(203, '1. **Attributive role before label.** A disease mention used attributively is a **Modifier** (rule 3, including locus-designator heads). The Specific Disease / Disease Class test (rule 1b) does not apply to it. For other disease-name spans, the adjacency test in rule 3 is applied first; rule 1b then decides between Specific Disease and Disease Class for non-attributive mentions not already decided by rule 1a or 1a(i).'),),
        'worded differently',
        'loop08 的优先级项明确纳入 history 框架并排除自身为中心词的病名，loop04 的优先级项继续按邻接测试及 deficiency 先行结果分流。',
        'more', 'history 框架的疾病补语，loop08 明确给 Modifier 而 loop04 的邻接规则把它分到 Specific Disease。',
    ),
    Pair(
        (Clause(165, '4. **Adjectival deficiency forms.** An adjectival deficiency form (“[enzyme]-deficient”) is a **Modifier** (item 7, Negative Constraint 1), not a Specific Disease.'),),
        (), 'only in loop08',
        'loop08 在优先级章节再次明确形容词式 deficiency 为 Modifier，loop04 没有这一位置的重复项。',
        'unclear', '形容词式 enzyme-deficient，loop04 的 deficiency 限制项已给出同类分配。',
    ),
    Pair(
        (), (Clause(207, '5. **Gene-level before disease.** Gene symbols, mutations, polymorphisms, variants, and gene-level dysfunction are O (item 8) unless a disease term is attributive to them (rule 3). A molecule-level deficiency that follows from a gene mutation is governed by rule 1a or 1a(i). If it is not a lexicalized named condition, it is a molecular-defect paraphrase and is not a disease mention. It is also not a rule 1c span (rule 1c, exclusion (b)), and it remains O.'),),
        'only in loop04',
        'loop04 在优先级章节再次保留 gene-level 对象的疾病修饰语例外并说明分子缺陷的后续排除，loop08 没有对应列表项。',
        'unclear', '修饰 gene-level 对象的疾病词，loop08 的 Modifier 条款另有覆盖而此项还包含其他类型的排除。',
    ),
    Pair(
        (Clause(237, '    - “ovarian cancer” = **Modifier** in both. In the first it is the complement of a history frame; in the second it is an attributive premodifier of a non-disease head.'),),
        (Clause(293, '    - "ovarian cancer" in "a family history of ovarian cancer" = **Specific Disease** (complement of the preposition "of," followed by punctuation; rule 3 adjacency test).'),
         Clause(294, '    - "ovarian cancer" in "ovarian cancer cases" and "ovarian cancer risk" = **Modifier** (immediately followed by a head noun).')),
        'worded differently',
        'loop08 的 worked example 把 history of 和 cases 中的病名都标 Modifier，loop04 只把 cases 与 risk 中的病名标 Modifier。',
        'more', 'a family history of ovarian cancer 中的 ovarian cancer。',
    ),
    Pair(
        (Clause(234, '    - “Coats disease” = **Specific Disease**. The phrase names the disorder whose form is described; “classical form” is not part of the mention.'),),
        (), 'only in loop08',
        'loop08 给出 form of Coats disease 的完整非 Modifier 例子，loop04 没有对应 worked example。',
        'unclear', 'form of 后的病名，loop04 的邻接测试也把介词补语分到 Specific Disease。',
    ),
    Pair(
        (Clause(240, '    - “SLS” = **Specific Disease**. The “with” frame is post-modification, not an attributive premodifier.'),),
        (), 'only in loop08',
        'loop08 单独给出 kindreds with SLS 的非 Modifier 例子，loop04 没有这一 worked example。',
        'unclear', 'kindreds with 后的 SLS，loop04 的介词补语分支也不给 Modifier。',
    ),
    Pair(
        (Clause(243, '    - “Norrie disease” = **Modifier**. “gene” and “NDP” remain unlabelled.'),),
        (Clause(297, '    - "breast cancer" = **Modifier** (locus-designator head; immediately followed by "susceptibility").'),),
        'worded differently',
        'loop08 用 Norrie disease gene 展示疾病子串的 Modifier，loop04 用 breast cancer susceptibility gene 1 展示 locus 中的 Modifier。',
        'unclear', 'gene 名称内部的疾病子串，两种例子都支持给疾病部分 Modifier。',
    ),
    Pair(
        (Clause(259, '    - “DTD” as a premodifier of “gene” is **Modifier** (item 3, short form defined in the document).'),),
        (Clause(122, '- **Example.** In "breast cancer susceptibility gene 1 (BRCA1)," "breast cancer" is **Modifier**, and "BRCA1" is O. In "SLS genes," "SLS" is **Modifier**.'),),
        'worded differently',
        'loop08 用已定义的 DTD 修饰 gene，loop04 的另一处例子用 SLS genes 并同时给出 breast cancer 的长形式。',
        'unclear', '已定义为疾病的缩写修饰 gene 或 genes，两处都给 Modifier。',
    ),
    Pair(
        (), (Clause(289, '    - "Wiskott-Aldrich syndrome" = **Modifier** (immediately followed by "protein," so the adjacency test in rule 3 applies; attributive role takes precedence over the eponym anchor).'),),
        'only in loop04',
        'loop04 单列 Wiskott-Aldrich syndrome protein 的 Modifier 例子，loop08 没有这个 worked example。',
        'unclear', 'protein 前的疾病名称，loop08 的非疾病中心词及命名内部子串规则也可涵盖。',
    ),
    Pair(
        (), (Clause(301, '    - "G6PD deficient" = **Modifier** (attributive deficiency word).'),),
        'only in loop04',
        'loop04 在 worked example 再次把 G6PD deficient 标为 Modifier，loop08 只在规则中的例子和一般 deficiency 条款说明这一用法。',
        'unclear', 'phenotype 前的 G6PD deficient，两份指南都明确涵盖这种修饰用法。',
    ),
    Pair(
        (), (Clause(323, '    - "fragile X syndrome" = **Modifier** (immediately followed by "patients").'),),
        'only in loop04',
        'loop04 单列 fragile X syndrome patients 的 Modifier 例子，loop08 没有这个 worked example。',
        'unclear', 'patients 前的疾病名称，loop08 已把 patient 中心词列入前置修饰条件。',
    ),
)


ROOT = Path(__file__).resolve().parents[4]
ANALYSIS = ROOT / 'nodes' / '2026-11-06_seminar' / 'error-analysis'  # bar_clause_pilot and bar_attribution
SHARED = ROOT / 'nodes' / 'shared' / 'error-analysis'
GUIDELINES = ANALYSIS / 'outputs/bar_clause_pilot/codex_locate/inputs/guidelines'
OUT = ROOT / 'nodes' / '2026-11-13_seminar' / 'error-analysis' / 'outputs/overall_view'
LABELS = ('Modifier', 'SpecificDisease', 'DiseaseClass')


def verify_quotes() -> tuple[int, list[str]]:
    """Check the manually written quotations against their stated plain lines."""
    count = 0
    failures = []
    for side in ('loop08', 'loop04'):
        path = GUIDELINES / f'top4_{side}.txt'
        lines = path.read_text(encoding='utf-8').splitlines()
        for row_number, pair in enumerate(PAIRS, 1):
            for clause in getattr(pair, side):
                count += 1
                if not 1 <= clause.line <= len(lines) or clause.text not in lines[clause.line - 1]:
                    failures.append(f'{side}，对照行 {row_number}，指南行 {clause.line}：引文不逐字匹配。')
    return count, failures


ARTIFACTS = (
    'type_f1.csv', 'grouped_bars.png',
    *(f'similarity_{label}.csv' for label in LABELS),
    'similarity_matrices.png', 'pair_loop08_loop04_modifier.md',
)
CHECKS = (
    'loop07 两份文件的 gold 行一致',
    '精确 d 四舍五入到四位小数等于每个 gold 行的存值',
    '33 个精确 d 合计等于柱值，|diff| < 1e-6',
    '33 组 TP、FP 等于原指南均值加变化量，|diff| < 1e-6',
    '11 个 overall_f1 等于 loops.valid_f1',
    '3 个相似度矩阵对称且对角线为 1',
    '每条引文与所写 plain 指南行号逐字一致',
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def prefix(guideline: str) -> str:
    return guideline.replace('top-4 ', 'top4_').replace('top-1 ', 'top1_')


def existing_label_counts() -> dict:
    """Execute only the existing read/count sections, with no module writes.

    loop_label_tables.py has top-level reporting and writes. Select its exact
    AST statements for run discovery, saved overall metrics, and C/D counts.
    No matcher, pairing rule, error category, or FP logic is reimplemented.
    """
    path = SHARED / 'scripts/loop_label_tables.py'
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))

    def assignment(target: str) -> int:
        return next(i for i, node in enumerate(tree.body)
                    if isinstance(node, ast.Assign)
                    and ast.unparse(node.targets[0]) == target)

    nodes = (tree.body[assignment('ROOT'):assignment('(out, rec)')]
             + tree.body[assignment('n_lab'):assignment('ov')])
    namespace = {
        '__file__': str(path), 'Path': Path, 'csv': csv, 'json': json,
        'Counter': Counter,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    require(namespace['ROOT'] == ROOT, 'Existing counting code resolved a different root.')
    return namespace


def gold_key(row: dict[str, str]) -> tuple[str, int, int, str]:
    return row['doc'], int(row['start']), int(row['end']), row['gold_label']


def gold_universe() -> dict[str, tuple]:
    keys = {label: [] for label in (*LABELS, 'CompositeMention')}
    for path in sorted((ROOT / 'data/datasets/ncbi_disease/valid').glob('*.json')):
        document = json.loads(path.read_text(encoding='utf-8'))
        for mention in document['denotations']:
            label = mention['obj']
            keys[label].append((str(document['sourceid']), mention['span']['begin'],
                                mention['span']['end'], label))
    for label, mentions in keys.items():
        require(len(mentions) == len(set(mentions)), f'Duplicate gold key: {label}')
    return {label: tuple(sorted(mentions)) for label, mentions in keys.items()}


def loop07_check() -> int:
    """Compare gold identities and outcomes, excluding locating metadata."""
    base = ANALYSIS / 'outputs/bar_clause_pilot'
    fields = ('category', 'doc', 'start', 'end', 'text', 'gold_label',
              'n_orig_of_19', 'd', 'target_state', 'target_pred_label',
              'target_pred_start', 'target_pred_end', 'target_pred_text')
    signatures = []
    for filename in ('top4_loop07_instances.csv', 'loop07_instances.csv'):
        signatures.append(Counter(tuple(row[field] for field in fields)
                                  for row in read_csv(base / filename) if row['gold_label']))
    require(signatures[0] == signatures[1], 'The two loop07 files disagree on gold rows.')
    return sum(signatures[0].values())


def exact_vectors(guidelines: list[str], universe: dict) -> tuple[dict, int]:
    vectors = {}
    all_keys = set().union(*(set(keys) for keys in universe.values()))
    checked_rows = 0
    for guideline in guidelines:
        rows = read_csv(ANALYSIS / 'outputs/bar_clause_pilot' / f'{prefix(guideline)}_instances.csv')
        values = {}
        for row in rows:
            if not row['gold_label']:
                continue
            key = gold_key(row)
            require(key in all_keys, f'{guideline}: unknown gold key {key}')
            require(key not in values, f'{guideline}: duplicate gold key {key}')
            n_orig = int(row['n_orig_of_19'])
            require(0 <= n_orig <= 19, f'{guideline}: invalid baseline count {key}')
            y = int(row['category'] == 'gold_now_right')
            exact = Fraction(y) - Fraction(n_orig, 19)
            require(round(exact, 4) == Fraction(row['d']),
                    f'{guideline}, {key}: exact d={exact} does not round to stored {row["d"]}')
            values[key] = exact
            checked_rows += 1
        vectors[guideline] = {
            label: tuple(values.get(key, Fraction(0)) for key in universe[label])
            for label in LABELS
        }
    return vectors, checked_rows


def cosine_matrix(order: list[str], vectors: dict, label: str) -> list[list[float]]:
    # Fractions retain exact integer-count d values through dot products.
    norms = {g: sum(value * value for value in vectors[g][label]) for g in order}
    for g in order:
        require(norms[g] > 0, f'{label}, {g}: cosine undefined for a zero vector.')
    return [[float(sum(a * b for a, b in zip(vectors[g][label], vectors[h][label])))
             / math.sqrt(float(norms[g] * norms[h])) for h in order] for g in order]


def item_rows(side: str) -> list[dict[str, str]]:
    path = ANALYSIS / f'outputs/bar_clause_pilot/codex_locate/aggregate/top4_{side}_items.csv'
    return [row for row in read_csv(path) if row['level'] == 'item']


def clause_cell(clauses: tuple[Clause, ...], items: list[dict]) -> str:
    if not clauses:
        return ''
    quotes = [f'L{clause.line}: `{clause.text}`' for clause in clauses]
    covering = []
    for item in items:
        start, end = map(int, item['lines'].split('-'))
        if any(start <= clause.line <= end for clause in clauses):
            covering.append('; '.join(f'{field}={item[field]}' for field in
                                      ('item_id', 'lines', 'n', 'gold_gain', 'gold_loss', 'new_fp_n')))
    return '<br><br>'.join(quotes + ['现有条目：' + '<br>'.join(covering)
                                   if covering else '现有条目：没有覆盖这些引文行的 item 级行。'])


def pair_markdown(bars: dict) -> str:
    # PAIRS is unchanged from the first run. Only now attach existing counts.
    items08, items04 = item_rows('loop08'), item_rows('loop04')
    lines = [
        '# top-4 loop08 与 top-4 loop04：Modifier 条款对照', '',
        '行号为 plain 指南从 1 起的行号。沿用首次运行中先于 instances、predictions 和 items.csv 阅读写定的条款方向。', '',
        '现有统计只抄录 level 为 item、lines 覆盖引文行的记录；同一提及可出现在多条记录中，不求和。', '',
        '| 对照行 | loop08 行号、逐字原文与现有条目 | loop04 行号、逐字原文与现有条目 | status | 文字差别 | loop08 相对 loop04 的 Modifier 方向及对象 |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for i, pair in enumerate(PAIRS, 1):
        require(pair.status in ('same content', 'worded differently', 'only in loop08', 'only in loop04'),
                f'Pair {i}: invalid status.')
        if pair.status != 'same content':
            require(pair.direction in ('more', 'fewer', 'unclear') and pair.difference and pair.affected,
                    f'Pair {i}: missing frozen difference or direction.')
        direction = f'`{pair.direction}`：{pair.affected}' if pair.direction else ''
        cells = (str(i), clause_cell(pair.loop08, items08), clause_cell(pair.loop04, items04),
                 pair.status, pair.difference, direction)
        require(all('|' not in cell for cell in cells), f'Pair {i}: unescaped table delimiter.')
        lines.append('| ' + ' | '.join(cells) + ' |')
    lines += ['', f'top-4 loop08 Modifier：{bars["Modifier"]["top-4 loop08"]:+.2f}', '',
              f'top-4 loop04 Modifier：{bars["Modifier"]["top-4 loop04"]:+.2f}']
    return '\n'.join(lines) + '\n'


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


@contextmanager
def plot_config():
    """Use inherited workspace permissions rather than tempfile's owner ACL."""
    config = OUT / 'matplotlib_config'
    config.mkdir(exist_ok=True)
    try:
        yield str(config)
    finally:
        for path in config.glob('fontlist-v*.json'):
            path.unlink()
        config.rmdir()


def figures(orders: dict, rows_by_key: dict, bars: dict, by_label: dict, matrices: dict) -> None:
    # Keep matplotlib configuration/cache temporary and use no GUI backend.
    with plot_config() as config:
        os.environ['MPLCONFIGDIR'] = config
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
        fig, axes = plt.subplots(3, 1, figsize=(18, 14), layout='constrained')
        for ax, label, color in zip(axes, LABELS, ('#315b83', '#4f7d72', '#8c634e')):
            order = orders[label]
            values = [bars[label][g] for g in order]
            padding = max(3.0, (max(values) - min(values)) * 0.12)
            ax.bar(range(len(order)), values, width=0.68, color=color)
            ax.axhline(0, color='#242424', linewidth=1)
            for i, (g, value) in enumerate(zip(order, values)):
                if by_label[g][label]['tp_out']:
                    ax.scatter(i, value + (padding * 0.3 if value >= 0 else -padding * 0.3),
                               marker='*', s=95, color='#151515', zorder=4)
            ax.set_xticks(range(len(order)),
                          [g.replace(' ', '\n') + f'\nF1 {rows_by_key[g, label]["f1"]:.3f}' for g in order])
            ax.set_ylim(min(0, min(values)) - padding, max(0, max(values)) + padding)
            ax.set_title(label, loc='left', fontweight='bold')
            ax.set_ylabel('Strict TP change\nvs. 19-run mean')
            ax.set_axisbelow(True)
            ax.grid(axis='y', alpha=0.2)
        fig.suptitle('Refined guidelines by entity type\n'
                     'Descending label F1; ties by overall F1. Star: TP outside the 19 original runs\' range.',
                     fontsize=15)
        fig.savefig(OUT / 'grouped_bars.png', dpi=180)
        plt.close(fig)

        fig, axes = plt.subplots(1, 3, figsize=(24, 9), layout='constrained')
        for ax, label in zip(axes, LABELS):
            order = orders[label]
            matrix = matrices[label]
            heatmap = ax.imshow(matrix, cmap='RdBu_r', vmin=-1, vmax=1)
            ax.set_xticks(range(len(order)), [g.replace(' ', '\n') for g in order], fontsize=8)
            ax.set_yticks(range(len(order)), order, fontsize=9)
            for i, row in enumerate(matrix):
                for j, value in enumerate(row):
                    ax.text(j, i, f'{value:.2f}', ha='center', va='center', fontsize=8,
                            color='white' if abs(value) >= 0.55 else '#202020')
            ax.set_title(label, fontweight='bold')
        fig.colorbar(heatmap, ax=list(axes), shrink=0.65, label='Cosine similarity')
        fig.suptitle('Gold-mention TP change vectors: cosine similarity\n'
                     'Exact d = y - n_orig_of_19 / 19; descending label F1, ties by overall F1.', fontsize=15)
        fig.savefig(OUT / 'similarity_matrices.png', dpi=180)
        plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # These named artifacts belong exclusively to this run and its first run.
    # Remove old figures before checks, so failures can never leave stale plots.
    for filename in ARTIFACTS:
        (OUT / filename).unlink(missing_ok=True)
    report_path = OUT / 'overall_view_output.txt'
    details = []
    passed = set()
    current = '读取输入'
    try:
        bars = json.loads((ANALYSIS / 'outputs/bar_attribution.json').read_text(encoding='utf-8'))['bars']
        tables = json.loads((SHARED / 'outputs/loop_label_tables.json').read_text(encoding='utf-8'))
        guidelines = list(bars['Modifier'])
        require(len(guidelines) == 11, 'Expected 11 refined guidelines.')
        require(all(set(bars[label]) == set(guidelines) for label in LABELS), 'Bar guideline sets differ.')

        current = CHECKS[0]
        n_loop07 = loop07_check()
        details.append(f'PASS：{current}，{n_loop07} 个 gold 行的身份及结果字段一致；不比较定位元数据。')
        passed.add(current)

        current = CHECKS[1]
        universe = gold_universe()
        vectors, n_exact = exact_vectors(guidelines, universe)
        details.append(f'PASS：{current}，{n_exact}/{n_exact} 行通过（包括输入中的 CompositeMention gold 行）。')
        passed.add(current)

        current = CHECKS[2]
        for g in guidelines:
            for label in LABELS:
                total = float(sum(vectors[g][label]))
                difference = total - bars[label][g]
                require(abs(difference) < 1e-6, f'{g}, {label}: sum d differs from bar by {difference}')
                details.append(f'  {g}, {label}: sum_d={total:.12f}, bar={bars[label][g]:.12f}, '
                               f'diff={difference:+.12f}, PASS')
        details.append(f'PASS：{current}，33/33。')
        passed.add(current)

        counts = existing_label_counts()
        require(set(guidelines) == {counts['name'][run] for run in counts['changed']},
                'Existing counting code and bar guideline sets differ.')
        loops = {f'{row["method"]} loop{row["loop"]:02d}': row for row in tables['loops']}
        rows = []
        for run in counts['changed']:
            g = counts['name'][run]
            for label in LABELS:
                gold_n, tp, fp = counts['n_lab'][label], counts['tp'][run][label], counts['fp'][run][label]
                fn = gold_n - tp
                rows.append(dict(guideline=g, label=label, gold_n=gold_n, tp=tp, fp=fp, fn=fn,
                                 f1=2 * tp / (2 * tp + fp + fn), overall_f1=counts['met'][run]['f1']))
        rows_by_key = {(row['guideline'], row['label']): row for row in rows}

        current = CHECKS[3]
        for row in rows:
            g, label = row['guideline'], row['label']
            expected_tp = tables['start'][label]['tp_mean'] + tables['by_label'][g][label]['tp']
            mean_fp = statistics.mean(counts['fp'][run][label] for run in counts['orig'])
            expected_fp = mean_fp + tables['by_label'][g][label]['fp']
            require(abs(row['tp'] - expected_tp) < 1e-6 and abs(row['fp'] - expected_fp) < 1e-6,
                    f'{g}, {label}: TP/FP mismatch: {row["tp"]}/{row["fp"]} vs {expected_tp}/{expected_fp}')
            require(row['gold_n'] == len(universe[label]) == tables['start'][label]['gold'],
                    f'{g}, {label}: gold mention totals differ.')
            details.append(f'  {g}, {label}: TP={row["tp"]}, expected_TP={expected_tp:.12f}; '
                           f'FP={row["fp"]}, mean_FP={mean_fp:.12f}, expected_FP={expected_fp:.12f}, PASS')
        details.append(f'PASS：{current}，33/33；复用 loop_label_tables.py 的 run 发现与 C/D 计数语句，19 次原指南。')
        passed.add(current)

        current = CHECKS[4]
        for g in guidelines:
            actual = rows_by_key[g, 'Modifier']['overall_f1']
            expected = loops[g]['valid_f1']
            require(actual == expected, f'{g}: overall_f1 {actual} != {expected}')
            details.append(f'  {g}: overall_f1={actual}, loops.valid_f1={expected}, PASS')
        details.append(f'PASS：{current}，11/11。')
        passed.add(current)

        orders = {label: sorted(guidelines, key=lambda g: (-rows_by_key[g, label]['f1'],
                                                         -rows_by_key[g, label]['overall_f1'], g))
                  for label in LABELS}
        current = CHECKS[5]
        matrices = {label: cosine_matrix(orders[label], vectors, label) for label in LABELS}
        for label, matrix in matrices.items():
            asymmetry = max(abs(matrix[i][j] - matrix[j][i]) for i in range(11) for j in range(11))
            diagonal = max(abs(matrix[i][i] - 1) for i in range(11))
            require(asymmetry < 1e-12 and diagonal < 1e-12,
                    f'{label}: matrix asymmetry={asymmetry}, diagonal deviation={diagonal}')
            require(all(-1 - 1e-12 <= value <= 1 + 1e-12 for row in matrix for value in row),
                    f'{label}: cosine out of range.')
            details.append(f'  {label}: 11 x 11; max_asymmetry={asymmetry:.3g}, '
                           f'max_diagonal_error={diagonal:.3g}, gold_n={len(universe[label])}, PASS')
        details.append(f'PASS：{current}，3/3；缺失提及填 0，仅使用 gold 行的 TP 差值。')
        passed.add(current)

        current = CHECKS[6]
        quoted_count, quote_failures = verify_quotes()
        require(not quote_failures, '\n'.join(quote_failures))
        pair_text = pair_markdown(bars)
        for pair in PAIRS:
            for clause in (*pair.loop08, *pair.loop04):
                require(f'L{clause.line}: `{clause.text}`' in pair_text, 'A quotation was altered in pair rendering.')
        details.append(f'PASS：{current}，{quoted_count}/{quoted_count} 条引文，{len(PAIRS)} 个对照行。')
        passed.add(current)

        current = '写出指定产物'
        write_csv(OUT / 'type_f1.csv', ['guideline', 'label', 'gold_n', 'tp', 'fp', 'fn', 'f1', 'overall_f1'],
                  [rows_by_key[g, label] for label in LABELS for g in orders[label]])
        for label in LABELS:
            order = orders[label]
            write_csv(OUT / f'similarity_{label}.csv', ['guideline', *order],
                      [dict(guideline=g, **dict(zip(order, row))) for g, row in zip(order, matrices[label])])
        (OUT / 'pair_loop08_loop04_modifier.md').write_text(pair_text, encoding='utf-8')
        figures(orders, rows_by_key, bars, tables['by_label'], matrices)
        listing = []
        for label in LABELS:
            listing += [label, 'guideline | label_f1 | bar_TP_change | tp_out | FP_change | fp_out | cosine_with_highest_label_f1',
                        f'最高 label F1 的指南：{orders[label][0]}']
            for i, g in enumerate(orders[label]):
                cell = tables['by_label'][g][label]
                listing.append(f'{g} | {rows_by_key[g, label]["f1"]:.9f} | {bars[label][g]:+.9f} | '
                               f'{str(cell["tp_out"]).lower()} | {cell["fp"]:+.9f} | '
                               f'{str(cell["fp_out"]).lower()} | {matrices[label][i][0]:.9f}')
            listing.append('')
        report = ['2026-11-08 overall view 执行记录', '', '状态：完成。',
                  '排序：各标签严格 F1 降序，同分按整体 F1 降序；仍同分则按指南名称。',
                  'd = y - n_orig_of_19 / 19，以 Fraction 精确重建；未使用已舍入 d 做求和或余弦。', '',
                  *listing, '检查结果', *details, '',
                  '首次运行的 PAIRS 文字及方向未修改；方向先于统计阅读写定，现有条目统计仅按行号附入，没有新计数或求和。']
        report_path.write_text('\n'.join(report) + '\n', encoding='utf-8')
        print(f'PASS: all {len(CHECKS)} check groups; {n_exact} exact-d rows, 33 TP/FP rows, '
              f'3 matrices, {quoted_count} verbatim quotations.')
        print(f'Wrote {len(ARTIFACTS) + 1} outputs to {OUT}')
        return 0
    except Exception as exc:
        # Any failed required check stops here, before figures can be produced.
        for filename in ('grouped_bars.png', 'similarity_matrices.png'):
            (OUT / filename).unlink(missing_ok=True)
        report = ['2026-11-08 overall view 执行记录', '', '状态：停止，未保留图表。',
                  f'FAIL：{current}', f'{type(exc).__name__}: {exc}', '', *details, '',
                  *(f'NOT RUN / NOT PASSED：{check}' for check in CHECKS if check not in passed)]
        report_path.write_text('\n'.join(report) + '\n', encoding='utf-8')
        print(f'STOP: {current}: {exc}')
        print(f'Details: {report_path}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
