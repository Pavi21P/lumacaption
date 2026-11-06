# Caption evaluation protocol

Protocol: LumaCaption-eval-v1

Recorded: 2026-11-05

Status: protocol only; runner and measured baseline are LC07.

## Purpose and limits

Establish a repeatable local baseline for the existing captioner, with lexical scores, operational failures, and separate human judgments. This is a small educational evaluation, not a published benchmark replication or a controlled comparison against the tutorial model. Smoke-test captions are not quality measurements.

The test subset is held out from this project's tuning. Overlap with upstream BLIP training data is unverified; do not call it an uncontaminated test set. The [pinned model card](https://huggingface.co/Salesforce/blip-image-captioning-base/blob/82a37760796d32b1411fe092ab5d4e227313294b/README.md) describes COCO pretraining, and the [BLIP paper](https://arxiv.org/abs/2201.12086) describes web image/text pretraining. Neither establishes absence of Flickr8k overlap. Once inspected, this subset becomes a regression set; further quality claims need a new holdout.

## Dataset, rights, and storage

Use the locally supplied Flickr8k images, raw Flickr8k.token.txt references, and official train/dev/test lists. The [publisher's dataset page and terms](https://hockenmaier.cs.illinois.edu/Framing_Image_Description/KCCA.html) provide the material for non-commercial research and educational purposes, retain the original image owners' rights, and require respecting Flickr's terms. This protocol does not grant redistribution or commercial-use rights. Dataset material is outside LumaCaption's MIT license.

Attribute: Micah Hodosh, Peter Young, and Julia Hockenmaier (2013), *Framing Image Description as a Ranking Task: Data, Models and Evaluation Metrics*, Journal of Artificial Intelligence Research 47, 853-899.

Keep images, references, manifests, generated captions, and individual review records local. Original files remain outside the repository. Store run artifacts under ignored .local/evaluation/v1/<run-id>/; never overwrite a previous run. Public documentation may contain aggregate results and anonymized environment information after checking for private paths and source content.

## Deterministic selection

1. Read Flickr_8k.trainImages.txt, Flickr_8k.devImages.txt, and Flickr_8k.testImages.txt as UTF-8 with optional BOM. Strip surrounding whitespace and ignore blank lines; preserve case. Require basename-only identifiers, no path separators, absolute paths, or traversal components. Reject duplicates and overlap between splits.
2. Before inspecting test images, freeze an exclusion list of images previously used for smoke tests or manual tuning, with reasons. Include identifiers from existing local offline reports. The LC06 audit found two known smoke-test images; neither occurs in dev/test. Record any additional known prior use before freezing.
3. For each remaining identifier, calculate SHA-256 of UTF-8 text consisting of protocol identifier, split name (test or dev), and basename, joined by literal vertical bars. Example input shape: LumaCaption-eval-v1|test|<basename>. Sort by hexadecimal digest ascending, then basename ascending to break ties.
4. Take the first 50 test identifiers and first 10 dev identifiers in that order. Dev is for runner calibration and warmup; do not tune against test results. Do not select by caption quality, image availability, or perceived difficulty.
5. Parse raw references as identifier#reference-number, a tab, then caption. Each selected image must have exactly five nonempty references numbered 0 through 4, without duplicate identifiers/numbers. Malformed selected references invalidate the evaluation; do not substitute lemmatized captions or legacy expert/crowd judgments.
6. Freeze a private manifest before test generation: protocol/version, ordered identifiers, exclusions/reasons, source-list and reference-file SHA-256 hashes, five references per image, and source-image hashes where readable. Record missing/unreadable files explicitly. Selection precedes availability checks; never silently replace failed images.

For selection/exclusion digests, hash UTF-8 identifiers joined with LF plus a final LF; use rank order for selections and ascending basename order for exclusions. Record the frozen manifest's byte hash in every report. Supply image/reference roots at runtime; public reports must not expose local paths.

The 2026-11-05 metadata audit found disjoint 6,000/1,000/1,000 train/dev/test lists. All 1,000 test identifiers had five references and existing image paths. All selected 50 test and 10 dev identifiers had files and references 0-4. No images were decoded and no inference ran. The aggregate audit is retained locally; LC07 must freeze the complete manifest and verify file hashes.

## Fixed generation and execution

Use the shared application engine and image loader, without caption edits:

| Setting | Value |
| --- | --- |
| Model | Salesforce/blip-image-captioning-base |
| Revision | 82a37760796d32b1411fe092ab5d4e227313294b |
| Device | CPU |
| Length | Standard, max_new_tokens=35 |
| Search | num_beams=3, do_sample=False, no_repeat_ngram_size=3 |
| Input | No text prompt; existing RGB/EXIF/size-limit processing |
| Output | Original engine caption, including existing whitespace/capitalization handling |

Load the cached model once, offline, and time preparation separately. Warm up with the first selected dev image, outside measured test results. Then process all 50 test images in manifest order using one engine. Refuse network downloads; record any inability to complete preparation. Record warmup failure explicitly. A retry requires a new run identifier and must retain the original failed report.

Record Git commit and dirty flag, protocol and manifest hashes, dependency-lock hash, actual Python/Pillow/torch/transformers versions, OS, CPU model and thread count, generation settings, and UTC start/end times. Omit usernames, hostnames, tokens, and private paths from public summaries. Do not promise identical output across different runtimes or hardware.

Each manifest row retains generated caption, status (done/error/not_processed), elapsed time, and a sanitized failure category. Missing or corrupt images remain in the 50-image denominator. A fatal model failure leaves remaining rows not_processed. Interrupted runs are provisional, not completed baselines. Missing/invalid references invalidate metric reporting; do not silently omit those rows.

## Automatic metrics

All metrics below are project-defined variants, displayed on a 0-100 scale; none is an accuracy percentage. Keep full precision in the private report and round displayed scores to two decimals. Use all five references. Failed/not_processed rows contribute empty hypotheses when references are valid; report their counts alongside scores.

Tokenization: Unicode NFKC normalization, casefold, replace U+2019 with ASCII apostrophe, then extract matches of the Python regular expression [a-z0-9]+(?:'[a-z0-9]+)?. Apply identically to predictions and references. No stemming, stopword removal, or synonym matching.

### Corpus BLEU-1 and BLEU-4

Use corpus modified precision: clip each candidate n-gram count by its maximum count in any reference for that image, then sum numerators and denominators over images. Let C be total candidate length and R the sum of closest reference lengths, breaking equal-distance ties toward the shorter reference. BP is 1 if C > R, otherwise exp(1 - R/C). Score = BP times exp(mean(log(p_n))) for n=1..N, with N=1 or 4. Return zero if C=0 or any required precision/denominator is zero. No smoothing or effective-order reduction.

This follows the core [BLEU definition, Papineni et al. (2002)](https://aclanthology.org/P02-1040/), with the explicit tokenizer and edge cases above. Scores on this small subset are not directly comparable to published COCO or Flickr8k results.

### ROUGE-L, best-reference F1

For each hypothesis/reference pair, let L be token longest-common-subsequence length. Pair F1 = 2L / (hypothesis length + reference length); an empty hypothesis scores zero. Take the maximum F1 across the five references, then the arithmetic mean over all 50 images.

This is an explicitly defined sentence-level variant inspired by [ROUGE, Lin (2004)](https://aclanthology.org/W04-1013/). It is not summary-level union-LCS ROUGE-Lsum. Lexical overlap can penalize valid paraphrases and reward fluent but incorrect descriptions.

### Reliability and timing

Report done/error/not_processed counts and done/50 completion rate. Record preparation and warmup time separately, total test wall time including failures, and per-image load-plus-inference time. For successful images report count, median, and nearest-rank p95 (sorted index ceil(0.95*n), one-based); use null when n=0. Report failure timing separately. Timing applies only to the recorded machine and runtime.

## Human review

Human ratings must come from an actual reviewer. Default to null/unreviewed; do not infer ratings from lexical scores or generate them with the captioning model. Aim to review every successful test caption. Show the image and original generated caption before references; hide model identity where feasible. Shuffle review order by SHA-256 of LumaCaption-eval-v1|review|<basename>, then basename.

| Axis | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Faithfulness | Wrong main subject/action or major invented claim | Minor unsupported detail | No observed unsupported claim |
| Coverage | Misses salient content | Captures some main content | Captures main entities/action |
| Fluency | Unintelligible | Understandable but awkward | Clear English |

Also record hallucination as yes/no/uncertain and a short explanation. Judge visible content without guessing identity or sensitive personal attributes. A caption is acceptable under this rubric only if faithfulness=2, coverage>=1, fluency>=1, and hallucination=no. Never edit a caption before grading it; save proposed improvements separately.

Record reviewer pseudonym, review time, and rubric version. Report reviewed/successful coverage, axis distributions, hallucination counts, and acceptable/reviewed count. Unreviewed rows are not zero ratings. A second independent reviewer is optional; report disagreements explicitly if used, and do not claim inter-rater agreement from one reviewer. Fifty images support a modest local baseline, not broad population or superiority claims.

## LC07 implementation acceptance

- A CLI creates/validates a private frozen manifest and unique run directory, then uses the shared offline engine without changing source files.
- Synthetic cases verify stable selection, exclusions, malformed/duplicate references, clipped counts, brevity penalty, short/empty hypotheses, tokenization, LCS, and five-reference aggregation.
- Failure tests retain all selected rows, separate preparation from per-image timing, block downloads, and label partial runs and missing human reviews honestly.
- Run the real baseline when local data/cache are available. Publish only checked aggregates, exact configuration, failures, and limitations. Human-review fields remain pending until a person supplies ratings.
- Update this protocol/version before changing selection, tokenizer, metrics, or generation settings; retain previous manifests and reports.

See [validation evidence](VALIDATION.md), [execution plan](PLAN.md), and [third-party notices](../THIRD_PARTY_NOTICES.md).
