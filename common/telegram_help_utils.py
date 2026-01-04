"""===============================================================================

        FILE: /Users/nailbiter/Documents/forgithub/20250628-gemini-telegram-gcp/common/telegram_help_utils.py

       USAGE: (not intended to be directly executed)

 DESCRIPTION: 

     OPTIONS: ---
REQUIREMENTS: ---
        BUGS: ---
       NOTES: ---
      AUTHOR: Alex Leontiev (alozz1991@gmail.com)
ORGANIZATION: 
     VERSION: ---
     CREATED: 2025-11-02T09:29:47.662258
    REVISION: ---

==============================================================================="""

import os
import logging
import typing

import telegram
from alex_leontiev_toolbox_python.utils.logging_helpers import get_configured_logger


class TelegramBotWrapper:
    def __init__(self, token_envvar: str):
        self._logger = get_configured_logger(
            self.__class__.__name__,
            level="INFO",
            log_format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self._logger.info(f"getting token envvar from `{token_envvar}`")
        TELEGRAM_TOKEN = os.environ.get(token_envvar)
        self.bot = telegram.Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
        self._chat_id: typing.Optional[str] = None

    @property
    def is_able_to_work(self):
        return self.bot is not None

    @property
    def chat_id(self) -> typing.Optional[int]:
        return self._chat_id

    @chat_id.setter
    def chat_id(self, chat_id: typing.Optional[int]) -> None:
        self._logger.info(f"set chat_id to {chat_id}")
        self._chat_id = chat_id

    async def send_message(self, text: str, chat_id: typing.Optional[int] = None):
        return await self.bot.send_message(
            text=text, chat_id=self._chat_id if chat_id is None else chat_id
        )
