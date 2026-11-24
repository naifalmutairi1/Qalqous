-- 001_init.sql: the MVP schema (approved 2026-11-24).
-- All times are text in ISO 8601 with the Riyadh offset, e.g. 2026-11-23T23:02:07+03:00.
-- Riyadh has no daylight saving, so "+3 hours" from UTC is always correct.

-- The simulated employee accounts. Suspend / restore change only `status`.
CREATE TABLE accounts (
    id           INTEGER PRIMARY KEY,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+03:00', 'now', '+3 hours')),
    username     TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    access_ar    TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended'))
);

-- Raw login lines (read-only input). The id is the "log line ID" findings point to.
-- No foreign key on `account`: logs are raw input and may name any user.
CREATE TABLE log_events (
    id          INTEGER PRIMARY KEY,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+03:00', 'now', '+3 hours')),
    time        TEXT NOT NULL,
    account     TEXT NOT NULL,
    source_ip   TEXT NOT NULL,
    success     INTEGER NOT NULL CHECK (success IN (0, 1))   -- 0 = LOGIN_FAIL, 1 = LOGIN_SUCCESS
);
CREATE INDEX log_events_account_time ON log_events (account, time);

-- One suspicious burst. Detection fills the snapshot columns once;
-- the investigation fills the report columns.
CREATE TABLE incidents (
    id                INTEGER PRIMARY KEY,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+03:00', 'now', '+3 hours')),
    account           TEXT NOT NULL REFERENCES accounts (username),
    status            TEXT NOT NULL DEFAULT 'investigating'
                      CHECK (status IN ('investigating', 'awaiting_decision', 'decided')),
    first_fail_log_id INTEGER NOT NULL REFERENCES log_events (id),
    trigger_log_id    INTEGER NOT NULL UNIQUE REFERENCES log_events (id),
    source_ip         TEXT NOT NULL,
    failed_attempts   INTEGER NOT NULL CHECK (failed_attempts >= 5),
    ip_seen_before    INTEGER NOT NULL CHECK (ip_seen_before IN (0, 1)),
    access_ar         TEXT NOT NULL,
    report_source     TEXT CHECK (report_source IN ('ai', 'rules')),
    headline_ar       TEXT,
    summary_ar        TEXT,
    report_ready_at   TEXT,
    CHECK (first_fail_log_id < trigger_log_id),
    -- No report link without a report: once past "investigating", the report must exist.
    CHECK (status = 'investigating'
           OR (report_source IS NOT NULL AND headline_ar IS NOT NULL AND report_ready_at IS NOT NULL))
);
-- At most one undecided incident per account (a "partial" index: it only covers some rows).
CREATE UNIQUE INDEX incidents_one_open_per_account ON incidents (account) WHERE status != 'decided';

-- The five facts on the Report. confirmed = 0 means the UI shows «(غير مؤكد)».
CREATE TABLE findings (
    id          INTEGER PRIMARY KEY,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+03:00', 'now', '+3 hours')),
    incident_id INTEGER NOT NULL REFERENCES incidents (id),
    kind        TEXT NOT NULL
                CHECK (kind IN ('failed_attempts', 'success_time', 'source_ip', 'duration', 'seen_before')),
    confirmed   INTEGER NOT NULL DEFAULT 0 CHECK (confirmed IN (0, 1)),
    UNIQUE (incident_id, kind)
);

-- Which log lines back each finding (one finding -> many lines).
CREATE TABLE finding_evidence (
    id          INTEGER PRIMARY KEY,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+03:00', 'now', '+3 hours')),
    finding_id  INTEGER NOT NULL REFERENCES findings (id),
    log_id      INTEGER NOT NULL REFERENCES log_events (id),
    UNIQUE (finding_id, log_id)
);

-- The admin's decision. created_at is the decision time. Once per incident.
CREATE TABLE decisions (
    id          INTEGER PRIMARY KEY,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+03:00', 'now', '+3 hours')),
    incident_id INTEGER NOT NULL UNIQUE REFERENCES incidents (id),
    choice      TEXT NOT NULL CHECK (choice IN ('keep_suspended', 'restore'))
);

-- Each tool call Claude makes. One tool call = one step; at most 6.
CREATE TABLE investigation_steps (
    id          INTEGER PRIMARY KEY,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+03:00', 'now', '+3 hours')),
    incident_id INTEGER NOT NULL REFERENCES incidents (id),
    step_no     INTEGER NOT NULL CHECK (step_no BETWEEN 1 AND 6),
    tool        TEXT NOT NULL CHECK (tool IN ('search_logs', 'count_events', 'build_timeline')),
    tool_input  TEXT NOT NULL,   -- JSON text
    tool_output TEXT NOT NULL,   -- JSON text
    UNIQUE (incident_id, step_no)
);
