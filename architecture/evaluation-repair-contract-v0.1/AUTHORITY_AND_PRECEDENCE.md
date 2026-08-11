# Authority and Precedence

Lower rank number = higher authority.

1. `deterministic_validator`, `schema_validator`, `security_policy_check` (rank 1)
2. `score_aggregator` / `fake_adapter_oracle` (rank 2–3)
3. `model_judge` (rank 7, advisory only)

A model judge with `authoritative_for_executable=true` is invalid (`EVR-AUT-0001`).
