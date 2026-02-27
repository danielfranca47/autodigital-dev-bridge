from __future__ import annotations

import argparse
import sys

from bridge.ingest import ingest_codex_output, read_input_text
from bridge.report import get_notion_report_content, update_notion_report, update_testes_file
from bridge.task_manager import create_task, resolve_task


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bridge", description="autodigital-dev-bridge CLI (offline)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    task_parser = subparsers.add_parser("task", help="Operações de task")
    task_sub = task_parser.add_subparsers(dest="task_command", required=True)
    task_new = task_sub.add_parser("new", help="Criar nova task")
    task_new.add_argument("title", help="Título da task")

    codex_parser = subparsers.add_parser("codex", help="Operações de ingestão de output do Codex")
    codex_sub = codex_parser.add_subparsers(dest="codex_command", required=True)
    codex_ingest = codex_sub.add_parser("ingest", help="Ingerir output do Codex")
    codex_ingest.add_argument("--stage", required=True, choices=["diag", "impl"], help="Stage do output")
    codex_ingest.add_argument("--input", help="Arquivo de texto de entrada (se ausente, lê stdin)")
    codex_ingest.add_argument("--task", help="Task ID ou caminho da task")

    report_parser = subparsers.add_parser("report", help="Relatórios")
    report_sub = report_parser.add_subparsers(dest="report_command", required=True)
    report_notion = report_sub.add_parser("notion", help="Imprimir relatório Notion")
    report_notion.add_argument("--task", help="Task ID ou caminho da task")

    return parser


def cmd_task_new(title: str) -> int:
    task = create_task(title)
    print(f"Task criada: {task.task_id}")
    print(f"Pasta: {task.path}")
    return 0


def cmd_codex_ingest(stage: str, input_file: str | None, task_ref: str | None) -> int:
    task = resolve_task(task_ref)
    raw, source = read_input_text(input_file)
    result = ingest_codex_output(task=task, stage=stage, raw_text=raw, source=source)
    update_testes_file(task, result)
    update_notion_report(task, result)
    print(f"Ingest concluído para task {task.task_id} (stage={stage}, source={source}).")
    return 0


def cmd_report_notion(task_ref: str | None) -> int:
    task = resolve_task(task_ref)
    content = get_notion_report_content(task)
    print(content, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "task" and args.task_command == "new":
            return cmd_task_new(args.title)

        if args.command == "codex" and args.codex_command == "ingest":
            return cmd_codex_ingest(args.stage, args.input, args.task)

        if args.command == "report" and args.report_command == "notion":
            return cmd_report_notion(args.task)
    except FileNotFoundError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
