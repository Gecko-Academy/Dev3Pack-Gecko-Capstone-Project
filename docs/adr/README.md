# Decision records

An architecture decision record is a short file that says what you decided, what forced
the decision, and what the decision now rules out. One decision per file, written when
you make it, never rewritten afterwards.

You can write one in ten minutes. Copy [`TEMPLATE.md`](TEMPLATE.md), fill the seven
sections, commit it with the code it governs.

## When a decision deserves one

Write a record when any of these is true.

**It is hard to reverse.** Money moved, a transaction landed, an account exists at an
address derived from a name you cannot change. Reversing it costs more than a revert.

**It crosses a boundary somebody else depends on.** The shape of a refusal message, the
field your buyer pins before it checks a prepared transaction, the units a price is
quoted in. If a classmate's code or Thursday's project reads it, changing it later
breaks them, not you.

**There was a real alternative, and somebody will propose it again.** Usually that
somebody is you in nine days, or a coding agent that reads your repository and helpfully
suggests the thing you already rejected. The record is what stops you relitigating it
from memory.

## When it does not

Most of the time. If a code comment is the right size, write the comment. Naming a
variable, picking a loop over a comprehension, choosing where a helper lives: none of
that needs a file. A record you wrote because records felt professional will not be read
by anybody, including you, and it makes the ones that matter harder to find.

Rough test: if you cannot name the alternative you turned down, there was no decision.

## The line that makes a record worth writing

**A record that forbids nothing decided nothing.** If the "what this forbids" section is
empty or vague, you wrote a summary of what the code does and put a date on it. Go back
and name the specific thing that is now out of bounds, in words a reader can hold you
to. "The buyer never retries a call that may have charged" is a decision. "We handle
retries carefully" is a mood.

## Naming

```
docs/adr/YYYY-MM-DD-slug.md
```

Like `docs/adr/2026-09-29-no-retry-after-paid-call.md`. The date is the day you decided,
and it never changes even when you later supersede the record. Sorting the folder gives
you the order you made decisions in, which is the only order that explains anything.

Use a slug that says the decision, not the topic. `no-retry-after-paid-call` tells a
reader what they will find. `retries` does not.

## An accepted record is never edited

Not for typos in the reasoning, not to soften a position that aged badly. When a
decision turns out to be wrong you write a **new** record, dated today, that says it
supersedes the old one, and you add one line at the top of the old file pointing
forward:

```
Status: superseded by 2026-10-01-cache-prices-for-one-block.md
```

That is the only edit an accepted record ever gets.

This feels wrong the first time and it is the whole point. The reasoning that turned out
to be wrong is the most valuable thing in the folder. It tells the next reader what
looked true at the time, which evidence was missing, and what changed. Edit it and you
have deleted the only record of how you got it wrong, and left something that looks like
you were right all along.

## A worked example

Your buyer calls a paid service. The call times out. You have no response and no idea
whether you were charged.

The record says: retrying could pay twice for one result, and the failure gives you no
way to tell the two cases apart, so the buyer does not retry a call that may have
charged. It returns a refusal naming the call, the amount at risk, and the fact that the
outcome is unknown, which is a worse user experience and an honest one. This forbids any
automatic retry, any retry loop wrapped around the payment path, and any "it probably
did not go through" assumption in the code. The alternative, retrying with an
idempotency key, is better and stays available the day the service actually supports
one, so this is a two-way door.

Four sentences. It names a rule, it forbids three specific things, and it tells the next
person what would make it change.
