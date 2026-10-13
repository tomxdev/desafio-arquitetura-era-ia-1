# 0009. Concentrar timeout, retry e fallback no gateway; o app só tem timeout e falha explícita

- Status: aceita
- Data: 2026-10-13
- Nível: software

## Contexto

Na v1, os SDKs `openai` e `anthropic` usam por padrão **2 retries** e **600 s** de timeout de leitura (`docs/evidence/f01/sdk-defaults.txt`), contra os **30 s** da borda. O diagnóstico mostrou os dois efeitos: cada requisição com o provider em `error_500` gerou 3 chamadas, e com o provider em `timeout` o retry do SDK chamou o provider de novo ~5 min depois de a borda devolver 504 (requisição zumbi). Retries configurados em mais de um lugar (SDK, gateway, aplicação) se multiplicam. O requisito 5 pede timeout explícito, retry limitado com backoff para falhas transitórias e fallback técnico, com o número máximo de tentativas por destino declarado.

## Opções consideradas

1. Tudo na aplicação (retry e fallback em `adapters/gateway.py`).
2. Tudo no gateway; a aplicação só com timeout e sem retry.
3. Retry nos dois lugares.

## Decisão

Opção 2. O gateway conhece os destinos físicos e os tipos de erro de cada provider; a aplicação só conhece a capacidade.

| Mecanismo | Onde | Configuração |
|---|---|---|
| Timeout por tentativa | gateway, por deployment (`litellm_params.timeout`) | 4 s em classify/extract (o `large` responde em ~1,1 s); 30 s em suggest/topics (~16 s e ~10 s por chamada) |
| Retry | gateway (`router_settings.retry_policy`) | **1 retry** só para falhas transitórias (500, 503, 429); **0** para timeout (o próximo destino é mais útil do que esperar de novo o mesmo), 400/401/404 |
| Backoff | gateway (LiteLLM) | espera crescente entre a tentativa e o retry (observado: ~0,8 s; antes do fallback, ~1,5 s) |
| Fallback | gateway (`router_settings.fallbacks`) | ADR 0006 |
| Cooldown | desligado (`disable_cooldowns: true`) | cada requisição tenta o primário: o número de tentativas é determinístico e é o declarado (circuit breaker fora de escopo) |
| Retry no app | **nenhum** | `GatewayClient`: `max_retries=0` |
| Timeout no app | `adapters/gateway.py`, valores em `main.TIMEOUTS` | 12 s por chamada em F1/F2/F4 (abaixo dos 15 s exigidos; na F2, espera pelo 1º trecho e entre trechos) e 50 s por lote na F3 (a tarefa chega a `failed` em menos de 60 s) |
| Falha explícita | `adapters/gateway.py` + `main.py` | timeout, conexão ou erro do gateway viram `ports.CapabilityUnavailable` → `503 {"detail": "Capacidade <x> indisponível: <motivo>"}` |

**Máximo de tentativas por destino** (por chamada; a F3 faz uma chamada por lote):

| Destino | Falha transitória (500/503/429) | Timeout |
|---|---|---|
| Primário | 2 (1 + 1 retry) | 1 |
| Fallback técnico | 2 | 1 |
| Modelo fraco (F1, F2, F3) | 2 | 1 |

Observado no `/admin/calls` para os três destinos: com os dois providers inteiros em `error_500`, a F1 gera `gpt-fake-large:500 ×2`, `claude-fake-large:500 ×2`, `gpt-fake-mini:500 ×2` e responde `503` em 7,3 s ([evidência](../evidence/f06/all-down.txt)).

## Consequências

- Não há multiplicação: uma requisição da borda gera no máximo 2 + 2 + 2 = 6 chamadas ao provider (4 na F4), e o `/admin/calls` mostra exatamente essa sequência.
- Pior caso de latência das features síncronas curtas com os dois `large` travados: 4 s + 4 s + resposta do `mini`, abaixo dos 15 s.
- O gateway passa a ser o único lugar a ajustar quando a latência de um provider mudar.
- Limitação conhecida: um timeout do gateway não cancela a geração no provider (o provider simulado segura a conexão por 300 s); fora de escopo.

## Evidência

`bash scripts/verify/fallback.sh` ([saída](../evidence/f06/fallback.txt)): primário em `error_500` → `gpt-fake-large:500 gpt-fake-large:500 claude-fake-large:200`; `openai` em `timeout` → `gpt-fake-large:504` (1 tentativa, cortada em 4 s) seguida de `claude-fake-large:200`, F1 em 5,1 s pela borda.
