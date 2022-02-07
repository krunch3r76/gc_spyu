import yapapi
from decimal import Decimal
import debug
from datetime import datetime
import functools
import asyncio

class MySummaryLogger(yapapi.log.SummaryLogger):
    """intercept events, record agreement info, update linked blacklist"""
    """id_to_info: { <agr_id> : { name:, address:, timestamp: }, ... }"""
    ############# __init__ ########################
    def __init__(self, blacklist_ref, myModel, whitelist):
        self.whitelist=whitelist
        self._blacklist = blacklist_ref
        super().__init__()
        self.id_to_info=dict()
        self._invoicesReceived = dict() # agr_id to invoice amount, TODO enforce no duplicate keys (overwriting last)
        self._last_node_name = ''
        self._last_node_address= ''
        self._last_timestamp=Decimal('0.0')
        self._myModel=myModel
        debug.dlog("creating summarylogger.log file", 10)
        self._internal_log = open("summarylogger.log", "w", buffering=1)
        self.interrupted = False
        self.skipped = []


    #----------  _blacklist_provider  --------------
    def _blacklist_provider(self, address, name, mark_skipped=False):
        self._blacklist.add(address)
        self._blacklist.associate_name(address, name)
        if mark_skipped:
            self.skipped.append(f"{name}@{address}")
            print(f"skipped {name}@{address}: uncooperative")


    #----------  _addInvoice    --------------------
    def _addInvoice(self, agr_id: str, total: Decimal):
        if agr_id in self._invoicesReceived:
            raise Exception("saw second invoice for agreement")
        self._invoicesReceived[agr_id]=total

    #------------ sum_invoices -------------
    def sum_invoices(self):
        """aggregate invoicesReceived"""
        sum_=Decimal('0.0')
        if len(self._invoicesReceived) > 0:
            sum_ = functools.reduce(lambda a,b: a+b, self._invoicesReceived.values())
        return sum_

    #------------ __del__    --------------
    def __del__(self):
        self._internal_log.close()

    #-----------    log    --------------
    #super wrapper
    #------------------------------------
    def log(self, event: yapapi.events.Event) -> None:
        # [ AgreementCreated ]
        if isinstance(event, yapapi.events.AgreementCreated):
            """
            AgreementCreated: .job_id | .agr_id | .provider_id | .provider_info | .name | .subnet_tag
            """
            self.id_to_info[event.agr_id]={ 'name': event.provider_info.name
                    , 'address': event.provider_id
                    , 'timestamp': str(Decimal(str(datetime.now().timestamp())))
            }
            debug.dlog(f"agreement created with agr_id: {event.agr_id} with provider named: {event.provider_info.name}")
        # [ TaskAccepted ]
        elif isinstance(event, yapapi.events.TaskAccepted):
            agr_id = event.result['agr_id']
            address = self.id_to_info[agr_id]['address']
            name = self.id_to_info[agr_id]['name']

            debug.dlog(f"{event}\n--------blacklisting {name}@{address} because of task accepted")
            self._blacklist_provider(address, name)
        # [ WorkerFinished ]
        elif isinstance(event, yapapi.events.WorkerFinished):
            if event.exc_info != None and len(event.exc_info) > 0:
                debug.dlog(f"{event}\nWorker associated with agreement id {event.agr_id} finished but threw the exception {event.exc_info[1]}"
                       "\nWorker name is {self.id_to_info['event.agr_id']}" )
        # [ ActivityCreateFailed ]
        elif isinstance(event, yapapi.events.ActivityCreateFailed):
            if len(event.exc_info) > 0:
                agr_id=event.agr_id
                name = self.id_to_info[agr_id]['name']
                address = self.id_to_info[agr_id]['address']
                debug.dlog(f"{event}\nAn exception occurred preventing an activity/script from starting (provider name {name}@{address}).\n"
                        f"{event.exc_info[1]}"
                        )
                # self._blacklist_provider(address, name)
                self.interrupted=True
        # [ InvoiceReceived ]
        elif isinstance(event, yapapi.events.InvoiceReceived):
            assert event.agr_id not in self._invoicesReceived, "duplicate invoice!"
            amountInvoiceAsDecimal = Decimal(event.amount)
            self._addInvoice(event.agr_id, amountInvoiceAsDecimal)
            # self._invoicesReceived[event.agr_id]=Decimal(event.amount)
            debug.dlog(f"received invoice for {self._invoicesReceived[event.agr_id]}")
            records = self._myModel.execute(f"SELECT nodeInfoId FROM agreement WHERE id = '{event.agr_id}'").fetchall()
            if len(records) > 0:
                nodeInfoId = records[0][0]
                self._myModel.execute(f"INSERT INTO 'cost'(nodeInfoId, total) VALUES (?, ?)", [ nodeInfoId, amountInvoiceAsDecimal ])
                # self._myModel.execute(f"INSERT 
        # [ ExecutionInterrupted ]
        elif isinstance(event, yapapi.events.ExecutionInterrupted):
            if event.exc_info[1] and len(str(event.exc_info[1]))>0:
                print(f"\033[1mThe worker logic was interrupted by an exception of name {event.exc_info[0].__name__} with these details: {event.exc_info[1]}\033[0m")
        # [ ComputationFinished ]
        elif isinstance(event, yapapi.events.ComputationFinished):
            if event.exc_info != None and len(event.exc_info) > 0 and isinstance(event.exc_info, TimeoutError):
                debug.dlog("?????????????????????????????????? computation timed out ?????????????????????????")
        elif isinstance(event, yapapi.events.AgreementTerminated):
            # eg
            #AgreementTerminated(job_id='1', agr_id='5d3111a228c970317bb99312657a0cf88653e6bdfc27697ec0c6654bf0dcdb0a', reason={'message': 'Work cancelled', 'golem.requestor.code': 'Cancelled'})
            agr_id=event.agr_id
            name = self.id_to_info[agr_id]['name']
            address = self.id_to_info[agr_id]['address']
            # print(f"{name}@{address} cancelled the work unexpectedly and will be skipped.")
            if self.interrupted:
                self._blacklist_provider(address, name, True)
                self.interrupted=False
        self._internal_log.write(f"\n-----\n{event}\n-------\n")

        super().log(event)

        
        diff = self._blacklist.difference(self.whitelist)
        if len(diff) == 0:
            raise KeyboardInterrupt
        else:
            debug.dlog(f"looking for {diff}")
