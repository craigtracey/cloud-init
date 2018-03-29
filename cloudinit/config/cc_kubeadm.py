# Copyright (C) 2018 Craig Tracey <craigtracey@gmail.com>
#
# This file is part of cloud-init. See LICENSE file for license information.

#import itertools
#import json
import os

#from cloudinit import templater
#from cloudinit import url_helper
#from cloudinit import util

DEFAULT_KUBEADM_PATH = '/usr/bin/kubeadm'


def kubeadm_installed():
    if not os.path.isfile(DEFAULT_KUBEADM_PATH):
        return False
    return True


def handle(name, cfg, cloud, log, _args):
    """Handler method activated by cloud-init."""

    if 'kubeadm' not in cfg:
        log.debug("Skipping 'kubeadm' module as there is not config")
        return
