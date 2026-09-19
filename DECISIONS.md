---
svcdesk_decisions:
  C1: wallclock      # wallclock | business
  C2: immutable      # reopen | immutable
  C3: vip            # matrix | vip
---
<!-- ai-generated: 85% - Claude Code drafted the decisions and reasoning from specs/REQUIREMENTS.md, using the resolutions chosen via the /speckit-specify clarification questions; reviewed and accepted as-is -->

# Decisions

## C1 - SLA clock for P1

**Decision:** P1 tickets run on the wall clock: their 15-minute acknowledge and 4-hour resolve targets count nights, weekends and holidays. Every other priority (P2-P4) still pauses outside Mon-Fri 08:00-16:00 Europe/Warsaw.

**Rejected alternative:** Applying the same business-hours pause to P1 as to every other priority, so a P1 raised on Friday evening would not go late until Monday morning.

**Reason:** R-14 requires P1 to be tracked "around the clock", which only makes sense if its clock never pauses; R-13's blanket business-hours pause is written for the general case and would silently hide the worst outages for a whole weekend if it also applied to P1.

**Service owner:** The on-call incident manager, because they are paged specifically for P1s and are the one who has to explain why a stopped-work incident sat untouched over a weekend.

**Customer outcome:** When the whole organisation stops working, the desk's lateness clock keeps running even outside office hours, so an unattended P1 shows up as breached at the next SLA check instead of hiding until Monday.

## C2 - Closed tickets and reopening

**Decision:** Reopening applies only to tickets in state `resolved`, within 7 days of resolution. A `closed` ticket is fully immutable: no reopen, no edit, no repeated close.

**Rejected alternative:** Allowing reopen on both `resolved` and `closed` tickets within the 7-day window, as R-10's literal wording suggests.

**Reason:** R-09 states plainly that a closed ticket is immutable and that further work needs a new ticket via `related_to`; letting R-10 reopen a closed ticket would break that promise for exactly the tickets it protects. Closing is a deliberate, reporter-confirmed act in the R-07 flow; resolving is not. Drawing the line at close, not resolve, matches the one step that is genuinely the reporter's own sign-off.

**Service owner:** The service owner accountable for the ticket record's integrity to reporters and to audits, because immutability after close is what makes a closed ticket a trustworthy record of "this was fixed and confirmed."

**Customer outcome:** A reporter who finds the fix didn't work has a real, time-boxed way to reopen it before confirming closure; once they've confirmed the fix by letting it close, the record of that closed issue never silently changes underneath them.

## C3 - VIP reporters and the priority matrix

**Decision:** A VIP reporter's ticket priority is floored at P2: if the impact/urgency matrix would give P3 or P4, the ticket is raised to P2; if the matrix already gives P1 or P2, it is left unchanged.

**Rejected alternative:** A strictly matrix-only priority with no adjustment for any reporter attribute, leaving R-06 unimplemented.

**Reason:** R-05's "and from nothing else" rules out someone requesting or negotiating a priority by hand. R-06's VIP floor is not a request — it's a disclosed, automatic, deterministic rule applied identically to every VIP reporter, so it doesn't reintroduce the arbitrary override R-05 guards against. Implementing R-06 keeps the requirement the document itself ties to executive visibility, a goal named directly in REQUIREMENTS.md's Purpose section.

**Service owner:** The service desk product owner, because visibility of executive-reported issues to the desk is named directly in the requirements' purpose as their goal.

**Customer outcome:** Executive and VIP reporters get a guaranteed floor of visibility (never lower than P2) even when their issue looks minor on paper, without their attention ever letting a ticket jump ahead of a genuinely more severe P1.
