# Copyright (c) 2023 Canonical Ltd., Chi Wai Chan <chiwai.chan@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.


import subprocess

from sos.collector.exceptions import JujuNotInstalledException
from sos.collector.transports import RemoteTransport
from sos.utilities import sos_get_command_output


class JujuSSH(RemoteTransport):
    """
    A "transport" that leverages `juju ssh` to perform commands on the remote
    hosts.

    This transport is expected to be used in juju managed environment, and the
    user should have the necessary credential for accessing the controller.
    When using this transport, the --nodes option will be expected to be a
    comma separated machine IDs or unit names, **not** IP addr, since `juju
    ssh` identifies the ssh target by machine ID or unit name.

    Examples:

    sos collect --nodes 0,1,2 --no-local --transport juju --batch
    sos collect --nodes ubuntu/0,ubuntu/1 --no-local --transport juju --batch

    """

    name = "juju_ssh"

    def _check_juju_installed(self):
        cmd = "juju version"
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError:
            self.log_error("Failed to check `juju` version")
            raise JujuNotInstalledException
        return True

    def _chmod(self, fname):
        cmd = f"{self.remote_exec} chmod o+r {fname}"
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError:
            self.log_error(f"Failed to make {fname} world-readable")
            raise
        return True

    def _connect(self, password=''):
        self._connected = self._check_juju_installed()
        return self._connected

    def _disconnect(self):
        return True

    @property
    def connected(self):
        return self._connected

    @property
    def remote_exec(self):
        return f"juju ssh {self.address} sudo"

    def _retrieve_file(self, fname, dest):
        self._chmod(fname)  # juju scp need the archieve to be world-readable
        cmd = f"juju scp -- -r {self.address}:{fname} {dest}"
        res = sos_get_command_output(cmd)
        return res['status'] == 0
