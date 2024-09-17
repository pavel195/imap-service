import aioimaplib
import email, warnings, logging
import datetime
from pathlib import Path
from email.header import decode_header
from typing import Tuple, List, Any
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
import re, threading
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
local = threading.local()


async def connect_async():
    try:
        imap = aioimaplib.IMAP4_SSL(
            host=app.config.IMAP_SERVER.host,
            port=app.config.IMAP_SERVER.port,
            timeout=30,
        )
        await imap.wait_hello_from_server()
        await imap.login(app.config.IMAP_SERVER.user, app.config.IMAP_SERVER.password)
        await imap.select("Inbox")
        return imap
    except Exception as ex:
        logger.error(f"{ex}")
        raise ConnectionErrorException(ex)


async def get_imap_async():
    try:
        imap = local.imap
    except AttributeError:
        imap = local.imap = await connect_async()
    return imap


async def disconnect_async():
    imap = await get_imap_async()
    await imap.logout()


async def get_message_async(id: bytes):
    try:
        imap = await get_imap_async()
        status = ""
        status, data = await imap.uid("fetch", id.decode(), "(RFC822)")
    except Exception as ex:
        logger.error(f"{ex}")
    if status == "OK":
        try:
            if len(data) > 1:
                return email.message_from_bytes(data[1])
            else:
                return None
        except Exception as ex:
            logger.error(f"{ex}")
    return None


async def search_messages_async(criteria) -> Any:
    """Поиск писем не ранее 1 года
    по вхождению строки (criteria) в заголовке и теле письма
    если критерий поиска несколько, то ищется по любому их них
    """
    imap = await get_imap_async()
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
        status, data = await imap.uid_search(*args)
    except Exception as ex:
        logger.error(f"{ex}")
        status = "FAIL"
    if status == "OK":
        return data
    else:
        return None


async def get_message_data_async(id: bytes, criteria: str = ""):
    msg = await get_message_async(id=id)
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
        logger.error(f"{ex}")
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
async def fetch_messages_async(criteria: str):
    results = []
    data = await search_messages_async(criteria)
    if data:
        for id in data[0].split():
            result = await get_message_data_async(id, criteria)
            results.append(result)
    await disconnect_async()
    return [x for x in results if x] if results else []


async def fetch_message_async(id: bytes):
    result = await get_message_data_async(id)
    await disconnect_async()
    return [result]


async def fetch_attachments_async(id: str, att_id: str = ""):
    msg = await get_message_async(id)
    await disconnect_async()
    if msg:
        return extract_attachments(msg, att_id)
    return None


if __name__ == "__main__":
    pass
