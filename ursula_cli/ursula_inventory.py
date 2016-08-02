#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2016, Jesse Keating <jkeating@j2solutions.net>
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations

import argparse
import collections
import json
import logging
import os
import yaml
from ConfigParser import ConfigParser, NoOptionError, NoSectionError

import ansible

from ansible.constants import DEFAULTS, get_config, load_config_file
from ansible.inventory import Inventory
from ansible.inventory.dir import InventoryDirectory, get_file_parser
from ansible.inventory.group import Group
from ansible.parsing.dataloader import DataLoader
from ansible.plugins import vars_loader
from ansible.utils.vars import combine_vars
from ansible.utils.vars import load_extra_vars
from ansible.utils.vars import load_options_vars
from ansible.vars import VariableManager
from ursula_cli.shell import _initialize_logger

LOG = logging.getLogger(__name__)


def deep_update_dict(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = deep_update_dict(d.get(k, {}) or {}, v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


class UrsulaInventory(Inventory):

    def parse_inventory(self, host_list):
        ungrouped = Group('ungrouped')
        all = Group('all')
        all.add_child_group(ungrouped)

        self.groups = dict(all=all, ungrouped=ungrouped)

        # Ensure basedir is inside the directory
        host_list = os.path.join(self.host_list, "hosts")
        self.parser = get_file_parser(host_list, self.groups, self._loader)
        vars_loader.add_directory(self.basedir(), with_subdir=True)

        self._vars_plugins = [x for x in vars_loader.all(self)]

        # our default vars plugin
        default_vars = self._get_defaults()

        # set group vars from group_vars/ files and vars plugins
        for g in self.groups:
            group = self.groups[g]
            group.vars = combine_vars(group.vars,
                                      self.get_group_variables(group.name))
            if default_vars:
                group_vars = group.vars
                group.vars = deep_update_dict(default_vars, group_vars)

            self.get_group_vars(group)

        # get host vars from host_vars/ files and vars plugins
        for host in self.get_hosts(ignore_limits_and_restrictions=True):
            host.vars = combine_vars(host.vars,
                                     self.get_host_variables(host.name))
            self.get_host_vars(host)

    def _get_defaults(self):
        p, cfg_path = load_config_file()
        defaults_file = get_config(p, DEFAULTS, 'var_defaults_file',
                                   'ANSIBLE_VAR_DEFAULTS_FILE', None)
        if not defaults_file:
            return None

        ursula_env = self.host_list
        defaults_path = os.path.join(ursula_env, defaults_file)
        if os.path.exists(defaults_path):
            with open(defaults_path) as fh:
                return yaml.safe_load(fh)
        return None


def run(args):

    env = os.environ.get('URSULA_ENV')
    if not env:
        raise Exception("Environment not provided")

    if not os.path.exists(env):
        raise Exception("Environment '%s' does not exist" % env)

    loader = DataLoader()

    variable_manager = VariableManager()

    inventory = UrsulaInventory(loader, variable_manager, env)

    # populate the dict to output
    result = {}

    # Define the groups and host memberships
    for host in inventory.get_hosts():
        for group in host.get_groups():
            ghosts = result.setdefault(group.name, {'hosts': []})['hosts']
            if host.name not in ghosts:
                result[group.name]['hosts'].append(host.name)

    # Define the group variables (takes defaults into account)
    for group in inventory.groups:
        if group != 'ungrouped':
            groupobj = inventory.get_group(group)
            result[group]['vars'] = groupobj.vars

    # Define the host vars in _meta to avoid --host calls
    result['_meta'] = {'hostvars': inventory._vars_per_host}

    if args.list:
        print(json.dumps(result))


def parse_args():
    parser = argparse.ArgumentParser(description='Inventory script for Ursula')
    parser.add_argument('--list', help='List the inventory',
                        action='store_true', default=True),
    parser.add_argument('--host', help='Show a specific host detail')
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        _initialize_logger()
        run(args)
    except Exception as e:
        LOG.exception(e)


if __name__ == '__main__':
    main()
