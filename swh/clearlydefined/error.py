# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU Affero General Public License version 3, or any later version
# See top-level LICENSE file for more information


class InvalidComponents(Exception):
    """
    Raise this when ID has invalid components
    For example: maven/mavencentral/cobol-parser/abc/revision/def/0.4.0.json
    """

    pass


class RevisionNotFound(Exception):
    """
    Raise this when ID does not has revision component at the expected place
    For example: maven/mavencentral/cobol-parser/abc/0.4.0.json
    """

    pass


class WrongMetadata(Exception):
    """
    Raise this when tried to process invalid metadata
    """

    pass


class NoJsonExtension(Exception):
    """
    Raise this when ID does not have .json extension at end
    For example: maven/mavencentral/cobol-parser/revision/0.4.0.txt
    """

    pass


class ToolNotFound(Exception):
    """
    Raise this when ID does not have revision component at the expected place
    For example: npm/npmjs/@ngtools/webpack/revision/10.2.1/abc/scancode/3.2.2.json
    """

    pass


class ToolNotSupported(Exception):
    """
    Raise this when ID contains an unknown tool
    For example: npm/npmjs/@ngtools/webpack/revision/10.2.1/tool/newtool/3.2.2.json
    """

    pass
