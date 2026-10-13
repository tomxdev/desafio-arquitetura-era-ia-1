from .ports import LLMGateway
from .schemas import ReplySuggestion, TicketInput

CAPABILITY = "helpdesk-suggest"


def suggest(ticket: TicketInput, gateway: LLMGateway) -> ReplySuggestion:
    text = gateway.complete(CAPABILITY, "suggest", ticket.text)
    return ReplySuggestion(ticket_id=ticket.ticket_id, suggestion=text)
