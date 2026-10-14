# 0007. Decidir o modo de execução de cada feature (F1–F4)

- Status: aceita
- Data: 2026-10-13
- Nível: solução

## Contexto

Na v1, as quatro features respondem de forma síncrona, com o resultado inteiro no corpo. O diagnóstico mediu o custo disso pela borda (`localhost:8000`, que corta com `504` depois de 30 s sem nenhum byte):

- o relatório do mês (F3) leva ~331 s (34 lotes sequenciais de ~9,7 s) e morre em `504` aos 30 s, enquanto o app segue pagando as chamadas (dor 1);
- a sugestão (F2) leva 15,96 s e o primeiro byte só chega no fim (dor 2);
- F1 e F4 levam ~1,1 s.

Uma chamada a LLM demora segundos, custa por token, chega aos poucos e prende conexões. A pergunta não é "qual modo adotar", e sim "qual modo para cada caso de uso", e cada modo tem custo: streaming muda a espera percebida, mas mantém a conexão aberta; o assíncrono libera a conexão, mas cobra estado e polling. Árvore de decisão aplicada a cada feature: **alguém está esperando agora? cabe no orçamento de latência? é consumível aos poucos?**

## Opções consideradas

1. Síncrono (com timeout explícito).
2. Streaming (SSE).
3. Asynchronous Request-Reply (`202` + status + `303`), com o estado em memória no app.
4. Assíncrono com fila e worker dedicados (serviços extras no compose).

## Decisão

### F1 Classificar ticket: **síncrono**, com timeout explícito
- **Alguém está esperando agora?** Sim: o cliente, na abertura do ticket, esperando a confirmação na tela.
- **Cabe no orçamento de latência?** Sim: saída curta, de valores fixos; o `large` responde em ~1,1 s pela borda (limite: 3 s).
- **É consumível aos poucos?** Não: `category` e `priority` só fazem sentido completos.
- Implementação: `POST /tickets/classification` → `200` com o JSON completo. Timeout por chamada ao gateway de **12 s** (`main.TIMEOUTS`), abaixo dos 15 s exigidos com o provider travado e dos 30 s da borda; sem destino disponível → `503` explícito.

### F2 Sugerir resposta: **streaming (SSE)**
- **Alguém está esperando agora?** Sim: o atendente, olhando a tela.
- **Cabe no orçamento de latência?** O texto inteiro, não: saída longa, ~16 s no `large` (dor 2). O primeiro trecho, sim: ~0,8 s até o primeiro token.
- **É consumível aos poucos?** Sim: o atendente começa a ler e a editar assim que o texto aparece.
- Implementação: `POST /tickets/reply-suggestion` → `200`, `Content-Type: text/event-stream`, eventos `data: {"chunk": "..."}` à medida que chegam do gateway, e `event: end` + `data: {"ticket_id"}` no fim. Falha **antes** do primeiro trecho (nenhum destino disponível) → `503` em JSON, pois o status ainda não saiu. Falha **no meio** (o `midstream_error` do provider) → `event: error` + `data: {"ticket_id", "message": "A geração foi interrompida"}` e o stream termina (o gateway não esconde a falha com fallback no meio do stream: verificado). Para nada no caminho acumular a resposta: o app envia `X-Accel-Buffering: no` (a borda, que não pode ser alterada, não desliga o buffer do nginx por conta própria) e `Cache-Control: no-cache`; o gateway repassa os trechos sem buffer (`stream_timeout: 5` por destino: espera máxima pelo 1º trecho e entre trechos, para cair no fallback antes dos 30 s da borda).

### F3 Relatório de temas: **Asynchronous Request-Reply**
- **Alguém está esperando agora?** Não: quem pede é um painel interno; "ninguém fica esperando olhando para ele". E o painel, no navegador, não expõe callback (webhook descartado).
- **Cabe no orçamento de latência?** Não: o mês inteiro são 34 lotes e ~5,5 min, 11 × a paciência da borda.
- **É consumível aos poucos?** Não: o relatório só vale agregado (contagens e exemplos somados entre os lotes).
- Implementação: `POST /reports/topics` → `202 Accepted` com `Location: /reports/topics/status/{id}` e `Retry-After: 5` (corpo: `{"job_id", "state": "pending"}`; o `422` de período inválido continua no próprio pedido). `GET /reports/topics/status/{id}` → `200 {"state": "pending" | "running", "progress": "n/total"}` ou `200 {"state": "failed", "reason": "..."}`, e `303 See Other` com `Location: /reports/topics/{id}` quando termina. `GET /reports/topics/{id}` → `200` com o relatório. A tarefa roda num pool de threads do próprio app (`report_jobs.TopicsJobs`), com o estado em memória: **sem fila nem worker** (opção 4 descartada: o requisito não pede sobreviver a reinício, e cada serviço a mais no compose exigiria operar e justificar mais uma peça). Para nunca ficar presa em `running`: cada lote tem timeout de **50 s** no app (o gateway já corta cada destino em 30 s), e qualquer falha do lote leva a tarefa a `failed` com o motivo.

### F4 Extrair dados do pedido: **síncrono estrito**, com timeout explícito
- **Alguém está esperando agora?** Sim: a automação de troca e devolução precisa do resultado para seguir.
- **Cabe no orçamento de latência?** Sim: saída curta, ~1,1 s.
- **É consumível aos poucos?** Não: `order_number` e `product` só podem ser usados completos e validados; um campo errado gera uma troca errada.
- Implementação: igual à F1 (timeout de 12 s, `503` explícito), e **sem fallback para modelo fraco** (ADR 0006): sem nenhum `large`, falha explicitamente em vez de entregar um dado possivelmente errado.

## Consequências

- Nenhuma feature depende mais de terminar em 30 s: F1/F4 terminam em ~1 s (ou em `503` em ≤ 12 s), F2 envia o primeiro byte em < 1 s, F3 responde o pedido em milissegundos.
- F2 mantém uma conexão aberta por ~16 s por sugestão (custo aceito: é o que dá ao atendente texto para ler já no primeiro segundo). Cancelar a geração quando o cliente fecha o stream está fora de escopo.
- F3 passa a ter estado: tarefas em memória (perdidas num reinício do app, fora de escopo), polling pelo cliente e dois endpoints novos. Pedidos repetidos para o mesmo período geram tarefas independentes (deduplicar está fora de escopo). Também não há limite para tarefas na fila nem para as concluídas guardadas em memória: com pedidos acima da vazão do pool (2 tarefas por vez), a fila e a memória crescem. É uma limitação aceita para o volume do helpdesk (um relatório por período, pedido por pessoas); limitar a fila (recusando com `429`/`503` antes do `202`) e expirar resultados é a evolução natural se a F3 virar API pública.
- O contrato HTTP de F2 e F3 mudou: a suíte de caracterização da `main` consome SSE e polling, e continua comparando o conteúdo com os goldens da `v1-coupled` (que permanecem iguais nas tags).

## Evidência

`bash scripts/verify/flows.sh` ([saída](../evidence/f07/flows.txt)) e `python -m pytest tests/contract -q`, pela borda:

| Critério | Observado |
|---|---|
| F1 em até 3 s | 5 execuções, 1,09–1,12 s |
| F2: 1º trecho em até 1,5 s e antes da metade do total (`curl -N`) | 1º trecho em 0,85 s; fim em 16,20 s; 606 trechos |
| F2 com o primário em `midstream_error` | 151 trechos, depois `event: error` com `{"ticket_id": "TK-00042", "message": "A geração foi interrompida"}` |
| F3 do mês aceito em até 1 s | `202` em 0,07 s, com `Location` e `Retry-After: 5` |
| F3 do mês completo | `303` → `200`, `total_tickets: 5000`, 34 chamadas `topics` 200 em `/admin/calls` |
| F3 com os dois providers em `error_500` | `failed` com `reason` em 7,7 s (limite: 60 s) |
| F1 com o primário em `timeout` | `200` via fallback em 5,1 s |
| Nenhum `504` da borda | nenhum status 504 em todo o roteiro |

Reexecutado na F08: [saída](../evidence/f08/flows.txt) (`RESULTADO: OK`): F1 1,09–1,12 s; F2 1º trecho em 0,86 s e fim em 16,28 s; F3 aceita em 0,07 s, mês com 5.000 tickets e 34 chamadas `topics`; `failed` em 7,74 s; nenhum `504`.
