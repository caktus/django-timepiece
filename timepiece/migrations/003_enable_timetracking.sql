BEGIN;
ALTER TABLE timepiece_attribute ADD COLUMN "enable_timetracking" boolean;
UPDATE timepiece_attribute SET "enable_timetracking" = false;
UPDATE timepiece_attribute SET "enable_timetracking" = true WHERE type = 'project-status' AND label = 'Current';
ALTER TABLE timepiece_attribute ALTER COLUMN "enable_timetracking" SET NOT NULL;
COMMIT;
