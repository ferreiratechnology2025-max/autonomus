# Jarvis v3

Agente autônomo para automação de interface gráfica (Windows + Web) com percepção visual, execução de ações (GUI + navegador), memória episódica, integração com LLM (local-first), política de segurança determinística, planejamento hierárquico com cache inteligente.

## Requisitos

- Python 3.10+
- Windows 10/11
- Tesseract OCR (opcional, para OCR): [Download](https://github.com/UB-Mannheim/tesseract/wiki)
- OpenRouter API key (opcional, para LLM em nuvem): [https://openrouter.ai/keys](https://openrouter.ai/keys)
- Ollama (opcional, para LLM local): [https://ollama.com](https://ollama.com)

## Setup rápido

```bash
scripts\setup_local_first.bat
```

Isso cria venv, instala dependências, configura `.env` e verifica Ollama.

## Setup manual

```bash
pip install -r requirements.txt
pip install textual chromadb ollama python-dotenv  # opcionais
```

Copie o arquivo de configuração:

```bash
copy .env.example .env
# Edite .env com sua OpenRouter API key e/ou PRIVACY_MODE
```

## Configuração

Todas as configurações são definidas via variáveis de ambiente ou arquivo `.env`:

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `OPENROUTER_API_KEY` | `""` | Chave da API OpenRouter |
| `PRIVACY_MODE` | `true` | `true` = 100% local (ignora nuvem) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL do servidor Ollama |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Modelo Ollama padrão |
| `OLLAMA_TIMEOUT` | `30.0` | Timeout para chamadas Ollama (s) |
| `ENABLE_POLICY_ENGINE` | `true` | Ativa o policy engine |
| `REQUIRE_CONFIRM_HIGH_RISK` | `true` | Exige confirmação em ações de alto risco |
| `HEALTH_CHECK_INTERVAL_SECONDS` | `30` | Intervalo entre health checks |
| `MAX_DAILY_LLM_BUDGET` | `2.0` | Teto de gasto diário com LLM (USD) |
| `LLM_REQUEST_TIMEOUT_SECONDS` | `10.0` | Timeout para chamadas de API |
| `CALIBRATION_OVERRIDE_THRESHOLD` | `3` | Overrides para rebaixar risco de uma ação |
| `CALIBRATION_DECAY_DAYS` | `7` | Dias sem override para decair contador |
| `UIA_CLICK_DEBOUNCE_MS` | `80` | Delay entre detecção UIA e clique |
| `UIA_ENABLE_VISUAL_STABILITY_CHECK` | `true` | Verifica estabilidade visual antes do clique |

## Uso

### Iniciar o sistema (modo padrão — dashboard terminal)

```bash
python -m src.main
```

Tenta abrir o dashboard Textual. Se textual não estiver instalado, cai para o modo CLI.

### Modo CLI puro

```bash
python -m src.main_cli
```

### Diagnóstico do ambiente

```bash
python scripts\diagnose_local_first.py
```

## Arquitetura

O sistema é dividido em módulos:

```
src/
├── core/           Config, health check, logging, orchestrator, main loop
├── perception/     Screen capture (MSS), OCR (Tesseract), UI detection (OpenCV), UIA wrapper, window classifier
├── execution/      Ações atômicas (pyautogui), ações web (Playwright), debounce visual, context locking, rollback
├── memory/         SQLite, episódios, repositório de ações
├── integration/    OpenRouter client, Ollama client, hybrid router, LLM cache, cost budget
├── governance/     Policy engine, risk rules, sensitive data detector, calibration (determinística)
├── planning/       HTN decomposer, plan executor, repair engine, validator (UIA + OCR), cache de planos
└── utils/          LatencyTracker, métricas de performance
```

### Módulos

| Módulo | Responsabilidade |
|--------|------------------|
| **Core** | Bootstrap, configuração, health checks, main loop assíncrono |
| **Perception** | Captura de tela (MSS), OCR (Tesseract), detecção de UI (OpenCV), wrapper UIA (Windows Accessibility API), classificador de janela |
| **Execution** | Ações de mouse/teclado (pyautogui em `to_thread`), **ações web (Playwright**: navegação, clique, digitação, select em dropdown, extração de texto), debounce visual, context locking por HWND, rollback atômico |
| **Memory** | Banco SQLite, episódios, aprendizado |
| **Integration** | Cliente OpenRouter + Ollama com fallback em cascata, cache LRU, roteamento por sensibilidade, budget de gastos |
| **Governance** | Segurança determinística (regex + regras), detecção de dados sensíveis, calibração com decaimento temporal |
| **Planning** | HTN planner com **cache SQLite** (TTL 24h, invalidação automática em falha terminal), execução passo a passo, reparo com fallback, validação por UIA + OCR |
| **Utils** | LatencyTracker: tracker de latência assíncrono para relatórios de performance |

## Modo Local-First

O sistema prioriza execução local quando possível:

1. **PRIVACY_MODE=true** → 100% local (nuvem desabilitada)
2. **Dados sensíveis detectados** (CPF, dados médicos, financeiros) → rota local automática
3. **Sem OpenRouter** → rota local automática
4. **Fallback local** → se nuvem falha, tenta Ollama local

### Roteamento inteligente

```
Entrada
  │
  ▼
SensitiveDataDetector
  │
  ├── Dado sensível → Ollama local (exclusivamente)
  ├── PRIVACY_MODE  → Ollama local (exclusivamente)
  ├── Sem nuvem     → Ollama local
  └── Texto limpo   → OpenRouter → se falhar → Ollama local
```

## Automação Web (Playwright)

O sistema agora suporta automação de navegadores via Playwright (Chrome/Edge), com fallbacks robustos para elementos web:

| Ação | Descrição |
|------|-----------|
| `launch_browser` | Abre Chrome/Edge (headless opcional) |
| `navigate` | Navega para URL |
| `browser_click` | Clique em elemento por seletor CSS (6 estratégias de fallback) |
| `browser_click_by_text` | Clique em elemento por texto visível |
| `browser_type` | Digita texto em campo por seletor (fill → type → fallback genérico) |
| `browser_type_by_placeholder` | Digita em campo pelo placeholder |
| `browser_select` / `browser_select_by_label` | Seleciona option em dropdown com fallback fuzzy (acentos via JS) |
| `browser_press_enter` | Pressiona Enter no navegador |
| `browser_get_page_text` | Extrai texto visível da página |
| `browser_wait_for_selector` / `browser_wait_for_load` | Aguarda elemento ou carregamento |
| `close_browser` | Fecha navegador |

Os fallbacks garantem que mesmo com seletores CSS imprecisos (gerados por LLM pequeno), a ação ainda pode ser executada com sucesso.

### Smoke Test PJe (Produção)

O sistema inclui um smoke test multi-tribunal para validar resiliência em ambiente hostil:

```
python scripts/smoke_test_pje.py
```

- Tenta **5 tribunais** em sequência até encontrar consulta pública funcional
- Registra latência de navegação, preenchimento e extração (via LatencyTracker)
- `check_health()` valida sessão antes/depois de cada ação
- Relatório JSON salvo em `data/reports/smoke_pje_<timestamp>.json`
- Tribunais testados: TJPR, TJPB, TJMG, TJMA, TJPI (apenas TJPR respondeu — redirect Projudi)

Resultado típico: ~6s total (navegação 3s + filtro 1s + extração 200ms).

## Cache Inteligente de Planos (HTN)

O sistema possui um cache persistente SQLite que armazena planos gerados pelo LLM:

- **Cache-first**: antes de chamar o LLM, verifica se o mesmo objetivo já foi decomposto
- **Cache HIT**: resposta em <10ms (vs 40-70s de LLM)
- **TTL configurável**: 24h padrão, entradas expiradas são limpas automaticamente
- **Hash SHA256**: normaliza espaços e capitalização para matching consistente
- **Invalidação automática**: se a execução de um plano falha com erro terminal (elemento não encontrado, seletor inválido), o cache é invalidado para forçar regeneração
- **Falhas recuperáveis** (timeout, rede) não invalidam o cache
- **Recuperação condicional**: o orquestrador verifica a saúde da sessão (URL atual, erros HTTP, janela ativa) antes de regenerar o plano — se a sessão está comprometida (login redirect, erro 500, janela fechada), aborta o retry e escala o erro

## Segurança e Governança

### Policy Engine

O policy engine classifica ações em 5 níveis de risco:

| Nível | Exemplo | Decisão padrão |
|-------|---------|----------------|
| `SAFE` | Mover mouse, scroll | ALLOW |
| `LOW` | Digitar texto não-sensível | ALLOW |
| `MEDIUM` | Screenshot, clicar em botão "Login" | ALLOW |
| `HIGH` | Clicar em "Delete", digitar senha | CONFIRM |
| `CRITICAL` | Senha em texto, API key, rm -rf | BLOCK |

Todo o policy engine é **100% determinístico e local** — nenhuma decisão de segurança depende de LLM ou conectividade.

## Performance em Navegadores

Para melhor performance em Chrome/Edge, force a acessibilidade:

```bash
chrome.exe --force-renderer-accessibility
msedge.exe --force-renderer-accessibility
```

O sistema tentará UIA primeiro (HYBRID), com fallback para OCR.

### Política de Calibração (Escopo por Processo)

A calibração de risco é **específica por processo**. Sobrescrever "Delete" no Outlook não reduz o risco de "Delete" no CMD. A chave de calibração inclui `{action_type}:{process_name}`, garantindo isolamento entre aplicações.

### Dados Sensíveis

O detector reconhece automaticamente via regex:

- **Gerais**: Senhas, e-mails, cartões de crédito, API keys, tokens JWT, telefones, SSN
- **Brasileiros**: CPF, CNPJ, CEP, RG, CNS, PIS, processo jurídico
- **Médicos**: CID, CRM, prontuário
- **Financeiros**: Conta bancária, agência, chave PIX, CVV, passaporte, CNH, título de eleitor

### Calibração Determinística

Substitui o antigo gradiente descendente por contagem simples:

- A cada override do usuário, o contador da ação incrementa
- Após N overrides (padrão: 3), o risco da ação é rebaixado permanentemente (ex: HIGH → MEDIUM)
- O contador decai com o tempo (padrão: 7 dias sem override = -1)
- Persistência write-behind com flush periódico + auto-flush para overrides HIGH/CRITICAL

### Proteção contra Race Condition

O sistema verifica o HWND da janela **antes e depois** de cada clique. Se a janela mudar durante a execução (ex: usuário pressionou Alt+Tab):

1. Aborta a ação com `RaceConditionError`
2. Janela filha legítima (popup) é permitida
3. RepairEngine tenta revalidar e retentar
4. Se falha permanente, aborta a tarefa

Isso impede cliques em janelas erradas sem bloquear o input do usuário.

### Context Locking (HWND)

Antes de executar um clique via UIA, o sistema:

1. Captura o HWND da janela alvo
2. Aguarda debounce visual (80ms) + verificação de estabilidade
3. Verifica se o HWND atual é o mesmo ou é uma janela filha (até 25 níveis `GetParent`)
4. Fallback: se a árvore de parentesco falhar, compara o PID das janelas
5. Se mudou, aborta o clique com log — evita cliques em janela errada

### Roteamento Inteligente (UIA vs OCR)

O `WindowClassifier` detecta o tipo de janela ativa e roteia a validação:

| Janela | Estratégia | Motivo |
|--------|------------|--------|
| Chrome, Edge, Firefox | OCR_PRIMARY | UIA é caixa preta em WebViews |
| Electron (VS Code, Slack) | OCR_PRIMARY | Baseado em Chromium |
| Bloco de Notas, Explorer, Calculadora | UIA_PRIMARY | UIA é confiável em Win32 nativo |
| Desconhecido | HYBRID | Tenta UIA, fallback OCR |

### Cost Budget (teto de gastos)

- Acumula gasto diário com LLM em JSON persistente
- Se `MAX_DAILY_LLM_BUDGET` for excedido, retorna resposta vazia com `model_used="budget_exceeded"`
- Cache é consultado antes do budget (não gasta se já tem resposta)
- Overrides HIGH/CRITICAL disparam auto-flush para salvar instantaneamente

### Modelos de LLM (nuvem)

Três modelos em cascata com timeout configurável:

| Modelo | Uso | Custo |
|--------|-----|-------|
| Owl Alpha (padrão) | Planejamento, contexto grande | Grátis |
| Claude Haiku (fallback rápido) | Tarefas simples | Baixo |
| Claude Sonnet (fallback preciso) | Dados sensíveis, reparo | Alto |

### Modelo local (Ollama)

| Modelo | Uso |
|--------|-----|
| qwen2.5:7b | **Padrão local** (4.7 GB, FP16), planejamento de qualidade para tarefas web |
| qwen2.5:3b | Alternativa leve, 1.9 GB |
| qwen2.5-coder:3b | Tarefas de código |
| llama3.2:3b | Alternativa |

### Cache de Planos (HTN)

Planejamento com cache-first reduz chamadas LLM em 70-90% para tarefas repetitivas. O cache é:

- **Persistente**: SQLite em `data/htn_cache.db`
- **Autolimpante**: entradas expiram após TTL (padrão 24h)
- **Tolerante a falhas**: invalidação automática em falhas terminais de execução
- **Transparente**: cache HIT vs MISS é logado para debug

## Testes

```bash
# Diagnóstico rápido
python scripts\diagnose_local_first.py

# Todos os testes (356+ testes)
pytest tests/ -v

# Unitários apenas
pytest tests/unit/ -v

# Com cobertura
pytest tests/ --cov=src -v
```

## Estrutura de diretórios

```
scripts/
├── diagnose_local_first.py    # Diagnóstico do ambiente
├── setup_local_first.bat      # Setup automatizado
├── test_sandbox.py            # Teste sandbox local PJe (dropdown)
├── smoke_test_pje.py          # Smoke test multi-tribunal PJe (produção)
src/
├── main.py                    # Entry point (dashboard → CLI fallback)
├── main_cli.py                # Modo CLI puro
├── core/
│   ├── config.py              # Settings (Pydantic) com env vars
│   ├── health.py              # HealthChecker
│   ├── logging.py             # Loguru setup
│   ├── main_loop.py           # JarvisMainLoop (task queue assíncrona)
│   └── orchestrator.py        # JarvisOrchestrator
├── cli/
│   └── dashboard.py           # Dashboard terminal (Textual)
├── perception/
│   ├── screen_capture.py      # MSS + asyncio to_thread
│   ├── ocr.py                 # Tesseract + fallback
│   ├── ui_detector.py         # OpenCV contours (buttons, inputs)
│   ├── uia_wrapper.py         # Windows Accessibility API wrapper
│   └── window_classifier.py   # Roteamento UIA vs OCR por tipo de janela
├── execution/
│   ├── action_executor.py     # Click, type, hotkey, scroll + debounce + context locking
│   ├── atomic_action.py       # Rollback atômico
│   └── composite_actions.py   # Macros
├── memory/
│   ├── db_manager.py          # aiosqlite
│   ├── episode_repository.py
│   ├── memory.py              # MemorySystem
│   └── models.py              # Episode, ActionRecord
├── integration/
│   ├── models.py              # LLMRequest/Response
│   ├── openrouter_client.py   # HTTP + retry + fallback + budget
│   ├── ollama_client.py       # HTTP para Ollama local
│   ├── hybrid_client.py       # Roteamento local-first
│   ├── model_router.py        # Roteamento por sensibilidade
│   ├── llm_cache.py           # SQLite + TTL
│   ├── cost_budget.py         # Teto de gastos diário com persistência
│   └── browser_manager.py     # Playwright lifecycle + fallbacks
├── governance/
│   ├── models.py              # RiskLevel, PolicyDecision, RiskAssessment
│   ├── sensitive_detector.py  # Regex + OCR para dados sensíveis
│   ├── risk_rules.py          # Classificação de ações por keywords
│   ├── policy_engine.py       # Tomada de decisão + integração com calibração
│   ├── calibration_models.py  # CalibrationSignal
│   ├── calibration_loop.py    # (legado) Gradiente descendente
│   └── simple_calibration.py  # Calibração determinística com decaimento temporal
├── planning/
│   ├── models.py              # Task, Plan, TaskStatus, RepairStrategy
│   ├── htn_cache.py           # Cache SQLite persistente de planos
│   ├── htn_decomposer.py      # Decomposição hierárquica (HTN) com cache-first
│   ├── plan_executor.py       # Execução passo a passo + classificação de falhas
│   ├── repair_engine.py       # Retry + fallback + escalonamento LLM
│   └── validator.py           # Pós-condição (UIA primário, OCR fallback)
├── utils/
│   └── latency_tracker.py     # Tracker de latência assíncrono com relatório JSON
├── approval.py                # ApprovalHandler (dashboard interactivo)
└── ...
examples/
├── pje_sandbox.html            # Sandbox local para testes de dropdown web
├── demo_policy.py              # Demonstração do policy engine
├── demo_planner.py             # Demonstração do HTN planner
├── demo_full_system.py         # Sistema completo
└── demo_llm.py                 # Integração LLM

tests/
├── unit/                       # 280+ testes unitários
├── integration/                # 70+ testes de integração
└── conftest.py

## Manutenção e Qualidade (ECC)

O código segue padrões ECC (Erlang/OTP-style Clean Code):

- **Zero silent exception swallows**: todo `except` loga com `logger.warning()`/`logger.exception()` e `exc_info=True`
- **Funções <50 linhas**: extração de métodos mantém foco e testabilidade
- **Validação nas fronteiras**: input validation em `_dispatch()` com required_params, params ausentes logados
- **RaceConditionError** tratado em double_click/right_click com mesmo padrão do click
```

## Fluxo de Decisão (Pipeline)

```
Tarefa recebida
    │
    ▼
HTNDecomposer ────► Cache SQLite (cache-first)
    │
    ├── Cache HIT (hash SHA256, TTL 24h) → plano imediato (<10ms)
    └── Cache MISS → LLM (local/nuvem) → armazena no cache
    │
    ▼
PolicyEngine ────► RiskRules (keywords) ────► SensitiveDataDetector (regex)
    │
    ├── BLOCK    → Log + aborta
    ├── CONFIRM  → Pergunta usuário → se negado, registra override
    └── ALLOW    → Prossegue
    │
    ▼
SimpleCalibration ────► Conta overrides ────► Decaimento temporal
    │                                           │
    │                                           ▼
    │                                    Se ≥ threshold: demote risk
    │                                    Se HIGH/CRITICAL: auto-flush
    ▼
ActionExecutor
    │
    ├── Ações desktop: UIA click_element → debounce → context lock (HWND) → click
    │                   PyAutoGUI click: validate_coords → to_thread → timeout
    │
    ├── Ações web (Playwright): browser.launch → navigate → click/type/select
    │                   Fallback: fill → type → primeiro input visível
    │                   Dropdown: select → fuzzy JS (acentos)
    │
    └── type_text: to_thread → pyautogui.write
    │
    ▼
Validação de falha e sessão:
    ├── Falha terminal + sessão saudável → invalida cache → retry (regenera plano)
    ├── Falha terminal + sessão comprometida → aborta retry, escala erro
    ├── Falha recuperável (rede, temporário) → cache preservado → contínua
    └── Ação crítica (delete, remove) → invalida cache → aborta
    │
    ▼
Validator ────► WindowClassifier ────► UIA_PRIMARY | OCR_PRIMARY | HYBRID
    │
    ▼
RepairEngine (se falhou) ────► RETRY → ALTERNATIVE → ESCALATE_LLM → ASK_USER
```
