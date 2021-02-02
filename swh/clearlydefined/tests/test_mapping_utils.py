# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU Affero General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.clearlydefined.mapping_utils import map_sha1_with_swhid
from swh.clearlydefined.mapping_utils import map_row
from swh.clearlydefined.mapping_utils import map_definition
from swh.clearlydefined.error import (
    InvalidComponents,
    WrongMetadata,
    NoJsonExtension,
    RevisionNotFound,
    ToolNotSupported,
    ToolNotFound,
)

from swh.model import from_disk
from swh.model.model import (
    MetadataTargetType,
    Origin,
    Content,
    Revision,
    Person,
    TimestampWithTimezone,
    Timestamp,
    RevisionType,
    Directory,
    DirectoryEntry,
)
from swh.model.hashutil import hash_to_bytes

import gzip
import os
from typing import Tuple
import pytest


content_data = [
    Content.from_data(b"42\n"),
    Content.from_data(b"4242\n"),
]

directory = Directory(
    id=hash_to_bytes("5256e856a0a0898966d6ba14feb4388b8b82d302"),
    entries=tuple(
        [
            DirectoryEntry(
                name=b"foo",
                type="file",
                target=content_data[0].sha1_git,
                perms=from_disk.DentryPerms.content,
            ),
        ],
    ),
)

revision_data = [
    Revision(
        id=hash_to_bytes("4c66129b968ab8122964823d1d77677f50884cf6"),
        message=b"hello",
        author=Person(
            name=b"Nicolas Dandrimont",
            email=b"nicolas@example.com",
            fullname=b"Nicolas Dandrimont <nicolas@example.com> ",
        ),
        date=TimestampWithTimezone(
            timestamp=Timestamp(seconds=1234567890, microseconds=0),
            offset=120,
            negative_utc=False,
        ),
        committer=Person(
            name=b"St\xc3fano Zacchiroli",
            email=b"stefano@example.com",
            fullname=b"St\xc3fano Zacchiroli <stefano@example.com>",
        ),
        committer_date=TimestampWithTimezone(
            timestamp=Timestamp(seconds=1123456789, microseconds=0),
            offset=120,
            negative_utc=False,
        ),
        parents=(),
        type=RevisionType.GIT,
        directory=directory.id,
        metadata={
            "checksums": {
                "sha1": "tarball-sha1",
                "sha256": "tarball-sha256",
            },
            "signed-off-by": "some-dude",
        },
        extra_headers=(
            (b"gpgsig", b"test123"),
            (b"mergetag", b"foo\\bar"),
            (b"mergetag", b"\x22\xaf\x89\x80\x01\x00"),
        ),
        synthetic=True,
    ),
    Revision(
        id=hash_to_bytes("3c66129b968ab8122964823d1d77677f50884cf6"),
        message=b"hello again",
        author=Person(
            name=b"Roberto Dicosmo",
            email=b"roberto@example.com",
            fullname=b"Roberto Dicosmo <roberto@example.com>",
        ),
        date=TimestampWithTimezone(
            timestamp=Timestamp(
                seconds=1234567843,
                microseconds=220000,
            ),
            offset=-720,
            negative_utc=False,
        ),
        committer=Person(
            name=b"tony",
            email=b"ar@dumont.fr",
            fullname=b"tony <ar@dumont.fr>",
        ),
        committer_date=TimestampWithTimezone(
            timestamp=Timestamp(
                seconds=1123456789,
                microseconds=220000,
            ),
            offset=0,
            negative_utc=False,
        ),
        parents=(),
        type=RevisionType.GIT,
        directory=directory.id,
        metadata=None,
        extra_headers=(),
        synthetic=False,
    ),
]


def make_row(id: str, text: str) -> Tuple[str, bytes]:
    """
    Take id and text as input and return a
    row like a row present in
    clearcode toolkit database
    """
    row = (id, gzip.compress(text.encode()))
    return row


def file_data(file_name):
    with open(file_name) as file:
        data = file.read()
        return data


def add_content_data(swh_storage):
    swh_storage.content_add(content_data)


def add_revision_data(swh_storage):
    swh_storage.revision_add(revision_data)


def test_mapping_sha1_with_swhID(swh_storage):
    add_content_data(swh_storage)
    sha1 = "34973274ccef6ab4dfaaf86599792fa9c3fe4689"
    assert "swh:1:cnt:d81cc0710eb6cf9efd5b920a8453e1e07157b6cd" == map_sha1_with_swhid(
        sha1=sha1, storage=swh_storage
    )


def test_mapping_with_empty_sha1(swh_storage):
    add_content_data(swh_storage)
    sha1 = ""
    assert map_sha1_with_swhid(sha1=sha1, storage=swh_storage) is None


def test_mapping_with_wrong_sha1(swh_storage):
    add_content_data(swh_storage)
    sha1 = "6ac599151a7aaa8ca5d38dc5bb61b49193a3cadc1ed33de5a57e4d1ecc53c846"
    assert map_sha1_with_swhid(sha1=sha1, storage=swh_storage) is None


def test_map_row_for_definitions_with_sha1(swh_storage, datadir):
    add_content_data(swh_storage)
    row = make_row(
        id="maven/mavencentral/za.co.absa.cobrix/cobol-parser/revision/0.4.0.json",
        text=file_data(os.path.join(datadir, "definitions.json")),
    )
    expected = (
        True,
        [
            (
                "swh:1:cnt:d81cc0710eb6cf9efd5b920a8453e1e07157b6cd",
                MetadataTargetType.CONTENT,
                Origin(
                    url="http://central.maven.org/maven2/za/co/absa/cobrix/"
                    "cobol-parser/0.4.0/cobol-parser-0.4.0-sources.jar"
                ),
            )
        ],
    )
    assert map_row(storage=swh_storage, row=row) == expected


def test_map_row_for_definitions_with_gitsha1(swh_storage, datadir):
    add_revision_data(swh_storage)
    row = make_row(
        id="maven/mavencentral/za.co.absa.cobrix/cobol-parser/revision/0.4.0.json",
        text=file_data(os.path.join(datadir, "definitions_sha1git.json")),
    )
    expected = (
        True,
        [
            (
                "swh:1:rev:4c66129b968ab8122964823d1d77677f50884cf6",
                MetadataTargetType.REVISION,
                Origin(
                    url="http://central.maven.org/maven2/za/co/absa/cobrix/"
                    "cobol-parser/0.4.0/cobol-parser-0.4.0-sources.jar"
                ),
            )
        ],
    )
    assert map_row(storage=swh_storage, row=row) == expected


def test_map_row_for_scancode(swh_storage, datadir):
    add_content_data(swh_storage)
    row = make_row(
        id="npm/npmjs/@ngtools/webpack/revision/10.2.1/tool/scancode/3.2.2.json",
        text=file_data(os.path.join(datadir, "scancode.json")),
    )
    expected = (
        False,
        [
            (
                "swh:1:cnt:d81cc0710eb6cf9efd5b920a8453e1e07157b6cd",
                MetadataTargetType.CONTENT,
                None,
            )
        ],
    )
    assert map_row(storage=swh_storage, row=row) == expected


def test_map_row_for_scancode_true_mapping_status(swh_storage, datadir):
    add_content_data(swh_storage)
    row = make_row(
        id="npm/npmjs/@ngtools/webpack/revision/10.2.1/tool/scancode/3.2.2.json",
        text=file_data(os.path.join(datadir, "scancode_true.json")),
    )
    expected = (
        True,
        [
            (
                "swh:1:cnt:d81cc0710eb6cf9efd5b920a8453e1e07157b6cd",
                MetadataTargetType.CONTENT,
                None,
            )
        ],
    )
    assert map_row(storage=swh_storage, row=row) == expected


def test_map_row_for_licensee(swh_storage, datadir):
    add_content_data(swh_storage)
    row = make_row(
        id="npm/npmjs/@fluidframework/replay-driver/revision/0.31.0/tool/licensee/\
            9.13.0.json",
        text=file_data(os.path.join(datadir, "licensee.json")),
    )
    expected = (
        False,
        [
            (
                "swh:1:cnt:36fade77193cb6d2bd826161a0979d64c28ab4fa",
                MetadataTargetType.CONTENT,
                None,
            )
        ],
    )
    assert map_row(storage=swh_storage, row=row) == expected


def test_map_row_for_licensee_true_mapping_status(swh_storage, datadir):
    add_content_data(swh_storage)
    row = make_row(
        id="npm/npmjs/@fluidframework/replay-driver/revision/0.31.0/tool/licensee/\
            9.13.0.json",
        text=file_data(os.path.join(datadir, "licensee_true.json")),
    )
    expected = (
        True,
        [
            (
                "swh:1:cnt:36fade77193cb6d2bd826161a0979d64c28ab4fa",
                MetadataTargetType.CONTENT,
                None,
            )
        ],
    )
    assert map_row(storage=swh_storage, row=row) == expected


def test_map_row_for_clearlydefined(swh_storage, datadir):
    add_content_data(swh_storage)
    row = make_row(
        id="npm/npmjs/@pixi/mesh-extras/revision/5.3.5/tool/clearlydefined/1.3.4.json",
        text=file_data(os.path.join(datadir, "clearlydefined.json")),
    )
    expected = (
        False,
        [
            (
                "swh:1:cnt:36fade77193cb6d2bd826161a0979d64c28ab4fa",
                MetadataTargetType.CONTENT,
                None,
            )
        ],
    )
    map_row(storage=swh_storage, row=row) == expected


def test_map_row_for_clearlydefined_true_mapping_status(swh_storage, datadir):
    add_content_data(swh_storage)
    row = make_row(
        id="npm/npmjs/@pixi/mesh-extras/revision/5.3.5/tool/clearlydefined/1.3.4.json",
        text=file_data(os.path.join(datadir, "clearlydefined_true.json")),
    )
    expected = (
        True,
        [
            (
                "swh:1:cnt:36fade77193cb6d2bd826161a0979d64c28ab4fa",
                MetadataTargetType.CONTENT,
                None,
            )
        ],
    )
    map_row(storage=swh_storage, row=row) == expected


def test_sha1git_not_in_revision(swh_storage, datadir):
    add_revision_data(swh_storage)
    assert (
        map_definition(
            metadata_string=file_data(
                os.path.join(datadir, "definitions_not_mapped_sha1_git.json")
            ),
            storage=swh_storage,
        )
        is None
    )


def test_sha1_not_in_content(swh_storage, datadir):
    add_content_data(swh_storage)
    assert (
        map_definition(
            metadata_string=file_data(
                os.path.join(datadir, "definitions_not_mapped.json")
            ),
            storage=swh_storage,
        )
        is None
    )


def test_map_definition_with_wrong_metadata(swh_storage, datadir):
    with pytest.raises(WrongMetadata):
        map_definition(
            metadata_string=file_data(os.path.join(datadir, "licensee.json")),
            storage=swh_storage,
        )


def test_map_row_with_invalid_ID(swh_storage):
    row = make_row(
        id="maven/mavencentral/cobol-parser/abc/revision/def/0.4.0.json", text="abc"
    )
    with pytest.raises(InvalidComponents):
        map_row(storage=swh_storage, row=row)


def test_map_row_with_empty_metadata_string(swh_storage):
    row = make_row(
        id="maven/mavencentral/za.co.absa.cobrix/cobol-parser/revision/0.4.0.json",
        text="",
    )
    assert map_row(storage=swh_storage, row=row) is None


def test_map_row_with_invalid_ID_without_revision(swh_storage):
    row = make_row(
        id="maven/mavencentral/za.co.absa.cobrix/cobol-parser/abc/0.4.0.json",
        text="abc",
    )
    with pytest.raises(RevisionNotFound):
        map_row(storage=swh_storage, row=row)


def test_map_row_with_invalid_ID_without_json_extension(swh_storage):
    row = make_row(
        id="maven/mavencentral/za.co.absa.cobrix/cobol-parser/revision/0.4.0.txt",
        text="abc",
    )
    with pytest.raises(NoJsonExtension):
        map_row(storage=swh_storage, row=row)


def test_map_row_with_invalid_ID_without_6_or_9_length(swh_storage):
    row = make_row(
        id="npm/npmjs/@ngtools/webpack/revision/10.2.1/tool/3.2.2.json", text="abc"
    )
    with pytest.raises(InvalidComponents):
        map_row(storage=swh_storage, row=row)


def test_map_row_with_invalid_tool(swh_storage):
    row = make_row(
        id="npm/npmjs/@ngtools/webpack/revision/10.2.1/tool/abc/3.2.2.json",
        text="abc",
    )
    with pytest.raises(ToolNotSupported):
        map_row(storage=swh_storage, row=row)


def test_map_row_with_invalid_harvest_ID(swh_storage):
    row = make_row(
        id="npm/npmjs/@ngtools/webpack/revision/10.2.1/abc/scancode/3.2.2.json",
        text="abc",
    )
    with pytest.raises(ToolNotFound):
        map_row(storage=swh_storage, row=row)
