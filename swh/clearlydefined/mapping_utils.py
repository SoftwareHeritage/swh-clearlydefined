# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU Affero General Public License version 3, or any later version
# See top-level LICENSE file for more information

from datetime import datetime
from enum import Enum
import gzip
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from swh.clearlydefined.error import (
    InvalidComponents,
    NoJsonExtension,
    RevisionNotFound,
    ToolNotFound,
    ToolNotSupported,
)
from swh.model.hashutil import hash_to_bytes
from swh.model.swhids import ExtendedSWHID, ExtendedObjectType
from swh.model.model import (
    MetadataAuthority,
    MetadataAuthorityType,
    MetadataFetcher,
    Origin,
    RawExtrinsicMetadata,
)


class ToolType(Enum):
    """The type of a row"""

    DEFINITION = "definition"
    SCANCODE = "scancode"
    CLEARLYDEFINED = "clearlydefined"
    LICENSEE = "licensee"
    FOSSOLOGY = "fossology"


class MappingStatus(Enum):
    """The type of mapping status of a row"""

    MAPPED = "mapped"
    UNMAPPED = "unmapped"
    IGNORE = "ignore"


AUTHORITY = MetadataAuthority(
    type=MetadataAuthorityType.REGISTRY,
    url="https://clearlydefined.io/",
    metadata=None,
)


FETCHER = MetadataFetcher(name="swh-clearlydefined", version="0.0.1", metadata=None,)


def is_sha1(s):
    return bool(re.match("^[a-fA-F0-9]{40}$", s))


def map_row_data_with_metadata(
    target: ExtendedSWHID,
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
        target=target,
        discovery_date=date,
        authority=AUTHORITY,
        fetcher=FETCHER,
        format=format,
        origin=origin.url if origin else None,
        metadata=json.dumps(metadata).encode("utf-8"),
    )


def map_sha1_with_swhid(storage, sha1: str) -> Optional[ExtendedSWHID]:
    """
    Take sha1 and storage as input and give the corresponding
    swhID for that sha1
    """
    if not sha1:
        return None
    content = storage.content_get([hash_to_bytes(sha1)])[0]
    if not content:
        return None
    return ExtendedSWHID(
        object_type=ExtendedObjectType.CONTENT, object_id=content.sha1_git
    )


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
        swhid = map_sha1_with_swhid(storage=storage, sha1=sha1)
        if swhid:
            data.append(
                map_row_data_with_metadata(
                    target=swhid, origin=None, metadata=file, date=date, format=format,
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
) -> Tuple[MappingStatus, List[RawExtrinsicMetadata]]:
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
    status = MappingStatus.UNMAPPED
    if mapping_status:
        status = MappingStatus.MAPPED
    return status, data


def map_definition(
    storage, metadata_string: str, date: datetime
) -> Tuple[MappingStatus, List[RawExtrinsicMetadata]]:
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
    if url:
        assert isinstance(url, str)
        origin = Origin(url=url)

    if not sha1_git:
        sha1_git = source.get("revision")

    if sha1_git:
        assert isinstance(sha1_git, str)
        if not is_sha1(sha1_git):
            return MappingStatus.IGNORE, []
        if not sha1_git_in_revisions(sha1_git=sha1_git, storage=storage):
            return MappingStatus.UNMAPPED, []
        swhid = ExtendedSWHID(
            object_type=ExtendedObjectType.REVISION, object_id=hash_to_bytes(sha1_git)
        )

    else:
        return MappingStatus.IGNORE, []

    return (
        MappingStatus.MAPPED,
        [
            map_row_data_with_metadata(
                target=swhid,
                origin=origin,
                metadata=metadata,
                date=date,
                format="clearlydefined-definition-json",
            )
        ],
    )


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
) -> Tuple[MappingStatus, List[RawExtrinsicMetadata]]:
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
        return MappingStatus.UNMAPPED, []

    if tool == "definition":
        return map_definition(
            metadata_string=metadata_string, storage=storage, date=date
        )

    else:
        return map_harvest(
            tool=tool, metadata_string=metadata_string, storage=storage, date=date,
        )
