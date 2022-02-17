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
# import traceback
import sys
import io
import argparse
import sqlite3
import tempfile
import pathlib
import os
import traceback

from yapapi import Golem, Task, WorkContext
from yapapi.log import enable_default_logger
from yapapi.payload import vm
import yapapi
import yapapi.log

import debug
from .filterms import FilterProviderMS, get_gnprovider_as_list
from . import utils
from .mysummarylogger import MySummaryLogger
from .model.create_db import create_db
from .luserset import luserset
from .model.mymodel import MyModel
from .model.get_datadir import get_datadir

g_source_dir=pathlib.Path(__file__).resolve().parent









def on_accepted_result(myModel :MyModel, mySummaryLogger: MySummaryLogger):
    """closure handler for each task a worker executes"""
    # called by provision_to_golem
    async def on_accepted_result_closure(result):
        # result := { provider_name: , json_file: , provider_id: , agr_id: }
        """ gatheredIntel := { unixtime: , name: , addr: , model: }"""
        debug.dlog(f"golem.execute_tasks has returned a Task object"
            f" with result: {result}", 11)
        with open(result['json_file'], "r") as json_fp:
            gatheredIntel = json.load(json_fp)
        providerId = myModel.fetch_field_value(f"SELECT providerId from"
        f" provider WHERE addr = '{gatheredIntel['addr']}'")
        if providerId == None:
            providerId = myModel.insert_and_id("INSERT INTO 'provider'(addr)"
            f" VALUES (?)", [ gatheredIntel['addr'] ] )

        nodeInfoId = myModel.insert_and_id("INSERT INTO 'nodeInfo'"
            f"(providerId, modelname, unixtime, nodename)"
                " VALUES(?, ?, ?, ?)"
                , [ providerId, gatheredIntel['model']
                    , gatheredIntel['unixtime'], gatheredIntel['name'] ]
                )
        myModel.execute("INSERT INTO 'agreement' (nodeInfoId, id) VALUES"
            " (?, ?)", ( nodeInfoId, result['agr_id'],))
        myModel.execute("INSERT INTO extra.offer (nodeInfoId, data) VALUES"
            " (?, ?)", [ nodeInfoId, json.dumps(result['offer']) ] )
        return [ nodeInfoId ]
    return on_accepted_result_closure




































class Provisioner():
    """setup context and interface for launching a Golem instance"""
    def __init__(self, perRunBudget, subnet_tag, payment_driver
            , payment_network, event_consumer, strategy, package
            , result_callback, golem_timeout=timedelta(minutes=6)):
        self._perRunBudget         =perRunBudget
        self.__golem_timeout        =golem_timeout # the timeout for the
            #golem instance | >= script timeout
        self._subnet_tag            =subnet_tag
        self._payment_driver        =payment_driver
        self._payment_network       =payment_network
        self._event_consumer        =event_consumer
        self._strategy              =strategy    # incorporates logic to
            # prevent work being resent to the same node in the same run
        self.__tempdir              =tempfile.TemporaryDirectory() # cleans
            #up on garbage collection
        self._workdir               =self.__tempdir.name
        self._package               =package
        self._result_callback       =result_callback
        self.__env_printed          =False
        self.__timeStartLast        =None
        self.nodeInfoIds           =[] # inspected
        # comment: golem_timeout set too low (e.g. < 10 minutes) might
        #result in no offers being collected















    async def _worker(self, context: WorkContext, tasks: AsyncIterable[Task]):
        """run spy script, d/l, and store provider ids and filepath to d/l
            in result"""
        """
        context.id -> activity id; same as ActivityCreated :event.act_id
        context.provider_name -> name of provider
        context.provider_id -> node address
        context._agreement_details.raw_details.offer -> offer
        """

        async for task in tasks:
            agr_id=context._agreement_details.agreement_id
            debug.dlog(
                    f"starting work: context id: {context.id},"
                    f" {context.provider_name}, {context.provider_id}"
                    f"\nagreement id is: {agr_id}"
                    )

            script = context.new_script(timeout=timedelta(minutes=2))
            script.run("/root/provider.sh", context.provider_name,
                    context.provider_id, str(datetime.now().timestamp()))
            target=f"{task.data['results-dir']}/{context.provider_id}.json"
            script.download_file(f"/golem/output/intelGathered.json", target)
            try:
                yield script
            except asyncio.CancelledError:
                debug.dlog(f"CancelledError inside worker")
                raise
            except:
                debug.dlog(f"other exception being raised!")
                raise
            else:
                # place result along with meta into a dict
                result_dict= { 'provider_name': context.provider_name
                        , 'json_file': target
                        , 'provider_id': context.provider_id
                        , 'agr_id': agr_id # may be used to lookup additional
                        # info in MySummaryLogger
                        , 'offer':
                        context._agreement_details.provider_view.properties
                        }
                task.accept_result(result_dict)















    async def __call__(self):
        """ enter market """
        self.__timeStartLast = datetime.now() # probably don't need this as
        # an attribute

        async with Golem(
                budget=self._perRunBudget
                , subnet_tag=self._subnet_tag
                , payment_driver=self._payment_driver
                , payment_network=self._payment_network
                , event_consumer=self._event_consumer.log
                , strategy=self._strategy
                , stream_output=False
                ) as golem:


            """ output parameters once """
            if self.__env_printed==False:
                utils.print_env_info(golem)
                self.__env_printed=True

            async for completed_task in golem.execute_tasks(
                    self._worker
                    , [Task(data={"results-dir": self._workdir})]
                    , payload=self._package
                    , max_workers=1
                    , timeout=self.__golem_timeout # arbitrary if
                        # self._wait_for_provider_timeout less
                    ):
                    result = completed_task.result
                    """ keys->'provider_name', 'json_file', 'provider_id',
                        'agr_id', 'offer' """
                    agr_id = result['agr_id']
                    try:
                        self.nodeInfoIds.extend(
                                await self._result_callback(result)
                                )
                    except Exception as e:
                        tb=sys.exc_info()[2]
                        print(f"\033[1mEXCEPTION:\033[0m\n")
                        print(f"{traceback.print_exc()}")
                        raise e



        if (datetime.now() - self.__timeStartLast) \
                > ( self.__golem_timeout - timedelta(minutes=1) ):
            return True
        else:
            return False













#####################################
#           spyuCTX                 #
#####################################
class spyuCTX:
    # -+-+-+-+ __init__ -+-+-+-+-+
    def __init__(self):
        datadir = get_datadir() / "gc_spyu"
        try:
            datadir.mkdir(parents=True)
        except FileExistsError:
            pass
        dbfilepath=datadir / "gc_spyu.db"

        self.myModel=MyModel(dbfilepath)
        self.mySummaryLogger=None
        self.provisioner=None


    # +++++++++ __call __ +++++++++++++
    async def __call__(self, CPUmax=Decimal("0.361"), ENVmax=Decimal("inf")
            , maxGlm=Decimal("1.0"), STARTmax=Decimal("0.37")
            , perRunBudget=Decimal("0.1"), whitelist=None):

        args=self._augment_parser().parse_args()
        self._check_args(args)
        if not args.disable_logging:
            enable_default_logger(log_file=args.log_file)

        whitelist = set(get_gnprovider_as_list())
        self.whitelist = whitelist
        blacklist=luserset()
        glmSpent=Decimal(0.0)
        package = await vm.repo(
            image_hash=
            "c1d015f76bbe8d6fa4ed8ffbd5280e261f4025dcca75490f0fd716cf"
        )
        strat=yapapi.strategy.DummyMS(
            max_fixed_price=Decimal("0.1")
            , max_price_for={
                yapapi.props.com.Counter.CPU: CPUmax/Decimal('3600')
                , yapapi.props.com.Counter.TIME: ENVmax/Decimal('3600')
                }
        )
        filtered_strategy = FilterProviderMS(blacklist, strat)
        self.mySummaryLogger=MySummaryLogger(blacklist, self.myModel
                , self.whitelist)
        self.provisioner = Provisioner(perRunBudget=perRunBudget
                , subnet_tag=args.subnet_tag
                , payment_driver=args.payment_driver
                , payment_network=args.payment_network
                , event_consumer=self.mySummaryLogger
                , strategy=filtered_strategy, package=package
                , result_callback=on_accepted_result(self.myModel
                    , self.mySummaryLogger)
                )
        print(f"waiting on {' '.join(whitelist)}")
        cancelled=False
        while not cancelled and len(whitelist) > 0:
            cancelled = await self.provisioner()
            whitelist = blacklist.difference(whitelist)
            if len(whitelist) > 0:
                print(f"still waiting on {' '.join(whitelist)}")





    # +++++++++++ get_results ++++++++++++++
    def get_results(self):
        return self.mySummaryLogger, self.provisioner.nodeInfoIds, \
                self.myModel






    def _augment_parser(self):
        """ add to parser and parse CLI and return parser """
        parser = utils.build_parser("spyu : a provider provider cpu inspector")
        parser.add_argument('--spy', action="extend", nargs="+", type=str
                , help="space delimited list of node/node names to fetch"
                " information about")
        parser.add_argument("--disable-logging", action="store_true",
                help="disable yapapi logging")
        return parser

    def _check_args(self, args):
        if args.spy == None and os.environ.get('GNPROVIDER', None) == None:
            print("Usage: spyu --spy <space delimited list of node names>")
            print("Example: spyu --spy q53 sycamore")
            sys.exit(1)

        """ populate whitelist from environment (filterms) """
        if args.spy != None:
            for element in args.spy:
                if ',' in element:
                    try:
                        input("WARNING, commas seen in node names passed as"
                        " arguments to --spy. If this was unintentional"
                        " please quit otherwise press enter to proceed")
                    except KeyboardInterrupt:
                        print()
                        sys.exit(0)
                    else:
                        break
            whitelist=set(args.spy)
            os.environ['GNPROVIDER']=f'[{",".join(args.spy)}]'
        else:
            print("Using GNPROVIDER filterms environment variable to select"
                   " nodes")
            try:
                input("press enter to proceed")
            except KeyboardInterrupt:
                print()
                sys.exit(0)





















# save
# future_result = script.run("/bin/sh", "-c", "/bin/echo [$(lscpu -J | jq -c),$(lscpu -JC | jq -c)] | sed s/\"field\"/\"k\"/g | sed s/\"data\"/\"v\"/g")
# cat /proc/cpuinfo |grep "model name" |head -n1 | sed  -rn 's/^[^:]+:[[:space:]]([^[$]+)$/\1/p'
