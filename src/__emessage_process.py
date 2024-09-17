import os
import logging
import imaplib
import email, warnings
import datetime
import re
import concurrent.futures
from pathlib import Path
from email.header import decode_header
from flask_restful import abort
from typing import Tuple, List, Any
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from multiprocessing import Manager
from .settings import *
from .result import Result
from .helpers import (
    get_name_template,
    write_contents,
    make_archive,
    decode_quoted_printable,
)
from src import app
from .exceptions import *

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)
logger = logging.getLogger(__name__)

manager = Manager()
man_dict: dict = manager.dict()
man_dict.imap = {}


def connect():
    try:
        imap = imaplib.IMAP4_SSL(
            host=app.config.IMAP_SERVER.host,
            port=app.config.IMAP_SERVER.port,
            timeout=30,
        )
        imap.login(app.config.IMAP_SERVER.user, app.config.IMAP_SERVER.password)
        imap.select("Inbox")
        return imap
    except Exception as ex:
        logger.error(f"{ex}")
        raise ConnectionErrorException(ex)


def get_imap():
    try:
        imap = man_dict.imap[str(os.getpid())]
    except AttributeError:
        imap = man_dict.imap[str(os.getpid())] = connect()
    except KeyError:
        imap = man_dict.imap[str(os.getpid())] = connect()
    return imap


def disconnect():
    imap = get_imap()
    imap.close()
    imap.logout()


def get_message(id: bytes):
    try:
        imap = get_imap()
        status = ""
        status, data = imap.uid("fetch", id.decode(), "(RFC822)")
    except Exception as ex:
        logger.error(f"{ex}")
    if status == "OK":
        try:
            if len(data) > 1:
                return email.message_from_bytes(data[0][1])
            else:
                return None
        except Exception as ex:
            logger.error(f"{ex}")
    return None


def search_messages(criteria) -> Any:
    """Поиск писем не ранее 1 года
    по вхождению строки (criteria) в заголовке и теле письма
    если критерий поиска несколько, то ищется по любому их них
    """
    imap = get_imap()
    status = ""
    date_begin = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime(
        "%d-%b-%Y"
    )
    args = []
    args.append("SENTSINCE")
    args.append(date_begin)
    if len(criteria.split(",")) > 1:
        args.append("OR")
    for cr in criteria.split(","):
        args.append("TEXT")
        args.append(cr)
    try:
        status, data = imap.uid(
            "search", "charset", "utf-8", " ".join(args).encode("utf-8")
        )
    except Exception as ex:
        logger.error(f"{ex}")
        status = "FAIL"
    if status == "OK":
        return data
    else:
        return None


def get_message_data(id: bytes, criteria: str = ""):
    msg = get_message(id=id)
    if msg:
        result = Result(criteria=criteria)
        result.criteria = criteria
        result.id = id
        result.sender = get_email_from_message(msg)
        result.subject = get_subject(msg)
        result.body, result.files = get_body(msg)
        if result.files:
            return result
    return None


# --------------------------------------------------------------------------
def get_subject(msg) -> str:
    try:
        subject = ""
        if msg["Subject"] is not None:
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()
    except Exception as ex:
        logger.warning(f"{ex}")
    finally:
        return subject


def get_date_from_message(msg):
    return email.utils.parsedate_tz(msg["Date"]) if msg else None


def get_email_from_message(msg):
    return msg["Return-path"] if msg else None


def get_sender(msg) -> Tuple[str, str]:
    dc = decode_header(msg["From"])
    if dc[0][1] is None:
        return "", dc[0][0]
    else:
        return dc[0][0].decode(), dc[0][1]


def get_body_text(part) -> str:
    encode = get_Transfer_Encoding(part)
    payload = part.get_payload()
    if encode == "base64":
        contents = email.base64mime.decode(payload)
    elif encode == "quoted-printable":
        contents = decode_quoted_printable(payload)
    else:
        contents = payload
    soup = BeautifulSoup(contents, "html.parser")
    text = re.sub(r"(\n)+", r"\n", soup.text)
    return text


def get_file_name(part):
    try:
        filename = decode_header(part.get_filename())[0][0]
        if isinstance(filename, bytes):
            filename = filename.decode()
    except Exception as ex:
        logger.error(f"{ex}")
    return filename


def get_Transfer_Encoding(part):
    data = [x for x in part.items() if x[0] == "Content-Transfer-Encoding"]
    return data[0][1] if data else ""


def get_body(msg) -> Tuple[str, list]:
    text = ""
    files = []
    for part in msg.walk():
        if part.get_content_maintype() == "text":
            text = get_body_text(part)
        elif part.get_content_disposition() == "attachment":
            filename = get_file_name(part)
            if filename:
                files.append({"id": Result.hashit(filename), "name": filename})
    return text, files


def extract_attachments(msg, att_ids) -> str:
    """Формируем файлы вложения для скачивания из письма
    если att_ids="0", то выбираются все файлы
    Возвращаем путь к файлу"""
    files = []
    filename = None
    path = Path(
        Path(__file__).resolve().parent.parent,
        get_name_template(app.config.OUTPUT_DIR),
    )
    path.mkdir(parents=True, exist_ok=True)

    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            filename = get_file_name(part)
            contents = part.get_payload(decode=True)
            if not filename in files:
                if (not att_ids or att_ids == "0") or Result.hashit(
                    filename
                ) in att_ids:
                    files.append(filename)
                    write_contents(Path(path, filename), contents)
    if files:
        if len(files) > 1:
            filename = make_archive(path, files)
        else:
            filename = Path(path, files[0])

    return str(filename)


# --------------------------------------------------------------------------
def fetch_messages(criteria: str):
    results = []
    clear_manager()
    data = search_messages(criteria)
    if data:
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
            future_to_url = {
                executor.submit(get_message_data, id, criteria): id
                for id in data[0].split()
            }

            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as ex:
                    results.append(Result(error_message=f"{ex}"))

    disconnect()
    return [x for x in results if x] if results else []


def fetch_message(id: bytes):
    clear_manager()
    result = get_message_data(id)
    disconnect()
    return [result]


def fetch_attachments(id: str, att_id: str = ""):
    clear_manager()
    msg = get_message(id)
    disconnect()
    if msg:
        return extract_attachments(msg, att_id)
    return None


def clear_manager():
    try:
        keys = []
        for key in man_dict.imap:
            keys.append(key)
        for key in keys:
            man_dict.imap.pop(key)
    except:
        pass


if __name__ == "__main__":
    pass
