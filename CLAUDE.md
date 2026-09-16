# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Hackathon submission repo for Mini Hackathon AI — Batch 04 · Lớp 3A (VinUni AI20k), team "Kẻ Độc Hành", room E403. Track D1: a voice-based simulated classroom where an AI "peer" persona states a plausible misconception about a concept, the learner interrupts by voice to correct it, and the AI checks the correction against a grounded source transcript before confirming or probing further. Design principle: Socratic, non-spoon-feeding — the AI never gives the answer, only reacts to what the learner says.

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

**Pipeline**: browser mic (`codebase/frontend/js/app.js`) → WebSocket `/ws/session` (`codebase/backend/app/main.py`) → STT (`app/voice/stt.py`) → LLM decision (`app/agents/peer.py`) → TTS (`app/voice/tts.py`) → audio back to the browser. STT/TTS sit behind abstract interfaces (`SpeechToText`, `TextToSpeech`) with `Mock*` implementations wired in by default — swap in a real provider by implementing the interface, not by changing call sites in `main.py`.

**Turn-taking state machine** (`PeerAgentSession` / `TurnState` in `app/agents/peer.py`) is a load-bearing design constraint, not an implementation detail: the interrupt threshold must differ by state — short (~300ms) while the AI is speaking a misconception (`AI_SPEAKING`, so the learner can barge in easily), long (multi-second silence tolerance) right after the AI asks a Socratic follow-up (`CONFIRMING`), because silence there means the learner is thinking, not that the turn ended. Collapsing this into one global VAD/endpointing timeout was flagged as the top interruption-handling risk during design research — don't do that.

**Grounding is structural, not prompted**: every `PeerAgentSession` carries a `source_span` (a transcript segment code like `[T06-131]`), and `check_correction()` must resolve to `"dung_du" | "dung_thieu" | "sai"` by comparing the learner's correction against that span — never let the model answer from its own general knowledge instead of the cited source. `app/prompts/peer_persona.py` documents the current worked example (encoder/decoder and the Q-K-V "thư viện sách" analogy, from `brief/data/vlearn-pack/transcript/transcript-06-clean.md`).

**MVP simplification, intentional**: the frontend uses an explicit "🖐️ Giơ tay" button as the interrupt trigger instead of automatic voice-activity detection. This is a reliability choice for a ~40h build, not a placeholder to rip out first — automatic barge-in detection is a stretch goal.

**Repo layout beyond `codebase/`** follows the hackathon's required submission structure, not a normal app convention (see `README.md` "Cấu trúc repo" for the full grading rubric): `spec.md` is the graded AI-spec document (template in place, sections empty), `eval/golden-set/` + `eval/results/` hold test cases and run logs against a quality bar that locks at CP4 and can't change afterward, `validation/` holds outside-user testing logs (optional, but skipping it caps the max score at 92/100), `reflection/` holds one file per member (see `reflection/TEMPLATE.md`).
