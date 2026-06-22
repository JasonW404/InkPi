"""Mutation authentication helpers for the admin portal."""

from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class AdminAuthPolicy:
    """Token policy used to guard admin mutation routes."""

    token: str | None = None

    @classmethod
    def from_environment(cls) -> AdminAuthPolicy:
        token = os.getenv("INKPI_ADMIN_TOKEN", "").strip() or None
        return cls(token=token)

    @property
    def configured(self) -> bool:
        return bool(self.token)

    def validate_mutation(self, *, token: str | None, origin: str | None, host: str | None) -> None:
        if not self.token:
            raise AdminAuthError("admin token is not configured", status=503)
        if not token or not hmac.compare_digest(token, self.token):
            raise AdminAuthError("invalid admin token", status=401)
        if origin and host and not _same_origin_host(origin, host):
            raise AdminAuthError("cross-origin mutation rejected", status=403)


class AdminAuthError(ValueError):
    """Raised when an admin mutation request is not authorized."""

    def __init__(self, message: str, *, status: int) -> None:
        super().__init__(message)
        self.status = status


def extract_bearer_token(value: str | None) -> str | None:
    """Extract a bearer token from an Authorization header."""

    if not value:
        return None
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _same_origin_host(origin: str, host: str) -> bool:
    parsed = urlparse(origin)
    return bool(parsed.netloc) and parsed.netloc.lower() == host.lower()
