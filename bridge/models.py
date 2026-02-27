from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedSections:
    arquivos_modificados: str = ""
    diff_logico: str = ""
    como_testar: str = ""
    riscos: str = ""
    observacoes: str = ""
    found_any_section: bool = False


@dataclass
class IngestResult:
    task_id: str
    stage: str
    source: str
    raw_text: str
    parsed: ParsedSections
    summary_lines: list[str] = field(default_factory=list)
