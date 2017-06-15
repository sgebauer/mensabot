import argparse
import os

from telegram import ParseMode

from mensabot.bot.ext import updater
from mensabot.bot.tasks import SCHED


def main():
    if not os.path.isfile("mensabot.sqlite"):
        raise AssertionError(
            "Could not find 'mensabot.sqlite'. Please change to the directory containing the database.")
    from mensabot.db import CHATS, connection

    parser = argparse.ArgumentParser(description='Broadcast a message to all mensabot users.')
    parser.add_argument('--silent', action='store_true')
    parser.add_argument('--test', action='store_true')
    parser.add_argument('message', action='store')
    args = parser.parse_args()

    with connection() as (conn, execute):
        res = execute(CHATS.select())
        rows = res.fetchall()
        for row in rows:
            if args.test and row.id != 114998496:
                print("Skipping %s" % row)
                continue
            print("Broadcasting to %s" % row)
            updater.bot.sendMessage(chat_id=row.id, text=args.message, parse_mode=ParseMode.MARKDOWN,
                                    disable_notification=args.silent)


if __name__ == "__main__":
    main()
    SCHED.run()
