import logging
import math
import sched
import time as systime
from contextlib import ExitStack, closing
from datetime import datetime, time, timedelta

from sqlalchemy import and_

from mensabot.bot.ext import updater
from mensabot.bot.command.mensa import send_menu_message
from mensabot.db import CHATS, SQL_ENGINE
from mensabot.mensa import clear_caches, get_menu_day

SCHED = sched.scheduler(systime.time, systime.sleep)
SCHED_INTERVAL = 1

logger = logging.getLogger("mensabot.sched")


def run_sched():
    running = True
    while running:
        try:
            SCHED.run(blocking=True)
        except KeyboardInterrupt:
            running = False
            logger.info("KeyboardInterrupt, shutting down.", exc_info=1)
            updater.stop()
        except:
            logger.error("Exception from scheduler, restarting.", exc_info=1)


def schedule_notification(now=None):
    if not now:
        now = datetime.now()
        now = now.replace(minute=math.floor(now.minute / SCHED_INTERVAL) * SCHED_INTERVAL,
                          second=0, microsecond=0)
    later = now + timedelta(minutes=SCHED_INTERVAL)

    if not get_menu_day(now):
        later = (later + timedelta(days=1)).replace(hour=0, minute=0)
        logger.debug("Not sending any notifications at {:%Y-%m-%d %H:%M} as no menu is available".format(now))
    else:
        logger.debug("Scheduling notifications between {:%H:%M} and {:%H:%M}".format(now, later))

    SCHED.enterabs(later.timestamp(), 10, schedule_notification, [later])

    with ExitStack() as s:
        conn = s.enter_context(closing(SQL_ENGINE.connect()))
        res = s.enter_context(closing(conn.execute(
            CHATS.select()
                .where(and_(CHATS.c.notification_time >= now.time(), CHATS.c.notification_time < later.time()))
                .order_by(CHATS.c.notification_time.asc())
        )))
        for row in res:
            notify_time = datetime.combine(now.date(), row.notification_time)
            logger.debug("Scheduling notification to {} for {:%H:%M}".format(row, notify_time))
            SCHED.enterabs(notify_time.timestamp(), 100, send_menu_message, [notify_time, row, row.id])


def schedule_clear_cache():
    now = datetime.now()
    SCHED.enterabs(datetime.combine((now + timedelta(days=7 - now.weekday())).date(), time(1, 0)).timestamp(),
                   1000, schedule_clear_cache)
    clear_caches()