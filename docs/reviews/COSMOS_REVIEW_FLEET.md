# Cosmos Review Fleet

The Cosmos review fleet uses specialized agents to provide complementary pull-request checks. Depending on repository configuration, the fleet can include:

- a PR author agent that owns the change and responds to feedback, CI failures, and merge conflicts;
- deep code review and risk analysis agents that examine correctness, security, and change impact; and
- a verifier agent that independently checks the implementation and available evidence.

Agents report findings on the pull request and keep their work attributable to their Cosmos sessions. They do not replace human review: a human remains responsible for approval and the final merge decision.