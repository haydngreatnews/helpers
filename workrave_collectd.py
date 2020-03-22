"""
If you wish to check the script has everything it needs, you
may call this script directly, and it will output the data
it fetches from workrave (or maybe fail with a helpful error
message).

You can call it like:
`python workrave_collectd.py ~/.workrave/todaystats`

Create a folder for collectd plugins, I chose
`/var/lib/collectd/plugins/python/`.

Copy this file there, and add something like the following
config snippet to collectd.

```
<Plugin python>
        ModulePath "/var/lib/collectd/plugins/python/"
        LogTraces true
        Import "workrave_collectd"
        <Module workrave_collectd>
                todaystats_path "/home/<user>/.workrave/todaystats"
                name "haydn"
                dpi "123" # optional, defaults to 72
        </Module>
</Plugin>
```

Substituting the file path, name and dpi as appropriate. You
may repeat the Module block multiple times if you have
multiple workrave files you wish to read, but ensure you
supply different values for the "name" field

"""

import sys

if __name__ != "__main__":
    import collectd

PLUGIN_NAME = "workrave"
DEBUG = False
DEFAULT_DPI = 72

MISC_ROW_KEYS = [
    "_line_marker",
    "_num_stats",
    "active_time",
    "mouse_distance_px",
    "mouse_drag_distance_px",
    "mouse_movement_time",
    "mouse_clicks",
    "keystrokes",
]


def log(msg):
    if "collectd" in sys.modules:
        collectd.info("{}: {}".format(PLUGIN_NAME, msg))
    else:
        print(msg)


def debug(msg):
    if DEBUG:
        log("{}: {}".format(PLUGIN_NAME, msg))


log("loading python plugin: " + PLUGIN_NAME)

_conf = []


def configure(confobj):
    log(
        "running configure with key={0!s}, children={1!r}".format(
            confobj.key, confobj.children
        )
    )
    config = {c.key: c.values for c in confobj.children}
    log("added config for {0!r}".format(config))
    _conf.append(config)
    log("resulting config is {0!r}".format(_conf))


def values_from_file(file_path):
    debug("Opening file {}".format(file_path))
    stats_content = open(file_path).read()
    stats = None
    for line in stats_content.split("\n"):
        # Skip the break lines
        if not line.startswith("m"):
            continue
        line_parts = line.split(" ")
        stats = dict(zip(MISC_ROW_KEYS, line_parts))
        break

    return stats


def postprocess_stats(stats, conf):
    # Strip out the _ keys
    processed_stats = {
        key: value for key, value in stats.items() if not key.startswith("_")
    }

    dpi = int(conf.get("dpi", [DEFAULT_DPI])[0])
    processed_stats["mouse_distance_mm"] = (
        int(stats.get("mouse_distance_px", 0)) / dpi * 25.4
    )
    processed_stats["mouse_drag_distance_mm"] = (
        int(stats.get("mouse_drag_distance_px", 0)) / dpi * 25.4
    )

    return processed_stats


def read(data=None):
    for conf in _conf:
        path = conf.get("todaystats_path")[0]
        stats = values_from_file(path)
        if stats is None:
            log("Could not find stats in file {}".format(path))
        stats = postprocess_stats(stats, conf)

        instance_name = conf.get("name")[0]
        if not instance_name:
            log("Could not report for {}, name not configured".format(path))
            continue

        for key, stat_value in stats.items():
            value = collectd.Values(
                type="counter",
                type_instance=key,
                plugin_instance=instance_name,
                plugin=PLUGIN_NAME,
                values=[stat_value],
            )
            value.dispatch()


if __name__ == "__main__":
    path = sys.argv[2]
    stats = values_from_file(path)
    if stats is None:
        log("Could not find stats in file {}".format(path))
    stats = postprocess_stats(stats, {"dpi": 123})
    log("Results:")
    log(stats)
else:
    collectd.register_config(configure)
    collectd.register_read(read)
