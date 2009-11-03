BEGIN;
ALTER TABLE timepiece_project ADD COLUMN "type_id" integer REFERENCES "timepiece_attribute" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE timepiece_project ADD COLUMN "status_id" integer REFERENCES "timepiece_attribute" ("id") DEFERRABLE INITIALLY DEFERRED;

INSERT INTO timepiece_attribute (type, label) VALUES ('project-type', 'Consultation');
INSERT INTO timepiece_attribute (type, label) VALUES ('project-type', 'Software');

INSERT INTO timepiece_attribute (type, label) VALUES ('project-status', 'Incoming');
INSERT INTO timepiece_attribute (type, label) VALUES ('project-status', 'Current');
INSERT INTO timepiece_attribute (type, label) VALUES ('project-status', 'Complete');
INSERT INTO timepiece_attribute (type, label) VALUES ('project-status', 'Closed');

UPDATE timepiece_project p SET type_id = a.id FROM timepiece_attribute a WHERE p.type = lower(a.label) AND a.type = 'project-type';
UPDATE timepiece_project p SET status_id = a.id FROM timepiece_attribute a WHERE p.status = lower(a.label) AND a.type = 'project-status';
COMMIT;
BEGIN;
ALTER TABLE timepiece_project ALTER COLUMN "type_id" SET NOT NULL;
ALTER TABLE timepiece_project ALTER COLUMN "status_id" SET NOT NULL;
ALTER TABLE timepiece_project DROP COLUMN "type";
ALTER TABLE timepiece_project DROP COLUMN "status";
COMMIT;
