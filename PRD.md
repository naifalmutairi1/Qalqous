# قلقوص (Qalqous)

## Problem
A solo IT admin at a small company learns an account was taken over only after it happens. The login records that would have shown it are thousands of lines long, and he has no time or security training to read them.

## User
Abu Fahad, 34, the only IT person in a 25-person contracting company. Knows what a log and an IP are, but can't tell an attack from a normal mistake. Opens Qalqous on his laptop late at night after an alert email, tense and wanting a clear answer fast: which account, how they got in, what that account can damage, and what to do.

## Goal
Give a non-expert admin a trustworthy first answer about a login attack in minutes, and stop the damage while he sleeps.
**Worked if:** one week after launch, an IT admin who isn't me runs قلقوص on a simulated attack and, without my help, names the targeted account and decides to restore it or keep it suspended in under 5 minutes.

## User stories
- **Must** As an IT admin, I want قلقوص to spot a successful login after repeated failures, open an incident and suspend the account (in the simulation) by itself, so that the attacker is stopped even if I'm asleep.
- **Must** As an IT admin, I want a short Arabic report (which account, what it can damage, how many attempts, when, from which address and whether that address was seen before) with a log line behind every claim, so that I can tell an attack from an employee who forgot their password.
- **Must** As an IT admin, I want to choose «إرجاع الحساب» or «إبقاءه موقوف», confirm it, and see a clear, lasting confirmation with the time, so that I know my decision was recorded.
- **Should** As an IT admin, I want one email per new incident, so that I know without keeping the page open.
- **Should** As an IT admin, I want to see previous reports and my past decisions, so that I can check what happened before.
- **Could** As an IT admin, I want a timeline of the attack.
- **Could** As an IT admin, I want to ask a follow-up question in Arabic.

## MVP scope
The 3 Musts, with these limits:

- One attack type only: 5 or more failed logins within 10 minutes, followed by a successful one.
- Suspension happens only in the simulated data. No real system is touched.
- Shallow on purpose: the investigation has a hard cap on steps and stays inside the log. If a claim has no log line behind it, the report says "unconfirmed".
- If the AI investigation fails, a basic rule-based report is shown instead.
- Qalqous never stores or compares passwords.
- Verdict on 4 days: the Musts fit only with these limits. The Shoulds come after the Musts work.

## Out of scope
- Real systems, real company logs, real blocking
- Storing or comparing anyone's passwords
- Deep forensics beyond what the logs show
- Any attack or log type besides repeated failed logins then success
- Contacting the affected employee (that's Abu Fahad's job, outside Qalqous)
- SMS alerts, live log stream, chat
- Login, accounts, multi-company
- Claiming to replace a security team: this is first-pass triage

## Key screens
1. **Home:** status (calm day, incident open, investigation running, or AI failed with basic report), the open incident, last decision, previous reports («عرض الكل» expands the list on Home).
2. **Report:** headline, what happened, what the account can damage, the decision (with "are you sure?" and a green confirmation box), evidence log lines (collapsed).

## Data it remembers
- Log events (time, account, source address, success or fail)
- Accounts (username and a one-line description of what each can access)
- Incidents (account, status, when opened, suspended or not)
- Investigation steps taken
- Findings, each linked to its evidence log line
- Decisions (restore or keep suspended) with time

## Open questions
- How many log lines make the demo feel real without slowing it?
- Is the Arabic report clear to someone who isn't technical?
- Which one real admin can test it after the demo?

## Riskiest assumptions
1. **Auto-suspend will not lock out honest employees too often.** A false alarm locks a real person out at night; the report must make it obvious when it was the employee.
2. **It will only work on the attack I wrote.** If the data is scripted by me, the agent may look smart only on that one case.
3. **12 hours is enough for a beginner.** Three Musts, an agent loop, auto-suspend and a decision screen in 4 evenings leaves no slack.