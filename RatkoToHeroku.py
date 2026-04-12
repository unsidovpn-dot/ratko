# ---------------------------------------------------------------------------------
# Name: RatkoToHeroku
# Description: Switch your ratko to Heroku
# Author: @unsidogandon
# Commands: ratkotoheroku
# meta developer: @unsidogandon
# meta_desc: Switch your ratko to Heroku
# ---------------------------------------------------------------------------------

import contextlib
import logging
import subprocess
import sys
from pathlib import Path

import git
from herokutl.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)

TARGET_REPO_URL = "https://github.com/coddrago/Heroku"
TARGET_REPO_WEB = "https://github.com/coddrago/Heroku"
TARGET_BRANCHES = ("master",)
MODULE_OWNER_RENAMES = {
    "RatkoBackupMod": "HerokuBackupMod",
    "RatkoConfigMod": "HerokuConfigMod",
    "RatkoInfoMod": "HerokuInfoMod",
    "RatkoPluginSecurity": "HerokuPluginSecurity",
    "RatkoSecurityMod": "HerokuSecurityMod",
    "RatkoSettingsMod": "HerokuSettingsMod",
    "RatkoWebMod": "HerokuWebMod",
}


class MigrationError(Exception):
    pass


@loader.tds
class RatkoToHeroku(loader.Module):
    """Switch this ratko install to Heroku"""

    strings = {
        "name": "RatkoToHeroku",
        "already": "<b>You are already running Heroku.</b>",
        "confirm": (
            "<b>This command will switch this install from ratko to Heroku,"
            " migrate renamed module data and restart the userbot.</b>\n\n"
            "<b>Recommended:</b> create a manual backup first with"
            " <code>{prefix}backupall</code>.\n\n"
            "Run <code>{prefix}ratkotoheroku -f</code> to continue."
        ),
        "starting": "<b>Starting switch to Heroku...</b>",
        "switching_repo": "<b>Switching git remote to Heroku...</b>",
        "migrating_db": "<b>Migrating database owners for Heroku...</b>",
        "installing": "<b>Installing Heroku requirements...</b>",
        "requirements_failed": (
            "<b>Requirements installation failed.</b> The repository is already"
            " switched, but you may need to install dependencies manually after"
            " restart."
        ),
        "restarting": "<b>Migration complete. Restarting into Heroku...</b>",
        "dirty": (
            "<b>The repository has tracked local changes.</b>\n"
            "Commit or stash them first, then run the switch again."
        ),
        "no_git": "<b>This install is not running from a git repository.</b>",
        "no_remote_branch": (
            "<b>Couldn't find a compatible branch on the Heroku remote.</b>"
        ),
        "failed": "<b>Switch failed:</b> <code>{}</code>",
        "done": (
            "<b>Switched to Heroku successfully.</b>\n"
            "This helper module will unload itself now."
        ),
        "github": "📖 GitHub",
        "_cmd_doc_ratkotoheroku": "Switch this ratko install to Heroku",
    }

    strings_ru = {
        "already": "<b>У тебя уже запущен Heroku.</b>",
        "confirm": (
            "<b>Эта команда переключит этот инстанс с ratko на Heroku,"
            " перенесет данные переименованных модулей и перезапустит юзербот.</b>\n\n"
            "<b>Лучше сначала сделать ручной бэкап через</b>"
            " <code>{prefix}backupall</code>.\n\n"
            "Запусти <code>{prefix}ratkotoheroku -f</code>, чтобы продолжить."
        ),
        "starting": "<b>Начинаю переключение на Heroku...</b>",
        "switching_repo": "<b>Переключаю git remote на Heroku...</b>",
        "migrating_db": "<b>Переношу DB-данные модулей под Heroku...</b>",
        "installing": "<b>Устанавливаю зависимости Heroku...</b>",
        "requirements_failed": (
            "<b>Не удалось поставить зависимости.</b> Репозиторий уже переключен,"
            " но после перезапуска может понадобиться вручную доставить пакеты."
        ),
        "restarting": "<b>Миграция завершена. Перезапускаюсь уже в Heroku...</b>",
        "dirty": (
            "<b>В репозитории есть локальные изменения в отслеживаемых файлах.</b>"
            "\nСначала закоммить или убери их в stash, потом повтори переключение."
        ),
        "no_git": "<b>Этот инстанс запущен не из git-репозитория.</b>",
        "no_remote_branch": (
            "<b>На удаленном репозитории Heroku не нашлась подходящая ветка.</b>"
        ),
        "failed": "<b>Переключение не удалось:</b> <code>{}</code>",
        "done": (
            "<b>Переход на Heroku завершен успешно.</b>\n"
            "Теперь этот вспомогательный модуль сам выгрузится."
        ),
        "github": "📖 GitHub",
        "_cmd_doc_ratkotoheroku": "Переключить этот ratko инстанс на Heroku",
    }

    async def client_ready(self):
        if not self.get("done"):
            return

        self.set("done", None)
        await self.inline.bot.send_message(
            self.tg_id,
            self.strings("done"),
            reply_markup=self.inline.generate_markup(
                [{"text": self.strings("github"), "url": TARGET_REPO_WEB}]
            ),
        )

        with contextlib.suppress(Exception):
            await self.invoke("unloadmod", "RatkoToHeroku", peer=self.tg_id)

    def _repo_root(self) -> Path:
        return Path(utils.get_base_dir()).parent

    def _repo(self) -> git.Repo:
        try:
            return git.Repo(self._repo_root())
        except git.exc.InvalidGitRepositoryError as e:
            raise MigrationError(self.strings("no_git")) from e

    def _is_already_heroku(self) -> bool:
        try:
            repo = self._repo()
            origin = repo.remote("origin")
            urls = list(origin.urls)
            return any("coddrago/Heroku" in url for url in urls)
        except Exception:
            return False

    def _clone_jsonable(self, value):
        if isinstance(value, dict):
            return {
                key: self._clone_jsonable(subvalue) for key, subvalue in value.items()
            }

        if isinstance(value, list):
            return [self._clone_jsonable(item) for item in value]

        if isinstance(value, tuple):
            return [self._clone_jsonable(item) for item in value]

        return value

    def _raw_db_snapshot(self) -> dict:
        return {key: self._clone_jsonable(value) for key, value in self._db.items()}

    def _migrated_db_snapshot(self, source: dict) -> dict:
        snapshot = self._clone_jsonable(source)

        for old_owner, new_owner in MODULE_OWNER_RENAMES.items():
            old_data = snapshot.get(old_owner, None)
            if not isinstance(old_data, dict):
                continue

            new_data = snapshot.get(new_owner, {})
            if not isinstance(new_data, dict):
                new_data = {}

            merged = dict(old_data)
            merged.update(new_data)
            snapshot[new_owner] = merged

        updater_cfg = snapshot.setdefault("UpdaterMod", {}).setdefault("__config__", {})
        updater_cfg["GIT_ORIGIN_URL"] = TARGET_REPO_URL
        return snapshot

    def _switch_repo(self) -> None:
        repo = self._repo()
        if repo.is_dirty(untracked_files=False):
            raise MigrationError(self.strings("dirty"))

        try:
            origin = repo.remote("origin")
            origin.set_url(TARGET_REPO_URL)
        except ValueError:
            origin = repo.create_remote("origin", TARGET_REPO_URL)

        repo.git.fetch("origin", "--prune")
        refs = {ref.remote_head: ref for ref in repo.remote("origin").refs}
        target_branch = next(
            (branch for branch in TARGET_BRANCHES if branch in refs),
            None,
        )
        if target_branch is None:
            raise MigrationError(self.strings("no_remote_branch"))

        remote_ref = refs[target_branch]
        if target_branch in repo.heads:
            local_branch = repo.heads[target_branch]
        else:
            local_branch = repo.create_head(target_branch, remote_ref.commit)

        local_branch.set_tracking_branch(remote_ref)
        local_branch.checkout(force=True)
        repo.git.reset("--hard", f"origin/{target_branch}")

    def _apply_snapshot(self, snapshot: dict) -> None:
        self._db.clear()
        self._db._update_from_read(snapshot)
        self._db.save()

    def _install_requirements(self) -> bool:
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(self._repo_root() / "requirements.txt"),
                    "--user",
                ],
                check=True,
                timeout=600,
                capture_output=True,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            logger.exception("RatkoToHeroku requirements install failed")
            return False

    @loader.command()
    async def ratkotoheroku(self, message: Message):
        if self._is_already_heroku():
            await utils.answer(message, self.strings("already"))
            return

        args = utils.get_args_raw(message)
        if "-f" not in args.split():
            await utils.answer(
                message,
                self.strings("confirm").format(
                    prefix=utils.escape_html(self.get_prefix())
                ),
            )
            return

        try:
            source_db = self._raw_db_snapshot()
            migrated_db = self._migrated_db_snapshot(source_db)

            await utils.answer(message, self.strings("starting"))
            await utils.answer(message, self.strings("switching_repo"))
            self._switch_repo()

            await utils.answer(message, self.strings("migrating_db"))
            self._apply_snapshot(migrated_db)
            self.set("done", True)

            await utils.answer(message, self.strings("installing"))
            if not self._install_requirements():
                await utils.answer(message, self.strings("requirements_failed"))

            await utils.answer(message, self.strings("restarting"))
            await self.invoke("restart", "-f", peer=message.peer_id)
        except MigrationError as e:
            await utils.answer(message, str(e))
        except Exception as e:
            logger.exception("RatkoToHeroku failed")
            await utils.answer(
                message,
                self.strings("failed").format(utils.escape_html(str(e))),
            )
