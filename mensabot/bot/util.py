import datetime as dtm
import logging
import sys
from contextlib import contextmanager

import requests
from telegram import Message, MessageEntity, ParseMode, Update
from telegram.ext import CommandHandler

from mensabot.bot.ext import dispatcher
from mensabot.db import CHATS, connection


@contextmanager
def chat_record(id):
    if isinstance(id, Message):
        id = id.chat.id
    elif isinstance(id, Update):
        id = id.message.chat.id
    elif not isinstance(id, int):
        raise ValueError("ID '%s' is not an int." % id)
    with connection() as (conn, execute):
        res = execute(
            CHATS.select().where(CHATS.c.id == id)
        ).fetchone()
        if not res:
            execute(
                CHATS.insert().values(id=id)
            )
            res = execute(
                CHATS.select().where(CHATS.c.id == id)
            ).fetchone()
        yield res


def ensure_date(dt):
    if isinstance(dt, dtm.datetime):
        return dt.date()
    elif isinstance(dt, dtm.date):
        return dt
    else:
        raise ValueError("'%s' can't be converted to a date" % dt)


def get_args(update):
    text = update.message.text  # FIXME message might be None
    for ent in update.message.entities:
        if ent.type == MessageEntity.BOT_COMMAND:
            text = text[:ent.offset] + text[ent.offset + ent.length:]
    return text.strip().split(" ")


com_logger = logging.getLogger("mensabot.bot.command")


def ComHandlerFunc(command, **kwargs):
    # TODO use pass_args param
    def func_decorator(func):
        def func_wrapper(update, ctx):
            try:
                func(update, ctx)
            except:
                com_logger.error("Command /%s failed", command, exc_info=True)
                if sys.exc_info()[0] in [requests.exceptions.ConnectionError, requests.exceptions.Timeout]:
                    ctx.bot.sendMessage(
                        chat_id=update.message.chat_id, text="I got network problems, please try again later! 😢",
                        parse_mode=ParseMode.MARKDOWN)
                else:
                    # FIXME message might be None
                    ctx.bot.sendMessage(
                        chat_id=update.message.chat_id, text="Master, I failed! 😢", parse_mode=ParseMode.MARKDOWN)
                raise

        handler = CommandHandler(command, func_wrapper, **kwargs)
        dispatcher.add_handler(handler)
        func_wrapper.handler = handler
        return func_wrapper

    return func_decorator
