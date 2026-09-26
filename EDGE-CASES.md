---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 45% - Claude Code drafted this from the practice fixture's own data and my review of METRIC-SPEC.md; I checked every number against the running service and edited the prose -->

# Edge cases in the practice event log

## E1 - clock skew produces a negative lead time

- What the log contains: Three (commit, deployment) pairs where the deployment's `at` is earlier
  than the commit's `at` it supposedly shipped: `sha-0040` (commit 18:51:41, deployed 18:37:47,
  -834s), `sha-0094` (-51s) and `sha-0123` (-780s). Two independent clocks - the developer's
  machine and the deployment pipeline's - disagree by a few minutes, and the commit lost.
- What a default definition would have done: A default `deployment.at - commit.at` implementation
  either reports a negative number for the metric outright (a dashboard showing "median lead time:
  -834 seconds" is nonsensical and destroys trust in every other number on the page), or someone
  "fixes" it by dropping negative pairs from the data, which quietly shrinks the sample and biases
  the median toward whatever is left.
- Why the rule is defensible: R-08 clamps the pair to zero and still counts it in
  `counts.lead_time_pairs`. Zero is honest about what we can actually claim ("we cannot show this
  change took negative time to ship") without discarding a delivery that genuinely happened, and
  without the discontinuity of "sometimes commits are silently invisible to the metric." A reader
  who drills into `anomalies.negative_lead_time_pairs` sees exactly how many pairs needed this
  clamp, which is a clock-quality signal a hidden default would erase.

## E2 - a revert of a revert

- What the log contains: `sha-0070` reverts `sha-0069` (change `CHG-0033`), and `sha-0071` reverts
  `sha-0070` - a revert of the revert, i.e. the team put `CHG-0033` back. All three commits carry
  `reverts` chains that terminate at `sha-0069`'s own `change_id`, and only `sha-0069` has a
  non-null `change_id` of its own.
- What a default definition would have done: A definition that counts every commit with a
  `change_id` (or every commit, full stop) as a separate change would report three changes here:
  the original work, the revert, and the re-revert. That triples the apparent throughput for a
  single piece of work that, at the end of the window, is exactly as merged as if nobody had
  touched it - `deployment_frequency` and `counts.changes` both inflate for zero net delivery.
  A team could hit its throughput targets in a sprint that shipped nothing.
- Why the rule is defensible: R-06 makes `reverts` transitively resolve to the original
  `change_id`, so a revert-of-a-revert collapses back to `CHG-0033` - one change, not three. This
  is what "distinct changes" has to mean if the metric is going to measure delivered work rather
  than commit-count churn: reverting a revert is not two additional deliveries, it is undoing an
  undo. `anomalies.revert_chains_collapsed` (2 here, for `sha-0070` and `sha-0071`) tells a reader
  exactly how much of that churn the log contains without changing what counts as a change.

## E3 - a hotfix that never touched `main`

- What the log contains: Four shas reach production on a branch other than `main` -
  `sha-0108`/`hotfix/6085` (DEP-0028), `sha-0127`/`hotfix/1544` (DEP-0033),
  `sha-0019`/`hotfix/2609` (DEP-0006) and `sha-0077`/`hotfix/4347` (DEP-0019) - all four
  deployments are otherwise ordinary successful production deployments.
- What a default definition would have done: The obvious-looking implementation filters
  `commit.branch == "main"` before computing lead time, on the assumption that "main" is where
  released work lives. That silently drops every hotfix from the lead-time sample and from
  `counts.changes` - the fastest, highest-pressure deliveries (the ones that shipped straight to
  production because they could not wait for a merge to `main`) become invisible to the metric
  meant to measure delivery speed, which is exactly backwards.
- Why the rule is defensible: R-09 says `branch` is never consulted for R-08 - a commit that
  reached production is in scope regardless of which ref it came from, because DORA's definition
  of "change" is about work that reached the user, not about the team's branching convention. The
  branch name is a workflow detail; production is production. `anomalies.commits_never_on_main`
  surfaces the four hotfixes as a separate signal (a process question - why did they bypass
  `main`?) instead of using them to quietly filter the metric itself.

## E4 - a deployment with zero linked commits

- What the log contains: Four production deployments in the window carry an empty `commits` list:
  `DEP-0026` and `DEP-0032` (both successful) and `DEP-0043`/`DEP-0044` (both failures).
  Configuration flips, feature-flag toggles or infrastructure-only releases plausibly ship nothing
  from the commit log.
- What a default definition would have done: A naive R-08 that iterates `for sha in
  deployment.commits: pair = ...` simply produces zero pairs for these and moves on - harmless by
  itself. The dangerous default is elsewhere: `change_fail_rate = failed / commits.length` style
  reasoning, or "drop deployments with no commits, they're not real releases," either divides by
  something that can be zero or removes two of the eight failures in this fixture from the
  denominator entirely, understating how often production deployments fail.
- Why the rule is defensible: R-10 keeps a commit-less deployment in every count and rate that is
  about deployments (frequency, change fail rate, rework rate) while contributing nothing to the
  metrics that are about commits (lead time). A deployment is a real production event whether or
  not the commit log can point to what moved; excluding it from `counts.deployments` because its
  payload wasn't code-shaped would make the denominator answer a different question than the one
  the dashboard claims to answer. `anomalies.deployments_without_commits` names the four so a
  reader can go check what they actually shipped.

## E5 - a deployment that failed and never recovered

- What the log contains: `DEP-0015` failed and is covered by `INC-0004`, opened
  2026-09-07T06:35:41Z - but `INC-0004` has no `resolved` event anywhere in the log. As of the
  window's end, the incident is still open.
- What a default definition would have done: A default recovery-time calculation needs a
  `resolved` timestamp to subtract from, so it either crashes/errors on this row, silently skips
  it (which understates how bad the incident load looks, since the worst, still-open incident is
  the one erased), or - worse - invents an end time (`now`, or the window's `to`) and reports a
  recovery time as if the incident were fixed, hiding an ongoing outage inside a healthy-looking
  median.
- Why the rule is defensible: R-12 with E5 excludes an unrecovered failure from the recovery-time
  median (you cannot honestly report how long a repair took when there has been no repair) but
  still counts it in `counts.open_failures`, which is a distinct, visible field. That keeps the
  median meaningful (only measuring durations that actually happened) while making sure an
  incident that is still hurting users cannot vanish from the report just because it lacks a
  closing timestamp - it shows up as a 1 in `open_failures` instead of a fabricated number in the
  median.

## E6 - overlapping incidents

- What the log contains: Eleven unordered pairs of incidents whose `[opened, end)` intervals
  intersect, almost all of them caused by `INC-0004` (the still-open incident from E5): because it
  never resolves, its interval runs from 06:35:41 all the way to the window's end, so it overlaps
  seven other incidents that occurred anywhere in the following two weeks (`INC-0005` through
  `INC-0011`). A further four pairs among the short incidents themselves also overlap in time
  (e.g. `INC-0005`/`INC-0010`, `INC-0007`/`INC-0008`).
- What a default definition would have done: A definition that computes "total incident time" by
  merging overlapping intervals, or by summing every incident's duration and calling that the
  recovery-time input, either merges `INC-0004`'s ballooning open-ended interval into everything it
  touches (making seven unrelated incidents look like one 15-day outage) or double/triple counts
  wall-clock time that several incidents share, inflating whatever aggregate is reported.
- Why the rule is defensible: R-13 computes recovery time **per failed deployment**, never per
  incident, and explicitly forbids merging or summing overlapping intervals. `DEP-0015`'s recovery
  time (had `INC-0004` resolved) would only ever be compared against `DEP-0015`'s own covering
  incident, regardless of what else happened to overlap it. `anomalies.overlapping_incident_pairs`
  exists purely as a red flag for the person reading the dashboard: eleven overlaps this dense,
  nearly all driven by one long-open incident, is itself a fact worth knowing, but it must never be
  allowed to distort a metric that is defined per-deployment.

## Gaming demonstration

The metric improved is `deployment_frequency_per_day` (rule `R-11`), and the incentive it rewards
is the oldest one in the DORA literature: ship more often, regardless of what "more often" is
shipping. `R-11` counts *any* production deployment in the window, of *any* outcome, with *any*
number of commits (E4 already established that an empty-commit deployment counts fully). Nothing
in the rule asks whether a deployment changed anything a user would notice.

`gaming/after.jsonl` adds a run of extra production deployments to the base log - each `outcome:
"success"`, each `unplanned: false`, each `commits: []` - timestamped inside the window but never
touching the base work: no base commit is retimed, no base deployment is moved earlier or has its
outcome flipped, nothing is deleted (R-19 conservation holds). Because R-10 counts an
empty-commits deployment in `counts.deployments` just like any other, this is enough to clear
`deployment_frequency_per_day`'s +25% margin (R-20) while touching not one commit that carries the
team's actual work: measured on the base commits and incidents alone, the true change lead time and
number of changes delivered are exactly what they were before (R-21) - because nothing about the
real deliveries changed.

In a real team this is what "deploy a no-op change to hit the DORA dashboard" looks like: redeploy
the current config, bump a version string nobody reads, ship an empty release with a green
checkmark. It costs almost nothing to produce and is invisible to anyone who only reads the
headline number. The people rewarded for it are exactly the people under pressure to show
improving delivery metrics without doing the (harder, slower) work of actually shipping more
real changes - a team lead defending their sprint metrics to management, or an engineer told their
review depends on the deployment-frequency graph trending up. The person who pays for it is
whoever reads that dashboard and concludes the team is delivering value faster than it actually is.
