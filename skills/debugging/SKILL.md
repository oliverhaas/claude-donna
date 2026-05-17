---
name: debugging
description: Investigate root cause before proposing fixes. Cite the evidence (logs, source, profile, config) you used. Use when diagnosing bugs, performance regressions, styling glitches, or "why is X failing/slow?" questions.
user-invocable: false
---

# Debugging: Investigate First, Cite Evidence

Before proposing a fix, find the root cause. Don't fix the first thing that pattern-matches to "could plausibly cause this".

## The discipline

1. **Reproduce or observe the failure.** A failing test, a stack trace, a log line, a profile, a screenshot of the bad render. Without one of these, you're guessing.
2. **Form a hypothesis.** State it explicitly: "I think the SIGKILL is caused by OOM in the heavy worker." A hypothesis is testable; a hunch isn't.
3. **Find evidence that confirms or refutes it.** Read the chart/config, run the query, open the failing baseline image, check the deploy manifest. Don't jump to step 5.
4. **If refuted, form a new hypothesis.** Don't bend the evidence to fit the first guess.
5. **Then propose the fix.** Reference the evidence: "[chart/values.yaml:42] — the heavy worker has `memory: 512Mi` but the import job uses ~700Mi based on [the dump in logs]. Bump to 1Gi."

Skipping step 3 ("OOM is probably the issue, let me bump memory") is how you fix the wrong thing twice and the right thing on the third try.

## Categories that all require investigation first

- **Exceptions / test failures**: read the full traceback, find the actual offending line. Don't fix the closest plausible thing.
- **Performance regressions**: profile, don't guess. "Where does the 160ms actually go?" before "let me optimize this loop."
- **Styling glitches**: diff against a known-good baseline screenshot or compare against the spec. Don't guess "probably a font race" without checking the network panel.
- **Config drift / deploy issues**: read the actual chart/manifest/values file. Don't theorize about pod restarts when the value is one `cat` away.
- **"Called twice" / "fires N times" claims**: verify with a log or breakpoint before asserting.
- **Library / framework bugs**: read the library source before blaming it.

## Common anti-patterns

- **Hypothesis as conclusion**: stating "this is happening because X" without checking X.
- **Symptom-fixing**: silencing the error / adding a try/except / bumping the timeout instead of finding why the underlying call fails.
- **Doc-cargo-cult fixes**: copying a Stack Overflow snippet because the symptom matches, without verifying the cause matches.
- **Skipping the failing baseline**: changing screenshot test code without ever opening the actual diff image.
- **Profiling-by-vibes**: optimizing the wrong code path because it "looks slow".

## When the root cause is genuinely unknown

Say so. List the hypotheses you considered, the evidence you checked, what you can't access. "I checked the chart values and the worker logs but can't reach the production pod metrics. Best guess is OOM but unverified." beats a confident wrong fix.

## After the fix

See the `verification` skill — produce the evidence that the fix works (test passes, profile improves, page renders correctly) before declaring done. And sweep for the same bug class elsewhere.
