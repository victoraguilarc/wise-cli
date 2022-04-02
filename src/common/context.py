from dataclasses import dataclass

from fabric import Connection

from src.commands.config import ProjectConfig


@dataclass
class CommandContext(object):
    connection: Connection
    config: ProjectConfig
