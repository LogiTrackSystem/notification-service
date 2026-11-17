"""Unitaria 1: events._resolver_canal elige el canal del cliente o el de por defecto."""
from app import events
from app.preferencias import configurar_preferencia


def test_resolver_canal_usa_la_preferencia_del_cliente():
    # Arrange
    configurar_preferencia("cliente-1", "en", "email")
    # Act / Assert
    assert events._resolver_canal("cliente-1", "push") == ("email", "en")
    assert events._resolver_canal("otro-cliente", "push") == ("push", "es")
