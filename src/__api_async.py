# API при использовании ассинхроного модуля aioimaplib
import asyncio
import logging
from functools import lru_cache
from .__emessage_async import (
    fetch_messages_async,
    fetch_message_async,
    fetch_attachments_async,
)
from src import app
from .exceptions import *

logger = logging.getLogger(__name__)

@lru_cache(maxsize=32, typed=False)
def fetch_messages(**param):
    """Получить список писем по ИНН или ОГРН
    ИНН или ОГРН ищутся в теле и заголовке писем
    если задан идентификатор id возвращается письмо соответстующее
    этому идентификатору
    """
    try:
        id = param.get("id")
        if id:
            id = bytes(str(id), "utf-8")
            results = asyncio.run(fetch_message_async(id))
        else:
            search_text = param.get("inn") if param.get("inn") else ""
            search_text += "," if param.get("inn") and param.get("ogrn") else ""
            search_text += param.get("ogrn") if param.get("ogrn") else ""
            results = asyncio.run(fetch_messages_async(search_text))
        return results
    except ConnectionErrorException as ex:
        logger.error(f"{ex}")
    except Exception as ex:
        logger.error(f"{ex}")
    return "error"


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
                results = asyncio.run(fetch_attachments_async(id, attachments))
                return results
    except ConnectionErrorException as ex:
        logger.error(f"{ex}")
    except Exception as ex:
        logger.error(f"{ex}")
    return "error"


if __name__ == "__main__":
    pass
