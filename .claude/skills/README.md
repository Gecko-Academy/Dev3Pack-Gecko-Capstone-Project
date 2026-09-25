# Writing your own skill

A skill is instructions your agent loads when it decides they are relevant, and ignores
the rest of the time. You write one so you stop explaining the same thing every session.

## Where it lives

```
.claude/skills/<skill-name>/SKILL.md
```

One directory per skill, one `SKILL.md` inside it. Put extra files next to it and
reference them from the body. Claude Code reads `.claude/` from the repository root when
you start it in this folder, so a skill you add here works for anyone who clones the
repository.

## The frontmatter

```yaml
---
name: gecko-first-call
description: Use when an agent has to call an API it has never seen and get the call right the first time. Triggers on "add this API to my agent", "integrate this API", a first call that came back 404 or 422 ...
allowed-tools: Bash(npx:*), Bash(gecko:*), Read, Write
---
```

- `name` matches the directory.
- `description` is the whole ballgame. Read the next section.
- `allowed-tools` is optional and narrows what the skill may use.

Below the frontmatter, write instructions to an agent. Imperative, ordered, with the
exact commands. Not an essay about the topic.

## The description decides whether the skill ever fires

When the model chooses between your skills, it has not read any of them. It has read
the `description` lines and nothing else. A skill with a perfect body and a vague
description never loads, and you will think skills do not work.

So write the description for the router, not for a person browsing the folder. Name the
situation, and name it in the words somebody actually types, including the error message
they pasted.

Same skill, two descriptions.

**Bad:**

```yaml
description: A comprehensive guide to API integration best practices with Gecko.
```

**Good:**

```yaml
description: Use when an agent has to call an API it has never seen and get the call
  right the first time. Triggers on "add this API to my agent", "integrate this API",
  "how do I call this", a first call that came back 404 or 422, or an OpenAPI file
  sitting in the repo that nothing uses yet. Proves the calls offline first, for zero
  cost and with no key. Never writes a private key or a keypair file.
```

Why the first one loses:

- "comprehensive guide" describes the document. The router needs the situation.
- "best practices" matches nothing. Nobody types it.
- No error strings. `404` and `422` are what a stuck developer pastes, and they are the
  cheapest match you can give the router.
- No boundary. The second one says it never writes a key, so the router has a reason to
  skip it for a task about key management instead of loading it and improvising.

A useful check: could a person read only the description and say "yes, that is my
problem right now"? If not, rewrite it before touching the body.

## Make it refuse

Every skill in this folder ends with a section saying what it will not do. Write one.

The failure a skill is most likely to cause is not doing nothing. It is confidently
producing something plausible and wrong. A skill that tells an agent what to say when it
cannot verify something is worth more than one that tells it what to do when everything
works, because the happy path was never the hard part.

Two rules worth copying:

- **A claim you cannot back is worse than a missing answer.** "I could not find the auth
  scheme in the docs" costs a minute. "Uses Bearer auth", guessed, costs an afternoon
  and sometimes a leaked key.
- **Say which command you did not run.** Output an agent did not see and quotes anyway
  is the worst thing it can hand you.

## No keys, in any skill

No skill in this repository contains a signing path, a private key, a seed phrase, or a
keypair file, and none should. This repository gets cloned under deadline, and a
repository containing a key-handling snippet eventually contains a key.

Put that boundary in the `description` line, not only in the body. The router reads the
description, so a boundary stated there keeps the skill from being loaded for a job it
should refuse. The body only helps after it has already loaded.

## Before you commit it

1. Start a fresh session and type the problem in your own words, without naming the
   skill. If it does not load, the description is wrong, not the body.
2. Run every command in the body, from a directory that is not yours, and paste what it
   actually printed. A quickstart nobody ran cold is how this repository has burned
   people before.
3. Read the "will not do" section and ask whether it would have stopped the last thing
   that went wrong.
