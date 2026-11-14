# NFL.com Week 10 schedule page — what it publishes, and what it does not
url: https://www.nfl.com/schedules/2026/by-week/week-10
read_on: 2026-11-14
reader: Arena fetch_page rendered text, chunks 0-2
purpose: >
  This file exists to support one specific claim used by `prices.py`: that NFL.com, the only
  publisher this repository reads, publishes NO PRICE for any NFL fixture. The claim is not
  inherited from an earlier session; it was re-read for this desk on 2026-11-14.

## What the page prints for each fixture

Every fixture is presented as a headline link plus club logos, e.g.:

    - [Steelers at Bengals, Sunday, November 15th, 8:20 PM, NBC](https://www.nfl.com/games/steelers-at-bengals-2026-reg-10)

and each block then prints a venue line and two commercial links:

    [Tickets...](https://www.ticketmaster.com/...)   [Hotel...](https://www.marriott.com/...)

The fields printed per game are therefore: away club, home club, weekday, date, kick-off time,
broadcast network, venue, a Ticketmaster event link and a Marriott hotel-search link. For the
final game of the week the page additionally prints `Weather` and a one-word condition.

## What the page does NOT print

Across all 14 Week 10 fixtures the rendered text contains **no spread, no total and no moneyline
for any game**. The commercial links on the page are ticketing and hotel partners. No odds vendor,
line, price or implied probability appears anywhere in the rendered text.

The page does print the four clubs on bye with their records (CHI 7-2, DEN 7-2, PHI 2-7, TB 3-6),
which is a standings fact, not a price.

## Consequence for the price store

An opening number and a closing number cannot be recorded from this publisher, because this
publisher does not issue one. Every price cell in `data/price-snapshots.csv` is therefore blank,
with `price_state = unpriced` and a named reason. This is a property of the source, not a gap in
the work: substituting an unregistered third-party price would break the repository's own rule
that every table row cites a registered official source.
