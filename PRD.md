# قلقوص (Qalqous)

## Problem

A solo IT admin at a small company learns an account was taken over only after it happens. The login records that would have shown it are thousands of lines long, and he has no time or security training to read them.

## User

Abu Fahad, 34, the only IT person in a 25-person contracting company. He is pinged late at night when an employee reports something odd. He works from the office or his phone and needs to know fast: was there a breach, which account, how did they get in, what do I do first.

## Goal

Give a non-expert admin a trustworthy first answer about a login attack in minutes.
**Worked if:** one week after launch, an IT admin who isn't me runs قلقوص on a simulated attack and, without my help, names the targeted account and the first step in under 5 minutes.

## User stories

* **Must** As an IT admin, I want قلقوص to spot a suspicious login pattern by itself and open an incident, so that I don't read thousands of lines.
* **Must** As an IT admin, I want a short Arabic report (which account, how they got in, what to do first) with a log line behind every claim, so that I can trust it in minutes.
* **Must** As an IT admin, I want any suggested action to wait for my Approve or Reject, so that nothing changes without me.
* **Should** As an IT admin, I want a timeline of the attack, so that I see the order of events at a glance.
* **Could** As an IT admin, I want to ask a follow-up in Arabic, so that I can clarify a finding.

## MVP scope

The 3 Musts, with these limits:

* One attack type only: repeated failed logins followed by a successful one.
* Shallow on purpose: the investigation has a hard cap on steps and stays inside the log. It never guesses beyond it. If a claim has no log line behind it, the report says "unconfirmed".
* Approve/Reject only records the decision. Nothing is really blocked.
* Verdict on 4 days: the Musts fit only with these limits. A live log stream, a timeline view and chat do not fit and are cut.

## Out of scope

* Real systems, real company logs, real blocking
* Deep forensics or root-cause digging beyond what the logs show
* Any attack or log type besides repeated failed logins then success
* Live log stream, timeline view, chat (all post-MVP)
* Login, accounts, multi-company
* Email/SMS alerts
* Claiming to replace a security team: this is first-pass triage

## Key screens

1. **Logs \& alerts:** the simulated logs and the incident that was opened.
2. **Investigation report:** the Arabic findings, each with its evidence line, or "unconfirmed".
3. **Action approval:** the proposed action with Approve and Reject.

## Data it remembers

* Log events (time, account, source address, success or fail)
* Incidents (status, when opened)
* Investigation steps taken
* Findings, each linked to its evidence log line
* Proposed actions and the admin's decision with time

## Open questions

* What exact pattern counts as suspicious (how many failures, in how long)?
* How many log lines make the demo feel real without slowing it?
* Is the Arabic report clear to someone who isn't technical?
* Which one real admin can test it after the demo?

## Riskiest assumptions

1. **It will only work on the attack I wrote.** If the data is scripted by me, the agent may look smart only on that one case, and a judge could notice.
2. **A capped investigation is still useful.** Limiting depth to avoid wrong answers may leave reports too thin to name the account and first step.
3. **12 hours is enough for a beginner.** Three Musts, an agent loop and an approval screen in 4 evenings leaves no slack if one part breaks.

