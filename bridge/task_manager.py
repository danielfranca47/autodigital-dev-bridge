from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from bridge.constants import (
    CURRENT_TASK_FILE,
    HEADER_TEMPLATE_FILE,
    TASK_FILE_NAMES,
    TASK_TEMPLATE_DIR,
    TASKS_DIR,
)
from bridge.io_utils import atomic_write_text, ensure_dir, fill_placeholders, now_iso, read_text


@dataclass
class ResolvedTask:
    task_id: str
    path: Path


def slugify(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lower = ascii_only.lower().strip()
    lower = re.sub(r"\s+", "-", lower)
    lower = re.sub(r"[^a-z0-9-]", "", lower)
    lower = re.sub(r"-+", "-", lower).strip("-")
    return lower or "task"


def build_task_id(title: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{stamp}_{slugify(title)}"


def _header_for(task_id: str, title: str, status: str, stage: str) -> str:
    template = read_text(HEADER_TEMPLATE_FILE)
    now = now_iso()
    return fill_placeholders(
        template,
        {
            "task_id": task_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "status": status,
            "stage": stage,
        },
    )


def _stage_for_file(filename: str) -> str:
    if filename.startswith("03_"):
        return "diag"
    if filename.startswith("05_"):
        return "impl"
    return ""


def create_task(title: str) -> ResolvedTask:
    ensure_dir(TASKS_DIR)
    task_id = build_task_id(title)
    task_path = TASKS_DIR / task_id
    ensure_dir(task_path)

    for name in TASK_FILE_NAMES:
        template_path = TASK_TEMPLATE_DIR / name
        if not template_path.exists():
            raise FileNotFoundError(f"Template ausente: {template_path}")
        body = read_text(template_path)
        header = _header_for(task_id=task_id, title=title, status="draft", stage=_stage_for_file(name))
        atomic_write_text(task_path / name, f"{header}\n\n{body}".rstrip() + "\n")

    set_current_task(task_id)
    return ResolvedTask(task_id=task_id, path=task_path)


def set_current_task(task_id: str) -> None:
    ensure_dir(TASKS_DIR)
    atomic_write_text(CURRENT_TASK_FILE, f"{task_id}\n")


def resolve_task(task_ref: str | None = None) -> ResolvedTask:
    if task_ref:
        path_candidate = Path(task_ref)
        if path_candidate.exists() and path_candidate.is_dir():
            return ResolvedTask(task_id=path_candidate.name, path=path_candidate)

        by_id = TASKS_DIR / task_ref
        if by_id.exists() and by_id.is_dir():
            return ResolvedTask(task_id=task_ref, path=by_id)

        raise FileNotFoundError(f"Task não encontrada para --task={task_ref}")

    if CURRENT_TASK_FILE.exists():
        task_id = read_text(CURRENT_TASK_FILE).strip()
        if task_id:
            current = TASKS_DIR / task_id
            if current.exists() and current.is_dir():
                return ResolvedTask(task_id=task_id, path=current)

    tasks = sorted((p for p in TASKS_DIR.glob("*") if p.is_dir()), key=lambda p: p.name)
    if tasks:
        latest = tasks[-1]
        set_current_task(latest.name)
        return ResolvedTask(task_id=latest.name, path=latest)

    raise FileNotFoundError('Nenhuma task atual. Rode: bridge task new "<titulo>"')


def update_header_metadata(path: Path, *, status: str | None = None, stage: str | None = None) -> None:
    content = read_text(path)
    lines = content.splitlines()
    updated = []
    now = now_iso()
    in_header = False

    for line in lines:
        if line.strip() == "---" and not in_header:
            in_header = True
            updated.append(line)
            continue
        if line.strip() == "---" and in_header:
            updated.append(line)
            in_header = False
            continue

        if in_header:
            if line.startswith("updated_at:"):
                updated.append(f"updated_at: {now}")
                continue
            if status is not None and line.startswith("status:"):
                updated.append(f"status: {status}")
                continue
            if stage is not None and line.startswith("stage:"):
                updated.append(f"stage: {stage}")
                continue

        updated.append(line)

    atomic_write_text(path, "\n".join(updated).rstrip() + "\n")
