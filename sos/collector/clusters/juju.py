# Copyright (c) 2023 Canonical Ltd., Chi Wai Chan <chiwai.chan@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import collections
from sos.collector.clusters import Cluster


def _parse_option_string(strings):
    """Parse commad separated string."""
    if not strings:
        return []
    return [string.strip() for string in strings.split(",")]


class juju(Cluster):
    """
    The juju cluster profile is intended to be used on juju managed clouds.
    It"s assumed that `juju` is installed on the machine where `sos` is called,
    and that the juju user has superuser privilege to the current controller.

    By default, the sos reports will be collected from all the applications in
    the current model. If necessary, you can filter the nodes by models /
    applications / units / machines with cluster options.

    Example:

    sos collect --cluster-type juju -c "juju.models=sos" -c "juju.apps=a,b,c"

    """

    cmd = "juju"
    cluster_name = "Juju Managed Clouds"
    option_list = [
        ("apps", "", "Filter node list by apps (comma separated)."),
        ("units", "", "Filter node list by units (comma separated)."),
        ("models", "", "Filter node list by moedls (comma separated)."),
        ("machines", "", "Filter node list by machines (comma separated)."),
    ]

    def _get_model_info(self, model_name):
        model_option = f"-m {model_name}" if model_name else ""
        format_option = "--format json"
        status_cmd = f"{self.cmd} status {model_option} {format_option}"

        juju_status = None
        res = self.exec_primary_cmd(status_cmd)
        if res["status"] == 0:
            juju_status = json.loads(res["output"])
        else:
            raise Exception(f"{status_cmd} did not return usable output")

        index = collections.defaultdict(dict)
        for app, app_info in juju_status["applications"].items():
            nodes = []
            units = app_info.get("units")
            if units:
                for unit, unit_info in units.items():
                    machine = unit_info["machine"]
                    node = f"{model_name}:{machine}"
                    index["units"][unit] = [node]
                    index["machines"][machine] = [node]
                    nodes.append(node)
            index["apps"][app] = nodes
        return index

    def _filter_by_resource(self, key, resources, model_info):
        nodes = set()
        for resource in resources:
            nodes.update(model_info[key].get(resource, []))
        return nodes

    def set_transport_type(self):
        """Dynamically change transport to 'juju'."""
        return "juju"

    def get_nodes(self):
        """Get the public addresses from `juju status`."""
        models = _parse_option_string(self.get_option("models"))
        apps = _parse_option_string(self.get_option("apps"))
        units = _parse_option_string(self.get_option("units"))
        machines = _parse_option_string(self.get_option("machines"))
        filters = {"apps": apps, "units": units, "machines": machines}

        if not models:
            models = [""]  # use current model by default

        nodes = set()

        for model in models:
            model_info = self._get_model_info(model)
            if not any(filters.values()):
                for _nodes in model_info["apps"].values():
                    nodes.update(_nodes)
            else:
                for key, resource in filters.items():
                    _nodes = self._filter_by_resource(
                        key, resource, model_info
                    )
                    nodes.update(_nodes)

        return list(nodes)
