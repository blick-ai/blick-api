import boto3

from domain.ports import IUserLookupService


class CognitoUserLookupService(IUserLookupService):
    """
    Busca o e-mail de um usuario a partir do cliente_id (o "sub" do
    Cognito, ja usado como identificador em toda a API). Implementado
    como classe separada de proposito — o servico de autenticacao
    existente (login/cadastro) nao precisa saber nada sobre isso.
    """

    def __init__(self, user_pool_id: str, region: str):
        self._client = boto3.client("cognito-idp", region_name=region)
        self._user_pool_id = user_pool_id

    def obter_email(self, cliente_id: str) -> str | None:
        try:
            resposta = self._client.admin_get_user(
                UserPoolId=self._user_pool_id,
                Username=cliente_id,
            )
            for atributo in resposta.get("UserAttributes", []):
                if atributo["Name"] == "email":
                    return atributo["Value"]
        except Exception:
            # se nao conseguir achar o email por qualquer motivo (usuario
            # removido, erro de permissao, etc.), quem chama deve tratar
            # como "sem email disponivel" e seguir sem travar o resto
            pass
        return None
