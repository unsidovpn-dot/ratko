# ---------------------------------------------------------------------------------
# Name: ExteraGramEmojiTest
# Description: Test exteraGram emoji fallback paths
# Author: @unsidogandon
# Commands: xetest xeanswer xedirect xeedit xefile xephoto xeinline xelist xegallery
# meta developer: @unsidogandon
# ---------------------------------------------------------------------------------

from herokutl.tl.types import Message

from .. import loader, utils

TEST_IMAGE = "https://raw.githubusercontent.com/unsidogandon/ratko/main/upd.jpg"
TG_EMOJI = '<tg-emoji emoji-id="5449599833973203438">🧡</tg-emoji>'
LEGACY_EMOJI = "<emoji document_id=5300759756669984376>🚫</emoji>"


@loader.tds
class ExteraGramEmojiTest(loader.Module):
    """Test exteraGram emoji fallback in different send paths"""

    strings = {
        "name": "ExteraGramEmojiTest",
        "menu": (
            "<b>exteraGram emoji test module</b>\n\n"
            "<code>.xeanswer</code> utils.answer\n"
            "<code>.xedirect</code> client.send_message\n"
            "<code>.xeedit</code> client.edit_message\n"
            "<code>.xefile</code> client.send_file caption\n"
            "<code>.xephoto</code> client.send_photo caption\n"
            "<code>.xeinline</code> inline form\n"
            "<code>.xelist</code> inline list\n"
            "<code>.xegallery</code> inline gallery"
        ),
        "answer": (
            f"{TG_EMOJI} <b>utils.answer test</b>\n"
            f"{LEGACY_EMOJI} <b>legacy emoji tag test</b>"
        ),
        "direct": (
            f"{TG_EMOJI} <b>client.send_message test</b>\n"
            f"{LEGACY_EMOJI} <b>legacy emoji tag test</b>"
        ),
        "edit": (
            f"{TG_EMOJI} <b>client.edit_message test</b>\n"
            f"{LEGACY_EMOJI} <b>legacy emoji tag test</b>"
        ),
        "caption": (
            f"{TG_EMOJI} <b>media caption test</b>\n"
            f"{LEGACY_EMOJI} <b>legacy emoji tag test</b>"
        ),
        "inline": (
            f"{TG_EMOJI} <b>inline form test</b>\n"
            f"{LEGACY_EMOJI} <b>legacy emoji tag test</b>"
        ),
        "list1": (
            f"{TG_EMOJI} <b>inline list page 1</b>\n"
            f"{LEGACY_EMOJI} <b>legacy emoji tag test</b>"
        ),
        "list2": (
            f"{TG_EMOJI} <b>inline list page 2</b>\n"
            f"{LEGACY_EMOJI} <b>switch pages to test edits</b>"
        ),
        "gallery1": (
            f"{TG_EMOJI} <b>inline gallery page 1</b>\n"
            f"{LEGACY_EMOJI} <b>caption test</b>"
        ),
        "gallery2": (
            f"{TG_EMOJI} <b>inline gallery page 2</b>\n"
            f"{LEGACY_EMOJI} <b>caption edit test</b>"
        ),
        "close": "Close",
        "_cmd_doc_xetest": "Show available exteraGram emoji tests",
        "_cmd_doc_xeanswer": "Test exteraGram emojis through utils.answer",
        "_cmd_doc_xedirect": "Test exteraGram emojis through client.send_message",
        "_cmd_doc_xeedit": "Test exteraGram emojis through client.edit_message",
        "_cmd_doc_xefile": "Test exteraGram emojis in send_file caption",
        "_cmd_doc_xephoto": "Test exteraGram emojis in send_photo caption",
        "_cmd_doc_xeinline": "Test exteraGram emojis in inline form",
        "_cmd_doc_xelist": "Test exteraGram emojis in inline list",
        "_cmd_doc_xegallery": "Test exteraGram emojis in inline gallery",
    }

    async def _close(self, call):
        await call.delete()

    @loader.command()
    async def xetest(self, message: Message):
        await utils.answer(message, self.strings("menu"))

    @loader.command()
    async def xeanswer(self, message: Message):
        await utils.answer(message, self.strings("answer"))

    @loader.command()
    async def xedirect(self, message: Message):
        await self._client.send_message(message.peer_id, self.strings("direct"))

    @loader.command()
    async def xeedit(self, message: Message):
        await self._client.edit_message(
            message.peer_id, message.id, self.strings("edit")
        )

    @loader.command()
    async def xefile(self, message: Message):
        await self._client.send_file(
            message.peer_id,
            TEST_IMAGE,
            caption=self.strings("caption"),
            reply_to=getattr(message, "reply_to_msg_id", None),
        )

    @loader.command()
    async def xephoto(self, message: Message):
        await self._client.send_photo(
            message.peer_id,
            TEST_IMAGE,
            caption=self.strings("caption"),
            reply_to=getattr(message, "reply_to_msg_id", None),
        )

    @loader.command()
    async def xeinline(self, message: Message):
        await self.inline.form(
            message=message,
            text=self.strings("inline"),
            reply_markup=[[{"text": self.strings("close"), "callback": self._close}]],
        )

    @loader.command()
    async def xelist(self, message: Message):
        await self.inline.list(
            message=message,
            strings=[self.strings("list1"), self.strings("list2")],
        )

    @loader.command()
    async def xegallery(self, message: Message):
        await self.inline.gallery(
            message=message,
            next_handler=[TEST_IMAGE, TEST_IMAGE],
            caption=[self.strings("gallery1"), self.strings("gallery2")],
        )
