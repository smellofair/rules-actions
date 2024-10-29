#!/usr/bin/env python3

import argparse
import json
import logging
import markdown
import os
import os.path
import shutil
import textwrap
import yaml

from bs4 import BeautifulSoup as soup
from functools import partial
from pathlib import Path


LOG_FORMAT="[%(asctime)s] %(levelname)s: %(funcName)s:%(lineno)d -- %(message)s"

logger = logging.getLogger(__name__)
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)


def main(args):
    base = Path("./")
    if args.test:
        base = Path("./test")

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    _output = base.joinpath("output")
    create_directory(_output)

    fh = logging.FileHandler(_output.joinpath("_build.log"))
    fh.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(fh)


    _hub = base.joinpath("hub")

    _actions = base.joinpath("actions") # TODO - is this used?

    if args.test and os.path.exists(_output):
        logger.debug("Blowing away existing output directory")
        shutil.rmtree(_output)
        create_directory(_output)

    config = load_config(_hub)
    available = load_available_translations(_hub)

    build_hub(_hub, _output, config, available)


def build_hub(_hub, _output, config, available):
    # build the top level first
    languages = dict(en="English") # TODO - key: `en` value: `English`

    copy_with_replace(
        _hub.joinpath("hub-root/index.html"),
        _output.joinpath("index.html"),
        lambda line: "REPLACE:" in line,
        partial(do_main_replace, languages)
    )

    for key, val in languages.items():
        # build each languages index page
        copy_with_replace(
            _hub.joinpath("hub-root/gamelist.html"), # TODO - get a language specific file?
            _output.joinpath(f"{key}/index.html"),
            lambda line: False,
            lambda x, y: None
        )

        # build each languages game pages
        # TODO


def copy_with_replace(source, dest, test_func, replace_func):
    create_directory(os.path.dirname(dest))

    logger.debug(f"Copying from {source} to {dest}")
    with open(source) as s, open(dest, "w") as d:
        for line in s.readlines():
            if test_func(line):
                d.write(replace_func(line))
            else:
                d.write(line)


def do_main_replace(data, line):
    idx = line.find("REPLACE:")
    relevant = line[idx:line.find(" ", idx)].split(":")[1]

    if relevant == "LANGUAGES":
        langs = json.dumps(list(data.keys()))
        return f"{line[:idx]} {langs}"
    elif relevant == "HEADER":
        return "<h1>HEADER COMING EVENTUALLY</h1>"
    elif relevant == "FOOTER":
        return "<footer>FOOTER COMING SOON</footer>"
    elif relevant == "LANGLIST":
        return markdown.markdown(
            "\n".join([
                f"- [{v}]({k})"
                for k,v in data.items()
            ])
        )

    else:
        raise ValueError("Unknown replacement key: " + relevant)


def load_config(_hub):
    with open(_hub.joinpath("config.yml")) as f:
        return yaml.safe_load(f)


def load_available_translations(_hub):
    return dict() # TODO

def create_directory(dest):
    if not os.path.exists(dest):
        logger.debug(f"Creating directory: {dest}")
        os.makedirs(dest)
    else:
        logger.debug(f"Directory already exists: {dest}")


def list_contents(path):

    all_files = []
    for root, dirs, files in os.walk(path):
        if not len(files):
            continue

        if os.path.basename(root).startswith("."):
            continue

        all_files.extend([
            os.path.join(root, f)
            for f in files
            if not f.startswith(".")
        ])

    return all_files


if __name__ == "__main__":
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", "-t", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")

    main(parser.parse_args())
