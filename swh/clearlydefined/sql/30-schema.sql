---
--- SQL implementation of the Clearlydefined data
---

-- schema versions
create table dbversion
(
  version     int primary key,
  release     timestamptz,
  description text
);

comment on table dbversion is 'Details of current db version';
comment on column dbversion.version is 'SQL schema version';
comment on column dbversion.release is 'Version deployment timestamp';
comment on column dbversion.description is 'Release description';

-- latest schema version
insert into dbversion(version, release, description)
      values(1, now(), 'Work In Progress');

--schema clearcode_cditem
create table clearcode_cditem(
  path                varchar(2048) primary key,
  content             bytea not null,
  last_modified_date  timestamptz not null,
  last_map_date       timestamptz,
  map_error           text,
  uuid uuid           not null
);

comment on table clearcode_cditem is 'Data of clearcode_toolkit';
comment on column clearcode_cditem.path is 'ID';
comment on column clearcode_cditem.content is 'Metadata content';

--schema unmapped_data
create table unmapped_data(
  path     varchar primary key
);

comment on table unmapped_data is 'Unmapped Data of clearcode_toolkit';
comment on column unmapped_data.path is 'ID';

--schema clearcode_env
create table clearcode_env(
  key    text primary key,
  value  text
);

comment on table clearcode_env is 'Stores key value pair';
