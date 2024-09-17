import jwt
import logging
from flask_httpauth import HTTPTokenAuth, MultiAuth
from jwt.exceptions import InvalidSignatureError, ExpiredSignatureError, DecodeError
from src import app

logger = logging.getLogger(__name__)
### Настройки авторизации по токену
token_auth = HTTPTokenAuth()
multi_auth = MultiAuth(
    token_auth,
)


@token_auth.verify_token
def verify_token(token):
    try:
        error_message = ""
        data = {}
        data = jwt.decode(
            token,
            app.config.SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_signature": app.config.JWT_VERIFY_SIGNATURE},
        )
    except InvalidSignatureError:
        error_message = "Invalid signature."
    except ExpiredSignatureError:
        error_message = "message", "Token has expired."
    except DecodeError:
        error_message = "Token could not be decoded."
    except Exception as ex:
        error_message = "message", f"{ex}"
    result = {
        "ogrn": data.get("ogrn"),
        "inn": data.get("inn"),
        "token": token,
        "error": error_message,
    }
    return result


#######################################################################################################
