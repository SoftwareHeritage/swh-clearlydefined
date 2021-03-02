# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU Affero General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime
from typing import List, Optional

import attr
import dateutil
import psycopg2

from swh.clearlydefined.mapping_utils import (
    AUTHORITY,
    FETCHER,
    MappingStatus,
    get_type_of_tool,
    map_row,
)
from swh.model.model import RawExtrinsicMetadata
from swh.storage.interface import StorageInterface


class Row:
    def __init__(self, path, metadata, date):
        self.path = path
        self.metadata = metadata
        self.date = date


def write_in_storage(
    storage: StorageInterface,
    metadata: RawExtrinsicMetadata,
) -> None:
    """
    Take storage and metadata as input
    and add metadata in storage
    """
    storage.raw_extrinsic_metadata_add([metadata])


def init_storage(storage: StorageInterface) -> None:
    """
    Take storage as input and add MetadataFetcher, MetadataAuthority inside storage
    """
    storage.metadata_authority_add([attr.evolve(AUTHORITY, metadata={})])
    storage.metadata_fetcher_add([attr.evolve(FETCHER, metadata={})])


def write_next_date(
    cursor, update_connection, previous_date: Optional[datetime], new_date: datetime
) -> None:
    """
    Take cursor, update_connection, previous_date, new_date as input
    and if it previous_date is None, then enter new_date, else
    update the date stored in table with new_date
    """
    if not previous_date:
        cursor.execute(
            """INSERT into clearcode_env (key, value) VALUES(%s,%s)""",
            ("date", new_date),
        )
    else:
        cursor.execute(
            """UPDATE clearcode_env SET value = %s WHERE key='date'""",
            (new_date,),
        )
    update_connection.commit()


def get_last_run_date(cursor) -> Optional[datetime]:
    """
    Take cursor as input and get last run date from which
    new rows will be orchestered, return None if it's first
    orchestration
    """
    cursor.execute("SELECT value FROM clearcode_env WHERE key='date';")
    rows = cursor.fetchall()
    if len(rows) < 1:
        return None
    date = rows[0][0]
    return dateutil.parser.isoparse(date)


def write_data_from_list(
    storage: StorageInterface, metadata_list: List[RawExtrinsicMetadata]
):
    """
    Take list of RawExtrinsicMetadata and
    write in storage
    """
    for data in metadata_list:
        write_in_storage(storage=storage, metadata=data)


def orchestrate_row(
    storage: StorageInterface, cursor, connection, row: Row
) -> Optional[bool]:
    """
    Take storage, cursor, connection, row as input
    and if able to completely map that row then write
    data in storage, else store the ID in unmapped_data
    table and return true if that row is fully mapped
    false for partial or no mapping
    """
    able_to_be_mapped = map_row(
        metadata=row.metadata, id=row.path, date=row.date, storage=storage
    )

    mapping_status, metadata_list = able_to_be_mapped

    if mapping_status == MappingStatus.IGNORE:
        return None

    elif mapping_status == MappingStatus.UNMAPPED:
        # This is a case when no metadata of row is not able to be mapped
        write_in_not_mapped(
            cd_path=row.path, cursor=cursor, write_connection=connection
        )
        write_data_from_list(storage=storage, metadata_list=metadata_list)
        return False

    else:
        # This is a case when partial metadata of that row is able to be mapped
        write_data_from_list(storage=storage, metadata_list=metadata_list)
        return True


def map_previously_unmapped_data(storage: StorageInterface, cursor, connection) -> None:
    """
    Take storage, cursor, connection as input and map previously
    unmapped data
    """
    cursor.execute("SELECT path FROM unmapped_data ;")
    rows = cursor.fetchall()
    for row in rows:
        cd_path = row[0]
        cursor.execute(
            """SELECT path,content,last_modified_date FROM
         clearcode_cditem WHERE path=%s;""",
            (cd_path,),
        )
        unmapped_row = cursor.fetchall()[0]
        if orchestrate_row(
            storage=storage,
            row=Row(
                path=unmapped_row[0], metadata=unmapped_row[1], date=unmapped_row[2]
            ),
            cursor=cursor,
            connection=connection,
        ):
            cursor.execute("DELETE FROM unmapped_data WHERE path=%s", (cd_path,))
            connection.commit()


def write_in_not_mapped(cursor, write_connection, cd_path: str) -> None:
    """
    Take cursor, write_connection, cd_path as input
    and write 'cd_path' if 'cd_path' does not exists
    inside unmapped_data
    """
    cursor.execute(
        "INSERT INTO unmapped_data (path) VALUES (%s) ON CONFLICT (path) DO NOTHING;",
        (cd_path,),
    )
    write_connection.commit()
    return


def read_from_clearcode_and_write_in_swh(
    storage: StorageInterface, cursor, connection, date: Optional[datetime]
) -> None:
    """
    Take storage, cursor, connection, date as input
    and read from clearcode database and write only
    the data that is discovered after 'date' in swh storage.
    'date' is the last discovery date of the object that was
    stored at the time of previous run.
    """
    if date:
        cursor.execute(
            "SELECT path,content,last_modified_date FROM clearcode_cditem "
            "WHERE last_modified_date < %s "
            "ORDER BY last_modified_date DESC;",
            (date,),
        )
    else:
        cursor.execute(
            """SELECT path,content,last_modified_date FROM clearcode_cditem
            ORDER BY last_modified_date DESC;"""
        )
    rows = cursor.fetchall()
    if len(rows) < 1:
        return
    new_date = rows[0][2]
    write_next_date(
        cursor=cursor,
        update_connection=connection,
        previous_date=date,
        new_date=new_date,
    )
    for row in rows:
        tool = get_type_of_tool(row[0]).value
        if tool == "fossology":
            pass
        else:
            orchestrate_row(
                storage=storage,
                cursor=cursor,
                connection=connection,
                row=Row(path=row[0], metadata=row[1], date=row[2]),
            )


def orchestrator(storage: StorageInterface, clearcode_dsn: str) -> None:
    """
    Take clearcode_dsn, swh_storage_backend_config as input
    and write data periodically from clearcode database to
    swh raw extrensic metadata
    """
    connection = psycopg2.connect(dsn=clearcode_dsn)
    cursor = connection.cursor()
    init_storage(storage=storage)
    map_previously_unmapped_data(storage=storage, cursor=cursor, connection=connection)
    date = get_last_run_date(cursor=cursor)
    read_from_clearcode_and_write_in_swh(
        storage=storage, cursor=cursor, connection=connection, date=date
    )
