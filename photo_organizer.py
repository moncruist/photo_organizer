import argparse
import typing


def enumerate_files(path: str):
    pass

def main():
    parser = argparse.ArgumentParser(description="Organizing image and video files")
    parser.add_argument("source", help="Source directory")
    parser.add_argument("destination", help="Destination directory")

    args = parser.parse_args()
    enumerate_files(args.source)


if __name__ == '__main__':
    main()
