#!/usr/bin/env python3
import asyncio
from typing import AsyncIterable

from yapapi import Golem, Task, WorkContext
from yapapi.log import enable_default_logger
from yapapi.payload import vm
from itertools import count
from filterms import FilterProviderMS
import yapapi
import yapapi.log
import json
from decimal import Decimal
from datetime import datetime, timedelta
import pprint
import pathlib
import debug
import traceback

from marshal_result import marshal_result
import utils
import sys
import io
import argparse
import sqlite3
import tempfile

"""create_db
inputs                          process                     output
 dbpath                         setup adapters              conn
 isolation                      register adapters
                                connect
"""
def create_db(dbpath, isolation_level=None):
    """setup adapters"""
    def adapt_decimal(d):
        return str(d)

    def convert_decimal(s):
        return Decimal(s.decode('utf-8'))

    """register"""
    sqlite3.register_adapter(Decimal, adapt_decimal)
    sqlite3.register_converter("DECIMAL", convert_decimal)

    """connect"""
    con = sqlite3.connect(dbpath, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES, isolation_level=isolation_level)

    """output"""
    return con



class MySummaryLogger(yapapi.log.SummaryLogger):
    """intercept events, record agreement info, update linked blacklist"""
    """id_to_info: { <agr_id> : { name:, address:, timestamp: }, ... }"""
    def __init__(self, blacklist_ref):
        self._blacklist = blacklist_ref
        super().__init__()
        self.id_to_info=dict()

        self._last_node_name = ''
        self._last_node_address= ''
        self._last_timestamp=Decimal('0.0')

        debug.dlog("creating summarylogger.log file", 10)
        self._internal_log = open("summarylogger.log", "w", buffering=1)

    def __del__(self):
        self._internal_log.close()

    def log(self, event: yapapi.events.Event) -> None:
        if isinstance(event, yapapi.events.AgreementCreated):
            """
            event: .job_id | .agr_id | .provider_id | .provider_info | .name | .subnet_tag
            """
            self.id_to_info[event.agr_id]={ 'name': event.provider_info.name
                    , 'address': event.provider_id
                    , 'timestamp': str(Decimal(str(datetime.now().timestamp())))
            }
            debug.dlog(f"agreement created with agr_id: {event.agr_id} with provider named: {event.provider_info.name}")
        elif isinstance(event, yapapi.events.TaskAccepted):
            agr_id = event.result['agr_id']
            debug.dlog(f"{event}\n--------blacklisting {self.id_to_info[agr_id]['name']} because of task accepted")
            self._blacklist.add(self.id_to_info[agr_id]['address'])
        elif isinstance(event, yapapi.events.WorkerFinished):
            if event.exc_info != None and len(event.exc_info) > 0:
                debug.dlog(f"{event}\nWorker associated with agreement id {event.agr_id} finished but threw the exception {event.exc_info[1]}"
                       "\nWorker name is {self.id_to_info['event.agr_id']}" )
        elif isinstance(event, yapapi.events.ActivityCreateFailed):
            if len(event.exc_info) > 0:
                providerName = self.id_to_info[event.agr_id]['name']
                debug.dlog(f"{event}\nAn exception occurred preventing an activity/script from starting (provider name {providerName}).\n"
                        f"{event.exc_info[1]}"
                        )
        elif isinstance(event, yapapi.events.ExecutionInterrupted):
            print("The worker logic was interrupted by an exception: {event.exc_info[1]}")

        self._internal_log.write(f"\n-----\n{event}\n-------\n")

        super().log(event)









async def on_accepted_result(result):
    """handler for each task a worker executes"""
    # called by provision_to_golem
    debug.dlog(f"golem.execute_tasks has returned a Task object with result: {result}")





class Provisioner():
    def __init__(self, budgetPerTask, golem_timeout, subnet_tag, payment_driver, payment_network, event_consumer, strategy, package, result_callback):
        self._budgetPerTask         =budgetPerTask
        self._golem_timeout         =golem_timeout # the timeout for the golem instance | >= script timeout
        self._subnet_tag            =subnet_tag
        self._payment_driver        =payment_driver
        self._payment_network       =payment_network
        self._event_consumer        =event_consumer
        self._strategy              =strategy    # incorporates logic to prevent work being resent to the same node in the same run
        self.__tempdir              =tempfile.TemporaryDirectory() # cleans up on garbage collection
        self._workdir               =self.__tempdir.name
        self._package               =package
        self._result_callback       =result_callback
        self.__env_printed          =False
        # comment: golem_timeout set too low (e.g. < 10 minutes) might result in no offers being collected




    async def _worker(self, context: WorkContext, tasks: AsyncIterable[Task]):
        """run topology gathering script, d/l, and store provider ids and filepath to d/l in result"""
        """
        context.id -> activity id; same as ActivityCreated :event.act_id (stored 
        context.provider_name -> name of provider
        context.provider_id -> node address
        context._agreement_details.raw_details.offer -> offer
        """

        async for task in tasks:
            agr_id=context._agreement_details.agreement_id
            debug.dlog(f"starting work: context id: {context.id}, {context.provider_name}, {context.provider_id}\nagreement id is: {agr_id}")

            script = context.new_script(timeout=timedelta(minutes=2))
            script.run("/root/provider.sh", context.provider_name, context.provider_id, str(datetime.now().timestamp()))
            target=f"{task.data['results-dir']}/{context.provider_id}.json"
            script.download_file(f"/golem/output/topology.json", target)
            try:
                yield script
            except:
                raise
            else:
                # place result along with meta into a dict
                result_dict= { 'provider_name': context.provider_name
                        , 'graphical_output_file': target
                        , 'provider_id': context.provider_id
                        , 'agr_id': agr_id # may be used to lookup additional info in MySummaryLogger
                }
                task.accept_result(result_dict)






    async def __call__(self, time_last_run):
        """ enter market """
        async with Golem(
                budget=self._budgetPerTask
                , subnet_tag=self._subnet_tag
                , payment_driver=self._payment_driver
                , payment_network=self._payment_network
                , event_consumer=self._event_consumer.log
                , strategy=self._strategy
                , stream_output=False
                ) as golem:

            """ output parameters """
            if self.__env_printed==False:
                utils.print_env_info(golem)
                self.__env_printed=True

            """ send task """
            async for completed in golem.execute_tasks(
                    self._worker
                    , [Task(data={"results-dir": self._workdir})]
                    , payload=self._package
                    , max_workers=1
                    , timeout=self._golem_timeout
                    ):

                """ handle result """
                await self._result_callback(completed.result)

                """ reset start time """
                time_last_run=datetime.now()

        """ output """
        return time_last_run









async def spyu(CPUmax=Decimal("0.5"), ENVmax=Decimal("0.18"), maxGlm=Decimal("1.0"), STARTmax=Decimal("0.0")):
    glmSpent=Decimal(0.0)

    """ create blacklist """
    blacklist=set()

    """ parse CLI """
    parser = utils.build_parser("spyu : a provider cpu topology inspector")
    # parser.add_argument("--results-dir", help="where to store downloaded task results", default="/tmp/spyu_workdir")
    # parser.add_argument("--max-budget", help="maximum total budget", default=Decimal(1))
    args=parser.parse_args()

    """ enable logging """
    enable_default_logger(log_file=args.log_file)

    """ setup package """
    package = await vm.repo(
        image_hash="719736740563a4bb8afd1c8d663655c5984490391909ecaffe1ad603"
    )

    """ setup strategy """
    strat=yapapi.strategy.DummyMS(
        max_fixed_price=STARTmax
        , max_price_for={
            yapapi.props.com.Counter.CPU: CPUmax
            , yapapi.props.com.Counter.TIME: ENVmax
            }
    )

    """ filter strategy """
    filtered_strategy = FilterProviderMS(blacklist, strat)


    """ setup event consumer """
    mySummaryLogger=MySummaryLogger(blacklist)


    """ timestamp """
    time_last_run=datetime.now()
    new_work_timeout=timedelta(minutes=1)

    """ setup provisioner """
    provisioner = Provisioner(budgetPerTask=Decimal("0.001"), golem_timeout=timedelta(minutes=10), subnet_tag=args.subnet_tag, payment_driver=args.payment_driver, payment_network=args.payment_network, event_consumer=mySummaryLogger, strategy=filtered_strategy, package=package, result_callback=on_accepted_result)

    while datetime.now() - time_last_run < new_work_timeout:
        """ call provisioner """
        time_last_run = await provisioner(time_last_run)

    print(f"Stopping because no results seen for duration of {datetime.now() - time_last_run}")





if __name__ == "__main__":
    debug.dlog("starting")
    utils.run_golem_example(spyu())


# save
# future_result = script.run("/bin/sh", "-c", "/bin/echo [$(lscpu -J | jq -c),$(lscpu -JC | jq -c)] | sed s/\"field\"/\"k\"/g | sed s/\"data\"/\"v\"/g")
# cat /proc/cpuinfo |grep "model name" |head -n1 | sed  -rn 's/^[^:]+:[[:space:]]([^[$]+)$/\1/p'
