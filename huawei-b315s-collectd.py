#! /usr/bin/env python3

import collectd
import os
import requests
import time
import socket
import pprint

from defusedxml import ElementTree as etree
from timeit import default_timer as timer

from urlparse import urljoin

PLUGIN_NAME = '4gmodem'
STATS_PATH = '/api/monitoring/traffic-statistics'
# A dictionary mapping collectd identifiers to XML tags
VALUE_MAPPING = {
    'total_current': '_current_total',
    'rx_current': 'CurrentDownload',
    'tx_current': 'CurrentUpload',
    'uptime_connection': 'CurrentConnectTime',
    'total_total': '_total_total',
    'rx_total': 'TotalDownload',
    'tx_total': 'TotalUpload',
}
DEBUG=False

def log(msg):
    collectd.info('{}: {}'.format(PLUGIN_NAME, msg))

def debug(msg):
    if DEBUG:
        collectd.info('{}: {}'.format(PLUGIN_NAME, msg))

log('loading python plugin: '+PLUGIN_NAME)
_conf = []
def configure(confobj):
    log(pprint.pformat(confobj))
    log('running configure with key={0!s}, children={1!r}'.format(confobj.key, confobj.children))
    config = {c.key: c.values for c in confobj.children}
    log('added config for {0!r}'.format(config))
    _conf.append(config)
    log('resulting config is {0!r}'.format(_conf))

def read(data=None):
    for conf in _conf:
        root = 'http://{}/'.format(conf.get('hostname')[0])
        modem_name = conf.get('modem_name')[0]
        debug('Fetching data from {} for name {}'.format(root, modem_name))
        stats = get_stats(root)

        for k,v in VALUE_MAPPING.items():
            val = collectd.Values(type='derive', type_instance='/'.join([modem_name, k]))
            val.plugin = PLUGIN_NAME
            val.values = [stats.get(v)]
            debug('Dispatching value for {0}, value: {1}'.format(k, stats.get(v)))
            val.dispatch()

collectd.register_config(configure)
collectd.register_read(read)

def get_stats(root):
    session = requests.Session()
    indexr = session.get(root)
    if not indexr.ok:
        log("Index request failed with status {r.status_code}\n  Body:{r.text}".format(r=indexr))

    statsr = session.get(urljoin(root, STATS_PATH))
    if not statsr.ok:
        log("Index request failed with status {r.status_code}\n  Body:{r.text}".format(r=statsr))

    stats_t = etree.fromstring(statsr.content)
    stats = dict()

    for el in list(stats_t):
        stats[el.tag] = el.text

    if stats.get('code'):
        log("XML response contained error\n  Error Code:{r[code]}\n  Message:{r[message]}".format(r=stats))

    generate_calculated_stats(stats)
    return stats

def generate_calculated_stats(stats):
    stats['_current_total'] = int(stats['CurrentDownload']) + int(stats['CurrentUpload'])
    stats['_total_total'] = int(stats['TotalDownload']) + int(stats['TotalUpload'])


