from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import Message
import asyncio
import logging

from json import loads
import requests
import shutil
import yt_dlp


chat_id = ""
cmds = ["/start", "/help", "/settings", "/token", "/url", "/move"]
token_value = ""
url_value = "https://www.youtube.com/playlist?list=PLcLWzrwuuZhNet5VdtPJBV-K0WDcRSvhJ"
kind_value = "3"
skip_value = "0"


bot = Bot(token="")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class Form(StatesGroup):
    token = State()
    url = State()
    kind = State()
    skip = State()


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    global chat_id
    chat_id = message.chat.id
    await state.clear()
    if token_value == "none":
        await message.answer("Используйте комманду /token, чтобы настроить токен Яндекс Музыки")
    if url_value == "none":
        await message.answer("Используйте комманду /url, чтобы настроить параметры для переноса")
    if token_value != "none" and url_value != "none":
        await message.answer("Используйте комманду /move, чтобы начать перенос\n"
                            "Используйте комманду /settings, просмотреть параметры\n"
                            "Используйте комманду /help, чтобы получить список комманд")

@dp.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Доступные команды: " + " ".join(cmds))

@dp.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(f"Token: {token_value}\n"
                         f"Url: {url_value}\n"
                         f"Kind: {kind_value}\n"
                         f"Skip: {skip_value}")

@dp.message(Command("token"))
async def cmd_token(message: Message, state: FSMContext):
    await state.set_state(Form.token)
    await message.answer("Token? (отправьте слово 'pass' чтобы оставить как есть)")

@dp.message(Command("url"))
async def cmd_url(message: Message, state: FSMContext):
    await state.set_state(Form.url)
    await message.answer("Url? (отправьте слово 'pass' чтобы оставить как есть)")

@dp.message(Command("move"))
async def cmd_move(message: Message, state: FSMContext):
    await state.clear()
    if url_value == "none":
        await message.answer("Укажите ссылку с помощью команды /url")
    if token_value == "none":
        await message.answer("Укажите токен с помощью команды /token")
    if url_value != "none" and token_value != "none":
        await message.answer("Подождите...")

        try:
            download()
            await message.answer("Всё готово")
        except Exception as e:
            await message.reply(f"Не удалось скачать видео: {e}")



@dp.message(Form.token)
async def process_token(message: Message, state: FSMContext):
    global token_value
    if message.text != "pass":
        token_value = message.text
    await state.clear()
    await message.answer(f"Token: {token_value}")

@dp.message(Form.url)
async def process_url(message: Message, state: FSMContext):
    global url_value
    if message.text != "pass":
        url_value = message.text
    await state.set_state(Form.kind)
    await message.answer("Kind? (отправьте слово 'pass' чтобы оставить как есть)")

@dp.message(Form.kind)
async def process_kind(message: Message, state: FSMContext):
    global kind_value
    if message.text != "pass":
        kind_value = message.text
    await state.set_state(Form.skip)
    await message.answer("Skip? (отправьте слово 'pass' чтобы оставить как есть)")

@dp.message(Form.skip)
async def process_skip(message: Message, state: FSMContext):
    global skip_value
    if message.text != "pass":
        skip_value = message.text
    await state.clear()
    await message.answer(f"Используйте команду /move для начала переноса")


# MOVE
def upload(filename, target):
    with open(filename, "rb") as f:
        files = {"file": ("filename", f, "audio/mp3")}
        r = requests.post(url=target, files=files)
    return loads(r.text)

def get_target(filename):
    filename = ''.join(''.join(filename.split('\\')[1:]).split('.')[:-1])
    headers = {"Authorization": f"Bearer {token_value}"}
    target_url = f"https://music.yandex.ru/handlers/ugc-upload.jsx?kind={kind_value}&filename={filename}"
    return loads(requests.get(target_url, headers=headers).text).get("post-target")

def progress_hook(d):
    if d['status'] == 'finished':
        filename = d['filename']
        target = get_target(filename)
        status = upload(filename, target)

        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(bot.send_message(chat_id, status), loop)

def download():
    clear()
    ydl_opts = {
        'outtmpl': '%(title)s.%(ext)s', # output template to name files as <title>.<ext>
        'paths': {'home': dir}, # temp and main files in one folder
        'format': 'ba[ext=m4a]', # bestaudio.m4a
        'retries': 5,
        'quiet': True, # without logs
        'progress': True, # show progress bar
        'skip_unavailable_fragments': True,
	    'noincludeunavailablevideos': True,
	    'ignoreerrors': True,
	    'no_warnings': True,
	    'playliststart': skip_value,
        'progress_hooks': [progress_hook],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(url_value)
    except Exception as e:
        print(e)
    clear()

def clear():
    try:
        shutil.rmtree(dir)
    except:
        pass


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")
