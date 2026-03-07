from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


DEFAULT_TIMEOUT_SECONDS = 30


@dataclass
class GhCommandResult:
    returncode: int
    stdout: str
    stderr: str


class GhCliError(ValueError):
    pass


def _run_gh(args: list[str], timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> GhCommandResult:
    cmd = ["gh", *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GhCliError("GitHub CLI (gh) não encontrado no PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise GhCliError(f"Comando gh excedeu timeout de {timeout_seconds}s: {' '.join(cmd)}") from exc

    return GhCommandResult(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def auth_status_ok(timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> bool:
    result = _run_gh(["auth", "status"], timeout_seconds=timeout_seconds)
    return result.returncode == 0


def ensure_auth(timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> None:
    if not auth_status_ok(timeout_seconds=timeout_seconds):
        raise GhCliError("GitHub CLI não autenticado. Execute 'gh auth login'.")


def _with_repo(args: list[str], repo: str | None) -> list[str]:
    if repo:
        return [*args, "--repo", repo]
    return args


def pr_view_json(pr_number: int, repo: str | None = None, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> dict:
    args = _with_repo(
        [
            "pr",
            "view",
            str(pr_number),
            "--json",
            "number,title,baseRefName,headRefName,url",
        ],
        repo,
    )
    result = _run_gh(args, timeout_seconds=timeout_seconds)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        if "not found" in stderr.lower() or "could not resolve" in stderr.lower():
            repo_label = repo or "repositório atual"
            raise GhCliError(f"PR #{pr_number} não encontrado ou sem permissão no {repo_label}.")
        raise GhCliError(f"Falha ao consultar PR #{pr_number}: {stderr}")

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GhCliError("Saída inválida do 'gh pr view --json'.") from exc

    if not isinstance(payload, dict):
        raise GhCliError("Saída inesperada do 'gh pr view --json'.")
    return payload


def pr_diff_text(pr_number: int, repo: str | None = None, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    args = _with_repo(["pr", "diff", str(pr_number)], repo)
    result = _run_gh(args, timeout_seconds=timeout_seconds)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        if "not found" in stderr.lower() or "could not resolve" in stderr.lower():
            repo_label = repo or "repositório atual"
            raise GhCliError(f"PR #{pr_number} não encontrado ou sem permissão no {repo_label}.")
        raise GhCliError(f"Falha ao obter diff do PR #{pr_number}: {stderr}")
    return result.stdout
