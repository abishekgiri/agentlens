# Manual Beta Process

Phase 3 is manual by design.

1. User installs AgentLens.
2. User runs a broken agent.
3. User sends diagnosis output, not secrets.
4. If they can share it safely, user sends an anonymized trace.
5. We save anonymized traces in `real_world_cases/`.
6. We manually review diagnosis accuracy.
7. We update `feedback/users.csv`.
8. We ask:
- What broke?
- Did diagnosis help?
- Did the fix work?
- Did you trust the diagnosis?
- What was confusing during install or setup?
- What would make this worth paying for?

Success means the user trusts the diagnosis enough to try the suggested fix.

Do not move to Phase 4 until real users validate the RCA engine.
