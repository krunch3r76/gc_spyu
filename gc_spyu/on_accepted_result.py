import json
import debug
from collections import namedtuple
from decimal import Decimal



NodeInfoNT = namedtuple('NodeInfoNT', ['nodeInfoId', 'providerId'
    , 'modelname', 'unixtime', 'nodename']) # unixtime is Decimal


# _________ _add_nodeInfo _______________
def _add_nodeInfo(myModel, providerId, intel_d, attached_prefix):
    if attached_prefix != '':
        assert '.' in attached_prefix, "malformed attached db prefix"

    inserted_nodeInfoId = myModel.execute_and_id(
            f"INSERT INTO {attached_prefix}nodeInfo" \
            + "(providerId, modelname, unixtime, nodename)" \
            + " VALUES(?, ?, ?, ?)", [ providerId, intel_d['model'], \
            Decimal(intel_d['unixtime']), intel_d['name'] 
            ])[0]
    return inserted_nodeInfoId

# ____________ _add_provider ____________
def _add_provider(myModel, addr, attached_prefix=''):
    if attached_prefix != '':
        assert '.' in attached_prefix, "malformed attached db prefix"
    providerId = myModel.execute_and_id("INSERT INTO " \
            + f"{attached_prefix}provider(addr)" \
            + "VALUES (?)", [ addr ])[0]
    return providerId

# _____________ _lookup_provider_id ___________
def _lookup_provider_id(myModel, addr, attached_prefix=''):
    if attached_prefix != '':
        assert '.' in attached_prefix, "malformed attached db prefix"
    recs = myModel.execute("SELECT providerId, addr FROM " \
            + f"{attached_prefix}provider" \
            + " WHERE addr" \
            + f"='{addr}'").fetchall()
    rv_providerId = recs[0][0] if len(recs) == 1 else None
    return rv_providerId






######## BEGIN update_main_db ################
def update_main_db(myModel, intel_d):

    # _-_-_-_- __update_nodeInfotime _-_-_-_-
    def __update_nodeInfo_time(nodeInfoId, unixtime_str):
        myModel.execute("UPDATE nodeInfo SET unixtime = (?) WHERE" \
                + f" nodeInfoId = {nodeInfoId}", [Decimal(unixtime_str)])

    # _-_-_-_- __lookup_last_nodeinfo_record _-_-_-_-
    def __lookup_last_nodeinfo_record(providerId) ->NodeInfoNT:
        rv_nodeInfoRecord = None
        nodeInfoRows = myModel.execute("SELECT nodeInfoId, providerId" \
                + ", modelname" \
                + ",unixtime, nodename, MAX(unixtime) FROM nodeInfo WHERE" \
                + f" providerId = {providerId} GROUP BY " \
                + "providerId").fetchall()
        
        if len(nodeInfoRows) != 0:
            rv_nodeInfoRecord = NodeInfoNT(*nodeInfoRows[0][:-1])

        debug.dlog(f"timestamp for {rv_nodeInfoRecord.nodename}:"
                f" {rv_nodeInfoRecord.unixtime}")
        debug.dlog(f"returning: {rv_nodeInfoRecord}")
        return rv_nodeInfoRecord

# --------------------start update_maind_db--------------- #
    prefixAttached=''

    providerId = _lookup_provider_id(myModel, intel_d['addr'], prefixAttached)
    if providerId == None:
        providerId = _add_provider(myModel, intel_d['addr'], prefixAttached)
        _add_nodeInfo(myModel, providerId, intel_d, prefixAttached)
    else:
        nodeInfoRec = __lookup_last_nodeinfo_record(providerId)
        if nodeInfoRec != None:
            if not ( intel_d['name'] == nodeInfoRec.nodename and \
                    intel_d['model'] == nodeInfoRec.modelname ):
                _add_nodeInfo(myModel, providerId, intel_d, prefixAttached)
        else:
            __update_nodeInfo_time(nodeInfoRec.nodeInfoId
                        , intel_d['unixtime'])

########### END update_main_db ###################
        

########## BEGIN update_extra_db ###############
def update_extra_db(myModel, intel_d, offer: str, agr_id):
    # _-_-_-_- __add_offer _-_-_-_-
    def __add_offer(nodeInfoId, offer):    
        myModel.execute(f"INSERT INTO {prefixAttached}offer(nodeInfoId," \
                + "data) VALUES (?, ?)",
                [ nodeInfoId, offer ] )

    # _-_-_-_- __add_agreement _-_-_-_-
    def __add_agreement(nodeInfoId, agr_id):
        myModel.execute(f"INSERT INTO {prefixAttached}agreement(nodeInfoId," \
                + "id) VALUES (?, ?)",
                [ nodeInfoId, agr_id ] )

    # --------------------- start ----------------------- #

    prefixAttached='extra.'
    providerId = _lookup_provider_id(myModel, intel_d['addr'], prefixAttached)
    if providerId == None:
        providerId = _add_provider(myModel, intel_d['addr'], prefixAttached)
    nodeInfoId = _add_nodeInfo(myModel, providerId, intel_d, prefixAttached)
    __add_offer(nodeInfoId, offer)
    __add_agreement(nodeInfoId, agr_id)
    return nodeInfoId



######## on_accepted_result ########
def on_accepted_result(myModel, mySummaryLogger):
    """closure handler for each task a worker executes"""
    # called by provision_to_golem
    async def on_accepted_result_closure(result):
        # result := { provider_name: , json_file: , provider_id: , agr_id: }
        """ gatheredIntel := { unixtime: , name: , addr: , model: }"""

        extraNodeInfoId = None

        with open(result['json_file'], "r") as json_fp:
            gatheredIntel = json.load(json_fp)

        update_main_db(myModel, gatheredIntel)
        myModel.commit()

        extraNodeInfoId = update_extra_db(myModel, gatheredIntel,
                json.dumps(result['offer']) , result['agr_id'])
        myModel.commit()
        return [ extraNodeInfoId ]

    return on_accepted_result_closure







