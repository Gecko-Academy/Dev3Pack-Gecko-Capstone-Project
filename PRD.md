# Capstone: an agent that buys a call it has never made

Week 3, 28 September to 2 October 2026. Showcase Saturday 3 October.

This is the product note for the thing you build on top of project 00. Read it once,
then go and build. It is also a reference project: anybody can clone this repository and
run the same path.

## The problem, on a Tuesday morning

09:40. You have a goal and a docs URL. You tell your agent to get tonight's odds.

The agent reads the docs page, writes a request to `/v2/fixtures/odds`, and gets a 404.
That path was in a code sample under a heading about a deprecated version. It tries
`/api/odds`, `/v2/odds`, `/odds/live`. One of them returns 200 with an empty array,
which looks like "no matches tonight" and is actually the wrong resource. It tries the
real endpoint at last and gets `402 Payment Required`, and stops there, because it has
no idea what paying means.

You unblock it the fast way. You paste your API key into `mcp.json` and re-run. Now the
key is in a file, the file is in a repository, and the model can read it. The call
finally works. Nobody can tell you whether the number it returned is the right number,
because the only evidence is that the request did not error.

Three separate failures in twenty minutes: a call invented rather than derived, a
paywall the agent could not cross, a credential in a place it must never be. The third
one is the expensive one and it is the one nobody notices.

## What Gecko is, in the founder's words

Gecko is how an agent moves money on Solana and proves it landed as asked.

Ask once. Gecko finds the program and the mechanism, builds the call, rehearses its
effect on a fork against the request you pinned, refuses by field when they disagree,
hands unsigned bytes to the signer you already have, reads the ledger, and writes the
one receipt that says what moved.

Execution comes first. The check is the second paragraph, not the headline. Two
comparisons the founder uses, and both are deliberately partial: Visa is every program
and every signer, Waze is the route and the hazard and never the car. Gecko holds no
key and signs nothing.

**Do not describe this project, or Gecko, as an API comprehension layer.** That line is
retired. It describes the engine rather than what anyone is paying for, and it sells a
middle layer between a program and its caller, which is a position that gets absorbed.
Comprehension is a step this project performs. It is not what the project is.

Who this is aimed at, and it is worth knowing while you build: a person at a chat
window, one click, on a surface they already use. Not an operator running
infrastructure. If your demo needs a terminal and a config file to make sense, you have
built the thing for the wrong person.

## Who this is for

A Dev3Pack student in week 3 who has project 00 working: a store, and a buyer that
refuses with both numbers. You have Python 3.11+, `uv`, and a GitHub account.

Also for any developer who wants a small, readable example of an agent choosing an API
at run time instead of being handed one.

Not for: somebody learning Python; somebody who wants a trading bot; an API provider
looking to list a service; anybody who wants an agent that runs unattended with a funded
key. That last one does not exist here and is not being built here.

## The one thing it does

Given a goal and no API named, the agent picks a paid service it has never seen, proves
the call before it counts, pays for it, and returns the data.

The choosing is the part worth demoing. An agent handed one endpoint is plumbing. An
agent that reads a list, picks, and can say why it picked is the project.

## Scope

In:

- one goal, stated in plain language, with no API named in it
- the agent selecting a surface at run time and saying in one line what it matched on
- comprehension of a surface the agent has not seen before, at $0, before any live call
- the buyer from project 00, extended so it checks a prepared transaction field by field
  against what was asked for
- a README showing the exact command and what it printed when you ran it

Out, and stay out:

- a web UI of any kind
- more than one API inside a single run
- writing your own MCP server (session 13 teaches that; do not pre-empt it here)
- your own signer, your own key, your own mainnet transaction
- retry loops that keep trying until something succeeds
- a database, a queue, or a deploy

Later, if the week goes well:

- a second surface in the same run, joined on one field
- `gecko drift` to notice when a working call stops working
- deploying it (session 14)

## The journey

Every step names a command. Steps 1 to 7 need no key, no account, and no money.

1. Get the repository and make it yours.
   `git clone https://github.com/Gecko-Academy/Dev3Pack-Gecko-Capstone-Project.git my-capstone`
   then the two `gh` commands in the root README.
2. Check the environment. `npx @geckovision/gecko doctor` prints the version and the
   exact next step. No install, no key.
3. Let the agent see what already exists. Connect the keyless surface:
   `claude mcp add --transport http gecko https://mcp.geckovision.tech/gecko/mcp`, then
   have the agent call `list_surfaces`. This is the list it chooses from.
4. Give it a goal with no API in it. The agent picks one entry and writes down, in one
   line, which field made it pick. Save that line. It is the pinned intent and
   everything later is checked against it.
5. Comprehend a surface that was not on the list.
   `npx @geckovision/gecko add <spec-or-docs-url>` reads the surface into a graph at $0
   with no live call. Over MCP the same door is `comprehend_api`. If there is no spec,
   `npx @geckovision/gecko from-docs <docs-url>` recovers a draft one.
6. Read the scorecard before trusting it.
   `npx @geckovision/gecko report <spec>` returns a grade and the findings behind it.
   A poor grade is a result. Refusing an API here is a valid ending for step 6 and a
   better demo than most passes.
7. Run it for free. `npx @geckovision/gecko test <spec> --mode recorded` generates
   first-call-correctness checks and runs them against responses synthesised from the
   schema. Keep the output. It is the plan you will compare the live run against.
8. Hand the surface to the agent.
   `npx @geckovision/gecko serve <spec> --stdio`, wired into your client the same way as
   step 3. The agent now asks questions instead of guessing paths. Going live is its own
   deliberate step: `gecko auth set <provider>` puts the key in your OS keychain, never
   in `mcp.json`.
9. For the on-chain leg, connect `https://mcp.geckovision.tech/orquestra/mcp` (keyless,
   16 tools). Browse with `list_stores`. Do all the deciding here, where nothing expires.
10. Prove the call before it counts. `npx @geckovision/gecko prove "<your intent>"`
    routes the intent, shows where every account came from, and simulates it unsigned on
    a fork. Exit 0 means it lands. Exit 1 means it routed and does not pass.
11. Prepare, once, only after the buyer has chosen. `prepare_purchase` returns the bytes
    and an `expires` field. Read that number rather than assuming one. Your buyer now
    checks those bytes against the record from step 4: program, store, product, price in
    the smallest unit, mint address (never the symbol), quantity, destination.
12. Sign those exact bytes with a signer you added yourself. Gecko holds no key and signs
    nothing. On the fork lane, `try_purchase` does the rehearsal with a throwaway key
    that cannot reach mainnet. Mainnet is instructor-run and never uses your key.

## Success criteria

| What | Number | How it is checked |
|---|---|---|
| Time from `git clone` to a first successful call with no key | under 10 minutes | you time it and write the figure in your README next to the command |
| Keys committed to the repository | 0 | `git grep -nE "BEGIN [A-Z ]*PRIVATE KEY\|sk-[A-Za-z0-9]{20}"` returns nothing, and `mcp.json` contains no secret |
| Auth headers visible in the agent-facing tool definitions | 0 | the findings section of `npx @geckovision/gecko report <spec>` |
| Distinct refusals your buyer can produce on demand, each naming both numbers | at least 4 | `uv run bootcamp check ch10`, plus you triggering each one live |
| Difference between the recorded plan and the live plan | 0 fields | run `gecko test <spec> --mode recorded` then `--mode live`; the chosen operation, path and argument names must match |
| Goals where the agent picks a surface that can answer | at least 4 of 5 | write 5 goals before you run any of them, then run them once each and record the picks |
| Transactions signed before a simulation passed | 0 | every signature in your log has a `gecko prove` exit 0 or a `try_purchase` result ahead of it, by timestamp |

A criterion you cannot fail is not a criterion. If every number above comes out perfect
on the first try, your goals were too easy.

## What must be true before money moves

All of these, every time. Not a warning, a checklist.

1. The intent is written down before any bytes exist, and the check compares the
   prepared call to that record field by field.
2. A simulation has passed for this exact call. `gecko prove` exit 0, or a `try_purchase`
   result on a fork.
3. The prepared bytes have been read back and matched: program, store, product, price in
   the smallest unit, mint address compared as an address, quantity, destination.
4. No key exists in this repository. API keys go to the OS keychain via
   `gecko auth set`. Private keys are not part of any required step.
5. The signer is a connector you added, separate from Gecko, and you know its address,
   its balance, and whether it waits for a human tap. If it waits, settle that before
   preparing, not after.
6. You prepare once and sign those exact bytes. You do not prepare several options to
   compare them.
7. The mainnet lane is run by the instructor. Your required path ends on the fork.

## Non-goals and known limits

- The fork rehearsal tool `try_purchase` is account-gated. Browsing, preparing and
  proving are not. If you hit the gate, that is the design, not a bug: ask.
- The paid-HTTP path stays in stub mode for this project. Do not flip it.
- Retrieval on the served surface is lexical. A goal worded in your own words, with none
  of the surface's words in it, can miss. Measured on 2026-09-20 over four golden sets,
  paraphrase recall@8 was 0.04 for the ranker and 0.22 with fallback. Hybrid retrieval
  exists in the engine and is not wired into the served surface. Plan your five goals
  knowing this, and treat a miss as a finding worth showing.
- The independent check that catches a well-formed but wrong address is hand-written per
  program. It does not cover every program in the catalog.
- Nothing here runs unattended. Every step has a human at the keyboard.
- 27 of roughly 31 CLI verbs need no key and no account. The rest do, and `doctor` will
  say so.
- Docs drift. A spec that comprehended cleanly last week can fail this week. That is the
  failure you want on stage.

## Open questions

| Question | Who decides |
|---|---|
| Which paid service the showcase run uses | you, by Monday 28 |
| Whether a mainnet leg runs at the showcase at all, and with whose key | the instructor |
| Whether `try_purchase` accounts are issued per student or the fork lane is run once by the instructor | the instructor |
| Whether the agent may submit a surface through `comprehend_api`, or must be handed a spec URL you chose | you, and write the answer in your README so a reader is not guessing |
| Whether the project 00 buyer is reused as is or rewritten to check a prepared transaction | you |
| The positioning line at the top of this document | the founder |
