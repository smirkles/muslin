# Iris Tailor

**The expert sewing friend you don't have.**

Every fitted sewing project starts with a muslin — a test garment in cheap fabric, sewn to check the fit before cutting into good material. Then comes the moment a beginner gives up and an intermediate googles for an hour: standing in front of a mirror, trying to figure out why it pulls there, gapes here, bunches at the back. An experienced friend would just glance over and say "you need a swayback adjustment."

Iris Tailor is that friend. Upload your pattern, your measurements, and a photo of yourself in the muslin. Claude Opus 4.7 — orchestrated as specialist agents via Managed Agents — diagnoses fit issues from the photo, cascades corrections through the pattern, and animates each change so you learn pattern-making while the work happens.

Built solo for Anthropic's "Built with Opus 4.7" hackathon, April 2026.

## Status

🚧 **In development.** Hackathon deadline: April 27, 2026.

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) for Python
- [pnpm](https://pnpm.io/) for Node
- SMPL model files (register at [smpl.is.tue.mpg.de](https://smpl.is.tue.mpg.de/), place in `assets/smpl_models/`)

### Install

```bash
# Backend
cd backend
uv sync

# Frontend
cd ../frontend
pnpm install
```

### Environment

```bash
cp .env.example .env.local
# Edit .env.local and add your API keys
```

### Run

```bash
# Backend (in one terminal)
cd backend && uv run uvicorn main:app --reload

# Frontend (in another)
cd frontend && pnpm dev
```

Open [http://localhost:3000](http://localhost:3000).

## Architecture

See `docs/v2-plan.md` for the full plan, week schedule, and architectural decisions.

In short:
- **Claude Opus 4.7** via Managed Agents does the reasoning (fit diagnosis, cascade orchestration).
- **Deterministic Python** handles the geometry (SVG pattern manipulation, grading, SMPL body generation).
- **Next.js + React + Three.js** is the frontend.
- **GSAP** animates the cascade.

The brain-hands split: Claude reasons about *what should happen*, deterministic code executes *how*.

## Development

See `CLAUDE.md` for the development workflow. In short:

1. Features start as specs in `docs/specs/`
2. `/implement` runs a TDD subagent that writes failing tests, then implementation
3. `/review` runs a fresh-context reviewer
4. All prompts are versioned files in `prompts/`
5. Prompts have evals in `evals/`

## License

MIT — see `LICENSE`.

## Credits

Built by [Steph](https://digitalsmiles.io) (Digital Smiles) for Anthropic's hackathon.
