from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from bridge.constants import SECTION_ALIASES, STAGE_TO_FILE
from bridge.io_utils import atomic_write_text, read_text
from bridge.models import IngestResult, ParsedSections
from bridge.task_manager import ResolvedTask, update_header_metadata


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    return value.lower().strip()


def _title_to_key(raw_title: str) -> str | None:
    normalized = _normalize(raw_title).replace(":", "").strip()
    for key, aliases in SECTION_ALIASES.items():
        if normalized in {_normalize(alias) for alias in aliases}:
            return key
    return None


def _detect_heading(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None

    md_heading = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
    if md_heading:
        return md_heading.group(1)

    bold_heading = re.match(r"^\*\*(.+?)\*\*\s*:?$", stripped)
    if bold_heading:
        return bold_heading.group(1)

    under_heading = re.match(r"^__(.+?)__\s*:?$", stripped)
    if under_heading:
        return under_heading.group(1)

    plain_heading = re.match(r"^([\wÀ-ÿ\s]+)\s*:\s*$", stripped)
    if plain_heading:
        return plain_heading.group(1)

    return None


def parse_sections(raw_text: str) -> ParsedSections:
    lines = raw_text.splitlines()
    sections: dict[str, list[str]] = {
        "arquivos_modificados": [],
        "diff_logico": [],
        "como_testar": [],
        "riscos": [],
        "observacoes": [],
    }

    current_key: str | None = None
    found = False

    for line in lines:
        heading = _detect_heading(line)
        if heading:
            key = _title_to_key(heading)
            if key:
                current_key = key
                found = True
                continue

        if current_key:
            sections[current_key].append(line)

    return ParsedSections(
        arquivos_modificados="\n".join(sections["arquivos_modificados"]).strip(),
        diff_logico="\n".join(sections["diff_logico"]).strip(),
        como_testar="\n".join(sections["como_testar"]).strip(),
        riscos="\n".join(sections["riscos"]).strip(),
        observacoes="\n".join(sections["observacoes"]).strip(),
        found_any_section=found,
    )


def _extract_summary_lines(raw_text: str) -> list[str]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    out: list[str] = []
    for line in lines:
        if line.startswith(("-", "*", "•")):
            out.append(f"Codex informou: {line[1:].strip()}")
        else:
            out.append(f"Codex informou: {line}")
        if len(out) >= 8:
            break
    return out


def _render_stage_output(result: IngestResult) -> str:
    parsed = result.parsed
    blocks = [
        "## Ingest Metadata",
        f"- task_id: {result.task_id}",
        f"- stage: {result.stage}",
        f"- source: {result.source}",
        "",
        "## Seções detectadas",
        f"- arquivos_modificados: {'sim' if bool(parsed.arquivos_modificados) else 'não'}",
        f"- diff_logico: {'sim' if bool(parsed.diff_logico) else 'não'}",
        f"- como_testar: {'sim' if bool(parsed.como_testar) else 'não'}",
        f"- riscos: {'sim' if bool(parsed.riscos) else 'não'}",
        f"- observacoes: {'sim' if bool(parsed.observacoes) else 'não'}",
        "",
    ]

    if parsed.found_any_section:
        blocks += [
            "## Arquivos modificados",
            parsed.arquivos_modificados or "(não informado)",
            "",
            "## Diff lógico",
            parsed.diff_logico or "(não informado)",
            "",
            "## Como testar",
            parsed.como_testar or "(não informado)",
            "",
            "## Riscos",
            parsed.riscos or "(não informado)",
            "",
            "## Observações",
            parsed.observacoes or "(não informado)",
            "",
        ]
    else:
        blocks += ["## Resumo best-effort", ""]
        blocks.extend([f"- {line}" for line in result.summary_lines] or ["- Não foi possível identificar seções no texto ingerido."])
        blocks.append("")

    blocks += ["## RAW INPUT", "```text", result.raw_text.rstrip(), "```", ""]
    return "\n".join(blocks)


def ingest_codex_output(task: ResolvedTask, stage: str, raw_text: str, source: str) -> IngestResult:
    if stage not in STAGE_TO_FILE:
        raise ValueError("--stage deve ser diag ou impl")

    parsed = parse_sections(raw_text)
    result = IngestResult(
        task_id=task.task_id,
        stage=stage,
        source=source,
        raw_text=raw_text,
        parsed=parsed,
        summary_lines=_extract_summary_lines(raw_text),
    )

    stage_file = task.path / STAGE_TO_FILE[stage]
    original = read_text(stage_file)
    new_content = original.rstrip() + "\n\n" + _render_stage_output(result)
    atomic_write_text(stage_file, new_content.rstrip() + "\n")
    update_header_metadata(stage_file, status="updated", stage=stage)
    return result


def read_input_text(input_file: str | None) -> tuple[str, str]:
    if input_file:
        path = Path(input_file)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo de input não encontrado: {input_file}")
        return path.read_text(encoding="utf-8"), "file"

    import sys

    data = sys.stdin.read()
    if not data.strip():
        raise ValueError("Nenhum texto recebido via stdin. Informe --input ou passe conteúdo via pipe/stdin.")
    return data, "stdin"
