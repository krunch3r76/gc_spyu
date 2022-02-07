#!/usr/bin/env python3
# authored by krunch3r (https://www.github.com/krunch3r76)
# license GPL 3.0
import asyncio
from typing import AsyncIterable
from itertools import count
import json
from decimal import Decimal
from datetime import datetime, timedelta
import pprint
import pathlib
import debug
# import traceback
import sys
import io
import argparse
import sqlite3
import tempfile
import pathlib
import os

from yapapi import Golem, Task, WorkContext
from yapapi.log import enable_default_logger
from yapapi.payload import vm
import yapapi
import yapapi.log

from filterms import FilterProviderMS, get_gnprovider_as_list
import utils
from mysummarylogger import MySummaryLogger
from model.create_db import create_db
from luserset import luserset
from on_run_conclusion import on_run_conclusion
from get_datadir import get_datadir

g_source_dir=pathlib.Path(__file__).resolve().parent




class MyModel():
    def __init__(self, dbpath):
        self.con = create_db(dbpath)

    def execute(self, *args):
        debug.dlog(args)
        recordset = None
        recordset = self.con.execute(*args)
        return recordset

    def execute_and_id(self, *args):
        # debug.dlog(args)
        recordset = None
        cur = self.con.cursor()
        recordset = cur.execute(*args)
        lastrowid = cur.lastrowid
        rv = (lastrowid, recordset,)
        return rv

    def insert_and_id(self, *args):
        return self.execute_and_id(*args)[0]














def on_accepted_result(myModel :MyModel):
    """closure handler for each task a worker executes"""
    # called by provision_to_golem
    async def closure(result):
        # result := { provider_name: , json_file: , provider_id: , agr_id: }
        """ gatheredIntel := { unixtime: , name: , addr: , model: }"""
        debug.dlog(f"golem.execute_tasks has returned a Task object with result: {result}")
        with open(result['json_file'], "r") as json_fp:
            gatheredIntel = json.load(json_fp)
        providerId = myModel.insert_and_id("INSERT OR IGNORE INTO 'provider'(addr) VALUES (?)", [ gatheredIntel['addr'] ] )
        nodeInfoId = myModel.insert_and_id("INSERT INTO 'nodeInfo'(providerId, modelname, unixtime)"
                " VALUES(?, ?, ?)"
                , [ providerId, gatheredIntel['model'], gatheredIntel['unixtime'] ]
                )
        myModel.insert_and_id("INSERT INTO 'agreement'(nodeInfoId, id) VALUES (?, ?)", [ nodeInfoId, result['agr_id']])
        myModel.execute("INSERT INTO 'offer'(nodeInfoId, data) VALUES (?, ?)", [ nodeInfoId, json.dumps(result['offer']) ] )
        return [ nodeInfoId ]
    return closure




































class Provisioner():
    """setup context and interface for launching a Golem instance"""
    def __init__(self, perRunBudget, subnet_tag, payment_driver, payment_network, event_consumer, strategy, package, result_callback, golem_timeout=timedelta(minutes=6)):
        self._perRunBudget         =perRunBudget
        self.__golem_timeout        =golem_timeout # the timeout for the golem instance | >= script timeout
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
        self.__timeStartLast        =None
        self.nodeInfoIds           =[] # topologies downloaded
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
            debug.dlog(
                    f"starting work: context id: {context.id}, {context.provider_name}, {context.provider_id}\nagreement id is: {agr_id}"
                    )

            script = context.new_script(timeout=timedelta(minutes=2))
            script.run("/root/provider.sh", context.provider_name, context.provider_id, str(datetime.now().timestamp()))
            target=f"{task.data['results-dir']}/{context.provider_id}.json"
            script.download_file(f"/golem/output/intelGathered.json", target)
            try:
                yield script
            except asyncio.CancelledError:
                debug.dlog(f"****************************CancelledError inside worker**************************")
                raise
            except:
                debug.dlog(f"other exception being raised!")
                raise
            else:
                # place result along with meta into a dict
                result_dict= { 'provider_name': context.provider_name
                        , 'json_file': target
                        , 'provider_id': context.provider_id
                        , 'agr_id': agr_id # may be used to lookup additional info in MySummaryLogger
                        , 'offer': context._agreement_details.provider_view.properties
                }

                task.accept_result(result_dict)















    async def __call__(self):
        """ enter market """
        self.__timeStartLast = datetime.now() # probably don't need this as an attribute
        async with Golem(
                budget=self._perRunBudget
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
            async for completed_task in golem.execute_tasks(
                    self._worker
                    , [Task(data={"results-dir": self._workdir})]
                    , payload=self._package
                    , max_workers=1
                    , timeout=self.__golem_timeout # arbitrary if self._wait_for_provider_timeout less
                    ):
                    # condition result 1-lookup and add cost associated with the agreement id
                    result = completed_task.result
                    """ keys->'provider_name', 'json_file', 'provider_id', 'agr_id', 'offer' """
                    agr_id = result['agr_id']
                    self.nodeInfoIds.extend(await self._result_callback(result))



        if datetime.now() - self.__timeStartLast > ( self.__golem_timeout - timedelta(minutes=1) ):
            return True
        else:
            return False














#####################################
#           spyuCTX                 #
#####################################
class spyuCTX:
    def __init__(self, myModel):
        self.mySummaryLogger=None
        self.provisioner=None
        self.myModel=myModel

    async def __call__(self, CPUmax=Decimal("0.361"), ENVmax=Decimal("inf"), maxGlm=Decimal("1.0"), STARTmax=Decimal("0.37"), perRunBudget=Decimal("0.1"), whitelist=None):
        """ add to parser and parse CLI """
        parser = utils.build_parser("spyu : a provider cpu topology inspector")
        parser.add_argument("--disable-logging", action="store_true", help="disable yapapi logging")
        # parser.add_argument("--results-dir", help="where to store downloaded task results", default="/tmp/spyu_workdir")
        # parser.add_argument("--max-budget", help="maximum total budget", default=Decimal(1))
        args=parser.parse_args()

        if args.spy == None and os.environ.get('GNPROVIDER', None) == None:
            print("Usage: spyu --spy <space delimited list of node names>")
            print("Example: spyu --spy q53 sycamore")
            sys.exit(1)

        """ init """
        glmSpent=Decimal(0.0)

        """ populate whitelist from environment (filterms) """
        if args.spy != None:
            for element in args.spy:
                if ',' in element:
                    input("WARNING, commas seen in node names passed as arguments to --spy. If this was not intentional please quit otherwise press enter to proceed")
                    break
            whitelist=set(args.spy)
            os.environ['GNPROVIDER']=f'[{",".join(args.spy)}]'
        else:
            print("Using GNPROVIDER filterms environment variable to select nodes")
            input("press enter to proceed")

        debug.dlog(f"---++++ os.environ['GNPROVIDER'] is {os.environ['GNPROVIDER']}")
        whitelist = set(get_gnprovider_as_list())
        self.whitelist = whitelist
        """ create blacklist """
        blacklist=luserset()
        # TODO populate blacklist with node addresses according to rules such as < time since last

        """ enable logging """
        if not args.disable_logging:
            enable_default_logger(log_file=args.log_file)

        """ setup package """
        package = await vm.repo(
            image_hash="c1d015f76bbe8d6fa4ed8ffbd5280e261f4025dcca75490f0fd716cf"
        )

        """ setup strategy """
        strat=yapapi.strategy.DummyMS(
            max_fixed_price=Decimal("0.1")
            , max_price_for={
                yapapi.props.com.Counter.CPU: CPUmax/Decimal('3600')
                , yapapi.props.com.Counter.TIME: ENVmax/Decimal('3600')
                }
        )

        """ filter strategy """
        filtered_strategy = FilterProviderMS(blacklist, strat)

        """ setup event consumer """
        self.mySummaryLogger=MySummaryLogger(blacklist, self.myModel, self.whitelist)

        """ setup provisioner """
        self.provisioner = Provisioner(perRunBudget=perRunBudget, subnet_tag=args.subnet_tag, payment_driver=args.payment_driver, payment_network=args.payment_network, event_consumer=self.mySummaryLogger, strategy=filtered_strategy, package=package, result_callback=on_accepted_result(self.myModel))
        print(f"waiting on {' '.join(whitelist)}")
        cancelled=False
        while not cancelled and len(whitelist) > 0:
            cancelled = await self.provisioner()
            whitelist = blacklist.difference(whitelist)
            if len(whitelist) > 0:
                print(f"still waiting on {' '.join(whitelist)}")

        # return mySummaryLogger.sum_invoices(), provisioner.nodeInfoIds, myModel
        """
        print("\nTotal glm spent:", mySummaryLogger.sum_invoices())

        on_run_conclusion(provisioner.nodeInfoIds, myModel)
        """


    def get_results(self):
        return self.mySummaryLogger.sum_invoices(), self.provisioner.nodeInfoIds, self.myModel














if __name__ == "__main__":
    debug.dlog("starting")

    datadir = get_datadir() / "gc_spyu"
    try:
        datadir.mkdir(parents=True)
    except FileExistsError:
        pass
    dbfilepath=datadir / "gc_spyu.db"


    myModel =MyModel(str(dbfilepath))
    spyu_ctx=spyuCTX(myModel)
    utils.run_golem_example(spyu_ctx())
    sumInvoices, nodeInfoIds, myModel = spyu_ctx.get_results()

    if len(spyu_ctx.mySummaryLogger.skipped) > 0:
        msg="The following providers were skipped because they were unreachable or otherwise uncooperative:"
        print(f"\n{msg}")
        print("-" * (len(msg)-1))
        for skipped in spyu_ctx.mySummaryLogger.skipped:
            print(skipped)
        print("-" * (len(msg)-1))

    print("\nTotal glm spent:", sumInvoices)

    if isinstance(nodeInfoIds, list)  and len(nodeInfoIds) > 0:
        try:
            on_run_conclusion(nodeInfoIds, myModel)
        except KeyboardInterrupt:
            print("\nas you wish")
    
# save
# future_result = script.run("/bin/sh", "-c", "/bin/echo [$(lscpu -J | jq -c),$(lscpu -JC | jq -c)] | sed s/\"field\"/\"k\"/g | sed s/\"data\"/\"v\"/g")
# cat /proc/cpuinfo |grep "model name" |head -n1 | sed  -rn 's/^[^:]+:[[:space:]]([^[$]+)$/\1/p'
