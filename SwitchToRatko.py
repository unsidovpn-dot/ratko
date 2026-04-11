# ---------------------------------------------------------------------------------
# Name: SwitchToRatko
# Description: Switch your Heroku to ratko
# Author: @unsidogandon
# Commands: switchtoratko
# meta developer: @unsidogandon
# meta_desc: Switch your Heroku to ratko
# ---------------------------------------------------------------------------------

import asyncio
import contextlib
import datetime
import io
import json
import logging
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import git
from herokutl.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)

TARGET_REPO_URL = "https://github.com/unsidogandon/ratko"
TARGET_REPO_WEB = "https://github.com/unsidogandon/ratko"
TARGET_BRANCHES = ("main", "master")
MODULE_OWNER_RENAMES = {
    "HerokuBackupMod": "RatkoBackupMod",
    "HerokuConfigMod": "RatkoConfigMod",
    "HerokuInfoMod": "RatkoInfoMod",
    "HerokuPluginSecurity": "RatkoPluginSecurity",
    "HerokuSecurityMod": "RatkoSecurityMod",
    "HerokuSettingsMod": "RatkoSettingsMod",
    "HerokuWebMod": "RatkoWebMod",
}


class MigrationError(Exception):
    pass


@loader.tds
class SwitchToRatko(loader.Module):
    """Create backup and switch this Heroku install to ratko"""

    strings = {
        "name": "SwitchToRatko",
        "already": "<b>You are already running ratko.</b>",
        "confirm": (
            "<b>This command will create a full backup in Saved Messages, switch"
            " this install from Heroku to ratko, migrate renamed module data and"
            " restart the userbot.</b>\n\n"
            "Run <code>{prefix}switchtoratko -f</code> to continue."
        ),
        "backing_up": "<b>Creating backup before switching...</b>",
        "backup_saved": (
            "<b>Backup saved to your Saved Messages.</b>\n"
            "Switching this install to ratko..."
        ),
        "switching_repo": "<b>Switching git remote to ratko...</b>",
        "migrating_db": "<b>Migrating database owners for ratko...</b>",
        "installing": "<b>Installing ratko requirements...</b>",
        "requirements_failed": (
            "<b>Requirements installation failed.</b> The repository is already"
            " switched, but you may need to install dependencies manually after"
            " restart."
        ),
        "restarting": "<b>Migration complete. Restarting into ratko...</b>",
        "backup_caption": (
            "<b>Backup created before switching from Heroku to ratko.</b>\n"
            "Reply to this file with <code>{prefix}restoreall</code> if you need"
            " to roll back."
        ),
        "dirty": (
            "<b>The repository has tracked local changes.</b>\n"
            "Commit or stash them first, then run the switch again."
        ),
        "no_git": "<b>This install is not running from a git repository.</b>",
        "no_remote_branch": (
            "<b>Couldn't find a compatible branch on the ratko remote.</b>"
        ),
        "failed": "<b>Switch failed:</b> <code>{}</code>",
        "done": (
            "<b>Switched to ratko successfully.</b>\n"
            "This helper module will unload itself now."
        ),
        "github": "📖 GitHub",
        "_cmd_doc_switchtoratko": "Create backup and switch this Heroku install to ratko",
    }

    strings_ru = {
        "already": "<b>У тебя уже запущен ratko.</b>",
        "confirm": (
            "<b>Эта команда создаст полный бэкап в Избранном, переключит"
            " этот инстанс с Heroku на ratko, перенесет данные переименованных"
            " модулей и перезапустит юзербот.</b>\n\n"
            "Запусти <code>{prefix}switchtoratko -f</code>, чтобы продолжить."
        ),
        "backing_up": "<b>Создаю бэкап перед переключением...</b>",
        "backup_saved": (
            "<b>Бэкап отправлен в Избранное.</b>\nПереключаю этот инстанс на ratko..."
        ),
        "switching_repo": "<b>Переключаю git remote на ratko...</b>",
        "migrating_db": "<b>Переношу DB-данные модулей под ratko...</b>",
        "installing": "<b>Устанавливаю зависимости ratko...</b>",
        "requirements_failed": (
            "<b>Не удалось поставить зависимости.</b> Репозиторий уже переключен,"
            " но после перезапуска может понадобиться вручную доставить пакеты."
        ),
        "restarting": "<b>Миграция завершена. Перезапускаюсь уже в ratko...</b>",
        "backup_caption": (
            "<b>Бэкап создан перед переходом с Heroku на ratko.</b>\n"
            "Если понадобится откат, ответь на этот файл командой"
            " <code>{prefix}restoreall</code>."
        ),
        "dirty": (
            "<b>В репозитории есть локальные изменения в отслеживаемых файлах.</b>"
            "\nСначала закоммить или убери их в stash, потом повтори переключение."
        ),
        "no_git": "<b>Этот инстанс запущен не из git-репозитория.</b>",
        "no_remote_branch": (
            "<b>На удаленном репозитории ratko не нашлась подходящая ветка.</b>"
        ),
        "failed": "<b>Переключение не удалось:</b> <code>{}</code>",
        "done": (
            "<b>Переход на ratko завершен успешно.</b>\n"
            "Теперь этот вспомогательный модуль сам выгрузится."
        ),
        "github": "📖 GitHub",
        "_cmd_doc_switchtoratko": "Создать бэкап и переключить этот Heroku инстанс на ratko",
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
            await self.invoke("unloadmod", "SwitchToRatko", peer=self.tg_id)

    def _repo_root(self) -> Path:
        return Path(utils.get_base_dir()).parent

    def _repo(self) -> git.Repo:
        try:
            return git.Repo(self._repo_root())
        except git.exc.InvalidGitRepositoryError as e:
            raise MigrationError(self.strings("no_git")) from e

    def _is_already_ratko(self) -> bool:
        try:
            repo = self._repo()
            origin = repo.remote("origin")
            urls = list(origin.urls)
            return any("unsidogandon/ratko" in url for url in urls)
        except Exception:
            return False

    def _raw_db_snapshot(self) -> dict:
        return json.loads(json.dumps(self._db, ensure_ascii=False))

    def _migrated_db_snapshot(self, source: dict) -> dict:
        snapshot = json.loads(json.dumps(source, ensure_ascii=False))

        for old_owner, new_owner in MODULE_OWNER_RENAMES.items():
            old_data = snapshot.pop(old_owner, None)
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

    async def _pip_freeze(self) -> bytes:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "pip",
            "freeze",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout

    async def _build_backup(self, source_db: dict) -> io.BytesIO:
        db_json = json.dumps(
            source_db,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ).encode("utf-8")

        mods = io.BytesIO()
        with zipfile.ZipFile(mods, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(loader.LOADED_MODULES_DIR):
                for file in files:
                    if not file.endswith(f"{self.tg_id}.py"):
                        continue

                    module_path = os.path.join(root, file)
                    with open(module_path, "rb") as module_file:
                        zipf.writestr(file, module_file.read())

            zipf.writestr(
                "db_mods.json",
                json.dumps(
                    self.lookup("Loader").get("loaded_modules", {}),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ).encode("utf-8"),
            )

        mods.seek(0)
        reqs = await self._pip_freeze()

        archive = io.BytesIO()
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y-%H-%M")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("db.json", db_json)
            zf.writestr("mods.zip", mods.getvalue())
            zf.writestr(f"pip-backup-{timestamp}.txt", reqs)

        archive.seek(0)
        archive.name = f"switch-to-ratko-{timestamp}.backup"
        return archive

    async def _send_backup(self, archive: io.BytesIO) -> None:
        await self._client.send_file(
            "me",
            archive,
            caption=self.strings("backup_caption").format(
                prefix=utils.escape_html(self.get_prefix())
            ),
        )

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
            logger.exception("SwitchToRatko requirements install failed")
            return False

    @loader.command()
    async def switchtoratko(self, message: Message):
        if self._is_already_ratko():
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

            await utils.answer(message, self.strings("backing_up"))
            backup = await self._build_backup(source_db)
            await self._send_backup(backup)

            await utils.answer(message, self.strings("backup_saved"))
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
            logger.exception("SwitchToRatko failed")
            await utils.answer(
                message,
                self.strings("failed").format(utils.escape_html(str(e))),
            )
