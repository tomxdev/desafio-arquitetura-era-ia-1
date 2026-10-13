"""Casos da suíte de caracterização (Feathers): o comportamento observado da v1-coupled.

Cada caso é uma requisição HTTP pela borda e um golden em golden/<nome>.json, com o status, o
Content-Type e o corpo inteiro gravados da aplicação recebida (ver record_golden.py). Os casos de
sucesso dependem do provider simulado em modo normal (saída determinística) e de um modelo large
por trás de cada feature; os casos de erro de entrada não chegam ao provider.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Case:
    name: str
    feature: str
    path: str
    body: dict | None = None
    raw: str | None = None  # corpo enviado sem serialização (ex.: JSON inválido)
    tags: tuple[str, ...] = field(default_factory=tuple)


TK_00042 = {"ticket_id": "TK-00042", "text": "Meu pedido #481516 não chegou e já passou do prazo, urgente"}
TK_00002 = {"ticket_id": "TK-00002", "text": "Tenho aqui a nota fiscal 530720. O produto veio quebrado na caixa, "
            "pedido #605065. Sou cliente da loja há bastante tempo. Fico no aguardo de uma solução."}
TK_00031 = {"ticket_id": "TK-00031", "text": "Paguei o boleto de o edredom casal e o pagamento não foi confirmado. "
            "Sou cliente da loja há bastante tempo. Obrigado desde já. Prefiro contato por e-mail."}
TK_00003 = {"ticket_id": "TK-00003", "text": "Vocês têm loja física na minha cidade? Referente ao pedido #117367. "
            "Moro em Campinas, caso ajude. Prefiro contato por e-mail. Obrigado desde já. Fico no aguardo de uma solução."}
TK_SEM_PEDIDO = {"ticket_id": "TK-00100", "text": "Gostaria de saber o horário de atendimento da loja"}

CLASSIFICATION = "/tickets/classification"
SUGGESTION = "/tickets/reply-suggestion"
REPORT = "/reports/topics"
EXTRACTION = "/tickets/extraction"

CASES = [
    # F1 Classificar ticket
    Case("f1_ok_delivery_tk00042", "f1", CLASSIFICATION, TK_00042, tags=("ok",)),
    Case("f1_ok_defeito_tk00002", "f1", CLASSIFICATION, TK_00002, tags=("ok",)),
    Case("f1_ok_pagamento_tk00031", "f1", CLASSIFICATION, TK_00031, tags=("ok",)),
    Case("f1_erro_sem_text", "f1", CLASSIFICATION, {"ticket_id": "TK-00042"}, tags=("erro",)),
    Case("f1_erro_json_invalido", "f1", CLASSIFICATION, raw="isto não é json", tags=("erro",)),
    # F2 Sugerir resposta
    Case("f2_ok_tk00042", "f2", SUGGESTION, TK_00042, tags=("ok",)),
    Case("f2_erro_text_vazio", "f2", SUGGESTION, {"ticket_id": "TK-00042", "text": ""}, tags=("erro",)),
    # F3 Relatório de temas (um dia: 137 tickets, um lote, ~10 s pela borda; o mês inteiro dá 504 na v1)
    Case("f3_ok_um_dia", "f3", REPORT, {"start": "2026-08-01", "end": "2026-08-01"}, tags=("ok",)),
    Case("f3_erro_inicio_depois_do_fim", "f3", REPORT, {"start": "2026-08-31", "end": "2026-08-01"}, tags=("erro",)),
    Case("f3_erro_data_invalida", "f3", REPORT, {"start": "2026-02-30", "end": "2026-08-01"}, tags=("erro",)),
    Case("f3_erro_sem_end", "f3", REPORT, {"start": "2026-08-01"}, tags=("erro",)),
    # F4 Extrair dados do pedido
    Case("f4_ok_pedido_tk00042", "f4", EXTRACTION, TK_00042, tags=("ok",)),
    Case("f4_ok_nota_fiscal_e_pedido_tk00002", "f4", EXTRACTION, TK_00002, tags=("ok",)),
    Case("f4_ok_produto_tk00031", "f4", EXTRACTION, TK_00031, tags=("ok",)),
    Case("f4_ok_pedido_sem_produto_tk00003", "f4", EXTRACTION, TK_00003, tags=("ok",)),
    Case("f4_ok_sem_pedido", "f4", EXTRACTION, TK_SEM_PEDIDO, tags=("ok",)),
    Case("f4_erro_sem_ticket_id", "f4", EXTRACTION, {"text": "Meu pedido #481516 não chegou"}, tags=("erro",)),
]


def by_feature(feature: str) -> list[Case]:
    return [case for case in CASES if case.feature == feature]
