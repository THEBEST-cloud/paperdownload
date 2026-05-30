import csv
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Set

FIELDS = ["doi", "publisher", "title", "status", "reason", "file_path", "attempted_at"]


@dataclass
class ResultRow:
    doi: str
    publisher: str
    title: str
    status: str  # "success" | "failed"
    reason: str
    file_path: str
    attempted_at: str = ""


class ResultStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._rows: List[dict] = []
        if self.path.exists():
            with self.path.open(newline="", encoding="utf-8") as f:
                self._rows = list(csv.DictReader(f))

    def record(self, row: ResultRow) -> None:
        d = asdict(row)
        if not d["attempted_at"]:
            d["attempted_at"] = datetime.now(timezone.utc).isoformat()
        self._rows.append(d)
        self._flush()

    def _flush(self) -> None:
        with self.path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(self._rows)

    def completed_dois(self) -> Set[str]:
        return {r["doi"] for r in self._rows if r["status"] == "success"}

    def failed_dois(self) -> List[str]:
        done = self.completed_dois()
        seen, out = set(), []
        for r in self._rows:
            if r["status"] == "failed" and r["doi"] not in done and r["doi"] not in seen:
                seen.add(r["doi"])
                out.append(r["doi"])
        return out
