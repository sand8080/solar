
import copy

from itertools import imap, ifilter
from pprint import pprint

import networkx as nx
import jinja2
import mock

from jinja2 import Template


class Node(object):

    def __init__(self, config):
        self.uid = config['id']
        self.tags = set(config.get('tags', ()))
        self.config = copy.deepcopy(config)

    def __repr__(self):
        return 'Node(uid={0},tags={1})'.format(self.uid, self.tags)


class Resource(object):

    def __init__(self, config):
        self.uid = config['id']
        self.values = config['input']
        self.tags = set(config.get('tags', ()))

    def __repr__(self):
        return 'Resource(uid={0},tags={1})'.format(self.uid, self.tags)

    def __hash__(self):
        return hash(self.uid)

    def depends_on(self, value=None, tags=None):
        if tags is None:
            tags = []

        if value is None:
            value = self.values

        called_with_tags = []

        if isinstance(value, dict):
            for k, v in value.items():
                self.depends_on(value=v, tags=tags)
        elif isinstance(value, list):
            for e in value:
                self.depends_on(value=e, tags=tags)
        elif isinstance(value, str):
            env = Template(value)
            tags_call_mock = mock.MagicMock()

            env.globals['with_tags'] = tags_call_mock
            env.globals['first_with_tags'] = tags_call_mock

            try:
                env.render()
            except jinja2.exceptions.UndefinedError:
                # On dependency resolving stage we should
                # not handle rendering errors, we need
                # only information about graph, this
                # information can be provided by tags
                # filtering calls
                pass

            # Get arguments, which are tags, and flatten the list
            used_tags = sum(map(
                lambda call: list(call[0]),
                tags_call_mock.call_args_list), [])

            called_with_tags.extend(used_tags)

        tags.extend(called_with_tags)

        return tags


class DataGraph(nx.DiGraph):

    node_klass = Resource

    def __init__(self, resources=(), nodes=(), *args, **kwargs):
        super(DataGraph, self).__init__(*args, **kwargs)
        self.resources = map(lambda r: self.node_klass(r), resources)
        self.nodes = map(lambda n: Node(n), nodes)
        self.init_edges()

    def init_edges(self):
        for res in self.resources:
            self.add_node(res.uid, res=res)

            for dep_res in self.resources_with_tags(res.depends_on()):
                self.add_node(dep_res.uid, res=dep_res)
                self.add_edge(res.uid, dep_res.uid, parent=res.uid)

    def resources_with_tags(self, tags):
        """Filter all resources which have tags
        """
        return ifilter(lambda r: r.tags & set(tags), self.resources)

    def merge_nodes_resources(self):
        """Each node has a list of resources
        """
        merged = {}
        for node in self.nodes:
            merged.setdefault(node.uid, {})
            merged[node.uid] = list(self.resources_with_tags(node.tags))

        return merged

    def get_node(self, uid):
        return filter(lambda n: n.uid == uid, self.nodes)[0]

    def resolve(self):
        data = {}
        render_order = nx.topological_sort(self.reverse())

        # Use provided order to render resources
        for resource_id in render_order:
            # Iterate over all resources which are assigned for node
            for node_id, resources in self.merge_nodes_resources().items():
                # Render resources which should be rendered regarding to order
                for resource in filter(lambda r: r.uid == resource_id, resources):
                    # Create render context
                    ctx = {
                        'this': resource.values
                    }
                    ctx['this']['node'] = self.get_node(node_id).config
                    data['{0}-{1}'.format(node_id, resource.uid)] = self.render(resource.values, ctx)

        return data

    def render(self, value, context):
        if isinstance(value, dict):
            result_dict = {}
            for k, v in value.items():
                result_dict[k] = self.render(v, context)

            return result_dict
        elif isinstance(value, list):
            return map(lambda v: self.render(v, context), value)
        elif isinstance(value, str):
            env = Template(value)
            tags_call_mock = mock.MagicMock()

            def first_with_tags(*args):
                print self.merge_nodes_resources()
                obj = mock.MagicMock()
                objs = filter(lambda n: set(n['tags']) & set(args), self.merge_nodes_resources().items)

                if objs:
                    obj = objs[0]

                return obj

            env.globals['with_tags'] = tags_call_mock
            env.globals['first_with_tags'] = first_with_tags

            return env.render(**context)
