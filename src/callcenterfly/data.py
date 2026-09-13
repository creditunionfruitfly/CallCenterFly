"""CSV/JSONL dataset loading and release validation."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .schemas import DecisionPoint

SPLITS = ("train", "validation", "test")


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_action_catalog(dataset_root: Path) -> dict[str, str]:
    return {
        row["action_family"]: row["description"]
        for row in _rows(dataset_root / "data" / "action_catalog.csv")
    }


def load_prohibited_catalog(dataset_root: Path) -> set[str]:
    return {
        row["behavior_code"]
        for row in _rows(dataset_root / "data" / "prohibited_behavior_catalog.csv")
    }


def load_decision_points(dataset_root: Path, split: str) -> list[DecisionPoint]:
    if split not in SPLITS:
        raise ValueError(f"unknown split: {split}")
    path = dataset_root / "data" / f"decision_points_{split}.csv"
    return [DecisionPoint.from_mapping(row) for row in _rows(path)]


def iter_all_decision_points(dataset_root: Path) -> Iterable[DecisionPoint]:
    for split in SPLITS:
        yield from load_decision_points(dataset_root, split)


def find_decision(dataset_root: Path, decision_id: str) -> DecisionPoint:
    for decision in iter_all_decision_points(dataset_root):
        if decision.decision_id == decision_id:
            return decision
    raise KeyError(f"decision not found: {decision_id}")


@dataclass(frozen=True, slots=True)
class ValidationReport:
    passed: bool
    dataset_version: str
    episode_count: int
    decision_count: int
    action_count: int
    issues: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "dataset_version": self.dataset_version,
            "episode_count": self.episode_count,
            "decision_count": self.decision_count,
            "action_count": self.action_count,
            "issues": list(self.issues),
        }


def validate_release(dataset_root: Path) -> ValidationReport:
    manifest = json.loads((dataset_root / "manifest.json").read_text(encoding="utf-8"))
    actions = load_action_catalog(dataset_root)
    prohibited = load_prohibited_catalog(dataset_root)
    issues: list[str] = []
    decision_count = 0
    episode_count = 0
    decision_ids: set[str] = set()
    utterances: dict[str, set[str]] = {}

    for split in SPLITS:
        decisions = load_decision_points(dataset_root, split)
        utterances[split] = {decision.member_utterance for decision in decisions}
        decision_count += len(decisions)
        for decision in decisions:
            if decision.decision_id in decision_ids:
                issues.append(f"duplicate decision id: {decision.decision_id}")
            decision_ids.add(decision.decision_id)
            issues.extend(
                f"{decision.decision_id}: {issue}" for issue in decision.validate(set(actions))
            )
            unknown = set(decision.prohibited_behaviors) - prohibited
            if unknown:
                issues.append(
                    f"{decision.decision_id}: unknown prohibited behavior {sorted(unknown)}"
                )

        episode_path = dataset_root / "data" / f"episodes_{split}.jsonl"
        with episode_path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                episode = json.loads(line)
                episode_count += 1
                if episode.get("synthetic") is not True:
                    issues.append(f"{split} line {line_number}: synthetic flag is not true")
                if len(episode.get("turns", [])) != 3:
                    issues.append(f"{split} line {line_number}: expected three turns")

    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        overlap = utterances[left] & utterances[right]
        if overlap:
            issues.append(f"exact utterance leakage between {left} and {right}: {len(overlap)}")

    if decision_count != int(manifest["decision_count"]):
        issues.append("decision count does not match manifest")
    if episode_count != int(manifest["episode_count"]):
        issues.append("episode count does not match manifest")
    if manifest.get("scripts_included") is not False:
        issues.append("v0.1 dataset manifest must keep scripts_included=false")

    return ValidationReport(
        passed=not issues,
        dataset_version=str(manifest["version"]),
        episode_count=episode_count,
        decision_count=decision_count,
        action_count=len(actions),
        issues=tuple(issues),
    )
