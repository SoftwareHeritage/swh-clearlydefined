# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU Affero General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime
from enum import Enum
import gzip
import json
from typing import Any, Dict, List, Optional, Tuple

import attr

from swh.clearlydefined.error import (
    InvalidComponents,
    NoJsonExtension,
    RevisionNotFound,
    ToolNotFound,
    ToolNotSupported,
    WrongMetadata,
)
from swh.model.hashutil import hash_to_bytes, hash_to_hex
from swh.model.identifiers import parse_swhid
from swh.model.model import (
    MetadataAuthority,
    MetadataAuthorityType,
    MetadataFetcher,
    MetadataTargetType,
    Origin,
    RawExtrinsicMetadata,
)


class ToolType(Enum):
    """The type of content pointed to by a snapshot branch. Usually a
    revision or an alias."""

    DEFINITION = "definition"
    SCANCODE = "scancode"
    CLEARLYDEFINED = "clearlydefined"
    LICENSEE = "licensee"
    FOSSOLOGY = "fossology"


def map_row_data_with_metadata(
    swh_id: str,
    type: MetadataTargetType,
    origin: Optional[Origin],
    metadata: Dict,
    date: datetime,
    format: str,
) -> RawExtrinsicMetadata:
    """
    Take and data_list as input and write
    data inside RawExtrensicMetadata table inside
    swh storage
    """
    return RawExtrinsicMetadata(
        type=type,
        target=parse_swhid(swh_id),
        discovery_date=date,
        authority=attr.evolve(authority, metadata=None),
        fetcher=attr.evolve(fetcher, metadata=None),
        format=format,
        origin=origin.url if origin else None,
        metadata=json.dumps(metadata).encode("utf-8"),
    )


authority = MetadataAuthority(
    type=MetadataAuthorityType.REGISTRY,
    url="https://clearlydefined.io/",
    metadata={},
)


fetcher = MetadataFetcher(
    name="swh-clearlydefined",
    version="0.0.1",
    metadata={},
)


def map_sha1_with_swhid(storage, sha1: str) -> Optional[str]:
    """
    Take sha1 and storage as input and give the corresponding
    swhID for that sha1
    """
    if not sha1:
        return None
    content = storage.content_get([hash_to_bytes(sha1)])[0]
    if not content:
        return None
    sha1_git = hash_to_hex(content.sha1_git)
    swh_id = "swh:1:cnt:{sha1_git}".format(sha1_git=sha1_git)
    return swh_id


def sha1_git_in_revisions(storage, sha1_git: str) -> bool:
    """
    Take sha1_git and storage as input and
    tell whether that sha1_git exists in revision
    table
    """
    sha1_git_bytes = hash_to_bytes(sha1_git)
    missing_revision = storage.revision_missing([sha1_git_bytes])
    if len(list(missing_revision)) == 0:
        return True
    return False


def map_sha1_and_add_in_data(
    storage,
    sha1: Optional[str],
    data: List[RawExtrinsicMetadata],
    file: Dict,
    date: datetime,
    format: str,
    mapping_status=True,
) -> bool:
    """
    Take sha1, data, file, date, mapping_status as input
    and return whether the sha1 exists in content, if it exists
    map sha1 with swhid and push RawExtrensicMetadata object that got
    mapping row data with RawExtrensicMetadata
    """
    if sha1:
        assert isinstance(sha1, str)
        swh_id = map_sha1_with_swhid(storage=storage, sha1=sha1)
        if swh_id:
            data.append(
                map_row_data_with_metadata(
                    swh_id=swh_id,
                    type=MetadataTargetType.CONTENT,
                    origin=None,
                    metadata=file,
                    date=date,
                    format=format,
                )
            )
        else:
            mapping_status = False
    return mapping_status


def list_scancode_files(metadata_string: str) -> List[Tuple[str, Dict]]:
    """
    Returns (sha1, filename) pairs for each ScanCode metadata file
    referenced in the metadata_string.
    """
    metadata = json.loads(metadata_string)
    content = metadata.get("content") or {}
    files = content.get("files") or {}
    files_with_sha1 = []
    for file in files:
        sha1 = file.get("sha1")
        files_with_sha1.append((sha1, file))
    return files_with_sha1


def list_licensee_files(metadata_string: str) -> List[Tuple[str, Dict]]:
    """
    Returns (sha1, filename) pairs for each Licensee metadata file
    referenced in the metadata_string.
    """
    metadata = json.loads(metadata_string)
    licensee = metadata.get("licensee") or {}
    output = licensee.get("output") or {}
    content = output.get("content") or {}
    files = content.get("matched_files") or []
    files_with_sha1 = []
    for file in files:
        sha1 = file.get("content_hash")
        files_with_sha1.append((sha1, file))
    return files_with_sha1


def list_clearlydefined_files(metadata_string: str) -> List[Tuple[str, Dict]]:
    """
    Returns (sha1, filename) pairs for each ClearlyDefined metadata file
    referenced in the metadata_string.
    """
    metadata = json.loads(metadata_string)
    files = metadata.get("files") or []
    files_with_sha1 = []
    for file in files:
        hashes = file.get("hashes") or {}
        sha1 = hashes.get("sha1")
        assert sha1
        files_with_sha1.append((sha1, file))
    return files_with_sha1


def map_harvest(
    storage, tool: str, metadata_string: str, date: datetime
) -> Tuple[bool, List[RawExtrinsicMetadata]]:
    """
    Take tool, metadata_string and storage as input and try to
    map the sha1 of files with content, return status of
    harvest and data to be written in storage
    """
    tools = {
        "scancode": list_scancode_files,
        "licensee": list_licensee_files,
        "clearlydefined": list_clearlydefined_files,
    }
    formats = {
        "scancode": "clearlydefined-harvest-scancode-json",
        "licensee": "clearlydefined-harvest-licensee-json",
        "clearlydefined": "clearlydefined-harvest-clearlydefined-json",
    }

    format_ = formats[tool]

    mapping_status = True
    data: List[RawExtrinsicMetadata] = []
    for (sha1, file) in tools[tool](metadata_string):
        mapping_status = (
            map_sha1_and_add_in_data(storage, sha1, data, file, date, format_)
            and mapping_status
        )
    return mapping_status, data


def map_definition(
    storage, metadata_string: str, date: datetime
) -> Optional[Tuple[bool, List[RawExtrinsicMetadata]]]:
    """
    Take metadata_string and storage as input and try to
    map the sha1 of defintion with content/ gitSha in revision
    return None if not able to map
    else return data to be written in storage
    """
    metadata: Dict[str, Dict[str, Optional[Dict]]] = json.loads(metadata_string)
    described: Dict[str, Optional[Dict[str, Any]]] = metadata.get("described") or {}
    hashes: Dict[str, str] = described.get("hashes") or {}
    sha1_git = hashes.get("gitSha")
    source: Dict[str, str] = described.get("sourceLocation") or {}
    url = source.get("url")
    origin = None
    sha1 = hashes.get("sha1")
    if url:
        assert isinstance(url, str)
        origin = Origin(url=url)

    if sha1_git:
        assert isinstance(sha1_git, str)
        if not sha1_git_in_revisions(sha1_git=sha1_git, storage=storage):
            return None
        swh_id = "swh:1:rev:{sha1_git}".format(sha1_git=sha1_git)
        metadata_type = MetadataTargetType.REVISION

    elif sha1:
        assert isinstance(sha1, str)
        swh_id_sha1 = map_sha1_with_swhid(sha1=sha1, storage=storage)
        if not swh_id_sha1:
            return None
        assert isinstance(swh_id_sha1, str)
        swh_id = swh_id_sha1
        metadata_type = MetadataTargetType.CONTENT

    else:
        raise WrongMetadata("Wrong metadata")

    return True, [
        map_row_data_with_metadata(
            swh_id=swh_id,
            type=metadata_type,
            origin=origin,
            metadata=metadata,
            date=date,
            format="clearlydefined-definition-json",
        )
    ]


def get_type_of_tool(cd_path) -> ToolType:
    """
    Take cd_path as input if cd_path is invalid then raise exception,
    else return tyoe of tool of that row
    """
    list_cd_path = cd_path.split("/")
    # For example: maven/mavencentral/cobol-parser/abc/0.4.0.json
    if list_cd_path[4] != "revision":
        raise RevisionNotFound(
            "Not a supported/known ID, A valid ID should have"
            '5th component as "revision".'
        )
    # For example: maven/mavencentral/cobol-parser/revision/0.4.0.txt
    if not list_cd_path[-1].endswith(".json"):
        raise NoJsonExtension(
            'Not a supported/known ID, A valid ID should end with ".json" extension.'
        )
    # if the ID of row contains 9 components:
    # <package_manager>/<instance>/<namespace>/<name>/revision/<version>/tool/<tool_name>/<tool_version>.json
    # then it is a harvest
    if len(list_cd_path) == 9:
        # npm/npmjs/@ngtools/webpack/revision/10.2.1/abc/scancode/3.2.2.json
        if list_cd_path[6] != "tool":
            raise ToolNotFound(
                'Not a supported/known harvest ID, A valid harvest ID should have 7th\
                     component as "tool".'
            )
        tool = list_cd_path[7]
        # if the row contains an unknown tool
        if tool not in ("scancode", "licensee", "clearlydefined", "fossology"):
            raise ToolNotSupported(f"Tool for this ID {cd_path} is not supported")
        return ToolType(tool)
    elif len(list_cd_path) == 6:
        return ToolType.DEFINITION
    # For example: maven/mavencentral/cobol-parser/abc/revision/def/0.4.0.json
    raise InvalidComponents(
        "Not a supported/known ID, A valid ID should have 6 or 9 components."
    )


def map_row(
    storage, metadata: bytes, id: str, date: datetime
) -> Optional[Tuple[bool, List[RawExtrinsicMetadata]]]:
    """
    Take row and storage as input and try to map that row,
    if ID of row is invalid then raise exception,
    if not able to map that row, then return None
    else return status of that row and data to be written
    in storage
    """
    tool = get_type_of_tool(id).value

    # if the row doesn't contain any information in metadata return None so it can be
    # mapped later on
    metadata_string = gzip.decompress(metadata).decode()
    if metadata_string == "":
        return None

    if tool == "definition":
        return map_definition(
            metadata_string=metadata_string, storage=storage, date=date
        )

    else:
        return map_harvest(
            tool=tool,
            metadata_string=metadata_string,
            storage=storage,
            date=date,
        )
