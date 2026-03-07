from __future__ import annotations

import re

from bridge.io_utils import atomic_write_text, read_text
from bridge.models import IngestResult
from bridge.pr_analyze import PrAnalysisResult
from bridge.task_manager import ResolvedTask, update_header_metadata


def _to_checklist(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    checklist: list[str] = []
    for line in lines:
        item = re.sub(r"^[-*•]\s*", "", line).strip()
        if item:
            checklist.append(f"- [ ] {item}")
    return checklist


def update_testes_file(task: ResolvedTask, result: IngestResult) -> None:
    path = task.path / "06_testes.md"
    original = read_text(path).rstrip()

    tests = _to_checklist(result.parsed.como_testar)
    if not tests:
        tests = [
            "- [ ] (a confirmar) Executar o fluxo principal do comando alterado.",
            "- [ ] (a confirmar) Conferir se os arquivos esperados foram gerados/atualizados.",
            "- [ ] (a confirmar) Registrar evidências no relatório da task.",
        ]

    block = [
        f"## Atualização de testes ({result.stage})",
        *tests,
        "",
    ]
    atomic_write_text(path, original + "\n\n" + "\n".join(block))
    update_header_metadata(path, status="ready")


def _extract_files_list(text: str) -> list[str]:
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        candidate = re.sub(r"^[-*•]\s*", "", line).strip()
        if "/" in candidate or "\\" in candidate or re.search(r"\.[a-zA-Z0-9]{1,8}$", candidate):
            out.append(candidate)
    deduped: list[str] = []
    seen = set()
    for item in out:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def update_notion_report(task: ResolvedTask, result: IngestResult) -> None:
    path = task.path / "07_relatorio_notion.md"
    parsed = result.parsed

    files = _extract_files_list(parsed.arquivos_modificados)
    files_block = "\n".join(f"- {f}" for f in files) if files else "não informado"

    how_to_test = parsed.como_testar.strip() or "não informado"
    risks = parsed.riscos.strip() or "não informado"
    obs = parsed.observacoes.strip() or "não informado"
    what_done = parsed.diff_logico.strip() or "\n".join(f"- {line}" for line in result.summary_lines) or "não informado"

    report = [
        "## Contexto/Objetivo",
        "não informado",
        "",
        "## O que foi feito",
        what_done,
        "",
        "## Arquivos alterados",
        files_block,
        "",
        "## Como testar",
        how_to_test,
        "",
        "## Riscos/observações",
        f"Riscos: {risks}",
        f"Observações: {obs}",
        "",
        "## Próximos passos",
        "não informado",
        "",
    ]

    # keep full file header (frontmatter) from existing content
    existing = read_text(path)
    parts = existing.split("---\n")
    if len(parts) >= 3:
        frontmatter = "---\n" + parts[1] + "---\n"
        content = frontmatter + "\n" + "\n".join(report)
    else:
        content = existing.rstrip() + "\n\n" + "\n".join(report)

    atomic_write_text(path, content.rstrip() + "\n")
    update_header_metadata(path, status="ready")


def get_notion_report_content(task: ResolvedTask) -> str:
    return read_text(task.path / "07_relatorio_notion.md")


def append_pr_analysis_block(task: ResolvedTask, analysis: PrAnalysisResult) -> None:
    path = task.path / "07_relatorio_notion.md"
    existing = read_text(path).rstrip()

    pr_number = analysis.pr_meta.get("number", "?")
    title = analysis.pr_meta.get("title", "não informado")
    url = analysis.pr_meta.get("url", "não informado")
    base_ref = analysis.pr_meta.get("baseRefName", "não informado")
    head_ref = analysis.pr_meta.get("headRefName", "não informado")
    repo_line = analysis.repo or "(contexto atual do gh)"

    files_block = "\n".join(f"- {item}" for item in analysis.files) if analysis.files else "- (nenhum arquivo detectado no diff)"

    points: list[str] = []
    for file_summary in analysis.file_summaries:
        if file_summary.is_binary:
            points.append(f"- {file_summary.path}: binário/sem diff textual")
        for snippet in file_summary.snippets:
            points.append(f"- {file_summary.path}: {snippet}")

    if not points:
        points = ["- (sem linhas +/- significativas dentro dos limites configurados)"]

    warning = ""
    if analysis.diff_was_truncated:
        warning = f"\n> ⚠️ {analysis.truncated_reason or 'Resumo parcial do diff.'}\n"

    block = [
        "## Análise de PR",
        f"- PR: #{pr_number} — {title}",
        f"- URL: {url}",
        f"- Base/Head: {base_ref} <- {head_ref}",
        f"- Stage: {analysis.stage}",
        f"- Repo: {repo_line}",
        "",
        "### Arquivos alterados",
        files_block,
        "",
        "### Pontos-chave do diff (factual)",
        *points,
    ]

    content = existing + "\n\n" + "\n".join(block)
    if warning:
        content += warning

    atomic_write_text(path, content.rstrip() + "\n")
    update_header_metadata(path, status="ready")
