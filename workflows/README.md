# Surveying several APIs at once

Your agent has a goal and four candidate APIs. Checking them one at a time is four
waits. Nothing about candidate two depends on candidate one, so nothing should wait.

`survey.py` grades every candidate in parallel, then a single verify stage reads what
each lane produced and refuses the ones that are not ready.

## Run it

```bash
python3 workflows/survey.py
```

No key, no account, and with the two bundled specs, no network. It needs Python 3.11
and Node. The gecko CLI comes from `npx` and installs nothing permanent.

Real output, from this repository:

```
fan-out: 2 candidate(s), all at once

verify:

  candidate                          grade   blocking  calls    verdict
  receipts.json                      A 99    0         6/6      ready
  quotes.json                        A 91    2         3/3      not ready

  quotes.json is not ready:
    - blocking: GET /quote: no operationId
    - blocking: POST /quote/{id}/accept: no operationId

  artifacts in ./workflows/out
  1 of 2 candidate(s) refused
```

Exit code 1. Put it in a script and it stops the script.

Your own candidates, local files or URLs, mixed freely:

```bash
python3 workflows/survey.py workflows/specs/receipts.json https://petstore3.swagger.io/api/v3/openapi.json
```

## Read the refusal, because it is the point

`quotes.json` scored 91 out of 100 and got an A, and it is still refused. The letter
averages four dimensions, and averaging is how a blocking problem disappears. Neither
of its operations has an `operationId`, so the agent has to pick between tools named
`get__quote` and `post__quote__id__accept`. It will pick wrong, and it will pick wrong
more often the more operations the API has.

Meanwhile all three of its offline call checks pass, so `gecko test` alone would have
waved it through. Two different questions: can the call be built correctly, and can the
agent find the call to build. The verify stage asks both.

`gecko inspect` exits non-zero whenever there is a blocking finding, with or without
`--min-grade`. That is why the script reads the JSON report instead of the exit code
alone: the exit code says something is wrong, the report says what.

## What the script is doing

Two stages, and they are visible in the file.

**Fan-out.** One `Lane` per candidate. `ThreadPoolExecutor` starts all of them together.
Each lane runs `gecko inspect -o <report>.json` and `gecko test`, and writes its own
artifacts under `workflows/out/`. Lanes never read each other.

**Verify.** After every lane has finished, one pass reads the reports and applies one
rule: ready means no blocking findings and every offline call check passed. Anything
else prints why and the process exits 1.

Each artifact name carries an eight-character hash of the candidate's reference. That
is not decoration. The first version truncated long paths to a fixed length, two
absolute paths sharing a prefix produced the same filename, and one lane reported the
other lane's grade. The run looked fine and the numbers were wrong.

## Knobs

| Variable | Default | What it does |
|---|---|---|
| `GECKO` | `npx -y @geckovision/gecko` | set to `gecko` to use an installed copy |
| `SURVEY_TIMEOUT` | `300` | seconds per lane |
| `--out DIR` | `workflows/out` | where artifacts land |

`workflows/out/` is gitignored. The artifacts are evidence for one run, not something
to commit.

## Fanning out over agents, which this script does not do

The script fans out over processes. Fanning out over *agents* is a different thing and
this repository cannot run it standalone: it needs a client that can dispatch subagents,
such as Claude Code. So here is the pattern and the exact ask, described as a pattern
rather than dressed up as a script.

Three agents live in `.claude/agents/`. Two of them do independent work and can run at
the same time. The third reviews what they produced and has to run after.

Ask for it in one message, naming the parallelism, because an agent told to do three
things will do them in order unless you say otherwise:

> Use the spec-recovery agent on https://example.com/docs and the api-integrator agent
> on workflows/specs/receipts.json. Run them in parallel, they do not depend on each
> other. When both are done, run the call-reviewer agent over everything they produced
> and give me its findings without fixing anything.

The shape is the same as the script: independent work in parallel, then one stage that
judges the output. The difference is that `call-reviewer` has no `Write` and no `Edit`,
so it cannot quietly repair what it found. That is deliberate. A reviewer that can fix
will fix, and then nobody learns what was wrong.

## The specs in `specs/`

Two small APIs that exist only on disk. Both name
`https://api.example.invalid` as their server, and `.invalid` is a reserved top-level
domain, so nothing reaches a real host even if somebody adds `--mode live` by accident.

- `receipts.json` is written the way a spec should be: operation ids, declared enums,
  required markers, a path parameter, a `date-time` field.
- `quotes.json` is written the way most real specs are.

Replace them with the API you actually care about.
