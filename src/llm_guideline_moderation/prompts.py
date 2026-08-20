PROMPT_TEMPLATES = {
    "annotate_with_guidelines": """
{system_instruction}

**ENTITY SCHEMA:**
{entity_schema}

**HIGH-LEVEL INSTRUCTIONS:**
{instructions}

**ANNOTATION RULES:**
- Output MUST be a valid JSON object with a single key "annotations".
- "annotations" MUST be an array of objects following this JSON schema:
  {json_schema}
- {rationale_instruction}
- If no entities are found, return {{"annotations": []}}
- Spans must match the original text exactly. Do not alter spacing, casing, or punctuation.

**ANNOTATION GUIDELINES:**
{guidelines}

**TEXT TO ANNOTATE:**
---
{input_text}
---

Provide your response as a single JSON object.
""".strip(),
    "moderate_annotations": """
You are an AI quality control specialist for text annotation.
Your single source of truth is the "ENHANCED AI GUIDELINES".
Your goal is to review the "INITIAL ANNOTATIONS" and the "ORIGINAL TEXT", and produce a final, corrected set of annotations that perfectly aligns with the guidelines.
Perform compliance, completeness, and precision checks, and resolve any disagreements by prioritizing the intent of the "ENHANCED AI GUIDELINES". When adding or removing annotations, explicitly justify the decision and reference the relevant section.

**REFERENCE SAMPLES (Follow priority: Primary Gold -> Initial Annotations Sample -> Additional Gold Context):**
- Start by comparing the Primary Gold Sample to the Initial Annotations Sample and correct discrepancies.
- Use Additional Gold Samples only as contextual guidance after aligning with the primary gold sample.
{formatted_samples}

**Output Format:**
- Your final output MUST be a valid JSON object with the keys "annotations" and "changes".
- The value of "annotations" must be an array of objects using this schema:
  {json_schema}
- {rationale_instruction}
- The value of "changes" must be an array of objects: {{"action": string, "reason": string, "guideline_section": string}} describing each addition, removal, merge, or other adjustment in a brief, machine-readable audit trail that ties back to the guidelines.
- If no entities in the text meet the criteria, return an empty array for "annotations" and a "changes" array that explains why nothing was annotated.

---
**ENHANCED AI GUIDELINES:**
{enhanced_guidelines}
---
**ORIGINAL TEXT:**
{input_text}
---
**INITIAL ANNOTATIONS TO REVIEW:**
{initial_annotations}
---

**FINAL CORRECTED JSON OUTPUT:**
""".strip(),
    "generate_moderation_principle": """
You are an expert "AI Moderator" for an annotation task.
Your goal is to formulate **ONE Core Moderation Principle** based on the provided Linguistic Analysis of a single dominant error pattern.

**ENTITY DEFINITIONS:**
{entity_schema}

**LINGUISTIC ANALYSIS (The Problem):**
{discrepancy_pattern}

**SUPPORTING EXAMPLES (Evidence):**
{discrepant_examples}

**TASK:**
1. Review the **Linguistic Analysis** to understand the root cause.
2. **Synthesize** a **Single General Principle**:
   - **Structure**: IF [Condition] THEN [Action].
   - **Negative Constraint**: Explicitly state when this rule does **NOT** apply.
   - **Generalization**: Phrase the rule using abstract linguistic terms (e.g., "numeric modifiers", "prepositional phrases") rather than specific words, to ensure it applies to unseen data.
3. **Check Validity**: Ensure the principle contradicts neither the Entity Definitions nor the Current Guidelines.
4. Return the output as a Markdown list containing just this **Single General Principle**.
""".strip(),
    "refine_guidelines": """
You are an expert AI Moderator.

**GOAL:**
Update the official Annotation Guidelines to incorporate new "Moderation Principles" discovered from error analysis.

**CURRENT GUIDELINES:**
{guidelines}

**NEW MODERATION PRINCIPLES:**
{new_principles}

**CONSTRAINT: DO NOT BREAK THESE EXAMPLES:**
The following examples are currently handled CORRECTLY. Your new guidelines MUST NOT cause these to be annotated incorrectly.
{verified_examples}

**INSTRUCTIONS:**
1. Read the Current Guidelines and the New Principles.
2. Integrate the New Principles into the Guidelines naturally.
   - Do NOT just append them at the end unless it makes sense.
   - If an existing rule contradicts the new principle, update it.
   - **Conflict Resolution**: If the new principle necessitates changing an existing rule, explicitly justify (in your internal thought process) why the new rule is superior (e.g., more specific, resolves an ambiguity).
   - If the new principle clarifies a specific section, add it there.
3. **CONSTRAINT CHECK**:
   - Review the "CONSTRAINT" examples above.
   - Ensure your changes strictly support the New Principles WITHOUT invalidating the "CONSTRAINT" examples.
   - If a trade-off is required, prioritize specific sub-cases to avoid regression.
4. Maintain the original formatting and structure.
5. Return the FULL updated Guidelines text.
6. **CRITICAL INSTRUCTION**: Models often try to summarize or use placeholders like "(...)" to save tokens. **DO NOT DO THIS.** YOU MUST OUTPUT THE COMPLETED DOCUMENT IN FULL. If you leave out any section, the file will be corrupted.
7. Output ONLY the guideline text. Do not start with "Here are the updated guidelines:".
""".strip(),
    "infer_discrepancy_patterns": """
You are an expert Computational Linguist.
Your goal is to analyze **ONE Dominant Discrepancy Case** (a specific recurring error type) to find the underlying linguistic cause.

**FOCUS:** You are analyzing ONLY the discrepancy type described below. Do not analyze other random errors.

**ENTITY SCHEMA:**
{entity_schema}

**INPUT DATA:**
1. **Discrepancies (The Problem)**: Examples of the specific error type we are solving.
2. **True Positives (The Control)**: Correct examples where the model worked (for contrast).

---
**1. DISCREPANCIES TO ANALYZE:**
{discrepant_examples}

**2. TRUE POSITIVE EXAMPLES (For Contrast):**
{true_positive_examples}
---

**TASK:**
Step 1: **Deep Dive Analysis (Chain-of-Thought)**.
- **Contrast**: Explicitly compare the "Discrepancy" cases against the "True Positives". Identify the *single* boolean feature (syntactic, positional, or semantic) that separates them.
- **Isolate Trigger**: What specific word, phrase, or structure misled the model?
- **Hypothesis Check**: Does this trigger explain ALL the discrepancy examples? If not, refine the pattern.

Step 2: **Formulate Pattern**.
- Define the specific linguistic pattern that triggers this confusion.

**OUTPUT FORMAT:**
Return a **Markdown List** with exactly ONE "Pattern Insight" that explains this specific discrepancy cluster.
- **Pattern Name**: Short descriptive title.
- **Confusion Trigger**: The specific linguistic feature causing the error (e.g., "Nouns acting as adjectives").
- **Contrastive Evidence**: Briefly explain how the "True Positive" cases avoid this trigger.
- **Linguistic Rule (Proposed)**: The precise logic needed to distinguish this case correctly.
""".strip(),
}


def render_prompt(template_name: str, **kwargs: str) -> str:
    try:
        template = PROMPT_TEMPLATES[template_name]
    except KeyError as exc:
        raise ValueError(f"Unknown prompt template: {template_name}") from exc
    return template.format(**kwargs)
