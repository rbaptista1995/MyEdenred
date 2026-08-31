# Graph Report - ha-custom-component-myedenred-main  (2026-08-31)

## Corpus Check
- 20 files · ~3,554 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 146 nodes · 233 edges · 10 communities (9 shown, 1 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 10 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7342e210`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- MyEdenredSensor
- MY_EDENRED
- Account
- README.md
- ConfigFlow
- myedenred/__init__.py
- manifest.json
- Card
- api/__init__.py

## God Nodes (most connected - your core abstractions)
1. `MY_EDENRED` - 22 edges
2. `Account` - 20 edges
3. `Card` - 17 edges
4. `MyEdenredError` - 14 edges
5. `MyEdenredAuthError` - 12 edges
6. `MyEdenredSensor` - 11 edges
7. `MyEdenredChallengeRequired` - 9 edges
8. `Transaction` - 9 edges
9. `ConfigFlow` - 9 edges
10. `MyEdenredDataUpdateCoordinator` - 9 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `MY_EDENRED`  [EXTRACTED]
  example.py → custom_components/myedenred/api/myedenred.py
- `MY_EDENRED` --uses--> `Account`  [INFERRED]
  custom_components/myedenred/api/myedenred.py → custom_components/myedenred/api/account.py
- `MyEdenredAuthError` --uses--> `Account`  [INFERRED]
  custom_components/myedenred/api/myedenred.py → custom_components/myedenred/api/account.py
- `MyEdenredChallengeRequired` --uses--> `Account`  [INFERRED]
  custom_components/myedenred/api/myedenred.py → custom_components/myedenred/api/account.py
- `MyEdenredError` --uses--> `Account`  [INFERRED]
  custom_components/myedenred/api/myedenred.py → custom_components/myedenred/api/account.py

## Import Cycles
- None detected.

## Communities (10 total, 1 thin omitted)

### Community 0 - "MyEdenredSensor"
Cohesion: 0.11
Nodes (13): Any, async_setup_entry(), MyEdenredSensor, ConfigEntry, HomeAssistant, Set up all card sensors for the config entry., Represent the balance and transactions for one Edenred card., Return the entity name. (+5 more)

### Community 1 - "MY_EDENRED"
Cohesion: 0.11
Nodes (22): _challenge_id_from(), _log_token_expiry(), MY_EDENRED, MyEdenredAuthError, MyEdenredChallengeRequired, MyEdenredError, Issue LOGIN request and return a token., Issue LOGIN request with an email 2FA challenge code. (+14 more)

### Community 2 - "Account"
Cohesion: 0.12
Nodes (5): Account, Represents a MyEdenred account., Represents a MyEdenred account transaction., Transaction, Refresh card accounts without ever triggering a new login.

### Community 3 - "README.md"
Cohesion: 0.18
Nodes (10): Card, Configuration Through the interface, HACS (Recommended), Installation, Legal notice, myEdenred Card Integration, Transactions, Using a custom:browser-mod (+2 more)

### Community 4 - "ConfigFlow"
Cohesion: 0.17
Nodes (9): ConfigFlow, Handle reauthentication triggered by an expired token., Retry starting 2FA without asking for saved credentials., Use saved credentials once and continue directly to the 2FA code., Return authentication data or a challenge-required marker., MyEdenred config flow., Initialize the config flow., Handle a flow initialized by the user interface. (+1 more)

### Community 5 - "myedenred/__init__.py"
Cohesion: 0.19
Nodes (14): ConfigType, MyEdenredDataUpdateCoordinator, ConfigEntry, HomeAssistant, Fetch every card once per interval using the persisted session., async_reload_entry(), async_setup(), async_setup_entry() (+6 more)

### Community 6 - "manifest.json"
Cohesion: 0.17
Nodes (11): codeowners, config_flow, dependencies, documentation, domain, iot_class, issue_tracker, name (+3 more)

### Community 7 - "Card"
Cohesion: 0.21
Nodes (4): Card, Represents a MyEdenred card., Coordinate MyEdenred data updates for a config entry., Platform for the MyEdenred card balance sensors.

## Knowledge Gaps
- **17 isolated node(s):** `version`, `domain`, `name`, `documentation`, `issue_tracker` (+12 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MY_EDENRED` connect `MY_EDENRED` to `Account`, `ConfigFlow`, `myedenred/__init__.py`, `Card`?**
  _High betweenness centrality (0.226) - this node is a cross-community bridge._
- **Why does `Account` connect `Account` to `MY_EDENRED`, `myedenred/__init__.py`, `Card`?**
  _High betweenness centrality (0.166) - this node is a cross-community bridge._
- **Why does `MyEdenredSensor` connect `MyEdenredSensor` to `myedenred/__init__.py`, `Card`?**
  _High betweenness centrality (0.141) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `MY_EDENRED` (e.g. with `Account` and `Card`) actually correct?**
  _`MY_EDENRED` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Account` (e.g. with `Transaction` and `MY_EDENRED`) actually correct?**
  _`Account` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `Card` (e.g. with `MY_EDENRED` and `MyEdenredAuthError`) actually correct?**
  _`Card` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `MyEdenredError` (e.g. with `Account` and `Card`) actually correct?**
  _`MyEdenredError` has 2 INFERRED edges - model-reasoned connections that need verification._