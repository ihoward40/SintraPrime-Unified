# WS8-CMRD-001 Phase 1 prototype

Run from the directory containing `ws8_cmrd`:

```bash
python3 -m ws8_cmrd.calculator --mailing-date 2026-09-24 --trigger mailing --period 30 --day-type calendar --start-day exclude --jurisdiction NJ --today 2026-09-24 --output timeline.json
```

For business days, supply at least one `--holiday YYYY-MM-DD`, or use the Python API with `holidays=[]` to state that the selected scenario has none. The JSON includes an ordered chronology, every counted date, inputs, assumptions, and version. Recalculation of the same inputs yields the same date and chronology; the run ID and generation timestamp are new. No legal rule, holiday calendar, or weekend adjustment is inferred from jurisdiction. `days_remaining` is relative to the explicit `--today` date for reproducible exports.

## Deterministic replay

```bash
python3 -m ws8_cmrd.replay ws8_cmrd/example-timeline.json
python3 -m unittest ws8_cmrd.test_calculator -v
```

Replay recalculates from the preserved inputs and compares every deterministic result field, including counted dates, chronology, assumptions, final date, and algorithm version. It excludes only the new run ID and generation timestamp. The frozen `test-manifest.json` contains six passing scenarios and nine failure scenarios. Replay is an internal consistency check, not proof of who created a receipt: a person who can alter the entire JSON can create a self-consistent replacement. Authenticity would require a separately governed signature or trusted storage receipt.
