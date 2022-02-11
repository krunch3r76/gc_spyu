# on_run_conclusion.py
# authored by krunch3r
import debug

def console_interface(mySummaryLogger, nodeInfoIds, myModel):
    # provider name, nodeaddress, model, cost

    # update cost table now that invoices have been finalized
    for nodeInfoId in nodeInfoIds:
        # agr_id = myModel.fetch_field_value("SELECT id FROM agreement NATURAL JOIN nodeInfo")
        addr = myModel.fetch_field_value(f"SELECT addr FROM provider NATURAL JOIN nodeInfo WHERE nodeInfoId = {nodeInfoId}")
        debug.dlog(f"updating cost for {addr}")
        myModel.execute("INSERT INTO extra.cost (nodeInfoId, total) VALUES (?, ?)" 
                , [ nodeInfoId, mySummaryLogger.sum_invoices_on(addr) ]
                )

    ss=f"SELECT addr, json_extract(data, '$.\"golem.node.id.name\"') AS nameProvider, modelname, total" \
        f" FROM (select addr FROM provider NATURAL JOIN nodeInfo) AS addr" \
        f" JOIN nodeInfo" \
        f" NATURAL JOIN extra.cost" \
        f" NATURAL JOIN extra.offer" 

    if len(nodeInfoIds) > 1:
        ss+=f" WHERE nodeInfoId IN {tuple(nodeInfoIds)}"
    else:
        ss+=f" WHERE nodeInfoId IN ( {nodeInfoIds[0]} )"
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


def on_run_conclusion(mySummaryLogger, nodeInfoIds, myModel):
    """ work with most recent results """
    console_interface(mySummaryLogger, nodeInfoIds, myModel)

