import os, uuid, zipfile, logging, quopri, json, re
from datetime import datetime
from pathlib import Path
from src import app

logger = logging.getLogger(__name__)


def serialize(results):
    if isinstance(results, list):
        data = dict()
        data["result"] = results
        # serialized = json.dumps(data, ensure_ascii=False)
        serialized = json.dumps(results, indent=4, ensure_ascii=False)
        return serialized
    else:
        return str(results)


def get_name_template(path: str):
    return os.path.join(
        path,
        f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_{uuid.uuid4()}',
    )


def write_contents(filename, contents):
    with open(filename, mode="wb") as f:
        f.write(contents)
    return


def make_archive(path, files: list) -> str:
    arch_name = Path(path, "output.zip")
    try:
        arch_zip = zipfile.ZipFile(arch_name, "w")
        for file in files:
            arch_zip.write(
                Path(path, file),
                file,
                compress_type=zipfile.ZIP_DEFLATED,
            )
        arch_zip.close()
    except Exception as ex:
        logger.error(f"{ex}")

    return arch_name if Path.exists(arch_name) else None


def decode_quoted_printable(contents) -> str:
    text = quopri.decodestring(bytes(contents, "utf-8"))
    text = text.decode("utf-8")
    return text
