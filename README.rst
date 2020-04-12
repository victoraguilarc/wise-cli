Wise CLI
--------

`wise` is a tool to deploy `Django` projects based on [django-wise template](https://github.com/victoraguilarc/django-wise)

Installation
============

**Stable Version**::

    pip install wise-cli

**Development Version**::

    [sudo] pip install git+https://github.com/victoraguilarc/wise-cli.git


Usage
=====

- Clone wise Django template::
    git clone https://github.com/victoraguilarc/wise.git

- **Configure Project**. The project must have a folder called `.envs` for environment variables por development and a file `.env` for production with virtualenv deployment mode.

- Add config file to cloned project.

By defaul *wise* uses *django.json*, This file could contains configuration values, for example::

    {
        "deployment": "virtualenv",
        "project": "wise",
        "password": "CHANGE_THIS!!",
        "domain": "www.xiberty.com",
        "ipv4": "0.0.0.0",
        "db_engine": "postgres",
        "web_server": "nginx",
        "https": true,
        "superuser": "username",
        "sshkey": "/Users/username/.ssh/id_rsa.pub"
    }


Development
===========
::

    pip install -e .



License
-------
This code is licensed under the `MIT License`_.

.. _`MIT License`: https://github.com/victoraguilarc/suarm/blob/master/LICENSE



