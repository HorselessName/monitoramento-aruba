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
import fcntl

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
    Handle any API errors and return appropriate error messages.
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

    if refreshed_token_response.status_code != 200:
        # Return API error as JSON formatted for frontend
        error_data = refreshed_token_response.json()
        return {
            "data": [
                {"error": error_data.get('error_description', 'Unknown error occurred during token refresh')}
            ]
        }

    refreshed_token_data = refreshed_token_response.json()

    if 'refresh_token' not in refreshed_token_data or 'access_token' not in refreshed_token_data:
        return {
            "data": [
                {"error": "The response does not contain the expected tokens."}
            ]
        }

    return {
        'refresh_token': refreshed_token_data['refresh_token'],
        'access_token': refreshed_token_data['access_token']
    }


def write_config_with_lock(parser_for_file, file_path):
    """
    Write the configuration to the file with a file lock to ensure that only one process can write to the file at a time.
    """
    with open(file_path, 'w') as configfile:
        # Lock the file for writing
        fcntl.flock(configfile, fcntl.LOCK_EX)

        # Write the configuration to the file
        parser_for_file.write(configfile)

        # Unlock the file after writing
        fcntl.flock(configfile, fcntl.LOCK_UN)


def read_config_with_lock(parser_for_file, file_path):
    """
    Read the configuration from the file with a file lock to ensure that only one process can read the file at a time.
    This also prevents reading while the file is being written.
    """
    with open(file_path, 'r') as configfile:
        # Lock the file for reading
        fcntl.flock(configfile, fcntl.LOCK_SH)  # Shared lock for reading

        # Read the configuration
        parser_for_file.read_file(configfile)

        # Unlock the file after reading
        fcntl.flock(configfile, fcntl.LOCK_UN)


def list_aps(client_name, config_parser):
    headers = {
        "Authorization": "Bearer %s" % config_parser[client_name]['access_token'],
        "Accept": "application/json"
    }

    try:
        response = requests.get(BASE_URL + "/monitoring/v2/aps", headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        aps_data = response.json().get('aps', [])
    except requests.exceptions.RequestException as e:
        return json.dumps({"data": [{"error": str(e)}]}, indent=4)
    except ValueError:
        return json.dumps({"data": [{"error": "Invalid JSON response from server"}]}, indent=4)

    site = args.site
    validated_aps = [AccessPoint.from_dict(ap).__dict__ for ap in aps_data if ap.get('site') == site]

    return json.dumps({"data": validated_aps}, indent=4, ensure_ascii=False)


def list_switches(client_name, config_parser):
    headers = {
        "Authorization": "Bearer %s" % config_parser[client_name]['access_token'],
        "Accept": "application/json"
    }

    try:
        response = requests.get(BASE_URL + "/monitoring/v1/switches", headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        switches_data = response.json().get('switches', [])
    except requests.exceptions.RequestException as e:
        return json.dumps({"data": [{"error": str(e)}]}, indent=4)
    except ValueError:
        return json.dumps({"data": [{"error": "Invalid JSON response from server"}]}, indent=4)

    site = args.site
    validated_switches = [Switch.from_dict(switch).__dict__ for switch in switches_data if switch.get('site') == site]

    return json.dumps({"data": validated_switches}, indent=4, ensure_ascii=False)


def list_gateways(client_name, config_parser):
    headers = {
        "Authorization": "Bearer %s" % config_parser[client_name]['access_token'],
        "Accept": "application/json"
    }

    try:
        response = requests.get(BASE_URL + "/monitoring/v1/gateways", headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        gateways_data = response.json().get('gateways', [])
    except requests.exceptions.RequestException as e:
        return json.dumps({"data": [{"error": str(e)}]}, indent=4)
    except ValueError:
        return json.dumps({"data": [{"error": "Invalid JSON response from server"}]}, indent=4)

    site = args.site
    validated_gateways = [Gateway.from_dict(gateway).__dict__ for gateway in gateways_data if gateway.get('site') == site]

    return json.dumps({"data": validated_gateways}, indent=4, ensure_ascii=False)


def list_sites(client_name, config_parser):
    """
    List sites from the Aruba API and handle any API or data errors.
    Return error messages in a consistent JSON format for Zabbix.
    """
    headers = {
        "Authorization": "Bearer %s" % config_parser[client_name]['access_token'],
        "Accept": "application/json"
    }

    response = requests.get(BASE_URL + "/central/v2/sites", headers=headers)

    if response.status_code != 200:
        error_data = response.json()
        return json.dumps({
            "data": [
                {"error": error_data.get('error_description', 'Unknown error while fetching sites')}
            ]
        }, indent=4)

    sites_data = response.json().get('sites', [])

    if not sites_data:
        return json.dumps({"data": []}, indent=4)

    validated_sites = [Site.from_dict(site, client_name).__dict__ for site in sites_data]

    return json.dumps({"data": validated_sites}, indent=4)


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

    try:
        response = requests.get("%s/aiops/v2/insights/global/list" % BASE_URL, params=params, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        insights_data = response.json()
    except requests.exceptions.RequestException as e:
        return json.dumps({"data": [{"error": str(e)}]}, indent=4)
    except ValueError:
        return json.dumps({"data": [{"error": "Invalid JSON response from server"}]}, indent=4)

    validated_insights = [Insight.from_dict(insight).__dict__ for insight in insights_data if isinstance(insight, dict)]

    return json.dumps({"data": validated_insights}, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    """
    Main entry point for the script. This script refreshes access tokens on each execution and lists
    the devices from the selected token present in the INI file, according to the selected listing option.
    """

    base_dir = os.path.dirname(__file__)  # Get file directory
    config_file_path = os.path.join(base_dir, 'tokens_aruba.ini')
    configuration_parser = configparser.ConfigParser()

    if not os.path.exists(config_file_path):
        print(json.dumps({"data": [{"error": f"Configuration file {config_file_path} not found."}]}))
        exit(1)

    try:
        # Use read_config_with_lock to safely read the file
        read_config_with_lock(configuration_parser, config_file_path)
        normalized_client_name = args.cliente.strip().upper()

        if normalized_client_name not in [section.upper() for section in configuration_parser.sections()]:
            print(json.dumps({"data": [{"error": f"Client {args.cliente} not found in the configuration file."}]}))
            exit(1)

    except Exception as e:
        print(json.dumps({"data": [{"error": str(e)}]}))
        exit(1)

    # Refresh the tokens for the specified client
    renewed_tokens = refresh_token(normalized_client_name, configuration_parser)

    if 'data' in renewed_tokens and 'error' in renewed_tokens['data'][0]:
        print(json.dumps(renewed_tokens, indent=4))
        exit(1)

    # Ensure renewed_tokens is not an error
    if renewed_tokens and 'error' not in renewed_tokens:
        # Extract tokens
        refresh_token = renewed_tokens.get('refresh_token')
        access_token = renewed_tokens.get('access_token')

        if refresh_token and access_token:
            # Save the new refresh_token and access_token only if they differ from the current ones
            if configuration_parser[normalized_client_name]['refresh_token'] != refresh_token or \
                    configuration_parser[normalized_client_name]['access_token'] != access_token:
                # Update the configuration
                configuration_parser.set(normalized_client_name, "refresh_token", str(refresh_token))
                configuration_parser.set(normalized_client_name, "access_token", str(access_token))

                # Write the new tokens to the ini file with file locking
                write_config_with_lock(configuration_parser, config_file_path)

    # Handle different listing options
    if args.listar.lower() == "aps":
        aps_list = list_aps(normalized_client_name, configuration_parser)
        print(aps_list)
    elif args.listar.lower() == "switches":
        switches_list = list_switches(normalized_client_name, configuration_parser)
        print(switches_list)
    elif args.listar.lower() == "gateways":
        gateways_list = list_gateways(normalized_client_name, configuration_parser)
        print(gateways_list)
    elif args.listar.lower() == "sites":
        sites_list = list_sites(normalized_client_name, configuration_parser)
        print(sites_list)
    elif args.listar.lower() == "insights":
        insights_list = list_insights(normalized_client_name, configuration_parser)
        print(insights_list)
