import sqlite3
from decimal import Decimal
import debug
import sys
import pathlib

"""create_db
inputs                          process                     output
 dbpath                         setup adapters              conn
 isolation                      register adapters
                                connect
                                create
"""
def create_db(dbpath, isolation_level=None):
    model_working_dir=pathlib.Path(__file__).resolve().parent
    extradb_file=model_working_dir/"extra.db"
    extradbpath=str(extradb_file)

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
#    con_extra = sqlite3.connect(extrabpath, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES, isolation_level=isolation_level)
    con.execute(f"ATTACH '{extradbpath}' AS extra")
    con.execute("PRAGMA foreign_keys=ON")

    """create"""
    con.execute("CREATE TABLE IF NOT EXISTS provider ("
            "providerId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", addr TEXT NOT NULL UNIQUE"
            ")"
            )

    con.execute("CREATE TABLE IF NOT EXISTS nodeInfo ("
            "nodeInfoId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", providerId REFERENCES provider(providerId)"
            ", modelname TEXT DEFAULT ''"
            ", unixtime DECIMAL NOT NULL"
            ", nodename TEXT NOT NULL"
            ")"
            )

    con.execute("CREATE TABLE IF NOT EXISTS extra.offer ("
            "offerId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", nodeInfoId NOT NULL"
            ", data JSON NOT NULL"
            ")"
            )

    con.execute("CREATE TABLE IF NOT EXISTS extra.cost ("
            "costId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", nodeInfoId NOT NULL"
            ", total DECIMAL NOT NULL"
            ")"
            )

    con.execute("CREATE TABLE IF NOT EXISTS extra.agreement ("
            "agreementId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", nodeInfoId NOT NULL"
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

    schema_version=3

    ss = "CREATE TABLE IF NOT EXISTS schema_version" \
        "(" + f"version INT NOT NULL" + ")" 
    con.execute(ss)

    # debug

    recordset = con.execute("SELECT version FROM schema_version").fetchall()

    if len(recordset) == 0:
        ss = "INSERT INTO  schema_version (version) VALUES (?)"
        con.execute(ss, (schema_version,) )
    else:
        row=recordset[0]
        schemaCurrent=row[0]
        if schemaCurrent < 3:
            print("Uh oh, the version of gc_spy you are invoking is not compatible with an old database.")
            print(f"Please delete (or backup and delete) the file {dbpath} and rerun.")
            sys.exit(1)

    """output"""
    return con
