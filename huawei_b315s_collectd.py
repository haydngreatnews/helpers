#! /usr/bin/env python3

if __name__ != '__main__':
    import collectd

import os
import sys
import time
import socket
import pprint
from timeit import default_timer as timer

import requests
from defusedxml import ElementTree as etree

from urlparse import urljoin

"""
Make sure that you have installed all the relevant python
modules - At this stage, I think the only non-core modules
necessary are defusedxml and requests, which should be
available in your system's package manager.

In Ubuntu, these packages are called python-defusedxml and
python-requests respectively. Your distro may vary.

If you wish to check the script has everything it needs,
you may call this script directly, and it will output the
data it fetches from your modem (or maybe fail with a
helpful error message).

You can call it like:
`python huawei_b315s_collectd.py http://192.168.1.254/`

Create a folder for collectd plugins, I chose
`/var/lib/collectd/plugins/python/`.

Copy this file there, and add something like the following
config snippet to collectd.

```
<Plugin python>
        ModulePath "/var/lib/collectd/plugins/python/"
        LogTraces true
        Import "huawei_b315s_collectd"
        <Module huawei_b315s_collectd>
                hostname "192.168.1.254"
                modem_name "spark"
        </Module>
</Plugin>
```

Substituting IP addresses and modem names as appropriate to
your network. You may repeat this Module block multiple
times if you have more modems connected that you wish to
monitor.

"""

PLUGIN_NAME = '4gmodem'

ENDPOINTS = {
    'traffic': '/api/monitoring/traffic-statistics',
    'monthly': '/api/monitoring/month_statistics',
    'signal': '/api/device/signal',
}

def cleanup_db(measure):
    measure = measure.replace('dBm','')
    measure = measure.replace('dB','')
    measure = measure.replace('>=','')
    return float(measure)

# A dictionary mapping collectd identifiers to XML tags
VALUE_MAPPING = {
    # Traffic readings from main stats
    'uptime_connection': {'field': 'CurrentConnectTime', 'type': 'gauge'},
    'total_bytes': {'field': '_total_total', 'type': 'derive'},
    'rx_bytes': {'field': 'TotalDownload', 'type': 'derive'},
    'tx_bytes': {'field': 'TotalUpload', 'type': 'derive'},
    # Traffic from monthly stats
    'month_rx': {'field': 'CurrentMonthDownload', 'type': 'gauge'},
    'month_tx': {'field': 'CurrentMonthUpload', 'type': 'gauge'},
    # Signal related measures
    'snr': {'field': 'sinr', 'type': 'gauge', 'transform': cleanup_db},
    'rssi': {'field': 'rssi', 'type': 'gauge', 'transform': cleanup_db},
    'rsrp': {'field': 'rsrp', 'type': 'gauge', 'transform': cleanup_db},
    'band': {'field': 'band', 'type': 'gauge'},
    'ul_freq': {'field': 'lteulfreq', 'type': 'gauge'},
}

DEBUG=False

def log(msg):
    if 'collectd' in sys.modules:
        collectd.info('{}: {}'.format(PLUGIN_NAME, msg))
    else:
        print(msg)

def debug(msg):
    if DEBUG:
        log('{}: {}'.format(PLUGIN_NAME, msg))

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
            value_data = stats.get( v.get('field') )
            if 'transform' in v:
                value_data = v['transform'](value_data)

            if (value_data):
                val = collectd.Values(
                    type=v.get('type'),
                    type_instance=k,
                    plugin_instance=modem_name,
                    plugin=PLUGIN_NAME,
                    values= [ value_data ]
                )
                debug('Dispatching value for {0.type_instance}, value: {0.values}'.format(val))
                val.dispatch()

def get_stats(root):

    # Get a session authorization by visiting the homepage of the router
    session = requests.Session()
    indexr = session.get(root)
    if not indexr.ok:
        log("Index request failed with status {r.status_code}\n  Body:{r.text}".format(r=indexr))

    # Go fetch each of the URLs in the hash
    # and merge the resulting dict with the
    # overall stats
    stats = dict()

    for stats_type, endpoint in ENDPOINTS.items():
        response = session.get(urljoin(root, endpoint))
        if not response.ok:
            log("Index request failed with status {r.status_code}\n  Body:{r.text}".format(r=response))

        xml_t = etree.fromstring(response.content)

        result = {}
        for el in list(xml_t):
            result[el.tag] = el.text

        if stats.get('code'):
            log("XML response contained error\n  Error Code:{r[code]}\n  Message:{r[message]}".format(r=stats))
        else:
            stats.update(result)

    generate_calculated_stats(stats)
    return stats

def generate_calculated_stats(stats):
    stats['_current_total'] = int(stats['CurrentDownload']) + int(stats['CurrentUpload'])
    stats['_total_total'] = int(stats['TotalDownload']) + int(stats['TotalUpload'])

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Must supply a URL")
        sys.exit(1)
    root_url = sys.argv.pop(1)
    stats = get_stats(root_url)
    print('Dumping stats...')
    pprint.pprint(stats)
    for k,v in VALUE_MAPPING.items():
        value_data = stats.get( v.get('field') )
        if 'transform' in v:
            value_data = v['transform'](value_data)
        val = dict(
            type=v.get('type'),
            type_instance=k,
            plugin_instance='modem_name supplied',
            plugin=PLUGIN_NAME,
            values= [ value_data ]
        )
        print('Prepared value:')
        pprint.pprint(val)
else:
    collectd.register_config(configure)
    collectd.register_read(read)

