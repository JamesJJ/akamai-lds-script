#!/usr/bin/env python3


import os
import sys
import requests
from akamai.edgegrid import EdgeGridAuth, EdgeRc
from urllib.parse import urljoin
from string import Template
import re
import json


def remove_key(obj, rk):
    if rk in obj:
        del obj[rk]
    for key, value in obj.items():
        # check for rk in sub dict
        if isinstance(value, dict):
            remove_key(value, rk)

        # check for existence of rk in lists
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    remove_key(item, rk)
    return obj


def api_session():
    edgerc = EdgeRc(os.path.expanduser('~/.edgerc'))
    section = 'default'
    baseurl = 'https://%s' % edgerc.get(section, 'host')
    s = requests.Session()
    s.auth = EdgeGridAuth.from_edgerc(edgerc, section)
    return [s, baseurl]


def print_list():
    s, baseurl = api_session()
    ls = s.get(urljoin(baseurl, '/lds-api/v3/log-sources'))
    for log_source in filter(lambda x: (x.get('type', '') == 'cpcode-products'), ls.json()):
        try:
            print(log_source['cpCode'])
        except KeyError:
            pass


def cp_num_from_lc_element(e):
    m = re.search(r'^([0-9]+)($|[\s,])', e.get('logSource', {}).get('cpCode', ''))
    if m:
        return m.group(1)
    return None


def cp_num_from_ls_element(e):
    m = re.search(r'^([0-9]+)($|[\s,])', e.get('cpCode', ''))
    if m:
        return m.group(1)
    return None


def show_all_configs():

    s, baseurl = api_session()
    lc = s.get(urljoin(baseurl, '/lds-api/v3/log-sources/cpcode-products/log-configurations'))

    for log_config in lc.json():
        print('=== STARTING: {}'.format(cp_num_from_lc_element(log_config)))

        print(' = Existing Config:\n{}\n\n'.format(remove_key(log_config, 'links')))


def set_from_configfile(f):

    config = ''
    with open(f, 'r', encoding='utf-8') as cf:
        config = cf.read()

    s, baseurl = api_session()
    ls = s.get(urljoin(baseurl, '/lds-api/v3/log-sources'))
    lc = s.get(urljoin(baseurl, '/lds-api/v3/log-sources/cpcode-products/log-configurations'))

    for cp in sys.stdin:
        cp_re = re.search(r'^([0-9]+)($|[\s,\-]+)([A-Za-z0-9_\.\-]+)?', cp.strip())
        if not cp_re:
            continue
        print('=== STARTING: {}'.format(cp))

        existing_config = list(filter(
            lambda x: (cp_re.group(1) == cp_num_from_lc_element(x)),
            lc.json()
        ))
        if (len(existing_config) == 1):
            print(' = Existing Config:\n{}\n\n'.format(remove_key(existing_config[0], 'links')))
        elif (len(existing_config) > 1):
            print('Unable to determine existing config')
            sys.exit(1)

        tag = re.sub(r'[^a-z0-9_]', '_', cp_re.group(3).lower()).strip('_')

        ct = Template(config).substitute(tag=tag)
        jc = json.loads(ct)
        print(' = New Config:\n{}\n\n'.format(json.dumps(jc)))

        if (len(existing_config) == 1):
            lcid = existing_config[0]['id']
            print(' = Updating config ID: {}'.format(lcid))
            # AKAMAI "UPDATE" API is BROKEN, so just delete existing config, and create new:
            update = s.delete(urljoin(baseurl, '/lds-api/v3/log-configurations/{}'.format(lcid)))
            # update = s.put(urljoin(baseurl, '/lds-api/v3/log-configurations/{}'.format(lcid)), json=jc)
            print(' = Update status: {} ({})'.format(update.status_code, update.text))

        if True:  # else:
            lsconfig = list(filter(
                lambda x: (cp_re.group(1) == cp_num_from_ls_element(x)),
                ls.json()
            ))

            if (len(lsconfig) != 1):
                print('Unable to determine log source property')
                sys.exit(1)

            lsid = lsconfig[0]['id']

            print(' = Creating config for source ID: {}'.format(lsid))
            create = s.post(urljoin(baseurl, '/lds-api/v3/log-sources/{}/{}/log-configurations'.format('cpcode-products', lsid)), json=jc)
            print(' = Create status: {} ({})\n\n'.format(create.status_code, create.text))

            delivery_directory = jc.get('deliveryDetails', {}).get('directory', None)
            if delivery_directory:
                with open('dir_list.txt', 'a+') as dl:
                    dl.write('{}\n'.format(delivery_directory))


# print(result.status_code)
if ((sys.argv + [''])[1] == 'list'):
    print_list()

elif ((sys.argv + [''])[1] == 'show'):
    show_all_configs()

elif (((sys.argv + [''])[1] == 'set') and (len(sys.argv) == 3) and (os.path.isfile((sys.argv + ['', '/'])[2]))):
    set_from_configfile(sys.argv[2])

else:
    print(""" Usage:
                ./lds_script.py <action> [<config_file>]

              Action "get" will provide a list of ALL CP-Codes.

              Action "show" will show existing configs

              Action "set" will read a list of CP-Codes from STDIN,
              and apply <config_file> LDS config to each one.

              It is expected that you use "get" first, and then remove any CP-Codes
              that you do not own. Then apply your config to the remaining list e.g.

              1] ./lds_script.py get > complete_list.txt

              2] Remove not owned from complete_list.txt and save as my_list.txt

              2b] ./lds_script.py show < my_list.txt

              3] ./lds_script.py set my_config.txt < my_list.txt

              The config file may include ${tag} as a placeholder for a sanitized name tag for each property.
              e.g. if my_list.txt contains:
                  123456 - www.google.com
                  468246 - www.microsoft.com

              ... then ${tag} in would be replaced with "www_google_com" in 123456 and "www_microsoft_com" in 468246

              A file "dir_list.txt" will be created containing a list of (S)FTP directories. You can use this to
              easily create the directory structure on your (S)FTP server (LDS expects directories to already exist).



              """)
