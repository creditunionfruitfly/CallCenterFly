"""Post-selection response catalog; never part of the learned policy."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ResponseTemplate:
    script_id: str
    action_family: str
    response_text: str
    review_status: str
    required_slots: tuple[str, ...]
    prohibited_claims: tuple[str, ...]


class ResponseCatalog:
    def __init__(self, templates: list[ResponseTemplate]):
        self._by_action = {template.action_family: template for template in templates}
        if len(self._by_action) != len(templates):
            raise ValueError("response catalog has duplicate action families")

    @classmethod
    def from_csv(cls, path: Path) -> ResponseCatalog:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        return cls(
            [
                ResponseTemplate(
                    script_id=row["script_id"],
                    action_family=row["action_family"],
                    response_text=row["response_text"],
                    review_status=row["review_status"],
                    required_slots=tuple(filter(None, row["required_slots"].split("|"))),
                    prohibited_claims=tuple(filter(None, row["prohibited_claims"].split("|"))),
                )
                for row in rows
            ]
        )

    def resolve(self, action_family: str) -> ResponseTemplate | None:
        return self._by_action.get(action_family)

    @property
    def action_families(self) -> set[str]:
        return set(self._by_action)
