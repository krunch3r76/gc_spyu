# filter_dups_ms.py
# blacklist providers for where an entry exists in the spyu database
# otherwise handoff to filterms

import debug
from .filterms import FilterProviderMS, _partial_match_in

from yapapi.strategy import (
    SCORE_REJECTED,
    SCORE_NEUTRAL,
    SCORE_TRUSTED,
    MarketStrategy,
)


class SpyUFilterMS(FilterProviderMS):
    def __init__(self, con, whitelist, *args):
        self._con = con
        super().__init__(*args)
        self.whitelist = whitelist
        self.lowscored = set()
        self.dupIds = set()

    def _find_partial_match(self, addr):
        """return the whitelist partial match for a full addr"""
        match = None
        for element in self.whitelist:
            if addr.startswith(element):
                match = element
                break
        return match

    async def score_offer(self, offer):
        name = offer.props["golem.node.id.name"]
        ss = (
            "SELECT COUNT(*), providerId FROM provider WHERE addr = "
            f"'{offer.issuer}'"
        )
        count, id_ = self._con.execute(ss).fetchall()[0][:2]
        if count == 1:
            self.dupIds.add(id_)
            score = SCORE_REJECTED
            debug.dlog(
                f"skipping {name}@{offer.issuer}, reason:"
                "\033[5m already have model information!\033[25m"
            )
            partial_addr = self._find_partial_match(offer.issuer)
            # if partial_addr != None:
            if True:
                debug.dlog(f"discarding {partial_addr}", 10)
                self.whitelist.discard(partial_addr)
                self.whitelist.discard(name)
            if partial_addr != None:
                self.dupIds.add(partial_addr)
            debug.dlog(f"remaining count: {len(self.whitelist)}")
        else:
            debug.dlog(f"scoring {name}@{offer.issuer} count: {count}")
            try:
                score = await super().score_offer(offer)
            except Exception as e:
                print(f"unhandled exception ignored: {e}")
                score = SCORE_NEUTRAL
        if score == SCORE_REJECTED:
            partial_addr = self._find_partial_match(offer.issuer)
            if partial_addr != None:
                debug.dlog(f"discarding {partial_addr}")
                self.whitelist.discard(partial_addr)
                self.whitelist.discard(name)
                self.lowscored.add(f"{name}@{offer.issuer}")
        return score

    async def decorate_demand(self, demand):
        try:
            result = await super().decorate_demand(demand)
        except Exception as e:
            print("unhandled exception during decorate_demand" f" invocation {e}")
        return result
