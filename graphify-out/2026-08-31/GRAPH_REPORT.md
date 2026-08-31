# Graph Report - .  (2026-08-31)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 134 nodes · 222 edges · 9 communities (7 shown, 2 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 9 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ae5de7e2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- MyEdenredSensor
- myedenred.py
- Account
- MY_EDENRED
- ConfigFlow
- myedenred/__init__.py
- manifest.json
- Card
- api/__init__.py

## God Nodes (most connected - your core abstractions)
1. `MY_EDENRED` - 24 edges
2. `Account` - 17 edges
3. `MyEdenredSensor` - 17 edges
4. `Card` - 15 edges
5. `MyEdenredError` - 14 edges
6. `MyEdenredAuthError` - 13 edges
7. `MyEdenredChallengeRequired` - 11 edges
8. `Transaction` - 9 edges
9. `async_relogin()` - 8 edges
10. `ConfigFlow` - 8 edges

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

## Communities (9 total, 2 thin omitted)

### Community 0 - "MyEdenredSensor"
Cohesion: 0.08
Nodes (15): Any, async_setup_entry(), MyEdenredSensor, ConfigEntry, HomeAssistant, Return the unit the value is expressed in., Return the state attributes., Apply account data to the entity state. (+7 more)

### Community 1 - "myedenred.py"
Cohesion: 0.16
Nodes (15): _challenge_id_from(), _log_token_expiry(), MyEdenredAuthError, MyEdenredChallengeRequired, MyEdenredError, Issue LOGIN request with an email 2FA challenge code., Base exception for MyEdenred API errors., Raised when authentication fails. (+7 more)

### Community 2 - "Account"
Cohesion: 0.13
Nodes (4): Account, Represents a MyEdenred account., Represents a MyEdenred account transaction., Transaction

### Community 3 - "MY_EDENRED"
Cohesion: 0.16
Nodes (8): MY_EDENRED, Issue LOGIN request and return a token., Issue CARDS requests., Issue ACCOUNT MOVEMENT requests., Interfaces to https://myedenred.pt/, Return stored cookies as a HTTP Cookie header., Return common request headers., main()

### Community 4 - "ConfigFlow"
Cohesion: 0.20
Nodes (8): ConfigFlow, Handle reauthentication triggered by an expired token., Ask for credentials again when the token has expired., Return authentication data or a challenge-required marker., MyEdenred config flow., Initialize the config flow., Handle a flow initialized by the user interface., Handle the email 2FA challenge.

### Community 5 - "myedenred/__init__.py"
Cohesion: 0.28
Nodes (12): ConfigType, async_reload_entry(), async_relogin(), async_setup(), async_setup_entry(), async_unload_entry(), ConfigEntry, HomeAssistant (+4 more)

### Community 6 - "manifest.json"
Cohesion: 0.17
Nodes (11): codeowners, config_flow, dependencies, documentation, domain, iot_class, issue_tracker, name (+3 more)

## Knowledge Gaps
- **10 isolated node(s):** `version`, `domain`, `name`, `documentation`, `issue_tracker` (+5 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MY_EDENRED` connect `MY_EDENRED` to `MyEdenredSensor`, `myedenred.py`, `Account`, `ConfigFlow`, `myedenred/__init__.py`, `Card`?**
  _High betweenness centrality (0.321) - this node is a cross-community bridge._
- **Why does `MyEdenredSensor` connect `MyEdenredSensor` to `myedenred.py`?**
  _High betweenness centrality (0.213) - this node is a cross-community bridge._
- **Why does `Account` connect `Account` to `myedenred.py`, `MY_EDENRED`?**
  _High betweenness centrality (0.187) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `MY_EDENRED` (e.g. with `Account` and `Card`) actually correct?**
  _`MY_EDENRED` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Account` (e.g. with `Transaction` and `MY_EDENRED`) actually correct?**
  _`Account` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `Card` (e.g. with `MY_EDENRED` and `MyEdenredAuthError`) actually correct?**
  _`Card` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `MyEdenredError` (e.g. with `Account` and `Card`) actually correct?**
  _`MyEdenredError` has 2 INFERRED edges - model-reasoned connections that need verification._