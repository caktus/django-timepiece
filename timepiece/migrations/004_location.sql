BEGIN;
CREATE TABLE "timepiece_location" (
    "id" serial NOT NULL PRIMARY KEY,
    "name" text NOT NULL
)
;
INSERT INTO "timepiece_location" ("name") VALUES ('Office');
INSERT INTO "timepiece_location" ("name") VALUES ('SRC');
ALTER TABLE timepiece_entry ADD COLUMN "location_id" integer;
ALTER TABLE timepiece_entry ADD CONSTRAINT timepiece_entry_location_id_fkey FOREIGN KEY (location_id) REFERENCES timepiece_location (id) DEFERRABLE INITIALLY DEFERRED;
UPDATE timepiece_entry SET location_id=2 WHERE location like 'SRC';
UPDATE timepiece_entry SET location_id=1 WHERE location not like 'SRC';
ALTER TABLE timepiece_entry DROP COLUMN "location";
COMMIT;
