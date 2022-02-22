# filter_dups_ms.py
# blacklist providers for where an entry exists in the spyu database
# otherwise handoff to filterms

import debug
from .filterms import FilterProviderMS, _partial_match_in

from yapapi.strategy import SCORE_REJECTED, SCORE_NEUTRAL \
    , SCORE_TRUSTED, ComputationHistory, MarketStrategy


class SpyUFilterMS(FilterProviderMS):
    def __init__(self, con, whitelist, *args):
        self._con = con
        super().__init__(*args)
        self.whitelist=whitelist
        self.lowscored=set()

    def _find_partial_match(self, addr):
        """ return the whitelist partial match for a full addr """
        match = None
        for element in self.whitelist:
            if addr.startswith(element):
                match = element
                break
        return match

    async def score_offer(self, offer, history=None):
        name = offer.props["golem.node.id.name"]
        ss = "SELECT COUNT(*) FROM provider WHERE addr = "  \
                f"'{offer.issuer}'"
        count=self._con.execute(ss).fetchall()[0][0]
        if count == 1:
            score = SCORE_REJECTED
            print(f"skipping {name}@{offer.issuer}, reason:"
                    " already have model information")
            partial_addr = self._find_partial_match(offer.issuer)
            if partial_addr != None:
                debug.dlog(f"discarding {partial_addr}", 11)
                self.whitelist.discard(partial_addr)
                self.whitelist.discard(name)
            debug.dlog(f"remaining count: {len(self.whitelist)}")
        else:
            print(f"scoring {name}@{offer.issuer} count: {count}")
            score = await super().score_offer(offer, history)

        if score == SCORE_REJECTED:
            partial_addr = self._find_partial_match(offer.issuer)
            if partial_addr != None:
                debug.dlog(f"discarding {partial_addr}")
                self.whitelist.discard(partial_addr)
                self.whitelist.discard(name)
                self.lowscored.add(f"{name}@{offer.issuer}")

        return score

    async def decorate_demand(self, demand):
        return await super().decorate_demand(demand)

