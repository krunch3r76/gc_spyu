#!/usr/bin/env python3
from gc_spyu import spyu
from gc_spyu import utils
from gc_spyu.view.on_run_conclusion import on_run_conclusion
import debug
import pprint

if __name__ == "__main__":
    debug.dlog("starting")
    spyu_ctx = spyu.spyuCTX()
    utils.run_golem_example(spyu_ctx())

    mySummaryLogger, nodeInfoIds, myModel = spyu_ctx.get_results()
    mySummaryLogger.providersFailed.append(
        {"address": "0x3a8052f782c55f96be7ffbce22587ed917ad98b9", "name": "michal"}
    )
    merged_list = mySummaryLogger.providersFailed
    merged_list.extend(mySummaryLogger.skipped)
    if len(merged_list) > 0:
        msg = (
            "The following providers were skipped because they were"
            " unreachable or otherwise uncooperative:"
        )
        print(f"\n{msg}")
        print("-" * (len(msg) - 1))

        merged_pairs = set()
        for dict_ in merged_list:
            merged_pairs.add(
                (
                    dict_["name"],
                    dict_["address"],
                )
            )

        for name, address in merged_pairs:
            print(f"{name}@{address}")
        print("-" * (len(msg) - 1))

    if len(spyu_ctx.filtered_strategy.lowscored) > 0:
        msg = (
            "The following providers were skipped because they failed"
            " the scoring criteria:"
        )
        print(f"\n{msg}")
        print("-" * (len(msg) - 1))
        for low in spyu_ctx.filtered_strategy.lowscored:
            print(f"{low}")
        print("-" * (len(msg) - 1))

    if len(spyu_ctx.filtered_strategy.whitelist) > 0:
        msg = (
            "The following providers were skipped because they were not"
            " seen on the network:"
        )
        print(f"\n{msg}")
        print("-" * (len(msg) - 1))
        for unseen in spyu_ctx.filtered_strategy.whitelist:
            print(f"{unseen}")
        print("-" * (len(msg) - 1))

    print(
        "\n\033[0;32mTotal glm spent from all engine runs: \033[1m"
        + str(mySummaryLogger.sum_invoices())
        + "\033[0m"
    )

    if isinstance(nodeInfoIds, list) and (
        len(nodeInfoIds) > 0 or len(spyu_ctx.filtered_strategy.dupIds) > 0
    ):
        try:
            on_run_conclusion(
                mySummaryLogger, nodeInfoIds, myModel, spyu_ctx.filtered_strategy.dupIds
            )
        except KeyboardInterrupt:
            print("so be it")
