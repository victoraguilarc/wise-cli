# -*- coding: utf-8 -*-

import os

import click
from invoke import run, Responder


class Project:
    python = 'DJANGO_SETTINGS_MODULE=config.settings.production ./env/bin/python'
    pip = './env/bin/pip'

    @staticmethod
    def config_settings(connection, config):
        pass

    @staticmethod
    def push(connection, config, origin='production'):
        """ Push changes to selected server"""
        run('git push {0} master'.format(origin))

    @staticmethod
    def get_python(config):
        return (
            'DJANGO_READ_ENV_FILE=True '
            'DJANGO_SETTINGS_MODULE=config.settings.production '
            '{0}/env/bin/python'.format(config.project_path)
        )

    @staticmethod
    def install(connection, config):
        """
        Run intall command.
        """
        code_path = '{0}/code/'.format(config.project_path)
        venv_path = '{0}/env/'.format(config.project_path)
        pip = '{0}/env/bin/pip'.format(config.project_path)

        python = Project.get_python(config)

        click.echo(click.style('-> Configuring virtualenv', fg='cyan'))

        # TODO Check if folder exist, skip this step if this folder exists
        # TODO if an error occurrs recreate the folder
        connection.run(
            'virtualenv -p python3 {0} --always-copy --no-site-packages'.format(venv_path),
            warn=True, hide='both'
        )

        with connection.cd(code_path):

            click.echo(click.style('-> Installing production requirements ', fg='cyan'))
            connection.run('{0} install -r requirements/production.txt'.format(pip))

            click.echo(click.style('-> Loading migrations', fg='cyan'))
            connection.run('{0} manage.py migrate'.format(python))

            click.echo(click.style('-> Collecting static files', fg='cyan'))
            connection.run(
                '{0} manage.py collectstatic -v 0 '
                '--noinput '
                '--traceback '
                '-i django_extensions '
                '-i \'*.coffee\' '
                '-i \'*.rb\' '
                '-i \'*.scss\' '
                '-i \'*.less\' '
                '-i \'*.sass\' '.format(python)
            )

    @staticmethod
    def migrate(connection, config):
        Project.run_command(connection, config, command='migrate')

    @staticmethod
    def load_fixtures(connection, config):
        Project.run_command(connection, config, command='loaddata')

    @staticmethod
    def clean(connection, config):
        """
        TODO Clean project logs and cache.
        """
        pass

    @staticmethod
    def environment(connection, config):
        """ Push the environment configuration """
        if os.path.isfile('.env'):
            click.echo(click.style('-> Loading [.env] file', fg='cyan'))
            dest_env = '{0}/code/.env'.format(config.project_path)
            connection.put(
                local='.env',
                remote=dest_env,
            )
        else:
            click.echo(click.style('-> [.env] file is required', fg='red'))

    @staticmethod
    def start(connection, config):
        connection.sudo('supervisorctl start {0}'.format(config.project_name))

    @staticmethod
    def restart(connection, config):
        connection.sudo('supervisorctl restart {0}'.format(config.project_name))

    @staticmethod
    def stop(connection, config):
        connection.sudo('supervisorctl stop {0}'.format(config.project_name))

    @staticmethod
    def run_command(connection, config, command):
        code_path = '{0}/code/'.format(config.project_path)
        manage_py = '{0}manage.py'.format(code_path)
        python = Project.get_python(config)

        click.echo(click.style('-> Running {0}'.format(command), fg='cyan'))

        with connection.cd(code_path):
            connection.run(f"{python} {manage_py} {command}", pty=True)

    @staticmethod
    def create_superuser(connection, config):
        Project.run_command(connection, config, command='createsuperuser')

    @staticmethod
    def upload_key(connection, config):
        try:
            project_password = Responder(
                pattern=r'.*password:',
                response='{0}\n'.format(config.password),
            )
            run('ssh-copy-id {0}@{1}'.format(config.project_user, config.ipv4), pty=True, watchers=[project_password])
        except Exception as e:
            raise Exception('Unfulfilled local requirements')

    # def backup(connection, config):
    #     """
    #     Create a database backup
    #     """
    #
    #     # Backup DB
    #     sudo('pg_dump %(app)s > /tmp/%(app)s.sql' % {
    #         "app": make_app(env.project),
    #     }, user='postgres')
    #
    #     with settings(user=make_user(env.project), password=env.passwd):
    #         with cd(get_user_home(env.stage)):
    #             # Copy backup from temporal
    #             run("cp /tmp/%(app)s.sql ." %
    #                 {"app": make_app(env.project)})
    #             # Compress DB
    #             run("tar -cvf %(app)s.db.tar %(app)s.sql" %
    #                 {"app": make_app(env.project)})
    #
    #             run("rm %(app)s.sql" %
    #                 {"app": make_app(env.project)})
    #             # Compress media
    #             run("tar -cvf %(app)s.media.tar %(app)s/src/public/media/" %
    #                 {"app": make_app(env.project)})
    #
    #     # Clean DB from temporal
    #     sudo('rm /tmp/%(app)s.sql' % {"app": make_app(env.project)})
    #
    # @staticmethod
    # def download_backup(connection, config):
    #
    #     click.echo("\n----------------------------------------------------------")
    #     click.echo("Downloading backup patient please ...!!!")
    #     click.echo("----------------------------------------------------------")
    #
    #     get(remote_path="%(home)s/%(app)s.db.tar" % {
    #         "home": get_user_home(env.stage),
    #         "app": make_app(env.project)
    #     }, local_path=".", use_sudo=True)
    #     click.echo("---> DB Backup                          OK")
    #     get(remote_path="%(home)s/%(app)s.media.tar" % {
    #         "home": get_user_home(env.stage),
    #         "app": make_app(env.project)
    #     }, local_path=".", use_sudo=True)
    #     click.echo("---> MEDIA Backup                       OK")
    #     click.echo("----------------------------------------------------------\n")
