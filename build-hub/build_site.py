#!/usr/bin/env python3

import markdown
import os
import os.path

from bs4 import BeautifulSoup as soup
from pathlib import Path


def main():
    output_base = Path("./output")
    create_directory(output_base)

    contents = list_contents()

    condensed = "\n".join([f"- {c}" for c in contents])

    final = markdown.markdown(f"# Files List\n\n {condensed}")

    with open(output_base.joinpath("files.html"), "w") as f:
        f.write(final)


def create_directory(dest):
    if not os.path.exists(dest):
        os.mkdir(dest)


def list_contents():
    import os
    import os.path

    all_files = []
    for root, dirs, files in os.walk("."):
        if len(files):
            all_files.extend([
                os.path.join(root, f)
                for f in files
            ])

    return all_files


if __name__ == "__main__":
    main()
