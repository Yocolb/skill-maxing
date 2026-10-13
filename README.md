# skill-maxing

**A Claude Code skill that finds new Claude skills, audits them for malware and prompt injection, judges whether they're useful to you, and installs only what passes, with your approval.**

Most people install skills by pasting a `curl` from a random registry. A skill is a set of instructions Claude follows in every future session. A bad one can quietly inject prompts, leak your `.env`, run code, or hijack unrelated work with a description that says "use this EVERY time". skill-maxing makes "level up Claude" safe to do on repeat.

## How it works

```
 /skill-maxing video
        │
        ▼
 ┌─────────────┐   2–3 scout agents in parallel: official repos, curated lists,
 │   SCOUTS    │   open GitHub search. They resolve the real GitHub source and
 └──────┬──────┘   check stars, last push, license. Read-only.
        ▼
 ┌─────────────┐   One auditor agent per candidate, in parallel. Each one:
 │  AUDITORS   │   • clones into a quarantine folder (hooks off, nothing executed)
 └──────┬──────┘   • runs scan.py, a static red-flag scanner
        │          • reads EVERY file: injection, exfil, exec, secrets, hijack,
        │            junk, license
        ▼          → SAFE / SAFE WITH CHANGES / REJECT / UNVERIFIABLE + exact edits
 ┌─────────────┐   One judge agent scores usefulness 1–10 for *your* work, and
 │    JUDGE    │   flags overlap with installed skills and trigger risk.
 └──────┬──────┘
        ▼
 ┌─────────────┐   You get one table and decide. (`auto` pre-approves
 │  APPROVAL   │   SAFE + useful ≥ 7; REJECT is never installed.)
 └──────┬──────┘
        ▼
 ┌─────────────┐   Main agent only: re-checks the commit SHA, copies just that skill
 │   INSTALL   │   folder, applies the auditor's edits, re-scans, and records
 └─────────────┘   provenance in ~/.claude/skills/INSTALLED-FROM.md.
```

Subagents never install anything. Repo contents are treated as untrusted data, and a file that tries to instruct Claude is an automatic REJECT.

## Install

```bash
git clone https://github.com/Yocolb/skill-maxing
cp -r skill-maxing/skills/skill-maxing ~/.claude/skills/
```
Start a new Claude Code session. Needs `git` and Python 3, and `gh` (GitHub CLI) is recommended for repo metadata.

## Use

| Command | What it does |
|---|---|
| `/skill-maxing` | Hunt for skills that fit your current work (inferred from CLAUDE.md and memory) |
| `/skill-maxing video` | Hunt one topic |
| `/skill-maxing owner/repo` | Audit one specific skill |
| `/skill-maxing update` | Re-audit installed skills whose upstream changed. Never auto-pulls. |
| `/skill-maxing sales auto` | Pre-approve installs that are SAFE and score ≥ 7/10 |

## The scanner

`skills/skill-maxing/scripts/scan.py` uses only the Python standard library and only reads files. It never imports, runs or fetches anything. It flags:

- prompt-injection phrases and hidden HTML-comment instructions
- invisible or bidi unicode
- over-broad "EVERY time" descriptions
- network calls and webhook or paste hosts
- `eval`/`exec`/`subprocess` and `curl | sh`
- runtime installs and pre/post-install hooks
- secret and credential paths
- base64 and obfuscated blobs
- binaries and symlinks
- affiliate and UTM junk

```bash
python -I skills/skill-maxing/scripts/scan.py path/to/skill [--json]
```
The scan is evidence, not a verdict. The auditor agent still reads every file.

## Limits

This is a careful review, not a guarantee. Static scanning and LLM review can miss well-hidden attacks, so prefer skills from known maintainers and keep the approval gate on.

## License

MIT
