#!/usr/bin/env python3
"""Independent integrity checks for the v0.1 dataset release."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DOCS = ROOT / "docs"


def load_jsonl(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    schema = json.loads((DOCS / "episode_schema.json").read_text(encoding="utf-8"))
    source_keys = {row["source_key"] for row in load_csv(DATA / "source_registry.csv")}
    action_codes = {row["action_family"] for row in load_csv(DATA / "action_catalog.csv")}
    prohibited_codes = {row["behavior_code"] for row in load_csv(DATA / "prohibited_behavior_catalog.csv")}

    episodes = {}
    decisions = {}
    templates = {}
    utterances = {}
    expected_episode_counts = {"train": 1750, "validation": 375, "test": 375}
    expected_decision_counts = {"train": 5250, "validation": 1125, "test": 1125}
    failures = []

    for split in ("train", "validation", "test"):
        split_episodes = load_jsonl(DATA / f"episodes_{split}.jsonl")
        split_decisions = load_csv(DATA / f"decision_points_{split}.csv")
        episodes[split] = split_episodes
        decisions[split] = split_decisions
        templates[split] = {row["template_family_id"] for row in split_decisions}
        utterances[split] = {row["member_utterance"] for row in split_decisions}
        if len(split_episodes) != expected_episode_counts[split]:
            failures.append(f"{split}: episode count {len(split_episodes)}")
        if len(split_decisions) != expected_decision_counts[split]:
            failures.append(f"{split}: decision count {len(split_decisions)}")

        scenario_counts = Counter(e["scenario_id"] for e in split_episodes)
        expected_per_scenario = 70 if split == "train" else 15
        if len(scenario_counts) != 25 or set(scenario_counts.values()) != {expected_per_scenario}:
            failures.append(f"{split}: scenario balance mismatch")

        episode_by_id = {e["call_id"]: e for e in split_episodes}
        if len(episode_by_id) != len(split_episodes):
            failures.append(f"{split}: duplicate call_id")

        for episode in split_episodes:
            if episode.get("synthetic") is not True:
                failures.append(f"{episode['call_id']}: synthetic flag")
            if len(episode.get("turns", [])) != 3:
                failures.append(f"{episode['call_id']}: turn count")
            if any(turn.get("role") != "member" for turn in episode.get("turns", [])):
                failures.append(f"{episode['call_id']}: non-member text present")
            if not set(episode.get("source_keys", [])).issubset(source_keys):
                failures.append(f"{episode['call_id']}: unknown source key")

        for row in split_decisions:
            candidate = json.loads(row["candidate_actions_json"])
            acceptable = json.loads(row["acceptable_action_families_json"])
            prohibited = json.loads(row["prohibited_behaviors_json"])
            rewards = json.loads(row["candidate_rewards_json"])
            if row["call_id"] not in episode_by_id:
                failures.append(f"{row['decision_id']}: missing episode")
            if row["preferred_action_family"] not in candidate:
                failures.append(f"{row['decision_id']}: preferred outside mask")
            if not set(candidate).issubset(action_codes):
                failures.append(f"{row['decision_id']}: unknown candidate action")
            if not set(acceptable).issubset(set(candidate)):
                failures.append(f"{row['decision_id']}: acceptable outside mask")
            if not set(prohibited).issubset(prohibited_codes):
                failures.append(f"{row['decision_id']}: unknown prohibited behavior")
            if set(rewards) != set(candidate):
                failures.append(f"{row['decision_id']}: reward key mismatch")
            if row["script_text_status"] != "NOT_INCLUDED":
                failures.append(f"{row['decision_id']}: script text present")

    if templates["train"] & templates["validation"]:
        failures.append("train/validation template-family overlap")
    if templates["train"] & templates["test"]:
        failures.append("train/test template-family overlap")
    if templates["validation"] & templates["test"]:
        failures.append("validation/test template-family overlap")
    if utterances["train"] & utterances["validation"]:
        failures.append("train/validation exact-utterance overlap")
    if utterances["train"] & utterances["test"]:
        failures.append("train/test exact-utterance overlap")
    if utterances["validation"] & utterances["test"]:
        failures.append("validation/test exact-utterance overlap")

    all_text = "\n".join(
        row["member_utterance"]
        for split_rows in decisions.values()
        for row in split_rows
    )
    pii_patterns = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "phone": r"\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "long_number": r"\b\d{12,19}\b",
    }
    for label, pattern in pii_patterns.items():
        if re.search(pattern, all_text):
            failures.append(f"PII-like {label} pattern")

    try:
        import jsonschema
        validator = jsonschema.Draft202012Validator(schema)
        for split_rows in episodes.values():
            for episode in split_rows:
                errors = list(validator.iter_errors(episode))
                if errors:
                    failures.append(f"{episode['call_id']}: schema {errors[0].message}")
    except ImportError:
        print("jsonschema not installed; structural checks completed without JSON Schema validation")

    observed_episode_count = sum(len(rows) for rows in episodes.values())
    observed_decision_count = sum(len(rows) for rows in decisions.values())
    if observed_episode_count != manifest["episode_count"]:
        failures.append("manifest episode count mismatch")
    if observed_decision_count != manifest["decision_count"]:
        failures.append("manifest decision count mismatch")

    if failures:
        for failure in failures[:50]:
            print(f"FAIL: {failure}")
        print(f"Validation failed with {len(failures)} issue(s).")
        return 1

    print(
        f"PASS: {observed_episode_count} episodes, {observed_decision_count} decisions, "
        "25 balanced scenarios, no script text, no PII-pattern hits, no template-family leakage."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
