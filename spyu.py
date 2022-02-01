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
            debug.dlog(event)
            agr_id = event.result['agr_id']
            debug.dlog(f"--------blacklisting {self.id_to_info[agr_id]['name']} because of task accepted")
            self._blacklist.add(self.id_to_info[agr_id]['address'])
        elif isinstance(event, yapapi.events.WorkerFinished):
            debug.dlog(event)
            if event.exc_info != None and len(event.exc_info) > 0:
                debug.dlog(f"Worker associated with agreement id {event.agr_id} finished but threw the exception {event.exc_info[1]}"
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
        script.run("/root/provider.sh", context.provider_name, context.provider_id)
        target=f"{task.data['results-dir']}/{context.provider_id}"
        script.download_file(f"/golem/output/topology.svg", str(target+".svg"))
        script.download_file(f"/golem/output/topology.asc", str(target+".asc"))
        try:
            yield script
        except:
            raise
        else:
            # place result along with meta into a dict
            result_dict= { 'agr_id': agr_id
                    , 'graphical_output_file': target
                    , 'provider_id': context.provider_id
            }
            task.accept_result(result_dict)








async def on_executed_task(completed):
    info = mySummaryLogger.id_to_info[completed.result.agr_id]

    objects_j=json.loads(completed.result.stdout)
    nt_raw_parse = marshal_result(objects_j)
    lscpu = {
            'essentials': nt_raw_parse.essentials
            ,'caches': nt_raw_parse.caches
            ,'vulnerabilities': nt_raw_parse.vulnerabilities
            }
    result_summary = dict()
    result_summary['provider_id']=info['address']
    result_summary['provider_name']=info['name']
    result_summary['timestamp']=info['timestamp']
    result_summary['info']=lscpu


    # print(f"------\n{result_j}\n------")

    filename=f"{result_summary['provider_id'][:6]}_{result_summary['provider_name']}.json"
    print("------------------------------------------------------")
    path_to_file=(pathlib.Path("./tmp")/filename).resolve()
    print("++++++++++++++++++++++++++++++++++++++")
    print(f"!!!!!!!!!!!! ${path_to_file} !!!!!!")
    with open(str(path_to_file), "w") as f:
        # with open(f'output{next(counter)}.txt', "w") as f:
        # f.write(completed.result.stdout)
        f.write(json.dumps(result_summary, indent=4))

    print(f"RESULT SUMMARY**********\n{json.dumps(result_summary, indent=1)}")
            # print(completed.result.stdout)



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
        image_hash="2e8bc4d29bc4019b06ebba9e23b81a2e71500a8d436662bcb2b1fafb"
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
                # print(completed.result['stdout'])
                # await on_executed_task(completed)
                timestart=datetime.now()





if __name__ == "__main__":
    debug.dlog("starting")
    utils.run_golem_example(main())
#    loop = asyncio.get_event_loop()
#    task = loop.create_task(main())
#    loop.run_until_complete(task)



# save
# future_result = script.run("/bin/sh", "-c", "/bin/echo [$(lscpu -J | jq -c),$(lscpu -JC | jq -c)] | sed s/\"field\"/\"k\"/g | sed s/\"data\"/\"v\"/g")
# cat /proc/cpuinfo |grep "model name" |head -n1 | sed  -rn 's/^[^:]+:[[:space:]]([^[$]+)$/\1/p'
