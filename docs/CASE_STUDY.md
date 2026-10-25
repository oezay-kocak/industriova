# Industriova: from interconnected requirements to working software

## Context and evidence

Industriova is an industrial idle and factory-management application, originally named Production Zero. It provides a concrete setting for requirements analysis: production, energy, storage, logistics, money and progression interact continuously. A change to one rule can alter several other systems and the explanations shown to the user.

This case study addresses recruiters, Business Analysts, Product Owners, Requirements Engineers and people responsible for AI transformation. It focuses on inspectable work products and decisions. Evidence consists of the source, tests and dated engineering reports. This is a development playtest; no adoption, commercial performance, regulated deployment or complete human release acceptance is claimed.

The review date is 25 October 2026. Fresh checks and their limitations are recorded in [PORTFOLIO_RELEASE_REPORT.md](PORTFOLIO_RELEASE_REPORT.md). Older reports describe earlier checkpoints and sometimes superseded rules.

## The analysis problem

A production chain has more constraints than its visible recipe. A machine needs a valid location, a selected unlocked product, ingredients, power and shared storage. Goods committed to a shipment cannot remain available for another sale. A contract needs a consistent quantity, reward and settlement lifecycle. Research modifies applicable values without silently rewriting committed transactions.

The task is to turn these dependencies into precise state transitions and understandable feedback. For example, “deliver goods to contracts” leaves reservation, priority, partial fulfillment, cancellation and in-flight behavior undefined. The current [allocation planner](../src/production_zero/core/contract_allocation.py) makes those rules inspectable, with [priority tests](../tests/test_contract_priority_auto.py) and [integration tests](../tests/test_industriova_release_integration.py) supporting review.

## Requirements translated into system design

The project separates static definitions from owned card instances. Definitions describe machine families, production options and resources; instances carry ownership and upgrades. This prevents an individual upgrade from changing the global catalog.

| Concern | Implementation | Review question |
| --- | --- | --- |
| Authoritative state | [state.py](../src/production_zero/core/state.py) | Which facts are stored and which are derived? |
| Intent and validation | [commands.py](../src/production_zero/core/commands.py) | What must be true before a mutation commits? |
| Time and production | [simulation.py](../src/production_zero/core/simulation.py) | Does the rule hold for ticks and catch-up? |
| Logistics | [freight.py](../src/production_zero/core/freight.py), [settlement](../src/production_zero/core/freight_settlement.py) | When is stock reserved, removed and paid? |
| Persistence | [SQLite store](../src/production_zero/persistence/sqlite_store.py), [session writer](../src/production_zero/persistence/session_writer.py) | What survives failure, reload and shutdown? |
| Presentation | [main window](../src/production_zero/ui/main_window.py) and UI components | Does the screen explain the actual rule? |
| External boundary | [service interfaces](../src/production_zero/services/interfaces.py) | Which capabilities remain local implementations? |

These boundaries allow rules to be investigated without a complete native play session. They do not remove all coupling: several domain and UI modules are substantial, compatibility paths remain, and the historical toolchain needs consolidation.

## Structuring extensive development work

The [0.3 roadmap](industriova-03-implementation-roadmap.md) and phase reports divide work into performance, inventory, drag interactions, freight, statistics, economy, contracts and navigation. They record scope and checks, creating a trail from an observed problem to a bounded change and reviewable result.

Economic analysis is distinguished from implementation. The [recipe normalization analysis](industriova-03-phase11d-recipe-normalization-analysis.md) and [final calibration](industriova-03-phase11e-final-economy-calibration.md) compare alternatives before the [rebalance implementation report](industriova-03-phase11fg-economy-rebalance-implementation.md) describes runtime changes. An analytical scenario must not be presented as an already delivered feature.

These are artifacts of decomposition and traceability. They do not establish a formal agile process, team size or delivery velocity. Much of the development predates this portfolio preparation and was uncommitted; the existing Git history does not support fine-grained commit attribution for every phase.

## Economic balancing and data analysis

Balancing combines dependencies, cycle timing, capacity, upgrade costs and realized sales. An isolated machine's nominal output can overstate its benefit if upstream production, power, storage or freight is the bottleneck.

The calibration reports distinguish isolated quotes from financed whole-company comparisons. Assumptions and alternative curves are recorded rather than treating one formula as an objective optimum. The current [MK implementation](../src/production_zero/core/mk_upgrades.py), [fixed prices](../src/production_zero/core/fixed_prices.py) and [rebalance tests](../tests/test_economy_rebalance_mk.py) expose the chosen rules.

The transferable method is to define units, model dependencies, compare alternatives under a consistent baseline and test boundaries. Simulated cashflow is not player income, a business forecast or evidence of financial-market expertise. Long-run experience still needs human assessment.

## Learning from reported playtests

The [first real playtest fix report](first-playtest-fix-pass.md) records specific feedback: a confusing resource-flow indicator, a preconfigured starter machine, repeated Production Guide delays and contract values whose meaning needed clarification.

For the resource indicator, the important distinction was configured production potential versus instantaneous storage delta. Those answer different questions. A planning indicator should not disappear because a machine is temporarily blocked; an actual-flow display must account for stock movements. [Resource-flow consistency tests](../tests/test_resource_flow_consistency.py) and [playtest polish tests](../tests/test_live_playtest_polish.py) make parts of the intended semantics executable.

The report also records retaining Guide widgets instead of rebuilding them on each opening. This connects an interaction symptom to a specific cause and bounded remedy. Historical timings belong to that fixture and environment and are not reused here as a current performance promise.

The evidence has limits. Reports describe feedback and follow-up work, but there is no complete anonymized research dataset establishing participant counts, representative sampling or a usability success rate. A report explicitly stating that no second human playtest occurred cannot establish one.

## Investigating responsiveness and persistence

The [Research interaction report](research-interaction-polish-2026-09-13.md) describes ordered background saves. A subsequent [live-freeze investigation](research-live-freeze-diagnosis-2026-09-13.md) distinguishes callback time from delays after it and traces snapshot encoding and persistence.

The problem-solving method is to define the observed symptom, instrument the full path, reproduce it in a controlled fixture and isolate the remaining cost. A fast click handler alone does not prove the application stays responsive afterwards.

The persistence approach captures snapshots for ordered background processing. It retains transaction boundaries, retry and shutdown handling, with an explicit tradeoff: a purchase callback can return before its save is durable. Normal shutdown waits for outstanding work; termination during pending writes remains a limitation. [Live-save tests](../tests/test_research_live_save.py) and [SQLite tests](../tests/test_sqlite_store.py) support this behavior. This demonstrates a desktop persistence design, without a claim of banking-grade transaction processing.

## Quality assurance and acceptance

Tests cover domain rules, integration, migration, persistence and Qt interaction. Examples include invalid purchases without partial mutations, preserved in-flight goods after route changes, contract allocation, research prerequisites and save/load behavior. [Release integration tests](../tests/test_industriova_release_integration.py) connect several systems.

Portfolio verification runs every module in a fresh process through [run_release_tests.py](../scripts/run_release_tests.py). Isolation and timeouts make Qt state leakage and hanging interactions easier to identify. Individual module reports and combined results must be inspected; the runner's own exit code is insufficient.

Offscreen checks prove particular paths run and render under that environment. They do not establish native drag-and-drop, subjective responsiveness, all DPI configurations or gameplay acceptance. Fresh totals and unresolved failures belong in the [validation report](PORTFOLIO_RELEASE_REPORT.md), not in undated claims.

The final portfolio pass on 25 October 2026 demonstrates this distinction in practice: 15 initial failures were classified as two implementation defects and 13 obsolete expectations or fixtures. The tracing integration and compact header were repaired; outdated assumptions were corrected without deleting or disabling tests. The complete rerun passed all 3,784 tests in 121 modules. [QA_FINALIZATION.md](QA_FINALIZATION.md) records each original failure, its applicable rule and the resulting verification.

## Human direction and AI-assisted work

Product responsibility is distinct from generated implementation. The project initiator confirmed the following division of responsibility on 25 October 2026: the complete game idea, architecture, gameplay loop, underlying game logic and every feature were personally conceived, designed and directed by the initiator. The initiator planned the work and coordinated one or more AI agents. The initiator did not personally program the code; AI agents performed the implementation.

This authorship account is the initiator's explicit statement. Source, tests, analyses and phase reports provide evidence of the resulting system and development process; they are not used to manufacture line-level human coding contributions.

| Work area | Inspectable record | Attribution boundary |
| --- | --- | --- |
| Product intent and priorities | Roadmap, phase scopes and reported playtest requests | Initiator: complete concept, feature design, planning and direction |
| Architecture and gameplay logic | Domain boundaries, dependency models and executable rules | Initiator: conceptual design; AI agents: code implementation |
| Concepts and balancing | Alternatives, formulas and analyses | Initiator: game-system direction; generated calculations and analysis remain evidence to review, without a claim that every calculation was performed manually |
| Implementation | Python, catalogs and integration changes | AI agents wrote the code; the initiator claims no personal programming contribution |
| QA and investigation | Tests, diagnostics and dated findings | Automated results are distinct from human acceptance |
| Visual assets | Supplied batches, integration reports and owner declaration | Owner confirms GPT generation without external templates; reviewed hashes bind that declaration to the publication assets |
| Release preparation | Inventories, documentation, privacy and rights review | Publication requires owner approval |

The personal contribution presented here is conception, system and feature design, planning, and direction of AI-assisted delivery. Reports of playtesting and automated QA are attributed to their recorded methods; this statement does not imply that every test, calculation or investigation was personally performed by the initiator.

A defensible AI workflow sets constraints, decomposes changes, requests evidence, reviews outputs against criteria and revises based on defects. The reports contain artifacts compatible with that workflow. They do not justify claiming that AI autonomously delivered an accepted finished product or that every generated output was manually audited.

## Relevance to business analysis and AI transformation

| Capability | Concrete evidence | Transferable reasoning |
| --- | --- | --- |
| Requirements precision | Reservation, priority, settlement and renewal | Resolve ambiguity before behavior diverges |
| System analysis | State, command, simulation and persistence boundaries | Identify data ownership and downstream effects |
| Data-informed decisions | Recipe and upgrade comparisons with explicit assumptions | Compare alternatives using a consistent baseline |
| Defect analysis | Playtest follow-ups and Research tracing | Distinguish symptoms, causes and acceptance evidence |
| AI oversight | Bounded phases, tests and recorded limitations | Require verifiable outputs from generated work |
| Change governance | Historical reports, migrations and release inventories | Preserve context and make changes reviewable |

For banking-related roles, the connection is disciplined rule modeling, traceability and validation. The project does not demonstrate regulatory compliance, bank integrations, security certification, customer data processing or production financial controls.

## Limitations and next steps

Native Windows acceptance, extended balancing sessions and a consolidated release process remain necessary. Local Consortium and leaderboard implementations do not establish a deployed multiplayer system. Version identifiers and older packaging recipes are not fully consolidated.

The owner confirmed GPT creation of all artwork without external templates and chose to keep original source and documentation without a general open-source license. [RIGHTS.md](../RIGHTS.md) describes that scope, while [RIGHTS_REVIEW.md](RIGHTS_REVIEW.md) distinguishes the owner declaration, technical provenance and dependency obligations. Personal attribution is confirmed as described above. Publication and any visibility change still require explicit owner approval.

This preparation preserves Git history and game rules. It makes the work and its limits visible enough for another person to evaluate the reasoning, implementation and validation.
