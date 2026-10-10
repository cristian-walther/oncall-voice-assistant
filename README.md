# On-call Voice Assistant

A voice agent that briefs an on-call engineer about a production incident. The agent is built in ElevenLabs; its prompt is fixed and uses four dynamic variables (`incident_id`, `service`, `severity`, `incident_briefing`) filled in when each conversation starts.

All data in this repo is mock data. Nothing comes from a real PagerDuty account or from customers.

## How it works

```
data/incident.json ──► src/summarize_incident.py ──► incident_briefing (spoken-style text)
                                                          │
                       incident_id, service, severity ────┤
                                                          ▼
         src/start_conversation.py (local server, holds the API key)
            ├─ GET /api/session ─► ElevenLabs signed URL + the four variables
            └─ GET /            ─► web/index.html (JS SDK: startSession with dynamicVariables)
```

The browser never sees `ELEVENLABS_API_KEY`; it only gets a short-lived signed URL.

## Setup (Windows, Python 3.12)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

| Variable | Purpose |
|---|---|
| `ELEVENLABS_API_KEY` | Used server-side to request a signed URL |
| `ELEVENLABS_AGENT_ID` | Your existing agent |
| `ANTHROPIC_API_KEY` | Optional; live briefing summaries |
| `ANTHROPIC_MODEL` | Defaults to `claude-haiku-5-5` (low-cost, fast) |
| `USE_MOCK_SUMMARY` | `true` uses a predefined briefing, no Anthropic key needed |

## Run

```powershell
python -m src.start_conversation --dry-run   # print the four variables, start nothing
python -m src.start_conversation             # then open http://localhost:8000
python -m pytest                             # tests (APIs are mocked)
```

## Repo layout

- `agent/` - system prompt, first message, runbook, sanitized agent config
- `data/incident.json` - mock PagerDuty-style incident (INC-4821)
- `src/summarize_incident.py` - payload to voice-friendly briefing (Anthropic API, or mock)
- `src/start_conversation.py` - local server that starts the conversation with dynamic variables
- `web/index.html` - minimal demo page
- `tests/` - pytest suite

## Design notes

- **Least privilege.** The API key started with read-only agent scope. `get-signed-url` requires `convai_write`, so only that scope was raised.
- **Draft vs. published.** The dashboard preview uses the agent's draft; API sessions use the published version. Publish after every prompt change before testing from this repo.
- **Capability boundaries in the prompt.** Testing showed the agent claiming it had paged the secondary on-call, although it has no paging tool. Stating explicitly what it cannot do (and telling it to ask the engineer to page) fixed it. A PagerDuty tool with engineer confirmation is the first roadmap item.
- **Dynamic variables instead of per-incident prompts.** Incident data is passed when each conversation starts, so concurrent incidents never overwrite each other's prompt.
- **`end_call` enabled.** The built-in tool lets the agent actually hang up instead of leaving the line open.
- **Latency and consistency.** Low reasoning effort and temperature 0 keep voice latency down and answers consistent. RAG is off because the runbook is short.
- **Key stays server-side.** The signed URL means the API key never reaches the browser. The agent is public for the demo; enabling agent auth is a production step.
- **Graceful degradation.** The summarizer falls back to a predefined briefing if Anthropic is unavailable (or no key / `USE_MOCK_SUMMARY=true`).
- **Thinking disabled for the summary.** Haiku's adaptive thinking could consume the whole output budget and leave no text, which made the summarizer silently fall back to the mock briefing. Thinking is now disabled for this short task, and empty responses log a warning.

## How this would roll out at an enterprise customer

> Demo with mock data: nothing here has been piloted or measured.

### Business value

The value hypothesis is faster, more consistent first minutes of a SEV-1:

- **Less time to orientation.** A responder paged at night otherwise has to read the alert, open dashboards and find the runbook before acting. A spoken briefing of what is failing, since when and the likely cause can happen while they are still getting to a laptop.
- **Consistent first step.** Every responder hears the same runbook-grounded suggestion, regardless of who is on call or how familiar they are with the service.
- **Hands-free.** The briefing works when the laptop is not open yet.
- **Cost of delay.** The cost of a minute of downtime differs per customer and per service, so it is an input to collect during the pilot, not a number to assume.

What it deliberately does not do: it cannot page, notify or change anything. It briefs and suggests; the engineer acts.

### Metrics

No numbers are claimed here. Each row says what is measured and where the baseline comes from; targets are agreed with the customer after the baseline is known.

| Metric | Definition | Baseline source | Pilot measurement |
|---|---|---|---|
| MTTA (mean time to acknowledge) | Page sent to human acknowledges | The customer's PagerDuty analytics for the pilot services, for a period before rollout | Same report after rollout, same services, compared against the baseline period |
| Time to first correct action | Acknowledge to first runbook-appropriate step | Reviewed from past incident timelines and postmortems (manual labeling, since this is rarely recorded) | Incident timeline plus conversation transcripts, labeled by a reviewer |
| Escalation accuracy | Share of escalations that were needed and went to the right team | Past incidents reviewed against the escalation policy | Conversation transcripts compared with what the runbook and policy required |
| Briefing accuracy | Share of briefings with no factual error vs. the source alert | Not applicable (new capability) | Spot-check of briefings against the alert payload, with errors recorded by type |
| Responder trust / CSAT | Whether responders found the assistant useful and safe to rely on | Short survey before the pilot, if the customer agrees | Short post-incident survey for responders who used it |

Caveats to state up front: incident mix and severity vary between periods, so before/after comparisons need care, and a small number of incidents will not support strong conclusions.

### Pilot-to-production plan

1. **Pilot (shadow mode):** one team, one or two services. Replay past incidents through the summarizer and compare briefings with the real alert data and with what responders actually did. Exit criterion: briefings are factually accurate on the replayed set, reviewed by the team.
2. **Limited live:** the same team, business hours first, then on-call. The human stays in the loop; the agent only briefs and suggests. Collect the metrics above and review transcripts weekly. Exit criterion: agreed with the team before starting.
3. **Production:** more teams, real PagerDuty webhooks replace the mock payload, per-service runbooks, agent authentication enabled, and access control and audit logging for conversations.
4. **Guardrails:** read-only by default; no action on production systems without explicit human confirmation; data retention and PII handling for transcripts and audio reviewed with the customer's security team. Customer-specific constraints are gathered during the pilot kickoff.

## Docs used

- ElevenLabs: dynamic variables, JS client (`@elevenlabs/client`), signed URL endpoint
- Anthropic: Python SDK (`messages.create`), model overview
