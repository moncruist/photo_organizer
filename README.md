# Photo organizer script

This simple script organizes photos and videos gathered from iOS. It groups media files into subfolders with `YEAR-MONTH` format like Windows photo. If file is already there (has the same name and size), the copying will be skipped.

## Setup

You need install [exiftool](https://exiftool.org/) in order to run this script.

## Usage

`python3 photo_organizer.py SOURCE DESTINATION [OPTIONS]`

OPTIONS are:  
`--dry-run` - only print which files are going to be copied. Actual copy is not performed. 
