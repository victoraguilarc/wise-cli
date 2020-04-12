# -*- coding: utf-8 -*-

import json
import sys
import click
import warnings

from fabric import Config
from os.path import isfile
from functools import wraps
from getpass import getpass
from fabric.connection import Connection
from paramiko import AuthenticationException

from wise.commands.project import Project
from wise.commands.server import Server
from wise.commands.config import Global, WebServer


def logit(logfile='out.log'):
    def logging_decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            log_string = func.__name__ + " was called"
            print(log_string)
            # Open the logfile and append
            with open(logfile, 'a') as opened_file:
                # Now we log to the specified logfile
                opened_file.write(log_string + '\n')
        return wrapped_function
    return logging_decorator


def update_config_file(key, value):
    with open(Global.CONFIG_FILE_NAME, 'r+') as f:
        data = json.load(f)
        if 'https' in data:
            data['https'] = True  # <--- add `https` value.
            f.seek(0)  # <--- should reset file position to the beginning.
            json.dump(data, f, indent=4)
            f.truncate()  # remove remaining part


def settings(allow_sudo=False, only_local=False):
    def settings_decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                with Global.settings() as config:
                    key_filename = config.sshkey
                    connection_config = {
                        'host': config.ipv4,
                        'port': config.port
                    }
                    if allow_sudo:
                        sudo_pass = getpass('Put your [SUDO] password for User [{0}]: '.format(config.superuser))
                        connection_config['user'] = config.superuser
                        connection_config['config'] = Config(
                            overrides={'sudo': {'password': sudo_pass}}
                        )
                    else:
                        connection_config['user'] = config.project_user

                    if not isfile(key_filename):
                        sys.exit('[sshkey] file doesn\'t exists')
                    connection_config['connect_kwargs'] = {'key_filename': key_filename}
                    connection = Connection(**connection_config)

                    try:
                        if not only_local:
                            connection.run('uname', hide='both', warn=True)
                        func(connection, config, *args, **kwargs)
                    except AuthenticationException:
                        click.echo(
                            click.style(
                                'Your ssh connection isn\'t configured correctly\n'
                                'Set your private ssh_keyfile for [{0}]'.format(connection_config['user']),
                                fg='red'
                            )
                        )
        return wrapped_function
    return settings_decorator


class Pipeline:

    @staticmethod
    @settings(allow_sudo=True)
    def update(connection, config):
        connection.sudo('apt-get update')
        connection.sudo('apt-get upgrade -y')

    @staticmethod
    @settings(allow_sudo=True)
    def deps(connection, config):
        Server.deps(connection, config)

    @staticmethod
    @settings(allow_sudo=True)
    def setup_server(connection, config):
        Server.deps(connection, config)
        Server.user(connection, config)
        Server.group(connection, config)
        Server.layout(connection, config)
        Server.create_db(connection, config)
        Server.fix_permissions(connection, config)
        Server.git(connection, config)
        Server.add_remote(connection, config)
        Server.web_server(connection, config)
        Server.gunicorn(connection, config)
        Server.supervisor(connection, config)
        Server.fix_permissions(connection, config)
        Server.letsencrypt(connection, config)

    @staticmethod
    @settings(allow_sudo=True)
    def clean_server(connection, config):
        """
        Uninstall app in selected server(s)
        """
        Server.clean(connection, config)

    @staticmethod
    @settings(allow_sudo=True)
    def restart_server(connection, config):
        """
        Restart all app services.
        """
        Server.restart_services(connection, config)

    @staticmethod
    @settings()
    def deploy(connection, config):
        Project.push(connection, config)
        Project.environment(connection, config)
        Project.install(connection, config)
        Project.clean(connection, config)

    @staticmethod
    @settings(allow_sudo=True)
    def fix_permissions(connection, config):
        Server.fix_permissions(connection, config)

    @staticmethod
    @settings()
    def add_remote(connection, config):
        Server.add_remote(connection, config)

    @staticmethod
    @settings(allow_sudo=True)
    def createsuperuser(connection, config):
        """
        Create a project superuser in selected server(s).
        """
        Project.create_superuser(connection, config)

    @staticmethod
    @settings()
    def run_command(connection, config, command):
        Project.run_command(connection, config, command)

    @staticmethod
    @settings()
    def migrate(connection, config):
        Project.migrate(connection, config)

    @staticmethod
    @settings()
    def load_fixtures(connection, config):
        Project.load_fixtures(connection, config)

    @staticmethod
    @settings(only_local=True)
    def upload_sshkey(connection, config):
        """
        Upload SSH key to server.
        """
        Project.upload_key(connection, config)

    @staticmethod
    @settings(allow_sudo=True)
    def setup_ssl(connection, config, artifact=None):
        if artifact:

            if not config.https:
                is_agree = input(
                    'We will change the value of [https] in your config file, Are you agree? Y/n: '
                ) or 'n'

                if is_agree.upper() == "Y":
                    update_config_file(key="https", value=True)

            if artifact == 'renew':
                Server.renew_ssl(connection, config)

            elif artifact == WebServer.NGINX.value:
                Server.nginx(connection, config)

            else:
                click.echo(click.style('[{0}] doesn\'t implemented'.format(artifact), fg='red'))
        else:
            Server.certbot(connection, config)
            Server.letsencrypt(connection, config)

    @staticmethod
    @settings(allow_sudo=True)
    def server_language(connection, config):
        if connection.run('echo $LANG').ok:
            connection.sudo('echo "LANG=C.UTF-8" >> /etc/environment')

        if connection.run('echo $LC_CTYPE').ok:
            connection.sudo('echo "LC_CTYPE=C.UTF-8" >> /etc/environment')

        if connection.run('echo $LC_ALL').ok:
            connection.sudo('echo "LC_ALL=C.UTF-8" >> /etc/environment')

    @staticmethod
    @settings(allow_sudo=True)
    def reset_db(connection, config):
        Server.reset_db(connection, config)

    # @classmethod
    # def make_backup(cls):
    #     Global.set_user(superuser=True)
    #     with settings(hide('warnings'), warn_only=True):
    #         execute(Project.backup, hosts=env.hosts)
    #         execute(Project.download_backup, hosts=env.hosts)
    #