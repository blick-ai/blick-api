import os
from functools import lru_cache

import boto3
import httpx
from jose import JWTError, jwk, jwt

from domain.exceptions import (
    BlickAuthError,
    BlickInvalidCredentialsError,
    BlickUserAlreadyExistsError,
    BlickUserNotConfirmedError,
)
from domain.ports import IAuthService

COGNITO_REGION = os.getenv("COGNITO_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "us-east-1_Xqao8BA2H")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "24bc2a4d4ok7sp2hrsir5a09pt")
JWKS_URL = (
    f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
    f"{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
)


@lru_cache
def _fetch_jwks() -> dict:
    response = httpx.get(JWKS_URL, timeout=10)
    response.raise_for_status()
    return response.json()


class CognitoAuthService(IAuthService):
    def __init__(self):
        self._client = boto3.client("cognito-idp", region_name=COGNITO_REGION)
        self._jwks = _fetch_jwks()

    def verify_token(self, token: str) -> str:
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            key = None
            for k in self._jwks["keys"]:
                if k["kid"] == kid:
                    key = jwk.construct(k)
                    break
            if key is None:
                raise BlickAuthError("Chave pública não encontrada no JWKS")

            claims = jwt.decode(
                token,
                k,
                algorithms=["RS256"],
                audience=COGNITO_CLIENT_ID,
                issuer=f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}",
                options={"verify_aud": False},
            )
            return claims["sub"]
        except JWTError as e:
            raise BlickAuthError(f"Token inválido: {e}")

    def cadastrar(self, email: str, senha: str) -> None:
        try:
            self._client.sign_up(
                ClientId=COGNITO_CLIENT_ID,
                Username=email,
                Password=senha,
                UserAttributes=[{"Name": "email", "Value": email}],
            )
        except self._client.exceptions.UsernameExistsException:
            raise BlickUserAlreadyExistsError("Usuário já cadastrado")
        except self._client.exceptions.InvalidPasswordException as e:
            raise BlickAuthError(f"Senha inválida: {e}")
        except Exception as e:
            raise BlickAuthError(f"Erro ao cadastrar: {e}")

    def login(self, email: str, senha: str) -> dict:
        try:
            response = self._client.initiate_auth(
                ClientId=COGNITO_CLIENT_ID,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": email,
                    "PASSWORD": senha,
                },
            )
            result = response["AuthenticationResult"]
            return {
                "access_token": result["AccessToken"],
                "refresh_token": result.get("RefreshToken", ""),
                "id_token": result["IdToken"],
            }
        except self._client.exceptions.NotAuthorizedException:
            raise BlickInvalidCredentialsError("Email ou senha incorretos")
        except self._client.exceptions.UserNotConfirmedException:
            raise BlickUserNotConfirmedError("Usuário não confirmado")
        except Exception as e:
            raise BlickAuthError(f"Erro ao fazer login: {e}")

    def recuperar_senha(self, email: str) -> None:
        try:
            self._client.forgot_password(
                ClientId=COGNITO_CLIENT_ID,
                Username=email,
            )
        except Exception as e:
            raise BlickAuthError(f"Erro ao recuperar senha: {e}")

    def confirmar_cadastro(self, email: str, codigo: str) -> None:
        try:
            self._client.confirm_sign_up(
                ClientId=COGNITO_CLIENT_ID,
                Username=email,
                ConfirmationCode=codigo,
            )
        except self._client.exceptions.CodeMismatchException:
            raise BlickAuthError("Código de confirmação inválido")
        except self._client.exceptions.ExpiredCodeException:
            raise BlickAuthError("Código de confirmação expirado")
        except Exception as e:
            raise BlickAuthError(f"Erro ao confirmar cadastro: {e}")
