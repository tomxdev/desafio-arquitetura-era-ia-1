# 0003. Persistir chaves virtuais e gasto num Postgres dedicado ao gateway (`gateway-db`)

- Status: aceita
- Data: 2026-10-13
- Nível: solução

## Contexto

O requisito 5 exige que a aplicação use uma chave do próprio gateway (sem as chaves dos providers) e que haja pelo menos uma chave com orçamento e uma com limite de requisições, recusadas antes de chegar ao provider. No LiteLLM, chaves virtuais, orçamento e gasto por chave dependem de um banco (`DATABASE_URL`); sem banco, só existe a master key. A restrição do enunciado: todo serviço além de `app` e `gateway` precisa de um ADR que o justifique a partir de um requisito. A pista do enunciado também pede que as chaves sejam criadas sem passo manual.

## Opções consideradas

1. Postgres dedicado ao gateway, como serviço do compose.
2. Sem banco: a aplicação usa a master key do gateway.
3. Banco gerenciado externo (proibido: o avaliador só pode depender das imagens públicas do compose).

## Decisão

Opção 1: serviço `gateway-db` (`postgres:16-alpine`, volume nomeado `gateway-db`), visível só dentro da rede do compose, acessado apenas pelo `gateway`. A opção 2 daria à aplicação a credencial de administração do gateway (capaz de criar chaves e mudar orçamentos) e não permitiria orçamento nem limite por chave, ou seja, não atenderia ao requisito.

As chaves são criadas na subida por `gateway/seed_keys.py`, executado pelo `gateway/entrypoint.sh` depois que o proxy responde com o banco conectado: a chave do app (`HELPDESK_GATEWAY_KEY`, valor fixo de laboratório do `.env.example`) é criada com `/key/generate` se ainda não existir (idempotente). O healthcheck do gateway só passa depois disso, então `docker compose up -d --build --wait` continua sendo o único comando, e o `app` só sobe quando a sua chave já é válida. Optamos por semear dentro do próprio serviço `gateway` em vez de um serviço `gateway-init` separado, para não acrescentar mais uma peça ao compose.

## Consequências

- O gateway passa a depender do banco: sem `gateway-db` saudável ele não sobe (o compose ordena por `service_healthy`).
- A subida aplica ~170 migrações do Prisma no primeiro `up` (~25 s neste host); com o volume existente, é mais rápida.
- Os valores de chaves e senha são de laboratório, versionados no `.env.example` por exigência de reprodutibilidade (`cp .env.example .env` basta); num ambiente real viriam de um cofre.
- `docker compose down -v` apaga o volume (gasto e chaves); a próxima subida recria as chaves.

## Evidência

```bash
docker compose ps gateway-db gateway                        # healthy
docker compose logs gateway | grep "chave helpdesk-app"     # criada / já existe
curl -s localhost:4000/key/info?key=sk-helpdesk-app-0001 -H "Authorization: Bearer sk-litellm-master-0001"
```
