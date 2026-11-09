# Working state

## Current state
- Reproduced duplicate submission in the checkout component. No patch applied yet.
- Evidence: work/repro.txt; relevant handler: src/checkout.ts:82.

## Decisions
- Disable repeat submission while a request is pending. Preserve retry after a failed request.
- Hypothesis: local state should be sufficient; server idempotency is outside this task's scope.

## Verification
- Existing checkout test suite passes before changes. Command: npm test -- checkout.
- The new regression test has not been written or run yet.

## Dead ends
- A click debounce still allows a second order after the debounce interval. Do not repeat it.

## Next actions
1. Add the regression test for two submissions while the first is pending.
2. Add a pending guard, then run the focused suite.
- Completion: satisfy AC1 and AC2 in GOAL.md with recorded results.

## Open questions
- None blocking. Confirm failure-path retry behavior in the existing test fixture.
