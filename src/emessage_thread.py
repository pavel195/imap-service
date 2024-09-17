import os
import imaplib
import email, warnings, logging
import datetime
import re, threading
import concurrent.futures
from pathlib import Path
from email.header import decode_header
from typing import Tuple, List, Any
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from concurrent.futures import ThreadPoolExecutor
from email.mime.text import MIMEText
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

lock = threading.Lock()
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)
logger = logging.getLogger(__name__)


def connect(folder: str):
    try:
        imap = imaplib.IMAP4_SSL(
            host=app.config.IMAP_SERVER.host,
            port=app.config.IMAP_SERVER.port,
            timeout=30,
        )
    except Exception as ex:
        logger.error(f"{ex}")
        raise ConnectionErrorException(ex)

    try:
        imap.login(app.config.IMAP_SERVER.user, app.config.IMAP_SERVER.password)
    except Exception as ex:
        logger.error(f"{ex}")
        raise AccessDeniedException(ex)

    status, _ = imap.select(folder)
    if status == "OK":
        return imap
    else:
        try:
            status, folders = imap.list()
            if folders:
                folders = "".join([x.decode("utf-8") for x in folders]).strip("'") + "("
                folders = ",".join(
                    re.findall(r"(?<=\s)[A-Za-zА-Яа-я-\s]{2,}(?=\()", folders)
                )
        finally:
            imap.logout()
            raise InboxIsNotSelected(f"{folder}. Список доступных папок: {folders}")


def disconnect(imap):
    try:
        imap.close()
    finally:
        imap.logout()


def get_message(id: bytes, folder: str):
    error_message = ""
    imap = connect(folder)
    status = ""
    try:
        status, data = imap.uid("fetch", id.decode(), "(RFC822)")
    except Exception as ex:
        error_message = f"{ex}"
        logger.error(f"{error_message}")
        status = "FAIL"
    finally:
        disconnect(imap)
    if status == "OK":
        try:
            if len(data) > 1:
                return email.message_from_bytes(data[0][1])
            else:
                return None
        except Exception as ex:
            logger.error(f"{ex}")
    else:
        raise DataIsNotFound(error_message)

    return None


def search_messages(criteria, folder: str) -> Any:
    """Поиск писем не ранее 1 года
    по вхождению строки (criteria) в заголовке и теле письма
    если критерий поиска несколько, то ищется по любому их них
    """
    error_message = ""
    imap = connect(folder)
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
        criteria_text = " ".join(args).encode("utf-8")
        status, data = imap.uid("search", "charset", "utf-8", criteria_text)
    except Exception as ex:
        error_message = f"{ex}"
        logger.error(f"{error_message}")
        status = "FAIL"
    finally:
        disconnect(imap)
    if status == "OK":
        return data
    else:
        raise DataIsNotFound(error_message)


def get_message_data(id: bytes, folder: str, criteria: str = ""):
    msg = get_message(id, folder)
    if msg:
        lock.acquire()
        try:
            result = Result(criteria=criteria)
            result.criteria = criteria
            result.path = folder
            result.id = id
            result.sender = get_email_from_message(msg)
            result.date = get_date_from_message(msg)
            result.subject = get_subject(msg)
            result.body, result.files = get_body(msg)
        finally:
            lock.release()

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
        pass
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
        pass
    return filename


def get_Transfer_Encoding(part):
    data = [x for x in part.items() if x[0] == "Content-Transfer-Encoding"]
    return data[0][1] if data else ""


def get_body(msg) -> Tuple[str, list]:
    text = ""
    files = []
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            filename = get_file_name(part)
            if filename:
                files.append({"id": Result.hashit(filename), "name": filename})
        elif part.get_content_maintype() == "text":
            text = get_body_text(part)
    return text, files


def extract_attachments(msg, att_ids):
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
def fetch_messages(criteria: str, folders):
    results = []
    for folder in folders:
        data = search_messages(criteria, folder)
        if data:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                future_to_url = {
                    executor.submit(get_message_data, id, folder, criteria): id
                    for id in data[0].split()[:100]
                }

                for future in concurrent.futures.as_completed(future_to_url):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as ex:
                        results.append(Result(error_message=f"{ex}"))
    return (
        list(reversed((sorted([x for x in results if x], key=lambda x: x.date))))
        if results
        else []
    )


def fetch_message(id: bytes, folders: set):
    results = list()
    for folder in folders:
        result = get_message_data(id, folder)
        if result:
            results.append(result)
    return results


def fetch_attachments(id: str, folders: set, att_id: str = ""):
    for folder in folders:
        msg = get_message(id, folder)
        if msg:
            return extract_attachments(msg, att_id)
    return None


if __name__ == "__main__":
    pass
