# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Hackathon submission repo for Mini Hackathon AI — Batch 04 · Lớp 3A (VinUni AI20k), team "Kẻ Độc Hành", room E403. Track D3: "learning by teaching" — the learner teaches a concept back to an AI "student" persona; the AI asks Socratic follow-up questions exactly where the explanation is thin, vague, or wrong (checked against a grounded source transcript), and only marks the session "taught" once the explanation is good enough. Design principle: Socratic, non-spoon-feeding — the AI is a controlled-naive learner, it never states the correct answer itself, only reacts to what the learner says.

Full rubric/checkpoint rules and reference material (challenge brief, guide, tracks, and the protected VLearn data pack) live in `brief/` — **gitignored, never commit it**. Read `brief/01-challenge-brief.md`, `brief/02-guide.md`, and `brief/data/vlearn-pack/` before designing prompts or eval cases; cite data only by segment code (`[Txx-NNN]`, `turn_id`), never paste long excerpts into tracked files (`eval/`, `spec.md`) — see `brief/README-goc-btc.md` section "Bảo mật dữ liệu".

## Commands

No build/lint/test tooling is set up yet (fresh scaffold). To run what exists:

```bash
# backend
cd codebase/backend
pip install -r requirements.txt   # STT/TTS/LLM SDKs are commented out — uncomment the ones chosen first
cp .env.example .env              # fill in keys for the providers chosen
uvicorn app.main:app --reload --port 8000

# frontend — no build step; open codebase/frontend/index.html directly,
# or serve it (needed for getUserMedia mic access outside localhost):
python -m http.server 5500 --directory codebase/frontend
```

## Architecture

**Pipeline**: browser mic (`codebase/frontend/js/app.js`) → WebSocket `/ws/session` (`codebase/backend/app/main.py`) → STT (`app/voice/stt.py`) → LLM decision (`app/agents/student.py`) → TTS (`app/voice/tts.py`) → audio back to the browser. STT/TTS sit behind abstract interfaces (`SpeechToText`, `TextToSpeech`) with `Mock*` implementations wired in by default — swap in a real provider by implementing the interface, not by changing call sites in `main.py`.

**Turn-taking state machine** (`StudentAgentSession` / `TurnState` in `app/agents/student.py`) is a load-bearing design constraint, not an implementation detail: the learner is the primary speaker (they're teaching), so silence tolerance must differ by state — short-ish while they're mid-explanation (`STUDENT_TEACHING`) is fine to end-of-turn on, but long (multi-second silence tolerance) right after the AI asks a Socratic follow-up (`STUDENT_RESPONDING`), because silence there means the learner is thinking, not that the turn ended. Collapsing this into one global VAD/endpointing timeout was flagged as the top interruption-handling risk during design research (carried over from the D1 exploration) — don't do that.

**Grounding is structural, not prompted**: every `StudentAgentSession` carries a `source_span` (a transcript segment code like `[T06-131]`), and `evaluate_explanation()` must resolve to `"day_duoc" | "ho" | "sai"` by comparing the learner's explanation against that span — never let the model answer from its own general knowledge instead of the cited source. `"day_duoc"` ends the session; `"ho"`/`"sai"` trigger exactly one follow-up question at the specific gap, never a spoon-fed correction, and never even when the learner explicitly asks for the answer. `app/prompts/student_persona.py` documents the current worked example and the hard-test rule that a near-verbatim paste of the source doesn't count as `"day_duoc"` — it must come back in the learner's own words.

**MVP simplification, intentional**: the frontend uses an explicit "done explaining" button (`#done-btn` in `index.html`/`app.js`) as the turn-end trigger instead of automatic voice-activity detection. This is a reliability choice for a ~40h build, not a placeholder to rip out first — automatic endpointing is a stretch goal.

**Repo layout beyond `codebase/`** follows the hackathon's required submission structure, not a normal app convention (see `README.md` "Cấu trúc repo" for the full grading rubric): `spec.md` is the graded AI-spec document (template in place, sections empty), `eval/golden-set/` + `eval/results/` hold test cases and run logs against a quality bar that locks at CP4 and can't change afterward, `validation/` holds outside-user testing logs (optional, but skipping it caps the max score at 92/100), `reflection/` holds one file per member (see `reflection/TEMPLATE.md`).
