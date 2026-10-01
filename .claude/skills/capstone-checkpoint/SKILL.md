---
name: capstone-checkpoint
description: Use when finishing a capstone milestone, checking what to run before a commit, or asking whether work is ready to push. Guides offline validation and a review of the worktree. Never stages, commits, pushes, runs a live purchase, or handles a key.
allowed-tools: Read, Grep, Bash(make scan), Bash(make lint), Bash(make test), Bash(make recorded), Bash(git status --short), Bash(git diff --check), Bash(git diff --stat)
---

# Capstone checkpoint

Use this before the student commits a coherent milestone. The student decides what to
stage, commit, and push; this skill only validates and reports.

## Workflow

1. Read the relevant project README and identify the milestone's check. Do not assume a
   project is complete because a command exits successfully.
2. Run the relevant local project check only when its behavior is clear, offline, and
   permitted by this skill's tool list. Otherwise report the command for the student to
   run. If the check is missing, ambiguous, or may use devnet/mainnet, do not run it.
3. Run `make scan` before a commit. If Python source changed, run `make lint`. If buyer
   code or tests changed, run `make test`.
4. If the buyer's recorded behavior changed, run `make recorded`. It is expected to report
   incomplete cases and may exit nonzero while student TODOs remain. Report its result
   accurately; do not call that a setup failure or claim the cases passed.
5. Review `git diff --check`, `git diff --stat`, and `git status --short`. Identify
   unrelated or pre-existing changes separately; do not stage or discard them.
6. Summarize the milestone, commands and outcomes, expected TODO/xfail state, and which
   files appear related to it. The student chooses the commit boundary and runs Git write
   commands themselves. A useful cadence is one commit after each coherent, checked
   milestone, then push the student's branch at least daily.

## Boundaries

- Never run `make smoke`, devnet/mainnet purchases, wallet creation/registration, or any
  command that reads, prints, copies, or moves a key.
- Never stage, commit, push, reset, stash, clean, or otherwise change Git state.
- Never write the student's `parse_intent`, check, or step-body TODOs. Explain the
  relevant docstring and test so the student can implement it.
- Recorded output is practice, not evidence of a landed purchase. Do not present it as a
  live run or receipt.
- A secret scan is a guard, not permission to keep a key in the repository.

## Report

State the milestone and its validation results, including any failing checks or expected
xfails. Say whether the diff contains unrelated changes and which files appear ready for
the student to review. Do not say "ready to commit" without naming what was checked.