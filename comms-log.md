---
lab4_comms:
  awareness: 2026-10-24T10:18:38Z
  detection: 2026-10-24T10:18:09Z
  classification: 2026-10-24T10:25:00Z
  nis2:
    early_warning_due: 2026-10-25T10:18:38Z
    notification_due: 2026-10-27T10:18:38Z
    notification_sent: 2026-10-26T08:00:00Z
    final_report_due: 2026-11-26T08:00:00Z
  ksc:
    early_warning_due: 2026-10-25T10:18:09Z
    notification_due: 2026-10-27T10:18:09Z
    notification_sent: 2026-10-26T08:30:00Z
    final_report_due: 2026-11-26T08:30:00Z
  dora:
    initial_due: 2026-10-24T14:25:00Z
    initial_sent: 2026-10-24T13:00:00Z
    intermediate_due: 2026-10-27T13:00:00Z
    intermediate_sent: 2026-10-27T09:00:00Z
    final_due: 2026-11-27T09:00:00Z
  log:
    - {at: 2026-10-24T13:00:00Z, to: the financial supervisor, what: DORA initial notification of a major ICT-related incident}
    - {at: 2026-10-26T08:00:00Z, to: the CSIRT, what: NIS2 incident notification}
    - {at: 2026-10-26T08:30:00Z, to: the CSIRT, what: KSC incident notification}
    - {at: 2026-10-27T09:00:00Z, to: the financial supervisor, what: DORA intermediate report}
---
<!-- ai-generated: 85% - Claude Code computed the deadlines with a script from the incident's instants; the on-call chose the instants -->

# Communications log: the regulators' clocks

Suppose the shop is an entity that NIS2, the Polish KSC act and DORA all apply to. All instants are UTC.

## The three instants you defend

- **Awareness (NIS2), 2026-10-24T10:18:38Z.** The on-call acknowledged the P1 ticket 29 seconds after the page. From that moment
  a person knew that checkout was failing for customers, so the entity was aware of a significant incident.
- **Detection (KSC), 2026-10-24T10:18:09Z.** CheckoutErrorRate started firing in Prometheus. KSC counts "from the moment of
  detection", and the alert is the first moment a system detected the fault, 29 seconds before anyone acknowledged it.
- **Classification (DORA), 2026-10-24T10:25:00Z.** After the flags were off and service was back at 10:20:59Z, the checkout
  error ratio of about 10 % over several minutes was weighed against the major-incident criteria; the classification
  came about seven minutes after awareness, within 24 hours, so the DORA initial deadline is classification + 4 h.

## The log

| at (UTC) | to | what | clock it answers |
|---|---|---|---|
| 2026-10-24T13:00:00Z | the financial supervisor | DORA initial notification | DORA initial, due 2026-10-24T14:25:00Z |
| 2026-10-26T08:00:00Z | the CSIRT | NIS2 notification | NIS2 notification, due 2026-10-27T10:18:38Z |
| 2026-10-26T08:30:00Z | the CSIRT | KSC notification | KSC notification, due 2026-10-27T10:18:09Z |
| 2026-10-27T09:00:00Z | the financial supervisor | DORA intermediate report | DORA intermediate, due 2026-10-27T13:00:00Z |

The early warnings (24 hours from awareness and from detection) fall on Sunday 25 October. The log above holds the
notifications only; a real entity would also send the NIS2 and KSC early warnings before those instants.
