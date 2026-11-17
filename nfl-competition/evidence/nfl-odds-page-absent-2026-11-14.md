# Evidence — NFL.com publishes no odds page (checked 2026-11-14)

- URL requested: https://www.nfl.com/odds/
- Result as rendered: HTTP 404, page title "404 - Flag on the Play."
- Read on: 2026-11-14 (session arena/064da913-own7)
- Retrieval class: rendered text via the Arena page reader, full page (1 of 1 chunks).

## Body of the response as printed

404 - Flag on the Play.
BACK TO NFL.COM

(No odds table, no price, no operator name and no market list is present anywhere in the
rendered response. The remainder of the response is the site-wide icon sprite list and the
"browser you are using is no longer supported" notice.)

## What this does and does not establish

It establishes that the single URL a reader would try first for league-published prices
does not exist. It does not, on its own, prove that no NFL.com page anywhere prints a
price; that would require enumerating every page on the domain, which the NFL.com terms
restrict. This lab therefore records the finding as:

  "No official NFL page consulted by this project publishes an executable price, a point
   spread or a total offered by any operator. The price-snapshot store is built, its
   schema is published and its ingest contract is testable, and it holds zero rows."

The lab's own game-page read of 2026-11-14 (Commanders at Giants, Week 10) is consistent:
the official game page prints a score, a by-quarter table, game info and a standings
widget, and prints no point spread, no total and no price of any kind.

## Consequence for the eight requirements

- Requirement 1 (price-snapshot store): the store is built and empty. Opening and closing
  numbers cannot be recorded for a market that no consulted official source prices.
- Requirement 4 (fair line, market line, difference): the fair line is published, the
  market line is blank and the difference is blank. A difference is never printed as zero
  and never inferred from a fair line alone.
- Requirements 5 and 8 (staking columns; demotion gate): the staking half of the
  leaderboard and the return-based demotion triggers stay blank for the same reason. Only
  the signal half, which needs no price, carries numbers.
