#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

from gotenberg_client import GotenbergClient

GOTENBERG_API = "http://localhost:3000"


def html_to_pdf(file):
    # Safe-guard non-html if passed by mistake
    if file.suffix != ".html":
        print(f"skipping non-html file '{file.name}'! did you forget to pass '-m --merge'?")
        return 1

    with GotenbergClient(GOTENBERG_API) as client:
        with client.chromium.html_to_pdf() as route:
            response = (
                route.index(file)
                .resources(file.parent.glob("*.JPG"))
                .resources(file.parent.glob("*.jpg"))
                .resources(file.parent.glob("*.png"))
                .resources(file.parent.glob("*.svg"))
                .run()
            )
            # TODO Compress https://github.com/stumpylog/gotenberg-client/discussions/115

            output = file.with_suffix(".pdf")
            response.to_file(output)
            print(f"-> '{output}'")
            print("note: pdf compression is recommended")


def merge_pdfs(files, out):
    # Safe-guard non-pdf if passed by mistake
    for file in files:
        if file.suffix != ".pdf":
            print(f"non-pdf file '{file.name}' found!")
            return 1

    with GotenbergClient(GOTENBERG_API) as client:
        with client.merge.merge() as route:
            response = route.merge(files).run()

            output = files[0].parent / out
            response.to_file(output)
            print(f"-> '{output}'")
            print("note: pdf compression is recommended")


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Converts WSB to PDF and merges them.")
    parser.add_argument("files", type=Path, nargs="+", help="path to WSB HTML export")
    parser.add_argument("-m", "--merge", action="store_true", help="merge PDFs")
    parser.add_argument("-o", "--out", type=str, default="Stages.pdf", help="output file name (merged PDF)")
    args = parser.parse_args()

    for file in args.files:
        if not file.exists():
            parser.error(f"invalid file: '{file}'")

    # Health check
    with GotenbergClient(GOTENBERG_API) as client:
        try:
            health = client.health.health()
            print(f"Health: overall={health.overall}, chromium={health.chromium.status}")
        except Exception as e:
            print(f"is Gotenberg running? {e}")
            return 1

    # Process
    if args.merge:
        print("merging PDFs")
        merge_pdfs(args.files, args.out)
    else:
        for file in args.files:
            print(f"converting '{file}' to PDF")
            html_to_pdf(file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
