# autodigital-dev-bridge

CLI local (offline) em Python 3.11 para organizar tasks, ingerir output do Codex e gerar relatório em Markdown.

## Requisitos
- Python 3.11+
- Sem dependências externas para o MVP (stdlib)

## Execução (Windows / VS Code Terminal)

### Opção 1: sem instalar pacote
```powershell
python -m bridge.cli --help
```

### Opção 2: instalando entrypoint `bridge` (opcional)
```powershell
pip install -e .
bridge --help
```

## Comandos MVP

### 1) Criar task
```powershell
python -m bridge.cli task new "Diagnóstico fluxo ingest"
```
Resultado esperado:
- cria `tasks/YYYYMMDD-HHMMSS_slug/`
- cria arquivos `00..07`
- atualiza `tasks/.current`

### 2) Ingerir saída do Codex

#### via stdin (colar texto e finalizar com Ctrl+Z + Enter)
```powershell
python -m bridge.cli codex ingest --stage diag
```

#### via arquivo
```powershell
python -m bridge.cli codex ingest --stage impl --input .\codex_output_impl.txt
```

Resultado esperado:
- atualiza arquivo de stage (`03` ou `05`) com RAW + seções detectadas/best-effort
- atualiza `06_testes.md`
- atualiza `07_relatorio_notion.md`

### 3) Imprimir relatório Notion
```powershell
python -m bridge.cli report notion
```

Com task específica:
```powershell
python -m bridge.cli report notion --task 20260101-101010_minha-task
```

## Fluxo manual de validação (A/B/C)

### A) `task new`
1. Rodar:
   ```powershell
   python -m bridge.cli task new "MVP CLI offline"
   ```
2. Confirmar pasta criada em `tasks/`.
3. Confirmar 8 arquivos (`00..07`).
4. Abrir dois arquivos e validar header (`task_id`, `created_at`, `updated_at`, `status=draft`).

### B) `codex ingest`
1. Rodar `diag` com stdin:
   ```powershell
   python -m bridge.cli codex ingest --stage diag
   ```
2. Colar exemplo:
   ```text
   ## Arquivos modificados
   - bridge/cli.py
   - bridge/ingest.py

   ## Diff lógico
   Refatorado parser de ingest.

   ## Como testar
   - Rodar python -m bridge.cli --help

   ## Riscos
   - Baixo risco

   ## Observações
   - Sem dependências externas
   ```
3. Validar `03_codex_output_diag.md`, `06_testes.md`, `07_relatorio_notion.md`.
4. Rodar `impl` com arquivo:
   ```powershell
   python -m bridge.cli codex ingest --stage impl --input .\exemplo_impl.txt
   ```
5. Testar texto sem seções e confirmar modo best-effort sem inferências.

### C) `report notion`
1. Rodar sem `--task`:
   ```powershell
   python -m bridge.cli report notion
   ```
2. Confirmar stdout igual a `07_relatorio_notion.md` da task atual.
3. Rodar com `--task <id|path>` e confirmar resolução correta.

## Observações
- O MVP não faz chamadas HTTP/APIs.
- O MVP não automatiza navegador.
