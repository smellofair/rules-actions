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

    if args.test and os.path.exists(_output):
        logger.debug("Blowing away existing output directory")
        shutil.rmtree(_output)
        create_directory(_output)

    hub_config = load_config(_hub)
    translations = load_translations(_hub.joinpath("translations"), hub_config)

    build_hub(_hub, _output, translations)

    add_debug_info(_hub, _output)


def load_translations(_home, hub_config):
    translations = dict()

    for repo_name, repo_config in hub_config.items():
        repo_path = _home.joinpath(repo_name)
        if not os.path.isdir(repo_path):
            continue

        repo_translations = load_repo_translations(repo_path, repo_config)

        merge_translations(translations, repo_translations)

    return translations


def load_repo_translations(_repo, config):
    # config is { "en": "all", "es-pe": ["fog"] }
    translations = dict()

    with open(_repo.joinpath("_lang.yml")) as f:
        translation_config = yaml.safe_load(f)

    repo_translations = translation_config.get("translations", [])

    for language_translation in repo_translations:
        code = language_translation.get("language-code", "unknown")
        lang_games = dict()

        if code not in config:
            logger.debug(f"Skipping {code} as it's not listed in the hub config")
            continue

        _lang = _repo.joinpath(language_translation.get("directory", code))

        allowed_games = config[code]

        for game_code, game_config in language_translation.get("games", dict()).items():
            if game_code in allowed_games or allowed_games == "all":
                actual_game_config = expand_game_config(game_code, game_config)
                available_files = find_translated_files(
                    _lang.joinpath(actual_game_config["directory"]),
                    actual_game_config,
                )

                if not len(available_files):
                    continue

                lang_games[game_code] = dict(
                    name=actual_game_config.get("name"),
                    files=available_files
                )

        if len(lang_games):
            translations[code] = dict(
                games=lang_games,
                name=language_translation.get("name", "Unknown"),
            )


    return translations


def find_translated_files(_home, config):
    files = dict()
    rules_path = _home.joinpath(config["rules"])
    faq_path = _home.joinpath(config["faq"])
    assets_path = _home.joinpath("assets")

    if os.path.isfile(rules_path):
        files["rules"] = rules_path

    if os.path.isfile(faq_path):
        files["faq"] = faq_path

    if os.path.isdir(assets_path):
        files["assets"] = assets_path

    return files


def expand_game_config(code, config):
    if type(config) == str:
        config = {"local-name": config}

    return dict(
        name=config.get("local-name"),
        directory=config.get("directory", code),
        rules=config.get("rules", "rules.md"),
        faq=config.get("faq", "faq.md"),
    )


def merge_translations(translations, repo_translations):
    _merge(translations, repo_translations)


def _merge(dest, source):
    for k, v in source.items():
        if not k in dest:
            dest[k] = v
        elif type(v) == dict:
            _merge(dest[k], v)


def build_hub(_hub, _output, translations):
    # build the top level first
    # translations looks like:
    # en:
    #   name: English
    #   games:
    #     fh:
    #       name: Frosthaven
    #       files:
    #         rules: /path/to/rules.md
    #         faq: /path/to/faq.md
    # es-pe:
    #    name: Spanish (Peru)
    #    games:
    #      bnb:
    #        name: Buttons & Bugs
    #        files:
    #         rules: /path/to/rules.md
    #         faq: /path/to/faq.md
    _templates = _hub.joinpath("hub-root")

    load_header_and_footer(_templates)

    copy_with_replace(
        _templates.joinpath("index.html"),
        _output.joinpath("index.html"),
        lambda line: "REPLACE:" in line,
        partial(do_replace, translations, main_replace_delegate),
    )

    for key, val in translations.items():
        # build each languages index page
        _lang = _output.joinpath(key)
        copy_with_replace(
            _templates.joinpath("gamelist.html"), # TODO - get a language specific file?
            _lang.joinpath("index.html"),
            lambda line: "REPLACE:" in line,
            partial(do_replace, val, gamelist_replace_delegate)
        )

        for code, game in val.get("games", {}).items():
            _game = _lang.joinpath(code)
            for kind, path in game.get("files", {}).items():
                if kind == "assets":
                    shutil.copytree(path, _game.joinpath(kind))
                else:
                    copy_with_replace(
                        path,
                        _game.joinpath(f"{kind}.html"),
                        lambda line: "REPLACE:" in line,
                        partial(do_replace, game, game_replace_delegate),
                        True
                    )


HEADER = None
FOOTER = None
def load_header_and_footer(_templates):
    global HEADER, FOOTER

    logger.debug("Loading header and footer from templates...")

    with open(_templates.joinpath("header.html")) as f:
        HEADER = f.read()

    with open(_templates.joinpath("footer.html")) as f:
        FOOTER = f.read()


def copy_with_replace(source, dest, test_func, replace_func, is_markdown=False):
    create_directory(os.path.dirname(dest))

    logger.debug(f"Copying from {source} to {dest}")
    with open(source) as s:
        if is_markdown:
            data = s.read()
            # TODO - need to get a full html header / footer in here
            source_data = f"""
            <!-- REPLACE:HEADER -->
            {_m(data)}
            <!-- REPLACE:FOOTER -->
            """.split("\n")
        else:
            source_data = s.readlines()

    with open(dest, "w") as d:
        for line in source_data:
            if test_func(line):
                try:
                    d.write(replace_func(line))
                except:
                    logger.exception(line, replace_func(line))
            else:
                d.write(line)


def do_replace(data, delegate, line):
    idx = line.find("REPLACE:")
    relevant = line[idx:line.find(" ", idx)].split(":")[1]

    if relevant == "HEADER":
        return HEADER
    elif relevant == "FOOTER":
        return FOOTER
    else:
        value = delegate(data, relevant)
        if value is None:
            raise ValueError("Unknown replacement key: " + relevant)

        return value


def main_replace_delegate(data, relevant):
    if relevant == "LANGUAGES":
        return json.dumps(list(data.keys()))
    elif relevant == "LANGLIST":
        return _m(
            "\n".join([
                f"- [{v['name']}]({k})"
                for k,v in data.items()
            ])
        )
    elif relevant == "TITLE":
        return "Smell-of-Air Rules Hub"


def gamelist_replace_delegate(data, relevant):
    if relevant == "GAMELIST":
        games = []
        for code, game in data["games"].items():
            line = f"{game['name']} - "

            links = []
            if "rules" in game["files"]:
                links.append(f"[Rules]({code}/rules.html)")

            if "faq" in game["files"]:
                links.append(f"[FAQ]({code}/faq.html)")

            games.append(line + " | ".join(links))

        return _m("\n".join([f"- {g}" for g in games]))

    elif relevant == "TITLE":
        return f"Smell-of-Air {data['name']} Rules Hub"


    return relevant


def game_replace_delegate(data, relevant):
    if relevant == "TITLE":
        return f"Smell-of-Air {data['name']} *game* Rules/FAQ"

    # TODO - what could I possibly have here?
    return None


def load_config(_hub):
    with open(_hub.joinpath("config.yml")) as f:
        config = yaml.safe_load(f)

    config_by_repo = dict()
    for repo in config.get("translations", []):
        if type(repo) is not dict:
            continue

        repo_name = repo.get("repo", None)
        if not repo_name:
            continue

        repo_config = dict()

        for lang in repo.get("languages", []):
            if type(lang) is not dict:
                continue

            games = lang.get("games", [])
            repo_config[lang.get("code", None)] = games

        config_by_repo[repo.get("repo")] = repo_config

    return config_by_repo


def create_directory(dest):
    if not os.path.exists(dest):
        logger.debug(f"Creating directory: {dest}")
        os.makedirs(dest)
    else:
        logger.debug(f"Directory already exists: {dest}")


def list_contents(path):

    all_files = []
    with os.scandir(path) as it:
        for entry in it:
            if entry.name.startswith("."):
                continue

            if entry.is_file():
                all_files.append(entry.path)
            elif entry.is_dir():
                all_files.extend(
                    list_contents(entry.path)
                )

    return all_files


def add_debug_info(_hub, _output):
    files = "\n".join([f"- {n}" for n in list_contents(_hub)])
    md = f"# Files\n\n{files}"

    with open(_output.joinpath("_files.html"), "w") as f:
        f.write(_m(md))


def _m(data):
    return markdown.markdown(data)


def _j(data):
    return json.dumps(data, indent=2)


if __name__ == "__main__":
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", "-t", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")

    main(parser.parse_args())
