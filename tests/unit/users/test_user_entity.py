"""
Testes unitários para a entidade User.
"""

from src.modules.users.domain.entities import User


class TestUserEntity:
    """Testes para a entidade User."""

    def test_create_user_with_defaults(self):
        user = User(full_name="João Silva", email="joao@test.com")
        assert user.full_name == "João Silva"
        assert user.email == "joao@test.com"
        assert user.role == "producer"
        assert user.is_active is True
        assert user.id is not None

    def test_validate_role_valid(self):
        user = User(
            full_name="Maria", email="maria@test.com", role="technician"
        )
        user.validate_role()  # não deve lançar exceção

    def test_validate_role_invalid(self):
        user = User(
            full_name="Carlos", email="carlos@test.com", role="hacker"
        )
        try:
            user.validate_role()
            assert False, "Deveria lançar ValueError"
        except ValueError:
            pass

    def test_deactivate_user(self):
        user = User(full_name="Ana", email="ana@test.com")
        assert user.is_active is True
        user.deactivate()
        assert user.is_active is False

    def test_activate_user(self):
        user = User(
            full_name="Ana", email="ana@test.com", is_active=False
        )
        user.activate()
        assert user.is_active is True

    def test_user_equality_by_id(self):
        user1 = User(full_name="A", email="a@test.com")
        user2 = User(full_name="B", email="b@test.com")
        assert user1 != user2

        # Mesmo ID → iguais
        user2.id = user1.id
        assert user1 == user2
