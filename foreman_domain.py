#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Ansible module to manage Foreman domain resources.
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: foreman_domain
short_description: Manage Foreman Domains using Foreman API v2
description:
- Create and delete Foreman Domain using Foreman API v2
options:
  name:
    description: Domain name
    required: true
  fullname:
    description: Description of the domain
    required: false
    default: None
  dns_proxy:
    description: dns_proxy
  state:
    description: Domain state
    required: false
    default: present
    choices: ["present", "absent"]
  organizations:
    description: List of organizations the domain should be assigned to
    required: false
  locations:
    description: List of locations the domain should be assigned to
    required: false
  foreman_host:
    description: Hostname or IP address of Foreman system
    required: false
    default: 127.0.0.1
  foreman_port:
    description: Port of Foreman API
    required: false
    default: 443
  foreman_user:
    description: Username to be used to authenticate on Foreman
    required: true
    default: None
  foreman_pass:
    description: Password to be used to authenticate user on Foreman
    required: true
    default: None
  foreman_ssl:
    description: Enable SSL when connecting to Foreman API
    required: false
    default: true
notes:
- Requires the python-foreman package to be installed. See https://github.com/Nosmoht/python-foreman.
version_added: "2.0"
author: "Thomas Krahn (@nosmoht)"
'''

EXAMPLES = '''
- name: Ensure example.com
  foreman_domain:
    name: example.com
    fullname: Example domain
    state: present
    organizations:
    - Torchlight
    locations:
    - Cardiff
    - London
    foreman_host: 127.0.0.1
    foreman_port: 443
    foreman_user: admin
    foreman_pass: secret
'''

try:
    from foreman.foreman import *
except ImportError:
    foremanclient_found = False
else:
    foremanclient_found = True

try:
    from ansible.module_utils.foreman_utils import *

    has_import_error = False
except ImportError as e:
    has_import_error = True
    import_error_msg = str(e)


def domains_equal(data, domain, comparable_keys):
    if not all(data.get(key, None) == domain.get(key, None) for key in comparable_keys):
        return False
    if not organizations_equal(data, domain):
        return False
    if not locations_equal(data, domain):
        return False
    return True


def get_resources(resource_type, resource_specs, theforeman):
    result = []
    for item in resource_specs:
        search_data = dict()
        if isinstance(item, dict):
            for key in item:
                search_data[key] = item[key]
        else:
            search_data['name'] = item
        try:
            resource = theforeman.search_resource(resource_type=resource_type, data=search_data)
            if not resource:
                module.fail_json(
                    msg='Could not find resource type {resource_type} defined as {spec}'.format(
                        resource_type=resource_type,
                        spec=item))
            result.append(resource)
        except ForemanError as e:
            module.fail_json(msg='Could not search resource type {resource_type} defined as {spec}: {error}'.format(
                resource_type=resource_type, spec=item, error=e.message))
    return result


def ensure(module):
    comparable_keys = ['name', 'fullname']
    name = module.params['name']
    fullname = module.params['fullname']
    state = module.params['state']
    dns_proxy = module.params['dns_proxy']
    organizations = module.params['organizations']
    locations = module.params['locations']

    theforeman = init_foreman_client(module)

    data = {'name': name}

    try:
        domain = theforeman.search_domain(data=data)
        if domain:
            domain = theforeman.get_domain(id=domain.get('id'))
    except ForemanError as e:
        module.fail_json(msg='Could not get domain: {0}'.format(e.message))

    if organizations:
        data['organization_ids'] = get_organization_ids(module, theforeman, organizations)

    if locations:
        data['location_ids'] = get_location_ids(module, theforeman, locations)

    data['fullname'] = fullname
    if dns_proxy:
        data['dns_id'] = get_resources(resource_type='smart_proxies', resource_specs=[dns_proxy],
                                       theforeman=theforeman)[0].get('id')

    if not domain and state == 'present':
        try:
            domain = theforeman.create_domain(data=data)
            return True, domain
        except ForemanError as e:
            module.fail_json(msg='Could not create domain: {0}'.format(e.message))

    if domain:
        if state == 'absent':
            try:
                domain = theforeman.delete_domain(id=domain.get('id'))
                return True, domain
            except ForemanError as e:
                module.fail_json(msg='Could not delete domain: {0}'.format(e.message))

        if not domains_equal(data, domain, comparable_keys):
            try:
                domain = theforeman.update_domain(id=domain.get('id'), data=data)
                return True, domain
            except ForemanError as e:
                module.fail_json(msg='Could not update domain: {0}'.format(e.message))

    return False, domain


def main():
    global module

    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True),
            fullname=dict(type='str', required=False),
            dns_proxy=dict(type='str', required=False),
            state=dict(type='str', default='present', choices=['present', 'absent']),
            organizations=dict(type='list', required=False),
            locations=dict(type='list', required=False),
            foreman_host=dict(type='str', default='127.0.0.1'),
            foreman_port=dict(type='str', default='443'),
            foreman_user=dict(type='str', required=True),
            foreman_pass=dict(type='str', required=True, no_log=True),
            foreman_ssl=dict(type='bool', default=True)
        ),
    )

    if not foremanclient_found:
        module.fail_json(msg='python-foreman module is required. See https://github.com/Nosmoht/python-foreman.')

    changed, domain = ensure(module)
    module.exit_json(changed=changed, domain=domain)


from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
