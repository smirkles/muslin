# Setup Guide

One-time setup steps to go from zero to a working dev environment.

## 1. Prerequisites

Install if you don't have them:

```bash
# uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# pnpm (Node package manager)
npm install -g pnpm

# Claude Code (if not already)
# See https://docs.claude.com for current install instructions
```

Verify:

```bash
uv --version
pnpm --version
claude --version
```

## 2. Initialize Git repo

```bash
cd muslin
git init
git add .
git commit -m "chore: initial project scaffold"
```

## 3. Register for SMPL model

SMPL requires a manual license acceptance — cannot be automated.

1. Go to https://smpl.is.tue.mpg.de/
2. Register with your email (use a real one; they verify)
3. Accept the license terms (free for research and non-commercial use)
4. Download the SMPL model files (pick the Python version)
5. Place the `.pkl` files in `assets/smpl_models/`

For the hackathon, the non-commercial research license is sufficient.

## 4. Backend setup

```bash
cd backend
uv sync  # installs all dependencies from pyproject.toml
uv run pytest  # should run (no tests yet, but should not error)
```

## 5. Frontend setup

**Not yet scaffolded** — will do this as part of Day 2 or first frontend spec. For now:

```bash
cd frontend
# Next.js scaffolding will be added when we start on UI work
```

## 6. Environment variables

```bash
cp .env.example .env.local
```

Edit `.env.local` and add:
- `ANTHROPIC_API_KEY` — from https://console.anthropic.com
- `REPLICATE_API_TOKEN` — from https://replicate.com (free tier works for hackathon)

## 7. Claude Code initialization

```bash
cd muslin
claude
```

When Claude Code starts, it should:
- Detect the `.claude/` directory and load settings
- Register the `/spec`, `/implement`, `/review` slash commands
- Register the implementer, reviewer, spec-writer subagents
- Wire up the post-edit hook

Verify by typing `/` at the Claude Code prompt — you should see the custom commands listed.

## 8. First test run

To sanity-check the workflow:

```bash
# In Claude Code:
/spec "a tiny utility function that reverses a string — just to test the workflow end to end"
```

Steph reviews, approves, then:

```bash
/implement 02-string-reverse-test  # or whatever the spec ID is
```

Watch the implementer write failing tests, then implementation. Then:

```bash
/review 02-string-reverse-test
```

If all three commands worked cleanly, the workflow is live. Delete the test spec and move on.

## 9. Push to GitHub

```bash
# Create repo on GitHub first (public, MIT license)
git remote add origin git@github.com:USERNAME/muslin.git
git branch -M main
git push -u origin main
```

## Next steps

After setup, open `docs/v2-plan.md` and start Day 1.
