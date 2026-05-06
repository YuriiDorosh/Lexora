# Lexora Academy

**Powered by [Avantgarde Systems](https://avantgarde.systems)**

> A full-stack language learning ecosystem for English, Ukrainian, Greek, and Polish — built on
> Odoo 18 Community with spaced repetition science, AI-powered vocabulary intelligence,
> real-time PvP duels, and a Chrome Extension that turns the entire web into a classroom.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Odoo](https://img.shields.io/badge/Odoo-18_Community-875A7B?logo=odoo&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3-FF6600?logo=rabbitmq&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-Proprietary-red)

---

## Table of Contents

1. [Concept](#1-concept)
2. [Feature Catalogue](#2-feature-catalogue)
3. [The Browser Ecosystem (M22–M28)](#3-the-browser-ecosystem-m22m28)
4. [Backend Architecture](#4-backend-architecture)
5. [Async Microservices](#5-async-microservices)
6. [Spaced Repetition (SM-2)](#6-spaced-repetition-sm-2)
7. [PvP Word Duels](#7-pvp-word-duels)
8. [Knowledge Library](#8-knowledge-library)
9. [AI Roleplay Scenarios](#9-ai-roleplay-scenarios)
10. [Deployment Guide](#10-deployment-guide)
11. [Development Setup](#11-development-setup)
12. [Module Install Order](#12-module-install-order)
13. [Environment Variables](#13-environment-variables)
14. [Implementation Status](#14-implementation-status)
15. [Roadmap](#15-roadmap)
16. [License](#16-license)

---

## 1. Concept

Language acquisition research shows that vocabulary sticks when learners encounter
words in authentic contexts — not flashcard drills in isolation. Lexora is built around
this principle:

- **Immersion-first capture**: the Chrome Extension watches every page you visit.
  See an unknown word on YouTube, Netflix, or any website? One click saves it with
  full sentence context, automatic translation, and LLM-generated enrichment.
- **Spaced repetition science**: SM-2 algorithm schedules reviews at the scientifically
  optimal moment — when you're about to forget.
- **Social pressure through competition**: PvP duels with real opponents or a bot put
  your vocabulary under fire and award XP that feeds a visible leaderboard.
- **Ecosystem integration**: the same word you saved from a YouTube subtitle shows up
  in your morning new-tab practice card, your grammar exercises, and as a distractor
  option in an opponent's PvP round.

The entire stack runs on a single low-resource VPS. No cloud GPU, no per-request API
fees, no external databases — just Docker Compose on a CPU-only Linux server.

---

## 2. Feature Catalogue

### Core Learning

| Feature | Details |
|---|---|
| **Vocabulary manager** | Add words, phrases, and sentences in EN/UK/EL; automatic dedup via normalisation pipeline; sharing toggle |
| **Auto-translation** | On every save: async `deep_translator` (Google Translate / MyMemory fallback) for all learning languages |
| **LLM enrichment** | On-demand: Qwen2.5-1.5B Q4_K_M via `llama-cpp-python`; synonyms, antonyms, 3–7 example sentences, explanation — always in the source language |
| **Anki import** | `.apkg` + `.txt` formats; auto field-mapping; Zstd-compressed modern decks; embedded audio extraction; persistent dedup import log |
| **Audio** | Browser mic recording + Microsoft Edge TTS (online, zero-RAM, en/uk/el/pl with `pl-PL-ZofiaNeural`); Whisper `base` STT transcription; all stored in Odoo filestore |
| **Spaced repetition** | SM-2 algorithm; `/my/practice` flashcard portal; due-card counter on portal home |
| **PDF export** | Printable cheat sheets: personal vocabulary, Gold Vocabulary by CEFR level, Grammar sections |

### Community & Social

| Feature | Details |
|---|---|
| **Posts & articles** | Draft → moderator review → publish flow; rich-text body; @mention comments |
| **Public channels** | Language-specific discuss channels (English / Ukrainian / Greek / Polish); visible to all registered users |
| **Private DMs** | 1-to-1 chat initiated from user profile; "Save to My List" inline popup from any message |
| **Copy-to-list** | Select text in any post or chat message → floating popup → creates `language.entry` + auto-queues translation |

### Gamification

| Feature | Details |
|---|---|
| **XP system** | Earned from practice reviews (5/10/15/20 XP by grade), duel wins, grammar practice, sentence builder |
| **Levels** | `level = 1 + floor(sqrt(xp / 50))`, capped at 20; displayed as a badge on the leaderboard |
| **Daily streaks** | Consecutive-day learning streaks; resets on missed day; frozen by Streak Freeze shop item |
| **XP Shop** | Spend XP on: Streak Freeze (50 XP), Profile Frame (100 XP), Double XP Booster (80 XP / 5 reviews) |
| **Leaderboard** | Top-20 by XP, paginated; current-user highlight; language-pair filter |
| **PvP arena** | Real-time async word duels; matchmaking by language pair; Lexora Bot opponent; 10-round battles; XP stake |

### Practice Modes

| Feature | Details |
|---|---|
| **Grammar Pro** | 110 cloze-test exercises (EN A1–B2 + Greek A1–A2); instant green/red feedback; CEFR / category filters |
| **Sentence Builder** | Word-ordering game using grammar dataset sentences; click-to-order tiles; XP reward |
| **AI Roleplay** | 6 scenarios (café, job interview, doctor, hotel, airport, market); LLM native speaker with inline grammar corrections; conversation history persisted |
| **Phrasebook** | 6 tourist kits × ~15 phrases × 3 languages; one-click "Practice in Roleplay" |
| **Idioms Hub** | 100+ phrasal verbs (EN) + idioms (UK/EL); flip-card UI; save-to-vocabulary button |

### Library & Tools

| Feature | Details |
|---|---|
| **AI Translator** | Google-Translate-style `/translator` page; en↔uk↔el; "Add to Vocabulary" CTA |
| **Gold Vocabulary** | 3,184 most common English words with CEFR level, POS, UK + EL translations; tabbed by level |
| **Grammar Encyclopedia** | 6 sections: 12 tenses, 200 irregular verbs, articles, conditionals, modals, passive/reported speech |

---

## 3. The Browser Ecosystem (M22–M28)

The Chrome Extension is the centrepiece of the immersion strategy. It turns every
browser tab into a capture and practice surface.

### M22 — Companion Extension Scaffold

A Manifest V3 Chrome Extension with a glassmorphism popup that lets users save
vocabulary without leaving the current tab.

- **Glassmorphism popup**: type a word, select language (EN/UK/EL), optionally add
  context and a translation, click Add — the entry lands in Lexora with translation
  auto-queued.
- **Options page**: configure the Lexora server URL (default `http://localhost:5433`).
- **Session bridge**: the popup reads the Odoo session cookie via `chrome.cookies.get`
  and forwards it as `X-Lexora-Session-Id` so the Odoo API controller recognises the
  user without a CORS/SameSite issue.
- **Odoo API endpoint** `POST /lexora_api/add_word`: `auth='none'` with manual session
  resolution; returns `{"status":"ok","entry_id":N}` or `{"status":"duplicate"}`.

### M23 — Contextual Capture

Right-click any selected text on any page → **"Add to Lexora"** context menu item.

- The background service worker captures the surrounding sentence by walking the DOM
  text node containing the selection and splitting on `.!?` boundaries.
- The word and context are posted to `/lexora_api/add_word` directly from the
  background script (no CORS restrictions for background fetch).
- A **glassmorphism toast notification** slides in from the bottom-right with a
  shrinking progress bar confirming the save (✓), duplicate (=), or error (!).
- Opening the popup immediately after shows the word pre-filled from the context-menu
  capture via `chrome.storage.session`.

### M24 — YouTube Subtitle Integration

Every word in a YouTube subtitle track becomes clickable.

**How it works:**

1. A `MutationObserver` watches `.ytp-caption-window-container` for subtitle DOM changes.
2. On each new subtitle line, each word is wrapped in a `<span class="lx-word">` element.
3. Clicking a word pauses the video and opens a **glassmorphism definition overlay**
   positioned adjacent to the clicked word.
4. The overlay fetches `GET /lexora_api/define?word=X&lang=Y`:
   - First checks the user's own saved translations.
   - If none found: calls the Translation Service's `/translate` endpoint synchronously
     (live translation, not persisted — user controls persistence via "Add").
   - Returns definition + live badge if translation was on-the-fly.
5. **"Add to Vocabulary"** in the overlay saves with `source_url` set to
   `<youtube_url>#t=<timestamp>` so the entry links back to the exact moment.
6. **Retry button**: if the definition lookup times out (5 s), a retry button
   re-runs the full lookup cycle.

Additionally, a **Quick Look overlay** (Shadow DOM, fully isolated CSS) activates on
any text selection ≥ 2 characters across all pages. A floating "L" icon appears at the
right edge of the selection; clicking it opens the same definition overlay with
language auto-detection via Unicode block ranges (Cyrillic → uk, Greek → el, Polish-diacritics `[ąćęłńóśźż]` → pl, else en).

### M25 — Premium New Tab Dashboard

Replacing the browser's default new tab with a Lexora vocabulary card.

- **Animated dark gradient background** with two floating orbs (same design language
  as the Lexora portal hero).
- **Live clock** (hours:minutes, updates every second).
- **Personalised greeting**: fetches the user's name from `/lexora_api/whoami`; "Good
  morning / afternoon / evening, {first name}".
- **Daily vocabulary card**: random entry from the user's own vocabulary with at least
  one completed translation (Priority 1), falling back to a random idiom (Priority 2),
  or an empty state prompting the user to add words.
- The card shows: source word, source language flag, all completed translations with
  flags, and a "Practice →" CTA linking to `/my/practice`.
- **Refresh button**: fetches a different card without reloading the tab.
- **Disable override**: a toggle in the extension options restores Chrome's native new
  tab page without uninstalling the extension.
- **Authentication-aware**: if the user is logged out, the card shows "Sign in to
  Lexora" and links to the portal.

### M27 — Review in the Wild

Every webpage becomes a passive vocabulary review surface.

- **Automatic highlighting**: the content script runs a single-pass `TreeWalker` over
  every text node via `requestIdleCallback`. Words that exist in the user's vocabulary
  receive a coloured dotted underline (`border-bottom: 2px dotted`) colour-keyed by SRS
  state: **indigo** = due for review, **green** = in learning, **amber** = new.
- **SRS-aware tooltip**: hovering a highlighted word shows a glassmorphism card with
  the word, SRS age ("Reviewed 3 days ago"), and — simultaneously — the Ukrainian 🇺🇦,
  Greek 🇬🇷, and Polish 🇵🇱 translations rendered side by side.
- **Multi-language support**: `GET /lexora_api/get_learned_words` returns a
  `translations: {"uk": "...", "el": "..."}` dict. The content script stores
  `data-trans-uk` / `data-trans-el` attributes on each `<span>` so the tooltip renders
  both translations without an extra network call.
- **15-minute local cache**: word list is fetched once and stored in
  `chrome.storage.local` with a `generated_at` timestamp. Cache is automatically
  invalidated when the user adds a new word via the popup or context menu.
- **SPA-safe**: a `MutationObserver` on `document.body` (debounced 500 ms) re-highlights
  after React/Vue/Angular route changes without thrashing the DOM.
- **YouTube safety**: subtitle spans (`lx-yt-word`) are excluded from the walker so
  subtitle highlighting and the M24 Quick Look overlay are never double-applied.

### M28 — AI Grammar Explainer

One click produces a 2-sentence linguistic explanation of any selected phrase, powered
by the local Qwen 1.5B model.

- **"Explain Grammar" button** appears in both the global Quick Look overlay (any
  webpage text selection) and the YouTube subtitle word-click overlay.
- **LLM endpoint**: `POST /explain-grammar` on the LLM service (FastAPI sync);
  `max_tokens=150`, `temperature=0.3`, `repeat_penalty=1.1`. System prompt requests a
  2-sentence linguistics explanation in the same language as the input phrase.
- **Odoo proxy**: `POST /lexora_api/explain_grammar` forwards to the LLM service with a
  60-second timeout (same synchronous pattern as the `/roleplay` proxy).
- **Sentence-length support**: `_QL_MAX_LEN` raised to 1000 characters so full sentences
  can be selected for grammar analysis (not just individual words).
- **Draggable overlays**: both the Quick Look card (Shadow DOM) and the YouTube overlay
  (page DOM) are draggable by their header bars. Viewport-clamped repositioning; the
  YouTube overlay converts from `bottom/transform` to pure `top/left` positioning on
  first drag so delta arithmetic is clean.
- **Scrollable content**: a flex-column sandwich layout (`header → scroll body → footer`)
  with `!important` on all structural flex/overflow properties survives YouTube's
  aggressive stylesheet overrides.
- **Latency UX**: button shows "Explaining…" immediately; overlay stays open so the user
  can read translations while the model generates (~10–40 s on E5-2680v2 CPU).

---

## 4. Backend Architecture

```
                        ┌─────────────────────────────────────┐
                        │           Browser / Client           │
                        │  (Chrome Extension + Portal UI)      │
                        └────────────┬────────────────────────┘
                                     │ HTTP / WebSocket
                        ┌────────────▼────────────────────────┐
                        │          Nginx (reverse proxy)       │
                        │   SSL termination · WebSocket proxy  │
                        └────────────┬────────────────────────┘
                                     │
                        ┌────────────▼────────────────────────┐
                        │        Odoo 18 Community             │
                        │  website · portal · mail · auth      │
                        │  Custom modules: language_* (×11)    │
                        │  Odoo bus (WebSocket / long-poll)    │
                        └─┬──────┬──────┬──────────┬──────────┘
                          │      │      │          │
              RabbitMQ    │  Reads/     │     Redis PvP
              publish     │  writes     │     ephemeral state
                          │      │      │
              ┌───────────▼──┐   │  ┌───▼────┐  ┌─▼────────┐
              │  RabbitMQ    │   │  │Postgres│  │  Redis   │
              │  (event bus) │   │  │  (DB)  │  │   (PvP)  │
              └──┬──┬──┬──┬──┘   │  └────────┘  └──────────┘
                 │  │  │  │      │
       ┌─────────┘  │  │  └──────────────────────────┐
       │            │  │                              │
┌──────▼──────┐ ┌───▼───▼────┐ ┌──────────────┐ ┌───▼────────────┐
│ Translation │ │   Anki     │ │  LLM Service │ │  Audio/TTS     │
│  Service    │ │  Import    │ │  (llama.cpp  │ │  Service       │
│ (FastAPI +  │ │  Service   │ │  Qwen2.5-1.5B│ │  edge-tts +    │
│deep_trans.) │ │ (FastAPI)  │ │  enrichment) │ │  Whisper STT)  │
└─────────────┘ └────────────┘ └──────────────┘ └────────────────┘
```

**Key design decisions:**

- **Odoo is the single system of record.** All business data — users, vocabulary,
  translations, enrichments, audio metadata, PvP results, leaderboard — lives in
  Postgres via Odoo ORM. External services are stateless processors.
- **RabbitMQ for async jobs.** Translation, enrichment, Anki import, and TTS generation
  are all async. Each job carries a UUID `job_id` for idempotency. Odoo drains result
  queues via a 1-minute cron (ADR-023).
- **Redis for PvP ephemeral state only.** Matchmaking queues, live round state, and
  reconnect grace timers live in Redis with short TTLs. Odoo persists the final result.
- **CPU-only throughout.** No GPU is assumed anywhere in the stack. The LLM service
  (Qwen2.5-1.5B Q4_K_M via `llama-cpp-python`) runs on AVX-capable x86 CPUs.

---

## 5. Async Microservices

### Translation Service (port 8001)

- **Library:** `deep_translator==1.11.4` (MIT)
- **Primary provider:** `GoogleTranslator` (free, no API key, sub-second latency)
- **Fallback provider:** `MyMemoryTranslator` (auto-engaged on primary error)
- **Languages:** `en`, `uk`, `el`, `pl` — all 12 directional pairs handled directly, no
  two-hop routing (M29: Polish added with `pl-PL` MyMemory locale)
- **Sync endpoint:** `POST /translate` for the AI Translator portal tool
- **Config:** `TRANSLATE_PROVIDER`, `TRANSLATE_FALLBACK_PROVIDER`,
  `TRANSLATE_TIMEOUT_SECONDS` — swap to DeepL or Google Cloud in one env-var change

### LLM Enrichment Service (port 8002)

- **Runtime:** `llama-cpp-python` with `llama.cpp` C++ engine (AVX-only compatible)
- **Model:** `Qwen/Qwen2.5-1.5B-Instruct-GGUF` — `qwen2.5-1.5b-instruct-q4_k_m.gguf`
  (~0.95 GiB on disk, ~1.2 GiB resident)
- **Model delivery:** downloaded on first start via `huggingface_hub` into a Docker
  named volume `llm_models`; subsequent restarts load from disk in ~1 s
- **Enrichment scope:** always in the entry's **source language** — no translation,
  no cross-lingual output (ADR-028)
- **JSON enforcement:** `response_format={"type":"json_object"}` + parse fallback to
  stub to prevent queue wedging
- **Sync endpoints:** `POST /roleplay` for AI Roleplay; `POST /explain-grammar` for the
  Grammar Explainer button in the browser extension (both bypass RabbitMQ; both require
  immediate response)

### Anki Import Service (port 8003)

- **Formats:** `.apkg` (SQLite + zip, Zstd-compressed modern format supported) and
  `.txt` (tab-separated)
- **Auto field mapping:** reads `col.models` JSON to detect Front/Back convention;
  falls back to user-defined mapping
- **Audio extraction:** extracts MP3/OGG/WAV from `.apkg` media bundle; attaches to
  `language.audio` records as `audio_type='imported'`; extraction failures are logged
  but never block text import
- **Dedup:** normalises each card through the same pipeline as manual entry saves;
  reports created/skipped/failed counts back to Odoo

### Audio / TTS Service (port 8004)

- **TTS engine:** `edge-tts` (Microsoft Edge online TTS API — no API key, zero RAM
  overhead, excellent quality for EN/UK/EL)
- **TTS fallback:** `espeak-ng` (system package, offline, lower quality)
- **STT engine:** `faster-whisper` `base` model (~145 MB / ~300 MB resident);
  `int8` quantization on CPU; 2–4× faster than openai-whisper
- **Voice map:** `en → en-US-JennyNeural`, `uk → uk-UA-PolinaNeural`,
  `el → el-GR-AthinaNeural`

---

## 6. Spaced Repetition (SM-2)

Lexora implements the SM-2 algorithm — the same core algorithm behind Anki.

**Review grades:** Again (0) · Hard (1) · Good (2) · Easy (3)

**Interval calculation:**

```
EF  = ease factor (default 2.5, min 1.3, max 3.5)
n   = consecutive correct repetitions
I   = interval in days

Grade 0 (Again): n=0,   I=1,          EF unchanged  → state=learning
Grade 1 (Hard):  n=0,   I=max(1,I×1.2), EF−=0.15
Grade 2 (Good):  n+=1,  I=next_I(n,EF,I), EF unchanged
Grade 3 (Easy):  n+=1,  I=next_I()×1.3, EF+=0.15    → state=review

next_I(1, ef, _) = 1
next_I(2, ef, _) = 4
next_I(n, ef, I) = round(I × ef)
```

**State machine:** `new → learning → review`

Cards for all user entries are auto-created on first visit to `/my/practice`. The
portal shows one flashcard at a time: source text → "Show answer" reveals all
completed translations + an enrichment example sentence snippet. Four grade buttons
submit to `POST /my/practice/review/<card_id>`.

---

## 7. PvP Word Duels

**Entry point:** `/my/arena` — requires ≥10 PvP-eligible entries in the chosen
practice language (configurable system parameter `language.pvp.min_entries`).

**Match flow:**

1. User creates an open challenge (practice language + native language + XP stake).
2. Another user in the same language pair accepts within the matchmaking window —
   or the challenger clicks "Challenge Lexora Bot".
3. **10 rounds** — each round: the system picks one of the current player's
   PvP-eligible vocabulary entries and presents it with 4 translation choices
   (1 correct + 3 distractors pulled from the player's own dictionary).
4. Both players answer independently.
5. After all rounds: the player with more correct answers wins and gains the staked
   XP; loser loses the same amount (floor at 0). Draw: no XP change.

**Lexora Bot:** server-side opponent at ~70% accuracy. Bot battles count in history,
win rate, and XP. Bot user is created automatically and reactivated if archived.

**PvP eligibility:** an entry is PvP-eligible when it has at least one `completed`
translation record.

---

## 8. Knowledge Library

### Gold Vocabulary

3,184 most common English words seeded from the Volka frequency list. Each word has:
- CEFR level (A1–C2)
- Part of speech
- Ukrainian translation (A1/A2 fully translated; B1–C2 seeded with metadata only)
- Greek translation (same coverage)

Portal at `/useful-words` — tabbed by CEFR level, 50 words/page, "Add to My List"
button per word. Printable PDF cheat sheet per level via `/useful-words/print?level=A1`.

### Grammar Encyclopedia

6 sections with full HTML content:

1. **All 12 English Tenses** — form + usage + timeline + Ukrainian/Greek equivalents
2. **Irregular Verbs** — ~200 verbs (Base/Past/Past Participle + Ukrainian translation)
3. **Articles (a/an/the/zero)** — rules with EN/UK/EL examples
4. **Conditionals 0–3** — form + usage + translation pairs
5. **Modal Verbs** — can/could/may/might/must/should/would + equivalents
6. **Passive Voice & Reported Speech** — transformation rules + examples

Portal at `/grammar` — sidebar navigation; printable PDF per section.

---

## 9. AI Roleplay Scenarios

6 conversation scenarios where the LLM acts as a native speaker:

| Scenario | Setting |
|---|---|
| ☕ Café | Ordering food and drinks |
| 💼 Job Interview | Professional English practice |
| 🏥 Doctor's Office | Medical vocabulary and describing symptoms |
| 🏨 Hotel Check-In | Hospitality and travel phrases |
| ✈️ Airport | Check-in, customs, directions |
| 🛒 Market / Shop | Haggling, prices, product descriptions |

Each scenario:
- Has a purpose-built system prompt (plain prose under 100 words — critical for
  reliable output from a 1.5B model; numbered lists cause the model to echo the
  list format)
- Persists conversation history in Postgres (`language.scenario.session.chat_history`
  as a JSON string) — context survives page reloads
- Uses `repeat_penalty=1.15` and `max_tokens=200` to prevent looping/hallucination

The LLM call is **synchronous** (direct `requests.post` to `POST /roleplay` on the
LLM service) because conversation turns require an immediate response — RabbitMQ
async would produce an unusable UX.

---

## 10. Deployment Guide

### Hardware Profile

Lexora is explicitly optimised for **low-resource CPU-only VPS** hosting.

**Minimum verified configuration:**

| Component | Spec |
|---|---|
| CPU | Intel Xeon E5-2680 v2 (AVX, no AVX2) · 6 vCPUs @ 2.8 GHz |
| RAM | 8 GiB |
| Storage | 40 GiB SSD (OS + Docker volumes) |
| Network | 100 Mbit/s outbound (required for `deep_translator` + `edge-tts`) |
| GPU | **None required** |

**RAM budget at steady state (M25 stack):**

| Service | Resident RAM |
|---|---|
| Odoo (4 workers) | ~1.5–2.0 GiB |
| PostgreSQL 15 | ~0.5–1.0 GiB |
| RabbitMQ (Erlang VM) | ~0.3 GiB |
| Redis 7 | ~0.05 GiB |
| Translation Service | ~0.1 GiB |
| LLM Service (Qwen2.5-1.5B Q4_K_M) | ~1.2 GiB |
| Anki Service | ~0.1 GiB |
| Audio Service | ~0.4 GiB (Whisper base loaded) |
| Nginx | ~0.05 GiB |
| **Total** | **~4.2–5.2 GiB** |

Headroom of ~2.5–3.5 GiB on an 8 GiB host is sufficient for the M25 stack under
normal portal traffic (< 10 concurrent users).

**Why M26 (AI Helpdesk RAG) was postponed:**
The `ai_mentor` service adds ~1.5–2.0 GiB on top of the above (fastembed ONNX
~100 MB + Qwen2.5-1.5B GGUF second instance ~1.2 GiB + pgvector Postgres extension).
Under peak portal traffic this pushes the host into swap, causing OOM kills on Odoo
workers. The feature is architecturally complete (see the `m26_ai_helpdesk` git
branch) and will be re-enabled when the server is upgraded to ≥16 GiB RAM.

### Production Checklist

- [ ] Set `workers = 4` in `src/configs/odoo.conf` (already set)
- [ ] Configure Nginx SSL (Let's Encrypt or pre-provisioned cert)
- [ ] Replace `.env` defaults with production secrets
- [ ] Set `POSTGRES_MAX_CONNECTIONS=500` (already set)
- [ ] Enable Redis AOF persistence for PvP state durability across restarts
- [ ] Configure RabbitMQ durable queues (already set via `durable=True` in publishers)
- [ ] Set `TRANSLATE_PROVIDER=google` (or switch to a paid provider)
- [ ] Set `TTS_ENGINE=edge-tts` (requires outbound HTTPS to Microsoft)
- [ ] Verify `LLM_AUTO_DOWNLOAD=1` (first start downloads ~0.95 GiB model)

---

## 11. Development Setup

### Prerequisites

- Docker Engine ≥ 24 and Docker Compose V2
- GNU Make
- 8 GiB RAM recommended (4 GiB minimum with LLM service disabled)
- Outbound HTTPS (required for `deep_translator` + `edge-tts` + HuggingFace downloads)

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/YuriiDorosh/Lexora.git
cd Lexora

# 2. Create the shared Docker network (required once)
docker network create backend

# 3. Copy and edit environment variables
cp env.example .env
# Edit .env — at minimum set POSTGRES_PASSWORD

# 4. Start the full development stack
make up-dev
# Services start in order: postgres → rabbitmq → redis → odoo+nginx → translation → llm → anki → audio
# LLM service downloads ~0.95 GiB model on first start (allow 2–5 min)

# 5. Wait for Odoo to be ready
curl http://localhost:5433/web/health
# → {"status": "pass"}

# 6. Create the Odoo database (first time only)
# Open http://localhost:5433 in your browser → complete the setup wizard
# Database name: lexora

# 7. Install all custom modules
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora \
  --init language_security,language_core,language_words,language_translation,\
language_enrichment,language_audio,language_anki_jobs,language_chat,\
language_dashboard,language_pvp,language_portal,language_learning,\
base_search_fuzzy,web_notify,password_security,\
website_menu_by_user_status,website_require_login \
  --stop-after-init

# 8. Restart Odoo to load all modules
docker restart odoo

# 9. Verify service health
curl http://localhost:8001/health   # Translation → {"provider":"google","ready":true}
curl http://localhost:8002/health   # LLM → {"llm_ready":true,"consumer_alive":true}
curl http://localhost:8003/health   # Anki → {"status":"ok","consumer_alive":true}
curl http://localhost:8004/health   # Audio → {"whisper_ready":true,"consumer_alive":true}
curl http://localhost:15672         # RabbitMQ management UI (guest/guest)
docker exec redis redis-cli ping    # → PONG
```

### Useful Make Targets

```bash
make up-dev          # Start full stack
make down-dev        # Stop full stack
make ps-dev          # Show running containers
make logs-dev        # Tail last 50 lines from every service
make logs-odoo       # Odoo logs only
make logs-llm        # LLM service logs (model loading progress)

make up-llm-no-cache         # Rebuild LLM service image
make up-translation-no-cache # Rebuild translation service image
make up-audio-no-cache       # Rebuild audio service image

make load-backup FILE=your_backup.dump  # Restore Postgres from pg_dump
```

---

## 12. Module Install Order

Custom Odoo modules must be installed in dependency order:

```
language_security
    └── language_core
            ├── language_words
            │       ├── language_translation
            │       ├── language_enrichment
            │       ├── language_audio
            │       └── language_anki_jobs
            ├── language_chat
            ├── language_dashboard
            ├── language_pvp
            ├── language_learning   ← SRS, XP, leaderboard, gamification, shop
            └── language_portal     ← all portal views, translator, roleplay, grammar, library
```

OCA addons (present in `src/addons/`, must be explicitly installed):
- `base_search_fuzzy` — fuzzy vocabulary search via `pg_trgm`
- `web_notify` — browser push notifications
- `password_security` — password strength enforcement
- `website_require_login` — redirect unauthenticated visitors
- `website_menu_by_user_status` — show/hide nav items by auth state

---

## 13. Environment Variables

Key variables in `.env` (see `env.example` for the full list):

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_DB` | `lexora` | Odoo database name |
| `POSTGRES_USER` | `odoo` | DB user |
| `POSTGRES_PASSWORD` | *(required)* | DB password |
| `RABBITMQ_USER` | `guest` | RabbitMQ user |
| `RABBITMQ_PASS` | `guest` | RabbitMQ password |
| `TRANSLATE_PROVIDER` | `google` | `google` or `mymemory` |
| `TRANSLATE_TIMEOUT_SECONDS` | `10` | Per-request timeout |
| `TRANSLATE_FALLBACK_PROVIDER` | `mymemory` | Auto-engaged on primary error |
| `LLM_MODEL_REPO` | `Qwen/Qwen2.5-1.5B-Instruct-GGUF` | HuggingFace model repo |
| `LLM_MODEL_FILENAME` | `qwen2.5-1.5b-instruct-q4_k_m.gguf` | GGUF filename |
| `LLM_N_CTX` | `2048` | LLM context window |
| `LLM_AUTO_DOWNLOAD` | `1` | `0` to disable auto-download (air-gapped) |
| `TTS_ENGINE` | `edge-tts` | `edge-tts` or `espeak-ng` |
| `WHISPER_MODEL` | `base` | `base`, `small`, `medium` |
| `AUDIO_TRANSCRIPTION_ENABLED` | `1` | Enable STT transcription |

---

## 14. Implementation Status

| Milestone | Status | Description |
|---|---|---|
| M0 | ✅ Complete | Docker Compose stack, all services boot |
| M1 | ✅ Complete | 11 Odoo modules scaffold, auth groups, auto-assignment |
| M2 | ✅ Complete | Vocabulary CRUD, dedup, language detection, sharing |
| M3 | ✅ Complete | Translation service, RabbitMQ events, portal display |
| M4 | ✅ Complete | LLM enrichment service, portal enrich button |
| M4b | ✅ Complete | Real CPU-only LLM (Qwen2.5-1.5B GGUF via llama-cpp) |
| M4c | ✅ Complete | Translation pivot to deep_translator; LLM restricted to enrichment |
| M5 | ✅ Complete | Anki .apkg + .txt import, Zstd support, audio extraction, import log |
| M6 | ✅ Complete | Audio recording + edge-tts TTS + Whisper STT |
| M7 | ✅ Complete | Posts, articles, comments, @mentions, copy-to-list |
| M8 | ✅ Complete | Public channels, private DMs, save-from-chat |
| M9 | ✅ Complete | SM-2 spaced repetition, /my/practice, SRS backend views |
| M10 | ✅ Complete | PvP duels, Lexora Bot, XP system, personal dashboard |
| M11 | ✅ Complete | XP Shop (Streak Freeze, Profile Frame, Double XP Booster) |
| M12 | ✅ Complete | Gold Vocabulary (3,184 words), Grammar Encyclopedia (6 sections) |
| M13 | ✅ Complete | PDF export suite (vocabulary, gold vocab by CEFR, grammar) |
| M14 | ✅ Complete | Premium dark UI, glassmorphism, Avantgarde Systems branding |
| M15 | ✅ Complete | AI Translator (/translator), sync translation API |
| M16 | ✅ Complete | Proprietary license, professional README |
| M17 | ✅ Complete | AI Roleplay (6 scenarios, LLM native speaker, grammar corrections) |
| M18 | ✅ Complete | Grammar Pro cloze tests (110 exercises, EN + EL, CEFR filters) |
| M18.5 | ✅ Complete | Header dropdown redesign (Practice / Library / Tools) |
| M19 | ✅ Complete | Idioms Hub (100+ phrasal verbs + idioms, flip-card UI) |
| M20 | ✅ Complete | Survival Phrasebook (6 scenarios, 3 languages, copy-to-roleplay) |
| M21 | ✅ Complete | Sentence Builder word-ordering game |
| M22 | ✅ Complete | Chrome Extension scaffold, /lexora_api/* Odoo endpoints |
| M23 | ✅ Complete | Context menu "Add to Lexora", surrounding sentence capture, toast |
| M24 | ✅ Complete | YouTube clickable subtitles, global Quick Look overlay (Shadow DOM) |
| M25 | ✅ Complete | New Tab vocabulary card, live clock, animated dark gradient |
| M26 | ⏸ Postponed | AI Helpdesk RAG — requires ≥16 GiB RAM; preserved on `m26_ai_helpdesk` |
| M27 | ✅ Complete | Known vocabulary highlighted on any webpage; SRS-aware tooltip with simultaneous 🇺🇦/🇬🇷 translations; 15-min local cache; MutationObserver re-scan |
| M28 | ✅ Complete | "Explain Grammar" in Quick Look + YouTube overlays; Qwen 1.5B via Odoo proxy; draggable scrollable overlays |
| M29 | ✅ Complete | Polish (`pl` / 🇵🇱) as a first-class language across DB, services, extension, portal; 1055 entries backfilled; canonical `LANGUAGE_SELECTION` import enforced (ADR-029) |

---

## 15. Roadmap

**M26 — AI Helpdesk (Postponed):** Full automated helpdesk with OdooBot replies
generated by a local pgvector + Qwen2.5-1.5B RAG pipeline. Complete implementation
exists on `m26_ai_helpdesk` branch. Blocked by server RAM constraints (requires ≥16 GiB).

**Potential future milestones:**
- M30: ELO rating system for PvP matchmaking
- M31: Multi-language expansion (Spanish, German — Polish landed in M29)
- M32: Collaborative vocabulary lists / class rooms
- M33: Mobile PWA / React Native companion

---

## 16. License

Copyright © 2026 Yurii Dorosh / Avantgarde Systems. All Rights Reserved.

This software is proprietary and confidential. No part of this codebase may be
reproduced, distributed, or transmitted in any form or by any means without the
prior written permission of the copyright holder.

For licensing inquiries: contact.yuriidorosh@gmail.com
