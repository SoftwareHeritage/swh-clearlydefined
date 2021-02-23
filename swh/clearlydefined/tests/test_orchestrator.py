# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU Affero General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime
from datetime import timezone
import gzip
import os
from typing import List, Optional, Tuple
import uuid

import psycopg2

from swh.clearlydefined.orchestrator import get_last_run_date, orchestrator
from swh.model.model import Content

content_data = [
    Content.from_data(b"42\n"),
    Content.from_data(b"4242\n"),
]


def add_content_data(swh_storage):
    swh_storage.content_add(content_data)


def file_data(file_name: str) -> str:
    with open(file_name) as file:
        return file.read()


def gzip_compress_data(filename: Optional[str], datadir) -> bytes:
    """
    Take filename as input
    and return gzip compressed
    data for that filename
    """
    if not filename:
        return gzip.compress("".encode("utf-8"), compresslevel=9)
    else:
        return gzip.compress(
            file_data(os.path.join(datadir, filename)).encode("utf-8"), compresslevel=9
        )


def fill_rows_in_table(
    rows: List[Tuple[str, bytes, datetime, datetime, str]], cursor, connection
):
    """
    Take rows as input and store
    those rows in clearcode_cditem table
    """
    for row in rows:
        cursor.execute(
            """INSERT INTO clearcode_cditem (path, content, last_modified_date,
                last_map_date, map_error, uuid) VALUES (%s, %s, %s, %s, %s, %s);""",
            (
                *row,
                uuid.uuid4(),
            ),
        )
    connection.commit()


def fill_data_before_updation_of_storage(connection, cursor, datadir):
    rows = [
        (
            "maven/mavencentral/za.co.absa.cobrix/cobol-parser/revision/0.4.0.json",
            gzip_compress_data("definitions.json", datadir=datadir),
            datetime(year=2021, month=2, day=1, tzinfo=timezone.utc),
            datetime(year=2021, month=2, day=1, tzinfo=timezone.utc),
            "",
        ),
        (
            "npm/npmjs/@ngtools/webpack/revision/10.2.1/tool/scancode/" "3.2.2.json",
            gzip_compress_data("scancode_true.json", datadir=datadir),
            datetime(year=2021, month=2, day=2, tzinfo=timezone.utc),
            datetime(year=2021, month=2, day=2, tzinfo=timezone.utc),
            "",
        ),
        (
            "npm/npmjs/@fluidframework/replay-driver/revision/0.31.0/tool/licensee/"
            "9.13.0.json",
            gzip_compress_data("licensee_true.json", datadir=datadir),
            datetime(year=2021, month=2, day=3,tzinfo=timezone.utc),
            datetime(year=2021, month=2, day=3,tzinfo=timezone.utc),
            "",
        ),
        (
            "npm/npmjs/@pixi/mesh-extras/revision/5.3.5/tool/clearlydefined/1.3.4.json",
            gzip_compress_data("clearlydefined_true.json", datadir=datadir),
            datetime(year=2021, month=2, day=4,tzinfo=timezone.utc),
            datetime(year=2021, month=2, day=4,tzinfo=timezone.utc),
            "",
        ),
        (
            "maven/mavencentral/za.co.absa.cobrix/cobol/revision/0.4.0.json",
            gzip_compress_data("def_not_mapped.json", datadir=datadir),
            datetime(year=2021, month=2, day=5,tzinfo=timezone.utc),
            datetime(year=2021, month=2, day=5,tzinfo=timezone.utc),
            "",
        ),
        (
            "npm/npmjs/@pixi/mesh-extras/revision/5.3.6/tool/clearlydefined/1.3.4.json",
            gzip_compress_data("clearydefined_not_mapped.json", datadir=datadir),
            datetime(year=2021, month=2, day=6,tzinfo=timezone.utc),
            datetime(year=2021, month=2, day=6,tzinfo=timezone.utc),
            "",
        ),
        (
            "npm/npmjs/@pixi/mesh-extras/revision/5.3.5/tool/fossology/1.3.4.json",
            gzip_compress_data(None, datadir=datadir),
            datetime(year=2021, month=2, day=1,tzinfo=timezone.utc),
            datetime(year=2021, month=2, day=1,tzinfo=timezone.utc),
            "",
        ),
    ]
    fill_rows_in_table(rows=rows, cursor=cursor, connection=connection)


def fill_data_after_updation_of_storage(connection, cursor, datadir):
    rows = [
        (
            "maven/mavencentral/cobrix/cobol-parser/revision/0.4.0.json",
            gzip_compress_data(None, datadir=datadir),
            datetime(year=2021, month=2, day=1,tzinfo=timezone.utc),
            datetime(year=2021, month=2, day=8,tzinfo=timezone.utc),
            "",
        ),
    ]
    fill_rows_in_table(rows=rows, cursor=cursor, connection=connection)


def get_length_of_unmapped_data(connection, cursor) -> int:
    cursor.execute("SELECT COUNT(*) FROM unmapped_data")
    count = cursor.fetchall()[0][0]
    return count


def test_orchestrator(swh_storage, clearcode_dsn, datadir):
    connection = psycopg2.connect(dsn=clearcode_dsn)
    cursor = connection.cursor()
    add_content_data(swh_storage)
    # Fill data in clearcode database, for first time orchestration
    fill_data_before_updation_of_storage(
        connection=connection, cursor=cursor, datadir=datadir
    )
    orchestrator(storage=swh_storage, clearcode_dsn=clearcode_dsn)
    # Check how much data is unmapped after first orchestration
    assert 2 == get_length_of_unmapped_data(connection=connection, cursor=cursor)
    assert datetime(2021, 2, 6, 0, 0, tzinfo=timezone.utc) == get_last_run_date(
        cursor=cursor
    )
    content_data.extend(
        [Content.from_data(b"424242\n"), Content.from_data(b"42424242\n")]
    )
    add_content_data(swh_storage)
    # Run orchestration after insertion in swh storage and
    # check how much data is unmapped after second orchestration
    orchestrator(storage=swh_storage, clearcode_dsn=clearcode_dsn)
    assert 0 == get_length_of_unmapped_data(connection=connection, cursor=cursor)
    fill_data_after_updation_of_storage(
        connection=connection, cursor=cursor, datadir=datadir
    )
    # Fill new data in clearcode database and
    # check how much data is unmapped after second orchestration
    orchestrator(storage=swh_storage, clearcode_dsn=clearcode_dsn)
    assert 1 == get_length_of_unmapped_data(connection=connection, cursor=cursor)
    # Check how much data is unmapped when archive was not updated
    orchestrator(storage=swh_storage, clearcode_dsn=clearcode_dsn)
    assert 1 == get_length_of_unmapped_data(connection=connection, cursor=cursor)
