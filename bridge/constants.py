from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT_DIR / "tasks"
CURRENT_TASK_FILE = TASKS_DIR / ".current"
TEMPLATES_DIR = ROOT_DIR / "templates"
TASK_TEMPLATE_DIR = TEMPLATES_DIR / "task"
HEADER_TEMPLATE_FILE = TEMPLATES_DIR / "file_header.md"

TASK_FILE_NAMES = [
    "00_intent.md",
    "01_context.md",
    "02_prompt_diagnostico.md",
    "03_codex_output_diag.md",
    "04_prompt_implementacao.md",
    "05_codex_output_impl.md",
    "06_testes.md",
    "07_relatorio_notion.md",
]

STAGE_TO_FILE = {
    "diag": "03_codex_output_diag.md",
    "impl": "05_codex_output_impl.md",
}

SECTION_KEYS = [
    "arquivos_modificados",
    "diff_logico",
    "como_testar",
    "riscos",
    "observacoes",
]

SECTION_ALIASES = {
    "arquivos_modificados": [
        "arquivos modificados",
        "arquivo modificado",
        "files changed",
        "arquivos alterados",
    ],
    "diff_logico": ["diff logico", "diff lógico", "logical diff"],
    "como_testar": ["como testar", "testes", "how to test"],
    "riscos": ["riscos", "risco", "risks"],
    "observacoes": ["observacoes", "observações", "notas", "observations"],
}
