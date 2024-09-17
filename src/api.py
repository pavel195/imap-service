import logging
import requests
from functools import lru_cache
# from .emessage_process import (
#     fetch_messages as f_messages,
#     fetch_message as f_message,
#     fetch_attachments as f_attachments,
# )

from src.emessage_thread import (
    fetch_messages as f_messages,
    fetch_message as f_message,
    fetch_attachments as f_attachments,
)
from flask_api import status
from src.helpers import serialize
from src.result import Result
from src import app
from src.exceptions import *

logger = logging.getLogger(__name__)


# @lru_cache(maxsize=32, typed=False)
def fetch_messages(**param):
    """Получить список писем по ИНН или ОГРН
    ИНН или ОГРН ищутся в теле и заголовке писем
    если задан идентификатор id возвращается письмо
    соответстующее этому идентификатору
    """
    try:
        id = param.get("id")
        if id:
            id = bytes(str(id), "utf-8")
            results = f_message(id, param["path"])
        else:
            search_text = param.get("inn") if param.get("inn") else ""
            search_text += "," if param.get("inn") and param.get("ogrn") else ""
            search_text += param.get("ogrn") if param.get("ogrn") else ""
            results = f_messages(search_text, param["path"])
        return results
    except ConnectionErrorException as ex:
        return Result(error_message=f"{ex}")
    except Exception as ex:
        return Result(error_message=f"{ex}")


def fetch_attachments(**param):
    """Получить вложения письма по идентификатору письма id
    если задан иден.файла "attach" не равный "0", то возвращается
    файл соответствующий этому идентификатору
    """
    try:
        id = param.get("id")
        if id:
            id = bytes(str(id), "utf-8")
            attachments = param.get("attach")
            if attachments:
                results = f_attachments(id, param["path"], attachments)
                return results
    except ConnectionErrorException as ex:
        return Result(error_message=f"{ex}")
    except Exception as ex:
        return Result(error_message=f"{ex}")


if __name__ == "__main__":
    pass
