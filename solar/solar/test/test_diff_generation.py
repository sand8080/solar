
from pytest import fixture
from dictdiffer import revert, patch
import networkx as nx

from solar.system_log import change
from solar.core.resource import wrap_resource


@fixture
def staged():
    return {'id': 'res.1',
            'tags': ['res', 'node.1'],
            'input': {'ip': {'value': '10.0.0.2'},
                     'list_val': {'value': [1, 2]}},
            'metadata': {},
            'connections': [
                ['node.1', 'res.1', ['ip', 'ip']],
                ['node.1', 'res.1', ['key', 'key']]]
            }

@fixture
def commited():
    return {'id': 'res.1',
            'tags': ['res', 'node.1'],
            'input': {'ip': '10.0.0.2',
                     'list_val': [1]},
            'metadata': {},
            'connections': [
                ['node.1', 'res.1', ['ip', 'ip']]]
            }

@fixture
def full_diff(staged):
    return change.create_diff(staged, {})


@fixture
def diff_for_update(staged, commited):
    return change.create_diff(staged, commited)


def test_create_diff_with_empty_commited(full_diff):
    # add will be executed
    expected = [('add', '', [('connections', [['node.1', 'res.1', ['ip', 'ip']], ['node.1', 'res.1', ['key', 'key']]]), ('input', {'ip': {'value': '10.0.0.2'}, 'list_val': {'value': [1, 2]}}), ('metadata', {}), ('id', 'res.1'), ('tags', ['res', 'node.1'])])]
    assert full_diff == expected


def test_create_diff_modified(diff_for_update):
    assert diff_for_update == [
        ('add', 'connections',
            [(1, ['node.1', 'res.1', ['key', 'key']])]),
         ('change', 'input.ip', ('10.0.0.2', {'value': '10.0.0.2'})),
         ('change', 'input.list_val', ([1], {'value': [1, 2]}))]


def test_verify_patch_creates_expected(staged, diff_for_update, commited):
    expected = patch(diff_for_update, commited)
    assert expected == staged


def test_revert_update(staged, diff_for_update, commited):
    expected = revert(diff_for_update, staged)
    assert expected == commited


@fixture
def resources():
    r = {'n.1':
            {'uid': 'n.1',
             'args': {'ip': '10.20.0.2'},
             'connections': [],
             'tags': []},
         'r.1':
             {'uid': 'r.1',
              'args': {'ip': '10.20.0.2'},
              'connections': [['n.1', 'r.1', ['ip', 'ip']]],
              'tags': []},
          'h.1':
             {'uid': 'h.1',
              'args': {'ip': '10.20.0.2',
                       'ips': ['10.20.0.2']},
              'connections': [['n.1', 'h.1', ['ip', 'ip']]],
              'tags': []}}
    return r

@fixture
def conn_graph():
    edges = [
        ('n.1', 'r.1', {'label': 'ip:ip'}),
        ('n.1', 'h.1', {'label': 'ip:ip'}),
        ('r.1', 'h.1', {'label': 'ip:ips'})
    ]
    mdg = nx.MultiDiGraph()
    mdg.add_edges_from(edges)
    return mdg


def test_stage_changes(resources, conn_graph):
    commited = {}
    log = change._stage_changes(resources, conn_graph, commited, [])

    assert len(log) == 3
    assert [l.res for l in log] == ['n.1', 'r.1', 'h.1']


def test_resource_fixture(staged):
    res = wrap_resource(staged)
