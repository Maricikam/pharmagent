# PharmAgent AI — MVP Definition

## Problem

Community pharmacists in Scotland dispense thousands of prescriptions weekly with no AI-assisted safety net.

- **Drug interaction checking** is done manually, from memory or printed reference cards — slow, inconsistent, and error-prone for patients on five or more medications.
- **Stock management** is reactive: reorder decisions made on gut feel, expiry waste untracked.
- **Patient engagement** (refill reminders) is routinely skipped because there is no time.
- **Adverse drug reactions from missed interactions** account for an estimated 6.5% of UK hospital admissions. Most are preventable.

## Target user

A community pharmacist working in a single-branch NHS Scotland pharmacy. Works alone or with one dispensing technician. Has no dedicated IT support and cannot wait for a multi-year NHS procurement cycle.

---

## MVP scope

The MVP answers one question: **can a single pharmacist, using only a chat app or a browser, make safer and faster clinical decisions with AI assistance?**

### In scope — core features

| Feature | Why it is core |
|---|---|
| **Drug interaction check** | Highest clinical risk. A missed Major interaction can kill a patient. This is the single most important thing the system does. |
| **Patient lookup** | Required for every interaction check. Pharmacist must be able to look up a patient by CHI or name without leaving the tool. |
| **Stock review with auto-reorder** | Saves significant time daily. Prevents stockouts that block dispensing entirely. |
| **Refill reminder campaign** | Patients who don't collect their prescriptions are the next emergency supply waiting to happen. Proactive outreach reduces that risk. |
| **Audit trail** | Non-negotiable for NHS regulatory compliance. Every agent action must be logged. |
| **Daily briefing** | The orchestrated workflow that ties all agents together. Delivers the key morning status in one request. |
| **OpenClaw/WhatsApp integration** | Meets the pharmacist where they already are. No new app to install. |

### In scope — supporting features

These are implemented and working but are not the primary value proposition:

| Feature | Notes |
|---|---|
| **Shift handover** | Useful but lower urgency than the core six above. |
| **Emergency supply record** | Covers an NHS legal requirement. Relatively rare event. |
| **Analytics — patient prioritisation** | Useful for morning planning. Depends on having patient data populated. Exposed via dashboard tab and `pharmagent-analytics` OpenClaw skill. |
| **Analytics — anomaly detection** | Flags what the pharmacist might otherwise miss across the full patient list. Same skill and tab. |
| **Analytics — workflow optimisation** | Advisory only. Lower urgency for MVP. Same skill and tab. |

---

## What is built and working

| Component | Status |
|---|---|
| 7 specialist agents | Built and callable |
| 20+ FastAPI endpoints | Live on Railway |
| Web dashboard | Working — all tabs functional |
| OpenClaw skills (8 files) | Written and registered |
| CHI number validation (Modulus 11) | Implemented |
| 80-record DDI database (DrugBank / Micromedex) | Integrated — injected into every interaction check |
| 5,000-record adherence dataset | Integrated — used for patient risk scoring |
| Audit trail | Every agent action logged with timestamp and agent identity |
| Demo mode / Live AI toggle | Dashboard switches between seeded demo data and live AI |
| Rate limiting | Applied to all agent endpoints |
| API key protection | All endpoints except `/health` and `/demo` |
| PostgreSQL (production) / SQLite (local) | Both supported |
| 10 seeded demo patients with realistic medication profiles | Ready for testing |

---

## What is stubbed — not production-ready

These features exist in the code but do not do what they claim in a real deployment:

| Feature | Current state | What production needs |
|---|---|---|
| **SMS / email delivery** | `send_patient_message()` logs the message to the audit trail instead of sending it | Twilio (SMS) or NHS Notify integration with real credentials |
| **Supplier reorders** | `place_reorder()` logs a reference number — no supplier API is called | EDI or supplier portal integration (e.g. AAH, Alliance Healthcare) |
| **Prescriber notification (emergency supply)** | The 72-hour notification requirement is written into the generated record but the notification is not actually sent | Automated fax or NHS Mail to the prescriber's practice |
| **Patient data** | 10 seeded demo patients in a local database | Integration with the pharmacy's existing PMR system (e.g. Nexphase, Titan) |
| **Stock data** | Seeded inventory in a local database | Live feed from the dispensary's stock management system |
| **Authentication** | Single shared API key | Per-user login, role-based access (pharmacist vs. technician vs. manager) |

---

## Out of scope for MVP

These are deliberately excluded. They would add significant complexity without validating the core value proposition:

- **Patient-facing portal** — patients do not interact with the system directly in MVP
- **GP / EHR integration** — prescription data comes from the pharmacy's PMR, not GP systems
- **Controlled drug (CD) register** — separate legal framework; too complex for MVP
- **Multi-branch support** — single pharmacy only
- **Billing / NHS reimbursement claims** — separate system
- **Regulatory approval (MHRA, NHS Digital)** — required before live clinical use; not a software problem
- **Real-time prescription intake** (electronic prescribing EPS feed) — requires NHS Spine access

---

## Success criteria for MVP

The MVP is validated when a pharmacist can:

1. Check a patient's interaction risk for a new medication in under 30 seconds, from a WhatsApp message
2. Get a complete stock status with predicted shortages in one click, without opening the dispensary system
3. Send personalised refill reminders to all patients due this week in a single action
4. Start their shift with a full briefing covering stock, expiry, and patient priorities without manual preparation
5. Have every one of those actions appear in a timestamped audit trail

None of these require Twilio, supplier APIs, or PMR integration — they work with the seeded dataset, proving the AI layer before the integrations are built.

---

## Production readiness gaps (before real clinical use)

Before this can be used with real patients:

1. **PMR integration** — replace seeded data with a live read from the pharmacy's patient medication record system
2. **SMS delivery** — connect `send_patient_message()` to Twilio or NHS Notify with real opt-out handling
3. **Supplier reorder API** — replace the logged reference with a real EDI call
4. **Per-user authentication** — replace the shared API key with individual logins and role-based access control
5. **Data residency** — deploy within DataVita's Scottish data centres (architecture already designed for this)
6. **Clinical governance sign-off** — pharmacist-in-charge review of interaction severity rules and AI output boundaries
7. **Information governance** — Data Protection Impact Assessment (DPIA) for patient data processing

---

## Roadmap (post-MVP)

| Version | Focus |
|---|---|
| **v1.1** | Real SMS delivery via Twilio / NHS Notify; supplier reorder API |
| **v1.2** | PMR system integration (read patient and prescription data from existing dispensary software) |
| **v2.0** | Multi-branch support; per-user authentication; pharmacist-facing mobile app |
| **v2.1** | EPS feed integration (NHS electronic prescriptions) |
| **v3.0** | Regulatory submission; live clinical pilot with consenting pharmacy |
