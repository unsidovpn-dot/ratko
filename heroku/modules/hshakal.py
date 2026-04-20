# meta developer: @h_m_256

import asyncio
import contextlib
import logging
import os
import random
import string
import gzip
import shutil
from datetime import datetime as dt

from herokutl.tl.types import DocumentAttributeVideo, Message

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class HShakalMod(loader.Module):
    """Модуль для экстремального ухудшения качества видео, звука, фото и стикеров"""

    strings = {
        "name": "h:shakal",
        "no_reply": "⏳ шох репли",
        "not_media": "⏳ гой репли",
        "not_photo_video": "⏳ гой репли",
        "downloading_video": "⏳ скачиваю ратко",
        "download_failed_video": "⏳ ратко не скачалась",
        "processing_video": "⏳ шахаю ратко",
        "uploading_video": "⏳ шахаю",
        "video_error": "⏳ ошибка ратко",
        "general_error": "⏳ ошибка ратко",
        "downloading_photo": "⏳ скачиваю ратко",
        "download_failed_photo": "⏳ ошибка ратко",
        "processing_photo": "⏳ шахаю ратко",
        "uploading_photo": "⏳ шахаю",
        "photo_error": "⏳ ошибка ратко",
        "invalid_level": "⏳ инвалид шах до 50 левела",
        "downloading_sticker": "⏳ скачиваю ратко",
        "download_failed_sticker": "⏳ ошибка ратко",
        "processing_sticker": "⏳ шахаю ратко",
        "uploading_sticker": "⏳ все еще шахаю",
        "sticker_error": "⏳ ошибка ратко",
        "animated_not_supported": "⏳ медиа гавна",
    }

    async def _run_ffmpeg(self, cmd, timeout=120):
        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            return process.returncode, stdout, stderr
        except asyncio.TimeoutError:
            if process:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
            return -1, b"", b"Timeout exceeded"
        except Exception as e:
            if process:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
            return -1, b"", str(e).encode()

    def _get_video_params(self, level):
        level = max(1, min(50, level))

        video_bitrate = int(1000 - (level - 1) * (1000 - 5) / 49)
        audio_bitrate = int(64 - (level - 1) * (64 - 1) / 49)

        if level <= 10:
            audio_freq = "22050"
        elif level <= 25:
            audio_freq = "11025"
        else:
            audio_freq = "8000"

        fps = max(5, int(30 - (level - 1) * 25 / 49))
        scale = max(120, int(720 - (level - 1) * 600 / 49))

        return {
            "video_bitrate": f"{video_bitrate}k",
            "audio_bitrate": f"{audio_bitrate}k",
            "audio_freq": audio_freq,
            "fps": str(fps),
            "scale": str(scale),
        }

    def _get_photo_params(self, level):
        level = max(1, min(50, level))
        quality = max(1, int(20 - (level - 1) * 19 / 49))
        scale = max(0.05, 1.0 - (level - 1) * 0.95 / 49)
        return {"quality": quality, "scale": scale}

    @loader.command()
    async def шакал(self, message: Message):
        """[1-50] <реплай на видео/фото/стикер> - экстремально ухудшить качество"""
        reply = await message.get_reply_message()

        if not reply:
            await utils.answer(message, self.strings("no_reply"))
            return

        if not reply.file and not reply.photo and not reply.sticker:
            await utils.answer(message, self.strings("not_media"))
            return

        is_video = False
        is_photo = False
        is_sticker = False
        is_animated_sticker = False
        is_video_sticker = False

        if reply.sticker:
            is_sticker = True
            if reply.file:
                mime = reply.file.mime_type or ""
                if mime == "application/x-tgsticker":
                    is_animated_sticker = True
                elif mime == "video/webm":
                    is_video_sticker = True
        elif reply.photo:
            is_photo = True
        elif reply.file and reply.file.mime_type:
            if reply.file.mime_type.startswith("video/"):
                is_video = True
            elif reply.file.mime_type.startswith("image/"):
                is_photo = True

        if not is_video and not is_photo and not is_sticker:
            await utils.answer(message, self.strings("not_photo_video"))
            return

        args = utils.get_args_raw(message)

        level = 25
        if args:
            try:
                level = int(args)
                if level < 1 or level > 50:
                    await utils.answer(message, self.strings("invalid_level"))
                    return
            except ValueError:
                level = 25

        if is_video:
            await self._process_video(message, reply, level)
        elif is_sticker:
            if is_animated_sticker:
                await self._process_animated_sticker(message, reply, level)
            elif is_video_sticker:
                await self._process_video_sticker(message, reply, level)
            else:
                await self._process_static_sticker(message, reply, level)
        else:
            await self._process_photo(message, reply, level)

    @loader.command()
    async def ffmpeg(self, message: Message):
        """Показать команду установки ffmpeg"""
        await utils.answer(
            message,
            'команда для установки ffmpeg\n<pre><code class="language-bash">.terminal sudo apt update && sudo apt install ffmpeg libavcodec-dev libavutil-dev libavformat-dev libswscale-dev libavdevice-dev -y</code></pre>',
        )

    async def _process_video(self, message, reply, level):
        params = self._get_video_params(level)
        timestamp = str(int(dt.now().timestamp()))
        rand_str = "".join(random.choices(string.ascii_letters + string.digits, k=8))

        input_file = f"temp_input_{timestamp}_{rand_str}.mp4"
        output_file = f"temp_output_{timestamp}_{rand_str}.mp4"

        try:
            msg = await utils.answer(message, self.strings("downloading_video"))
            await reply.download_media(input_file)

            if not os.path.exists(input_file) or os.path.getsize(input_file) == 0:
                await utils.answer(msg, self.strings("download_failed_video"))
                return

            msg = await utils.answer(msg, self.strings("processing_video").format(level))

            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                input_file,
                "-c:v",
                "libx264",
                "-b:v",
                params["video_bitrate"],
                "-c:a",
                "aac",
                "-b:a",
                params["audio_bitrate"],
                "-ar",
                params["audio_freq"],
                "-ac",
                "1",
                "-vf",
                f'scale={params["scale"]}:-2',
                "-r",
                params["fps"],
                "-preset",
                "ultrafast",
                "-movflags",
                "+faststart",
                output_file,
            ]

            returncode, stdout, stderr = await self._run_ffmpeg(cmd, timeout=180)

            if returncode != 0:
                logger.error("ffmpeg video error: %s", (stderr or b"")[-500:])
                simple_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    input_file,
                    "-c:v",
                    "libx264",
                    "-b:v",
                    params["video_bitrate"],
                    "-c:a",
                    "aac",
                    "-b:a",
                    params["audio_bitrate"],
                    "-ar",
                    params["audio_freq"],
                    "-ac",
                    "1",
                    "-preset",
                    "ultrafast",
                    "-movflags",
                    "+faststart",
                    output_file,
                ]
                returncode, stdout, stderr = await self._run_ffmpeg(simple_cmd, timeout=180)

                if returncode != 0:
                    copy_cmd = [
                        "ffmpeg",
                        "-y",
                        "-i",
                        input_file,
                        "-c:v",
                        "libx264",
                        "-b:v",
                        params["video_bitrate"],
                        "-an",
                        "-preset",
                        "ultrafast",
                        output_file,
                    ]
                    returncode, stdout, stderr = await self._run_ffmpeg(copy_cmd, timeout=180)

                    if returncode != 0:
                        await utils.answer(msg, self.strings("video_error"))
                        return

            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                await utils.answer(msg, self.strings("video_error"))
                return

            msg = await utils.answer(msg, self.strings("uploading_video"))
            await message.client.send_file(
                message.to_id,
                output_file,
                reply_to=reply.id if reply else None,
                video_note=False,
                supports_streaming=True,
                silent=True,
                attributes=[
                    DocumentAttributeVideo(
                        duration=0,
                        w=0,
                        h=0,
                        round_message=False,
                        supports_streaming=True,
                    )
                ],
            )

            await msg.delete()
        except Exception as e:
            logger.error("Video processing error: %s", e, exc_info=True)
            await utils.answer(message, self.strings("general_error").format(str(e)[:100]))
        finally:
            for file in [input_file, output_file]:
                if os.path.exists(file):
                    with contextlib.suppress(Exception):
                        os.remove(file)

    async def _process_photo(self, message, reply, level):
        params = self._get_photo_params(level)
        timestamp = str(int(dt.now().timestamp()))
        rand_str = "".join(random.choices(string.ascii_letters + string.digits, k=8))

        input_file = f"temp_input_{timestamp}_{rand_str}.png"
        temp_small = f"temp_small_{timestamp}_{rand_str}.png"
        output_file = f"temp_output_{timestamp}_{rand_str}.jpg"

        try:
            msg = await utils.answer(message, self.strings("downloading_photo"))
            await reply.download_media(input_file)

            if not os.path.exists(input_file) or os.path.getsize(input_file) == 0:
                await utils.answer(msg, self.strings("download_failed_photo"))
                return

            msg = await utils.answer(msg, self.strings("processing_photo").format(level))

            scale = params["scale"]
            quality = params["quality"]

            scale_down_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                input_file,
                "-vf",
                f"scale=iw*{scale}:ih*{scale}:flags=bilinear",
                "-pix_fmt",
                "rgb24",
                temp_small,
            ]
            returncode, stdout, stderr = await self._run_ffmpeg(scale_down_cmd, timeout=60)

            if returncode != 0:
                alt_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    input_file,
                    "-vf",
                    f"scale=iw*{scale}:-1",
                    temp_small,
                ]
                returncode, stdout, stderr = await self._run_ffmpeg(alt_cmd, timeout=60)

                if returncode != 0:
                    simple_cmd = [
                        "ffmpeg",
                        "-y",
                        "-i",
                        input_file,
                        "-q:v",
                        "31",
                        output_file,
                    ]
                    returncode, stdout, stderr = await self._run_ffmpeg(simple_cmd, timeout=60)
                    if returncode != 0:
                        await utils.answer(msg, self.strings("photo_error"))
                        return

                    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                        msg = await utils.answer(msg, self.strings("uploading_photo"))
                        await message.client.send_file(
                            message.to_id,
                            output_file,
                            reply_to=reply.id if reply else None,
                            silent=True,
                        )
                        await msg.delete()
                        return

            if os.path.exists(temp_small) and os.path.getsize(temp_small) > 0:
                scale_up_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    temp_small,
                    "-vf",
                    f"scale=iw/{scale}:ih/{scale}:flags=neighbor",
                    "-q:v",
                    str(max(2, 31 - quality)),
                    output_file,
                ]
                returncode, stdout, stderr = await self._run_ffmpeg(scale_up_cmd, timeout=60)

                if returncode != 0:
                    alt_up_cmd = [
                        "ffmpeg",
                        "-y",
                        "-i",
                        temp_small,
                        "-q:v",
                        "31",
                        output_file,
                    ]
                    returncode, stdout, stderr = await self._run_ffmpeg(alt_up_cmd, timeout=60)

                    if returncode != 0:
                        shutil.copy(temp_small, output_file)

            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                if os.path.exists(temp_small) and os.path.getsize(temp_small) > 0:
                    shutil.copy(temp_small, output_file)
                else:
                    await utils.answer(msg, self.strings("photo_error"))
                    return

            msg = await utils.answer(msg, self.strings("uploading_photo"))
            await message.client.send_file(
                message.to_id,
                output_file,
                reply_to=reply.id if reply else None,
                silent=True,
            )
            await msg.delete()
        except Exception as e:
            logger.error("Photo processing error: %s", e, exc_info=True)
            await utils.answer(message, self.strings("general_error").format(str(e)[:100]))
        finally:
            for file in [input_file, temp_small, output_file]:
                if os.path.exists(file):
                    with contextlib.suppress(Exception):
                        os.remove(file)

    async def _process_static_sticker(self, message, reply, level):
        params = self._get_photo_params(level)
        timestamp = str(int(dt.now().timestamp()))
        rand_str = "".join(random.choices(string.ascii_letters + string.digits, k=8))

        input_file = f"temp_sticker_{timestamp}_{rand_str}.webp"
        temp_png = f"temp_sticker_png_{timestamp}_{rand_str}.png"
        temp_small = f"temp_sticker_small_{timestamp}_{rand_str}.png"
        output_file = f"temp_sticker_out_{timestamp}_{rand_str}.webp"

        try:
            msg = await utils.answer(message, self.strings("downloading_sticker"))
            await reply.download_media(input_file)

            if not os.path.exists(input_file) or os.path.getsize(input_file) == 0:
                await utils.answer(msg, self.strings("download_failed_sticker"))
                return

            msg = await utils.answer(msg, self.strings("processing_sticker").format(level))

            convert_cmd = ["ffmpeg", "-y", "-i", input_file, temp_png]
            returncode, stdout, stderr = await self._run_ffmpeg(convert_cmd, timeout=60)
            if returncode != 0:
                await utils.answer(msg, self.strings("sticker_error"))
                return

            scale = params["scale"]
            scale_down_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                temp_png,
                "-vf",
                f"scale=iw*{scale}:ih*{scale}:flags=bilinear",
                temp_small,
            ]
            returncode, stdout, stderr = await self._run_ffmpeg(scale_down_cmd, timeout=60)
            if returncode != 0:
                alt_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    temp_png,
                    "-vf",
                    f"scale=iw*{scale}:-1",
                    temp_small,
                ]
                returncode, stdout, stderr = await self._run_ffmpeg(alt_cmd, timeout=60)

            if os.path.exists(temp_small) and os.path.getsize(temp_small) > 0:
                scale_up_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    temp_small,
                    "-vf",
                    f"scale=iw/{scale}:ih/{scale}:flags=neighbor",
                    "-quality",
                    str(max(1, 100 - level * 2)),
                    output_file,
                ]
                returncode, stdout, stderr = await self._run_ffmpeg(scale_up_cmd, timeout=60)
                if returncode != 0:
                    simple_cmd = [
                        "ffmpeg",
                        "-y",
                        "-i",
                        temp_small,
                        "-quality",
                        "1",
                        output_file,
                    ]
                    returncode, stdout, stderr = await self._run_ffmpeg(simple_cmd, timeout=60)

            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                await utils.answer(msg, self.strings("sticker_error"))
                return

            msg = await utils.answer(msg, self.strings("uploading_sticker"))
            await message.client.send_file(
                message.to_id,
                output_file,
                reply_to=reply.id if reply else None,
                silent=True,
            )
            await msg.delete()
        except Exception as e:
            logger.error("Static sticker error: %s", e, exc_info=True)
            await utils.answer(message, self.strings("general_error").format(str(e)[:100]))
        finally:
            for file in [input_file, temp_png, temp_small, output_file]:
                if os.path.exists(file):
                    with contextlib.suppress(Exception):
                        os.remove(file)

    async def _process_video_sticker(self, message, reply, level):
        params = self._get_video_params(level)
        timestamp = str(int(dt.now().timestamp()))
        rand_str = "".join(random.choices(string.ascii_letters + string.digits, k=8))

        input_file = f"temp_vsticker_{timestamp}_{rand_str}.webm"
        output_file = f"temp_vsticker_out_{timestamp}_{rand_str}.mp4"

        try:
            msg = await utils.answer(message, self.strings("downloading_sticker"))
            await reply.download_media(input_file)

            if not os.path.exists(input_file) or os.path.getsize(input_file) == 0:
                await utils.answer(msg, self.strings("download_failed_sticker"))
                return

            msg = await utils.answer(msg, self.strings("processing_sticker").format(level))
            scale_val = max(64, int(512 - (level - 1) * 448 / 49))

            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                input_file,
                "-c:v",
                "libx264",
                "-b:v",
                params["video_bitrate"],
                "-vf",
                f"scale={scale_val}:-2",
                "-r",
                params["fps"],
                "-an",
                "-t",
                "3",
                "-preset",
                "ultrafast",
                "-movflags",
                "+faststart",
                output_file,
            ]
            returncode, stdout, stderr = await self._run_ffmpeg(cmd, timeout=120)

            if returncode != 0:
                simple_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    input_file,
                    "-c:v",
                    "libx264",
                    "-b:v",
                    "50k",
                    "-an",
                    "-preset",
                    "ultrafast",
                    "-movflags",
                    "+faststart",
                    output_file,
                ]
                returncode, stdout, stderr = await self._run_ffmpeg(simple_cmd, timeout=120)
                if returncode != 0:
                    await utils.answer(msg, self.strings("sticker_error"))
                    return

            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                await utils.answer(msg, self.strings("sticker_error"))
                return

            msg = await utils.answer(msg, self.strings("uploading_sticker"))
            await message.client.send_file(
                message.to_id,
                output_file,
                reply_to=reply.id if reply else None,
                video_note=False,
                supports_streaming=True,
                silent=True,
                attributes=[
                    DocumentAttributeVideo(
                        duration=3,
                        w=scale_val,
                        h=scale_val,
                        round_message=False,
                        supports_streaming=True,
                    )
                ],
            )
            await msg.delete()
        except Exception as e:
            logger.error("Video sticker error: %s", e, exc_info=True)
            await utils.answer(message, self.strings("general_error").format(str(e)[:100]))
        finally:
            for file in [input_file, output_file]:
                if os.path.exists(file):
                    with contextlib.suppress(Exception):
                        os.remove(file)

    async def _process_animated_sticker(self, message, reply, level):
        params = self._get_video_params(level)
        timestamp = str(int(dt.now().timestamp()))
        rand_str = "".join(random.choices(string.ascii_letters + string.digits, k=8))

        input_file = f"temp_tgs_{timestamp}_{rand_str}.tgs"
        temp_json = f"temp_tgs_{timestamp}_{rand_str}.json"
        temp_gif = f"temp_tgs_{timestamp}_{rand_str}.gif"
        output_file = f"temp_tgs_out_{timestamp}_{rand_str}.mp4"
        frame_files = []
        palette_file = f"temp_palette_{timestamp}_{rand_str}.png"

        try:
            msg = await utils.answer(message, self.strings("downloading_sticker"))
            await reply.download_media(input_file)

            if not os.path.exists(input_file) or os.path.getsize(input_file) == 0:
                await utils.answer(msg, self.strings("download_failed_sticker"))
                return

            msg = await utils.answer(msg, self.strings("processing_sticker").format(level))

            try:
                with gzip.open(input_file, "rb") as f_in:
                    with open(temp_json, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            except Exception as e:
                logger.error("TGS unpack error: %s", e)
                await utils.answer(msg, self.strings("sticker_error"))
                return

            rlottie_available = False
            try:
                from rlottie_python import LottieAnimation

                rlottie_available = True
            except ImportError:
                pass

            if rlottie_available:
                try:
                    anim = LottieAnimation.from_file(temp_json)
                    frames = anim.lottie_animation_get_totalframe()

                    for i in range(frames):
                        frame_file = f"temp_frame_{timestamp}_{rand_str}_{i:04d}.png"
                        anim.lottie_animation_render(i)
                        anim.save_frame(frame_file)
                        frame_files.append(frame_file)

                    gif_cmd = [
                        "ffmpeg",
                        "-y",
                        "-framerate",
                        "30",
                        "-i",
                        f"temp_frame_{timestamp}_{rand_str}_%04d.png",
                        "-vf",
                        "palettegen",
                        palette_file,
                    ]
                    await self._run_ffmpeg(gif_cmd, timeout=60)

                    gif_cmd2 = [
                        "ffmpeg",
                        "-y",
                        "-framerate",
                        "30",
                        "-i",
                        f"temp_frame_{timestamp}_{rand_str}_%04d.png",
                        "-i",
                        palette_file,
                        "-lavfi",
                        "paletteuse",
                        temp_gif,
                    ]
                    await self._run_ffmpeg(gif_cmd2, timeout=60)
                except Exception as e:
                    logger.error("rlottie error: %s", e)
                    await utils.answer(msg, self.strings("animated_not_supported"))
                    return
            else:
                await utils.answer(msg, self.strings("animated_not_supported"))
                return

            if not os.path.exists(temp_gif) or os.path.getsize(temp_gif) == 0:
                await utils.answer(msg, self.strings("sticker_error"))
                return

            scale_val = max(64, int(256 - (level - 1) * 192 / 49))
            shakal_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                temp_gif,
                "-c:v",
                "libx264",
                "-b:v",
                params["video_bitrate"],
                "-vf",
                f"scale={scale_val}:-2",
                "-r",
                params["fps"],
                "-preset",
                "ultrafast",
                "-movflags",
                "+faststart",
                output_file,
            ]
            returncode, stdout, stderr = await self._run_ffmpeg(shakal_cmd, timeout=120)

            if returncode != 0:
                simple_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    temp_gif,
                    "-c:v",
                    "libx264",
                    "-b:v",
                    "50k",
                    "-vf",
                    f"scale={scale_val}:-2",
                    "-preset",
                    "ultrafast",
                    "-movflags",
                    "+faststart",
                    output_file,
                ]
                returncode, stdout, stderr = await self._run_ffmpeg(simple_cmd, timeout=120)
                if returncode != 0:
                    await utils.answer(msg, self.strings("sticker_error"))
                    return

            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                await utils.answer(msg, self.strings("sticker_error"))
                return

            msg = await utils.answer(msg, self.strings("uploading_sticker"))
            await message.client.send_file(
                message.to_id,
                output_file,
                reply_to=reply.id if reply else None,
                video_note=False,
                supports_streaming=True,
                silent=True,
                attributes=[
                    DocumentAttributeVideo(
                        duration=3,
                        w=scale_val,
                        h=scale_val,
                        round_message=False,
                        supports_streaming=True,
                    )
                ],
            )
            await msg.delete()
        except Exception as e:
            logger.error("Animated sticker error: %s", e, exc_info=True)
            await utils.answer(message, self.strings("general_error").format(str(e)[:100]))
        finally:
            files_to_clean = [input_file, temp_json, temp_gif, output_file, palette_file] + frame_files
            for file in files_to_clean:
                if os.path.exists(file):
                    with contextlib.suppress(Exception):
                        os.remove(file)
