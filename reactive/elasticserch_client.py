from charmhelpers.core import unitdata
from charmhelpers.core.hookenv import (
    config,
    log,
    status_set,
)

from charms.reactive import (
    endpoint_from_flag,
    when,
    when_any,
    when_not,
    set_flag,
    clear_flag
)

from charms.layer.nginx import configure_site


kv = unitdata.kv()


@when_not('manual.elasticsearch.check.available')
def check_user_provided_elasticsearch():
    status_set('maintenance', 'Checking for elasticsearch config')
    if not config('es-hosts'):
        clear_flag('manual.elasticsearch.available')
        log('Manual elasticsearch not configured')
        status_set('active',
                   'Elasticsearch manual configuration NOT available')
    else:
        kv.set('es_hosts', config('es-hosts').split(","))
        set_flag('manual.elasticsearch.available')
        clear_flag('elasticsearch.client.proxy.available')
        status_set('active', 'Elasticsearch manual configuration available')
    set_flag('manual.elasticsearch.check.available')


@when('elasticsearch.available')
def render_elasticsearch_lb():
    """Write render elasticsearch cluster loadbalancer
    """
    status_set('maintenance',
               'Configuring application for elasticsearch')

    ES_SERVERS = []
    for application in endpoint_from_flag('elasticsearch.available'):
        for unit in application['hosts']:
            ES_SERVERS.append("{}:{}".format(unit['host'], unit['port']))

    kv.set('es_hosts', ES_SERVERS)

    status_set('active', 'Elasticsearch available')

    clear_flag('elasticsearch.broken')
    clear_flag('elasticsearch.client.proxy.available')
    set_flag('juju.elasticsearch.available')


@when('nginx.available')
@when_any('juju.elasticsearch.available',
          'manual.elasticsearch.available')
@when_not('elasticsearch.client.proxy.available')
def configure_es_proxy_hosts():
    """Write out the nginx config containing the es servers
    """
    status_set('maintenance', 'Configuring elasticsearch loadbalancing proxy')

    configure_site('es_cluster', 'es_cluster.conf.tmpl',
                   es_servers=kv.get('es_hosts'))

    set_flag('elasticsearch.client.proxy.available')


@when('elasticsearch.client.proxy.available')
@when_not('elasticsearch.lb.proxy.available')
def render_elasticsearch_lb_proxy():
    """Write out elasticsearch lb proxy
    """
    configure_site('es_lb_proxy', 'es_lb_proxy.conf.tmpl')
    status_set('active', 'Elasticsearch loadbalancer/proxy configured')
    set_flag('elasticsearch.lb.proxy.available')
    set_flag('elasticsearch.client.available')


@when_any('elasticsearch.broken',
          'config.changed.es-hosts')
@when('elasticsearch.lb.proxy.available')
def modify_elasticsearch_state():
    clear_flag('manual.elasticsearch.check.available')
    clear_flag('juju.elasticsearch.available')
    clear_flag('elasticsearch.client.proxy.available')
