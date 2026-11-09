# Goal: checkout-fix

## Objective
Fix checkout submission so a double click creates exactly one order.

## Constraints
- Preserve the existing public API and retry behavior.
- Keep unrelated user edits intact.

## Acceptance criteria
- AC1: A regression test demonstrates one order for two rapid submissions.
- AC2: The existing checkout tests pass.
