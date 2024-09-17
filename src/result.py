import re
import hashlib
import datetime
import logging
import json_fix
from typing import Any

logger = logging.getLogger(__name__)


class Result:
    def __init__(self, criteria: str = "", error_message: str = ""):
        try:
            patt = r'["0-9а-яёА-ЯЁ:\\\/\s-]'
            self.criteria = criteria
            self.compile: re.compile = re.compile(
                patt + "*?" + "(?:" + self.criteria.replace(",", "|") + ")" + patt + "*",
                re.I,
            )
            self.id: bytes = b"0"
            self.subject: str = ""
            self.date = None
            self.body: str = error_message
            self.sender: str = ""
            self.files: list = []
            self.path: str = ""
            self.error: str = error_message
        except Exception as ex:
            logger.error(f"{ex}")
            raise


    @classmethod
    def hashit(cls, s):
        return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]

    def find_in_body(self):
        return self.compile.findall(self.body)

    def find(self):
        return self.compile.findall(self.subject + self.body) or any(
            self.compile.findall(x) for x in self.files
        )

    def __json__(self):
        try:
            data = {
                "id": self.id.decode("utf-8"),
                "sender": self.sender,
                "subject": self.subject,
                "date": datetime.datetime(*self.date[:6]),
                "body": self.body,
                "path": self.path,
                "files": self.files,
            }
        except Exception as ex:
            logger.error(f"{ex}")
            raise

        return data
