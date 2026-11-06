"""Dependency-free selection, manifest validation, and evaluation metrics."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path, PureWindowsPath

PROTOCOL = "LumaCaption-eval-v1"
COUNTS = {"test": 50, "dev": 10}
SPLIT_FILES = {name: f"Flickr_8k.{name}Images.txt" for name in ("train", "dev", "test")}
REFERENCE_FILE = "Flickr8k.token.txt"


class EvaluationError(ValueError):
    """Invalid evaluation input; messages must not contain source content or paths."""


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def ids_digest(names: list[str]) -> str:
    return hashlib.sha256(("\n".join(names) + "\n").encode("utf-8")).hexdigest()


def identifier(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(c in value for c in '/\\:<>|"*?')
        or any(ord(c) < 32 for c in value)
        or value in {".", ".."}
        or value.endswith((".", " "))
        or PureWindowsPath(value).is_reserved()
    ):
        raise EvaluationError("Invalid image identifier.")
    return value


def rank(names: list[str], split: str) -> list[str]:
    def key(name):
        value = f"{PROTOCOL}|{split}|{name}".encode()
        return hashlib.sha256(value).hexdigest(), name

    return sorted(names, key=key)


def exclusions_from_reports(paths: list[Path]) -> dict[str, str]:
    excluded = {}
    for path in paths:
        try:
            document = json.loads(path.read_text(encoding="utf-8-sig"))
            rows = document["results"]
            if not isinstance(rows, list) or not rows:
                raise EvaluationError("Invalid smoke report.")
            for row in rows:
                excluded[identifier(row["filename"])] = "Prior offline smoke test"
        except (KeyError, TypeError, ValueError) as exc:
            raise EvaluationError("Invalid smoke report.") from exc
    return excluded


def _exclusions(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise EvaluationError("Exclusions must map image identifiers to reasons.")
    for name, reason in value.items():
        identifier(name)
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
            raise EvaluationError("Every exclusion requires a short reason.")
    return value


def build_manifest(text_root: Path, image_root: Path, exclusions: dict) -> dict:
    """Select before checking image availability; references never leave the caller."""
    _exclusions(exclusions)
    splits, hashes = {}, {}
    for split, filename in SPLIT_FILES.items():
        path = text_root / filename
        raw = path.read_bytes()
        names = [
            identifier(line.strip())
            for line in raw.decode("utf-8-sig").splitlines()
            if line.strip()
        ]
        if len({name.casefold() for name in names}) != len(names):
            raise EvaluationError("Duplicate split identifiers.")
        splits[split] = names
        hashes[filename] = hashlib.sha256(raw).hexdigest()
    all_names = [name.casefold() for names in splits.values() for name in names]
    if len(set(all_names)) != len(all_names):
        raise EvaluationError("Dataset splits overlap.")
    selected = {}
    for split, count in COUNTS.items():
        selected[split] = rank([name for name in splits[split] if name not in exclusions], split)[
            :count
        ]
        if len(selected[split]) != count:
            raise EvaluationError("Not enough eligible images for the fixed split.")
    wanted = {name for names in selected.values() for name in names}
    refs = {name: {} for name in wanted}
    ref_path = text_root / REFERENCE_FILE
    raw_references = ref_path.read_bytes()
    for line in raw_references.decode("utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            key, caption = line.split("\t", 1)
            name, number = key.rsplit("#", 1)
            identifier(name)
            if number not in {"0", "1", "2", "3", "4"} or not caption.strip():
                raise ValueError
            if name in wanted:
                if number in refs[name]:
                    raise ValueError
                refs[name][number] = caption
        except ValueError as exc:
            raise EvaluationError("Malformed or duplicate reference record.") from exc
    hashes[REFERENCE_FILE] = hashlib.sha256(raw_references).hexdigest()
    rows = {}
    for split, names in selected.items():
        rows[split] = []
        for name in names:
            if set(refs[name]) != {"0", "1", "2", "3", "4"}:
                raise EvaluationError("Selected image does not have five references.")
            try:
                image_hash, availability = digest(image_root / name), "readable"
            except OSError:
                image_hash, availability = None, "unreadable"
            rows[split].append(
                {
                    "id": name,
                    "references": [refs[name][str(i)] for i in range(5)],
                    "image_sha256": image_hash,
                    "availability": availability,
                }
            )
    manifest = {
        "protocol": PROTOCOL,
        "schema_version": 1,
        "source_sha256": hashes,
        "split_counts": {split: len(names) for split, names in splits.items()},
        "exclusions": exclusions,
        "exclusions_sha256": ids_digest(sorted(exclusions)),
        "selection_sha256": {split: ids_digest(names) for split, names in selected.items()},
        "images": rows,
    }
    validate_manifest(manifest)
    return manifest


def _sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_manifest(document: object) -> dict:
    """Reject incompatible or ambiguous manifests before creating a run directory."""
    try:
        if not isinstance(document, dict):
            raise ValueError
        if not all(
            isinstance(document[key], dict)
            for key in ("source_sha256", "split_counts", "images", "selection_sha256")
        ):
            raise ValueError
        if set(document["selection_sha256"]) != set(COUNTS):
            raise ValueError
        if (
            document["protocol"] != PROTOCOL
            or type(document["schema_version"]) is not int
            or document["schema_version"] != 1
        ):
            raise ValueError
        exclusions = _exclusions(document["exclusions"])
        if document["exclusions_sha256"] != ids_digest(sorted(exclusions)):
            raise ValueError
        expected = set(SPLIT_FILES.values()) | {REFERENCE_FILE}
        if set(document["source_sha256"]) != expected:
            raise ValueError
        if not all(_sha(h) for h in document["source_sha256"].values()):
            raise ValueError
        if set(document["split_counts"]) != set(SPLIT_FILES):
            raise ValueError
        if not all(type(n) is int and n >= 0 for n in document["split_counts"].values()):
            raise ValueError
        if set(document["images"]) != set(COUNTS):
            raise ValueError
        seen = set()
        for split, count in COUNTS.items():
            rows = document["images"][split]
            if not isinstance(rows, list) or len(rows) != count:
                raise ValueError
            names = []
            for row in rows:
                name = identifier(row["id"])
                if name.casefold() in seen or name in exclusions:
                    raise ValueError
                seen.add(name.casefold())
                names.append(name)
                refs = row["references"]
                if (
                    not isinstance(refs, list)
                    or len(refs) != 5
                    or not all(isinstance(r, str) and r.strip() for r in refs)
                ):
                    raise ValueError
                if row["availability"] == "readable":
                    if not _sha(row["image_sha256"]):
                        raise ValueError
                elif row["availability"] != "unreadable" or row["image_sha256"] is not None:
                    raise ValueError
            if names != rank(names, split):
                raise ValueError
            if document["selection_sha256"][split] != ids_digest(names):
                raise ValueError
            if document["split_counts"][split] < count:
                raise ValueError
    except (KeyError, TypeError, ValueError) as exc:
        raise EvaluationError("Invalid or incompatible evaluation manifest.") from exc
    return document


def load_manifest(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    try:
        document = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise EvaluationError("Invalid manifest JSON.") from exc
    return validate_manifest(document), raw


def tokenize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text).casefold().replace("\u2019", "'")
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", text)


def _ngrams(tokens: list[str], n: int) -> Counter:
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def _lcs(a: list[str], b: list[str]) -> int:
    previous = [0] * (len(b) + 1)
    for left in a:
        current = [0]
        for j, right in enumerate(b):
            current.append(previous[j] + 1 if left == right else max(previous[j + 1], current[-1]))
        previous = current
    return previous[-1]


def score(captions: list[str], references: list[list[str]]) -> dict:
    """Corpus BLEU and macro best-reference LCS-F1 on the protocol's 0-100 scale."""
    if not captions or len(captions) != len(references):
        raise EvaluationError("Metric inputs must be nonempty and aligned.")
    if any(len(refs) != 5 or not all(r.strip() for r in refs) for refs in references):
        raise EvaluationError("Metrics require five nonempty references per image.")
    clipped, totals = [0] * 4, [0] * 4
    candidate_length = reference_length = 0
    rouge = []
    for caption, refs in zip(captions, references, strict=True):
        hyp, ref_tokens = tokenize(caption), [tokenize(ref) for ref in refs]
        candidate_length += len(hyp)
        reference_length += min(
            (len(ref) for ref in ref_tokens), key=lambda n: (abs(n - len(hyp)), n)
        )
        for index in range(4):
            counts = _ngrams(hyp, index + 1)
            maximum = Counter()
            for ref in ref_tokens:
                maximum |= _ngrams(ref, index + 1)
            clipped[index] += sum((counts & maximum).values())
            totals[index] += sum(counts.values())
        rouge.append(
            max((2 * _lcs(hyp, ref) / (len(hyp) + len(ref)) if hyp else 0) for ref in ref_tokens)
        )
    bp = min(1.0, math.exp(1 - reference_length / candidate_length)) if candidate_length else 0

    def bleu(n):
        if not candidate_length or any(not clipped[i] or not totals[i] for i in range(n)):
            return 0.0
        return 100 * bp * math.exp(sum(math.log(clipped[i] / totals[i]) for i in range(n)) / n)

    return {
        "bleu_1": bleu(1),
        "bleu_4": bleu(4),
        "rouge_l": 100 * sum(rouge) / len(rouge),
        "denominator": len(captions),
    }
