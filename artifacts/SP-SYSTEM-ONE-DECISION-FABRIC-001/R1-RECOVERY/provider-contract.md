# R1-RECOVERY — Provider Contract

## DecisionProvider protocol (the only seam)

```python
class DecisionProvider(Protocol):
    name: str
    model: str
    async def evaluate(self, *, state: dict, contract: DecisionContract) -> DecisionResult: ...
```

Contract between the fabric and any provider:

1. **Never raises for provider-side problems.** Failures return results:
   - `ResultKind.UNAVAILABLE` — timeout, DNS, connection, 429, 5xx (transient)
   - `ResultKind.ERROR` — malformed body, unknown primitive, missing
     confidence/distribution, schema/contract mismatch
   - `ResultKind.ABSTAIN` — provider declines to classify
   - `ResultKind.DECISION` — answers present
2. **Returns canonical types only.** `Answer`, `DecisionResult` carry
   `Primitive.CHOICE|SCORE|BOOLEAN`. Provider vocabulary stays in the adapter
   (Jev: Choice/Score/Noul → recorded per-answer in
   `DecisionResult.raw_primitive_names` for provenance).
3. **Answers are complete per contract.** A DECISION contains exactly the
   contract's questions; missing/extra answers are ERROR.
4. **Distributions are preserved.** Choice answers carry the full probability
   map; the adapter computes top-1/top-2/margin; confidence is a separate axis.

## MockDecisionProvider

- Deterministic: identical inputs → identical outputs (request id derived from
  the canonical state hash).
- Fault injection via state keys (`_mock_fault`, `_mock_abstain`,
  `_mock_answers`) — used by conformance tests; keys are stripped before any
  live transport would see them.

## JevDecisionProvider

- Endpoint: `{JEV_BASE_URL}/v1/systemone`, model `typesafe-ai/jev`.
- Default base URL: `https://ai-gateway.vercel.com` (documented Gateway);
  overrides are recorded as provenance events by `providers/config.py`.
- Transport is injectable for deterministic tests; the default transport uses
  httpx (optional dependency) and maps HTTP classes:
  - 429 / 5xx / transport exceptions → `UNAVAILABLE`
  - other 4xx / malformed / mismatched payloads → `ERROR`
- Normalization table (frozen §4/§9):
  | Jev native | canonical |
  |---|---|
  | Choice | choice |
  | Score | score |
  | Noul | boolean |
  | (AI SDK) boolean/probability | boolean |

## Configuration contract

| Variable | Default | Notes |
|---|---|---|
| `SINTRAPRIME_DECISION_PROVIDER` | `mock` | unknown values → mock |
| `SINTRAPRIME_DECISION_SHADOW_ONLY` | `1` | any of `0/false/no` disables — a provenance event |
| `SINTRAPRIME_DECISION_TIMEOUT_MS` | `2500` | positive int; invalid → default |
| `JEV_BASE_URL` | Gateway root | override = provenance event |
| `JEV_MODEL` | `typesafe-ai/jev` | |
| `JEV_API_KEY` | none | live auth requires explicit env; never in source |
