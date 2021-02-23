# swh-clearlydefined

ClearlyDefined metadata Fetcher for Software Heritage


Installation of Clearcode Toolkit and running it
================================================

https://github.com/nexb/clearcode-toolkit#quick-start-using-a-database-storage


Setting up SWH-CLEARLYDEFINED
=============================

* pip3 install -r requirements-swh.txt


Running of SWH-CLEARLYDEFINED metadata fetcher
==============================================

* Create a config file (sample config file)
* Then pass command "swh clearlydefined [OPTIONS] fill_storage"
* OPTIONS - 
-   -C, --config-file <config_file>

    Configuration file (default: /home/jenkins/.config/swh/global.yml)
- --clearcode-dsn
    Sample DSN : "dbname=clearcode user=postgres host=127.0.0.1 port=32552 options=''"

* Sample command looks like this:
swh clearlydefined -C /path/to/file --clearcode-dsn dbname=clearcode user=postgres host=127.0.0.1 port=32552 options='' fill_storage

* Set a sample command like this on a cron tab that will fill data periodically

Example to run this command weekly at 8:00 am morning on Sunday:
    0 8 * * 0 swh clearlydefined -C /path/to/file --clearcode-dsn "dbname=clearcode user=clearcode host=127.0.0.1 port=32552 options=''" fill_storage


Architecture
============

When user gives above command, it activates orchestration process.

Orchestration Process - Fetches data from clearcode toolkit DB and then try to map it with SWH Storage, and the data which is able to be mapped (based on
mapping status) is written in RawExtrensicMetadata table of SWH Storage and data that is not being able to be mapped is stored in a state, so that data can
be mapped in future (updation of SWH storage).

Mapping Process - Clearcode toolkit majorly contains two types of row data, one is definitions and second is harvest. Havests can further be classified as 4
types for now (more harvest tools can be used in future) Clearlydefined, Licensee, Scancode, Fossology. Definitions can contain sha1 or sha1git and if it
is able to mapped we send mapping status true else false. Harvests of type Clearlydefined, Licensee, Scancode contains a list of sha1 data and if we are
able to map every sha1 from that list we send mapping status as true else false and since Harvests of Fossology doesn't contain any data that can be mapped
with SWH storage, we ignore it and neither try to map it nor store in the state
      
Mapping of Sha1 and Sha1git -  Sha1 is tried to be mapped with "content" table, if it exists in "content" table then SWHID is made using the respective
sha1git of that sha1 like this "swh:cnt:(sha1git)" and if it contains sha1git, then it is mapped using "revision" table, if it exists in "revision" table
then SWHID is made like this "swh:rev:(sha1git)".
