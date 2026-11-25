-- 002_investigation_attempts.sql: one row per AI investigation run (approved 2026-11-24).
-- A failure is stored, not guessed, so Home shows the failure strip only after a real AI failure.

-- One AI run for one incident. created_at is the start time.
CREATE TABLE investigation_attempts (
    id             INTEGER PRIMARY KEY,
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+03:00', 'now', '+3 hours')),
    incident_id    INTEGER NOT NULL REFERENCES incidents (id),
    outcome        TEXT NOT NULL DEFAULT 'running'
                   CHECK (outcome IN ('running', 'ai', 'failed', 'discarded')),
    failure_reason TEXT CHECK (failure_reason IN ('api_key_set', 'no_login', 'cli_missing', 'sdk_error',
                                                  'timeout', 'turn_limit', 'invalid_output', 'interrupted')),
    failure_detail TEXT,   -- short English error, for the developer only, never shown in the UI
    finished_at    TEXT,
    -- A reason exactly when the run failed.
    CHECK ((outcome = 'failed') = (failure_reason IS NOT NULL)),
    -- A finish time exactly when the run is over.
    CHECK ((outcome = 'running') = (finished_at IS NULL))
);
-- At most one running attempt per incident: the database's guard against two retries at once.
CREATE UNIQUE INDEX investigation_attempts_one_running ON investigation_attempts (incident_id)
    WHERE outcome = 'running';

-- investigation_steps now belongs to an attempt, so a retry can start again at step 1.
-- SQLite cannot change constraints in place, so the table is dropped and made again.
-- Guard: stop the whole migration if the old table holds any rows (it never has).
-- The CHECK fails on any count above 0, and BEGIN ... COMMIT in store.py undoes everything.
CREATE TEMP TABLE migration_guard (old_steps INTEGER CHECK (old_steps = 0));
INSERT INTO migration_guard SELECT COUNT(*) FROM investigation_steps;
DROP TABLE migration_guard;

DROP TABLE investigation_steps;

-- Each tool call the AI makes. One tool call = one step; at most 6 per attempt.
CREATE TABLE investigation_steps (
    id          INTEGER PRIMARY KEY,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+03:00', 'now', '+3 hours')),
    attempt_id  INTEGER NOT NULL REFERENCES investigation_attempts (id),
    step_no     INTEGER NOT NULL CHECK (step_no BETWEEN 1 AND 6),
    tool        TEXT NOT NULL CHECK (tool IN ('search_logs', 'count_events', 'build_timeline')),
    tool_input  TEXT NOT NULL,   -- JSON text
    tool_output TEXT NOT NULL,   -- JSON text
    UNIQUE (attempt_id, step_no)
);
