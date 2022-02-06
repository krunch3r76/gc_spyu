# on_run_conclusion.py
# authored by krunch3r
import debug

def console_interface(nodeInfoIds, myModel):
    # provider name, nodeaddress, model, cost
    ss=f"SELECT addr, json_extract(data, '$.\"golem.node.id.name\"') AS nameProvider, modelname, total" \
        f" FROM (select addr FROM provider NATURAL JOIN nodeInfo) AS addr" \
        f" JOIN nodeInfo" \
        f" NATURAL JOIN cost" \
        f" NATURAL JOIN offer" 

    if len(nodeInfoIds) > 1:
        ss+=f" WHERE nodeInfoId IN {tuple(nodeInfoIds)}"
    else:
        ss+=f" WHERE nodeInfoId IN ( {nodeInfoIds[0]} )"
    ss+=f" GROUP BY nodeInfoId"

    debug.dlog(ss)
    recordset = myModel.execute(ss) 
    records=recordset.fetchall()
    print(f"node address\tnode name\n model\tcost of procurement in GLM")

    for row in records:
        print(f"{row[0]}\t{row[1]}")
        print(f" {row[2]}\t{row[3]}")
        print("")

    if len(nodeInfoIds) > 1:
        ss=f"SELECT asc FROM topology WHERE nodeInfoId IN {tuple(nodeInfoIds)}"
    else:
        ss=f"SELECT asc FROM topology WHERE nodeInfoId IN ({nodeInfoIds[0]})"

    recordset = myModel.execute(ss)
    records=recordset.fetchall()
    input("Press enter to step thru topologies:")
    for row in records:
        print(row[0])
        input()

def on_run_conclusion(nodeInfoIds, myModel):
    """ work with most recent results """
    console_interface(nodeInfoIds, myModel)

