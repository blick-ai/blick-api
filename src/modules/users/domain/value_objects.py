"""
Value Objects do módulo Users.
"""

import re


class Email:
    """Value Object que valida e encapsula um endereço de e-mail."""

    EMAIL_REGEX = re.compile(
        r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    )

    def __init__(self, address: str):
        address = address.strip().lower()
        if not self.EMAIL_REGEX.match(address):
            raise ValueError(f"E-mail inválido: {address}")
        self._address = address

    @property
    def value(self) -> str:
        return self._address

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Email):
            return self._address == other._address
        return False

    def __hash__(self) -> int:
        return hash(self._address)

    def __str__(self) -> str:
        return self._address

    def __repr__(self) -> str:
        return f"Email('{self._address}')"


class FullName:
    """Value Object para nome completo com validação mínima."""

    def __init__(self, name: str):
        name = name.strip()
        if len(name) < 2:
            raise ValueError("Nome deve ter pelo menos 2 caracteres")
        self._name = name

    @property
    def value(self) -> str:
        return self._name

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"FullName('{self._name}')"
