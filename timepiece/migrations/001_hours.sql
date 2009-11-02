BEGIN;
ALTER TABLE timepiece_entry ADD COLUMN hours NUMERIC(8, 2);
UPDATE timepiece_entry SET hours = COALESCE(ROUND(CAST((EXTRACT (EPOCH FROM (end_time - start_time)) - seconds_paused) / 3600 AS NUMERIC), 2), 0.0);
COMMIT;

BEGIN;
ALTER TABLE timepiece_entry ALTER hours SET NOT NULL;
COMMIT;

BEGIN;
ALTER TABLE timepiece_project ADD CONSTRAINT timepiece_project_repeat_period_id_fkey FOREIGN KEY (billing_period_id) REFERENCES "timepiece_repeatperiod" ("id") DEFERRABLE INITIALLY DEFERRED;
COMMIT;
