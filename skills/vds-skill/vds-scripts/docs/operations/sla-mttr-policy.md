# SLA and MTTR Support Policy

This policy defines response and restoration targets for incidents in the `vds-scripts` platform tooling stack.

## Priority Definitions

| Priority | Description | Example Impact |
| --- | --- | --- |
| `P1` | Critical outage | Production automation blocked across teams |
| `P2` | Major degradation | Key workflow unavailable with partial workaround |
| `P3` | Minor degradation | Non-critical feature issue with workaround |
| `P4` | Low impact/request | Cosmetic defects or advisory improvements |

## SLA and MTTR Targets

| Priority | Acknowledge SLA | Mitigation SLA | MTTR Target |
| --- | --- | --- | --- |
| `P1` | 15 minutes | 60 minutes | 4 hours |
| `P2` | 30 minutes | 4 hours | 1 business day |
| `P3` | 4 business hours | 2 business days | 3 business days |
| `P4` | 1 business day | Planned backlog | 10 business days |

## Escalation Matrix

1. L1 Operations triages alerts and opens incident ticket with priority.
2. L2 Platform Engineering joins for root-cause and mitigation.
3. L3 Service Owner approves hotfix, rollback, or emergency config changes.
4. P1/P2 incidents require status updates every 30 minutes until mitigated.

## Incident Lifecycle Requirements

1. Detect and classify incident priority (`P1`..`P4`).
2. Acknowledge within SLA target.
3. Apply mitigation and recover service.
4. Confirm restoration against acceptance checks.
5. Publish incident summary and post-incident actions.

## Tracking and Evidence

- Incident tracker must store:
  - priority, owner, start time, ack time, restore time
  - mitigation actions and validation evidence
  - follow-up tasks for permanent fixes
- Weekly review reports include SLA compliance and MTTR trend by priority.
