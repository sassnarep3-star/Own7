"""Market-lifecycle desk (session arena/3f5c4cd6-own7).

Adds, without touching any other session's files:
  * an ordered origination pipeline (side -> total -> moneyline),
  * an append-only price-snapshot store for every originated market,
  * a leaderboard that separates signal from staking,
  * a pre-registered demotion gate (live -> paper),
  * a depth-of-replacement view consumed read-only from the cfdd desk,
  * an audit that every published correlation carries n and an official source.

No sportsbook price exists in this repository (rights constraint XS09/CF10 stands), so every
market-side field in the store is null with a stated reason. Nothing is inferred.
"""
