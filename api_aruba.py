#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import requests
import configparser
import json
import argparse

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
    def __init__(self, city, country, latitude, longitude, site_id, site_name, state, zipcode):
        self.city = city
        self.country = country
        self.latitude = latitude
        self.longitude = longitude
        self.site_id = site_id
        self.site_name = site_name
        self.state = state
        self.zipcode = zipcode

    @classmethod
    def from_dict(cls, data):
        return cls(
            city=data.get('city'),
            country=data.get('country'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            site_id=data.get('site_id'),
            site_name=data.get('site_name'),
            state=data.get('state'),
            zipcode=data.get('zipcode')
        )


def refresh_token(client_name, config_parser):
    """
    Use esse método para renovar o Access Token utilizado
    para a Organização Atual. Caso dê erro, ou esteja desatualizado,
    precisa atualizar corretamente com o criado para a empresa, no Central Management do ARUBA.

    É criado e mantido em System Apps & Tokens dentro do Customer, em Organization > REST API.
    """

    token_refresh_params = {
        "client_id": config_parser[client_name]['client_id'],
        "client_secret": config_parser[client_name]['client_secret'],
        "grant_type": "refresh_token",
        "refresh_token": config_parser[client_name]['refresh_token']
    }

    authorization_header = {
        "Authorization": "Bearer %s" % config_parser[client_name]['access_token']
    }

    refreshed_token_response = requests.request(
        "POST",
        BASE_URL + "/oauth2/token",
        params=token_refresh_params,
        headers=authorization_header
    )

    refreshed_token_data = json.loads(refreshed_token_response.text)

    if 'refresh_token' not in refreshed_token_data or 'access_token' not in refreshed_token_data:
        return {
            "error": "Erro: A resposta não contém os tokens esperados."
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

    validated_sites = [Site.from_dict(site).__dict__ for site in sites_data]

    return json.dumps({"sites": validated_sites}, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    """
    Ponto de entrada principal do script.

    Este script atualiza os tokens de acesso a cada execução, e lista os ativos
    do Token selecionado, presente no arquivo INI, de acordo com a opção de Listagem escolhida.

    Exemplo de uso:
    python3 script_name.py -c NOME_DO_CLIENTE -s 'São Paulo' -l OPÇÃO_LISTAR

    Argumentos:
    -c, --cliente: O nome do cliente do qual coletar os dados (obrigatório).
    -s, --site: Site em que o ativo pertence, dentro da empresa (obrigatório).
    -l, --listar: Exemplo: Aps, Switchs, Gateways (obrigatório).
    """

    current_directory = os.getcwd()

    configuration_parser = configparser.ConfigParser()
    config_file_path = os.path.join(base_dir, 'tokens_aruba.ini')

    try:
        configuration_parser.read(config_file_path)
        if args.cliente not in configuration_parser:
            raise KeyError("Cliente %s não encontrado no arquivo de configuração." % args.cliente)
    except Exception as e:
        raise

    renewed_tokens = refresh_token(args.cliente, configuration_parser)

    if (renewed_tokens and 'error' not in renewed_tokens and
            configuration_parser[args.cliente]['refresh_token'] != renewed_tokens['refresh_token']):
        configuration_parser.set(args.cliente, "refresh_token", renewed_tokens['refresh_token'])
        configuration_parser.set(args.cliente, "access_token", renewed_tokens['access_token'])

        with open(config_file_path, 'w') as configfile:
            configuration_parser.write(configfile)

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
