#!/usr/bin/env python3
"""===============================================================================

        FILE: /Users/nailbiter/Documents/forgithub/20250628-gemini-telegram-gcp/send-keyboard.py

       USAGE: .//Users/nailbiter/Documents/forgithub/20250628-gemini-telegram-gcp/send-keyboard.py

 DESCRIPTION: 

     OPTIONS: ---
REQUIREMENTS: ---
        BUGS: ---
       NOTES: ---
      AUTHOR: Alex Leontiev (alozz1991@gmail.com)
ORGANIZATION: 
     VERSION: ---
     CREATED: 2025-07-06T17:27:21.432433
    REVISION: ---

==============================================================================="""

import click

# from dotenv import load_dotenv
import os
from os import path
from telegram.request import HTTPXRequest
import logging
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Bot,
)
import asyncio
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    # Filters,
)


@click.command()
@click.option("--chat-id", "-c", type=str, default=True)
@click.option("--telegram-token", "-t", "token", required=True, type=str)
def send_keyboard(chat_id, token):
    _columns = 2
    _keyboard = [
        "useless",
        "gym",
        "social",
        "logistics",
        "sleeping",
        "german",
        "parttime",
        "coding",
        "rest",
        "reading",
    ]

    request_handler = HTTPXRequest(http_version="1.1", connection_pool_size=10)
    bot = Bot(token=token, request=request_handler)

    asyncio.run(
        bot.send_message(
            chat_id=chat_id,
            text="北鼻，你在幹什麼？",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(_keyboard[i + j], callback_data=str(i + j))
                        for j in range(_columns)
                        if i + j < len(_keyboard)
                    ]
                    for i in range(0, len(_keyboard), _columns)
                ]
            ),
        )
    )


if __name__ == "__main__":
    #    fn = ".env"
    #    if path.isfile(fn):
    #        logging.warning(f"loading `{fn}`")
    #        load_dotenv(dotenv_path=fn)
    send_keyboard()
