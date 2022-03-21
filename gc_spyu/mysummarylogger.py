import yapapi
from decimal import Decimal
import debug
from datetime import datetime
import functools
import asyncio
import traceback
from pathlib import Path
import tempfile


class MySummaryLogger(yapapi.log.SummaryLogger):
    """intercept events, record agreement info, update linked blacklist"""

    """id_to_info: { <agr_id> : { name:, address:, timestamp: }, ... }"""
    ############# __init__ ########################
    def __init__(self, blacklist_ref, myModel, whitelist):
        self.whitelist = whitelist
        self._blacklist = blacklist_ref
        super().__init__()
        self.id_to_info = dict()
        self._invoicesReceived = dict()  # agr_id to invoice amount, TODO
        # multiple invoices on single agr_id
        self._last_node_name = ""
        self._last_node_address = ""
        self._last_timestamp = Decimal("0.0")
        self._myModel = myModel
        self._jobid_to_agr = dict()
        debug.dlog("creating summarylogger.log file", 10)

        systmpdir_as_path = Path(tempfile.gettempdir())

        self._internal_log = open(
            str(systmpdir_as_path / "summarylogger.log"), "w", buffering=1
        )
        self.interrupted = False
        self.skipped = []
        self._agreementsConfirmed = []  # those for which a task was accepted
        self.providersFailed = []  # {name:, address:}, ...
        self.lastwaitlist = set()

    # implies an invoice

    # ----------  _blacklist_provider  --------------
    def _blacklist_provider(self, address, name, mark_skipped=False):
        def _find_partial_match(addr):
            """return the whitelist partial match for a full addr"""
            match = None
            for element in self.whitelist:
                if addr.startswith(element):
                    match = element
                    break
            return match

        self._blacklist.add(address)
        self._blacklist.associate_name(address, name)
        if mark_skipped:
            self.skipped.append({"name": name, "address": address})
            # self.skipped.append(f"{name}@{address}")
            # print(f"skipped {name}@{address}, reason: uncooperative")

        self.whitelist.discard(name)
        partial_match = _find_partial_match(address)
        self.whitelist.discard(partial_match)
        # print(f"--------discarded {partial_match}")

    # ----------  _addInvoice    --------------------
    def _addInvoice(self, agr_id: str, total: Decimal):
        if agr_id in self._invoicesReceived:
            raise Exception("saw second invoice for agreement")
            # TODO
        self._invoicesReceived[agr_id] = total

    # ------------ sum_invoices -------------
    def sum_invoices(self):
        """aggregate invoicesReceived"""
        sum_ = Decimal("0.0")
        if len(self._invoicesReceived) > 0:
            sum_ = Decimal(
                str(
                    functools.reduce(
                        lambda a, b: a + b, self._invoicesReceived.values()
                    )
                )
            )
        return sum_

    def sum_invoices_on(self, addr):
        """lookup invoice associated with addr return the sum"""
        # agr_id of addr in id_to_info.items()
        error = False
        agr_id = None
        invoice_total = None
        for key, val in self.id_to_info.items():
            if val["address"] == addr:
                agr_id = key
                break  # TODO refactor to single line
        if agr_id == None:
            error = True
            debug.dlog("--------- NO AGREEMENT FOR ADDR FOUND ------------")

        if not error:
            invoice_total = self._invoicesReceived.get(agr_id, Decimal("0.0"))
            if invoice_total == Decimal("0.0"):
                error = True
        if error:
            raise Exception("could not sum invoices on addr")

        return invoice_total

    # ------------ sum_invoices_on ----------
    # TODO
    # def sum_invoices_multiset_on(self, addr):
    #     """ return the sum of the invoices associated with a particular
    # 		addr """
    #     there is more than one invoice usually if there are multiple
    # 		script calls in a single worker
    #     list agreements (keys) with value 'address'=addr
    #     debug.dlog(f"summing invoices on {addr}")
    #     agreements=[]
    #     for key, val in self.id_to_info.items():
    #         if val['address'] == addr:
    #             agreements.append(key)
    #     sum_ = Decimal('0.0')
    #     for agreement in agreements:
    #         sum_ += Decimal(str(self._invoicesReceived.get(agreement,
    # 		Decimal("0.0"))))
    #     return sum_

    # ------------ __del__    --------------
    def __del__(self):
        self._internal_log.close()

    # -----------    log    --------------
    # super wrapper
    # ------------------------------------
    def log(self, event: yapapi.events.Event) -> None:
        # [ AgreementCreated ]
        if isinstance(event, yapapi.events.AgreementCreated):
            """
            AgreementCreated: .job_id | .agr_id | .provider_id
                | .provider_info || .name ||.subnet_tag
            """
            self.id_to_info[event.agr_id] = {
                "name": event.provider_info.name,
                "address": event.provider_id,
                "timestamp": str(Decimal(str(datetime.now().timestamp()))),
            }
            self._jobid_to_agr[event.job_id] = event.agr_id
            debug.dlog(
                f"agreement created with agr_id: {event.agr_id} with"
                f" provider named: {event.provider_info.name}"
            )
            # self._blacklist_provider(event.provider_id, event.provider_info.name)
        elif isinstance(self, yapapi.events.AgreementConfirmed):
            pass
        # [ TaskAccepted ]
        elif isinstance(event, yapapi.events.TaskAccepted):
            agr_id = event.result["agr_id"]
            address = self.id_to_info[agr_id]["address"]
            name = self.id_to_info[agr_id]["name"]
            self._agreementsConfirmed.append(agr_id)

            # debug.dlog(f"{event}\n--------blacklisting {name}@{address} "
            # " because of task accepted")
            # self._blacklist_provider(address, name)
        # [ WorkerFinished ]
        elif isinstance(event, yapapi.events.WorkerFinished):
            if event.exc_info != None and len(event.exc_info) > 0:
                debug.dlog(
                    f"{event}\nWorker associated with agreement id"
                    f" {event.agr_id} finished but threw the exception"
                    f" {event.exc_info[1]}"
                    f"\nWorker name is {self.id_to_info['event.agr_id']}"
                )
        # [ ComputationFinished ]
        elif isinstance(event, yapapi.events.ComputationFinished):
            debug.dlog(event)
            if event.exc_info != None:
                try:
                    agr_id = self._jobid_to_agr[event.job_id]
                    info = self.id_to_info[agr_id]
                except:
                    agr_id = "unknown agreement"
                    info = "no info"
                else:
                    self.providersFailed.extend(
                        [{"address": info["address"], "name": info["name"]}]
                    )
                    self._blacklist_provider(info["address"], info["name"])
                if (
                    event.exc_info != None
                    and len(event.exc_info) > 0
                    and isinstance(event.exc_info[1], TimeoutError)
                ):

                    debug.dlog(
                        f"? computation timed out ?\n{event}\n" f" {agr_id}\n{info}"
                    )
                elif (
                    event.exc_info != None
                    and len(event.exc_info) > 0
                    and isinstance(event.exc_info[1], asyncio.exceptions.CancelledError)
                ):
                    debug.dlog(
                        f"computation cancelled for agreement" f" {agr_id}\n{info}"
                    )
        # [ InvoiceReceived ]
        elif isinstance(event, yapapi.events.InvoiceReceived):
            assert event.agr_id not in self._invoicesReceived, "duplicate" " invoice!"
            amountInvoiceAsDecimal = Decimal(event.amount)
            self._addInvoice(event.agr_id, amountInvoiceAsDecimal)
            # self._invoicesReceived[event.agr_id]=Decimal(event.amount)
            debug.dlog(
                f"$$$$$$$$$$$$$$$$ received invoice for"
                f" {self._invoicesReceived[event.agr_id]} $$$$$$$$$$$$"
            )
            records = self._myModel.execute(
                f"SELECT nodeInfoId FROM" " extra.agreement WHERE id = '{event.agr_id}'"
            ).fetchall()
            if len(records) > 0:
                nodeInfoId = records[0][0]
                self._myModel.execute(
                    f"INSERT INTO extra.cost (nodeInfoId," " total) VALUES (?, ?)",
                    [nodeInfoId, amountInvoiceAsDecimal],
                )
                # self._myModel.execute(f"INSERT
        # [ ActivityCreateFailed ]
        elif isinstance(event, yapapi.events.ActivityCreateFailed):
            if len(event.exc_info) > 0:
                agr_id = event.agr_id
                name = self.id_to_info[agr_id]["name"]
                address = self.id_to_info[agr_id]["address"]
                debug.dlog(
                    f"{event}\nAn exception occurred preventing an"
                    f" activity/script from starting (provider name "
                    f" {name}@{address}).\n"
                    f"{event.exc_info[1]}"
                )
                self.interrupted = True
        # [ ExecutionInterrupted ]
        elif isinstance(event, yapapi.events.ExecutionInterrupted):
            if event.exc_info[1] and len(str(event.exc_info[1])) > 0:
                print(
                    f"\033[1mThe worker logic was interrupted by"
                    f" an exception of name {event.exc_info[0].__name__} with"
                    f" these details: {event.exc_info[1]}\033[0m"
                )
                tb = event.exc_info[2]
                traceback.print_tb(tb)
        # [ AgreementTerminated ]
        elif isinstance(event, yapapi.events.AgreementTerminated):
            # eg
            # AgreementTerminated(job_id='1', agr_id=
            #'5d3111a228c970317bb99312657a0cf88653e6bdfc27697ec0c6654bf
            # 0dcdb0a', reason={'message': 'Work cancelled',
            # 'golem.requestor.code': 'Cancelled'})
            agr_id = event.agr_id
            name = self.id_to_info[agr_id]["name"]
            address = self.id_to_info[agr_id]["address"]
            if self.interrupted:
                self._blacklist_provider(address, name, True)
                self.interrupted = False
        elif isinstance(event, yapapi.events.NoProposalsConfirmed):
            pass
            # boldlist = ', '.join(map(lambda s: f'\033[1m{s}\033[0m'
            #     , self.whitelist))
            # print(f"still waiting on {boldlist}")
        elif isinstance(event, yapapi.events.ProposalFailed):
            tb = event.exc_info[2]
            traceback.print_tb(tb)
        self._internal_log.write(f"\n-----\n{event}\n-------\n")

        super().log(event)

        diff = self._blacklist.difference(self.whitelist)
        if len(diff) == 0:
            # wait for all agreements to have invoices
            # _agreementsConfirmed set should equal the set of keys on
            # _invoicesReceived
            agreements_with_invoices = set(self._invoicesReceived.keys())
            agreementsConfirmed = set(self._agreementsConfirmed)
            if agreements_with_invoices == agreementsConfirmed:

                debug.dlog(f"agreements_with_invoices: {agreements_with_invoices}")
                debug.dlog(f"agreemintsConfirmd: {agreementsConfirmed}")
                debug.dlog("raising keyboardinterrupt")
                raise KeyboardInterrupt
        else:
            boldlist = ", ".join(map(lambda s: f"\033[1m{s}\033[0m", self.whitelist))
            if self.whitelist != self.lastwaitlist:
                print(f"still waiting on {boldlist}")
                self.lastwaitlist = self.whitelist.copy()
            # print(f"looking for {diff}")
            # debug.dlog(f"looking for {diff}")
