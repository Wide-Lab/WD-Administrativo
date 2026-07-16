"""Superfície de notificação do `core`. É daqui que um módulo dispara e-mail, sem conhecer o
provedor."""

from src.core.notifications.email import (
    EmailMessage,
    EmailSender,
    EmailSenderDep,
    LoggingEmailSender,
    get_email_sender,
)

__all__ = [
    "EmailMessage",
    "EmailSender",
    "EmailSenderDep",
    "LoggingEmailSender",
    "get_email_sender",
]
