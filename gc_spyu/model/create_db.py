import sqlite3
from decimal import Decimal
import debug
import sys
import pathlib, os, shutil
from pathlib import Path
import tempfile
schema_version=4



def _ensure_compatibility(con, dbpath: str, extradbpath: str):
    rv_compatible = True
    dbpath_as_path = Path(dbpath)
    extradbpath_as_path = Path(extradbpath)

    # check schema
    try:
        recordset = con.execute("SELECT version FROM schema_version").fetchall()
        row=recordset[0]
        schemaCurrent=row[0]
    except: # elaborate
        schemaCurrent=0

    tempdirname=tempfile.gettempdir()
    tempfilepath=Path(tempdirname) / "gc_spyu_db.bak"

    if schemaCurrent < schema_version:
        rv_compatible=False
        print("Uh oh, the version of gc_spy you are invoking is incompatible with an old"
        " database and cannot be upgraded.")
        print(f"I am moving the old database to your temporary directory to"
            f": {tempfilepath}"
                " as it is no longer relevant!")
        input("press enter to acknowledge")
        shutil.move(dbpath, str(tempfilepath))
        os.unlink(extradbpath)

    return rv_compatible




def _connect(dbpath, extradbpath, isolation_level):
    con = sqlite3.connect(dbpath,
            detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES
            , isolation_level=isolation_level)
    con.execute(f"ATTACH '{extradbpath}' AS extra")
    con.execute("PRAGMA foreign_keys=ON")
    return con



"""create_db
inputs                          process                     output
 dbpath                         setup adapters              conn
 isolation                      register adapters
                                connect
                                create
"""
def create_db(dbpath, isolation_level="DEFERRED"):
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
    con = _connect(dbpath, extradbpath, isolation_level)


    if not _ensure_compatibility(con, dbpath, extradbpath):
        con = _connect(dbpath, extradbpath, isolation_level) # reconnect after removal



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

    con.execute("CREATE TABLE IF NOT EXISTS extra.provider ("
            "providerId INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
            ", addr TEXT NOT NULL UNIQUE"
            ")"
            )

    con.execute("CREATE TABLE IF NOT EXISTS extra.nodeInfo ("
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



    ss = "CREATE TABLE IF NOT EXISTS schema_version" \
        "(" + f"version INT NOT NULL" + ")" 
    con.execute(ss)

    # debug

    recordset = con.execute("SELECT version FROM schema_version").fetchall()

    if len(recordset) == 0:
        ss = "INSERT INTO  schema_version (version) VALUES (?)"
        con.execute(ss, (schema_version,) )
        
    """output"""
    return con
