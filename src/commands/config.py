# -*- coding: utf-8 -*-

import json
from dataclasses import dataclass

from contextlib import contextmanager
from typing import Optional

from src.commands.enums import WebServer, Database, Deployment
from src.constants import CONFIG_FILE_NAME, SHARED_GROUP, HOME_BASE_PATH


@dataclass
class ProjectConfig(object):
    project_name: str
    password: str
    domain: str
    ipv4: str
    https: bool = False
    superuser: Optional[str] = None
    project_user: Optional[str] = None
    project_group: Optional[str] = None
    project_path: Optional[str] = None
    sshkey: str = '~/.ssh/id_rsa.pub'
    email: Optional[str] = 'team@xiberty.com'
    deployment: Deployment = Deployment.VIRTUALENV
    db_engine: Database = Database.POSTGRESQL
    web_server: WebServer = WebServer.NGINX
    port: int = 22

    @classmethod
    def build(cls, data: dict) -> 'ProjectConfig':
        return cls(
            project_name=data.get('project_name'),
            password=data.get('password'),
            domain=data.get('domain'),
            ipv4=data.get('ipv4'),
            db_engine=Database.from_value(
                data.get('db_engine', str(Database.POSTGRESQL)),
            ),
            web_server=WebServer.from_value(
                data.get('web_server', str(WebServer.NGINX)),
            ),
            https=data.get('https', False),
            superuser=data.get('superuser'),
            port=data.get('port', 22),
            sshkey=data.get('sshkey', '~/.ssh/id_rsa.pub'),
        )


def validate_config(config_json):
    pass


@contextmanager
def load_settings():
    config_file = open(CONFIG_FILE_NAME, 'r')
    config_json = json.load(config_file)
    validate_config(config_json)
    project_name = config_json.pop('project')
    config = ProjectConfig.build(config_json)
    config.project_name = project_name
    config.project_user = '{0}'.format(config.project_name)
    config.project_group = '{0}'.format(SHARED_GROUP)
    config.project_path = '{0}/{1}'.format(HOME_BASE_PATH, config.project_user)
    yield config


