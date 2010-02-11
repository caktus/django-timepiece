BEGIN;
CREATE TABLE "timepiece_location" (
    "id" serial NOT NULL PRIMARY KEY,
    "name" text NOT NULL
)
;
INSERT INTO "timepiece_location" ("name") VALUES ('Office');
ALTER TABLE timepiece_entry DROP COLUMN "location";
ALTER TABLE timepiece_entry ADD COLUMN "location_id" integer;
ALTER TABLE timepiece_entry ADD CONSTRAINT timepiece_entry_location_id_fkey FOREIGN KEY (location_id) REFERENCES timepiece_location (id) DEFERRABLE INITIALLY DEFERRED;
UPDATE timepiece_entry SET location_id=1;
COMMIT;
