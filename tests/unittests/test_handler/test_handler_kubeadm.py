import copy
import logging

from cloudinit import cloud
from cloudinit.config import cc_kubeadm
from cloudinit import distros, helpers
from cloudinit.sources import DataSourceNone
from cloudinit.tests.helpers import CiTestCase, mock

LOG = logging.getLogger(__name__)

BASE_MASTER_CONFIG = {
    "kubeadm": {
        "role": {
            "type": "master"
        }
    }
}

BASE_WORKER_CONFIG = {
    "kubeadm": {
        "role": {
            "type": "worker",
            "endpoint": "1.1.1.1:6443",
            "discovery_token": "d3adb33f",
        }
    }
}

class TestKubeadm(CiTestCase):

    def setUp(self):
        self._command = None
        self.patcher = mock.patch('cloudinit.config.cc_kubeadm.run_kubeadm',
                                  side_effect=self._fake_run_kubeadm)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def fetch_cloud(self, distro_kind):
        cls = distros.fetch(distro_kind)
        paths = helpers.Paths({})
        distro = cls(distro_kind, {}, paths)
        ds = DataSourceNone.DataSourceNone({}, distro, paths, None)
        return cloud.Cloud(ds, paths, {}, distro, None)

    def _fake_run_kubeadm(self, command):
        self._command = command

    @mock.patch('os.path.isfile')
    def _test_run(self, cfg, expected, kubeadm_exists=None):
        kubeadm_exists.return_code = True
        cc_kubeadm.handle('kubeadm', cfg, self.fetch_cloud('ubuntu'), LOG, [])
        if expected:
            self.assertListEqual(self._command, expected)

    @mock.patch('os.path.isfile')
    def test_kubeadm_path(self, kubeadm_exists=None):
        kubeadm_exists.return_code = True
        cfg = copy.deepcopy(BASE_MASTER_CONFIG)
        cfg['kubeadm']['path'] = "/some/path"
        cc_kubeadm.handle('kubeadm', cfg, self.fetch_cloud('ubuntu'), LOG, [])
        self.assertEqual(self._command[0], "/some/path")

    def test_master_command(self):
        cfg = copy.deepcopy(BASE_MASTER_CONFIG)
        expected = [
            "/usr/bin/kubeadm",
            "init",
        ]
        self._test_run(cfg, expected)

    def test_master_command_bootstrap_token(self):
        cfg = copy.deepcopy(BASE_MASTER_CONFIG)
        cfg["kubeadm"]["role"]["token"] = "d3adb33f"
        expected = [
            "/usr/bin/kubeadm",
            "init",
            "--token",
            "d3adb33f"
        ]
        self._test_run(cfg, expected)

    def test_worker_command(self):
        cfg = copy.deepcopy(BASE_WORKER_CONFIG)
        expected = [
            "/usr/bin/kubeadm",
            "join",
            "--discovery-token",
            "d3adb33f",
            "1.1.1.1:6443",
        ]
        self._test_run(cfg, expected)

    def test_worker_command_discovery_token_hash(self):
        cfg = copy.deepcopy(BASE_WORKER_CONFIG)
        cfg["kubeadm"]["role"]["discovery_token_ca_cert_hash"] = "somehash"
        expected = [
            "/usr/bin/kubeadm",
            "join",
            "--discovery-token",
            "d3adb33f",
            "--discovery-token-ca-cert-hash", 
            "somehash",
            "1.1.1.1:6443",
        ]
        self._test_run(cfg, expected)