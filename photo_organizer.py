import argparse
import subprocess
import os
import json
import sys
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import shutil


class ExifTool:
    sentinel = "{ready}" + os.linesep

    def __init__(self, executable="exiftool"):
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
    def __init__(self, path: str, size: int, creation_date: datetime):
        self.path = path
        self.size = size
        self.creation_date = creation_date


def parse_multimedia_file(file_path: str, exif_process: ExifTool) -> Optional[MultimediaFile]:
    metadata = exif_process.get_metadata(file_path)
    if len(metadata) == 0:
        return None
    img_creation_date = None
    try:
        metadata = metadata[0]
        mime_type = metadata['File:MIMEType']
        file_size = int(metadata['File:FileSize'])
        if mime_type == "image/jpeg" or mime_type == "image/png" or mime_type == "image/heic":
            tags = ["EXIF:DateTimeOriginal", "EXIF:CreateDate", "XMP:CreateDate"]
            for tag in tags:
                if tag in metadata:
                    img_creation_date = datetime.strptime(metadata[tag], "%Y:%m:%d %H:%M:%S")
                    break
        elif mime_type == "video/quicktime":
            if "QuickTime:CreationDate" in metadata:
                img_creation_date = datetime.strptime(metadata["QuickTime:CreationDate"], "%Y:%m:%d %H:%M:%S%z")
    except Exception as e:
        print("Exception wile parsing the file {}: {}".format(file_path, e), file=sys.stderr)
        return None
    if img_creation_date is not None:
        return MultimediaFile(file_path, file_size, img_creation_date)
    else:
        return None


def enumerate_files(path: str) -> List[MultimediaFile]:
    result = []
    count = 0
    with ExifTool() as exif_tool:
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = Path(root) / file
                mul_file = parse_multimedia_file(str(file_path), exif_tool)
                if mul_file is None:
                    continue
                result.append(mul_file)
                count += 1
                sys.stdout.write('\rEnumerating files: {}'.format(count))
    if count != 0:
        print()
    else:
        print("Enumerating files: 0")
    return result


def construct_target_path(file: MultimediaFile, destination: str) -> str:
    file_name = os.path.basename(file.path)
    folder_name = file.creation_date.strftime("%Y-%m")
    return os.path.join(destination, folder_name, file_name)


def unique_files(files: List[MultimediaFile], destination: str, skip_smaller: bool) -> List[MultimediaFile]:
    result = []
    count = 0
    for file in files:
        target_path = construct_target_path(file, destination)
        unique = not os.path.exists(target_path)
        if not unique:
            target_file_size = os.path.getsize(target_path)
            if skip_smaller and (file.size > target_file_size):
                print("Overwriting file {} (current size={}, new size={})".format(target_path, target_file_size,
                                                                                  file.size))
                unique = True
            elif not skip_smaller and (file.size != target_file_size):
                print("Warning! File {}: Sizes didn't match: current={}, new={}. OVERWRITING".format(target_path,
                                                                                                     target_file_size,
                                                                                                     file.size))
                unique = True
        if unique:
            result.append(file)
            count += 1
        sys.stdout.write('\rUnique files: {}'.format(count))
    print()

    return result


def print_copy_file(file: MultimediaFile, destination: str) -> None:
    print("Copy {} -> {}".format(file.path, construct_target_path(file, destination)))


def copy_file(file: MultimediaFile, destination: str) -> None:
    target_path = construct_target_path(file, destination)
    target_dir = Path(target_path).parent
    if not os.path.exists(target_dir):
        target_dir.mkdir(parents=True)
    shutil.copyfile(file.path, target_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Organizing image and video files")
    parser.add_argument("source", help="Source directory")
    parser.add_argument("destination", help="Destination directory")
    parser.add_argument("--dry-run", action="store_true", help="Do not perform actual copy")
    parser.add_argument("--skip-smaller", "-s", action="store_true",
                        help="Skip files if the new one is smaller than existing")

    args = parser.parse_args()
    files = enumerate_files(args.source)
    print("Found {} files".format(len(files)))

    unique = unique_files(files, args.destination, args.skip_smaller)
    for i, file in enumerate(unique):
        if args.dry_run:
            print_copy_file(file, args.destination)
        else:
            sys.stdout.write('\rCopy file: {}'.format(i + 1))
            copy_file(file, args.destination)
    print()


if __name__ == '__main__':
    main()
