from .create_db import create_db
import debug

class MyModel():
    def __init__(self, dbpath):
        self.con = create_db(dbpath)

    def execute(self, *args):
        debug.dlog(args)
        recordset = None
        recordset = self.con.execute(*args)
        return recordset

    def execute_and_id(self, *args):
        debug.dlog(f"{args} in-transaction: {self.con.in_transaction}")
        recordset_cursor = None
        recordset_cursor = self.con.execute(*args)
        lastrowid = recordset_cursor.lastrowid
        rv = (lastrowid, recordset_cursor,)
        return rv

    def insert_and_id(self, *args):
        return self.execute_and_id(*args)[0]


    def fetch_field_value(self, *args):
        """ get the value of a single field (first of the select statement) or return None """
        field_value = None
        recordset = self.execute(*args).fetchall()
        if len(recordset) == 1:
            field_value=recordset[0][0] # first value of first row
        elif len(recordset) > 1:
            debug.dlog("raising exception")
            raise Exception("expected one row but saw many")

        return field_value


