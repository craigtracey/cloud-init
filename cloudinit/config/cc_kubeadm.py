# Copyright (C) 2018 Craig Tracey <craigtracey@gmail.com>
#
# This file is part of cloud-init. See LICENSE file for license information.

# converge a master like so:
# kubeadm:
#   path: /home/user/kubeadm
#   role:
#     type: master
#     token: d3adb33f
#
# converge a worker like so:
# kubeadm:
#   path: /home/user/kubeadm
#   role:
#     type: worker
#     endpoint: 1.1.1.1:6443
#     discovery_token: 3adb33f

import os
import re

from cloudinit import util
from cloudinit.config.schema import validate_cloudconfig_schema
from cloudinit.distros import ALL_DISTROS
from cloudinit.settings import PER_INSTANCE

frequency = PER_INSTANCE
distros = [ALL_DISTROS]

SCHEMA = {
    'id': 'cc_kubeadm',
    'name': 'kubeadm',
    'title': 'bootstrap a kubernetes node',
    'distros': distros,
    'frequency': PER_INSTANCE,
    'type': 'object',
    'properties': {
        'type': 'object',
        'kubeadm': {
            'type': 'object',
            'required': ['role'],
            'properties': {
                'path': {'type': 'string'},
                'role': {
                    'type': 'object',
                    'properties': {
                        'type': {'enum': ['master', 'worker']}
                    },
                    'anyOf': [
                        {
                            'properties': {
                                'type': {'enum': ['master']},
                            },
                            'required': []
                        },
                        {
                            'properties': {
                                'type': {'enum': ['worker']},
                            },
                            'required': ['endpoint']
                        },
                    ],
                    'additionalProperties': False,
                }
            },
            'additionalProperties': False,
        },
        'additionalProperties': False,
    },
    'additionalProperties': False,
}


DEFAULT_KUBEADM_PATH = '/usr/bin/kubeadm'


class KubernetesCommonRole(object):

    def __init__(self, **kwargs):
        for param in self.OPTIONAL_PARAMS.keys() + self.REQUIRED_PARAMS.keys():
            if param in kwargs:
                setattr(self, param, kwargs[param])

    def _generate_command(self, param):
        if hasattr(self, param):
            return ["--%s" % re.sub('_', '-', param), getattr(self, param)]
        return []

    def command(self):
        cmd = [self.KUBEADM_COMMAND]
        for param in sorted(self.OPTIONAL_PARAMS.keys()):
            cmd += self._generate_command(param)
        return cmd


class KubeadmMasterRole(KubernetesCommonRole):

    KUBEADM_COMMAND = 'init'
    REQUIRED_PARAMS = {}
    OPTIONAL_PARAMS = {
        'apiserver_advertise_address': {'type': 'string'},
        'apiserver_bind_port': {'type': 'integer'},
        'apiserver_cert_extra_sans': {'type': 'array', 'items': {'type': {'type': 'string'}}},
        'cert_dir': {'type': 'string'},
        'config': {'type': 'string'},
        'cri_socket': {'type': 'string'},
        'feature_gates': {'type': 'string'},
        'ignore_preflight_errors': {'type': 'array', 'items': {'type': {'type': 'string'}}},
        'kubernetes_version': {'type': 'string'},
        'node_name': {'type': 'string'},
        'pod_network_cidr': {'type': 'string'},
        'service_cidr': {'type': 'string'},
        'service_dns_domain': {'type': 'string'},
        'skip_token': {'type': 'boolean'},
        'token': {'type': 'string'},
        'token_ttl': {'type': 'integer'},
    }


class KubeadmWorkerRole(KubernetesCommonRole):

    KUBEADM_COMMAND = 'join'
    REQUIRED_PARAMS = {
        'endpoint': {'type': 'string'},
    }
    OPTIONAL_PARAMS = {
        'config': {'type': 'string'},
        'cri_socket': {'type': 'string'},
        'discovery_file': {'type': 'string'},
        'discovery_token': {'type': 'string'},
        'discovery_token_ca_cert_hash': {'type': 'string'},
        'discovery_token_unsafe_skip_ca_verification': {'type': 'boolean'},
        'feature_gates': {'type': 'string'},
        'ignore_preflight_errors': {'type': 'array', 'items': {'type': 'string'}},
        'node_name': {'type': 'string'},
        'tls_bootstrap_token': {'type': 'string'},
        'token': {'type': 'string'},
    }

    def command(self):
        cmd = super(KubeadmWorkerRole, self).command()
        cmd += [self.endpoint]
        return cmd


class KubeadmConfig(object):

    KUBEADM_ROLES = {
        'master': KubeadmMasterRole,
        'worker': KubeadmWorkerRole,
    }

    def __init__(self, role, path=DEFAULT_KUBEADM_PATH):
        self.path = path

        if 'type' not in role:
            raise Exception("Missing 'role' type")
        if role['type'] not in self.KUBEADM_ROLES.keys():
            raise Exception("Unknown role: %s" % role['type'])

        self.role = self.KUBEADM_ROLES[role['type']](**role)

    def command(self):
        return [self.path] + self.role.command()


def update_schema():
    schema = SCHEMA
    s = schema['properties']['kubeadm']['properties']['role']['properties']
    r = schema['properties']['kubeadm']['properties']['role']['anyOf']
    for param, type in KubeadmMasterRole.OPTIONAL_PARAMS.items():
        s[param] = type
    for param, type in KubeadmMasterRole.REQUIRED_PARAMS.items():
        s[param] = type
        r[0]["required"].append(param)

    for param, type in KubeadmWorkerRole.OPTIONAL_PARAMS.items():
        s[param] = type
    for param, type in KubeadmWorkerRole.REQUIRED_PARAMS.items():
        s[param] = type
        r[1]["required"].append(param)
    return schema


def run_kubeadm(cmd):
    util.subp(cmd, capture=True, shell=True)


def handle(name, cfg, cloud, log, _args):
    """Handler method activated by cloud-init."""

    if 'kubeadm' not in cfg:
        log.debug("Skipping 'kubeadm' module as there is not config")
        return

    schema = update_schema()
    validate_cloudconfig_schema(cfg, schema, strict=True)

    config = None
    try:
        config = KubeadmConfig(**cfg['kubeadm'])
    except Exception as e:
        log.debug("Error parsing config: %s", e)
        log.error("Could not parse kubeadm configuration")
        return

    if not os.path.isfile(config.path):
        log.error("kubeadm is not installed. Failing.")
        return

    try:
        cmd = config.command()
        run_kubeadm(cmd)
    except Exception as e:
        log.error("Failed to run kubeadm: %s" % e)
