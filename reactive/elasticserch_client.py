from charmhelpers.core import hookenv, unitdata

from charms import reactive

from charms.layer import nginx


kv = unitdata.kv()


@reactive.when_not('manual.elasticsearch.check.available')
def check_user_provided_elasticsearch():
    hookenv.status_set('maintenance', 'Checking for elasticsearch config')
    if not hookenv.config('es-hosts'):
        hookenv.log('Manual elasticsearch not configured')
        hookenv.status_set('active',
                           'Elasticsearch manual configuration NOT available')
        reactive.clear_flag('manual.elasticsearch.available')
        reactive.clear_flag('juju.elasticsearch.available')
    else:
        hookenv.log('Manual elasticsearch configured')
        hookenv.status_set('active',
                           'Elasticsearch manual configuration available')

        kv.set('es_hosts', hookenv.config('es-hosts').split(","))

        reactive.set_flag('manual.elasticsearch.available')

        reactive.clear_flag('elasticsearch.client.proxy.available')

    reactive.set_flag('manual.elasticsearch.check.available')


@reactive.when('endpoint.elasticsearch.available')
def render_elasticsearch_lb():
    """Write render elasticsearch cluster loadbalancer
    """
    hookenv.status_set('maintenance',
                       'Configuring application for elasticsearch')

    ES_SERVERS = []
    for es in reactive.endpoint_from_flag(
       'endpoint.elasticsearch.available').list_unit_data():
            ES_SERVERS.append("{}:{}".format(es['host'], es['port']))

    kv.set('es_hosts', ES_SERVERS)

    hookenv.status_set('active', 'Elasticsearch available')

    reactive.set_flag('juju.elasticsearch.available')
    reactive.clear_flag('elasticsearch.client.proxy.available')
    reactive.clear_flag('endpoint.elasticsearch.available')


@reactive.when('nginx.available')
@reactive.when_any('juju.elasticsearch.available',
                   'manual.elasticsearch.available')
@reactive.when_not('elasticsearch.client.proxy.available')
def configure_es_proxy_hosts():
    """Write out the nginx config containing the es servers
    """
    hookenv.status_set('maintenance',
                       'Configuring elasticsearch loadbalancing proxy')

    nginx.configure_site('es_cluster', 'es_cluster.conf.tmpl',
                         es_servers=kv.get('es_hosts'))

    hookenv.status_set('active',
                       'Elasticsearch loadbalancer/proxy configured')
   

    reactive.clear_flag('juju.elasticsearch.available')
    reactive.set_flag('elasticsearch.client.proxy.available')


@reactive.when('nginx.available',
               'elasticsearch.client.proxy.available')
@reactive.when_not('elasticsearch.lb.proxy.available')
def render_elasticsearch_lb_proxy():
    """Write out elasticsearch lb proxy
    """
    nginx.configure_site('es_lb_proxy', 'es_lb_proxy.conf.tmpl')
    reactive.set_flag('elasticsearch.lb.proxy.available')


@reactive.when_any('juju.elasticsearch.available',
                   'manual.elasticsearch.available')
@reactive.when('elasticsearch.lb.proxy.available',
               'elasticsearch.client.proxy.available')
def set_es_client_avail():
    reactive.set_flag('elasticsearch.client.available')


@reactive.when_not('elasticsearch.client.available')
def need_relation_configuration_status():
    hookenv.status_set('blocked',
                       "Need relation/configuration for Elasticsearch")
    return


@reactive.when('config.changed.es-hosts')
def re_render_nginx_server_conf():
    reactive.clear_flag('manual.elasticsearch.check.available')


@reactive.when('elasticsearch.client.available')
@reactive.when_not('endpoint.elasticsearch.joined',
                   'manual.elasticsearch.available')
def clear_client_available():
    reactive.clear_flag('elasticsearch.client.available')
