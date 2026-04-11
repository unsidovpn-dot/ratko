# ©️ Codrago, 2024-2030
# This file is a part of Heroku Userbot
# 🌐 https://github.com/coddrago/Heroku
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import asyncio
import logging
import os
import subprocess
import typing

import git
import herokutl

from .. import version

parser = herokutl.utils.sanitize_parse_mode("html")
logger = logging.getLogger(__name__)
DEFAULT_REPO_URL = "https://github.com/unsidogandon/ratko"


def _is_no_git() -> bool:
    return os.environ.get("HEROKU_NO_GIT") == "1"


def _get_repo_url() -> str:
    if _is_no_git():
        return DEFAULT_REPO_URL

    try:
        url = git.Repo().remote("origin").url.strip()
    except Exception:
        return DEFAULT_REPO_URL

    if url.startswith("git@github.com:"):
        url = f"https://github.com/{url.removeprefix('git@github.com:')}"
    elif url.startswith("ssh://git@github.com/"):
        url = f"https://github.com/{url.removeprefix('ssh://git@github.com/')}"
    elif url.startswith("http://github.com/"):
        url = f"https://github.com/{url.removeprefix('http://github.com/')}"

    if url.endswith(".git"):
        url = url[:-4]

    return url or DEFAULT_REPO_URL


# GeekTG Compatibility
def get_git_info() -> typing.Tuple[str, str]:
    """
    Get git info
    :return: Git info
    """
    if _is_no_git():
        return ("", "")
    hash_ = get_git_hash()
    repo_url = _get_repo_url()
    return (
        hash_,
        f"{repo_url}/commit/{hash_}" if hash_ else "",
    )


def get_git_hash() -> str:
    """
    Get current Heroku git hash
    :return: Git commit hash
    """
    if _is_no_git():
        return ""
    try:
        return git.Repo().head.commit.hexsha
    except Exception:
        return ""


def get_commit_url() -> str:
    """
    Get current Heroku git commit url
    :return: Git commit url
    """
    if _is_no_git():
        return "Unknown"
    try:
        hash_ = get_git_hash()
        if not hash_:
            return "Unknown"
        return f'<a href="{_get_repo_url()}/commit/{hash_}">#{hash_[:7]}</a>'
    except Exception:
        return "Unknown"


def get_git_status() -> str:
    """
    :return: 'Clean' or 'X files modified'.
    """
    if _is_no_git():
        return "Git disabled"
    try:
        process = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if process.returncode != 0:
            return "Not a Git repo"

        output = process.stdout.strip()

        if not output:
            return "Clean"

        count = len(output.splitlines())
        word = "file" if count == 1 else "files"
        return f"{count} {word} modified"

    except subprocess.TimeoutExpired:
        return "Unknown"
    except Exception:
        return "Unknown"


def get_last_commit_message() -> str:
    """
    Get the message of the last commit
    :return: Last commit message
    """
    if _is_no_git():
        return "Unknown"
    try:
        repo = git.Repo()
        return repo.head.commit.message.strip()
    except Exception:
        return "Unknown"


def get_commit_count() -> int:
    """
    Get the total number of commits in the repository
    :return: Number of commits
    """
    if _is_no_git():
        return 0
    try:
        repo = git.Repo()
        return len(list(repo.iter_commits()))
    except Exception:
        return 0


def is_up_to_date():
    repo = git.Repo(search_parent_directories=True)
    diff = any(repo.iter_commits(f"HEAD..origin/{version.branch}", max_count=1))
    return not diff
