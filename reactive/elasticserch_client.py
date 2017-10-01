from charmhelpers.core import unitdata
from charmhelpers.core.hookenv import (
    config,
    log,
    status_set,
)

from charms.reactive import (
    when,
    when_any,
    when_not,
    set_state,
    remove_state
)

from charms.layer.nginx import configure_site


kv = unitdata.kv()


@when_not('manual.elasticsearch.check.available')
def check_user_provided_elasticsearch():
    status_set('maintenance', 'Checking for elasticsearch config')
    if not config('es-hosts'):
        remove_state('manual.elasticsearch.available')
        log('Manual elasticsearch not configured')
        status_set('active',
                   'Elasticsearch manual configuration NOT available')
    else:
        kv.set('es_hosts', config('es-hosts').split(","))
        set_state('manual.elasticsearch.available')
        remove_state('elasticsearch.client.proxy.available')
        status_set('active', 'Elasticsearch manual configuration available')
    set_state('manual.elasticsearch.check.available')


@when('elasticsearch.available')
def render_elasticsearch_lb(elasticsearch):
    """Write render elasticsearch cluster loadbalancer
    """
    status_set('maintenance',
               'Configuring application for elasticsearch')

    ES_SERVERS = []
    for unit in elasticsearch.list_unit_data():
        ES_SERVERS.append(unit['host'])

    kv.set('es_hosts', ES_SERVERS)

    status_set('active', 'Elasticsearch available')

    remove_state('elasticsearch.broken')
    remove_state('elasticsearch.client.proxy.available')
    set_state('juju.elasticsearch.available')


@when('nginx.available')
@when_any('juju.elasticsearch.available',
          'manual.elasticsearch.available')
@when_not('elasticsearch.client.proxy.available')
def configure_es_proxy_hosts():
    """Write out the nginx config containing the es servers
    """

    ES_SERVERS = []

    for host in kv.get('es_hosts'):
        ES_SERVERS.append({'host': host, 'port': "9200"})

    configure_site('es_cluster', 'es_cluster.conf.tmpl',
                   es_servers=ES_SERVERS)

    set_state('elasticsearch.client.proxy.available')


@when('elasticsearch.client.proxy.available')
@when_not('elasticsearch.lb.proxy.available')
def render_elasticsearch_lb_proxy():
    """Write out elasticsearch lb proxy
    """
    status_set('maintenance', 'Configuring elasticsearch loadbalancing proxy')
    configure_site('es_lb_proxy', 'es_lb_proxy.conf.tmpl')
    status_set('active', 'Elasticsearch loadbalancer/proxy configured')
    set_state('elasticsearch.lb.proxy.available')
    set_state('elasticsearch.client.available')


@when_any('elasticsearch.broken',
          'config.changed.es-hosts')
@when('elasticsearch.lb.proxy.available')
def modify_elasticsearch_state():
    remove_state('manual.elasticsearch.check.available')
    remove_state('juju.elasticsearch.available')
    remove_state('elasticsearch.client.proxy.available')
