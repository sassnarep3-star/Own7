# Market and settlement evidence

This independent research supplement documents *what the cited operators' own documents say* about basketball markets, single bets, player props and same-game or traditional parlays. It is not an assertion that a particular wager, price or jurisdiction is available or lawful, and it does not establish the operative terms of a real transaction. Rules change; dated documents are identified by their stated effective date. Nothing here guarantees profit or eliminates randomness.

**Review date:** 3 November 2026 UTC. Source text was read directly with the page/PDF reader against each statement in `evidence.json`. The TOTO basketball section and general Bet Builder section, Fanatics Ohio basketball and general parlay sections, Oneida SGP and traditional-parlay sections, and the cited help and regulator pages were examined. The TOTO PDF has 74 pages; the accessible reader returned the first 30, which include the cited basketball and Bet Builder passages. This is not a review of the other pages or every clause. The rules and help pages are primary sources for their own wording, not proof of the terms that will apply to a future bet.

The `finding` fields describe the source; `research_implication` fields are our proposed data/validation design choices. `flags` deliberately store an empty `unverified_value` where precedence or applicability is unresolved. We do not estimate a correlation coefficient or claim any tested strategy performance in this supplement.

## Rebuild and check

```sh
python3 market-evidence/build.py
python3 market-evidence/build.py --check
```

The offline check validates source-domain allowlisting, unique row IDs, source references, blank unverified values and deterministic HTML output. It does **not** check whether external websites remain reachable, whether source text has changed, or whether terms apply to any individual; those require current primary-source verification.

## Integration handoff

The independent page is `market-evidence/index.html`. Please link it from the canonical site navigation and publish its five `MF` items on the main Flagged for Review page. The main site's HTML row-source checker must recognize the cited official operator and regulator domains; accepting arbitrary HTTPS hosts would be unsafe. Do not merge the page while the combined site's tests fail. No source or policy here should be generalized between operators, jurisdictions, market types or rule versions.
