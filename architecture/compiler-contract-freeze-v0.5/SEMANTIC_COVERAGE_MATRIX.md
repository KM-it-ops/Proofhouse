# Semantic coverage matrix — PromptRig IR v0.1

**Recovery status:** MISSION-006. This matrix classifies the frozen schema; it does not alter it.

| IR path(s) | Owner / status | Preservation path | Unsupported behavior | Evidence |
|---|---|---|---|---|
| `/spec_version` | compiler / mandatory | validation and artifact provenance | error | schema validation |
| `/project/name`, `/project/mode`, `/project/compilation_level`, `/project/description` | compiler / mixed | request instructions where applicable; per-artifact provenance | provenance retained | recovery provenance tests |
| `/objective/goal`, `/objective/target_users`, `/objective/success_criteria`, `/objective/failure_conditions` | compiler / mandatory | goal lowered; all paths retained in provenance | no silent success | semantic gate |
| `/requirements/*/{id,statement,priority,mandatory,acceptance}` | compiler / mandatory | validation and per-artifact provenance | no silent success | semantic gate |
| `/input_contracts/*/{id,name,required,schema}` | compiler / optional | per-artifact provenance | recorded provenance retention | semantic matrix test |
| `/output_contracts/*/{id,name,required,schema}` | adapter / optional section | one representable contract lowers; all paths retained in provenance | more than one required contract errors | recovery output-contract test |
| `/behavior/{instructions,constraints,uncertainty_policy,evidence_policy}` | compiler / mandatory | instructions lowered; all paths retained in provenance | no silent success | semantic gate |
| `/knowledge/sources/*/{id,kind,required,sha256}` | compiler / optional | per-artifact provenance | recorded provenance retention | semantic matrix test |
| `/memory/{mode,retention,sensitive_data_allowed}` | compiler / optional | per-artifact provenance | recorded provenance retention | semantic matrix test |
| `/tools/*/{id,description,input_schema,output_schema,side_effecting,approval}` | adapter+safety / optional | function payload when declared; provenance and safety pass | declaration mismatch or unsafe conflict errors | capability and safety tests |
| `/workflow/steps/*/{id,action,on_failure}` | compiler / optional | per-artifact provenance | recorded provenance retention | semantic matrix test |
| `/autonomy/{approval_policy,max_tool_calls,stop_conditions}` | safety / optional | read-only conflict enforced; all paths retained in provenance | unsafe side effect errors | safety matrix |
| `/security/rules/*`, `/privacy/rules/*` | safety / optional | no frozen machine-readable policy grammar exists | populated free-text policy fails closed | recovery safety test |
| `/provider_requirements/{required_capabilities,optional_capabilities}` | capability resolution / optional | decisions retained in artifact provenance | missing/contradictory or required unresolved declarations error | capability tests |
| `/evaluation/{dimensions,repair_limit,baseline_required,test_categories}` | validation / mandatory | schema validation and provenance | invalid values error | existing validation tests |
| `/deployment/targets/*`, `/assumptions/*`, `/open_questions/*` | orchestration / optional | per-artifact provenance | recorded provenance retention | semantic matrix test |
| `/provenance/{source_id,source_sha256}` | compiler / mandatory | artifact provenance and canonical IR digest | no silent success | provenance test |

Every successful artifact carries the complete source-path set, canonical IR digest, compiler/adapter identities, manifest digest, and capability decisions. This is the v0.1 preservation path for semantics that do not have a provider-request representation.
