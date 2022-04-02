
from dataclasses import dataclass
from io import StringIO
from jinja2 import Environment, PackageLoader, select_autoescape


@dataclass
class Template(StringIO):
    name: str
    context: dict

    def __post_init__(self):
        content = self.render(self.name, self.context)
        super().__init__(content)

    def upload(self, connection, remote):
        tmp_file = '/tmp/{0}'.format(self.name)
        connection.put(local=self, remote=tmp_file)
        connection.sudo('mv {0} {1}'.format(tmp_file, remote))

    @classmethod
    def render(cls, name, context=None):
        context = context or {}
        env = Environment(
            loader=PackageLoader('src', 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template(name)
        return template.render(**context)
