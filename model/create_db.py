import sqlite3
from decimal import Decimal
import debug
import sys
"""create_db
inputs                          process                     output
 dbpath                         setup adapters              conn
 isolation                      register adapters
                                connect
                                create
"""
def create_db(dbpath, isolation_level=None):
    debug.dlog(f"creating database at {dbpath}")
    """setup adapters"""
    def adapt_decimal(d):
        return str(d)

    def convert_decimal(s):
        return Decimal(s.decode('utf-8'))

    """register"""
    sqlite3.register_adapter(Decimal, adapt_decimal)
    sqlite3.register_converter("DECIMAL", convert_decimal)

    """connect"""
    con = sqlite3.connect(dbpath, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES, isolation_level=isolation_level)

    """create"""
    con.execute("CREATE TABLE IF NOT EXISTS provider("
            "providerId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", addr TEXT NOT NULL UNIQUE"
            ")"
            )

    con.execute("CREATE TABLE IF NOT EXISTS nodeInfo("
            "nodeInfoId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", providerId REFERENCES provider(providerId)"
            ", modelname TEXT DEFAULT ''"
            ", unixtime DECIMAL NOT NULL"
            ")"
            )

    con.execute("CREATE TABLE IF NOT EXISTS offer("
            "offerId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", nodeInfoId REFERENCES nodeInfo(nodeInfoId)"
            ", data JSON NOT NULL"
            ")"
            )

    con.execute("CREATE TABLE IF NOT EXISTS cost("
            "costId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", nodeInfoId REFERENCES nodeInfo(nodeInfoId) NOT NULL"
            ", total DECIMAL NOT NULL"
            ")"
            )

    con.execute("CREATE TABLE IF NOT EXISTS agreement("
            "agreementId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", nodeInfoId REFERENCES nodeInfo(nodeInfoId) NOT NULL"
            ", id TEXT"
            ")"
            )

    try:
        r = con.execute("SELECT COUNT(*) FROM scchema_version").fetchall()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            TOPOVERSION=False
    else:
        TOPOVERSION=True

    if TOPOVERSION:
        print("Uh oh, the version of gc_spy you are invoking is not compatible with an old database.")
        print(f"Please delete (or backup and delete) the file {dbpath} and rerun.")
        sys.exit(1)

    con.execute("CREATE TABLE IF NOT EXISTS schema_version("
            "version INT DEFAULT 2"
            ")"
    )

    """output"""
    return con
