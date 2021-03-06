#!/usr/bin/env python3
import datetime

import argparse
from copy import deepcopy

from botocore.exceptions import ClientError

def fetch_glue_data(client, func, key, print, **kwargs):
    caller = getattr(client, func)
    try:
        response = caller(**kwargs)
        data = response[key]
        while 'NextToken' in response and response['NextToken'] != '':
            print({**kwargs, **{'NextToken': response['NextToken']}})
            response = caller({**kwargs, **{'NextToken': response['NextToken']}})
            data.extend(response[key])
        for resource in data:
            resource['region'] = client.meta.region_name
        return data
    except ClientError as error:
        code = error.response['Error']['Code']
        if code == 'AccessDeniedException':
            print('  {} FAILURE: MISSING NEEDED PERMISSIONS'.format(func))
        else:
            print(code)
    return []


def main(args, awsattack_main):
    session = awsattack_main.get_active_session()

    print = awsattack_main.print
    get_regions = awsattack_main.get_regions

    if args.regions is None:
        regions = get_regions('glue')
        if regions is None or regions == [] or regions == '' or regions == {}:
            print('This module is not supported in any regions specified in the current sessions region set. Exiting...')
            return
    else:
        regions = args.regions.split(',')

    all_dev_endpoints = []
    for region in regions:
        print('Starting region {}...'.format(region))
        client = awsattack_main.get_boto3_client('glue', region)

        dev_endpoints = fetch_glue_data(client, 'get_dev_endpoints', 'DevEndpoints', print)
        print('  {} development endpoint(s) found.'.format(len(dev_endpoints)))
        all_dev_endpoints += dev_endpoints

    summary_data = {
        'dev_endpoints': len(all_dev_endpoints),
    }

    for var in vars(args):
        if var == 'regions':
            continue
        if not getattr(args, var):
            del summary_data[var]

    glue_data = deepcopy(session.Glue)
    glue_data['DevEndpoints'] = all_dev_endpoints
    session.update(awsattack_main.database, Glue=glue_data)

    return summary_data


