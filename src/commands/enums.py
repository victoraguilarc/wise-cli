from src.common.base_enum import BaseEnum


class ServerOS(BaseEnum):
    UBUNTU_XENIAL = 'ubuntu_xenial'
    UBUNTU_BIONIC = 'ubuntu_bionic'
    CENTOS_7 = 'centos_7'
    CENTOS_8 = 'centos_8'


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
