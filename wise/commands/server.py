# -*- coding: utf-8 -*-

import click
from invoke import Responder, run
from pkg_resources import Requirement as req
from pkg_resources import resource_filename as src

from wise.commands.config import Database, WebServer, Deployment, Template
from wise.commands.config import Global


class Server:

    @staticmethod
    def deps(connection, config):
        """
        Install all server dependencies.
        """
        click.echo(click.style('\nInstalling [PROJECT] dependencies...\n', fg='green'))

        result = connection.run('lsb_release -sc', hide=True)
        distro = result.stdout.strip()

        deps_file = src(req.parse('wise'), 'wise/templates/system-{0}.txt'.format(distro))
        result = connection.local("grep -vE '^\s*\#' {0}  | tr '\n' ' '".format(deps_file), hide=True) # noqa
        pkgs = result.stdout.strip()

        connection.sudo('apt-get install -y %s' % pkgs)
        connection.sudo('apt-get install -y python-virtualenv python-pip')
        connection.sudo('apt-get autoremove -y')

        click.echo(click.style('\nInstalling [DATABASES] dependencies...\n', fg='green'))

        if config.db_engine == Database.POSTGRESQL.value:
            connection.sudo('apt-get install -y postgresql postgresql-contrib libpq-dev')
        elif config.db_engine == Database.MYSQL.value:
            connection.sudo('apt-get install -y mysql-server libmysqlclient-dev')

        click.echo(click.style('\nInstalling [WEB SERVER] dependencies...\n', fg='green'))
        if config.web_server == WebServer.NGINX.value:
            connection.sudo('apt-get install -y nginx')
        elif config.web_server == WebServer.APACHE.value:
            connection.sudo('apt-get install -y apache2')

        if config.https:
            connection.sudo('apt-get install -y software-properties-common')
            connection.sudo('add-apt-repository -y ppa:certbot/certbot')
            connection.sudo('apt-get update')
            connection.sudo('apt-get install -y certbot')

        connection.sudo(
            'adduser {0} {1}'.format(config.superuser, config.project_group),
            warn=True, hide='both'
        )

    @staticmethod
    def layout(connection, config):
        click.echo(click.style('\n>> Configuring project layout...', fg='green'))
        connection.sudo('mkdir -p '
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
                        '{project_path}/htdocs/static/'.format(project_path=config.project_path),
                        hide='both')

        if config.deployment == Deployment.DOCKER.value:
            connection.sudo('mkdir -p {0}/volumes/'.format(config.project_path), hide='both')

        connection.sudo('chown -R {0}:{1} {2}'.format(config.project_user, config.project_group, config.project_path),
                        hide='both')
        click.echo(click.style('-> Layout configured', fg='cyan'))

    @staticmethod
    def certbot(connection, config):
        cmd = connection.sudo('certbot --help', warn=True, hide='both')
        if cmd.failed:
            connection.sudo('add-apt-repository ppa:certbot/certbot -yu')
            connection.sudo('apt install python-certbot-nginx')
            click.echo(click.style('-> Certbot installed!', fg='cyan'))

    @staticmethod
    def letsencrypt(connection, config):
        """
        1. Obtain certificates for apps
        2. Setting Up autorenew logic
        """

        if config.https:
            click.echo(click.style('-> Generating SSL certificate', fg='cyan'))
            connection.sudo(
                'certbot certonly \
                --standalone \
                --agree-tos \
                --email {email} \
                --domains "{domain}" \
                --pre-hook "service {web_server} stop" \
                --post-hook "service {web_server} start"'.format(
                    email=config.email,
                    domain=config.domain,
                    web_server=config.web_server,
                )
            )
            connection.sudo('chmod -R go-rwx /etc/letsencrypt/live/{0}'.format(config.domain))

            # (crontab -l ; echo "0 * * * * your_command") | sort - | uniq - | crontab -

            letsencrypt_folder = '/opt/letsencrypt'
            letsencrypt_renew = '{0}/renew.sh'.format(letsencrypt_folder)
            letsencrypt_crontab = '{0}/crontab.sh'.format(letsencrypt_folder)

            connection.sudo(f"mkdir -p {letsencrypt_folder}")

            click.echo(click.style('-> Adding crontab task', fg='cyan'))

            (Template(name='renew_le.sh', context={'web_server': config.web_server})
             .upload(connection, remote=f"{letsencrypt_renew}"))

            (Template(name='crontab_le.sh', context={'le_path': letsencrypt_folder})
             .upload(connection, remote=letsencrypt_crontab))

            connection.sudo('chmod +x {0}'.format(letsencrypt_renew))
            connection.sudo('chmod +x {0}'.format(letsencrypt_crontab))
            connection.sudo(letsencrypt_crontab)
            connection.sudo('rm {0}'.format(letsencrypt_crontab))
            connection.sudo('service cron restart')

            click.echo(click.style('-> Let\'s Encrypt configured', fg='cyan'))
        else:
            click.echo(click.style('-> Let\'s Encrypt configurations skipped!', fg='cyan'))

    @staticmethod
    def renew_ssl(connection, config):
        connection.sudo(
            'certbot renew --pre-hook "service {web_server} stop" '
            '--post-hook "service {web_server} start"'.format(web_server=config.web_server)
        )

    @staticmethod
    def reboot(connection, config):
        connection.sudo('reboot')

    @staticmethod
    def update(connection, config):
        connection.sudo('apt-get update')
        connection.sudo('apt-get upgrade -y')

    @staticmethod
    def user(connection, config):
        """
         Create project User.
        """
        click.echo(click.style('\n>> Creating Project User ...', fg='green'))
        user_exists = connection.run('id -u {0}'.format(config.project_user), warn=True, hide='both')
        if not user_exists.ok:
            connection.sudo(
                'adduser {0} --disabled-password --gecos \"\"'.format(config.project_user),
                hide=True
            )

            new_password = Responder('New password:', '{0}\n'.format(config.password))
            retype_new_password = Responder(r'Retype new password:', '{0}\n'.format(config.password))
            connection.sudo('passwd {0}'.format(config.project_user), pty=True,
                            watchers=[new_password, retype_new_password], hide='out')
        else:
            click.echo(click.style('User alredy exists..', fg='cyan'))
        connection.sudo('mkdir -p {0}'.format(Global.HOME_BASE_PATH), hide='both')

    @staticmethod
    def group(connection, config):
        """
         Create project Group.
        """
        click.echo(click.style('\n>> Configuring project group...', fg='green'))
        connection.sudo('groupadd --system {0}'.format(config.project_group), warn=True)
        connection.sudo(
            'useradd --system --gid {0} --shell /bin/bash --home {1} {2}'.format(
                config.project_group, config.project_path, config.project_user
            ), warn=True, hide='out'
        )

    @staticmethod
    def create_db(connection, config):
        click.echo(click.style('\n>> Configuring project Database...', fg='green'))
        if config.db_engine == Database.MYSQL.value:
            Server.mysql(connection, config)
        elif config.db_engine == Database.POSTGRESQL.value:
            Server.postgresql(connection, config)
        else:
            click.echo(click.style('-> Unsupported DB Engine', fg='red'))

    @staticmethod
    def postgresql(connection, config):
        """
        1. Create DB user.
        2. Create DB and assign to user.
        """
        result_db = connection.sudo('psql -c "CREATE DATABASE {0};"'.format(config.project_name),
                                    warn=True, hide='err', user='postgres')
        if not result_db.ok:
            click.echo(click.style('-> DB alredy exists', fg='cyan'))

        result_user = connection.sudo(
            'psql -c "CREATE USER {0} WITH ENCRYPTED PASSWORD \'{1}\';"'.format(
                config.project_name, config.password
            ), warn=True, hide='err', user='postgres'
        )
        if not result_user.ok:
            click.echo(click.style('-> DB User alredy exists', fg='cyan'))

    @staticmethod
    def mysql(connection, config):
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
    def web_server(connection, config):
        if config.web_server == WebServer.NGINX.value:
            Server.nginx(connection, config)
        elif config.web_server == WebServer.APACHE.value:
            Server.apache(connection, config)
        else:
            click.echo(click.style('-> Unsupported Web Server', fg='red'))

    @staticmethod
    def git_repo_path(config):
        return '{0}/repo/{1}.git'.format(config.project_path, config.project_name)

    @staticmethod
    def git(connection, config):
        """
        1. Setup bare Git repo.
        2. Create post-receive hook.
        """
        click.echo(click.style('\n>> Configuring project repository...', fg='green'))
        repo_git_path = Server.git_repo_path(config)

        connection.sudo('mkdir -p {0}'.format(repo_git_path),
                        user=config.project_user)

        connection.sudo('git init --bare --shared {0}'.format(repo_git_path),
                        user=config.project_user,
                        warn=True)

        work_dir = '{0}/code/'.format(config.project_path)
        post_receive_file = '{0}/hooks/post-receive'.format(repo_git_path)

        (Template(name='post-receive', context={'work_dir': work_dir})
         .upload(connection, remote=post_receive_file))

        connection.sudo('chmod +x {0}'.format(post_receive_file))
        connection.sudo(
            'chown -R {0}:{1} {2}'.format(
                config.project_user, config.project_group, repo_git_path
            ), hide='both'
        )
        click.echo(click.style('-> Git repository configured', fg='cyan'))

    @staticmethod
    def add_remote(connection, config, origin="production"):
        """
        1. Delete existent server remote git value.
        2. Add existent server remote git value.
        """
        git_repo_path = Server.git_repo_path(config)
        git_remote_path = '{0}@{1}:{2}'.format(
            config.project_user, config.domain, git_repo_path
        )

        run('git remote remove {0}'.format(origin), warn=True, hide='both')
        run('git remote add {0} {1}'.format(origin, git_remote_path), warn=True, hide='both')

        click.echo(click.style('-> Git origin configured', fg='cyan'))

    @staticmethod
    def nginx(connection, config):
        """
        1. Remove default nginx config file
        2. Create new config file
        3. Copy local config to remote config
        4. Setup new symbolic link
        """
        click.echo(click.style('\n>> Configuring nginx setting for the project ...', fg='green'))

        connection.sudo('rm /etc/nginx/sites-enabled/default',
                        hide='both', warn=True)
        connection.sudo('rm /etc/nginx/sites-enabled/{0}.conf'.format(config.project_name),
                        hide='both', warn=True)
        connection.sudo('rm /etc/nginx/sites-available/{0}.conf'.format(config.project_name),
                        hide='both', warn=True)

        context = {
            'project_name': config.project_name,
            'project_path': config.project_path,
            'project_htdocs': '{0}/htdocs/'.format(config.project_path),
            'project_domain': config.domain
        }
        if config.https:
            nginx_config = Template(
                name='django_nginx_ssl.conf', context=context
            )
        else:
            nginx_config = Template(
                name='django_nginx.conf', context=context
            )

        tmp_nginx_conf = '/tmp/{0}.conf'.format(config.project_name)
        dest_nginx_conf = '/etc/nginx/sites-available/{0}.conf'.format(config.project_name)
        connection.put(
            local=nginx_config,
            remote=tmp_nginx_conf,
        )

        connection.sudo('mv {0} {1}'.format(tmp_nginx_conf, dest_nginx_conf), warn=True, hide='both')
        connection.sudo('ln -s {0} /etc/nginx/sites-enabled/'.format(dest_nginx_conf), warn=True, hide='both')

        click.echo(click.style('-> Nginx configured', fg='cyan'))

    @staticmethod
    def apache(connection, config):
        """
        1. Remove default nginx config file
        2. Create new config file
        3. Copy local config to remote config
        4. Setup new symbolic link
        """
        pass

    @staticmethod
    def gunicorn(connection, config):
        """
        1. Create new gunicorn start script
        2. Copy local start script template redered to server
        """
        click.echo(click.style('\n>> Configuring gunicorn settings', fg='green'))

        connection.sudo('mkdir -p {0}/bin'.format(config.project_path), warn=True, hide='both')
        tmp_gunicorn = '/tmp/start.sh'
        dest_gunicorn = '{0}/bin/start.sh'.format(config.project_path)
        connection.put(
            local=Template(
                name='start.sh',
                context={
                    'project_name': config.project_name,
                    'project_path': config.project_path,
                    'project_code_path': '{0}/code/'.format(config.project_path),
                    'project_user': config.project_user,
                    'project_group': config.project_group,}),
            remote=tmp_gunicorn
        )
        connection.sudo('mv {0} {1}'.format(tmp_gunicorn, dest_gunicorn), warn=True, hide='both')
        connection.sudo('chmod +x {0}'.format(dest_gunicorn), warn=True, hide='both')
        click.echo(click.style('-> Gunicorn configured', fg='cyan'))

    @staticmethod
    def supervisor(connection, config):
        """
        1. Create new supervisor config file.
        2. Copy local config to remote config.
        3. Register new command.
        """
        click.echo(click.style('\n>> Configuring Supervisor for project', fg='green'))

        dest_supervisor = '/etc/supervisor/conf.d/{0}.conf'.format(config.project_name)

        (Template(
            name='django_supervisor.conf',
            context={
                'project_name': config.project_name,
                'project_path': config.project_path,
                'project_user': config.project_user,
                'project_group': config.project_group,
            }
        ).upload(connection, remote=dest_supervisor))

        click.echo(click.style('-> Supervisor configured', fg='cyan'))

    @staticmethod
    def restart_services(connection, config):
        """
        1. Update Supervisor configuration if app supervisor config exist.
        2. Restart nginx.
        3. Restart supervisor.
        """
        connection.sudo('supervisorctl reread')
        connection.sudo('supervisorctl update')

        connection.sudo('service nginx restart')
        connection.sudo('service supervisor restart')
        connection.sudo('supervisorctl restart {0}'.format(config.project_name))

    @staticmethod
    def configure_locales(connection, config):
        """
        Generate and configure locales in recently installed server.
        """
        connection.sudo('locale-gen en_US.UTF-8', warn=True, hide='both')
        connection.sudo('dpkg-reconfigure locales', warn=True, hide='both')

    @staticmethod
    def fix_permissions(connection, config):
        """
         Fix Permissions.
        """
        connection.sudo('chown -R {0}:{1} {2}'.format(
            config.project_user, config.project_group, config.project_path
        ), warn=True, hide='both')

        connection.sudo('chmod -R g+w {0}'.format(config.project_path), warn=True, hide='both')

    @staticmethod
    def clean(connection, config):
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
        connection.sudo('pkill -u {0}'.format(config.project_user), **cmd)
        Server.drop_db(connection, config)

        connection.sudo('rm -f /etc/supervisor/conf.d/{0}.conf'.format(config.project_name), **cmd)
        connection.sudo('rm -f /etc/nginx/sites-enabled/{0}.conf'.format(config.project_name), **cmd)
        connection.sudo('rm -f /etc/nginx/sites-available/{0}.conf'.format(config.project_name), **cmd)

        connection.sudo('rm -rf {0}/bin/{1}.socket'.format(config.project_path, config.project_name), **cmd)
        connection.sudo('groupdel {0}'.format(config.project_group), **cmd)
        connection.sudo('userdel -r {0}'.format(config.project_user), **cmd)
        connection.sudo('rm -rf {0}'.format(config.project_path), **cmd)

        click.echo(click.style('-> Project uninstalled', fg='cyan'))

    @staticmethod
    def drop_db(connection, config):
        if config.db_engine == Database.POSTGRESQL.value:
            connection.sudo(
                'psql -c "DROP DATABASE {0};"'.format(config.project_name),
                user='postgres', warn=True,
            )
            connection.sudo(
                'psql -c "DROP ROLE IF EXISTS {0};"'.format(config.project_user),
                user='postgres', warn=True,
            )
        elif config.db_engine == Database.MYSQL.value:
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
    def reset_db(connection, config):
        Server.drop_db(connection, config)
        Server.create_db(connection, config)


