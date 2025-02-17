#
# -*- coding: utf-8 -*-
# Copyright 2019 Red Hat Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
The iosxr interfaces fact class
It is in this file the configuration is collected from the device
for a given resource, parsed, and the facts tree is populated
based on the configuration.
"""

from __future__ import absolute_import, division, print_function


__metaclass__ = type

import re

from copy import deepcopy

from ansible_collections.ansible.netcommon.plugins.module_utils.network.common import utils

from ansible_collections.cisco.iosxr.plugins.module_utils.network.iosxr.argspec.interfaces.interfaces import (
    InterfacesArgs,
)
from ansible_collections.cisco.iosxr.plugins.module_utils.network.iosxr.utils.utils import (
    get_interface_type,
)


class InterfacesFacts(object):
    """The iosxr interfaces fact class"""

    def __init__(self, module, subspec="config", options="options"):
        self._module = module
        self.argument_spec = InterfacesArgs.argument_spec
        spec = deepcopy(self.argument_spec)
        if subspec:
            if options:
                facts_argument_spec = spec[subspec][options]
            else:
                facts_argument_spec = spec[subspec]
        else:
            facts_argument_spec = spec

        self.generated_spec = utils.generate_dict(facts_argument_spec)

    def get_config(self, connection):
        return connection.get_config(flags="interface")

    def populate_facts(self, connection, ansible_facts, data=None):
        """Populate the facts for interfaces
        :param module: the module instance
        :param connection: the device connection
        :param data: previously collected conf
        :rtype: dictionary
        :returns: facts
        """
        objs = []
        if not data:
            data = self.get_config(connection)

        # operate on a collection of resource x
        config = ("\n" + data).split("\ninterface ")
        for conf in config:
            if conf:
                obj = self.render_config(self.generated_spec, conf)
                if obj:
                    objs.append(obj)

        facts = {}
        if objs:
            facts["interfaces"] = []
            params = utils.validate_config(
                self.argument_spec,
                {"config": objs},
            )
            for cfg in params["config"]:
                facts["interfaces"].append(utils.remove_empties(cfg))

        ansible_facts["ansible_network_resources"].update(facts)
        return ansible_facts

    def render_config(self, spec, conf):
        """
        Render config as dictionary structure and delete keys from spec for null values
        :param spec: The facts tree, generated from the argspec
        :param conf: The configuration
        :rtype: dictionary
        :returns: The generated config
        """

        config = deepcopy(spec)
        match = re.search(r"^(\S+)", conf)
        if match:
            intf = match.group(1)
            if match.group(1).lower() == "preconfigure":
                match = re.search(r"^(\S+) (.*)", conf)
                if match:
                    intf = match.group(2)

            if get_interface_type(intf) == "unknown":
                return {}
            # populate the facts from the configuration
            config["name"] = intf
            config["description"] = utils.parse_conf_arg(conf, "description")
            if utils.parse_conf_arg(conf, "speed"):
                config["speed"] = int(utils.parse_conf_arg(conf, "speed"))
            if utils.parse_conf_arg(conf, "mtu"):
                config["mtu"] = int(utils.parse_conf_arg(conf, "mtu"))
            config["duplex"] = utils.parse_conf_arg(conf, "duplex")
            enabled = utils.parse_conf_cmd_arg(conf, "shutdown", False)
            config["enabled"] = enabled if enabled is not None else True

        return utils.remove_empties(config)
