# Conferência manual da métrica na v1-coupled (F03)

Régua do requisito 3 aplicada à mão sobre `app/helpdesk/` da tag `v1-coupled` (idêntico ao repositório base), para três módulos, comparada com `metrics/results/v1-coupled.csv`.

## `config`

- Imports de `config.py`: só `os` (biblioteca padrão), então **Ce = 0**.
- Quem importa `config`: `llm` (`from . import config`), `classification`, `suggestion`, `extraction`, `report` (`from . import config, llm…`) e `tickets` (`from . import config`), então **Ca = 6**.
- I = 0 / (0 + 6) = **0**; classes: nenhuma, então **A = 0**; D = |0 + 0 − 1| = **1**.
- CSV: `config,6,0,0.00,0.00,1.00` ✔. Zona de dor (A < 0,5, I < 0,5, D ≥ 0,5).

## `llm`

- Imports: `json` (padrão), `anthropic`, `openai` (externas), `from . import config` (componente), então **Ce = 1**.
- Quem importa `llm`: `classification`, `suggestion`, `extraction`, `report`, então **Ca = 4**.
- I = 1 / (1 + 4) = **0,2**; sem classes, então **A = 0**; D = |0 + 0,2 − 1| = **0,8**.
- CSV: `llm,4,1,0.20,0.00,0.80` ✔. Zona de dor.

## `report`

- Imports: `fastapi` (externa), `from . import config, llm, tickets` (3 componentes), `from .schemas import …` (componente `schemas`), então **Ce = 4**.
- Quem importa `report`: `main` (`from . import classification, extraction, report, suggestion`), então **Ca = 1**.
- I = 4 / (4 + 1) = **0,8**; sem classes, então **A = 0**; D = |0 + 0,8 − 1| = **0,2**.
- CSV: `report,1,4,0.80,0.00,0.20` ✔.

## Observação sobre `schemas`

`schemas.py` define 7 classes (`TicketInput`, `Classification`, `ReplySuggestion`, `OrderData`, `PeriodInput`, `Topic`, `TopicsReport`), todas herdando de `pydantic.BaseModel`, nenhuma de `Protocol`/`ABC`, então A = 0/7 = 0. Ce = 0 e Ca = 5 (`main` e as quatro features), então I = 0 e D = 1. É candidato a "estável por natureza" (tipos de valor do contrato), decisão do ADR da métrica.
