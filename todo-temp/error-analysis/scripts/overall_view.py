"""Required overall-view preflight and frozen text-first Modifier judgments.

Run with python -I. PAIRS was written after reading both complete guidelines,
before opening prediction, instance, or item aggregate files for this task.
The directions are fixed text-only judgments, not inferred from outcomes.

Execution stopped at the specification's first numeric check: the supplied
four-decimal CSV differences do not sum to the full-precision bars within
1e-6. Downstream tables, figures, and the assembled pair were therefore not
generated. The remaining pipeline has not been implemented past this gate.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import dataclass
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


ROOT = Path(__file__).resolve().parents[3]
ANALYSIS = ROOT / 'todo-temp' / 'error-analysis'
GUIDELINES = ANALYSIS / 'outputs/bar_clause_pilot/codex_locate/inputs/guidelines'
OUT = ANALYSIS / 'outputs/overall_view'
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


def main() -> int:
    """Record the failed mandatory check, then stop without downstream writes."""
    report_path = OUT / 'overall_view_output.txt'
    if report_path.exists():
        raise FileExistsError(f'Refusing to modify an existing output: {report_path}')

    quoted_count, quote_failures = verify_quotes()
    bars = json.loads((ANALYSIS / 'outputs/bar_attribution.json').read_text(encoding='utf-8'))['bars']
    results = []
    numeric_failures = []
    # Use the d column exactly as supplied. Do not reconstruct it from integer
    # counts or relax the tolerance after observing a failure.
    for guideline in bars['Modifier']:
        prefix = guideline.replace('top-4 ', 'top4_').replace('top-1 ', 'top1_')
        path = ANALYSIS / 'outputs/bar_clause_pilot' / f'{prefix}_instances.csv'
        with path.open(encoding='utf-8', newline='') as stream:
            gold_rows = [row for row in csv.DictReader(stream) if row['gold_label']]
        for label in LABELS:
            actual = math.fsum(float(row['d']) for row in gold_rows if row['gold_label'] == label)
            expected = bars[label][guideline]
            difference = actual - expected
            passed = abs(difference) < 1e-6
            line = (f'{guideline}, {label}: sum_d={actual:.12f}, '
                    f'bar={expected:.12f}, diff={difference:+.12f}, '
                    f'{"PASS" if passed else "FAIL"}')
            results.append(line)
            if not passed:
                numeric_failures.append(line)

    lines = [
        '2026-11-08 overall view 执行记录',
        '',
        '状态：按规格的失败停止条款中止，未生成图表或后续统计文件。',
        '规格：todo-temp/error-analysis/notes/20261108_overall_view_spec.md',
        '',
        '检查 1：每份指南、每个标签的 gold 行 d 之和等于柱值，要求 |diff| < 1e-6。',
        f'结果：FAIL，{len(numeric_failures)}/{len(results)} 项不满足容差。',
        *results,
        '',
        '输入 CSV 的 d 以四位小数保存；以上按该列原值求和，未从 n_orig_of_19 重算，也未放宽容差。',
        '',
        '检查 2：type_f1.csv 的 TP、FP 与 19 次原指南均值加变化量一致。',
        '结果：NOT RUN，检查 1 失败后停止，未生成 type_f1.csv。',
        '',
        '检查 3：overall_f1 等于 loops 中该指南的 valid_f1。',
        '结果：NOT RUN，检查 1 失败后停止。',
        '',
        '检查 4：三张相似度矩阵对称且对角线为 1。',
        '结果：NOT RUN，检查 1 失败后停止，未计算或输出矩阵。',
        '',
        '检查 5：逐字引文与所写指南行号一致。',
        (f'结果：FAIL，{len(quote_failures)}/{quoted_count} 条引文不符。'
         if quote_failures else f'结果：PASS，脚本中已写定的 {quoted_count} 条引文逐字匹配；未组装最终 pair 文件。'),
        *quote_failures,
        '',
        'top4_loop07_instances.csv 与 loop07_instances.csv 的 gold 行一致性：NOT RUN，检查 1 失败后停止。',
        '',
        '条款对照：两份指南均已完整阅读；PAIRS 中的文字方向先于本次读取 instances 和 items.csv 写定。',
        '现有 items.csv 仅查看了列与首行，尚未把统计附到对照行；未输出 pair_loop08_loop04_modifier.md。',
        '未生成：type_f1.csv、grouped_bars.png、三份 similarity_<label>.csv、similarity_matrices.png、pair_loop08_loop04_modifier.md。',
        '现有输入、PROGRESS.md、LOG.md、报告和 slides 均未修改；未调用 API、追加标注或提交。',
    ]
    # This script is the recorded stop point, not a completed downstream
    # pipeline. If upstream data changes, revisit the specification explicitly.
    if not numeric_failures and not quote_failures:
        raise RuntimeError('Recorded preflight failure no longer reproduces; downstream work needs to be resumed.')
    OUT.mkdir(parents=True, exist_ok=True)
    with report_path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write('\n'.join(lines) + '\n')
    print(f'STOP: {len(numeric_failures)}/{len(results)} sum-d checks failed; '
          f'{quoted_count - len(quote_failures)}/{quoted_count} quotations matched.')
    print(f'Failure details: {report_path}')
    print('No figures or downstream tables were generated.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
