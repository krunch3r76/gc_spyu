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


def print_env_info_once(golem):
    printed=False
    def closure():
        nonlocal printed
        if printed==False:
            printed=True
        utils.print_env_info(golem)
    return closure




class MySummaryLogger(yapapi.log.SummaryLogger):
    """intercepts events"""
    """id_to_info: <agr_id> : { name:, address:, timestamp: }"""
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
            job_id
            agr_id
            provider_id
            provider_info
                name
                subnet_tag
            """
            """
            _last_node_name=event.provider_info.name
            _last_node_address=event.provider_id
            _last_timestamp=Decimal(str(datetime.now().timestamp()))
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
        self._internal_log.write(f"\n-----\n{event}\n-------\n")

        super().log(event)



async def worker(context: WorkContext, tasks: AsyncIterable[Task]):
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








async def on_executed_task(completed):
    """handler for each task a worker executes"""
    """
    
    """
    debug.dlog(f"golem.execute_tasks has returned a Task object with result: {completed.result}")

async def main():
    glmSpent=Decimal(0.0)
    parser = utils.build_parser("spyu : a provider cpu topology inspector")
    parser.add_argument("--results-dir", help="where to store downloaded task results", default="/tmp/task_results")
    # parser.add_argument("--max-budget", help="maximum total budget", default=Decimal(1))
    args=parser.parse_args()

    enable_default_logger(log_file=args.log_file)
    blacklist=set()
    counter=count(1)
    package = await vm.repo(
        image_hash="719736740563a4bb8afd1c8d663655c5984490391909ecaffe1ad603"
    )

    tasks = [Task(data={"results-dir": args.results_dir})]
    mySummaryLogger=MySummaryLogger(blacklist)
    CPUmax=Decimal("0.5")
    ENVmax=Decimal("0.18")
    strat=yapapi.strategy.DummyMS(
        max_fixed_price=Decimal("0.0")
        , max_price_for={
            yapapi.props.com.Counter.CPU: CPUmax
            , yapapi.props.com.Counter.TIME: ENVmax
            }
    )
    timestart=datetime.now()
    print("starting")
    while datetime.now() - timestart < timedelta(minutes=1):
        print("-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+")
        timeout=timedelta(minutes=10)
        async with Golem(
                budget=0.1
                , subnet_tag=args.subnet_tag
                , payment_driver=args.payment_driver
                , payment_network=args.payment_network
                , event_consumer=mySummaryLogger.log
                , strategy=FilterProviderMS(blacklist, strat)
                , stream_output=False
                ) as golem:

            print_env_info_once(golem)
            async for completed in golem.execute_tasks(
                    worker
                    , tasks
                    , payload=package
                    , max_workers=1
                    , timeout=timeout
                    ):
                await on_executed_task(completed)
                timestart=datetime.now()
    print(f"Stopping because no results after {datetime.now() - timestamp}")





if __name__ == "__main__":
    debug.dlog("starting")
    utils.run_golem_example(main())
#    loop = asyncio.get_event_loop()
#    task = loop.create_task(main())
#    loop.run_until_complete(task)



# save
# future_result = script.run("/bin/sh", "-c", "/bin/echo [$(lscpu -J | jq -c),$(lscpu -JC | jq -c)] | sed s/\"field\"/\"k\"/g | sed s/\"data\"/\"v\"/g")
# cat /proc/cpuinfo |grep "model name" |head -n1 | sed  -rn 's/^[^:]+:[[:space:]]([^[$]+)$/\1/p'
