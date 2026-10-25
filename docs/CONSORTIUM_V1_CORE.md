# Consortium V1 core

## Status

Consortium V1A is implemented as a local authoritative service boundary that can later be replaced by a server-backed repository. Widgets do not mutate membership, roles, inventory, Contract progress, XP, or rewards directly.

## Domain and rules

`production_zero.core.consortium` owns the persisted network, Consortium, member, application, invitation, Contract, reward-receipt, and bounded activity models. Stable company IDs are used throughout. The local company defaults to `company.local` and may be replaced by a future authenticated identity.

Supported commands/services cover create, join, apply, invite, application processing, leave, remove, role changes, leadership transfer, settings, disband, Contract start, contribution, completion, expiration, reward delivery, and eligibility inspection.

- Policies: Open, Application, Invite Only.
- Roles: Chairman, Board Member, Member. Board Members can invite, process applications, and start Contracts; only the Chairman can change roles/settings, remove members, transfer leadership, or disband.
- Capacity milestones are data-driven: levels 1/5/10/15/20/30/40 unlock 10/15/20/25/30/40/50 members.
- Daily and Weekly offers use canonical runtime production definitions, `ProductionValueCalculator`, `ContractCapacityEstimate`, production-value requirement conversion, and a tunable `member_count ** 0.72` participant scale.
- Start materializes immutable gameplay snapshots: requirements, rewards, Consortium XP, eligible IDs, participant count, timestamps, and scaling inputs.
- Personal reward eligibility requires membership at start, at least one required unit contributed, and uninterrupted membership through completion. Leaving/removal permanently records forfeiture; rejoining cannot restore it.
- Local-player contributions atomically validate and consume Global Storage before shared progress is updated. Request IDs suppress retries and over-delivery is rejected.
- Each eligible participant receives the complete personal reward. Persistent member receipts and a separate Consortium-XP flag make completion idempotent.
- Completed and expired Contracts move into bounded history when a replacement offer is generated. Delivered goods are never returned.

## Persistence and migration

SQLite continues to store one atomic JSON state document. State schema version 4 adds `consortium`; missing data deserializes to a clean `ConsortiumNetwork` with no membership. The independent Factory split migration remains gated at schema version 3, so version-3 saves are repaired but not remigrated.

Persisted Consortium data includes members/roles, applications, invitations, available/active/history Contracts, eligibility snapshots, contribution maps, forfeitures, processed request IDs, reward receipts, XP delivery state, progression, settings, and bounded activity.

## Activity

Meaningful events enter the existing `CompanyCommunications.pending_activity` stream as `consortium` events. Repeated contributions by the same member to the same operation are coalesced in Consortium history. Both activity stores are bounded.

## Files

- `src/production_zero/core/consortium.py`
- `src/production_zero/core/state.py`
- `src/production_zero/core/commands.py`
- `src/production_zero/persistence/sqlite_store.py`
- `src/production_zero/ui/main_window.py` (state-copy integration)
- `tests/test_consortium.py`

## Deliberately deferred

Networking, chat, Events, Shared Research/upgrades, a shared warehouse/bank, member trading, PvP, arbitrary permissions, revenue requirements, and capacities above 50 are not implemented.

## Validation

- Baseline: compileall passed; full suite 916 passed / 3 failed / 0 skipped in 53:06.83. The three failures were the existing ticker append-position assertion and two offscreen Research hover-image assertions.
- Final Consortium + directly affected set: 63 passed / 0 failed / 0 skipped in 4:44.01.
- Final full suite before the navigation expectation update: 932 passed / 4 failed / 0 skipped in 45:40.16. The additional failure was the exact pre-feature top-level tab list; its expected sequence was updated to include the required `Consortium` destination. The other three failures match baseline exactly.
- `compileall` passed. `git diff --check` passed with line-ending warnings only.
