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

from marshal_result import marshal_result

class MySummaryLogger(yapapi.log.SummaryLogger):
    def __init__(self, blacklist_ref):
        self._blacklist = blacklist_ref
        super().__init__()
        self.id_to_info=dict()

        self._last_node_name = ''
        self._last_node_address= ''
        self._last_timestamp=Decimal('0.0')

        self._internal_log = open("summarylogger.log", "w")

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
            # self._blacklist.add(event.provider_id)
            _last_node_name=event.provider_info.name
            _last_node_address=event.provider_id
            _last_timestamp=Decimal(str(datetime.now().timestamp()))
            self.id_to_info[event.agr_id]={ 'name': _last_node_name
                    , 'address': _last_node_address
                    , 'timestamp': str(_last_timestamp)
            }
        elif isinstance(event, yapapi.events.TaskAccepted):
            debug.dlog(event)
            agr_id = event.result.agr_id
            print(f"\033[1m--------blacklisting {self.id_to_info[agr_id]['name']} because of task accepted\033[0m")
            # print(f"\033[2m{event}\033[0m")
            self._blacklist.add(self.id_to_info[agr_id]['address'])
        # elif isinstance(event, yapapi.events.ActivityCreateFailed):
        #    print(f"\033[1m--------blacklisting {self.id_to_info[event.agr_id]['name']} because of failure\033[0m")
        #    self._blacklist.add(self.id_to_info[event.agr_id]['address'])
            # TODO maybe blacklist when activity fails cmd execution error --> followed up with Terminated agreement
        else:
            self._internal_log.write(f"{type(event)}: {event}\n")
            pass
            # print(f"\033[3mrepr of\033[0m {type(event)}: {event}")

        super().log(event)

async def worker(context: WorkContext, tasks: AsyncIterable[Task]):
    async for task in tasks:
        """
        context.id -> activity id
        context.provider_name -> name of provider
        context.provider_id -> node address
        context._agreement_details.raw_details.offer -> offer
        """
        """
        # future_result = script.run("/bin/sh", "-c", "/bin/echo [$(lscpu -J | jq -c),$(lscpu -JC | jq -c)] | sed s/\"field\"/\"k\"/g | sed s/\"data\"/\"v\"/g")
        # cat /proc/cpuinfo |grep "model name" |head -n1 | sed  -rn 's/^[^:]+:[[:space:]]([^[$]+)$/\1/p'
        # future_result2 = script.run("/bin/sh", "-c", "cat", "/proc/cpuinfo", "|grep 'model name' |head -n1 | sed  -rn 's/^[^:]+:[[:space:]]([^[$]+)$/\1/p' >/golem/output/model")

        # one way to ensure multiple providers are not assigned is to score only once
        # and keep an in-memory database of scored in addition to the static db
        """

        script = context.new_script(timeout=timedelta(minutes=1))
        # script.run("/bin/sh", "-c", "/root/provider.sh", context.provider_name, context.provider_id)
        script.run("/root/provider.sh", context.provider_name, context.provider_id)
        target=f"/tmp/{context.provider_id}.svg"
        script.download_file(f"/golem/output/topology.svg", target)
        try:
            yield script
            # result=await future_result
        except:
            print("EXCEPTION!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            raise
            # instead reject and handle elsewhere
        else:
            task.accept_result(result=context.provider_id)



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

    # result_summary['provider_id']=mySummaryLogger._last_node_address
    # result_summary['provider_name']=mySummaryLogger._last_node_name
    # result_summary['timestamp']=str(mySummaryLogger._last_timestamp)
    # result_summary['info']=raw_parse

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
    blacklist=set()
    counter=count(1)
    package = await vm.repo(
        image_hash="677aa326a246e0671240edf0fdd954749b43d1b8b1a68ccae516d1d2",
    )

    tasks = [Task(data=None)]
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
        async with Golem(budget=1.0, subnet_tag="devnet-beta", event_consumer=mySummaryLogger.log, strategy=FilterProviderMS(blacklist, strat)
                ) as golem:
            async for completed in golem.execute_tasks(
                    worker
                    , tasks
                    , payload=package
                    , max_workers=2
                    , timeout=timeout
                    ):
                # await on_executed_task(completed)
                timestart=datetime.now()





if __name__ == "__main__":
    enable_default_logger(log_file="spyu.log")
    debug.dlog("starting")
    loop = asyncio.get_event_loop()
    task = loop.create_task(main())
    loop.run_until_complete(task)
