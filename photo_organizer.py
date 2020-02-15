import argparse
import subprocess
import os
import json
import sys
from typing import List, Optional
from datetime import datetime


class ExifTool:
    sentinel = "{ready}" + os.linesep

    def __init__(self, executable="/usr/bin/exiftool"):
        self.executable = executable

    def __enter__(self):
        self.process = subprocess.Popen(
            [self.executable, "-stay_open", "True",  "-@", "-"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.process.stdin.write(str.encode("-stay_open\nFalse\n"))
        self.process.stdin.flush()

    def execute(self, *args: str):
        args = args + ("-execute\n",)
        self.process.stdin.write(str.encode(str.join("\n", args)))
        self.process.stdin.flush()
        output = ""
        fd = self.process.stdout.fileno()
        while not output.endswith(self.sentinel):
            output += os.read(fd, 4096).decode()
        return output[:-len(self.sentinel)]

    def get_metadata(self, *filenames: str) -> str:
        return json.loads(self.execute("-G", "-j", "-n", *filenames))


class MultimediaFile:
    def __init__(self, path: str, creation_date: datetime):
        self.path = path
        self.creation_date = creation_date


def extract_creation_date(file_path: str, exif_process: ExifTool) -> Optional[datetime]:
    metadata = exif_process.get_metadata(file_path)
    if len(metadata) == 0:
        return None
    img_creation_date = None
    try:
        metadata = metadata[0]
        mime_type = metadata['File:MIMEType']
        if mime_type == "image/jpeg" or mime_type == "image/png":
            tags = ["EXIF:DateTimeOriginal", "EXIF:CreateDate", "XMP:CreateDate"]
            for tag in tags:
                if tag in metadata:
                    img_creation_date = datetime.strptime(metadata[tag], "%Y:%m:%d %H:%M:%S")
                    break
        elif mime_type == "video/quicktime":
            if "QuickTime:CreationDate" in metadata:
                img_creation_date = datetime.strptime(metadata["QuickTime:CreationDate"], "%Y:%m:%d %H:%M:%S%z")
    except Exception as e:
        print("Exception file parsing {}: {}".format(file_path, e), file=sys.stderr)
        return None
    return img_creation_date


def enumerate_files(path: str) -> List[MultimediaFile]:
    result = []
    with ExifTool() as exif_tool:
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                img_creation_date = extract_creation_date(file_path, exif_tool)
                if img_creation_date is None:
                    continue
                result.append(MultimediaFile(file_path, img_creation_date))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Organizing image and video files")
    parser.add_argument("source", help="Source directory")
    parser.add_argument("destination", help="Destination directory")

    args = parser.parse_args()
    files = enumerate_files(args.source)
    print("Found {} files".format(len(files)))


if __name__ == '__main__':
    main()
