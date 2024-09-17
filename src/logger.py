from logging.handlers import HTTPHandler
from requests.adapters import HTTPAdapter
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from requests.auth import HTTPBasicAuth

errors = []
logger = logging.getLogger(__name__)


class InfoFilter(logging.Filter):
    def __init__(self, *args, **kwargs):
        super(InfoFilter, self).__init__()

    def filter(self, record):
        return record.levelname == "INFO"


class DebugFilter(logging.Filter):
    def __init__(self, *args, **kwargs):
        super(DebugFilter, self).__init__()

    def filter(self, record):
        return record.levelname == "DEBUG"


class WarningFilter(logging.Filter):
    def __init__(self, *args, **kwargs):
        super(WarningFilter, self).__init__()

    def filter(self, record):
        return record.levelname == "WARNING"


class ErrorFilter(logging.Filter):
    def __init__(self, *args, **kwargs):
        super(ErrorFilter, self).__init__()

    def filter(self, record):
        if record.levelname == "ERROR" or record.levelname == "CRITICAL":
            text = ""
            if record.exc_text != None:
                text = record.exc_text
            elif record.exc_info != None:
                text = f"{record.name}:{record.lineno}"
            if text and len(errors) > 0 and (text in errors):
                return False
            errors.append(text)
            return record.levelname == "ERROR" or record.levelname == "CRITICAL"
        else:
            return False


class HTTPFilter(logging.Filter):
    def __init__(self, *args, **kwargs):
        super(HTTPFilter, self).__init__()

    def filter(self, record):
        return record.levelname == "INFO" and record.message.find("Архив") != -1


class CustomFormatter(logging.Formatter):

    def __init__(self, *args, **kwargs):
        super().__init__()
        grey = f"{chr(27)}[38m"
        green = f"{chr(27)}[32m"
        yellow = f"{chr(27)}[33m"
        red = f"{chr(27)}[31m"
        bold_red = f"{chr(27)}[31;1m"
        reset = f"{chr(27)}[0m"
        format = kwargs.get("format", "[%(levelname)s %(asctime)s] - {0}%(message)s{1}")
        self.datefmt = kwargs.get("datefmt", "%d-%m-%Y %H:%M:%S")
        self.FORMATS = {
            # logging.DEBUG: format.format(green, reset),
            logging.INFO: format.format(grey, reset),
            # logging.WARNING: format.format(yellow, reset),
            # logging.ERROR: format.format(red, reset),
            # logging.CRITICAL: format.format(bold_red, reset)
            "default": format.format("", ""),
        }

    def format(self, record, *args, **kwargs):
        log_fmt = self.FORMATS.get(record.levelno, self.FORMATS.get("default"))
        formatter = logging.Formatter(log_fmt, datefmt=self.datefmt)
        return formatter.format(record)


# class CustomHTTPHandler(HTTPHandler):
#     def __init__(self, host, url, method='GET', secure=False, credentials=None, context=None, *args, **kwargs):
#         self.host = host
#         self.url = url
#         self.method = method
#         self.credentials = credentials
#         super(CustomHTTPHandler,self).__init__(host, url, method, secure, credentials, context)

#     def mapLogRecord(self, record):
#         return super().mapLogRecord(record)

#     def emit(self, record):
#         log_entry = self.format(record)
#         url = self.url
#         session = requests.Session()
#         retry = Retry(connect=1, backoff_factor=0.5, redirect=2)
#         adapter = HTTPAdapter(max_retries=retry)
#         session.mount('http://', adapter)
#         session.mount('https://', adapter)
#         try:
#             response =session.get(url)
#         except requests.exceptions.ConnectionError:
#             response.status_code = "Connection refused"
#             # response = requests.get(url,verify=False)
#         return response.json()
#         # return requests.get(url=url)

#         # return requests.post(url, log_entry,
#         #                      headers={"Content-type": "application/json"},
#         #                      auth={"username":self.credentials[0],"password":self.credentials[1]}).content

import concurrent.futures

executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)


class CustomHTTPHandler(HTTPHandler):

    def __init__(
        self,
        host,
        url,
        method="GET",
        secure=False,
        credentials=None,
        context=None,
        *args,
        **kwargs,
    ):
        self.host = host
        self.url = url
        self.method = method
        self.credentials = credentials
        self.auth = HTTPBasicAuth(credentials[0], credentials[1])

        # sets up a session with the server
        self.MAX_POOLSIZE = 100
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
            }
        )

        self.session.mount(
            "https://",
            HTTPAdapter(
                max_retries=Retry(
                    total=5, backoff_factor=0.5, status_forcelist=[403, 500]
                ),
                pool_connections=self.MAX_POOLSIZE,
                pool_maxsize=self.MAX_POOLSIZE,
            ),
        )

        super(CustomHTTPHandler, self).__init__(
            host, url, method, secure, credentials, context
        )

    def emit(self, record):
        # body = self.format(record)
        try:
            self.session.get(self.url, auth=self.auth)
            # executor.submit(actual_emit, self, record)
        except Exception as ex:
            logger.exception("HTTPHandler")


def actual_emit(self, record):
    self.session.get(self.url, auth=self.auth)
