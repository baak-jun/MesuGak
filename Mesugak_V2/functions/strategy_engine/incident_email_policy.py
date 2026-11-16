"""Durable queue policy, including callers already running before deployment."""

POLICY_SQL = """
CREATE TABLE IF NOT EXISTS contest_mail_incidents (
    kind TEXT PRIMARY KEY, active INTEGER NOT NULL,
    opened_at INTEGER NOT NULL, alert_key TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS contest_incident_mail_delay
AFTER INSERT ON email_outbox
WHEN NEW.event_key LIKE 'health:%' OR NEW.event_key LIKE 'state:%'
BEGIN
    INSERT OR IGNORE INTO contest_mail_incidents(kind,active,opened_at,alert_key)
    VALUES (
      CASE WHEN NEW.event_key LIKE 'state:%' THEN 'state'
           ELSE substr(NEW.event_key,1,7+instr(substr(NEW.event_key,8),':')-1) END,
      0,0,'');

    -- A recovery is deliverable only for a genuinely sent, qualified incident.
    UPDATE email_outbox SET next_attempt_at=253402300799,
      last_error='suppressed_short_or_unsent_incident'
    WHERE event_key=NEW.event_key
      AND (NEW.subject LIKE '%이상 복구%' OR NEW.event_key LIKE 'state:%:False')
      AND (NEW.event_key LIKE 'health:scan_failures:%' OR NOT EXISTS (
        SELECT 1 FROM contest_mail_incidents i JOIN email_outbox a ON a.event_key=i.alert_key
        WHERE i.kind=CASE WHEN NEW.event_key LIKE 'state:%' THEN 'state'
                         ELSE substr(NEW.event_key,1,7+instr(substr(NEW.event_key,8),':')-1) END
          AND i.active=1 AND a.sent_at IS NOT NULL
          AND CAST(strftime('%s',NEW.created_at) AS INTEGER)-i.opened_at>=1200));

    -- Recovery cancels an alert that never reached the recipient.
    UPDATE email_outbox SET next_attempt_at=253402300799,last_error='suppressed_recovered_before_delivery'
    WHERE sent_at IS NULL AND event_key IN (
      SELECT alert_key FROM contest_mail_incidents
      WHERE kind=CASE WHEN NEW.event_key LIKE 'state:%' THEN 'state'
                      ELSE substr(NEW.event_key,1,7+instr(substr(NEW.event_key,8),':')-1) END)
      AND (NEW.subject LIKE '%이상 복구%' OR NEW.event_key LIKE 'state:%:False');

    UPDATE contest_mail_incidents SET active=0
    WHERE kind=CASE WHEN NEW.event_key LIKE 'state:%' THEN 'state'
                    ELSE substr(NEW.event_key,1,7+instr(substr(NEW.event_key,8),':')-1) END
      AND (NEW.subject LIKE '%이상 복구%' OR NEW.event_key LIKE 'state:%:False');

    -- Never create another reminder while the same incident is active.
    UPDATE email_outbox SET next_attempt_at=253402300799,last_error='suppressed_repeat_incident'
    WHERE event_key=NEW.event_key
      AND (NEW.subject LIKE '%이상 감지%' OR NEW.event_key LIKE 'state:%:True')
      AND EXISTS (SELECT 1 FROM contest_mail_incidents WHERE active=1
        AND kind=CASE WHEN NEW.event_key LIKE 'state:%' THEN 'state'
                      ELSE substr(NEW.event_key,1,7+instr(substr(NEW.event_key,8),':')-1) END);

    UPDATE contest_mail_incidents
    SET active=1, alert_key=NEW.event_key,
        opened_at=CAST(strftime('%s',NEW.created_at) AS INTEGER)
          -CASE WHEN NEW.event_key LIKE 'health:score_stale:%' THEN 1200 ELSE 0 END
    WHERE active=0
      AND kind=CASE WHEN NEW.event_key LIKE 'state:%' THEN 'state'
                    ELSE substr(NEW.event_key,1,7+instr(substr(NEW.event_key,8),':')-1) END
      AND (NEW.subject LIKE '%이상 감지%' OR NEW.event_key LIKE 'state:%:True');

    -- score_stale is already detected only after 20 minutes, so do not wait twice.
    UPDATE email_outbox SET next_attempt_at=(SELECT opened_at+1200 FROM contest_mail_incidents WHERE alert_key=NEW.event_key),
      last_error='waiting_for_20_minute_incident'
    WHERE event_key=NEW.event_key
      AND EXISTS(SELECT 1 FROM contest_mail_incidents WHERE alert_key=NEW.event_key AND active=1)
      AND (NEW.subject LIKE '%이상 감지%' OR NEW.event_key LIKE 'state:%:True');
END;
"""


def install(connection):
    connection.executescript(POLICY_SQL)
