#!/usr/bin/python3
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
import os
import requests
import configparser
import json
import argparse
import unicodedata
import re

BASE_URL = "https://apigw-uswest4.central.arubanetworks.com"

base_dir = os.path.dirname(os.path.abspath(__file__))

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--cliente", help="Nome do cliente de onde coletar os dados", required=True)
parser.add_argument("-s", "--site", help="Site onde está o Equipamento do cliente.", required=False)
parser.add_argument("-l", "--listar", help="Ex: Aps, Switchs, Gateways", required=True)

args = parser.parse_args()


class AccessPoint:
    def __init__(self, group_name, ip_address, macaddr, model, name, serial, site, status):
        self.group_name = group_name
        self.ip_address = ip_address
        self.macaddr = macaddr
        self.model = model
        self.name = name
        self.serial = serial
        self.site = site
        self.status = status

    @classmethod
    def from_dict(cls, data):
        return cls(
            group_name=data.get('group_name'),
            ip_address=data.get('ip_address'),
            macaddr=data.get('macaddr'),
            model=data.get('model'),
            name=data.get('name'),
            serial=data.get('serial'),
            site=data.get('site'),
            status=data.get('status')
        )


# Define the Switch class
class Switch:
    def __init__(self, group_name, ip_address, macaddr, name, public_ip_address, site, status):
        self.group_name = group_name
        self.ip_address = ip_address
        self.macaddr = macaddr
        self.name = name
        self.public_ip_address = public_ip_address
        self.site = site
        self.status = status

    @classmethod
    def from_dict(cls, data):
        return cls(
            group_name=data.get('group_name'),
            ip_address=data.get('ip_address'),
            macaddr=data.get('macaddr'),
            name=data.get('name'),
            public_ip_address=data.get('public_ip_address'),
            site=data.get('site'),
            status=data.get('status'),
        )


# Define the Gateway class
class Gateway:
    def __init__(self, group_name, ip_address, macaddr, name, serial, site, status):
        self.group_name = group_name
        self.ip_address = ip_address
        self.macaddr = macaddr
        self.name = name
        self.serial = serial
        self.site = site
        self.status = status

    @classmethod
    def from_dict(cls, data):
        return cls(
            group_name=data.get('group_name'),
            ip_address=data.get('ip_address'),
            macaddr=data.get('macaddr'),
            name=data.get('name'),
            serial=data.get('serial'),
            site=data.get('site'),
            status=data.get('status')
        )


class Site:
    def __init__(self, city, country, latitude, longitude, site_id, site_name, state, zipcode, company_name, host_name):
        self.city = city
        self.country = country
        self.latitude = latitude
        self.longitude = longitude
        self.site_id = site_id
        self.site_name = site_name
        self.state = state
        self.zipcode = zipcode
        self.company_name = company_name
        self.host_name = host_name

    @classmethod
    def from_dict(cls, data, company_name):
        site_name = data.get('site_name')
        host_name = cls.generate_host_name(company_name, site_name)
        return cls(
            city=data.get('city'),
            country=data.get('country'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            site_id=data.get('site_id'),
            site_name=site_name,
            state=data.get('state'),
            zipcode=data.get('zipcode'),
            company_name=company_name,
            host_name=host_name
        )

    @staticmethod
    def generate_host_name(company_name, site_name):
        # Normalize and remove accents
        company_name_clean = unicodedata.normalize('NFKD', company_name).encode('ASCII', 'ignore').decode('ASCII')
        site_name_clean = unicodedata.normalize('NFKD', site_name).encode('ASCII', 'ignore').decode('ASCII')

        # Convert to lowercase
        company_name_clean = company_name_clean.lower()
        site_name_clean = site_name_clean.lower()

        # Replace spaces with underscores and remove non-alphanumeric characters except underscores
        company_name_clean = re.sub(r'\s+', '_', company_name_clean)
        site_name_clean = re.sub(r'\s+', '_', site_name_clean)
        site_name_clean = re.sub(r'[^a-zA-Z0-9_]', '', site_name_clean)

        # Combine company name and site name
        return f"{company_name_clean}_{site_name_clean}"


class Insight:
    def __init__(self, category, description, impact, insight, insight_id, is_config_recommendation_insight, severity):
        self.category = category
        self.description = description
        self.impact = impact
        self.insight = insight
        self.insight_id = insight_id
        self.is_config_recommendation_insight = is_config_recommendation_insight
        self.severity = severity

    @classmethod
    def from_dict(cls, data):
        return cls(
            category=data.get('category', ''),
            description=data.get('description', ''),
            impact=data.get('impact', ''),
            insight=data.get('insight', ''),
            insight_id=data.get('insight_id', 0),
            is_config_recommendation_insight=data.get('is_config_recommendation_insight', False),
            severity=data.get('severity', 'low')
        )


def refresh_token(client_name, config_parser):
    """
    Use this method to refresh the access token using the current refresh token for the organization.
    """

    token_refresh_params = {
        "client_id": config_parser[client_name]['client_id'],
        "client_secret": config_parser[client_name]['client_secret'],
        "grant_type": "refresh_token",
        "refresh_token": config_parser[client_name]['refresh_token']
    }

    refreshed_token_response = requests.post(
        BASE_URL + "/oauth2/token",
        params=token_refresh_params
    )

    refreshed_token_data = refreshed_token_response.json()

    # Check if the response contains the tokens
    if 'refresh_token' not in refreshed_token_data or 'access_token' not in refreshed_token_data:
        return {
            "error": "Error: The response does not contain the expected tokens."
        }

    return {
        'refresh_token': refreshed_token_data['refresh_token'],
        'access_token': refreshed_token_data['access_token']
    }


def list_aps(client_name, config_parser):
    headers = {
        "Authorization": "Bearer %s" % config_parser[client_name]['access_token'],
        "Accept": "application/json"
    }

    response = requests.get(BASE_URL + "/monitoring/v2/aps", headers=headers)
    aps_data = response.json().get('aps', [])
    site = args.site

    validated_aps = [AccessPoint.from_dict(ap).__dict__ for ap in aps_data if ap.get('site') == site]

    return json.dumps({"aps": validated_aps}, indent=4, ensure_ascii=False)


def list_switches(client_name, config_parser):
    headers = {
        "Authorization": "Bearer %s" % config_parser[client_name]['access_token'],
        "Accept": "application/json"
    }

    response = requests.get(BASE_URL + "/monitoring/v1/switches", headers=headers)
    switches_data = response.json().get('switches', [])

    site = args.site
    validated_switches = [Switch.from_dict(switch).__dict__ for switch in switches_data if switch.get('site') == site]

    return json.dumps({"switches": validated_switches}, indent=4, ensure_ascii=False)


def list_gateways(client_name, config_parser):
    headers = {
        "Authorization": "Bearer %s" % config_parser[client_name]['access_token'],
        "Accept": "application/json"
    }

    response = requests.get(BASE_URL + "/monitoring/v1/gateways", headers=headers)
    gateways_data = response.json().get('gateways', [])

    site = args.site
    validated_gateways = [Gateway.from_dict(gateway).__dict__ for gateway in gateways_data if gateway.get('site') == site]

    return json.dumps({"gateways": validated_gateways}, indent=4, ensure_ascii=False)


def list_sites(client_name, config_parser):
    headers = {
        "Authorization": "Bearer %s" % config_parser[client_name]['access_token'],
        "Accept": "application/json"
    }

    company_sites = requests.get(BASE_URL + "/central/v2/sites", headers=headers)
    sites_data = company_sites.json().get('sites', [])

    validated_sites = [Site.from_dict(site, client_name).__dict__ for site in sites_data]

    return json.dumps({"sites": validated_sites}, indent=4, ensure_ascii=False)


def list_insights(client_name, config_parser):
    headers = {
        "Authorization": "Bearer %s" % config_parser[client_name]['access_token'],
        "Accept": "application/json"
    }

    now = datetime.now(timezone.utc)
    three_hours_ago = now - timedelta(hours=3)

    milliseconds_now = int(now.timestamp() * 1000)
    milliseconds_three_hours_ago = int(three_hours_ago.timestamp() * 1000)

    params = {
        "from": milliseconds_three_hours_ago,
        "to": milliseconds_now
    }

    response = requests.get("%s/aiops/v2/insights/global/list" % BASE_URL, params=params, headers=headers)

    try:
        insights_data = response.json()
    except ValueError:
        return json.dumps({"error": "Invalid JSON response from server"}, indent=4, ensure_ascii=False)

    validated_insights = [Insight.from_dict(insight).__dict__ for insight in insights_data if isinstance(insight, dict)]

    return json.dumps({"insights": validated_insights}, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    """
    Main entry point for the script. This script refreshes access tokens on each execution and lists
    the devices from the selected token present in the INI file, according to the selected listing option.
    """

    base_dir = os.getcwd()
    config_file_path = os.path.join(base_dir, 'tokens_aruba.ini')

    configuration_parser = configparser.ConfigParser()

    try:
        configuration_parser.read(config_file_path)
        if args.cliente not in configuration_parser:
            raise KeyError("Client %s not found in the configuration file." % args.cliente)
    except Exception as e:
        raise

    # Refresh the tokens for the specified client
    renewed_tokens = refresh_token(args.cliente, configuration_parser)

    if renewed_tokens and 'error' not in renewed_tokens:
        # Save the new refresh_token and access_token only if they differ from the current ones
        if configuration_parser[args.cliente]['refresh_token'] != renewed_tokens['refresh_token'] or \
           configuration_parser[args.cliente]['access_token'] != renewed_tokens['access_token']:
            configuration_parser.set(args.cliente, "refresh_token", renewed_tokens['refresh_token'])
            configuration_parser.set(args.cliente, "access_token", renewed_tokens['access_token'])

            # Write the new tokens to the ini file
            with open(config_file_path, 'w') as configfile:
                configuration_parser.write(configfile)

    # Based on the "listar" option, execute the correct function
    if args.listar.lower() == "aps":
        aps_list = list_aps(args.cliente, configuration_parser)
        print(aps_list)
    elif args.listar.lower() == "switches":
        switches_list = list_switches(args.cliente, configuration_parser)
        print(switches_list)
    elif args.listar.lower() == "gateways":
        gateways_list = list_gateways(args.cliente, configuration_parser)
        print(gateways_list)
    elif args.listar.lower() == "sites":
        sites_list = list_sites(args.cliente, configuration_parser)
        print(sites_list)
    elif args.listar.lower() == "insights":
        insights_list = list_insights(args.cliente, configuration_parser)
        print(insights_list)
