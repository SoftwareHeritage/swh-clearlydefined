# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU Affero General Public License version 3, or any later version
# See top-level LICENSE file for more information

import tempfile

from click.testing import CliRunner
import yaml

from swh.clearlydefined.cli import clearlydefined as cli


def test_orchestration_from_cli(swh_storage_backend_config, clearcode_dsn):
    config = {"storage": swh_storage_backend_config}
    with tempfile.NamedTemporaryFile("a", suffix=".yml") as config_fd:
        yaml.dump(config, config_fd)
        config_fd.seek(0)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["-C", config_fd.name, "--clearcode-dsn", clearcode_dsn, "fill_storage"],
        )
        assert result.exit_code == 0


def test_cli_with_config_without_storage(swh_storage_backend_config, clearcode_dsn):
    runner = CliRunner()
    result = runner.invoke(cli, ["--clearcode-dsn", clearcode_dsn, "fill_storage"],)
    assert result.exit_code == 2
