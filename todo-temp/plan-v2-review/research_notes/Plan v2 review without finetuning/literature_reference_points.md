# Published reference points for NCBI Disease NER that the thesis can cite instead of training a fine-tuned model

Scope note (read first). The thesis setting, as given by the coordinator: GPT-5.4 refines a guideline from 10 gold training documents; evaluation on the 100 official development documents (791 mentions); strict span and type matching over four subtypes (best single runs about 0.80 F1) plus a single-type exact-span score (about 0.85 F1). Almost every published number below differs from this on at least one of: split (official test set, not dev), label scheme (one Disease type, not four subtypes), unit of training data (sentences, not documents), matching rule (often token-level BIO spans after preprocessing, sometimes unstated), and preprocessing version (BLURB, Crichton et al. 2017, or Wang et al. 2018 versions). Each finding states these attributes. "Not stated" means I searched the extracted text and did not find it. Numbers marked "unverified" were seen only in a search snippet or secondary source.

## Q1. Low-resource supervised results and learning curves on NCBI Disease

### Takeaway
Published learning-curve points exist only for sentence-sampled, single-type NCBI Disease, mostly on the test set: fine-tuned BERT-family encoders reach about 0.61 to 0.76 F1 with 25 to 100 sentences, about 0.77 to 0.81 with 500 to 1,000 sentences (dev set), and, for BioBERT and SciBERT, about 0.81 to 0.86 with 626 to 1,171 sentences (10% to 20% of training, test set; general-domain BERT-base is lower, 0.73 to 0.80). No paper found samples whole documents, uses the dev split for the main score, or scores the four subtypes.

### Cited Findings

**Gutiérrez et al. 2022, "Thinking about GPT-3 In-Context Learning for Biomedical IE? Think Again" (Findings of EMNLP 2022; venue not re-checked), Table 2 and Table 10** (Source: [arXiv 2203.08410v2 PDF](https://arxiv.org/pdf/2203.08410v2))
- Data: BLURB versions of the datasets, used "exactly as they are used in the BLURB benchmark"; NCBI-Disease is single type; metric column says "F1 entity-level" (Table 1). Matching beyond "entity-level" is not stated.
- Training size: 100 training examples (BLURB instances, which are sentences; prompts say "List the diseases mentioned in the following sentences"). "True few-shot" protocol: prompt and hyperparameter choices made by cross-validation on the same 100 examples, no large validation set.
- Seeds/runs: "3 different 100-example training sets", mean and standard deviation reported.
- Test: "at most 1,000 test examples from each dataset", same subset for all methods. (BLURB NCBI test has 940 sentences per Chen et al. 2025 and Jahan et al. 2024, so this cap likely covers the full NCBI test set; this is my inference.)
- NCBI-Disease P / R / F1 (mean, SD in parentheses; I decoded the subscripts from PDF text extraction and checked the row assignment by recomputing the printed NER average for PubMedBERT, 68.2):
  - PubMedBERT-base: 68.5 (4.7) / 67.6 (2.4) / **68.0 (2.9)**
  - BioBERT-large: 59.6 (10.6) / 67.0 (6.1) / 63.0 (8.7)
  - RoBERTa-large: 64.3 (3.7) / 68.7 (6.7) / 66.4 (5.1)
  - BioBERT-base (Table 10): 58.8 (5.4) / 65.9 (2.7) / 62.1 (4.0)
  - RoBERTa-base (Table 10): 60.6 (3.2) / 61.9 (4.6) / 61.2 (3.5)
  - GPT-3 davinci in-context, kNN-retrieved demonstrations from the same 100 examples, up to 10 in-context examples: 55.2 (6.7) / 49.0 (6.1) / **51.4 (1.4)**
- Their data-efficiency curve (200 and 500 examples) is shown only for BC5CDR-disease (Figure 3), not NCBI.

**Su, Chen, Peng, Sun 2024, "Demonstration-based learning for few-shot biomedical NER under machine reading comprehension" (J Biomed Inform 2024 per search; I read only arXiv v2), Table 2** (Source: [arXiv 2308.06454v2](https://arxiv.org/html/2308.06454v2); abstract numbers also in [arXiv PDF listing](https://arxiv.org/pdf/2308.06454))
- Shot definition: "25 and 50 unique sentences" drawn as training sets; each run also uses a 100-sentence dev set (Dev100) and the original test set.
- Seeds: five random seeds, mean and SD reported.
- Metric: F1 from TP/FP/FN; strictness not stated. Single Disease type.
- NCBI-Disease F1, 25-shot / 50-shot: BERT-CRF vanilla 61.2 (4.6) / 71.7 (0.9); BERT-CRF popular 65.9 (4.2) / 73.0 (1.0); BERT-CRF grape 64.6 (1.8) / 72.7 (2.8); BERT-MRC popular 71.2 (0.8) / 75.8 (2.1); BERT-MRC grape 70.1 (1.5) / 75.6 (2.7).
- Internal inconsistency: the body text gives 85.4% for BERT-MRC grape at 50-shot on NCBI, while Table 2 gives 75.6; the "fully supervised" sentence (79.2% for NCBI) is also ambiguous. The abstract's NCBI numbers (70.1 at 25-shot, 75.6 at 50-shot) match Table 2.

**Gutiérrez, Sun, Su 2023, "Biomedical Language Models are Robust to Sub-optimal Tokenization" (BioNLP 2023; venue not re-checked), Tables 7 and 8** (Source: [arXiv 2306.17649 PDF](https://arxiv.org/pdf/2306.17649))
- Data: BLURB NER datasets (single type). Metric: entity-level F1.
- Low-resource (Table 8): 500 and 1,000 training examples; **results on the development set only** ("We report results on the development set only for our low-resource NER experiments"). Number of runs for this table not stated.
  - NCBI-Disease, PubMedBERT (their replica): **77.2 (500) / 81.2 (1,000)**; BioVocabBERT: 77.7 / 80.6.
- Fully supervised, test set, 3 runs (Table 7): originally reported PubMedBERT 87.8; their PubMedBERT replica 87.1 (0.8); BioVocabBERT 86.7 (0.4). Row assignment checked against the text ("BioVocab underperforms on NCBI-Disease").

**Yu, Mao, Chi, Wei, Huang 2021, "A Robust and Domain-Adaptive Approach for Low-Resource Named Entity Recognition" (RDANER; arXiv v1, venue not checked), Tables II, III, V** (Source: [arXiv 2101.00388 PDF](https://arxiv.org/pdf/2101.00388))
- Sampling: random subsets of training data at 10%, 20%, 30%, 50%, 100%. NCBI-Disease sentence counts (Table II): 626 / 1,171 / 1,737 / 2,943 / 5,825 sentences. Note 5,825 differs from BLURB's 5,424 training sentences, so the preprocessing version differs.
- Split and runs: Table III is "test set evaluation", "mean across five different runs with different random seeds". Table V settings are not restated; I assume the same but this is not explicit.
- Metric: "micro-averaged F1"; exact or partial matching not stated. Single type. CRF layer on all BERT variants.
- NCBI-Disease F1 at 10 / 20 / 30 / 50 / 100%:
  - BERT-base: 73.03 / 79.56 / 83.79 / 84.88 / 86.37 (Table III)
  - BERT further pretrained on 200k PubMed abstracts ("LM fine-tuning"): 76.09 / 80.20 / 84.37 / 85.70 / 87.49 (Table III)
  - RDANER (bootstrapping): 78.14 / 83.46 / 85.46 / 86.80 / 87.89 (Table III)
  - SciBERT: 80.82 / 83.69 / 86.35 / 87.37 / 88.57 (Table V)
  - **BioBERT: 81.08 / 85.82 / 87.02 / 88.53 / 89.36** (Table V)
- Row mapping checked: the RDANER column in Table V equals the NCBI rows of Table III.

**Chen, Su, Sun 2025, "Harnessing Large Language Models for Biomedical Named Entity Recognition" (BioSelectTune; arXiv preprint, Dec 2025)** (Source: [arXiv 2512.22738v1](https://arxiv.org/html/2512.22738v1))
- Fine-tuned Qwen3-8B on NCBI-Disease, Table 1 headed "F1-Score with Strict Match (%)": full-data SFT baseline 86.78; 50% of "curated positive data" 88.29; text also gives 82.06 at 25%. The subset is selected by a filtering method, not random, and counts are fractions of curated positive data, so this is not a clean learning curve. Split not stated in the fetched text.

**NEEDLE (Jiang et al. 2021)** (Source: [arXiv 2106.08977 PDF](https://arxiv.org/pdf/2106.08977))
- The "Size of Strongly Labeled Data" experiment (Figure 3, Table 8) is run only on E-commerce query NER (1%, 10%, 20%, 50%), not on NCBI Disease.

**Sachan et al. 2018, "Effective Use of Bidirectional Language Modeling for Transfer Learning in Biomedical NER" (PMLR 85, MLHC 2018), Section 4.3.3 and Figure 8a** (Source: [arXiv 1711.07908 PDF](https://arxiv.org/pdf/1711.07908))
- Plots F1 against number of training examples (x-axis 0 to 4,000) on NCBI-disease for BiLM pretraining vs no pretraining. Values appear only in the figure; the text gives no numbers.

**Classic full-training baselines (single type, document-level training)**
- BANNER trained on the 593 training abstracts, categories flattened: F 0.819 on the development set and 0.818 on the test set; 0.845 in 10-fold cross-validation on the training set (Source: [Doğan and Lu 2012, BioNLP, W12-2411](https://aclanthology.org/W12-2411.pdf), Section 3.5). Matching rule not stated.
- BANNER trained on the 593 gold training abstracts: F 0.785 (P 0.808, R 0.764) on the 100-abstract test set; trained instead on crowd annotations of 589 abstracts: F 0.739 (Source: [Good et al. 2015, PSB, arXiv 1408.1928](https://arxiv.org/pdf/1408.1928), Section 3.4).

**Unit conversion facts (reported counts)**
- NCBI corpus: 793 citations, 6,651 sentences (Source: [Doğan and Lu 2012, Table 3](https://aclanthology.org/W12-2411.pdf)).
- BLURB/standard sentence split: 5,424 train / 923 dev / 940 test sentences (Source: [Jahan et al. 2024, Table 1](https://arxiv.org/html/2310.04270v3); same counts in [Zhao and Goto 2025, Table 1](https://arxiv.org/html/2503.03261v2) and [Hou et al. 2025](https://arxiv.org/pdf/2509.04462)).

### Inferences
- Derived arithmetic, not a reported number: 5,424 training sentences over 593 training abstracts is about 9.1 sentences per abstract (assuming the BLURB training split is the 593 official training abstracts); 6,651 / 793 is about 8.4. So the thesis's 10 gold documents are on the order of 85 to 95 sentences, close to Gutiérrez et al.'s 100-sentence setting (PubMedBERT 68.0 F1, test). A random 100-sentence sample is spread over many documents and is not the same as 10 whole documents.
- The thesis's about 0.85 single-type exact-span F1 falls in the range that published supervised encoders reach with roughly 1,000 to 1,200 training sentences: PubMedBERT 81.2 at 1,000 sentences (dev), BioBERT 85.82 and SciBERT 83.69 at 1,171 sentences (20%, test, 5 seeds). By the derived ratio above, 1,000 to 1,200 sentences is on the order of 110 to 130 abstracts. A defensible wording is "comparable to published single-type supervised encoders trained on roughly one fifth of the NCBI training split (about 1,000 to 1,200 sentences)", with the caveats that (a) the thesis score is on the dev split, (b) the published curves sample sentences, (c) the thesis model also receives the expert guideline, which is a large additional source of supervision, and (d) RDANER does not state its matching rule.
- Dev vs test difficulty: the one model reported on both official splits (BANNER, 0.819 dev vs 0.818 test) suggests the two splits are similarly hard for a supervised tagger. This is a single data point and does not prove equivalence for LLMs.
- For the four-subtype strict score (about 0.80) there is no supervised learning-curve comparator at all (see Q5).

### Gaps
- No published learning curve on NCBI Disease that samples whole documents (for example 10, 50, 100, 200 abstracts) was found.
- No learning curve evaluated on the official dev split with the full curve; Gutiérrez et al. 2023 uses dev but only at 500 and 1,000.
- Su et al. 2024: encoder checkpoint names and strictness not confirmed; JBI version not checked against arXiv v2.
- RDANER Table V seeds and split not restated explicitly; venue not verified.
- Sachan et al. 2018 Figure 8a values not readable as text.
- Moradi et al. 2021 ("GPT-3 Models are Poor Few-Shot Learners in the Biomedical Domain", [arXiv 2109.02555](https://arxiv.org/pdf/2109.02555)): my text extraction found no NCBI or NER evaluation, so it is not a source for NCBI numbers.
- Košprdić et al. ([arXiv 2305.04928](https://arxiv.org/abs/2305.04928)) report averaged zero/few-shot results over nine entity types; NCBI-specific numbers not verified, and NCBI Disease appears among its training datasets per the model card in search results.

## Q2. LLM results on NCBI Disease

### Takeaway
On the single-type NCBI test set with exact-match F1, prompted frontier LLMs without task-specific supervision score about 0.58 to 0.69 (GPT-4 zero/few-shot 0.58 to 0.64, GPT-5 five-shot 0.691), and guideline-augmented GPT-4o reaches 0.810. Fine-tuned LLMs reach 0.84 to 0.91. Only two published LLM studies besides the base paper use the four subtypes (Kim et al. 2025 case study; Ge et al. 2025), and both score well below 0.80.

### Cited Findings

**Chen et al. 2025, "Benchmarking large language models for biomedical natural language processing applications and recommendations", Nature Communications (DOI 10.1038/s41467-025-56989-2)** (Sources: [PMC11972378](https://pmc.ncbi.nlm.nih.gov/articles/PMC11972378/); [arXiv 2305.16326 PDF](https://arxiv.org/pdf/2305.16326))
- Results table: Table 3 in the arXiv PDF (the PMC fetch labeled it Table 2; check numbering against the journal PDF before citing a table number).
- Split: full test set ("We benchmarked the models on the full testing sets"); NCBI-disease 5,424 / 923 / 940 sentences; error analysis counts 960 gold entities.
- Metric: "exact match (that is, the predicted tokens must have the same text spans as the gold standard) F1-score"; entity-level. Single Disease type.
- Decoding: temperature 0; static one- and five-shot examples randomly selected from the training set; no seeds reported; significance via bootstrapped Wilcoxon test.
- NCBI Disease entity F1 (column order verified from the arXiv table header):
  - SOTA before LLMs: 0.9090, cited to Zhang et al. 2022 (BINDER, PubMedBERT encoder)
  - Zero-shot: GPT-3.5 0.4060; GPT-4 0.5827; LLaMA 2 13B 0.2211
  - One-shot: GPT-3.5 0.4817; GPT-4 0.5988; LLaMA 2 13B 0.3811
  - Five-shot: GPT-3.5 0.4309; **GPT-4 0.6389**; LLaMA 2 13B 0.4847
  - Fine-tuned on full training set: **LLaMA 2 13B 0.8682**; PMC LLaMA 13B 0.8353
- Error analysis: LLMs predict "up to 512 entities correctly out of 960"; a public fine-tuned BioBERT (HF ugaray96/biobert_ncbi_disease_ner) scores entity-level F1 0.8920 with 863 of 960 correct, and 269 boundary issues.

**Hou, Zhan, Zeng, Wu, Zhou, Zhang 2025, "Benchmarking GPT-5 for biomedical natural language processing" (arXiv 2509.04462, Sept 2025)** (Source: [arXiv 2509.04462 PDF](https://arxiv.org/pdf/2509.04462))
- Same prompt templates, decoding parameters, and dataset partitions as Chen et al. (GPT-4 and GPT-3.5 rows copied from Chen et al.). NCBI-disease split 5,424 / 923 / 940. Metric: "exact match F1-score ... This strict F1 metric requires the model to produce entity names exactly as they appear in text". Single type. Core tasks run through the batch API.
- Text result: "On NCBI-Disease, however, GPT-5 reached only **0.691 in five-shot**, which is still more than twenty points lower than SOTA (0.909)."
- GPT-5 zero/one-shot and GPT-4o NCBI values are shown only in Figure 1 (not in extractable text). Reasoning-effort setting for GPT-5 not stated in the text I read.

**Zhao and Goto 2025, "Can Frontier LLMs Replace Annotators in Biomedical Text Mining? Analyzing Challenges and Exploring Solutions" (arXiv 2503.03261v2, May 2025)** (Source: [arXiv 2503.03261v2](https://arxiv.org/html/2503.03261v2))
- GPT-4o (2024-08-06), NCBI-Disease split 5,424 / 923 / 940, single Disease type; test set appears used in full (sampling mentioned only for LitCovid). Matching rule not specified in the fetched text.
- Table 4 P / R / F1: basic instruction 0.710 / 0.645 / 0.676; dynamic 3-shot 0.700 / 0.690 / 0.695; dynamic 3-shot plus instruction retrieval from the annotation guideline 0.803 / 0.734 / 0.767; two-step inference 0.771 / 0.744 / 0.757; **two-step inference plus guideline retrieval 0.843 / 0.780 / 0.810**; baseline labeled "SOTA foundation model" 0.882 / 0.912 / 0.897 (Table 1 names BioBERT-Large v1.2 for NCBI).
- This is the closest published analog to guideline-prompted LLM annotation on single-type NCBI.

**Jahan, Laskar, Peng, Huang 2024, "A Comprehensive Evaluation of Large Language Models on Benchmark Biomedical Text Processing Tasks" (Computers in Biology and Medicine per search; read arXiv v3)** (Source: [arXiv 2310.04270v3](https://arxiv.org/html/2310.04270v3))
- Zero-shot, BIO token-tagging prompt (one token per line), single Disease type; split listed as 5,424 / 923 / 940 but the evaluated split and strictness are not stated; outputs parsed by script plus human review.
- Table 9 P / R / F1: GPT-3.5 24.76 / 51.25 / 33.39; PaLM-2 25.10 / 41.04 / 31.15; Claude-2 39.33 / 54.69 / 45.75; LLaMA-2-13b 2.56 / 21.67 / 4.58; SOTA (BioBERT) 88.22 / 91.25 / 89.71. Table 16: Claude-2 1-shot F1 44.57, 3-shot 41.47.

**Monajatipoor et al. 2024, "LLMs in Biomedicine: A study on clinical Named Entity Recognition" (arXiv 2404.07376v1, preprint)** (Source: [arXiv 2404.07376v1](https://arxiv.org/html/2404.07376v1))
- NCBI-disease, single type; metric only "F1", no matching rule, split size not given.
- 16-shot: GPT-4 random demonstrations 70.0; GPT-4 with KATE nearest-neighbor demonstration retrieval 86.5 to 88.3 (best 88.3 with BioClinicalRoBERTa); GPT-3.5 KATE 76.1 to 78.8. Llama2-7B LoRA fine-tuned 91.3. Zero-shot: GPT-4 61.64 (62.17 with DiRAG); GPT-3.5 38.1 (45.0 with DiRAG); cited UniversalNER zero-shot 61.4.

**Ge, Das, Guo, Sarker 2025, "Retrieval augmented generation based dynamic prompting for few-shot biomedical NER using LLMs" (arXiv 2508.06504v1; Research Square preprint PMC12408026)** (Sources: [arXiv 2508.06504v1](https://arxiv.org/html/2508.06504v1); [PMC12408026](https://pmc.ncbi.nlm.nih.gov/articles/PMC12408026))
- Uses the **four NCBI subtypes** as labels (Appendix C prompt; Table 3 lists four entity types). Output is token-aligned; span matching rule not described; static and baseline runs averaged over four random runs; test size given as 20.5k tokens.
- Static prompt with all components (5-shot): GPT-3.5 45.24 F1; GPT-4 46.93; Llama 3-70B 34.80.
- Dynamic retrieval prompting, GPT-4: 5-shot TF-IDF 60.08; 10-shot TF-IDF 62.05; **20-shot TF-IDF 61.80 / 67.13 / 64.36**. Llama 3-70B best 51.35 (10-shot SBERT).
- A peer-reviewed version in npj Artificial Intelligence is mentioned on the PMC page; I did not verify it.

**Kim, Islamaj, Kim, Boudin, Aizawa 2025, "Repurposing Annotation Guidelines to Instruct LLM Annotators: A Case Study" (arXiv 2510.12835v1; public preprint by the base-paper group)** (Source: [arXiv 2510.12835v1 PDF](https://arxiv.org/pdf/2510.12835v1))
- GPT-4o as annotator and moderator, four categories, 5 sample documents per moderation phase, loop threshold 0.8 "motivated by the lowest inter-annotator agreement observed in the NCBI Disease corpus" (no number given). Evaluation set size not stated in the extracted text.
- Table 1, F1 under Strict / Strict without category / Soft / Soft without category: Baseline 0.36 / 0.57 / 0.48 / 0.74; GuidelinePrompt 0.46 / 0.67 / 0.54 / 0.78; Our Method 0.50 / 0.73 / 0.55 / 0.80; Human-in-the-loop 0.58 / 0.71 / 0.62 / 0.78.
- Table 2 per-category strict F1 (Our Method / Human-in-the-loop): SpecificDisease 0.65 / 0.70; DiseaseClass 0.29 / 0.20; Modifier 0.12 / 0.51; CompositeMention 0.24 / 0.07.

**Gutiérrez et al. 2022** (above): GPT-3 davinci in-context with 100-sentence retrieval pool, 51.4 F1 entity-level (Source: [arXiv 2203.08410v2](https://arxiv.org/pdf/2203.08410v2)).

**Fine-tuned LLMs and instruction-tuned models, as listed in Chen, Su, Sun 2025 Table 1 ("Strict Match")**: GPT-4 67.40; Taiyi 73.10; InstructUIE-11B 86.21; UniNER-7B 86.96; BioNER-Llama2-7B 88.00; BioMedBERT 87.82. Whether these were re-run or copied, and the GPT-4 setting, are not stated (Source: [arXiv 2512.22738v1](https://arxiv.org/html/2512.22738v1)).

**Hu et al. 2024 (JAMIA), "Improving large language models for clinical named entity recognition via prompt engineering"**: uses annotation-guideline-based prompts, but on clinical corpora (MTSamples, VAERS), not NCBI. Search summary reports GPT-4 relaxed F1 rising from 0.804 to 0.861 (MTSamples) and 0.593 to 0.736 (VAERS); **unverified**, my PubMed fetch failed (Sources: [PubMed 38281112](https://pubmed.ncbi.nlm.nih.gov/38281112/); [arXiv 2303.16416](https://arxiv.org/html/2303.16416v3)).

### Inferences
- The thesis's about 0.85 single-type exact-span F1 (dev100) is above every published prompted-LLM single-type number I verified on the test set (GPT-4 five-shot 0.6389, GPT-5 five-shot 0.691, GPT-4o plus guideline retrieval 0.810), except Monajatipoor et al.'s retrieval-based 16-shot GPT-4 (88.3), whose matching rule and retrieval pool size are not stated. Split differences (dev vs test) keep this from being a strict ranking.
- Zhao and Goto's 0.810 is the most relevant external LLM comparator: also guideline-driven, also single type, but uses retrieval of demonstrations from the full training set (dynamic 3-shot), so its gold exposure is larger than 10 documents.
- For four-subtype strict scoring, the comparators are the base paper's GPT-5 moderated 0.76 on the same dev100 (Q6), Kim et al. 2025's GPT-4o 0.50 to 0.58 (set size unknown), and Ge et al.'s GPT-4 at most 64.36 (matching rule unclear).
- "Exact match" in Chen et al. and Hou et al. compares predicted strings to gold spans on BLURB sentences; this is close to, but not identical with, character-offset strict matching in PubAnnotation.

### Gaps
- No GPT-5.x or GPT-4o zero-shot NCBI number in readable text (Hou et al. Figure 1 only).
- No o1/o3 NCBI results found.
- Monajatipoor et al.: retrieval pool, split, and matching rule not described.
- Jahan et al.: evaluated split and strictness not stated.
- Hu et al. 2024 numbers unverified in primary text.
- Kim et al. 2025: evaluation set size and venue not confirmed.

## Q3. Human inter-annotator agreement for NCBI Disease

### Takeaway
The often-cited "87.5%" comes from the DNorm paper (Leaman, Islamaj Doğan, Lu 2013), which states "inter-annotator agreement: 87.5%" without saying whether it measures mention spans, span plus category, or concept IDs, or at which phase. The two corpus papers give agreement only in figures: the 2012 paper says span and span-plus-category agreement were "above 80% after phase II", and the 2014 paper reports pairwise F-measure agreement after Phase I for the concept normalization task.

### Cited Findings
- **Doğan and Lu 2012 (BioNLP workshop, "An improved corpus of disease mentions in PubMed citations")** (Source: [ACL Anthology W12-2411](https://aclanthology.org/W12-2411.pdf))
  - Agreement measured "at phase I and II of the annotation process", per annotator pair per shared set, averaged over sets, then mean and SD over all pairs.
  - Two levels: (1) "both annotators tag the same exact phrase based on character indices as a disease mention", (2) the same exact phrase "as a disease mention of the same category". So level 2 is strict span plus subtype.
  - Results are in Figure 3 ("Inter-annotator annotation consistency measured at the span and span-category level"); the only text statement is "both span-consistency measure and span-category consistency measure is above 80% after phase II". Exact values are only in the figure.
  - Agreement between automatic pre-annotation and final annotation: "only 35%".
  - Split counts (Table 4): training 593 abstracts, 5,148 mentions (SpecificDisease 2,959; DiseaseClass 781; Modifier 1,292; CompositeMention 116); **development 100 abstracts, 791 mentions (409 / 127 / 218 / 37)**; test 100 abstracts, 961 mentions (556 / 121 / 264 / 20).
  - Category priority when several fit: "Modifier", "Composite Mention", "Disease Class", "Specific Disease".
- **Doğan, Leaman, Lu 2014 (J Biomed Inform 47:1 to 10, "NCBI disease corpus: a resource for disease name recognition and concept normalization")** (Source: [PMC3951655](https://pmc.ncbi.nlm.nih.gov/articles/PMC3951655/))
  - "We measured the annotators' agreement after Phase I of the annotation process", by "computing the F-measure between each pair of annotators", averaged per document and then per pair.
  - Figure 2 caption: "Inter-annotator annotation agreement for the disease name normalization task. The red dotted line shows the average F-score among all annotator pairs." No numeric value in the text; the abstract says only "a high inter-annotator agreement was observed". It states that mention-level annotation was described in the 2012 paper.
  - Table 2 counts differ slightly from 2012: 5,145 / 787 / 960 mentions (train / dev / test).
- **Leaman, Islamaj Doğan, Lu 2013 (DNorm, Bioinformatics 29(22):2909)**, Section 2 Methods: "Each abstract was annotated by two human annotators for disease mentions, as well as their corresponding concept identifiers in MEDIC (inter-annotator agreement: 87.5%)." No phase, level, or metric given (Source: [Bioinformatics article page](https://academic.oup.com/bioinformatics/article/29/22/2909/316280)).
- The base paper (ACL 2026, Appendix) cites this as "an inter-annotator agreement of approximately 87.5% for disease mention annotation (Leaman et al., 2013)", and separately gives BC5CDR test-set IAA of 87.49% for disease and 96.05% for chemical, and BioRED 97.01% (Sources: [ACL 2026 PDF](https://aclanthology.org/2026.acl-long.1760.pdf); [arXiv 2605.20809v1](https://arxiv.org/html/2605.20809v1)). The BC5CDR figure is from a different corpus; I did not check its primary source.
- **Non-expert crowd reference (not IAA)**: Good et al. 2015 (PSB). Amazon Mechanical Turk workers, 15 per document, majority-vote threshold K=6, compared with NCBI gold on the 593 training documents using strict exact-span matching ("no partial credit for the overlap"), micro-averaged, no category required: **F 0.872 (P 0.862, R 0.883)**. With one worker per document F is 0.78; it plateaus at 0.87 for more than 7 workers. Cost $0.06 per abstract per worker (Source: [arXiv 1408.1928](https://arxiv.org/pdf/1408.1928)).

### Inferences
- The plan's "about 0.875" matches DNorm's 87.5%, but that number does not state whether category agreement was required. Using it as a ceiling for the four-subtype strict score (0.80) or the single-type score (0.85) needs that caveat.
- The corpus papers' agreement figures are pairwise agreement of individual annotators at Phase I (and Phase II in 2012), before the consensus meetings that produced the gold standard. A model compared with consensus gold is therefore being compared with a different target than annotator-vs-annotator agreement.
- The crowd F 0.872 (span only, strict, training split) is a second human reference point for the single-type exact-span score. The thesis's about 0.85 single-type is close to it, but the crowd was scored on the training split and had gold feedback during training.
- The near coincidence of 87.5% (NCBI, via DNorm) and 87.49% (BC5CDR disease) is worth noting so the two are not conflated; I found no evidence linking them.

### Gaps
- The exact Phase I and Phase II values for span and span-category agreement (2012 Figure 3) and the concept-level average (2014 Figure 2) could not be read: they are only in images, and no PDF rendering tool was available.
- I could not determine what DNorm's 87.5% measures.

## Q4. Verification of the SOTA rows (NEEDLE 92.28, BioBERT 89.71) and higher numbers

### Takeaway
Both rows verify. NEEDLE 92.28 is span-level F1 on single-type NCBI-disease (Crichton et al. preprocessing), using weak dictionary labels on large unlabeled PubMed text plus the full gold training set, with final fine-tuning on gold. BioBERT 89.71 is entity-level exact-match F1 on the test set (Wang et al. 2018 preprocessing). Other reported numbers above 89.71: BINDER 90.9 and fine-tuned Llama2-7B 91.3 (preprint, unclear protocol); nothing above 92.28 found.

### Cited Findings
- **NEEDLE (Jiang et al. 2021, "Named Entity Recognition with Small Strongly Labeled and Large Weakly Labeled Data", ACL 2021)** (Source: [arXiv 2106.08977 PDF](https://arxiv.org/pdf/2106.08977))
  - Table 5 (span-level F1): NEEDLE NCBI-disease **92.28**; ablations w/o NAL 92.11, w/o WLC/NAL 91.73, w/o FT 89.14, w/o FT/NAL 88.86; supervised baseline BioBERT-CRF 89.22 (baselines were continually pretrained on the in-domain unlabeled data first, "for fair comparison"); SST 89.42; Mean Teacher 89.77. Reported F1 from Gu et al. 2020: BERT 85.87, BioBERT 89.13, SciBERT 88.25, PubMedBERT 87.82.
  - Table 9 (span P / R / F1): NEEDLE NCBI-disease 91.76 / 92.81 / 92.28.
  - Training: Stage I continual pretraining on in-domain unlabeled data; Stage II noise-aware continual pretraining on strong plus weak labels with weak-label completion; Stage III "final fine-tuning on strongly labeled data". Weak labels: "dictionary lookup and exact string match" over PubMed 2019 baseline titles and abstracts, dictionary of 3,016 chemical and 5,827 disease entities. So yes: weak labels plus the full gold training set.
  - Data: "These datasets only contain a single entity type." "We use the pre-processed data in BIO format from Crichton et al. (2017) following BioBERT and PubMedBERT." Metric: span-level P/R/F1. The test split is implied by the comparison with prior SOTA but not stated in so many words in the text I extracted. Seeds or run counts: not stated.
- **BioBERT (Lee et al. 2020, Bioinformatics 36(4):1234), Table 6** (Source: [Bioinformatics article page](https://academic.oup.com/bioinformatics/article/36/4/1234/5566506))
  - NCBI disease P / R / F: BioBERT v1.1 (+PubMed) **88.22 / 91.25 / 89.71**; BioBERT v1.0 (+PubMed+PMC) 89.04 / 89.69 / 89.36; BERT 84.12 / 87.19 / 85.63; previous SOTA (Xu et al. 2019) 88.30 / 89.00 / 88.60.
  - "All NER evaluations are based on entity-level exact matches." Test set. Seeds not stated. NCBI data is the Wang et al. (2018) preprocessed version, which has fewer annotations because duplicate articles were removed from training.
- **Higher than 89.71**:
  - BINDER (Zhang, Cheng, Gao, Poon 2022, "Optimizing Bi-Encoder for NER via Contrastive Learning", ICLR 2023): 90.9 on NCBI with PubMedBERT; this is the 0.9090 "SOTA" in Chen et al. 2025 and Hou et al. 2025 (Sources: [Chen et al. arXiv PDF, ref 93](https://arxiv.org/pdf/2305.16326); search snippet of [arXiv 2208.14565](https://arxiv.org/pdf/2208.14565)). Not checked in the BINDER primary text.
  - Llama2-7B LoRA fine-tuned 91.3 (Monajatipoor et al. 2024 preprint; matching rule and split not stated) (Source: [arXiv 2404.07376v1](https://arxiv.org/html/2404.07376v1)).
  - BERT-MRC (Sun et al., same group as Su et al.) 90.04 on NCBI-Disease, **unverified** (search snippet only) (Source: [arXiv 2009.01560](https://arxiv.org/pdf/2009.01560)).
  - BioSelectTune-8B 88.29 strict (below BioBERT) (Source: [arXiv 2512.22738v1](https://arxiv.org/html/2512.22738v1)).

### Inferences
- NEEDLE's 92.28 uses far more supervision than the thesis (full gold training split plus millions of weakly labeled PubMed sentences) and a different split (test) and label scheme (single type). It is a context number for task difficulty, as the base paper itself says ("not directly comparable to our setup").
- Different leaderboard rows use different preprocessed versions (Crichton et al. for NEEDLE, Wang et al. for BioBERT, BLURB for PubMedBERT/BINDER/Chen et al.), so small differences among 87.8 to 92.3 are partly version effects.

### Gaps
- NEEDLE run count and explicit test-split wording not found.
- BINDER and BERT-MRC numbers not read in their primary papers.

## Q5. Published results that use the four NCBI subtypes

### Takeaway
I found no published supervised (fine-tuned) result that scores NCBI Disease's four subtypes; all standard supervised benchmarks collapse them to one Disease type. Four-subtype results exist only in LLM work: the base paper (2026), its predecessor case study (Kim et al. 2025), and Ge et al. 2025.

### Cited Findings
- The corpus authors themselves flattened the categories for the BANNER experiments: "the different disease category annotations present in the NCBI corpus were flattened into only one single category", for AZDC compatibility (Source: [Doğan and Lu 2012](https://aclanthology.org/W12-2411.pdf), Section 2.6).
- Supervised benchmark versions are single type: NEEDLE ("These datasets only contain a single entity type") (Source: [arXiv 2106.08977](https://arxiv.org/pdf/2106.08977)); Jahan et al. list NCBI as "NER (DISEASE)" (Source: [arXiv 2310.04270v3](https://arxiv.org/html/2310.04270v3)); RDANER says "there is only 1 type of entity" on NCBI-Disease (Source: [arXiv 2101.00388](https://arxiv.org/pdf/2101.00388)).
- Four-subtype LLM results:
  - Base paper, GPT-5 moderated 0.82 / 0.71 / 0.76 strict span and type on dev100 (Q6) (Source: [ACL 2026 PDF](https://aclanthology.org/2026.acl-long.1760.pdf)).
  - Kim et al. 2025, GPT-4o, strict F1 0.36 to 0.58 overall, with per-category tables (Q2) (Source: [arXiv 2510.12835v1](https://arxiv.org/pdf/2510.12835v1)).
  - Ge et al. 2025, four-subtype labels in prompts, aggregate F1 only, GPT-4 best 64.36; matching rule not described; no per-subtype scores (Source: [arXiv 2508.06504v1](https://arxiv.org/html/2508.06504v1)).
- Per-type PubAnnotation evaluation pages for "ncbi-valid" projects appear in search results; these are the base-paper or thesis runs, not independent studies (Source: [PubAnnotation evaluation 507](https://pubannotation.org/projects/ncbi-valid-gemini-r-m/evaluations/507)).

### Inferences
- The thesis's four-subtype strict 0.80 can be compared directly only with the base paper's 0.76 (same dev100, same scheme, same matching). Against supervised models there is no published four-subtype number, so any "comparable to supervised" statement must use the single-type 0.85 score.
- Human span-plus-category agreement exists (Doğan and Lu 2012 level 2) but only as a figure, "above 80% after phase II".

### Gaps
- My searches were limited to the web search tool; a full-text search of PubMed Central or Semantic Scholar for subtype-level supervised results was not done. "None found" is not proof that none exist.

## Q6. Base paper (arXiv 2605.20809; ACL 2026 long paper 1760)

### Takeaway
Confirmed: NCBI evaluation uses the full official development split (100 documents, 791 mentions, four subtypes), strict span-and-type matching, 10 moderation documents randomly sampled from the training split, and GPT-5 moderated P/R/F1 0.82 / 0.71 / 0.76. The paper reports no fine-tuned comparison and no learning curve; it names a learning curve over development-data volume as future work.

### Cited Findings
- Title "Refining and Reusing Annotation Guidelines for LLM Annotation"; Kon Woo Kim, Jin-Dong Kim, Akiko Aizawa; arXiv v1 20 May 2026 (Sources: [arXiv abstract](https://arxiv.org/abs/2605.20809); [ACL 2026 PDF](https://aclanthology.org/2026.acl-long.1760.pdf)).
- Section 4.2: "For NCBI Disease and BioRED, we used their respective development splits in full, as both contain exactly 100 documents. For BC5CDR ... we randomly sampled 100." "We intentionally withheld the original test sets." "We randomly sampled 10 documents from the original training split of each benchmark to serve as the development dataset for iterative moderation."
- Appendix Table 5, NCBI evaluation set: CompositeMention 37, DiseaseClass 127, Modifier 218, SpecificDisease 409, total 791 (identical to Doğan and Lu 2012 Table 4 dev counts) (Source: [arXiv 2605.20809v1](https://arxiv.org/html/2605.20809v1)).
- Matching: results under strict span-and-type matching; soft matching (at least one character overlap) used only for discrepancy categorization.
- Table 1, NCBI (791), P / R / F1 (TP):
  - GPT-5: S (prompt only) 0.45 / 0.48 / 0.46 (378); G (original guidelines) 0.78 / 0.68 / 0.73 (540); **M (moderated) 0.82 / 0.71 / 0.76 (565)**; #Iters 3.
  - Gemini: 0.36 / 0.47 / 0.40; 0.69 / 0.57 / 0.63; 0.72 / 0.61 / 0.66; #Iters 5.
  - DeepSeek: 0.32 / 0.30 / 0.31; 0.72 / 0.45 / 0.55; 0.71 / 0.47 / 0.56; #Iters 2.
- Table 6 (one-sided tests, M > G, NCBI GPT): 0.7264 to 0.7588, delta +0.0323, bootstrap p 0.0762, approximate randomization p 0.0859 (not significant at 0.05).
- Inconsistency: Table 1 lists 3 iterations for GPT on NCBI, while Section 5.4 says it "concluded after four iterations".
- Reference numbers: "prior work reports official-test performance of 92.28 F1 on NCBI Disease, 93.74 on BC5CDR-Chemical, and 90.69 on BC5CDR-Disease (Jiang et al., 2021), and around 89 F1 on BioRED (Luo et al., 2022). These figures are not directly comparable to our setup."
- Learning curve: none reported; Section 6.2: "Future research should examine the learning curve by incrementally increasing the volume of development data." No fine-tuned model (BioBERT, PubMedBERT) is run.
- Loop termination threshold: strict-match F1 0.9, described as conservative relative to the cited IAA values.

### Inferences
- The thesis's dev100 and four-subtype strict scoring match the base paper exactly, so "0.80 vs 0.76" is a like-for-like comparison of single runs (subject to the run-to-run noise documented in the thesis repository).
- The base paper's own future-work item concerns more moderation documents, not supervised training, so a thesis statement about "equivalent supervised training size" has no support in the base paper and must rest on the external learning curves in Q1.

### Gaps
- I did not compare arXiv v1 and the ACL version line by line; the key numbers above match in both.

## Verification record (核查记录)

- Primary texts read by direct fetch (HTML) or by downloading the PDF and running `pdftotext -layout`, then `grep`/`sed` on the text: base paper arXiv HTML v1 and ACL 2026 PDF; Doğan and Lu 2012 PDF; Doğan et al. 2014 PMC page; DNorm and BioBERT journal pages; NEEDLE PDF; Gutiérrez et al. 2022 PDF; Gutiérrez et al. 2023 PDF; RDANER PDF; Chen et al. 2025 PMC page and arXiv PDF; Hou et al. 2025 PDF; Kim et al. 2025 PDF; Good et al. 2015 PDF; Sachan et al. 2018 PDF; Moradi et al. 2021 PDF; Jahan et al., Su et al., Ge et al., Monajatipoor et al., Zhao and Goto, Chen/Su/Sun arXiv HTML pages (read through the fetch tool's summarizer, so exact table cells there carry a small transcription risk).
- Only search snippets (unverified): BINDER 90.9, BERT-MRC 90.04, Hu et al. 2024 relaxed F1 values, venues for Jahan et al. (Computers in Biology and Medicine) and Su et al. (JBI).
- Downloaded PDFs, SHA-256 (`sha256sum`; scratchpad copies, not saved to the repository):
  - ACL 2026 base paper (aclanthology.org/2026.acl-long.1760.pdf): 0f0b205eea63f7bf4855fa9453423bc46c36f2c9261af50e49024cf60f40e15f
  - NEEDLE (arXiv 2106.08977): 3a730b8efdd0057acc92cbcacb67ab74de4660cdb0180ec5bc6d35d37c850d9f
  - Gutiérrez et al. 2022 (arXiv 2203.08410v2): 43644dcc04e27f3dd8dac0aca0fe8edcad24d4ed16aa150f111a5c8225737f21
  - Gutiérrez et al. 2023 (arXiv 2306.17649): 3beef9a8a4be526cc469bfc78fbd764cb0ae651073988da701126c5b87dc9111
  - RDANER (arXiv 2101.00388): 628759ac2e22963f58c8e88282b8c202c9da7c76e17cfd3ceba151aa1edb9fea
  - Chen et al. 2025 (arXiv 2305.16326): 0c63c0d83a0bfbf6c06ec110b394288e9f53474696743c43ab925c9c2ee2a827
  - Hou et al. 2025 (arXiv 2509.04462): f637600c2129feadf8423f3941ce4044583de07a67fde0c9e78014cdbfbad172
  - Kim et al. 2025 (arXiv 2510.12835v1): 54d085ff8283620638764b8d9e2c9527fee148c5bc57b95c4db6181bf9f81f6f
  - Doğan and Lu 2012 (W12-2411): b632de5542e297295f6448f0c6598a3d72a6771a8023e84f8fc629e0301a61d9
  - Good et al. 2015 (arXiv 1408.1928): ef9a79dc205692107e9cd383f90706abb3e9dba96e2118edcec37d20cc303b90
  - Sachan et al. 2018 (arXiv 1711.07908): cb6bc91280467061757aea7d5f904ce82db8ad530410dfba2211e9781c5e1217
  - Moradi et al. 2021 (arXiv 2109.02555): 8e0a82b9c2658307f2ece3d937ccb46c33e844a0ef20a9ad69a378df4a87ef90
- Not run: no PDF figure rendering (pdftoppm and pdfimages not installed), so figure-only values (Doğan 2012 Figure 3, Doğan 2014 Figure 2, Sachan Figure 8a, Hou Figure 1) were not read. No repository files were read or changed except this notes file.
