{
  // PharmAgent AI — OpenClaw Workspace Configuration
  // Place this file at: ~/.openclaw/openclaw.json
  // Or copy to your OpenClaw workspace root.
  //
  // Before use:
  //   1. Set PHARMAGENT_API_URL to your deployed PharmAgent API (e.g. https://pharmagent.up.railway.app)
  //   2. Set ANTHROPIC_API_KEY in your environment
  //   3. Run: openclaw onboard

  "skills": {
    "load": {
      "extraDirs": ["./skills"]
    },
    "entries": {
      "pharmagent-interaction-check": {
        "enabled": true,
        "env": {
          "PHARMAGENT_API_URL": "https://your-pharmagent-url.up.railway.app"
        }
      },
      "pharmagent-stock-review": {
        "enabled": true,
        "env": {
          "PHARMAGENT_API_URL": "https://your-pharmagent-url.up.railway.app"
        }
      },
      "pharmagent-patient-engagement": {
        "enabled": true,
        "env": {
          "PHARMAGENT_API_URL": "https://your-pharmagent-url.up.railway.app"
        }
      },
      "pharmagent-morning-briefing": {
        "enabled": true,
        "env": {
          "PHARMAGENT_API_URL": "https://your-pharmagent-url.up.railway.app"
        }
      }
    }
  },

  "automation": {
    "tasks": [
      {
        "id": "pharmagent-daily-briefing",
        "name": "PharmAgent Daily Morning Briefing",
        "description": "Runs the full pharmacy workflow every weekday at 08:00: stock review, expiry check, and patient SMS reminders.",
        "cron": "0 8 * * 1-5",
        "skill": "pharmagent-morning-briefing",
        "enabled": false
      }
    ]
  }
}
