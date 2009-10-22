BEGIN;
ALTER TABLE pendulum_entry ADD COLUMN hours NUMERIC(8, 2);
UPDATE pendulum_entry SET hours = COALESCE(ROUND(CAST((EXTRACT (EPOCH FROM (end_time - start_time)) - seconds_paused) / 3600 AS NUMERIC), 2), 0.0);
COMMIT;

BEGIN;
ALTER TABLE pendulum_entry ALTER hours SET NOT NULL;
COMMIT;
