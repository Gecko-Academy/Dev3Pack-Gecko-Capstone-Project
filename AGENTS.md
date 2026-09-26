# This repository, for coding assistants

This file tells a coding assistant what this repository is and how to help with it.

## Purpose

A student's own **final project** for the Dev3Pack AI-Engineering bootcamp: a store, the
Gecko MCP, and a buyer. It starts as a clone of a course-provided repository and becomes
the student's own: they push it to their own GitHub account (suggested name
`my-final-project`) and add one project per day of week 3. It is their portfolio piece,
shown at the optional showcase on Saturday 3 October.

Nothing in this repository is scored. This repository has no `bootcamp` command.

- **Weekly challenge 2** (the store and the buyer) is done, checked and submitted from the
  course folder: the session 10 notebook or `demos/10_your_store_and_buyer.ipynb`, then
  `uv run bootcamp submit ch10 --github <handle> --push`. `store.json` travels with that
  submission. Project 00 here describes it; it is not checked here.
- **The capstone** is the certificate: a research assistant, in a different repository
  made by `bootcamp capstone new`, graded privately and defended in session 15.

Do not conflate the three. If a student asks for a score, the answer is the course
folder, not this repository.

Gecko, in the founder's words: how an agent moves money on Solana and proves it landed as
asked. Never describe it as an "API comprehension layer"; that line is retired.

## How to help

- **Explain before you write.** The projects teach something. An assistant that hands
  over a finished answer has removed the exercise. Explain what a step is asking for and
  point at the file.
- **Never write the answer to a check.** Say what the check guards and what its message
  means.
- **Say when you are unsure.** A run that did not happen is not evidence. Do not claim a
  command worked unless it ran.
- **No keys, ever.** Nothing in this repository needs a private key or an API key. If a
  step seems to, that is a bug to report, not to work around. Never create, paste or
  commit one.
- **Credit what is borrowed.** If you bring in code from somewhere, say where in the
  file.

## How to run it

Each project folder has its own README with its own commands. There is no repository-wide
build.

```bash
git pull upstream main                                      # the next day's project
python3 projects/01-read-the-menu/check.py                  # project 01's local self-check
```

`check.py` prints a local score only. It reaches no leaderboard and no grader.
