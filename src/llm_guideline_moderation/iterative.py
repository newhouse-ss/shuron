from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .evaluation import (
    DocumentPair,
    PubAnnotationDiagnostics,
    PubAnnotationEvaluation,
    PubAnnotationEvaluatorOptions,
    build_pubannotation_diagnostics,
)
from .pipeline import annotate_with_guidelines
from .prompts import render_prompt
from .sampling import SampledDocument
from .types import Annotation, EntityDefinition, OutputConfiguration

SAFE_MAX_ITERATIONS = 20


@dataclass(slots=True)
class DiscrepancyExample:
    doc_id: str
    text_snippet: str
    gold_entity: str
    llm_entity: str
    entity_text: str
    start: int
    end: int
    gold_text: str | None = None
    llm_text: str | None = None
    llm_start: int | None = None
    llm_end: int | None = None
    snippet_start_offset: int = 0


@dataclass(slots=True)
class DiscrepancyCluster:
    key: str
    count: int
    examples: list[DiscrepancyExample]
    gold_label: str
    llm_label: str


@dataclass(slots=True)
class ModerationSummary:
    overall_f1: float
    precision: float
    recall: float
    true_positives: int
    false_positives: int
    false_negatives: int
    all_clusters: list[DiscrepancyCluster]
    dominant_cluster: DiscrepancyCluster
    all_doc_names: list[str]
    label_mismatch: int
    span_error: int
    is_good_enough: bool


@dataclass(slots=True)
class IterationSnapshot:
    iteration: int
    guidelines_before: str
    guidelines_after: str
    evaluation_before: PubAnnotationEvaluation
    evaluation_after: PubAnnotationEvaluation
    diagnostics_before: PubAnnotationDiagnostics
    diagnostics_after: PubAnnotationDiagnostics
    summary_before: ModerationSummary
    summary_after: ModerationSummary
    discrepancy_insight: str
    moderation_principle: str
    prompts: dict[str, str] = field(default_factory=dict)
    improved: bool = False
    reverted: bool = False
    # What the refinement step actually produced and how it scored, kept whether
    # or not it was adopted. On a reverted iteration guidelines_after,
    # summary_after and diagnostics_after are all reset to the "before" values,
    # so without these fields the candidate leaves no trace at all: its F1, its
    # per-document annotations and its text are discarded, and a reverted round
    # cannot be diagnosed beyond "F1 did not increase". Diagnostic only - the
    # revert logic is unchanged and none of this feeds back into the loop.
    guidelines_candidate: str = ""
    summary_candidate: ModerationSummary | None = None
    diagnostics_candidate: PubAnnotationDiagnostics | None = None


@dataclass(slots=True)
class IterativeRefinementResult:
    sampled_documents: list[str]
    sampled_sourceids: list[str]
    initial_guidelines: str
    final_guidelines: str
    initial_evaluation: PubAnnotationEvaluation
    final_evaluation: PubAnnotationEvaluation
    initial_diagnostics: PubAnnotationDiagnostics
    final_diagnostics: PubAnnotationDiagnostics
    initial_summary: ModerationSummary
    final_summary: ModerationSummary
    iterations: list[IterationSnapshot]
    stop_reason: str
    threshold_reached: bool
    valid_threshold: float


def _entity_schema_text(entities: list[EntityDefinition]) -> str:
    lines = []
    for entity in entities:
        lines.append(f"- {entity.name}: {entity.description}" if entity.description else f"- {entity.name}")
    return "\n".join(lines)


def _annotation_label(annotation: Annotation) -> str:
    return annotation.entity


def _annotation_to_key(annotation: Annotation) -> tuple[int, int, str]:
    return (annotation.start, annotation.end, _annotation_label(annotation))


def _annotation_summary(annotation: Annotation) -> str:
    label = _annotation_label(annotation)
    return f"{label} [{annotation.start}, {annotation.end}] \"{annotation.text}\""


def _is_exact_match(gold: Annotation, llm: Annotation) -> bool:
    return (
        _annotation_label(gold) == _annotation_label(llm)
        and gold.start == llm.start
        and gold.end == llm.end
    )


def _calculate_f1(gold_annotations: list[Annotation], llm_annotations: list[Annotation]) -> tuple[int, int, int, float, float, float]:
    gold_keys = {_annotation_to_key(annotation) for annotation in gold_annotations}
    llm_keys = {_annotation_to_key(annotation) for annotation in llm_annotations}

    true_positives = len(gold_keys & llm_keys)
    false_positives = len(llm_keys - gold_keys)
    false_negatives = len(gold_keys - llm_keys)
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return true_positives, false_positives, false_negatives, precision, recall, f1


def _build_discrepancy_clusters(pairs: list[DocumentPair]) -> list[DiscrepancyCluster]:
    discrepancy_map: dict[str, DiscrepancyCluster] = {}

    for pair in pairs:
        text = pair.text
        gold_annotations = pair.gold_annotations
        llm_annotations = pair.llm_annotations
        matched_gold: set[int] = set()
        matched_llm: set[int] = set()

        for gold_index, gold in enumerate(gold_annotations):
            for llm_index, llm in enumerate(llm_annotations):
                if _is_exact_match(gold, llm):
                    matched_gold.add(gold_index)
                    matched_llm.add(llm_index)

        for gold_index, gold in enumerate(gold_annotations):
            if gold_index in matched_gold:
                continue

            for llm_index, llm in enumerate(llm_annotations):
                if llm_index in matched_llm:
                    continue

                overlap = max(0, min(gold.end, llm.end) - max(gold.start, llm.start))
                if overlap <= 0:
                    continue

                is_same_entity = _annotation_label(gold) == _annotation_label(llm)
                error_type = "Span Boundary Error" if is_same_entity else "Label Mismatch"
                gold_label = _annotation_label(gold)
                llm_label = _annotation_label(llm)
                key = f"Gold: {gold_label} vs LLM: {llm_label} ({error_type})"

                cluster = discrepancy_map.setdefault(
                    key,
                    DiscrepancyCluster(
                        key=key,
                        count=0,
                        examples=[],
                        gold_label=gold_label,
                        llm_label=llm_label,
                    ),
                )
                cluster.count += 1
                if len(cluster.examples) < 100:
                    snippet_start = max(0, gold.start - 60)
                    snippet_end = min(len(text), gold.end + 60) # make the context window 60 characters before and after the gold annotation
                    cluster.examples.append(
                        DiscrepancyExample(
                            doc_id=pair.filename,
                            text_snippet=text[snippet_start:snippet_end],
                            gold_entity=gold_label,
                            llm_entity=llm_label,
                            entity_text=gold.text,
                            gold_text=gold.text,
                            llm_text=llm.text,
                            start=gold.start,
                            end=gold.end,
                            llm_start=llm.start,
                            llm_end=llm.end,
                            snippet_start_offset=snippet_start,
                        )
                    )

                matched_gold.add(gold_index)
                matched_llm.add(llm_index)

        for gold_index, gold in enumerate(gold_annotations):
            if gold_index in matched_gold:
                continue
            gold_label = _annotation_label(gold) or "Unknown"
            key = f"Gold: {gold_label} vs LLM: O (Missed)"
            cluster = discrepancy_map.setdefault(
                key,
                DiscrepancyCluster(
                    key=key,
                    count=0,
                    examples=[],
                    gold_label=gold_label,
                    llm_label="O",
                ),
            )
            cluster.count += 1
            if len(cluster.examples) < 100:
                snippet_start = max(0, gold.start - 60)
                snippet_end = min(len(text), gold.end + 60)
                cluster.examples.append(
                    DiscrepancyExample(
                        doc_id=pair.filename,
                        text_snippet=text[snippet_start:snippet_end],
                        gold_entity=gold_label,
                        llm_entity="O",
                        entity_text=gold.text,
                        start=gold.start,
                        end=gold.end,
                        snippet_start_offset=snippet_start,
                    )
                )

        for llm_index, llm in enumerate(llm_annotations):
            if llm_index in matched_llm:
                continue
            llm_label = _annotation_label(llm) or "Unknown"
            key = f"Gold: O vs LLM: {llm_label} (Added)"
            cluster = discrepancy_map.setdefault(
                key,
                DiscrepancyCluster(
                    key=key,
                    count=0,
                    examples=[],
                    gold_label="O",
                    llm_label=llm_label,
                ),
            )
            cluster.count += 1
            if len(cluster.examples) < 100:
                snippet_start = max(0, llm.start - 60)
                snippet_end = min(len(text), llm.end + 60)
                cluster.examples.append(
                    DiscrepancyExample(
                        doc_id=pair.filename,
                        text_snippet=text[snippet_start:snippet_end],
                        gold_entity="O",
                        llm_entity=llm_label,
                        entity_text=llm.text,
                        start=llm.start,
                        end=llm.end,
                        snippet_start_offset=snippet_start,
                    )
                )

    return sorted(discrepancy_map.values(), key=lambda cluster: cluster.count, reverse=True)


def _summarize_moderation_pairs(pairs: list[DocumentPair], f1_threshold: float) -> ModerationSummary:
    total_tp = total_fp = total_fn = 0
    for pair in pairs:
        tp, fp, fn, _, _, _ = _calculate_f1(pair.gold_annotations, pair.llm_annotations)
        total_tp += tp
        total_fp += fp
        total_fn += fn

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    overall_f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    all_clusters = _build_discrepancy_clusters(pairs)
    dominant_cluster = all_clusters[0] if all_clusters else DiscrepancyCluster(
        key="None",
        count=0,
        examples=[],
        gold_label="",
        llm_label="",
    )

    return ModerationSummary(
        overall_f1=overall_f1,
        precision=precision,
        recall=recall,
        true_positives=total_tp,
        false_positives=total_fp,
        false_negatives=total_fn,
        all_clusters=all_clusters,
        dominant_cluster=dominant_cluster,
        all_doc_names=[pair.filename for pair in pairs],
        label_mismatch=sum(
            cluster.count
            for cluster in all_clusters
            if cluster.gold_label != "O" and cluster.llm_label != "O" and cluster.gold_label != cluster.llm_label
        ),
        span_error=sum(
            cluster.count
            for cluster in all_clusters
            if cluster.gold_label == cluster.llm_label and cluster.gold_label != "O"
        ),
        is_good_enough=overall_f1 >= f1_threshold,
    )


def _build_pairs(
    sampled_documents: list[SampledDocument],
    predictions: dict[str, list[Annotation]],
) -> list[DocumentPair]:
    return [
        DocumentPair(
            filename=document.filename,
            text=document.text,
            llm_annotations=predictions.get(document.filename, []),
            gold_annotations=document.gold_annotations,
            gold_filename=document.filename,
            match_strategy="pubannotation",
        )
        for document in sampled_documents
    ]


def _annotate_documents(
    sampled_documents: list[SampledDocument],
    guidelines: str,
    entities: list[EntityDefinition],
    provider,
    instructions: str,
    output_configuration: OutputConfiguration,
) -> dict[str, list[Annotation]]:
    predictions: dict[str, list[Annotation]] = {}
    for document in sampled_documents:
        result = annotate_with_guidelines(
            text=document.text,
            guidelines=guidelines,
            entities=entities,
            provider=provider,
            instructions=instructions,
            output_configuration=output_configuration,
        )
        predictions[document.filename] = result.annotations
    return predictions


def _build_discrepant_examples_from_cluster(cluster: DiscrepancyCluster, n_examples: int) -> str:
    if not cluster.examples:
        return "(no discrepancy examples found)"
    return "\n\n".join(
        "\n".join(
            [
                f"Example {idx + 1} (Doc: {example.doc_id}):",
                f'Snippet: "...{example.text_snippet}..."',
                f"Gold: {example.gold_entity}, LLM: {example.llm_entity}",
                f'Entity Text: "{example.entity_text}"',
            ]
        )
        for idx, example in enumerate(cluster.examples[:n_examples])
    )


def _build_true_positive_examples(
    sampled_documents: list[SampledDocument],
    predictions: dict[str, list[Annotation]],
    n_examples: int,
) -> str:
    blocks: list[str] = []
    for document in sampled_documents:
        gold_keys = {_annotation_to_key(annotation): annotation for annotation in document.gold_annotations}
        pred_annotations = predictions.get(document.filename, [])
        pred_keys = {_annotation_to_key(annotation): annotation for annotation in pred_annotations}
        matched = [gold_keys[key] for key in gold_keys.keys() & pred_keys.keys()]
        if not matched:
            continue
        lines = [f"FILE: {document.filename}", f"TEXT: {document.text}", "MATCHED ANNOTATIONS:"]
        lines.extend(f"- {_annotation_summary(annotation)}" for annotation in matched[:n_examples])
        blocks.append("\n".join(lines))
        if len(blocks) >= n_examples:
            break
    return "\n\n".join(blocks) or "(no true positive examples found)"


def _build_verified_examples(
    sampled_documents: list[SampledDocument],
    predictions: dict[str, list[Annotation]],
    n_examples: int,
) -> str:
    return _build_true_positive_examples(sampled_documents, predictions, n_examples)


def _refine_guidelines_from_pairs(
    sampled_documents: list[SampledDocument],
    predictions: dict[str, list[Annotation]],
    current_guidelines: str,
    entities: list[EntityDefinition],
    summary: ModerationSummary,
    provider,
    n_examples: int,
) -> tuple[str, str, str, dict[str, str]]:
    dominant_cluster = summary.dominant_cluster
    discrepancy_examples = _build_discrepant_examples_from_cluster(dominant_cluster, n_examples)
    true_positive_examples = _build_true_positive_examples(sampled_documents, predictions, n_examples)
    verified_examples = _build_verified_examples(sampled_documents, predictions, n_examples)

    prompts = {
        "infer_discrepancy_patterns": render_prompt(
        "infer_discrepancy_patterns",
        entity_schema=_entity_schema_text(entities),
        discrepant_examples=discrepancy_examples,
        true_positive_examples=true_positive_examples,
    ),
    }
    discrepancy_insight = provider.complete(
        "infer_discrepancy_patterns",
        prompts["infer_discrepancy_patterns"],
    )

    discrepancy_pattern = dominant_cluster.key
    if discrepancy_insight.strip():
        discrepancy_pattern += f"\n\n**INFERRED PATTERNS:**\n{discrepancy_insight}"

    prompts["generate_moderation_principle"] = render_prompt(
        "generate_moderation_principle",
        entity_schema=_entity_schema_text(entities),
        discrepancy_pattern=discrepancy_pattern,
        discrepant_examples=discrepancy_examples,
    )
    moderation_principle = provider.complete(
        "generate_moderation_principle",
        prompts["generate_moderation_principle"],
    )

    prompts["refine_guidelines"] = render_prompt(
        "refine_guidelines",
        guidelines=current_guidelines or "(no guidelines provided)",
        new_principles=moderation_principle,
        verified_examples=verified_examples,
    )
    refined_guidelines = provider.complete("refine_guidelines", prompts["refine_guidelines"])
    return refined_guidelines, discrepancy_insight, moderation_principle, prompts


def run_iterative_refinement(
    sampled_documents: list[SampledDocument],
    guidelines: str,
    entities: list[EntityDefinition],
    provider,
    *,
    instructions: str = "",
    threshold_f1: float = 0.9,
    n_examples: int = 5,
    output_configuration: OutputConfiguration | None = None,
    evaluation_options: PubAnnotationEvaluatorOptions | None = None,
    on_iteration: Callable[[IterationSnapshot], None] | None = None,
) -> IterativeRefinementResult:
    """Refine the guidelines against the sampled documents until the stopping rule fires.

    ``on_iteration`` is invoked with each snapshot as soon as that iteration
    completes, so a caller can persist progress instead of losing everything if
    a later iteration fails. Omitted, behaviour is unchanged.
    """
    n_examples = max(1, n_examples)
    output_configuration = output_configuration or OutputConfiguration(
        include_rationale=True,
        include_guideline_section=True,
    )
    evaluation_options = evaluation_options or PubAnnotationEvaluatorOptions()

    initial_predictions = _annotate_documents(
        sampled_documents,
        guidelines,
        entities,
        provider,
        instructions,
        output_configuration,
    )
    current_guidelines = guidelines
    current_predictions = initial_predictions
    initial_diagnostics = build_pubannotation_diagnostics(
        _build_pairs(sampled_documents, initial_predictions),
        evaluation_options,
    )
    initial_summary = _summarize_moderation_pairs(
        _build_pairs(sampled_documents, initial_predictions),
        threshold_f1,
    )
    current_diagnostics = initial_diagnostics
    current_summary = initial_summary
    iterations: list[IterationSnapshot] = []

    stop_reason = "no_improvement"
    threshold_reached = current_summary.is_good_enough
    if threshold_reached:
        stop_reason = "threshold_reached_before_refinement"

    for iteration in range(1, SAFE_MAX_ITERATIONS + 1):
        if threshold_reached:
            break

        diagnostics_before = current_diagnostics
        evaluation_before = diagnostics_before.overall
        summary_before = current_summary
        guidelines_before = current_guidelines

        refined_guidelines, discrepancy_insight, moderation_principle, prompts = _refine_guidelines_from_pairs(
            sampled_documents=sampled_documents,
            predictions=current_predictions,
            current_guidelines=current_guidelines,
            entities=entities,
            summary=current_summary,
            provider=provider,
            n_examples=n_examples,
        )

        refined_predictions = _annotate_documents(
            sampled_documents,
            refined_guidelines,
            entities,
            provider,
            instructions,
            output_configuration,
        )
        refined_pairs = _build_pairs(sampled_documents, refined_predictions)
        refined_diagnostics = build_pubannotation_diagnostics(refined_pairs, evaluation_options)
        refined_summary = _summarize_moderation_pairs(refined_pairs, threshold_f1)

        improved = refined_summary.overall_f1 > summary_before.overall_f1
        reverted = not improved

        if improved:
            guidelines_after = refined_guidelines
            evaluation_after = refined_diagnostics.overall
            diagnostics_after = refined_diagnostics
            summary_after = refined_summary
            current_guidelines = refined_guidelines
            current_predictions = refined_predictions
            current_diagnostics = refined_diagnostics
            current_summary = refined_summary
        else:
            guidelines_after = current_guidelines
            evaluation_after = diagnostics_before.overall
            diagnostics_after = diagnostics_before
            summary_after = summary_before

        snapshot = IterationSnapshot(
            iteration=iteration,
            guidelines_before=guidelines_before,
            guidelines_after=guidelines_after,
            evaluation_before=evaluation_before,
            evaluation_after=evaluation_after,
            diagnostics_before=diagnostics_before,
            diagnostics_after=diagnostics_after,
            summary_before=summary_before,
            summary_after=summary_after,
            discrepancy_insight=discrepancy_insight,
            moderation_principle=moderation_principle,
            prompts=prompts,
            improved=improved,
            reverted=reverted,
            guidelines_candidate=refined_guidelines,
            summary_candidate=refined_summary,
            diagnostics_candidate=refined_diagnostics,
        )
        iterations.append(snapshot)
        if on_iteration:
            on_iteration(snapshot)

        threshold_reached = current_summary.is_good_enough
        if threshold_reached:
            stop_reason = "threshold_reached"
            break
        if reverted:
            stop_reason = "no_improvement"
            break
    else:
        stop_reason = "safety_cap_reached"

    return IterativeRefinementResult(
        sampled_documents=[document.filename for document in sampled_documents],
        sampled_sourceids=[document.sourceid for document in sampled_documents],
        initial_guidelines=guidelines,
        final_guidelines=current_guidelines,
        initial_evaluation=initial_diagnostics.overall,
        final_evaluation=current_diagnostics.overall,
        initial_diagnostics=initial_diagnostics,
        final_diagnostics=current_diagnostics,
        initial_summary=initial_summary,
        final_summary=current_summary,
        iterations=iterations,
        stop_reason=stop_reason,
        threshold_reached=threshold_reached,
        valid_threshold=threshold_f1,
    )
