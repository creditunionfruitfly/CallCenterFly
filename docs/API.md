# Experimental API

Install and run:

```bash
python -m pip install -e '.[serve]'
callcenterfly serve --host 127.0.0.1 --port 8080
```

The server is a local research boundary. It performs no authentication, account access,
payment action, or production workflow.

## `GET /healthz`

Returns backend identity, whether a connectome is in use, and production status.

## `POST /v1/decision`

Minimum illustrative request:

```json
{
  "decision_id": "synthetic-demo-1",
  "phase": "investigate_and_classify",
  "scenario_id": "CU004",
  "scenario_family": "zelle_pending_recipient_unenrolled",
  "category": "p2p_payments",
  "product": "zelle",
  "intent": "zelle_pending_recipient_unenrolled",
  "member_utterance": "My payment is pending and the recipient used another email.",
  "valence": "neutral",
  "arousal": "medium",
  "urgency": "time_sensitive",
  "authentication_state": "verified",
  "risk_tier": "routine",
  "candidate_actions": [
    "CHECK_RECIPIENT_ENROLLMENT",
    "CHECK_TRANSACTION_STATUS",
    "DOCUMENT_CASE"
  ]
}
```

Response fields include the selected action, ranked eligible probabilities, backend,
`connectome_used`, draft response ID/text/status, and mandatory review flags.

Inference requests must not include target labels or rewards in a future operational
integration. The current CLI can read labeled synthetic rows only to make evaluation
and demos reproducible.
