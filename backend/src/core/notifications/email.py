"""Porta de envio de e-mail.

A spec 06 manda o convite sair por uma porta em `core` e diz, com todas as letras, que o
**provedor concreto é detalhe de infra, não da spec**. Então aqui há a porta e uma
implementação que só registra em log: o convite é disparado de verdade pelo código de
negócio, e trocar o log por SES/SMTP é registrar outra fábrica, sem tocar no use case.

Diferente das outras portas do `core` (`UserReader`, `OrganizationReader`, …), esta **não é
implementada por um módulo** e por isso não ganha linha no `mount_routes`: e-mail é infra, não
tabela de ninguém. O default existe pra que o fluxo de convite funcione fim a fim em dev sem
um provedor configurado — o link sai no log."""

import logging
from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None: ...


class LoggingEmailSender:
    """O provedor de dev: escreve a mensagem no log em vez de mandar.

    Loga o corpo inteiro — inclusive o link com o token do convite —, e isso é aceitável
    exatamente enquanto o sender for este. Um provedor real não deve logar corpo."""

    async def send(self, message: EmailMessage) -> None:
        logger.info(
            "E-mail (sender de log, nada foi enviado) para %s — %s\n%s",
            message.to,
            message.subject,
            message.body,
        )


def get_email_sender() -> EmailSender:
    return LoggingEmailSender()


EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender)]
