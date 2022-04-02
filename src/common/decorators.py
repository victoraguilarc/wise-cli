import json
import sys
import warnings

import click
from fabric import Config
from os.path import isfile, exists
from functools import wraps
from getpass import getpass
from fabric.connection import Connection
from paramiko import AuthenticationException
from src.commands.config import CONFIG_FILE_NAME, load_settings
from src.common.context import CommandContext


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
    with open(CONFIG_FILE_NAME, 'r+') as f:
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
                file_exists = exists(CONFIG_FILE_NAME)
                if not file_exists:
                    print('Valid [{0}] file is required!'.format(CONFIG_FILE_NAME))
                    return
                with load_settings() as config:
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
                    context = CommandContext(
                        connection=Connection(**connection_config),
                        config=config,
                    )

                    try:
                        if not only_local:
                            context.connection.run('uname', hide='both', warn=True)
                        func(context, *args, **kwargs)
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
