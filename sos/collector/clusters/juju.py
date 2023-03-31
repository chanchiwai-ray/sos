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
            ips = []
            units = app_info.get("units")
            if units:
                for unit, unit_info in units.items():
                    ip = unit_info["public-address"]
                    machine = unit_info["machine"]
                    index["units"][unit] = [ip]
                    index["machines"][machine] = [ip]
                    ips.append(ip)
            index["apps"][app] = ips
        return index

    def _filter_by_resource(self, key, resources, model_info):
        ips = set()
        for res in resources:
            ips.update(model_info[key][res])
        return ips

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
            ips = set()
            for key, resource in filters.items():
                ips.update(self._filter_by_resource(key, resource, model_info))
            # If there is no ips after the filters, it means no filter is
            # applied. In this case, get all ips within the model.
            if not ips:
                for _ips in model_info["apps"].values():
                    ips.update(_ips)
            nodes.update(ips)

        return list(nodes)
