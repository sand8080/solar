$resource = hiera('{{ resource_name }}')

$ip = $resource['input']['ip']['value']
$admin_token = $resource['input']['admin_token']['value']
$db_user = $resource['input']['db_user']['value']
$db_password = $resource['input']['db_password']['value']
$db_name = $resource['input']['db_name']['value']
$admin_port = $resource['input']['admin_port']['value']
$port = $resource['input']['port']['value']

class {'keystone':
  package_ensure       => 'present',
  verbose              => True,
  catalog_type         => 'sql',
  admin_token          => $admin_token,
  database_connection  => "mysql://$db_user:$db_password@$ip/$db_name",
  public_port          => "$port",
  token_driver         => 'keystone.token.backends.kvs.Token'
}

#file { '/etc/keystone/keystone-exports':
#  owner     => 'root',
#  group     => 'root',
#  content   => template('keystone/exports.erb')
#}