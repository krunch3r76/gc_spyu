import sqlite3
from decimal import Decimal
import debug

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

    con.execute("CREATE TABLE IF NOT EXISTS topology("
            "topologyId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", providerId REFERENCES provider_id(providerId)"
            ", svg TEXT DEFAULT ''"
            ", asc TEXT DEFAULT ''"
            ", xml TEXT DEFAULT ''"
            ", modelname TEXT DEFAULT ''"
            ", unixtime DECIMAL NOT NULL"
            ")"
            )

    con.execute("CREATE TABLE IF NOT EXISTS offer("
            "offerId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", topologyId REFERENCES topology(topologyId)"
            ", data JSON NOT NULL"
            ")"
            )

    con.execute("CREATE TABLE IF NOT EXISTS cost("
            "costId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", topologyId REFERENCES topology(topologyId) NOT NULL"
            ", total DECIMAL NOT NULL"
            ")"
            )

    con.execute("CREATE TABLE IF NOT EXISTS agreement("
            "agreementId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", topologyId REFERENCES topology(topologyId) NOT NULL"
            ", id TEXT"
            ")"
            )
    """output"""
    return con
