if __name__ != '__main__':
    import collectd

import os
import sys
import time

PLUGIN_NAME="file_age"
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
    log('running configure with key={0!s}, children={1!r}'.format(confobj.key, confobj.children))
    config = {c.key: c.values for c in confobj.children}
    log('added config for {0!r}'.format(config))
    _conf.append(config)
    log('resulting config is {0!r}'.format(_conf))

def read(data=None):
    for conf in _conf:
        path = conf.get("path")[0]
        debug("Getting mtime for file {}".format(path))
        mtime = os.path.getmtime(path)
        age = time.time() - mtime
        instance_name = conf.get("name", [os.path.basename(path)])[0]
        value = collectd.Values(
            type="gauge",
            type_instance="age",
            plugin_instance=instance_name,
            plugin=PLUGIN_NAME,
            values=[ age ],
        )
        value.dispatch()

if __name__ == "__main__":
    pass
else:
    collectd.register_config(configure)
    collectd.register_read(read)
