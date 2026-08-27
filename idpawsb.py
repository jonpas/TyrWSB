#!/usr/bin/env python3

import argparse
import datetime
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup


def process_export(file, args):
    with open(file, "rb") as f:
        soup = BeautifulSoup(f, "html.parser")

    # Safe-guard template if passed by mistake
    if soup.find("span", string="[[stage-name]]"):
        print(f"skipping template file '{file.name}'! did you forget to pass '-t --template'?")
        return 1

    # Set title
    soup.title.string = file.stem

    # Fix main image path
    mainimg = soup.find("img", src=re.compile("_main.JPG", flags=re.IGNORECASE))
    mainimg["src"] = mainimg["src"].replace("main", "Default")

    # Move custom Scored Hits from Notes
    scoredhits = soup.find("span", string=re.compile(r"^Best \d*", flags=re.IGNORECASE))
    scoredhitsnotes = soup.find("span", string=re.compile(r"Scored Hits:", flags=re.IGNORECASE))
    wsbscoredhits = soup.find("span", string=re.compile(r"Best \d+ will be scored", flags=re.IGNORECASE))
    if scoredhitsnotes:
        newscoredhits = re.search(r"^Scored Hits:\s*(.*)$", scoredhitsnotes.string, flags=re.IGNORECASE | re.MULTILINE).group(1).strip()
        scoredhits.string = f"Best {newscoredhits}"
        scoredhitsnotes.string = re.sub(r"\r?\n?^Scored Hits:.*$", "", scoredhitsnotes.string, count=1, flags=re.IGNORECASE | re.MULTILINE)
        wsbscoredhits.string = re.sub(r"Best \d+ will be scored", f"Best {newscoredhits} will be scored", wsbscoredhits.string, count=1, flags=re.IGNORECASE)

    # Scoring & Hint Bullet
    scoring = soup.find("span", string=re.compile(r"^\d* rounds, \w*$", flags=re.IGNORECASE))
    rounds, _, scoringtype = scoring.string.split()
    # scoringtype = "Limited"  # DEBUG

    soup.find("span", string=re.compile(r"^#$")).string = rounds
    hintbullet = soup.find("span", string=re.compile(r"^∞⚠$"))

    if scoringtype == "Unlimited":
        scoring.string += " ∞"
        hintbullet.string = "∞"
    else:
        scoring.append(soup.new_tag("span", string=" ⚠", style="color:#ff0000;"))
        hintbullet.string = ""
        hintbullet.append(soup.new_tag("span", string="⚠", style="color:#ff0000;"))

        # Replace "Best N" with "Worst N" in Limited scoring
        scoredhits.string = scoredhits.string.replace("Best", "Worst")
        wsbscoredhits.string = wsbscoredhits.string.replace("Best", "Worst")

    # Concealment & Hint Vest
    vest = soup.find("span", string=re.compile(r"^\w*\s*Required$", flags=re.IGNORECASE))
    vestreq = "NOT" not in vest.string
    # vestreq = False  # DEBUG

    hintvest = soup.find("span", string=re.compile(r"^✓✗$"))

    if vestreq:
        vest.string += " ✓"
        hintvest.string = "✓"
    else:
        vest.append(soup.new_tag("span", string=" ✗", style="color:#ff8c00;"))
        hintvest.string = ""
        hintvest.append(soup.new_tag("span", string="✗", style="color:#ff8c00;"))

    # Hint Pistol
    condition = soup.find("span", string=re.compile(r"^\s*Gun \w*,?\s*\w*\s*\w*", flags=re.IGNORECASE)).string.split()[1:4]
    loaded = "loaded" in condition[0]
    loaded, chambered = "loaded" in condition[0], False
    if loaded:
        chambered = "empty" not in condition[2]
    # loaded, chambered = True, False  # DEBUG

    hintchamber, hintpistol = soup.find_all("span", string=re.compile(r"^✓✗$"), limit=2)

    if loaded:
        hintpistol.string = "✓"
    else:
        hintpistol.string = ""
        hintpistol.append(soup.new_tag("span", string="✗", style="color:#ff8c00;"))

    if chambered:
        hintchamber.string = "✓"
    else:
        hintchamber.string = ""
        hintchamber.append(soup.new_tag("span", string="✗", style="color:#ff8c00;"))

    # Remove "0 Plate(s)" and "Plate(s) must fall" if 0
    plates = soup.find_all("span", string=re.compile("0 Plate", flags=re.IGNORECASE))
    if plates:
        for span in soup.find_all("span", string=re.compile("0 Plate", flags=re.IGNORECASE)):
            span.string = re.sub(r", 0 Plates?", "", span.string, count=1, flags=re.IGNORECASE)
        for span in soup.find_all("span", string=re.compile(", Plate must fall", flags=re.IGNORECASE)):
            span.string = re.sub(r", Plates? must fall", "", span.string, count=1, flags=re.IGNORECASE)

    # Remove Additional Views if empty
    additionalviews = soup.find("div", string=re.compile(re.escape("[[additional-views-grid]]")))
    if additionalviews:
        additionalviews.find_parent("section").extract()

    # Set export date and version
    for watermark in soup.find_all("div", string=re.compile(r"^Built with Practisim Designer$", flags=re.IGNORECASE)):
        watermark.string += f" - {datetime.datetime.now():%Y-%m-%d}"

        if args.tag_version:
            watermark.string += f" (v{args.tag_version})"

    if args.tag_version:
        print(f"tag-version={args.tag_version}")
    else:
        print("no tag-version specified")

    with open(file.parent / f"{file.stem} Processed.html", "w") as f:
        f.write(str(soup))
        print(f"-> '{f.name}'")


def process_template(file):
    with open(file, "rb") as f:
        soup = BeautifulSoup(f, "html.parser")

    # Safe-guard export if passed by mistake
    if not soup.find("span", string="[[stage-name]]"):
        print(f"skipping export file '{file.name}'!")
        return 1

    # Improve CSS
    soup.style.string = soup.style.string.replace("overflow: hidden;", "")  # allow longer text to overlap (to spot it easier)

    # Set match logo image path
    soup.find("img", src="[[custom-image:logo]]")["src"] = "WSB-Logo.svg"

    # Rename watermark
    for watermark in soup.find_all("div", string=re.compile(r"^Generated by", flags=re.IGNORECASE)):
        watermark.string = "Built with Practisim Designer"

    # Fix Scenario and Stage Procedure merge fields
    for span in soup.find_all("span", string="[[procedure]]"):
        span.string = "[[scenario]]"
    for span in soup.find_all("span", string="[[full-briefing]]"):
        span.string = "[[procedure]]"

    with open(file.parent / f"{file.stem} Improved.html", "w") as f:
        f.write(str(soup))
        print(f"-> '{f.name}'")


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Improves the generated Practisim Designer WSB HTML template/export.")
    parser.add_argument("files", type=Path, nargs="+", help="path to WSB HTML template/export")
    parser.add_argument("-t", "--template", action="store_true", help="improve a template (otherwise export is presumed)")
    parser.add_argument("--tag-version", type=str, help="version to tag the export with (eg. v1 in footer)")
    args = parser.parse_args()

    for file in args.files:
        if not file.exists():
            parser.error(f"invalid file: '{file}'")

    # Process
    for file in args.files:
        if args.template:
            print(f"processing '{file}' as template")
            process_template(file)
        else:
            print(f"processing '{file}' as export")
            process_export(file, args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
