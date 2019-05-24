from __future__ import unicode_literals

import os

import click
from invoke import run, Responder


class Project:
    python = "DJANGO_SETTINGS_MODULE=config.settings.production ./env/bin/python"
    pip = "./env/bin/pip"

    @staticmethod
    def config_settings(connection, config):
        pass

    @staticmethod
    def push(connection, config, origin="production"):
        """ Push changes to selected server"""
        run(f"git push {origin} master")

    @staticmethod
    def get_python(config):
        return (f"DJANGO_READ_ENV_FILE=True "
                f"DJANGO_SETTINGS_MODULE=config.settings.production "
                f"{config.project_path}/env/bin/python")

    @staticmethod
    def install(connection, config):
        """
        Run intall command.
        """
        code_path = f"{config.project_path}/code/"
        venv_path = f"{config.project_path}/env/"
        pip = f"{config.project_path}/env/bin/pip"

        python = Project.get_python(config)

        click.echo(click.style('-> Configuring virtualenv', fg='cyan'))

        # TODO Check if folder exist, skip this step if this folder exists
        # TODO if an error occurrs recreate the folder
        connection.run(f"virtualenv -p python3 {venv_path} --always-copy --no-site-packages", warn=True, hide='both')


        with connection.cd(code_path):

            click.echo(click.style('-> Installing production requirements ', fg='cyan'))
            connection.run(f"{pip} install -r requirements/production.txt")

            click.echo(click.style('-> Loading migrations', fg='cyan'))
            connection.run(f"{python} manage.py migrate")

            click.echo(click.style('-> Collecting static files', fg='cyan'))
            connection.run(f"{python} manage.py collectstatic -v 0 "
                           f"--noinput "
                           f"--traceback "
                           f"-i django_extensions "
                           f"-i '*.coffee' "
                           f"-i '*.rb' "
                           f"-i '*.scss' "
                           f"-i '*.less' "
                           f"-i '*.sass'")

    @staticmethod
    def migrate(connection, config):
        Project.run_command(connection, config, command="migrate")

    @staticmethod
    def load_fixtures(connection, config):
        Project.run_command(connection, config, command="loaddata")

    @staticmethod
    def clean(connection, config):
        """
        TODO Clean project logs and cache.
        """
        pass

    @staticmethod
    def environment(connection, config):
        """ Push the environment configuration """
        if os.path.isfile(".env"):
            click.echo(click.style('-> Loading [.env] file', fg='cyan'))
            dest_env = f"{config.project_path}/code/.env"
            connection.put(
                local=".env",
                remote=f"{dest_env}",
            )
        else:
            click.echo(click.style('-> [.env] file is required', fg='red'))

    @staticmethod
    def start(connection, config):
        connection.sudo(f"supervisorctl start {config.project_name}")

    @staticmethod
    def restart(connection, config):
        connection.sudo(f"supervisorctl restart {config.project_name}")

    @staticmethod
    def stop(connection, config):
        connection.sudo(f"supervisorctl stop {config.project_name}")

    @staticmethod
    def run_command(connection, config, command):
        code_path = f"{config.project_path}/code/"
        manage_py = f"{code_path}manage.py"
        python = Project.get_python(config)

        click.echo(click.style(f'-> Running {command}', fg='cyan'))

        with connection.cd(code_path):
            connection.run(f"{python} {manage_py} {command}", pty=True)

    @staticmethod
    def create_superuser(connection, config):
        Project.run_command(connection, config, command="createsuperuser")

    @staticmethod
    def upload_key(connection, config):
        try:
            project_password = Responder(
                pattern=r'.*password:',
                response=f'{config.password}\n',
            )
            run(f"ssh-copy-id {config.project_user}@{config.domain}", pty=True, watchers=[project_password])
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
