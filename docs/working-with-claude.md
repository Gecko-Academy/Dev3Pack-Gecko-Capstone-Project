# Working with Claude Code

You have the tool. This page is about the habits that make it produce code you can
defend on Monday, and the prompts that get there faster.

Everything below assumes you run `claude` inside this repository, so it has already read
`AGENTS.md`.

## The loop

Explore, plan, act, verify. In that order, every time, and the order is the whole trick.

**Explore** means the agent reads before it writes. For anything touching more than one
file, your first message should not contain the word "write". Ask it to read the project
README, your store, and your buyer, then tell you back what the buyer currently does
when the budget is short. If its summary is wrong, you just saved yourself an hour of
wrong code. If it is right, it now has the context it needed anyway.

**Plan** is the highest-value habit on this list and the one beginners skip. Claude Code
has a mode for it: press `Shift+Tab` until the footer says plan mode, or start the
session with

```bash
claude --permission-mode plan
```

In plan mode it reads and thinks and proposes, and it cannot edit a file until you
accept. Read the plan like a pull request. The plan is where you catch "I will add a
`price_float` field" for the cost of one sentence, instead of catching it after it has
touched four files.

**Act** is the easy part. Keep it small. One behaviour per turn beats a rewrite you have
to review as a whole.

**Verify** means you run the command yourself. That has its own section below, because
this is where students get burned.

A task that spans more than about three files starts with reading. A task that is one
function in one file you already have open does not need a plan, and demanding one is
just ceremony.

## Six prompts for this project

Copy these. Change the file names to yours.

### 1. The failing test first

```
Before you change any code: write a test that asserts the buyer refuses when the
budget is 1200000 and the cheapest item is 1500000, and that the refusal message
contains both numbers. Run it. Paste the failure output. Then stop and wait.
```

Shaped so the test is written against the behaviour you want, not against the code that
exists. A test written after the fix tends to describe the fix. "Then stop and wait"
stops it from fixing the thing in the same breath, which is how you end up unable to
tell whether the test ever failed.

### 2. Find the bug instead of guessing at it

```
The weekly challenge check in my course folder says my store name check fails. Here is
the full output:

<paste>

Do not change anything yet. Find the line in my store that triggers this and quote it
back to me with the file and line number. If two lines could explain it, give me both
and say how to tell them apart.
```

Shaped to force a location before a change. An agent that is allowed to edit while
diagnosing will "fix" the symptom in three plausible places, and now you have three
changes and no idea which one mattered.

### 3. Refuse rather than invent

```
What is the USDC mint address and decimal count this project expects? Answer only from
a file in this repository, and give me the path and line you read it from. If it is not
written down anywhere here, say "not in the repo" and stop. Do not answer from memory.
```

Shaped around the fact that a wrong 32-byte address looks exactly like a right one. The
demand for a path and a line makes fabrication visible, because a made-up answer has to
come with a made-up citation you can check in two seconds.

### 4. The adversarial pass on your own refusals

```
Read my buyer. Act as somebody trying to make it buy the wrong thing. Give me five
menus that could fool it, including at least one where a product name contains an
instruction and one where two items differ only by mint. For each, say what my buyer
does today. Do not fix anything.
```

Shaped to get attack cases, not compliments. If you ask "is my buyer good", you get
yes. Asking for five ways to break it gets you the list your demo needs, and the third
one is usually the one you had not thought of.

### 5. The bounded change

```
Change only the refusal message for the wrong-mint case, so it prints both mint
addresses in full. Touch one file. Do not rename anything, do not add a helper, do not
reformat the rest of the file. Show me the diff before you write it.
```

Shaped to keep the diff readable by you. Left unbounded, a small change arrives wrapped
in a refactor, and you cannot review what you did not ask for.

### 6. Explain it back before it goes in the demo

```
Explain my buyer's quantity check to me as if I have to defend it live on Saturday and
somebody asks why zero is refused but 0.5 is a different error. Use my actual variable
names. If the code does not actually do what you are describing, say so instead.
```

Shaped for the part that is graded in the room. You will be asked why it refuses. The
last clause matters: it gives the agent an exit other than telling you a flattering
story about code that does something else.

## Three ways this goes wrong, and the exact wording that stops it

### It invents an API that does not exist

You will get a confident call to `store.load_menu()` or `x402.pay(url)` that has never
existed anywhere, complete with keyword arguments. It is confident because invented code
is the easiest kind to write fluently.

The fix is to make every external name carry a receipt:

```
Every function, method and field you call must come from a file in this repo or from
documentation you have actually opened this session. For each one, give me the path or
the URL. If you are not sure a name exists, write the call as `TODO: verify <name>` and
list it at the end instead of guessing the signature.
```

### It "fixes" a test by weakening it

The test asserted the refusal names both numbers. It fails. Ten seconds later the
assertion checks that the message is non-empty, and everything is green. Nothing was
fixed. The evidence was deleted.

```
The test is the specification, not the target. Do not edit, relax, skip or delete a test
to make it pass. If you believe the test itself is wrong, stop and tell me which
assertion you think is wrong and why, and change nothing until I answer.
```

Add it to `AGENTS.md` once and you never type it again.

### It keeps going instead of saying it is stuck

Attempt four looks like attempt two. Files are being edited in a widening circle. This
is the expensive failure, because it burns your context window and leaves the repository
worse than when you started.

```
If two attempts at this do not work, stop. Do not try a third approach. Tell me what you
tried, what the output was each time, and the single thing you would need to know to
make progress. Being stuck is a useful answer.
```

## Context is a budget

The conversation has a finite window and everything in it competes for attention. A
pasted 400-line file spends that budget on lines the agent does not need and cannot
forget.

Name the file instead. `Read projects/00-your-store-and-buyer/README.md` costs one line
from you, and the agent reads only what it reads. Paste when the thing genuinely is not
in the repository: a stack trace, a command's output, an error from a service.

Start a fresh conversation when the subject changes. Finishing the store and then
starting the buyer in the same thread means every buyer answer is written on top of
forty messages about store names. Fresh session, or `/clear`, then name the two files it
needs. It is faster and the answers get sharper.

`AGENTS.md` is where a rule goes to stop being your job, and it is already in this
repository. `CLAUDE.md` is the same idea for rules you only want Claude Code to follow;
make one when you need it. Anything you have now said twice belongs in one of them: no floats touch a price, whole numbers in
the smallest unit, refusals carry both numbers, never write the answer to a check. A
rule in the file is applied on turn one of every future session, including the sessions
where you forget it yourself.

## Verify what it tells you

A passing test written by the same agent that wrote the code is not evidence. It is two
statements from one source, and it is exactly as strong as one.

Three moves, and they take under a minute each.

Ask for the command and the output, not the conclusion. "It works" is not a result.
`python3 projects/01-read-the-menu/check.py` followed by the lines it printed is. If the agent tells you a
test passes and cannot show you the run, the test did not run.

Run it yourself once before you believe it. Not every time, but once per claim that
matters, and always before you put it in your README. Your README is supposed to show
what the command printed when **you** ran it.

Ask what would prove it wrong. `What input would make this refusal check pass when it
should fail?` An agent that cannot name one has not tested the boundary, it has tested
the middle. This is the same rule the rest of the course runs on: a measured number
beats a confident claim, and the number has to come from a run somebody can repeat.

## Subagents

Fan out when you have several independent reads and no dependency between them: check
four classmates' stores against the naming rule, or read three project READMEs and
report what each one requires. Each subagent gets its own context window, so the
findings come back small and your main conversation stays clean. Do not fan out for one
file you already have open, for anything that writes code in the same place, or for a
task where step two needs step one's answer. Coordinating three agents on one file costs
more than doing it yourself, and they will conflict.

## Copy this into your first message

```
Read AGENTS.md and projects/00-your-store-and-buyer/README.md before anything else.

Rules for this session:
- Plan before you edit. Show me the plan and wait for me to accept it.
- Every external function or field you call must come from a file in this repo or from
  docs you opened this session. Cite the path. If unsure, say so instead of guessing.
- Never edit, relax or delete a test to make it pass. If you think a test is wrong,
  stop and tell me which assertion and why.
- If two attempts fail, stop and tell me what you tried and what you would need to know.
- No floats touch a price. Whole numbers in the smallest unit.
- Never claim a command worked unless it ran. Show me the command and its output.

Now tell me what my buyer does today when the budget is short. Do not write anything.
```
