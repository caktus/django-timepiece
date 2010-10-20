BEGIN;
ALTER TABLE timepiece_personschedule ALTER COLUMN "hours_per_week" type numeric(8, 2);
ALTER TABLE timepiece_projectcontract ALTER COLUMN "num_hours" type numeric(8, 2);
ALTER TABLE timepiece_contractassignment ALTER COLUMN "num_hours" type numeric(8, 2);
COMMIT;
