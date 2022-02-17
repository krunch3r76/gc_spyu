#!/usr/bin/env python3
from gc_spyu import spyu
from gc_spyu import utils
from gc_spyu.view.on_run_conclusion import on_run_conclusion
import debug

if __name__ == "__main__":
    debug.dlog("starting")
    spyu_ctx=spyu.spyuCTX()
    utils.run_golem_example(spyu_ctx())

    mySummaryLogger, nodeInfoIds, myModel = spyu_ctx.get_results()

    if len(mySummaryLogger.providersFailed) > 0:
        msg="The following providers were skipped because they were unreachable or otherwise uncooperative:"
        print(f"\n{msg}")
        print("-" * (len(msg)-1))
        for skipped in mySummaryLogger.providersFailed:
            print(f"{skipped['name']}@{skipped['address']}")
        print("-" * (len(msg)-1))

    print("\n\033[0;32mTotal glm spent from all engine runs: \033[1m" + str(mySummaryLogger.sum_invoices()) + "\033[0m")

    if isinstance(nodeInfoIds, list)  and len(nodeInfoIds) > 0:
        try:
            on_run_conclusion(mySummaryLogger, nodeInfoIds, myModel)
        except KeyboardInterrupt:
            print("so be it")
