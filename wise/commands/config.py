# -*- coding: utf-8 -*-

import sys
import json

from io import StringIO
from contextlib import contextmanager
from wise.commands.utils import BaseEnum
from jinja2 import Environment, PackageLoader, select_autoescape


class Template(StringIO):

    def __init__(self, name: str, context: dict):
        content = self.render(name, context)
        self.name = name
        super().__init__(content)

    def render(self, name, context=None):
        context = context or {}
        env = Environment(
            loader=PackageLoader('wise', 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template(name)
        return template.render(**context)

    def upload(self, connection, remote):
        tmp_file = '/tmp/{0}'.format(self.name)
        connection.put(local=self, remote=tmp_file)
        connection.sudo('mv {0} {1}'.format(tmp_file, remote))


class ServerOS(BaseEnum):
    UBUNTU_XENIAL = 'ubuntu_xenial'
    UBUNTU_BIONIC = 'ubuntu_bionic'
    CENTOS_7 = 'centos_7'
    CORE_OS = 'core_os'


class Deployment(BaseEnum):
    DOCKER = 'docker'
    VIRTUALENV = 'virtualenv'


class WebServer(BaseEnum):
    NGINX = 'nginx'
    APACHE = 'apache'


class Database(BaseEnum):
    MYSQL = 'mysql'
    POSTGRESQL = 'postgres'
    SQLITE = 'sqlite'
    MONGODB = 'mongodb'


class ProjectConfig(object):
    deployment = 'virtualenv'
    password = None
    domain = None
    ipv4 = None
    superuser = None
    sshkey = '~/.ssh/id_rsa.pub'
    db_engine = 'postgres'
    web_server = 'nginx'
    https = False
    email = 'team@xiberty.com'

    project_name = None
    project_user = None
    project_group = None
    project_path = None

    port = 22

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class Global:

    CONFIG_FILE_NAME = 'django.json'
    HOME_BASE_PATH = '/srv'
    SHARED_GROUP = 'workload'

    @classmethod
    def validate(cls, config):
        pass

    @classmethod
    @contextmanager
    def settings(cls):
        try:
            config_file = open(cls.CONFIG_FILE_NAME, 'r')
            config_json = json.load(config_file)
            cls.validate(config_json)
            project_name = config_json.pop('project')
            config = ProjectConfig(**config_json)
            config.project_name = project_name
            config.project_user = '{0}'.format(config.project_name)
            config.project_group = '{0}'.format(cls.SHARED_GROUP)
            config.project_path = '{0}/{1}'.format(cls.HOME_BASE_PATH, config.project_user)
            yield config
        except Exception as e:
            print(e)
        except FileNotFoundError:
            sys.exit('Valid [{0}] file is required!'.format(cls.CONFIG_FILE_NAME))
