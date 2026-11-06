# AcademicBloom
An Application that helps students to improve academically and bloom in their examinations.

## Database setup

The project uses `db.sqlite3` when `DATABASE_URL` is not set, which is convenient
for local development. For a deployed service, configure `DATABASE_URL` to point
to a persistent PostgreSQL database so user accounts and other application data
survive deploys and are shared by all service instances. For Render, add a
PostgreSQL database and set the web service's `DATABASE_URL` environment variable
to that database's connection URL. The build script runs Django migrations.

Changing the database URL does not copy existing SQLite records into PostgreSQL;
existing accounts must be migrated separately or users will need to register
again in the new database.
