#    Copyright 2015 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Solar CLI api

On create "golden" resource should be moved to special place
"""

import argparse
import os
import sys
import pprint

import textwrap
import yaml

from solar import utils
from solar.core.resource import assign_resources_to_nodes
from solar.core.resource import connect_resources
from solar.core.tags_set_parser import Expression
from solar.interfaces.db import get_db

# NOTE: these are extensions, they shouldn't be imported here
# Maybe each extension can also extend the CLI with parsers
from solar.extensions.modules.discovery import Discovery


class Cmd(object):

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description=textwrap.dedent(__doc__),
            formatter_class=argparse.RawDescriptionHelpFormatter)
        self.subparser = self.parser.add_subparsers(
            title='actions',
            description='Supported actions',
            help='Provide of one valid actions')
        self.register_actions()
        self.db = get_db()

    def parse(self, args):
        parsed = self.parser.parse_args(args)
        return parsed.func(parsed)

    def register_actions(self):

        parser = self.subparser.add_parser('discover')
        parser.set_defaults(func=getattr(self, 'discover'))

        # Profile actions
        parser = self.subparser.add_parser('profile')
        parser.set_defaults(func=getattr(self, 'profile'))
        parser.add_argument('-l', '--list', dest='list', action='store_true')
        group = parser.add_argument_group('create')
        group.add_argument('-c', '--create', dest='create', action='store_true')
        group.add_argument('-t', '--tags', nargs='+', default=['env/test_env'])
        group.add_argument('-i', '--id', default=utils.generate_uuid())

        # Assign
        parser = self.subparser.add_parser('assign')
        parser.set_defaults(func=getattr(self, 'assign'))
        parser.add_argument('-n', '--nodes')
        parser.add_argument('-r', '--resources')

        # Run action on tags
        parser = self.subparser.add_parser('run')
        parser.set_defaults(func=getattr(self, 'run'))
        parser.add_argument('-t', '--tags')
        parser.add_argument('-a', '--action')

        # Perform resources connection
        parser = self.subparser.add_parser('connect')
        parser.set_defaults(func=getattr(self, 'connect'))
        parser.add_argument(
            '-p',
            '--profile')

    def run(self, args):
        from solar.core import actions
        from solar.core import resource

        resources = filter(
            lambda r: Expression(args.tags, r.get('tags', [])).evaluate(),
            self.db.get_list('resource'))

        for resource in resources:
            resource_obj = resource.load(resource['id'])
            actions.resource_action(resource_obj, args.action)

    def profile(self, args):
        if args.create:
            params = {'tags': args.tags, 'id': args.id}
            profile_template_path = os.path.join(
                utils.read_config()['template-dir'], 'profile.yml')
            data = yaml.load(utils.render_template(profile_template_path, params))
            self.db.store('profiles', data)
        else:
            pprint.pprint(self.db.get_list('profiles'))

    def discover(self, args):
        Discovery({'id': 'discovery'}).discover()

    def connect(self, args):
        profile = self.db.get_record('profiles', args.profile)
        connect_resources(profile)

    def assign(self, args):
        nodes = filter(
            lambda n: Expression(args.nodes, n.get('tags', [])).evaluate(),
            self.db.get_list('nodes'))

        resources = filter(
            lambda r: Expression(args.resources, r.get('tags', [])).evaluate(),
            self._get_resources_list())

        print("For {0} nodes assign {1} resources".format(len(nodes), len(resources)))
        assign_resources_to_nodes(resources, nodes)

    def _get_resources_list(self):
        result = []
        for path in utils.find_by_mask(utils.read_config()['resources-files-mask']):
            resource = utils.yaml_load(path)
            resource['path'] = path
            resource['dir_path'] = os.path.dirname(path)
            result.append(resource)

        return result


def main():
    api = Cmd()
    api.parse(sys.argv[1:])


if __name__ == '__main__':
    main()
