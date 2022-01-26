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
from datetime import datetime

from marshal_result import marshal_result

class MySummaryLogger(yapapi.log.SummaryLogger):
    def __init__(self, blacklist_ref):
        self._blacklist = blacklist_ref
        super().__init__()
        self._last_node_name = ''
        self._last_node_address= ''
        self._last_timestamp=Decimal('0.0')
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
            self._blacklist.add(event.provider_id)
            self._last_node_name=event.provider_info.name
            self._last_node_address=event.provider_id
            self._last_timestamp=Decimal(str(datetime.now().timestamp()))

        else:
            pass
            # print(f"repr of {type(event)}: {event}\n")
        super().log(event)

async def worker(context: WorkContext, tasks: AsyncIterable[Task]):
    async for task in tasks:
        print(task)
        script = context.new_script()
        future_result = script.run("/bin/sh", "-c", "/bin/echo [$(lscpu -J | jq -c),$(lscpu -JC | jq -c)] | sed s/\"field\"/\"k\"/g | sed s/\"data\"/\"v\"/g")

        yield script

        try:
            result=await future_result
        except:
            pass
            # instead reject and handle elsewhere


        task.accept_result(result=result)
        # one way to ensure multiple providers are not assigned is to score only once
        # and keep an in-memory database of scored in addition to the static db

async def main():
    blacklist=set()
    counter=count(1)
    package = await vm.repo(
        image_hash="eb6bbe94ef17b9071cb04226318c065aa657e9437c93200d175b6840",
    )

    tasks = [Task(data=None)]
    mySummaryLogger=MySummaryLogger(blacklist)
    while True:
        async with Golem(budget=1.0, subnet_tag="devnet-beta", event_consumer=mySummaryLogger.log, strategy=FilterProviderMS(blacklist)
    ) as golem:
            async for completed in golem.execute_tasks(worker, tasks, payload=package, max_workers=8):
                objects_j=json.loads(completed.result.stdout)
                raw_parse = marshal_result(objects_j)
                result_summary = dict()
                result_summary['provider_id']=mySummaryLogger._last_node_address
                result_summary['provider_name']=mySummaryLogger._last_node_name
                result_summary['timestamp']=str(mySummaryLogger._last_timestamp)
                result_summary['info']=raw_parse

                # print(f"------\n{result_j}\n------")
                with open(f'output{next(counter)}.txt', "w") as f:
                    # f.write(completed.result.stdout)
                    f.write(json.dumps(result_summary, indent=4))
                print(json.dumps(result_summary, indent=4))
                # print(completed.result.stdout)


if __name__ == "__main__":
    enable_default_logger(log_file="spyu.log")

    loop = asyncio.get_event_loop()
    task = loop.create_task(main())
    loop.run_until_complete(task)
