# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU Affero General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os

import click

from swh.clearlydefined.orchestrator import orchestrator
from swh.core.cli import CONTEXT_SETTINGS
from swh.core.cli import swh as swh_cli_group
from swh.storage import get_storage


@swh_cli_group.group(name="clearlydefined", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--config-file",
    "-C",
    default=None,
    type=click.Path(exists=True, dir_okay=False,),
    help="SWH storage config.",
)
@click.option("--clearcode-dsn", default=None, type=click.STRING, help="Clearcode DSN.")
@click.pass_context
def clearlydefined(ctx, config_file, clearcode_dsn):
    """Software Heritage Clearlydefined Metadata Fetcher"""
    from swh.core import config

    if config_file:
        if not os.path.exists(config_file):
            raise ValueError("%s does not exist" % config_file)
        conf = config.read(config_file)
    else:
        conf = {}

    if "storage" not in conf:
        ctx.fail("You must have a storage configured in your config file.")

    ctx.ensure_object(dict)
    ctx.obj["config"] = conf
    ctx.obj["dsn"] = clearcode_dsn


@clearlydefined.command(name="fill_storage")
@click.pass_context
def run_orchestration(ctx):
    print(ctx.obj["config"]["storage"])
    storage = get_storage(**ctx.obj["config"]["storage"])
    clearcode_dsn = ctx.obj["dsn"]
    orchestrator(storage=storage, clearcode_dsn=clearcode_dsn)
