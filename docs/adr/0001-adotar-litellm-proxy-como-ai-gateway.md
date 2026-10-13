# 0001. Adotar o LiteLLM Proxy self-hosted como AI Gateway entre a aplicação e os providers

- Status: aceita
- Data: 2026-10-13
- Nível: solução

## Contexto

Na `v1-coupled`, cada feature chama o SDK do provider direto (`app/helpdesk/llm.py`), com o nome do modelo físico e as chaves na aplicação (`config.py`, `env_file: .env`). O diagnóstico mediu o custo disso: trocar o modelo de uma feature exigiu rebuild e recriação do container (dor 4); com um provider fora, as features presas a ele param (dor 3); e os retries/timeouts padrão dos SDKs (2 retries, 600 s) geraram chamadas zumbis minutos depois do 504 da borda. Na métrica, `llm` (D 0,80) e `config` (D 1,00) estão na zona de dor: concretos, voláteis e importados por todas as features.

O requisito 5 pede um gateway **self-hosted**, rodando como serviço `gateway` no compose, com capacidades lógicas, credenciais fora da aplicação, troca de modelo por configuração, governança (orçamento e limite por chave) e resiliência (timeout, retry, fallback). O avaliador sobe tudo localmente, sem serviços externos.

## Opções consideradas

1. **LiteLLM Proxy** (`ghcr.io/berriai/litellm`), imagem pública, configuração em YAML.
2. Outro gateway open source (ex.: Portkey Gateway OSS, Envoy AI Gateway).
3. Um gateway próprio (FastAPI) traduzindo para os dois providers.
4. Gateway SaaS (proibido pelo enunciado).

## Decisão

Opção 1, na versão `v1.102.1` (pinada; é a testada pelo `provider-fake/README.md`). Ela entrega nativamente o que o requisito 5 pede: nomes lógicos (`model_name`) mapeados para modelos físicos de providers diferentes, API única compatível com OpenAI para a aplicação, chaves virtuais com `max_budget`/`rpm_limit`, `num_retries`/`timeout`/`fallbacks` por capacidade, e o preço por token configurável. A opção 3 reimplementaria tudo isso (e seria código nosso para manter); a 2 exigiria mais peças para o mesmo efeito.

**Posição:** entre a aplicação e os providers, dentro da rede do compose. O `app` fala só com `http://gateway:4000` usando a sua chave virtual; o gateway é o único serviço que conhece os providers, os modelos físicos e as chaves `FAKE_*`. A porta 4000 é publicada só em `127.0.0.1` do host, apenas para o roteiro de governança e para inspeção.

## Consequências

- Melhor: trocar o modelo de uma capacidade vira edição de `gateway/config.yaml` + `docker compose restart gateway`; credenciais, custo e resiliência ficam num lugar só; a aplicação usa um único cliente (SDK `openai`) em `adapters/gateway.py`.
- Pior: mais uma peça no caminho crítico (se o gateway cai, todas as features caem); chaves virtuais e gasto exigem um Postgres (ADR 0003); a imagem é grande (~1,6 GB) e a subida aplica ~170 migrações (~25 s neste host).
- Passa a ser necessário vigiar: retries configurados em mais de um lugar (o app usa `max_retries=0`), e a tradução Messages → Chat Completions (verificada na F05: mesma saída e mesmos tokens que a v1).

## Evidência

```bash
docker compose ps gateway                         # healthy
grep -rE "gpt-fake|claude-fake" app/              # vazio
curl -s -X POST localhost:8090/admin/reset; <F1 pela borda>; curl -s "localhost:8090/admin/calls?last=1"
docker compose logs gateway | grep "POST /chat/completions"   # o SDK openai usa base_url + /chat/completions
```

Reexecutado na F08 ([saída](../evidence/f08/adr-evidence.txt)): gateway e `gateway-db` saudáveis, nenhum nome físico em `app/`, F1 pela borda registrada em `/admin/calls` como `openai/gpt-fake-large` e `POST /chat/completions` nos logs do gateway.
