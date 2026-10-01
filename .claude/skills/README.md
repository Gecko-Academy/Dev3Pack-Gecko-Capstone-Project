# Skills in this repository

| Skill | Fires on | Will not |
|---|---|---|
| `gecko-connect-mcp` | connecting an assistant to `https://mcp.geckovision.tech/orquestra/mcp` | put a key in a config file |
| `gecko-buy-on-devnet` | running the buyer, a stuck buy, `expires`, a `[todo]` line | sign on mainnet, touch a key, write your checks |
| `gecko-read-a-refusal` | `refused: true`, `REFUSED on ...`, a Gecko refusal code | retry unchanged, weaken a check |
| `defend-my-capstone` | Friday, the defence, the six minutes, the cards | stage a card, fake a landing |
| `capstone-checkpoint` | finishing a milestone or checking before a commit | stage, commit, push, or run a live purchase |

# Writing your own skill

A skill is instructions your agent loads when it decides they are relevant, and ignores
the rest of the time. You write one so you stop explaining the same thing every session.

## Where it lives

```
.claude/skills/<skill-name>/SKILL.md
```

One directory per skill, one `SKILL.md` inside it. Claude Code reads `.claude/` from the
repository root when you start it in this folder, so a skill you add here works for
anyone who clones the repository.

## The frontmatter

```yaml
---
name: gecko-read-a-refusal
description: Use when a purchase was refused and the student wants to know why ...
allowed-tools: Read, Grep, Bash(uv run buyer:*)
---
```

- `name` matches the directory.
- `description` is the whole ballgame. Read the next section.
- `allowed-tools` is optional and narrows what the skill may use.

Below the frontmatter, write instructions to an agent. Imperative, ordered, with the
exact commands. Not an essay about the topic.

## The description decides whether the skill ever fires

When the model chooses between skills, it has read the `description` lines and nothing
else. A skill with a perfect body and a vague description never loads.

So write it for the router: name the situation in the words somebody actually types,
including the error they pasted.

**Bad:**

```yaml
description: A comprehensive guide to Solana purchases with Gecko.
```

**Good:**

```yaml
description: Use when a purchase was refused and the student wants to know why. Triggers
  on "refused: true", "REFUSED on", "product-unknown", "receipt-failed", "why did it
  refuse". Never retries a refusal unchanged and never weakens a check.
```

"Comprehensive guide" describes the document; the router needs the situation. Error
strings are the cheapest match you can give it. And the boundary in the description
("never retries") gives the router a reason to skip the skill for the wrong job.

## Make it refuse

Every skill here ends with what it will not do. The failure a skill is most likely to
cause is not doing nothing; it is confidently producing something plausible and wrong.

- **A claim you cannot back is worse than a missing answer.**
- **Say which command you did not run.**

## No keys, in any skill

No skill in this repository contains a private key, a seed phrase, or a keypair file, and
none should. Keys live in `~/.config/dev3pack/`, and only `buyer/signer.py` reads one.
Put that boundary in the `description` line, not only in the body.

## Before you commit it

1. Start a fresh session and type the problem in your own words, without naming the
   skill. If it does not load, the description is wrong, not the body.
2. Run every command in the body and paste what it actually printed.
3. Read the "will not" section and ask whether it would have stopped the last thing that
   went wrong.
