from __future__ import annotations
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional, Union

from app.core.config import get_settings


def send_document_email(
    to: str,
    subject: str,
    body: str,
    attachment_path: Optional[Union[str, Path]] = None,
) -> None:
    """Envoie un email (devis/facture) via SMTP. Lève ValueError si SMTP n'est pas configuré."""
    settings = get_settings()
    if not settings.smtp_host:
        raise ValueError(
            "Envoi d'email non configuré : renseignez SMTP_HOST (et SMTP_USER / SMTP_PASSWORD "
            "si nécessaire) dans la configuration serveur."
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from or settings.smtp_user or "no-reply@auta-gestion.local"
    message["To"] = to
    message.set_content(body)

    if attachment_path is not None:
        path = Path(attachment_path)
        if path.is_file():
            data = path.read_bytes()
            subtype = "pdf" if path.suffix.lower() == ".pdf" else "octet-stream"
            message.add_attachment(data, maintype="application", subtype=subtype, filename=path.name)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_tls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)
