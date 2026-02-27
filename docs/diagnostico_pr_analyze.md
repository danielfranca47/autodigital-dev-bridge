# Diagnóstico — comando `bridge pr analyze`

## Escopo
Adicionar um comando de diagnóstico (sem implementar ainda):

```bash
bridge pr analyze <pr_number> [--repo <owner/name>] [--task <id|path>] [--stage diag|impl]
```

Objetivo: usar `gh` via subprocess para ler metadados e diff real do PR, extrair referências concretas (arquivos + pontos-chave) e atualizar `07_relatorio_notion.md` sem inferências além do que está explícito no diff.

---

## 1) Design do comando (args e exemplos)

### Subcomando e posicionamento no CLI
- Nova árvore de comando: `bridge pr analyze`.
- Estrutura sugerida no `argparse` (conceitual):
  - comando raiz: `pr`
  - subcomando: `analyze`

### Argumentos
- `pr_number` (posicional, obrigatório)
  - Tipo: inteiro positivo.
  - Exemplo: `123`.
- `--repo <owner/name>` (opcional)
  - Override explícito do repositório alvo.
  - Se ausente: usar contexto atual do `gh` (repo do checkout atual).
- `--task <id|path>` (opcional)
  - Mesmo comportamento de resolução já existente (`resolve_task`).
  - Se ausente: task atual (`tasks/.current`).
- `--stage diag|impl` (opcional, default `impl`)
  - Define em qual “momento” registrar a análise no relatório.
  - Mesmo sem ingerir no `03/05`, fica útil para rastreabilidade textual no `07_relatorio_notion.md`.

### Comportamento esperado
1. Validar `pr_number`.
2. Checar disponibilidade/autenticação do `gh`.
3. Verificar existência/acesso ao PR (`gh pr view`).
4. Coletar diff (`gh pr diff`).
5. Extrair:
   - lista de arquivos alterados;
   - resumo factual de alterações por arquivo/hunk.
6. Atualizar `07_relatorio_notion.md` com seção específica de análise do PR.

### Exemplos de uso
```bash
# usa repo atual do checkout
bridge pr analyze 123

# força um repo específico
bridge pr analyze 456 --repo autodigital/dev-bridge

# associa a uma task específica por id
bridge pr analyze 456 --task 20260220-101122_fluxo-pr

# associa por caminho e marca stage de diagnóstico
bridge pr analyze 789 --task tasks/20260220-101122_fluxo-pr --stage diag
```

---

## 2) Estratégia de parsing do output do `gh pr diff`

### 2.1 Chamadas `gh` (somente subprocess)
Fluxo sugerido (na ordem):

1. **Pré-checagem de auth**
   - `gh auth status`
   - Falha: erro amigável orientando `gh auth login`.

2. **Validação do PR e metadados mínimos**
   - `gh pr view <pr_number> [--repo ...] --json number,title,baseRefName,headRefName,url`
   - Usa JSON para erro determinístico e metadados confiáveis.
   - Falha “PR inexistente/sem acesso”: mapear stderr para mensagem amigável.

3. **Coleta do diff textual**
   - `gh pr diff <pr_number> [--repo ...]`
   - Entrada única para extração factual.

> Observação: continua dentro da restrição “sem HTTP direto”; todo acesso passa pelo CLI `gh`.

### 2.2 Extração de lista de arquivos
Baseado em headers de diff unificado:

- Linha `diff --git a/<path> b/<path>` inicia bloco de arquivo.
- Casos especiais:
  - renomeio: usar `rename to <new_path>` quando existir;
  - arquivo novo: `new file mode` + caminho `b/<path>`;
  - arquivo removido: `deleted file mode` + caminho `a/<path>`.

Algoritmo simples:
1. Iterar linhas do diff.
2. Ao encontrar `diff --git`, abrir novo contexto de arquivo.
3. Resolver caminho canônico do arquivo para exibição.
4. Deduplicar preservando ordem de aparição.

Saída para relatório:
- bullets com caminhos reais (sem inferir arquivos não presentes).

### 2.3 Resumo factual (sem “fantasia”)
Regra central: **resumir só o que aparece em linhas de diff/hunk**.

Estratégia de baixo risco:
- Para cada arquivo, coletar no máximo N hunks (ex.: 3).
- Em cada hunk, coletar até M linhas adicionadas/removidas significativas (ex.: 8 por hunk), ignorando:
  - linhas vazias;
  - puro ruído de formatação quando detectável (opcional);
  - metadados (`+++`, `---`, `@@`).
- Produzir bullets no formato:
  - `<arquivo>: adiciona '<trecho curto>'`
  - `<arquivo>: remove '<trecho curto>'`

Restrições explícitas para evitar alucinação:
- Não classificar intenção (“refatorou”, “otimizou”, “corrigiu”) sem evidência literal.
- Não inferir comportamento em runtime.
- Não inventar testes executados.
- Se diff estiver truncado, declarar truncamento no relatório.

### 2.4 Limite de tamanho (diff grande)
Mecanismo recomendado:
- Limite de bytes no input processado (ex.: 1–2 MB) após captura do subprocess.
- Limites por arquivo/hunk/linha para síntese:
  - max arquivos resumidos: 30;
  - max hunks por arquivo: 3;
  - max linhas por hunk: 8;
  - max chars por snippet: 160.

Quando exceder:
- gerar resumo parcial com marcador:
  - `"Resumo parcial: diff excedeu limite configurado"`.
- manter lista completa de arquivos quando possível (ou também parcial com aviso explícito).

---

## 3) Arquivos novos/criados no repo (proposta)

Sem implementação nesta etapa; proposta de arquivos para próxima fase:

1. `bridge/pr_analyze.py`
   - Orquestra subprocess `gh`, parsing e geração de payload para relatório.
2. `bridge/gh_client.py`
   - Wrapper fino de subprocess para comandos `gh` (execução, timeout, mapeamento de erros amigáveis).
3. `tests/test_pr_diff_parser.py` (opcional, recomendado)
   - Testes unitários para parsing de `diff --git`, renomeio, arquivo novo/removido e truncamento.
4. Ajustes em `bridge/cli.py`
   - Registrar subcomando `pr analyze` e flags.
5. Ajustes em `bridge/report.py`
   - Função para anexar bloco “Análise de PR” no `07_relatorio_notion.md` sem destruir frontmatter.

Alternativa mínima (menos arquivos):
- concentrar tudo em `bridge/pr_analyze.py` e tocar `cli.py`/`report.py`.
- manter `gh_client.py` separado é preferível para testabilidade.

---

## 4) Testes manuais (comandos e outputs esperados)

### Caso feliz (repo atual)
```bash
python -m bridge.cli pr analyze 123
```
Esperado:
- exit code `0`;
- stdout informando PR analisado e task alvo;
- `07_relatorio_notion.md` atualizado com:
  - identificação do PR (número/título/url);
  - lista de arquivos reais do diff;
  - pontos-chave factuais do diff;
  - aviso de parcialidade se truncado.

### Repo explícito
```bash
python -m bridge.cli pr analyze 123 --repo owner/name
```
Esperado:
- mesmo comportamento do caso feliz;
- referência ao repo explícito no bloco de contexto da análise.

### Task explícita
```bash
python -m bridge.cli pr analyze 123 --task 20260220-101122_fluxo-pr --stage diag
```
Esperado:
- atualização do `07_relatorio_notion.md` da task informada (não da task atual);
- bloco contendo `stage=diag` para rastreabilidade.

### Erro: `gh` não autenticado
```bash
gh auth logout -h github.com
python -m bridge.cli pr analyze 123
```
Esperado:
- exit code `2`;
- stderr amigável, por exemplo:
  - `Erro: GitHub CLI não autenticado. Execute 'gh auth login'.`

### Erro: PR inexistente
```bash
python -m bridge.cli pr analyze 999999 --repo owner/name
```
Esperado:
- exit code `2`;
- stderr amigável, por exemplo:
  - `Erro: PR #999999 não encontrado ou sem permissão no repositório owner/name.`

---

## 5) Riscos e mitigação

1. **Diffs muito grandes**
   - Risco: consumo alto de memória/tempo e relatório verboso.
   - Mitigação: limites de processamento + resumo parcial explicitamente marcado.

2. **Repos privados/permissão insuficiente**
   - Risco: `gh pr view/diff` falha com mensagens pouco amigáveis.
   - Mitigação: traduzir erros comuns para mensagens de ação clara (login/permissão/repo).

3. **Ambiguidade de parsing (renomeios/binários)**
   - Risco: lista de arquivos incorreta ou resumo vazio.
   - Mitigação: regras específicas para `rename to`, `new file mode`, `deleted file mode` e “Binary files differ”.

4. **Resumo “fantasioso”**
   - Risco: confiança baixa no relatório.
   - Mitigação: política estrita de extração literal (somente evidências do diff), sem inferência causal/funcional.

5. **Dependência do estado local do `gh`**
   - Risco: comportamento varia por máquina (host, repo default, auth).
   - Mitigação: aceitar `--repo`, validar auth no início e retornar diagnóstico explícito do contexto.

---

## Proposta de faseamento (sem codar agora)
1. Implementar parser puro de diff com testes unitários (primeiro).
2. Integrar subprocess `gh` com mapeamento de erro amigável.
3. Expor `bridge pr analyze` no CLI.
4. Integrar atualização do `07_relatorio_notion.md`.
5. Rodar checklist manual acima com 1 PR pequeno e 1 PR grande.
