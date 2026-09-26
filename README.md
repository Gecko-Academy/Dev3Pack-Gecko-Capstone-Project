# Dev3Pack final project

![Python](https://img.shields.io/badge/python-3.11+-blue)
![uv](https://img.shields.io/badge/uv-managed-6e56cf)
![License](https://img.shields.io/badge/license-MIT-blue)
![Claude Code](https://img.shields.io/badge/Claude_Code-ready-orange)

One repository that becomes **yours**. One project a day. One thing you can demo at the end and explain when it breaks.

**Week 3, 28 September to 2 October 2026.** Optional showcase on Saturday 3 October.

This repository is your **final project**: a store, the Gecko MCP, and a buyer. It is your
portfolio piece, and you show it at the showcase if you want to. Nothing in it is scored.

It is **not your capstone**. The capstone is the certificate: a research assistant, in a
different repository that `bootcamp capstone new` makes for you in the course folder. It is
graded privately and you defend it in session 15. Keep the two apart. The GitHub name of
this template still says "Capstone-Project"; that is the template's name, not what it is for.

Weekly challenge 2 (your store and a buyer) is done, checked and submitted from the
**course folder**, not from here. See [project 00](projects/00-your-store-and-buyer/README.md).

## Contents

- [Start here](#start-here)
- [Make it yours](#make-it-yours)
- [Get each day's project](#get-each-days-project)
- [Repository map](#repository-map)
- [What you ship](#what-you-ship)
- [For coding assistants](#for-coding-assistants)
- [Commands](#commands)
- [Safety](#safety)

## Start here

```bash
git clone https://github.com/Gecko-Academy/Dev3Pack-Gecko-Capstone-Project.git my-final-project
cd my-final-project
```

That is the whole setup. There is nothing to install yet: each project says what it
needs, and none of them needs an API key.

**Windows:** run these in **Git Bash** or WSL2, not PowerShell.

If you have SSH keys set up,
`git clone git@github.com:Gecko-Academy/Dev3Pack-Gecko-Capstone-Project.git my-final-project`
works too. HTTPS is above because it needs nothing configured first.

## Make it yours

Five minutes, once. This repository is a starting point, not a place you hand work in.
After these two commands it is your repository: your commits, your name on it, yours to
show anybody.

You need the [GitHub CLI](https://cli.github.com/), signed in with `gh auth login`.

```bash
git remote rename origin upstream                                  # ours: the daily projects
gh repo create my-final-project --private --source=. --remote=origin --push   # yours
```

Use `--public` instead of `--private` if you want it visible now. You can switch either
way later.

**This is not a fork, on purpose.** A fork stays attached to ours: GitHub labels it
"forked from Gecko-Academy" and its stars and issues point back here. Yours is a
repository in its own right that happens to have started from ours. Rename it, make it
private, make it public, delete it. None of that touches this one.

## Get each day's project

We push one project per day of week 3. To pick up the next one:

```bash
git pull upstream main
```

Projects land in `projects/`. Your own work lives wherever you put it and is not
touched. If a pull stops because you changed the same file we did, git names the file
and nothing is lost.

| Day | Session | Project | Status |
|---|---|---|---|
| Monday 28 | 11: state and memory | [01: read the menu, prepare, refuse](projects/01-read-the-menu/README.md) | here |
| Tuesday 29 | 12: MCP architecture | | arrives Tuesday |
| Wednesday 30 | 13: build and secure an MCP server | | arrives Wednesday |
| Thursday 1 | 14: deploy and operate | | arrives Thursday |

## Repository map

| Path | What is in it |
|---|---|
| `projects/` | one folder per day, each with its own README |
| `PRD.md` | the product note for the final project: the problem, the scope, the journey, the success numbers |
| `.claude/` | skills and agents Claude Code loads in this folder, e.g. `gecko-connect-mcp`, `gecko-solana-read` |
| `docs/` | `working-with-claude.md` (prompts and habits) and `adr/` (a template for your decision records) |
| `workflows/` | `survey.py` grades several candidate APIs in parallel and refuses the ones that are not ready; sample specs and recorded output included |
| `AGENTS.md` | what a coding assistant should know about this repository |
| `README.md` | this page |
| `LICENSE` | MIT. Yours is yours; credit what you borrow |

Everything else is yours to add. There is no layout you have to follow.

## What you ship

One thing that runs, and a README that shows it running. By the end somebody should be
able to read this repository without you in the room and know:

- what it does, in a sentence;
- the exact command to run it, and what that command printed when **you** ran it;
- one thing it refuses to do, and why that refusal is the interesting part.

A demo that only works on the happy path is worth less than one with a failure you can
explain. Break it on purpose before somebody else does.

## For coding assistants

`AGENTS.md` tells an assistant what this repository is and how to help with it. Claude
Code reads it by itself when you start it in this folder:

```bash
claude
```

Ask it to explain a project before you ask it to write one. It is faster at reading than
you are, and slower at knowing what you meant.

## Commands

| Command | What it does |
|---|---|
| `git pull upstream main` | fetch the next day's project |
| `git push` | push your own work to your own repository |
| `gh repo view --web` | open your repository in a browser |

## Safety

Same lanes as the course.

| Lane | What it means |
|---|---|
| Offline | recorded responses. No key, no network, no money. This is where you build. |
| Read-only | reading a real catalogue over the network. Still no key, still nothing spent. |
| Fork | a rehearsal on a throwaway copy of mainnet, run by the instructor. Optional. |
| Mainnet | never part of anything required, and never with your own key. |

**Your code holds no keys and signs nothing.** If a step looks like it needs a private
key in this repository, that step is wrong. Ask before working around it. `.gitignore`
already refuses the usual ones, and that is a seatbelt, not a reason to have them here.

Credit what you borrow. Public code is the point; taking a function or a prompt and
saying where it came from makes a reader trust the repository more, not less.
