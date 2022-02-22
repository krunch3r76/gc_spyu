# on_run_conclusion.py
# authored by krunch3r
import debug

def console_interface(mySummaryLogger, nodeInfoIds, myModel, dupIds):
    # provider name, nodeaddress, model, cost
    if len(nodeInfoIds) > 0:
        # update cost table now that invoices have been finalized
        for nodeInfoId in nodeInfoIds:
            addr = myModel.fetch_field_value(f"SELECT addr FROM extra.provider"\
                    + " NATURAL JOIN extra.nodeInfo" \
                    + f" WHERE nodeInfoId = {nodeInfoId}")
            debug.dlog(f"updating cost for {addr}")
            try:
                myModel.execute("INSERT INTO extra.cost (nodeInfoId, total) VALUES (?, ?)" 
                        , [ nodeInfoId, mySummaryLogger.sum_invoices_on(addr) ]
                        )
            except:
                pass # interruptions may result in no cost info.. TODO REVIEW

            myModel.commit()

        ss=f"SELECT addr, json_extract(data, '$.\"golem.node.id.name\"') AS" \
            " nameProvider, modelname, total" \
            f" FROM (select addr FROM extra.provider NATURAL JOIN extra.nodeInfo)" \
            " AS addr" \
            f" JOIN extra.nodeInfo" \
            f" NATURAL JOIN extra.cost" \
            f" NATURAL JOIN extra.offer" 
        ss+=f" WHERE nodeInfoId IN ( {', '.join(map(str,nodeInfoIds))} )"
        ss+=f" GROUP BY nodeInfoId"

        debug.dlog(ss)
        recordset = myModel.execute(ss) 
        records=recordset.fetchall()
        line1=f"node address{' '*(43-12)}\tnode name"
        line2=f" model{' ' * (43-6)}\tcost of procurement in GLM"
        print(f"\n\n{line1}\n{line2}")
        print('-' * (len(line2)+4))
        for row in records:
            print(f"{row[0]}\t{row[1]}")
            print(f" {row[2]}\t{row[3]}")
            print("")

    if len(dupIds) > 0:
        ss = "SELECT nodename, addr, modelname" \
                + " FROM provider NATURAL JOIN nodeInfo" \
                +f" WHERE providerId IN ( {', '.join(map(str,dupIds))} )"
        if len(nodeInfoIds) > 0:
            ss = ss + " AND providerId NOT IN"  \
                    + " ( SELECT providerId FROM extra.nodeInfo" \
                    + " WHERE nodeInfoId NOT IN" \
                    + f" ( {','.join(map(str,nodeInfoIds))} )" \
                    + ")"

        debug.dlog(ss)
        rs = myModel.execute(ss).fetchall()
        if len(rs) > 0:
            max_nodeinfo_len=max([ len(r[0]) for r in rs ])
            max_modelname_len=max([ len(r[2]) for r in rs ])
            width=int(max_nodeinfo_len)+43+1+8
            # line1="node address {0: <{}}".format(' ', width) + "\tnode name"
            lines = []
            for row in rs:
                name = row[0]
                address = row[1]
                modelname = row[2]
                name_address=f"{name}@{address}"
                lines.append(f"{name_address: <{width}}\t{modelname}")
           
            max_line_len = max([ len(line) for line in lines ])
            print("\n\nThe model information for the following nodes were already"
                    " on record")
            print('-' * (max_line_len))
            for line in lines:
                print(line)


def on_run_conclusion(mySummaryLogger, nodeInfoIds, myModel, dupIds):
    """ work with most recent results """
    console_interface(mySummaryLogger, nodeInfoIds, myModel, dupIds)

