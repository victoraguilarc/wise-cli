# -*- coding: utf-8 -*-

import click
from invoke import Responder, run
from pkg_resources import Requirement
from pkg_resources import resource_filename as src

from src.commands.config import Database, WebServer, Deployment
from src.common.context import CommandContext
from src.common.template import Template
from src.constants import HOME_BASE_PATH


class Server:

    @staticmethod
    def deps(context: CommandContext):
        """
        Install all server dependencies.
        """
        click.echo(click.style('\nInstalling [PROJECT] dependencies...\n', fg='green'))

        result = context.connection.run('lsb_release -sc', hide=True)
        distro = result.stdout.strip()

        click.echo(click.style(distro, fg='green'))

        deps_file = src(Requirement.parse('wise-cli'), 'src/templates/system-{0}.txt'.format(distro))
        result = context.connection.local(
            "grep -vE '^\s*\#' {0}  | tr '\n' ' '".format(deps_file),
            hide=True,
        ) # noqa
        pkgs = result.stdout.strip()

        context.connection.sudo('apt install -y %s' % pkgs)
        context.connection.sudo('apt autoremove -y')

        click.echo(click.style('\nInstalling [DATABASES] dependencies...\n', fg='green'))

        if context.config.db_engine == Database.POSTGRESQL:
            context.connection.sudo('apt install -y postgresql postgresql-contrib libpq-dev')
        elif context.config.db_engine == Database.MYSQL:
            context.connection.sudo('apt install -y mysql-server libmysqlclient-dev')

        click.echo(click.style('\nInstalling [WEB SERVER] dependencies...\n', fg='green'))
        if context.config.web_server == WebServer.NGINX:
            context.connection.sudo('apt install -y nginx')
        elif context.config.web_server == WebServer.APACHE:
            context.connection.sudo('apt install -y apache2')

        if context.config.https:
            # context.connection.sudo('apt install -y software-properties-common')
            # context.connection.sudo('add-apt-repository -y ppa:certbot/certbot')
            context.connection.sudo('apt update')
            context.connection.sudo('apt install -y certbot')

        context.connection.sudo(
            'adduser {0} {1}'.format(context.config.superuser, context.config.project_group),
            warn=True, hide='both'
        )

    @staticmethod
    def layout(context: CommandContext):
        click.echo(click.style('\n>> Configuring project layout...', fg='green'))
        context.connection.sudo(
            'mkdir -p '
            '{project_path} '
            '{project_path}/code/ '
            '{project_path}/repo/ '
            '{project_path}/etc/ '
            '{project_path}/etc/nginx/ '
            '{project_path}/etc/ssl/ '
            '{project_path}/log/ '
            '{project_path}/bin/ '
            '{project_path}/htdocs/ '
            '{project_path}/htdocs/media/ '
            '{project_path}/htdocs/static/'.format(project_path=context.config.project_path),
            hide='both',
        )

        if context.config.deployment == Deployment.DOCKER:
            context.connection.sudo('mkdir -p {0}/volumes/'.format(context.config.project_path), hide='both')

        context.connection.sudo(
            'chown -R {0}:{1} {2}'.format(
                context.config.project_user,
                context.config.project_group,
                context.config.project_path,
            ),
            hide='both',
        )
        click.echo(click.style('-> Layout configured', fg='cyan'))

    @staticmethod
    def certbot(context: CommandContext):
        cmd = context.connection.sudo('certbot --help', warn=True, hide='both')
        if cmd.failed:
            context.connection.sudo('add-apt-repository ppa:certbot/certbot -yu')
            context.connection.sudo('apt install python-certbot-nginx')
            click.echo(click.style('-> Certbot installed!', fg='cyan'))

    @staticmethod
    def letsencrypt(context: CommandContext):
        """
        1. Obtain certificates for apps
        2. Setting Up autorenew logic
        """

        if context.config.https:
            click.echo(click.style('-> Generating SSL certificate', fg='cyan'))
            context.connection.sudo(
                'certbot certonly \
                --standalone \
                --agree-tos \
                --email {email} \
                --domains "{domain}" \
                --pre-hook "service {web_server} stop" \
                --post-hook "service {web_server} start"'.format(
                    email=context.config.email,
                    domain=context.config.domain,
                    web_server=context.config.web_server,
                )
            )
            context.connection.sudo(
                'chmod -R go-rwx /etc/letsencrypt/live/{0}'.format(context.config.domain),
            )

            # (crontab -l ; echo "0 * * * * your_command") | sort - | uniq - | crontab -

            letsencrypt_folder = '/opt/letsencrypt'
            letsencrypt_renew = '{0}/renew.sh'.format(letsencrypt_folder)
            letsencrypt_crontab = '{0}/crontab.sh'.format(letsencrypt_folder)

            context.connection.sudo(f"mkdir -p {letsencrypt_folder}")

            click.echo(click.style('-> Adding crontab task', fg='cyan'))

            (Template(name='renew_le.sh', context={'web_server': context.config.web_server})
             .upload(context.connection, remote=f"{letsencrypt_renew}"))

            (Template(name='crontab_le.sh', context={'le_path': letsencrypt_folder})
             .upload(context.connection, remote=letsencrypt_crontab))

            context.connection.sudo('chmod +x {0}'.format(letsencrypt_renew))
            context.connection.sudo('chmod +x {0}'.format(letsencrypt_crontab))
            context.connection.sudo(letsencrypt_crontab)
            context.connection.sudo('rm {0}'.format(letsencrypt_crontab))
            context.connection.sudo('service cron restart')

            click.echo(click.style('-> Let\'s Encrypt configured', fg='cyan'))
        else:
            click.echo(click.style('-> Let\'s Encrypt configurations skipped!', fg='cyan'))

    @staticmethod
    def renew_ssl(context: CommandContext):
        context.connection.sudo(
            'certbot renew --pre-hook "service {web_server} stop" '
            '--post-hook "service {web_server} start"'.format(web_server=context.config.web_server)
        )

    @staticmethod
    def reboot(context: CommandContext):
        context.connection.sudo('reboot')

    @staticmethod
    def update(context: CommandContext):
        context.connection.sudo('apt-get update')
        context.connection.sudo('apt-get upgrade -y')

    @staticmethod
    def user(context: CommandContext):
        """
         Create project User.
        """
        click.echo(click.style('\n>> Creating Project User ...', fg='green'))
        user_exists = context.connection.run('id -u {0}'.format(context.config.project_user), warn=True, hide='both')
        if not user_exists.ok:
            context.connection.sudo(
                'adduser {0} --disabled-password --gecos \"\"'.format(context.config.project_user),
                hide=True
            )

            new_password = Responder('New password:', '{0}\n'.format(context.config.password))
            retype_new_password = Responder(r'Retype new password:', '{0}\n'.format(context.config.password))
            context.connection.sudo(
                'passwd {0}'.format(context.config.project_user), pty=True,
                watchers=[new_password, retype_new_password], hide='out',
            )
        else:
            click.echo(click.style('User alredy exists..', fg='cyan'))
        context.connection.sudo('mkdir -p {0}'.format(HOME_BASE_PATH), hide='both')

    @staticmethod
    def group(context: CommandContext):
        """
         Create project Group.
        """
        click.echo(click.style('\n>> Configuring project group...', fg='green'))
        context.connection.sudo('groupadd --system {0}'.format(context.config.project_group), warn=True)
        context.connection.sudo(
            'useradd --system --gid {0} --shell /bin/bash --home {1} {2}'.format(
                context.config.project_group, context.config.project_path, context.config.project_user
            ), warn=True, hide='out'
        )

    @staticmethod
    def create_db(context: CommandContext):
        click.echo(click.style('\n>> Configuring project Database...', fg='green'))
        if context.config.db_engine == Database.MYSQL:
            Server.mysql(context)
        elif context.config.db_engine == Database.POSTGRESQL:
            Server.postgresql(context)
        else:
            click.echo(click.style('-> Unsupported DB Engine', fg='red'))

    @staticmethod
    def postgresql(context: CommandContext):
        """
        1. Create DB user.
        2. Create DB and assign to user.
        """
        result_db = context.connection.sudo(
            'psql -c "CREATE DATABASE {0};"'.format(context.config.project_name),
            warn=True, hide='err', user='postgres',
        )
        if not result_db.ok:
            click.echo(click.style('-> DB alredy exists', fg='cyan'))

        result_user = context.connection.sudo(
            'psql -c "CREATE USER {0} WITH ENCRYPTED PASSWORD \'{1}\';"'.format(
                context.config.project_name, context.config.password
            ), warn=True, hide='err', user='postgres',
        )
        if not result_user.ok:
            click.echo(click.style('-> DB User alredy exists', fg='cyan'))

    @staticmethod
    def mysql(context: CommandContext):
        """
        1. Verify id user exist.
        2. If not user exist create DB user.
        3. Verify if database exist.
        4. If DB not exist create DB and assign to user.
        """
        pass
        # with settings(hide('warnings'), warn_only=True):
        #     mysql_user = get_value(env.stage, "mysql_user")
        #     mysql_pass = get_value(env.stage, "mysql_pass")
        #
        #     # CREATE DATABASE
        #     run("mysql -u %(mysql_user)s -p%(mysql_password)s -e 'CREATE DATABASE %(database)s;'" % {
        #         "mysql_user": mysql_user,
        #         "mysql_password": mysql_pass,
        #         "database": make_app(env.project),
        #     })
        #
        #     # CREATE USER
        #     run("mysql -u %(mysql_user)s -p%(mysql_password)s -e "
        #         "'CREATE USER \"%(user)s\"@\"localhost\" IDENTIFIED BY \"%(password)s\";'" % {
        #             "mysql_user": mysql_user,
        #             "mysql_password": mysql_pass,
        #             "user": make_user(env.project),
        #             "password": env.passwd,
        #         })
        #
        #     # GRANT USER TO DB
        #     run("mysql -u %(mysql_user)s -p%(mysql_password)s -e "
        #         "'GRANT ALL PRIVILEGES ON %(database)s.* TO \"%(user)s\"@\"localhost\";'" % {
        #             "mysql_user": mysql_user,
        #             "mysql_password": mysql_pass,
        #             "database": make_app(env.project),
        #             "user": make_user(env.project),
        #         })
        #
        #     run("mysql -u %(mysql_user)s -p%(mysql_password)s -e 'FLUSH PRIVILEGES;'" % {
        #         "mysql_user": mysql_user,
        #         "mysql_password": mysql_pass,
        #     })

    @staticmethod
    def web_server(context: CommandContext):
        if context.config.web_server == WebServer.NGINX:
            Server.nginx(context)
        elif context.config.web_server == WebServer.APACHE:
            Server.apache(context)
        else:
            click.echo(click.style('-> Unsupported Web Server', fg='red'))

    @staticmethod
    def git_repo_path(config):
        return '{0}/repo/{1}.git'.format(config.project_path, config.project_name)

    @staticmethod
    def git(context: CommandContext):
        """
        1. Setup bare Git repo.
        2. Create post-receive hook.
        """
        click.echo(click.style('\n>> Configuring project repository...', fg='green'))
        repo_git_path = Server.git_repo_path(context.config)

        context.connection.sudo(
            'mkdir -p {0}'.format(repo_git_path),
            user=context.config.project_user,
        )

        context.connection.sudo(
            'git init --bare --shared {0}'.format(repo_git_path),
            user=context.config.project_user,
            warn=True
        )

        work_dir = '{0}/code/'.format(context.config.project_path)
        post_receive_file = '{0}/hooks/post-receive'.format(repo_git_path)

        (Template(name='post-receive', context={'work_dir': work_dir})
         .upload(context.connection, remote=post_receive_file))

        context.connection.sudo('chmod +x {0}'.format(post_receive_file))
        context.connection.sudo(
            'chown -R {0}:{1} {2}'.format(
                context.config.project_user,
                context.config.project_group,
                repo_git_path,
            ), hide='both'
        )
        click.echo(click.style('-> Git repository configured', fg='cyan'))

    @staticmethod
    def add_remote(context: CommandContext, origin="production"):
        """
        1. Delete existent server remote git value.
        2. Add existent server remote git value.
        """
        git_repo_path = Server.git_repo_path(context.config)
        git_remote_path = '{0}@{1}:{2}'.format(
            context.config.project_user,
            context.config.domain,
            git_repo_path,
        )

        run('git remote remove {0}'.format(origin), warn=True, hide='both')
        run('git remote add {0} {1}'.format(origin, git_remote_path), warn=True, hide='both')

        click.echo(click.style('-> Git origin configured', fg='cyan'))

    @staticmethod
    def nginx(context: CommandContext):
        """
        1. Remove default nginx config file
        2. Create new config file
        3. Copy local config to remote config
        4. Setup new symbolic link
        """
        click.echo(click.style('\n>> Configuring nginx setting for the project ...', fg='green'))

        context.connection.sudo(
            'rm /etc/nginx/sites-enabled/default',
            hide='both', warn=True,
        )
        context.connection.sudo(
            'rm /etc/nginx/sites-enabled/{0}.conf'.format(context.config.project_name),
            hide='both', warn=True,
        )
        context.connection.sudo(
            'rm /etc/nginx/sites-available/{0}.conf'.format(context.config.project_name),
            hide='both', warn=True,
        )

        template_context = {
            'project_name': context.config.project_name,
            'project_path': context.config.project_path,
            'project_htdocs': '{0}/htdocs/'.format(context.config.project_path),
            'project_domain': context.config.domain
        }
        if context.config.https:
            nginx_config = Template(
                name='django_nginx_ssl.conf',
                context=template_context,
            )
        else:
            nginx_config = Template(
                name='django_nginx.conf',
                context=template_context,
            )

        tmp_nginx_conf = '/tmp/{0}.conf'.format(context.config.project_name)
        dest_nginx_conf = '/etc/nginx/sites-available/{0}.conf'.format(context.config.project_name)
        context.connection.put(
            local=nginx_config,
            remote=tmp_nginx_conf,
        )

        context.connection.sudo(
            'mv {0} {1}'.format(tmp_nginx_conf, dest_nginx_conf),
            warn=True, hide='both',
        )
        context.connection.sudo(
            'ln -s {0} /etc/nginx/sites-enabled/'.format(dest_nginx_conf),
            warn=True, hide='both',
        )

        click.echo(click.style('-> Nginx configured', fg='cyan'))

    @staticmethod
    def apache(context: CommandContext):
        """
        1. Remove default nginx config file
        2. Create new config file
        3. Copy local config to remote config
        4. Setup new symbolic link
        """
        pass

    @staticmethod
    def gunicorn(context: CommandContext):
        """
        1. Create new gunicorn start script
        2. Copy local start script template redered to server
        """
        click.echo(click.style('\n>> Configuring gunicorn settings', fg='green'))

        context.connection.sudo(
            'mkdir -p {0}/bin'.format(context.config.project_path),
            warn=True, hide='both',
        )
        tmp_gunicorn = '/tmp/start.sh'
        dest_gunicorn = '{0}/bin/start.sh'.format(context.config.project_path)
        context.connection.put(
            local=Template(
                name='start.sh',
                context={
                    'project_name': context.config.project_name,
                    'project_path': context.config.project_path,
                    'project_code_path': '{0}/code/'.format(context.config.project_path),
                    'project_user': context.config.project_user,
                    'project_group': context.config.project_group,
                }
            ),
            remote=tmp_gunicorn
        )
        context.connection.sudo(
            'mv {0} {1}'.format(tmp_gunicorn, dest_gunicorn),
            warn=True, hide='both',
        )
        context.connection.sudo(
            'chmod +x {0}'.format(dest_gunicorn),
            warn=True, hide='both',
        )
        click.echo(click.style('-> Gunicorn configured', fg='cyan'))

    @staticmethod
    def supervisor(context: CommandContext):
        """
        1. Create new supervisor config file.
        2. Copy local config to remote config.
        3. Register new command.
        """
        click.echo(click.style('\n>> Configuring Supervisor for project', fg='green'))
        dest_supervisor = '/etc/supervisor/conf.d/{0}.conf'.format(context.config.project_name)
        (Template(
            name='django_supervisor.conf',
            context={
                'project_name': context.config.project_name,
                'project_path': context.config.project_path,
                'project_user': context.config.project_user,
                'project_group': context.config.project_group,
            }
        ).upload(context.connection, remote=dest_supervisor))

        click.echo(click.style('-> Supervisor configured', fg='cyan'))

    @staticmethod
    def restart_services(context: CommandContext):
        """
        1. Update Supervisor configuration if app supervisor config exist.
        2. Restart nginx.
        3. Restart supervisor.
        """
        context.connection.sudo('supervisorctl reread')
        context.connection.sudo('supervisorctl update')

        context.connection.sudo('service nginx restart')
        context.connection.sudo('service supervisor restart')
        context.connection.sudo('supervisorctl restart {0}'.format(context.config.project_name))

    @staticmethod
    def configure_locales(context: CommandContext):
        """
        Generate and configure locales in recently installed server.
        """
        context.connection.sudo('locale-gen en_US.UTF-8', warn=True, hide='both')
        context.connection.sudo('dpkg-reconfigure locales', warn=True, hide='both')

    @staticmethod
    def fix_permissions(context: CommandContext):
        """
         Fix Permissions.
        """
        context.connection.sudo(
            'chown -R {0}:{1} {2}'.format(
                context.config.project_user,
                context.config.project_group,
                context.config.project_path,
            ),
            warn=True, hide='both',
        )

        context.connection.sudo(
            'chmod -R g+w {0}'.format(context.config.project_path),
            warn=True, hide='both',
        )

    @staticmethod
    def clean(context: CommandContext):
        """
        1. kill all user's processes.
        2. Delete app user folder.
        3. Delete project folder.
        4. Delete supervisor and nginx config files.
        5. Drop app and user in database.
        6. Delete app socket.
        7. Delete app group.
        8. Delete app user.
        """
        click.echo(click.style('\n>> Uninstalling project ...', fg='green'))
        cmd = {'warn': True, 'hide': 'both'}
        context.connection.sudo('pkill -u {0}'.format(context.config.project_user), **cmd)
        Server.drop_db(context)

        context.connection.sudo(
            'rm -f /etc/supervisor/conf.d/{0}.conf'.format(context.config.project_name), **cmd)
        context.connection.sudo(
            'rm -f /etc/nginx/sites-enabled/{0}.conf'.format(context.config.project_name), **cmd)
        context.connection.sudo(
            'rm -f /etc/nginx/sites-available/{0}.conf'.format(context.config.project_name), **cmd)
        context.connection.sudo(
            'rm -rf {0}/bin/{1}.socket'.format(context.config.project_path, context.config.project_name), **cmd)
        context.connection.sudo(
            'groupdel {0}'.format(context.config.project_group), **cmd)
        context.connection.sudo(
            'userdel -r {0}'.format(context.config.project_user), **cmd)
        context.connection.sudo(
            'rm -rf {0}'.format(context.config.project_path), **cmd)

        click.echo(click.style('-> Project uninstalled', fg='cyan'))

    @staticmethod
    def drop_db(context: CommandContext):
        if context.config.db_engine == Database.POSTGRESQL:
            context.connection.sudo(
                'psql -c "DROP DATABASE {0};"'.format(context.config.project_name),
                user='postgres', warn=True,
            )
            context.connection.sudo(
                'psql -c "DROP ROLE IF EXISTS {0};"'.format(context.config.project_user),
                user='postgres', warn=True,
            )
        elif context.config.db_engine == Database.MYSQL:
            # mysql_user = get_value(env.stage, "mysql_user")
            # mysql_pass = get_value(env.stage, "mysql_pass")
            #
            # run("mysql -u %(mysql_user)s -p%(mysql_password)s -e 'DROP DATABASE %(database)s;'" % {
            #     "mysql_user": mysql_user,
            #     "mysql_password": mysql_pass,
            #     "database": make_app(env.project),
            # })
            #
            # run("mysql -u %(mysql_user)s -p%(mysql_password)s -e 'DROP USER \"%(user)s\"@\"localhost\";'" % {
            #     "mysql_user": mysql_user,
            #     "mysql_password": mysql_pass,
            #     "user": make_user(env.project),
            # })
            #
            # run("mysql -u %(mysql_user)s -p%(mysql_password)s -e 'FLUSH PRIVILEGES;'" % {
            #     "mysql_user": mysql_user,
            #     "mysql_password": mysql_pass,
            # })
            pass
        else:
            click.echo(click.style('-> Unsupported DB Engine', fg='red'))

    @staticmethod
    def reset_db(context: CommandContext):
        Server.drop_db(context)
        Server.create_db(context)
