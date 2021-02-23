# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU Affero General Public License version 3, or any later version
# See top-level LICENSE file for more information

from os import environ, path

import pytest

import swh.clearlydefined
from swh.core.db.pytest_plugin import postgresql_fact

SQL_DIR = path.join(path.dirname(swh.clearlydefined.__file__), "sql")

environ["LC_ALL"] = "C.UTF-8"
pytest_plugins = ["swh.storage.pytest_plugin"]

swh_clearcode = postgresql_fact(
    "postgresql_proc", db_name="clearcode", dump_files=path.join(SQL_DIR, "*.sql")
)


@pytest.fixture
def clearcode_dsn(swh_clearcode):
    """Basic pg storage configuration with no journal collaborator
    (to avoid pulling optional dependency on clients of this fixture)

    """
    clearcode_dsn = swh_clearcode.dsn
    return clearcode_dsn
