import yapapi
from decimal import Decimal
import debug
from datetime import datetime
import functools

class MySummaryLogger(yapapi.log.SummaryLogger):
    """intercept events, record agreement info, update linked blacklist"""
    """id_to_info: { <agr_id> : { name:, address:, timestamp: }, ... }"""
    def __init__(self, blacklist_ref, myModel):
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

    def _blacklist_provider(self, address, name):
        self._blacklist.add(address)
        self._blacklist.associate_name(address, name)


    def _addInvoice(self, agr_id: str, total: Decimal):
        if agr_id in self._invoicesReceived:
            raise Exception("saw second invoice for agreement")
        self._invoicesReceived[agr_id]=total

    def sum_invoices(self):
        """aggregate invoicesReceived"""
        sum_=Decimal('0.0')
        if len(self._invoicesReceived) > 0:
            sum_ = functools.reduce(lambda a,b: a+b, self._invoicesReceived.values())
        return sum_

    def __del__(self):
        self._internal_log.close()

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
                providerName = self.id_to_info[event.agr_id]['name']
                debug.dlog(f"{event}\nAn exception occurred preventing an activity/script from starting (provider name {providerName}).\n"
                        f"{event.exc_info[1]}"
                        )
        # [ InvoiceReceived ]
        elif isinstance(event, yapapi.events.InvoiceReceived):
            assert event.agr_id not in self._invoicesReceived, "duplicate invoice!"
            amountInvoiceAsDecimal = Decimal(event.amount)
            self._addInvoice(event.agr_id, amountInvoiceAsDecimal)
            # self._invoicesReceived[event.agr_id]=Decimal(event.amount)
            debug.dlog(f"received invoice for {self._invoicesReceived[event.agr_id]}")
            records = self._myModel.execute(f"SELECT topologyId FROM agreement WHERE id = '{event.agr_id}'").fetchall()
            if len(records) > 0:
                topologyId = records[0][0]
                self._myModel.execute(f"INSERT INTO 'cost'(topologyId, total) VALUES (?, ?)", [ topologyId, amountInvoiceAsDecimal ])
                # self._myModel.execute(f"INSERT 
        # [ ExecutionInterrupted ]
        elif isinstance(event, yapapi.events.ExecutionInterrupted):
            print(f"\033[1mThe worker logic was interrupted by an exception of name {event.exc_info[0].__name__} with these details: {event.exc_info[1]}\033[0m")
        # [ ComputationFinished ]
        elif isinstance(event, yapapi.events.ComputationFinished):
            if event.exc_info != None and len(event.exc_info) > 0 and isinstance(event.exc_info, TimeoutError):
                debug.dlog("?????????????????????????????????? computation timed out ?????????????????????????")

        self._internal_log.write(f"\n-----\n{event}\n-------\n")

        super().log(event)

