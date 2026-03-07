# Diagnóstico MVP — autodigital-dev-bridge (CLI local, offline)

## 1) Estrutura mínima proposta do repositório (Windows + Python 3.11)

```text
autodigital-dev-bridge/
  pyproject.toml
  README.md
  bridge/
    __init__.py
    cli.py                 # parser de comandos + dispatch
    constants.py           # nomes de arquivos padrão, status, templates de header
    models.py              # dataclasses simples de TaskMeta/ParsedSections
    task_manager.py        # criação e descoberta de tasks (task new, task atual)
    ingest.py              # ingestão de output codex (stdin/arquivo), normalização e parse
    report.py              # geração/atualização de 06_testes e 07_relatorio_notion
    io_utils.py            # utilitários de leitura/escrita atômica e timestamps
  templates/
    file_header.md         # header padrão para todos os arquivos de task
    task/
      00_intent.md
      01_context.md
      02_prompt_diagnostico.md
      03_codex_output_diag.md
      04_prompt_implementacao.md
      05_codex_output_impl.md
      06_testes.md
      07_relatorio_notion.md
  tasks/
    .gitkeep
  docs/
    diagnostico_mvp_cli.md
  tests/
    test_parse_sections.py # opcional futuro (não obrigatório para MVP)
```

### Por quê
- **Separação por responsabilidade**: criação de task, ingestão e relatório ficam em módulos pequenos para manter manutenção simples e previsível.
- **Offline por padrão**: toda lógica local em arquivos Markdown + stdlib, sem integrações externas.
- **Rastreabilidade**: `task_id`, `stage`, timestamps e status vivem no header e no fluxo de ingestão.
- **Evolução sem retrabalho**: módulos `report.py`/`ingest.py` já deixam encaixe natural para futura integração com `gh` e Notion API.

---

## 2) Framework CLI escolhido

### Escolha: `argparse` (stdlib)

**Motivos**
- Zero dependências externas (alinhado ao requisito offline/gratuito).
- Estável em Python 3.11 no Windows 10/11.
- Fácil distribuir e executar com `python -m bridge.cli ...`.
- Mantém escopo do MVP baixo e reduz risco de compatibilidade.

**Quando reconsiderar Typer/Click no futuro**
- Se crescer muito o número de subcomandos e opções (UX de ajuda mais rica, auto-complete e tipagem mais declarativa).

---

## 3) Contrato de ingestão de output do Codex

## 3.1 Entrada suportada
- `bridge codex ingest --stage diag|impl` com:
  - **stdin** (pipe/colar texto), ou
  - **arquivo** via flag sugerida `--input <caminho>`.

## 3.2 Destino por stage
- `diag` → grava em `03_codex_output_diag.md`
- `impl` → grava em `05_codex_output_impl.md`

Ambos sempre devem:
- manter bloco de **raw input** intacto,
- registrar metadados: `task_id`, `stage`, `ingested_at`, `source` (`stdin`/`file`).

## 3.3 Seções alvo (quando existirem)
Extrair, nessa ordem lógica:
1. `Arquivos modificados`
2. `Diff lógico`
3. `Como testar`
4. `Riscos`
5. `Observações`

### Estratégia regex + heurísticas (tolerante a variações)
- Normalizar títulos:
  - case-insensitive
  - remover acentuação para comparar chaves
  - aceitar variações: singular/plural e sinônimos comuns.
- Regex de cabeçalho de seção (linha inteira):
  - `^\s{0,3}(#{1,6}|\*\*|__)?\s*(<titulo-alvo>)\s*[:\-]?\s*(\*\*|__)?\s*$`
- Delimitação da seção:
  - do cabeçalho detectado até o próximo cabeçalho detectado, ou fim do texto.
- Fallback best-effort:
  - se nenhuma seção for detectada, preservar texto bruto e gerar resumo apenas com fatos explícitos (sem completar lacunas).

## 3.4 Múltiplos arquivos alterados
- Heurística para extrair caminhos em blocos de arquivos modificados:
  - linhas iniciadas com `-`, `*`, `•`
  - padrões com extensões comuns (`.py`, `.md`, `.toml`, etc.)
  - caminhos com `/` ou `\`
- Salvar lista normalizada em bullets, sem deduplicação agressiva (apenas trim + remoção de duplicatas exatas).

## 3.5 Rastreabilidade e consistência
- `task_id`: derivado da pasta da task (`YYYYMMDD-HHMMSS_slug`).
- `stage`: `diag|impl` (obrigatório no comando).
- timestamps:
  - `created_at` na criação da task,
  - `updated_at` em cada escrita relevante,
  - `ingested_at` no arquivo de output do stage.
- `status` sugerido por arquivo:
  - `draft` ao criar task,
  - `updated` após ingest,
  - `ready` quando relatório estiver consolidado.

---

## 4) Plano de implementação (máx. 6 passos)

1. **Base do CLI e constantes**
   - Definir subcomandos (`task new`, `codex ingest`, `report notion`) e constantes de arquivos/stages.
2. **Criação de task (`task new`)**
   - Gerar `task_id`, pasta em `./tasks/`, arquivos 00–07 e header padrão.
3. **Ingestão (`codex ingest`)**
   - Ler stdin/arquivo, normalizar texto, detectar seções por regex/heurística, persistir raw + parse.
4. **Geração de artefatos**
   - Atualizar `06_testes.md` (checklist mínimo) e `07_relatorio_notion.md` (resumo objetivo e rastreável).
5. **Relatório (`report notion`)**
   - Resolver “task atual” (mais recente) ou `--task <id|path>` e imprimir `07_relatorio_notion.md` no stdout.
6. **Validação manual + documentação**
   - Rodar fluxo completo local no Windows (PowerShell e terminal do VS Code), documentar exemplos no README.

---

## 5) Testes manuais (passo a passo)

### A. `bridge task new "<titulo>"`
1. Executar comando com título simples.
2. Validar criação de pasta em `tasks/` com timestamp + slug.
3. Conferir presença dos 8 arquivos (00–07).
4. Abrir 2 arquivos e checar header (`task_id`, `date`, `status`).

### B. `bridge codex ingest --stage diag|impl`
1. Executar com `--stage diag` usando stdin.
2. Validar escrita em `03_codex_output_diag.md`.
3. Confirmar atualização de `06_testes.md` e `07_relatorio_notion.md`.
4. Repetir com `--stage impl` via `--input arquivo.txt`.
5. Testar texto sem seções: validar fallback best-effort sem adicionar informação não explícita.

### C. `bridge report notion`
1. Executar sem argumentos (task atual).
2. Validar stdout igual ao conteúdo de `07_relatorio_notion.md`.
3. Executar com task específica (`--task <id|path>`) e validar resolução correta.

---

## 6) Otimizações futuras (não implementar agora)

- **GitHub via `gh` (opcional)**
  - `bridge pr create`, `bridge pr list`, `bridge pr view` usando subprocess local.
  - Modo “dry-run” para exibir comando sem executar.
- **Export para Notion (API opcional)**
  - Adaptador separado (`bridge/integrations/notion.py`) e feature flag.
  - Sem acoplar no fluxo core offline.
- **Clipboard mode opcional**
  - `bridge codex ingest --from-clipboard` e `bridge report notion --to-clipboard`.
  - Implementação condicional por SO para evitar dependências obrigatórias.
- **Validação de contrato**
  - comando `bridge doctor` para checar estrutura de task e headers.
- **Templates customizáveis por equipe**
  - `templates/` sobreponíveis por config local (`~/.bridge/templates`).

---

## Itens faltantes no repositório atual e sugestão objetiva

Hoje o repo contém apenas base mínima (`pyproject.toml`, `bridge/cli.py`, templates e README praticamente vazios), então faltam:
- organização modular da lógica (`task_manager.py`, `ingest.py`, `report.py`, etc.),
- templates completos dos 8 arquivos de task,
- pasta `tasks/` versionada com `.gitkeep`,
- documentação de uso no `README.md` com exemplos dos 3 comandos,
- (opcional futuro) testes unitários de parser.

### O que criar exatamente (próxima etapa de implementação)
1. Arquivos Python citados na estrutura proposta.
2. Templates Markdown de header e arquivos `00..07`.
3. `tasks/.gitkeep`.
4. README com quickstart e exemplos de execução no Windows.
