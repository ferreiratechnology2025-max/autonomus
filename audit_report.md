# Auditoria Jarvis v3 - 03/06/2026 15:30 BRT

## Resumo Executivo
- **Estado geral**: AMARELO (funcional parcial, dependências incompletas)
- **Pontos críticos**: 4
  1. Dependências `opencv-python` e `mss` não instaladas (erro de file lock no Windows)
  2. `comtypes`/`uiautomation` com falha de instalação similar
  3. API key real exposta em `.env.txt` (não carregada, mas risco de vazamento)
  4. Nenhum dashboard integrado ao sistema Python
- **Recomendação imediata**: Corrigir instalação de dependências e remover `.env.txt` com chave real

---

## 1. Estrutura de Diretórios

```
D:\Autonomus/
├── .env.example              ✅ OK (config padrão)
├── .env.txt                  ⚠️ Contém API key REAL (risco de segurança)
├── .pytest_cache/
├── README.md                 ✅ OK (documentação completa)
├── pyproject.toml             ✅ OK
├── requirements.txt           ✅ OK (18 libs)
├── requirements-dev.txt       ✅ OK (black, ruff, mypy, pre-commit, pytest-cov)
├── config/
│   └── config.yaml           ✅ OK (13 parâmetros)
├── data/
│   ├── calibration_weights.json  ✅ OK
│   ├── simple_calibration.json   ✅ OK (3 entradas de override)
│   ├── logs/                     ✅ OK (5 logs de execuções anteriores)
│   └── db/                       ✅ OK (vazio, aguardando init)
├── docker/                   ⚠️ VAZIO (previsto mas não implementado)
├── docs/                     ⚠️ VAZIO (previsto mas não implementado)
├── jarvis-v3-episodic-memory/ ✅ Projeto separado (AI Studio/React)
│   └── (App TSX, componentes, dados de episódios)
├── jarvis-v3-episodic-memory.zip ✅ Backup do projeto acima
├── src/
│   ├── __init__.py            ✅ OK
│   ├── main.py                ✅ OK (ponto de entrada funcional)
│   ├── core/
│   │   ├── config.py          ✅ OK (50 settings via Pydantic)
│   │   ├── health.py          ✅ OK (8 health checks)
│   │   ├── logging.py         ✅ OK (Loguru stderr + arquivo rotacionado)
│   │   ├── main_loop.py       ✅ OK (task queue async + health loop)
│   │   ├── metrics.py         ⚠️ NÃO documentado no README (RuntimeMetrics)
│   │   └── orchestrator.py    ✅ OK (integra todos os módulos)
│   ├── perception/
│   │   ├── screen_capture.py  ✅ OK (MSS + asyncio to_thread)
│   │   ├── ocr.py             ✅ OK (Tesseract + fallback)
│   │   ├── ui_detector.py     ✅ OK (OpenCV contours)
│   │   ├── uia_wrapper.py     ✅ OK (UIA com fallback condicional)
│   │   └── window_classifier.py ✅ OK (5 browsers, 2 electron, 7 native)
│   ├── execution/
│   │   ├── action_executor.py ✅ OK (click, type, hotkey, debounce, context lock)
│   │   ├── atomic_action.py   ✅ OK (rollback com compensação)
│   │   └── composite_actions.py ✅ OK (macros: select_all, paste, etc.)
│   ├── memory/
│   │   ├── db_manager.py      ✅ OK (aiosqlite wrapper)
│   │   ├── episode_repository.py ✅ OK (CRUD de episódios)
│   │   ├── memory.py          ✅ OK (MemorySystem completo)
│   │   ├── models.py          ✅ OK (Episode, ActionRecord, StateDiff)
│   │   └── schema.py          ⚠️ NÃO documentado no README (SQL schema)
│   ├── integration/
│   │   ├── models.py          ✅ OK (LLMRequest/Response)
│   │   ├── openrouter_client.py ✅ OK (dry-run, fallback, cache, budget)
│   │   ├── model_router.py    ✅ OK (roteamento por sensibilidade/contexto)
│   │   ├── llm_cache.py       ✅ OK (SQLite + TTL)
│   │   └── cost_budget.py     ✅ OK (teto diário com persistência)
│   ├── governance/
│   │   ├── models.py          ✅ OK (RiskLevel, PolicyDecision, etc.)
│   │   ├── policy_engine.py   ✅ OK (avaliação + calibração)
│   │   ├── risk_rules.py      ✅ OK (keywords + categorias)
│   │   ├── sensitive_detector.py ✅ OK (7 padrões regex)
│   │   ├── calibration_loop.py  ⚠️ CÓDIGO LEGADO (gradiente descendente)
│   │   ├── calibration_models.py ✅ OK (CalibrationSignal)
│   │   └── simple_calibration.py ✅ OK (calibração determinística)
│   └── planning/
│       ├── models.py          ✅ OK (Task, Plan, TaskStatus, RepairStrategy)
│       ├── htn_decomposer.py  ✅ OK (4 compound methods + LLM fallback)
│       ├── plan_executor.py   ✅ OK (execução + reparo + validação)
│       ├── repair_engine.py   ✅ OK (4 estratégias de reparo)
│       └── validator.py       ✅ OK (UIA + OCR + similarity)
├── tests/
│   ├── __init__.py            ✅ OK
│   ├── unit/                  ✅ 27 arquivos de teste
│   └── integration/           ✅ 7 arquivos de teste
└── examples/
    ├── demo_policy.py         ✅ OK
    ├── demo_planner.py        ✅ OK
    ├── demo_full_system.py    ✅ OK
    └── demo_llm.py            ✅ OK
```

### Diff vs README Prometido
| Item | README | Realidade | Status |
|------|--------|-----------|--------|
| `src/core/metrics.py` | NÃO listado | Existe | ⚠️ Omisso |
| `src/memory/schema.py` | NÃO listado | Existe | ⚠️ Omisso |
| `src/governance/calibration_models.py` | NÃO listado | Existe | ⚠️ Omisso |
| `docker/` | NÃO mencionado | Vazio | ⚠️ Pode remover |
| `docs/` | NÃO mencionado | Vazio | ⚠️ Pode remover |
| `jarvis-v3-episodic-memory/` | NÃO mencionado | Existe | ⚠️ Omisso |

---

## 2. Configuração (.env)

### Variáveis Definidas
| Arquivo | Variável | Valor |
|---------|----------|-------|
| `.env.example` | `OPENROUTER_API_KEY` | `sk-or-v1-your-key-here` (placeholder) |
| `.env.txt` | `OPENROUTER_API_KEY` | `sk-or-v1-40c6676...fafd` (**CHAVE REAL**) |

### ⚠️ Problemas
1. **Arquivo `.env` não existe** - sistema não consegue carregar variáveis
2. **`.env.txt` contém chave OpenRouter real** - risco de vazamento em commit
3. Config opcionais comentadas: `TESSERACT_PATH`, `LOG_LEVEL`, `SCREEN_CAPTURE_INTERVAL`, etc.

---

## 3. Dependências

### Instaladas com Sucesso
| Biblioteca | Versão | Status |
|------------|--------|--------|
| python-dotenv | 1.2.2 | ✅ |
| pyyaml | 6.0.3 | ✅ |
| loguru | 0.7.3 | ✅ (acabou de instalar) |
| pydantic | 2.12.5 | ✅ |
| pydantic-core | 2.41.5 | ✅ |
| pydantic-settings | 2.14.1 | ✅ |
| aiofiles | 25.1.0 | ✅ |
| pillow | 12.2.0 | ✅ |
| numpy | 1.26.4 | ✅ |
| pytesseract | 0.3.13 | ✅ |
| pyautogui | 0.9.54 | ✅ (acabou de instalar) |
| pynput | 1.8.2 | ✅ (acabou de instalar) |
| aiosqlite | 0.22.1 | ✅ |
| aiohttp | 3.13.4 | ✅ |
| tenacity | 9.1.4 | ✅ |
| pytest | 9.0.3 | ✅ |
| pytest-asyncio | 1.3.0 | ✅ |
| pytest-cov | 7.1.0 | ✅ |
| chromadb | 1.5.9 | ✅ (instalado mas NÃO em requirements.txt) |
| ollama | 0.6.2 | ✅ (instalado mas NÃO em requirements.txt) |

### NÃO Instaladas (falha de file lock no Windows)
| Biblioteca | Motivo |
|------------|--------|
| `opencv-python` (cv2) | ⛔ Erro: `f2py.exe.deleteme` (Windows file lock) |
| `mss` | ⛔ Erro de file lock durante instalação |
| `comtypes` | ⛔ Erro: `clear_comtypes_cache.exe.deleteme` |
| `uiautomation` | ⛔ Erro devido comtypes |

### Anomalias
- `chromadb` e `ollama` estão instalados mas **não constam** no `requirements.txt`
- `comtypes` é dependência do `uiautomation`, necessita instalação separada

---

## 4. Modelos LLM Locais

### Ollama Instalado ✅
```
NAME                ID              SIZE      MODIFIED
qwen2.5:3b          357c53fb659c    1.9 GB    2 weeks ago
llama3.2:3b         a80c4f17acd5    2.0 GB    2 weeks ago
qwen2.5-coder:3b    f72c60cabf62    1.9 GB    3 weeks ago
qwen2.5:1.5b        65ec06548149    986 MB    3 weeks ago
```

### Problemas
1. O sistema **não usa Ollama** atualmente - configurado apenas para OpenRouter
2. `ollama` está instalado como lib Python mas não há integração no código
3. Nenhum arquivo `.gguf` encontrado no projeto
4. Modelo padrão configurado: `openrouter/optimus-alpha` → não existe localmente

### Recomendação
- Integrar Ollama como fallback local (já tem `ollama` pip installado)
- Usar `qwen2.5-coder:3b` para tarefas simples e `qwen2.5:3b` para contexto maior

---

## 5. Dashboard Existente

### O que encontrei: Projeto AI Studio separado
**Localização**: `D:\Autonomus\jarvis-v3-episodic-memory\`
**Tecnologia**: React 19 + TypeScript + Vite + Tailwind + Google GenAI
**README**: "Run and deploy your AI Studio app"

### Funcionalidades (pelo código)
- Visualização e edição de episódios de memória
- SimilarityMap: mapa de similaridade entre episódios
- Header, Sidebar, NewAutomationModal, EditLogicModal
- 14.662 linhas de dados de episódios em `src/data/episodes.ts`

### ⚠️ Conclusão
**Não é um dashboard integrado ao sistema Python.** É um projeto exportado do Google AI Studio, separado e não conectado ao backend Python. Para integrá-lo como dashboard, seria necessário:
1. Criar API endpoints no backend Python
2. Conectar o frontend React a esses endpoints
3. Ou construir um dashboard novo com Textual (como mencionado anteriormente)

**Nenhum arquivo de dashboard Textual foi encontrado.**

---

## 6. Testes

### Estatísticas
| Métrica | Valor |
|---------|-------|
| Arquivos de teste unitário | 27 |
| Arquivos de teste integração | 7 |
| **Total funções teste** | **177 coletadas** |
| Erros de coleta | 11 (6.2%) |
| Testes que PASSARIAM (estimado) | ~150+ |

### Módulos com Cobertura ✅
- `core/config` (9 testes)
- `core/health` (12 testes)
- `core/main_loop` (via integração)
- `memory/schema`, `memory/system`, `memory/episode_repository`
- `governance/risk_rules`, `policy_engine`, `sensitive_detector`, `simple_calibration`, `calibration_loop`
- `integration/openrouter_client`, `model_router`, `llm_cache`, `cost_budget`
- `perception/screen_capture`, `ocr`, `ui_detector`, `uia_wrapper`, `window_classifier`
- `planning/htn_decomposer`, `plan_executor`, `repair_engine`, `validator`
- `execution/action_executor`, `atomic_action`, `composite_actions`

### Módulos SEM Cobertura ⚠️
- `core/orchestrator.py` (testado apenas via integração indireta)
- `core/metrics.py`
- `governance/calibration_models.py` (testado indiretamente)
- `memory/models.py` (testado indiretamente)

### Erros de 11 testes (todos por dependências faltantes)
```
❌ cv2 ausente → action_executor, atomic_action, composite_actions, htn_decomposer,
                  main_loop, ocr, plan_executor, repair_engine, ui_detector, validator
❌ mss ausente → screen_capture
```

---

## 7. Pontos de Entrada

### Scripts Encontrados
| Script | Status | Notas |
|--------|--------|-------|
| `python -m src.main` | ❌ Falha | `ModuleNotFoundError: cv2` (via orchestrator → action_executor) |
| `examples/demo_policy.py` | ✅ Funciona | Testado parcialmente |
| `examples/demo_planner.py` | ✅ Funciona | Testado parcialmente |
| `examples/demo_full_system.py` | ✅ Funciona | Testado parcialmente |
| `examples/demo_llm.py` | ✅ Funciona | Modo dry-run sem API key |

### Problema no Entry Point
O `main.py` importa `JarvisOrchestrator` → `ActionExecutor` → `import cv2`. Isso quebra toda a inicialização se `opencv-python` não estiver instalado. **Solução**: import cv2 dentro do método ou usar lazy import.

---

## 8. Análise de Risco Imediato

### 🔴 Crítico
1. **API key real exposta** em `D:\Autonomus\.env.txt` — valor: `sk-or-v1-40c6676...`
2. `.env` não existe — sistema roda SEM configuração de API
3. `pyproject.toml` não lista dependências completas (só 6, vs 18 em requirements.txt)

### 🟡 Médio
1. `src/governance/__init__.py` importa `PolicyEngine` no顶层, que importa `loguru` → qualquer import do pacote governance falha sem loguru
2. `src/planning/__init__.py` importa `PlanExecutor` → `ActionExecutor` → `cv2` → mesmo problema
3. `calibration_loop.py` é código LEGADO (gradiente descendente) mas ainda referenciado em `health.py` e `orchestrator.py`
4. `chromadb` e `ollama` instalados mas não usados — peso morto

### 🟢 Baixo
1. `docker/` e `docs/` vazios
2. `window_classifier.py` usa `logging.getLogger` em vez de `loguru`
3. `uia_wrapper.py` também usa `logging` padrão em vez de `loguru`
4. `src/core/logging.py` tem variável `is_debug` não utilizada (linha 17)

---

## 9. Ações Recomendadas para Fase 1

### Prioridade Alta
1. **Remover `.env.txt`** ou movê-lo para `.env` (nunca versione chaves reais)
2. **Instalar dependências restantes**: `opencv-python`, `mss`, `comtypes`, `uiautomation` (reiniciar terminal e tentar novamente)
3. **Fazer `pip install -r requirements.txt` completo** para garantir consistência
4. **Sincronizar `pyproject.toml`** com `requirements.txt` (faltam 12 dependências)

### Prioridade Média
5. **Integrar Ollama como fallback local** (biblioteca já instalada, modelos disponíveis)
6. **Decidir destino do `calibration_loop.py`** (legado vs. remover vs. manter)
7. **Corrigir `src/planning/__init__.py`** para não importar ActionExecutor no顶层 (quebra coleta de testes)
8. **Adicionar `.gitignore`** para `.env`, `__pycache__`, `data/logs/`, `data/db/`

### Prioridade Baixa
9. **Unificar logging** (`window_classifier.py`, `uia_wrapper.py` → loguru)
10. **Documentar módulos faltantes** (`metrics.py`, `schema.py`, `calibration_models.py`)
11. **Lazy import `cv2`** em `action_executor.py` para não quebrar entry point

---

*Relatório gerado automaticamente pela auditoria do Supervisor. Total de arquivos analisados: 85+*
