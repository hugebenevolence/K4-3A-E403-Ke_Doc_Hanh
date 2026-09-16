# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Hackathon submission repo for Mini Hackathon AI — Batch 04 · Lớp 3A (VinUni AI20k), team "Kẻ Độc Hành", room E403. Track D3: "learning by teaching" — the learner teaches a concept back to an AI "student" persona; the AI asks Socratic follow-up questions exactly where the explanation is thin, vague, or wrong (checked against a grounded source transcript), and only marks the session "taught" once the explanation is good enough. Design principle: Socratic, non-spoon-feeding — the AI is a controlled-naive learner, it never states the correct answer itself, only reacts to what the learner says.

Full rubric/checkpoint rules and reference material (challenge brief, guide, tracks, and the protected VLearn data pack) live in `brief/` — **gitignored, never commit it**. Read `brief/01-challenge-brief.md`, `brief/02-guide.md`, and `brief/data/vlearn-pack/` before designing prompts or eval cases; cite data only by segment code (`[Txx-NNN]`, `turn_id`), never paste long excerpts into tracked files (`eval/`, `spec.md`) — see `brief/README-goc-btc.md` section "Bảo mật dữ liệu".

## Commands

```bash
# backend — runs end-to-end on mocks, no API keys, no credit spent
cd codebase/backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows
cp .env.example .env              # USE_MOCKS=true by default
.venv/Scripts/python -m pytest tests/ -q
.venv/Scripts/uvicorn app.main:app --reload --port 8000

# frontend — no build step, but must be served (getUserMedia needs localhost)
python -m http.server 5500 --directory codebase/frontend
```

Console output is Vietnamese; on Windows set `PYTHONIOENCODING=utf-8` or `print` crashes on cp1252.

## Architecture

**Ports & adapters** (`app/domain` → `app/ports` → `app/adapters`, composition root in `app/main.py`): `domain/` imports no SDK and is fully testable without keys; swapping a provider means writing one file in `adapters/` and wiring it in `main.py`, never touching call sites. All four ports ship `Mock*` adapters and `USE_MOCKS=true` is the default, so the repo runs end-to-end on a fresh clone.

**Workflow, not a ReAct loop** (`app/graph/build.py`): the teach-back flow has stable structure (grade → branch → follow-up or close), so it's a LangGraph state graph with fixed nodes and conditional edges. Adding tools later means adding nodes — do not convert this into an autonomous agent loop. `compile()` takes both a checkpointer (in-session memory) and a store (cross-session student profile); passing only one is the classic LangGraph mistake.

**Talker runs parallel to the reasoner, and lives outside the graph** (`app/api/session.py`): a cheap-tier model speaks one sentence paraphrasing the learner within ~400ms while the grading model takes 1–2s. The talker is **forbidden from signalling right/wrong** — nothing is graded yet when it speaks; that rule lives in `prompts/talker/v1.md` and needs its own eval case. Putting the talker inside the graph would force the graph to wait for it, defeating the point.

**Turn-taking state machine** (`TurnState` in `app/domain/session.py`) is load-bearing: the learner is the primary speaker, so silence tolerance differs by state — normal mid-explanation (`STUDENT_TEACHING`), but multi-second right after a Socratic follow-up (`STUDENT_RESPONDING`), because silence there means the learner is thinking, not that the turn ended. Never collapse this into one global VAD timeout. The frontend additionally gates mic-open on the agent's audio finishing playback, or the mic captures the agent's own voice through the speaker.

**Grounding is structural, not prompted**: every turn resolves against `source_span_ids`, and grading returns `"day_duoc" | "ho" | "sai"` by comparing the learner's explanation to those spans — never the model's general knowledge. `"day_duoc"` ends the session; otherwise exactly one follow-up at the specific gap, never a spoon-fed correction, and never even when the learner asks for the answer outright. After `MAX_FOLLOWUPS` (3) the session closes by pointing at spans to review — never by revealing the answer. Two reinforcements: `domain/verbatim.py` catches near-verbatim recitation deterministically (string match, not an LLM call) and downgrades it to `"ho"`; and `prompts/schemas.py` orders `verdict` last so structured output must enumerate evidence before committing to a verdict.

**Prompts are versioned `.md` files** under `app/prompts/<name>/<version>.md`, loaded by `registry.py`. The constant part (instructions + source spans) goes in `system` and the variable part (learner's words) in `user` — OpenAI prompt caching only matches on shared prefix, so reversing this silently loses the 90% discount. Budget for the whole project is **$5 of credit**; see the tier table in `codebase/README.md`.

**MVP simplifications, intentional**: the frontend uses an explicit "done explaining" button (`#done-btn`) instead of automatic VAD endpointing, and `_transcribe()` in `main.py` buffers a whole turn before running STT. Both are reliability choices for a ~40h build; the STT port already has the streaming shape so wiring real partials changes one function.

**Repo layout beyond `codebase/`** follows the hackathon's required submission structure, not a normal app convention (see `README.md` "Cấu trúc repo" for the full grading rubric): `spec.md` is the graded AI-spec document (template in place, sections empty), `eval/golden-set/` + `eval/results/` hold test cases and run logs against a quality bar that locks at CP4 and can't change afterward, `validation/` holds outside-user testing logs (optional, but skipping it caps the max score at 92/100), `reflection/` holds one file per member (see `reflection/TEMPLATE.md`).
