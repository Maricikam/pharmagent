# PharmAgent AI — OpenClaw Integration Guide

PharmAgent ships four OpenClaw skills that let you control the pharmacy system directly from WhatsApp, Telegram, Discord, or any chat app connected to your OpenClaw instance.

---

## Skills included

| Skill | What it does |
|---|---|
| `pharmagent-interaction-check` | Check a patient's medications for interaction risks before dispensing |
| `pharmagent-stock-review` | Review stock levels, flag expiry, trigger supplier reorders |
| `pharmagent-patient-engagement` | Send personalised SMS refill reminders to patients |
| `pharmagent-morning-briefing` | Full orchestrated daily workflow (all three agents in sequence) |

---

## Setup (5 minutes)

### 1. Deploy PharmAgent API

Follow the main `README.md` to deploy the FastAPI backend (Railway free tier recommended).

Note your deployment URL — e.g. `https://web-production-1f27a.up.railway.app`

### 2. Install OpenClaw

```bash
npm install -g openclaw
openclaw onboard
```

### 3. Load PharmAgent skills

Clone this repo into your OpenClaw workspace, or copy the `skills/` folder:

```bash
git clone https://github.com/Maricikam/pharmagent
cd pharmagent
```

Then add the skills path to your `~/.openclaw/openclaw.json`:

```json
{
  "skills": {
    "load": {
      "extraDirs": ["./skills"]
    }
  }
}
```

Or copy the provided `openclaw.json` as a starting point:

```bash
cp openclaw.json ~/.openclaw/openclaw.json
```

### 4. Set your API URL

Edit `~/.openclaw/openclaw.json` and replace `https://your-pharmagent-url.up.railway.app` with your actual deployment URL.

### 5. Connect a channel (e.g. Telegram)

```bash
openclaw channel add telegram
```

Follow the prompts. Once connected, open Telegram and message your bot.

---

## Example conversations

Once set up, you can talk to PharmAgent naturally:

> **"Good morning, run the pharmacy check"**
> → Triggers the morning briefing: stock review + expiry check + patient reminders

> **"Check Thomas Robertson before I dispense — CHI 2201380015"**
> → Runs the interaction safety check against his active medications

> **"What's running low on stock?"**
> → Returns current low-stock items with reorder status

> **"Send SMS reminders to patients due this week"**
> → Contacts all patients with prescriptions due in 7 days

---

## Scheduled daily briefing

To automate the morning workflow, enable the scheduled task in `openclaw.json`:

```json
{
  "automation": {
    "tasks": [
      {
        "id": "pharmagent-daily-briefing",
        "cron": "0 8 * * 1-5",
        "skill": "pharmagent-morning-briefing",
        "enabled": true
      }
    ]
  }
}
```

This runs every weekday at 08:00 and sends the briefing to your connected channel.

---

## Architecture: why OpenClaw fits

PharmAgent is built on the same architectural principles as OpenClaw:

| Layer | PharmAgent | OpenClaw equivalent |
|---|---|---|
| Tool layer | Deterministic DB queries, stock checks, audit logging | OpenClaw tool plugins |
| Agent layer | Claude-powered reasoning agents | OpenClaw agent turns |
| Orchestration | OrchestratorAgent coordinates sub-agents | OpenClaw multi-agent + sub-agents |
| Communication | Chat interface for pharmacists | OpenClaw channels (WhatsApp, Telegram) |
| Automation | Scheduled morning briefing | OpenClaw cron tasks |

PharmAgent's FastAPI backend exposes the multi-agent system as HTTP endpoints, and these OpenClaw skills teach your lobster how to call them — turning a pharmacy AI into something you can manage from your phone.
