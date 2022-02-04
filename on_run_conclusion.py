# on_run_conclusion.py
# authored by krunch3r
import debug

def console_interface(topologyIds, myModel):
    # provider name, nodeaddress, model, cost
    ss=f"SELECT addr, json_extract(data, '$.\"golem.node.id.name\"') AS nameProvider, modelname, total" \
        f" FROM (select addr FROM provider NATURAL JOIN topology) AS addr" \
        f" JOIN topology" \
        f" NATURAL JOIN cost" \
        f" NATURAL JOIN offer" \
        f" WHERE topologyId IN {tuple(topologyIds)}" \
        f" GROUP BY topologyId"
    debug.dlog(ss)
    recordset = myModel.execute(ss) 
    records=recordset.fetchall()
    print(f"node address\tnode name\n model\tcost of procurement in GLM")

    for row in records:
        print(f"{row[0]}\t{row[1]}")
        print(f" {row[2]}\t{row[3]}")
        print("")

    ss=f"SELECT asc FROM topology WHERE topologyId IN {tuple(topologyIds)}"
    recordset = myModel.execute(ss)
    records=recordset.fetchall()
    input("Press enter to step thru topologies:")
    for row in records:
        print(row[0])
        input()

def on_run_conclusion(topologyIds, myModel):
    """ work with most recent results """
    console_interface(topologyIds, myModel)

