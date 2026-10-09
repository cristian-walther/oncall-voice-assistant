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

## How this would roll out at an enterprise customer

### Business value

<!-- TODO: fill in with your own reasoning/observations. Prompts to consider:
- Cost of a minute of SEV-1 downtime for a payments business
- Time an engineer spends reading alerts, dashboards and the runbook before acting at 3 AM
- Hands-free briefing while moving (laptop not open yet)
- Consistency: every responder gets the same runbook-grounded first steps -->

### Metrics

| Metric | Definition | Baseline | Pilot target |
|---|---|---|---|
| MTTA (mean time to acknowledge) | Page sent to human acknowledges | _TODO_ | _TODO_ |
| Time to first correct action | Acknowledge to first runbook-appropriate step | _TODO_ | _TODO_ |
| Escalation accuracy | Share of escalations that were needed and went to the right team | _TODO_ | _TODO_ |
| Briefing accuracy | Share of briefings with no factual error vs. the source alert | _TODO_ | _TODO_ |
| Responder trust / CSAT | Post-incident survey | _TODO_ | _TODO_ |

### Pilot-to-production plan

1. **Pilot (shadow mode):** one team, replay past incidents, compare briefings with what responders actually did. _TODO: observations_
2. **Limited live:** the same team, business hours first, then on-call. Human stays in the loop; the agent only briefs and suggests. _TODO: observations_
3. **Production:** more teams, real PagerDuty webhooks replace the mock payload, per-service runbooks, access control and audit logging for conversations. _TODO: observations_
4. **Guardrails:** read-only by default, no destructive actions without explicit human confirmation, data retention and PII policy reviewed with security. _TODO: customer-specific constraints_

## Docs used

- ElevenLabs: dynamic variables, JS client (`@elevenlabs/client`), signed URL endpoint
- Anthropic: Python SDK (`messages.create`), model overview
