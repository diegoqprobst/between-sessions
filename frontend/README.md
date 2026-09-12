# Frontend contract

The first version is dependency-free static HTML, CSS and JavaScript so it can be demoed immediately:

```bash
cd frontend && python3 -m http.server 5173
```

It intentionally uses synthetic, local placeholder data until the backend contract is ready. Claude can add these endpoints without changing the UI structure:

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/me/overview` | `GET` | Worker-visible weekly summary: sleep average, completed homework, check-in count, paused state and current plan. Never return message text or employer data. |
| `/api/me/pause` | `POST` | `{ "paused": true }`; maps to the existing patient pause control. |
| `/api/me/exclusions` | `POST` | `{ "signal": "sleep" }`; maps to `no compartas sueño`. |
| `/api/me/delete` | `DELETE` | Deletes signals, messages, check-ins and briefs after an explicit confirmation in the client. |
| `/api/me/slack` | `GET` | Returns a safe Slack deep link for the already-authorized DM. |

Authentication must identify the worker from Slack OAuth/session state. Never accept a `patient_id` from the browser, expose another worker's records, or return raw conversation text in the overview response.
