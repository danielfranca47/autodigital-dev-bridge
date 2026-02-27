from __future__ import annotations

import re
from dataclasses import dataclass, field

from bridge.gh_client import ensure_auth, pr_diff_text, pr_view_json
from bridge.task_manager import ResolvedTask, resolve_task

MAX_DIFF_BYTES = 1_500_000
MAX_FILES_SUMMARIZED = 30
MAX_HUNKS_PER_FILE = 3
MAX_LINES_PER_HUNK = 8
MAX_SNIPPET_CHARS = 160


@dataclass
class DiffFileSummary:
    path: str
    snippets: list[str] = field(default_factory=list)
    is_binary: bool = False


@dataclass
class PrAnalysisResult:
    task: ResolvedTask
    stage: str
    pr_meta: dict
    repo: str | None
    files: list[str]
    file_summaries: list[DiffFileSummary]
    diff_was_truncated: bool
    truncated_reason: str | None = None


def _truncate_snippet(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) <= MAX_SNIPPET_CHARS:
        return cleaned
    return cleaned[: MAX_SNIPPET_CHARS - 1] + "…"


def _parse_diff(diff_text: str) -> tuple[list[str], list[DiffFileSummary]]:
    files: list[str] = []
    summaries: list[DiffFileSummary] = []
    seen = set()

    current_file: DiffFileSummary | None = None
    current_hunk_lines = 0
    current_hunks = 0

    diff_header_re = re.compile(r"^diff --git a/(.+) b/(.+)$")

    def _start_file(path: str) -> None:
        nonlocal current_file, current_hunk_lines, current_hunks
        current_hunk_lines = 0
        current_hunks = 0
        current_file = DiffFileSummary(path=path)
        summaries.append(current_file)
        if path not in seen:
            seen.add(path)
            files.append(path)

    for raw_line in diff_text.splitlines():
        header_match = diff_header_re.match(raw_line)
        if header_match:
            _start_file(header_match.group(2))
            continue

        if current_file is None:
            continue

        if raw_line.startswith("rename to "):
            new_path = raw_line.replace("rename to ", "", 1).strip()
            if new_path:
                current_file.path = new_path
                if new_path not in seen:
                    seen.add(new_path)
                    files.append(new_path)
            continue

        if raw_line.startswith("Binary files ") and " differ" in raw_line:
            current_file.is_binary = True
            continue

        if raw_line.startswith("@@"):
            current_hunks += 1
            current_hunk_lines = 0
            continue

        if current_hunks == 0 or current_hunks > MAX_HUNKS_PER_FILE:
            continue

        if raw_line.startswith("+++") or raw_line.startswith("---"):
            continue

        if not raw_line.startswith(("+", "-")):
            continue

        if current_hunk_lines >= MAX_LINES_PER_HUNK:
            continue

        marker = "adiciona" if raw_line.startswith("+") else "remove"
        snippet = _truncate_snippet(raw_line[1:])
        if not snippet:
            continue

        current_file.snippets.append(f"{marker}: '{snippet}'")
        current_hunk_lines += 1

    deduped_summaries: list[DiffFileSummary] = []
    seen_paths = set()
    for item in summaries:
        if item.path in seen_paths:
            continue
        seen_paths.add(item.path)
        deduped_summaries.append(item)

    return files, deduped_summaries


def analyze_pr(pr_number: int, repo: str | None, task_ref: str | None, stage: str) -> PrAnalysisResult:
    if pr_number <= 0:
        raise ValueError("pr_number deve ser um inteiro positivo.")
    if stage not in {"diag", "impl"}:
        raise ValueError("stage deve ser 'diag' ou 'impl'.")

    task = resolve_task(task_ref)
    ensure_auth()

    pr_meta = pr_view_json(pr_number, repo=repo)
    diff_raw = pr_diff_text(pr_number, repo=repo)

    raw_bytes = diff_raw.encode("utf-8", errors="replace")
    truncated = False
    truncated_reason = None
    if len(raw_bytes) > MAX_DIFF_BYTES:
        truncated = True
        truncated_reason = "Resumo parcial: diff excedeu limite configurado."
        clipped = raw_bytes[:MAX_DIFF_BYTES]
        diff_text = clipped.decode("utf-8", errors="ignore")
    else:
        diff_text = diff_raw

    files, file_summaries = _parse_diff(diff_text)
    if len(file_summaries) > MAX_FILES_SUMMARIZED:
        truncated = True
        truncated_reason = truncated_reason or "Resumo parcial: limite de arquivos resumidos excedido."
        file_summaries = file_summaries[:MAX_FILES_SUMMARIZED]

    return PrAnalysisResult(
        task=task,
        stage=stage,
        pr_meta=pr_meta,
        repo=repo,
        files=files,
        file_summaries=file_summaries,
        diff_was_truncated=truncated,
        truncated_reason=truncated_reason,
    )
