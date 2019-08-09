Sawi is a tool to deploy `Django` projects based on sawi template at https://github.com/vicobits/sawi

Installation
------------

**Stable Version**
`pip install sawi`

**Development Version**
`[sudo] pip install git+https://github.com/vicobits/sawi-cli.git`


Usage
-----

1) Clone sawi Django template

`git clone https://github.com/vicobits/sawi.git`

2) Add environment variables

The project must have a folder called `.envs` for environment variables por development
and a file `.env` for production with virtualenv deployment mode.

3) Add config file

By defaul `sawi` uses `django.json`, This file could contains configuration values, for example::

    {
        "deployment": "virtualenv",
        "project": "sawi",
        "password": "CHANGE_THIS!!",
        "domain": "www.xiberty.com",
        "ipv4": "0.0.0.0",
        "db_engine": "postgres",
        "web_server": "nginx",
        "https": true,
        "superuser": "username",
        "sshkey": "/Users/username/.ssh/id_rsa.pub"
    }



License
-------
This code is licensed under the `MIT License`_.

.. _`MIT License`: https://github.com/vicobits/suarm/blob/master/LICENSE



