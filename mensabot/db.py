import logging
from contextlib import ExitStack, closing, contextmanager

from sqlalchemy import *

from mensabot.config_default import ECHO_SQL, DATABASE

logger = logging.getLogger("mensabot.db")

SCHEMA_VERSION = 2
metadata = MetaData()
CHATS = Table(
    'chats', metadata,
    Column('id', Integer, primary_key=True),
    Column('price_category', Integer, server_default=text("0")),
    Column('template', String, server_default=text("NULL")),
    Column('locale', String, server_default=text("NULL")),
    Column('push_time', Time, server_default=text("NULL")),
    Column('push_sound', Boolean, server_default=text("1")),
    Column('notify_change', Boolean, server_default=text("0")),
    Column('notify_change_sound', Boolean, server_default=text("0")),
    Column('update_menu', Boolean, server_default=text("1")),
)

SQL_ENGINE = create_engine(DATABASE, echo=ECHO_SQL)


@contextmanager
def connection():
    with ExitStack() as s:
        conn = s.enter_context(closing(SQL_ENGINE.connect()))
        execute = lambda *args, **kwargs: s.enter_context(closing(conn.execute(*args, **kwargs)))
        yield conn, execute


with connection() as (conn, execute):
    res = execute("PRAGMA user_version")
    version = res.fetchone()[0]

    if version == 0:
        logger.info("Migrating from version %s to version %s" % (version, SCHEMA_VERSION))
        metadata.create_all(SQL_ENGINE)
        execute("PRAGMA user_version = %s;" % (SCHEMA_VERSION,))
    elif version == 1:
        logger.info("Migrating from version %s to version %s" % (version, SCHEMA_VERSION))
        execute("ALTER TABLE chats RENAME TO chats_backup;")
        metadata.create_all(SQL_ENGINE)
        execute(
            "INSERT INTO chats (id, price_category, template, locale, push_time) "
            "SELECT id, price_category, template, locale, notification_time FROM chats_backup;"
        )
        execute("DROP TABLE chats_backup;")
        execute("PRAGMA user_version = %s;" % SCHEMA_VERSION)
    elif version == SCHEMA_VERSION:
        logger.debug("Database version %s is up-to-date" % version)
    elif version > SCHEMA_VERSION:
        raise AssertionError("Database version %s is from a more recent program version (code v %s)!" %
                             (version, SCHEMA_VERSION))
