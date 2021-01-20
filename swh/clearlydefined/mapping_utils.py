# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU Affero General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Optional

from swh.model.hashutil import hash_to_bytes
from swh.model.hashutil import hash_to_hex
import psycopg2


def map_sha1_with_swhid(sha1: str, dsn: str) -> Optional[str]:
    """
    Take sha1 and dsn as input and give the corresponding
    swhID for that sha1
    """
    if not sha1:
        return None
    read_connection = psycopg2.connect(dsn=dsn)
    cur = read_connection.cursor()
    sha1 = hash_to_bytes(sha1)
    cur.execute("SELECT sha1_git FROM content where sha1= %s;", (sha1,))
    sha1_git_tuple_data = cur.fetchall()
    if len(sha1_git_tuple_data) == 0:
        return None
    sha1_git = hash_to_hex(sha1_git_tuple_data[0][0])
    swh_id = "swh:1:cnt:{sha1_git}".format(sha1_git=sha1_git)
    return swh_id
