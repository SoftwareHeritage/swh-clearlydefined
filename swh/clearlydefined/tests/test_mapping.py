# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU Affero General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.clearlydefined.mapping_utils import map_sha1_with_swhid
import psycopg2


def add_data(dsn: str):
    write_connection = psycopg2.connect(dsn=dsn)
    cur = write_connection.cursor()
    data = [
        {
            "sha1": "\\xa6628c8a4fbc08c29b8472e2222975e5b9918131",
            "sha1_git": "\\xe103b11cbfecbc116dacbb1f9ab2a02176092a32",
            "sha256": (
                "\\x6ac599151a7aaa8ca5d38dc5bb61b49193a3cadc1ed33de5a57e4d1ecc53c846"
            ),
            "blake2s256": (
                "\\xc509b320abede3580bb1de75a0efa09ba7416db9c8de845a4e1b4317c0b8a8d9"
            ),
            "length": 717,
        },
        {
            "sha1": "\\xd1ece3dbe3e78a6648f37206f996e202acb3926b",
            "sha1_git": "\\x095b80e14c3ea6254f57e94761f2313e32b1d58a",
            "sha256": (
                "\\x2a24791d738e4380d55e1c990dd0bd2bcdc98240d9a25c488804abfd814b8c96"
            ),
            "blake2s256": (
                "\\xa18463fe94e1b4ee191815c2fa48948c44ffbdffcda49fad6591ac4c93f19aef"
            ),
            "length": 3138,
        },
    ]
    for row in data:
        cur.execute(
            "INSERT INTO content (sha1, sha1_git, sha256, blake2s256, length) VALUES \
                (%s,%s,%s,%s,%s);",
            (
                row["sha1"],
                row["sha1_git"],
                row["sha256"],
                row["blake2s256"],
                row["length"],
            ),
        )
        write_connection.commit()


def test_mapping(swh_storage_backend_config):
    dsn = swh_storage_backend_config["db"]
    add_data(dsn=dsn)
    sha1 = "a6628c8a4fbc08c29b8472e2222975e5b9918131"
    assert "swh:1:cnt:e103b11cbfecbc116dacbb1f9ab2a02176092a32" == map_sha1_with_swhid(
        sha1=sha1, dsn=dsn
    )


def test_mapping_with_empty_sha1(swh_storage_backend_config):
    dsn = swh_storage_backend_config["db"]
    add_data(dsn=dsn)
    sha1 = ""
    assert map_sha1_with_swhid(sha1=sha1, dsn=dsn) is None


def test_mapping_with_wrong_sha1(swh_storage_backend_config):
    dsn = swh_storage_backend_config["db"]
    add_data(dsn=dsn)
    sha1 = "6ac599151a7aaa8ca5d38dc5bb61b49193a3cadc1ed33de5a57e4d1ecc53c846"
    assert map_sha1_with_swhid(sha1=sha1, dsn=dsn) is None
