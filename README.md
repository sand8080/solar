# Setup development env

* Install [Vagrant](http://www.vagrantup.com/downloads.html)
* Setup environment:
```
cd solar
```
* 1. Configure vagrant-settings.yml, for example:
```
slaves_count: 2
slaves_ram: 2048
slaves_cpu: 2
slaves_ips:
  - 10.0.0.
  - 10.1.0.
  - 192.168.121.
master_ram: 2048
master_cpu: 2
master_ips:
  - 10.0.0.2
  - 10.1.0.2
  - 192.168.121.12
```
* 2. Provision the env
```
vagrant up
```

* Login into vm, the code is available in /vagrant directory
```
vagrant ssh
solar --help
```

* Launch standard deployment:
```
python example.py
```

* Get ssh details for running slave nodes (vagrant/vagrant):
```
vagrant ssh-config
```

* Get list of docker containers and attach to the foo container
```
sudo docker ps -a
sudo docker exec -it foo
```

## Solar usage

* To get data for the resource bar (raw and pretty-JSON):
```
solar resource show --tag 'resources/bar'
solar resource show --json --tag 'resources/bar' | jq .
solar resource show --name 'resource_name'
solar resource show --name 'resource_name' --json | jq .
```

* To clear all resources/connections:
```
solar resource clear_all
solar connections clear_all
```

* Some very simple cluster setup:
```
cd /vagrant

solar resource create node1 resources/ro_node/ '{"ip":"10.0.0.3", "ssh_key" : "/vagrant/.vagrant/machines/solar-dev1/virtualbox/private_key", "ssh_user":"vagrant"}'
solar resource create mariadb_service resources/mariadb_service '{"image": "mariadb", "root_password": "mariadb", "port": 3306}'
solar resource create keystone_db resources/mariadb_keystone_db/ '{"db_name": "keystone_db", "login_user": "root"}'
solar resource create keystone_db_user resources/mariadb_user/ user_name=keystone user_password=keystone  # another valid format

solar connect node1 mariadb_service
solar connect node1 keystone_db
solar connect mariadb_service keystone_db '{"root_password": "login_password", "port": "login_port"}'
# solar connect mariadb_service keystone_db_user 'root_password->login_password port->login_port'  # another valid format
solar connect keystone_db keystone_db_user

solar changes stage
solar changes proccess
<uid>
solar orch run-once <uid>
```

You can fiddle with the above configuration like this:
```
solar resource update keystone_db_user '{"user_password": "new_keystone_password"}'
solar resource update keystone_db_user user_password=new_keystone_password   # another valid format

solar changes stage
solar changes proccess
<uid>
solar orch run-once <uid>
```

* Show the connections/graph:
```
solar connections show
solar connections graph
```

You can also limit graph to show only specific resources:

```
solar connections graph --start-with mariadb_service --end-with keystone_db
```

* You can make sure that all input values are correct and mapped without duplicating your values with this command:
```
solar resource validate
```

* Disconnect
```
solar disconnect mariadb_service node1
```

* Tag a resource:
```
solar resource tag node1 test-tags # Remove tags
solar resource tag node1 test-tag --delete
```

# Low level API

## Usage:

Creating resources:

```
from x import resource
node1 = resource.create('node1', 'x/resources/ro_node/', 'rs/', {'ip':'10.0.0.3', 'ssh_key' : '/vagrant/tmp/keys/ssh_private', 'ssh_user':'vagrant'})

node2 = resource.create('node2', 'x/resources/ro_node/', 'rs/', {'ip':'10.0.0.4', 'ssh_key' : '/vagrant/tmp/keys/ssh_private', 'ssh_user':'vagrant'})

keystone_db_data = resource.create('mariadb_keystone_data', 'x/resources/data_container/', 'rs/', {'image' : 'mariadb', 'export_volumes' : ['/var/lib/mysql'], 'ip': '', 'ssh_user': '', 'ssh_key': ''}, connections={'ip' : 'node2.ip', 'ssh_key':'node2.ssh_key', 'ssh_user':'node2.ssh_user'})

nova_db_data = resource.create('mariadb_nova_data', 'x/resources/data_container/', 'rs/', {'image' : 'mariadb', 'export_volumes' : ['/var/lib/mysql'], 'ip': '', 'ssh_user': '', 'ssh_key': ''}, connections={'ip' : 'node1.ip', 'ssh_key':'node1.ssh_key', 'ssh_user':'node1.ssh_user'})
```

to make connection after resource is created use `signal.connect`

To test notifications:

```
keystone_db_data.args    # displays node2 IP

node2.update({'ip': '10.0.0.5'})

keystone_db_data.args   # updated IP
```

If you close the Python shell you can load the resources like this:

```
from x import resource
node1 = resource.load('rs/node1')

node2 = resource.load('rs/node2')

keystone_db_data = resource.load('rs/mariadn_keystone_data')

nova_db_data = resource.load('rs/mariadb_nova_data')
```

Connections are loaded automatically.


You can also load all resources at once:

```
from x import resource
all_resources = resource.load_all('rs')
```

## Dry run

Solar CLI has possibility to show dry run of actions to be performed.
To see what will happen when you run Puppet action, for example, try this:

```
solar resource action keystone_puppet run -d
```

This should print out something like this:

```
EXECUTED:
73c6cb1cf7f6cdd38d04dd2d0a0729f8: (0, 'SSH RUN', ('sudo cat /tmp/puppet-modules/Puppetfile',), {})
3dd4d7773ce74187d5108ace0717ef29: (1, 'SSH SUDO', ('mv "1038cb062449340bdc4832138dca18cba75caaf8" "/tmp/puppet-modules/Puppetfile"',), {})
ae5ad2455fe2b02ba46b4b7727eff01a: (2, 'SSH RUN', ('sudo librarian-puppet install',), {})
208764fa257ed3159d1788f73c755f44: (3, 'SSH SUDO', ('puppet apply -vd /tmp/action.pp',), {})
```

By default every mocked command returns an empty string. If you want it to return
something else (to check how would dry run behave in different situation) you provide
a mapping (in JSON format), something along the lines of:

```
solar resource action keystone_puppet run -d -m "{\"73c\": \"mod 'openstack-keystone'\n\"}"
```

The above means the return string of first command (with hash `73c6c...`) will be
as specified in the mapping. Notice that in mapping you don't have to specify the
whole hash, just it's unique beginning. Also, you don't have to specify the whole
return string in mapping. Dry run executor can read file and return it's contents
instead, just use the `>` operator when specifying hash:

```
solar resource action keystone_puppet run -d -m "{\"73c>\": \"./Puppetlabs-file\"}"
```

## Resource compiling

You can compile all `meta.yaml` definitions into Python code with classes that
derive from `Resource`. To do this run

```
solar resource compile_all
```

This generates file `resources_compiled.py` in the main directory (do not commit
this file into the repo). Then you can import classes from that file, create
their instances and assign values just like these were normal properties.
If your editor supports Python static checking, you will have autocompletion
there too. An example on how to create a node with this:

```
import resources_compiled

node1 = resources_compiled.RoNodeResource('node1', None, {})
node1.ip = '10.0.0.3'
node1.ssh_key = '/vagrant/.vagrant/machines/solar-dev1/virtualbox/private_key'
node1.ssh_user = 'vagrant'
```

## HAProxy deployment (not maintained)

```
cd /vagrant
solar deploy haproxy_deployment/haproxy-deployment.yaml
```

or from Python shell:

```
from solar.core import deployment

deployment.deploy('/vagrant/haproxy_deployment/haproxy-deployment.yaml')
```

