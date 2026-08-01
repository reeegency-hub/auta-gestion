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
    *,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None,
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

    data = attachment_bytes
    name = attachment_filename
    if data is None and attachment_path is not None:
        path = Path(attachment_path)
        if path.is_file():
            data = path.read_bytes()
            name = name or path.name
    if data is not None:
        filename = name or "document.pdf"
        subtype = "pdf" if filename.lower().endswith(".pdf") else "octet-stream"
        message.add_attachment(data, maintype="application", subtype=subtype, filename=filename)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_tls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)
