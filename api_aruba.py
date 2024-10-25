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


# Import appropriate locking mechanism based on OS
def is_windows():
    return os.name == 'nt'


if is_windows():
    import win32file
    import win32con
else:
    import fcntl

# Paths
BASE_URL = "https://apigw-uswest4.central.arubanetworks.com"
base_dir = os.path.dirname(os.path.abspath(__file__))  # Get file directory
tokens_folder = os.path.join(base_dir, 'aruba_tokens')  # Folder where token files are located

# Handle command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument("-c", "--cliente", help="Nome do cliente de onde coletar os dados", required=True)
parser.add_argument("-s", "--site", help="Site onde está o Equipamento do cliente.", required=False)
parser.add_argument("-l", "--listar", help="Ex: Aps, Switchs, Gateways", required=True)
args = parser.parse_args()


def normalize_name(name):
    """
    Limpa e normaliza o nome, removendo acentos, substituindo espaços por underscores
    e removendo caracteres não alfanuméricos, exceto underscores.
    """
    if name is None:
        return ''

    # Normalize and remove accents
    name_clean = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')

    # Convert to lowercase
    name_clean = name_clean.lower()

    # Replace spaces with underscores and remove non-alphanumeric characters except underscores
    name_clean = re.sub(r'\s+', '_', name_clean)
    name_clean = re.sub(r'[^a-zA-Z0-9_]', '', name_clean)

    return name_clean


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
        # Limpar e normalizar o nome do AP usando a função utilitária
        clean_name = normalize_name(data.get('name'))
        return cls(
            group_name=data.get('group_name'),
            ip_address=data.get('ip_address'),
            macaddr=data.get('macaddr'),
            model=data.get('model'),
            name=clean_name,  # Usando o nome limpo
            serial=data.get('serial'),
            site=data.get('site'),
            status=data.get('status')
        )


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
        # Limpar e normalizar o nome do Switch usando a função utilitária
        clean_name = normalize_name(data.get('name'))
        return cls(
            group_name=data.get('group_name'),
            ip_address=data.get('ip_address'),
            macaddr=data.get('macaddr'),
            name=clean_name,  # Usando o nome limpo
            public_ip_address=data.get('public_ip_address'),
            site=data.get('site'),
            status=data.get('status'),
        )


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
        # Limpar e normalizar o nome do Gateway usando a função utilitária
        clean_name = normalize_name(data.get('name'))
        return cls(
            group_name=data.get('group_name'),
            ip_address=data.get('ip_address'),
            macaddr=data.get('macaddr'),
            name=clean_name,  # Usando o nome limpo
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
        # Limpar e normalizar o nome do site e da empresa usando a função utilitária
        company_name_clean = normalize_name(company_name)
        site_name_clean = normalize_name(site_name)

        # Combine company name and site name
        return f"{company_name_clean}_{site_name_clean}"


class Insight:
    SEVERITY_ORDER = {
        'low': 1,
        'med': 2,
        'hig': 3
    }

    def __init__(self, category, description, impact, insight, insight_id, is_config_recommendation_insight, severity,
                 client):
        self.category = category
        self.description = description
        self.impact = impact
        self.insight = insight
        self.insight_id = insight_id
        self.is_config_recommendation_insight = is_config_recommendation_insight
        self.severity = severity
        self.client = client  # Adicionando o campo cliente

    @classmethod
    def from_dict(cls, data, client):
        return cls(
            category=data.get('category', ''),
            description=data.get('description', ''),
            impact=data.get('impact', ''),
            insight=data.get('insight', ''),
            insight_id=data.get('insight_id', 0),
            is_config_recommendation_insight=data.get('is_config_recommendation_insight', False),
            severity=data.get('severity', 'low'),
            client=client  # Passando o cliente
        )

    def __lt__(self, other):
        return self.SEVERITY_ORDER[self.severity] < self.SEVERITY_ORDER[other.severity]


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


# Verifica se o sistema operacional é Windows
def is_windows():
    return os.name == 'nt'


# Importa o fcntl apenas se não for Windows
if not is_windows():
    import fcntl


# Função de leitura com bloqueio exclusivo (para garantir que apenas um processo leia ou escreva por vez)
def read_config_with_lock(parser_for_file, file_path):
    if is_windows():
        # No Windows, só lê o arquivo sem bloqueio
        with open(file_path, 'r') as configfile:
            parser_for_file.read_file(configfile)
    else:
        with open(file_path, 'r') as configfile:
            # Bloqueio exclusivo para leitura no Linux/Unix (isso vai bloquear outros leitores e escritores)
            fcntl.flock(configfile, fcntl.LOCK_EX)  # Usar LOCK_EX para leitura exclusiva
            parser_for_file.read_file(configfile)
            fcntl.flock(configfile, fcntl.LOCK_UN)  # Libera o bloqueio após leitura


# Função de escrita com bloqueio exclusivo (somente no Linux/Unix)
def write_config_with_lock(parser_for_file, file_path):
    if is_windows():
        # No Windows, só escreve o arquivo sem bloqueio
        with open(file_path, 'w') as configfile:
            parser_for_file.write(configfile)
    else:
        with open(file_path, 'w') as configfile:
            # Bloqueio exclusivo para escrita no Linux/Unix
            fcntl.flock(configfile, fcntl.LOCK_EX)
            parser_for_file.write(configfile)
            fcntl.flock(configfile, fcntl.LOCK_UN)  # Libera o bloqueio após escrita


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

    site = args.site  # Pegando o site para filtrar os APs do site específico
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
    validated_gateways = [Gateway.from_dict(gateway).__dict__ for gateway in gateways_data if
                          gateway.get('site') == site]

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

    # Filtrando e validando os dados para o JSON final, incluindo o nome do cliente
    validated_insights = [Insight.from_dict(insight, client_name).__dict__ for insight in insights_data if isinstance(insight, dict)]

    # Ordenando os insights pela severidade
    validated_insights.sort(key=lambda i: Insight.SEVERITY_ORDER[i['severity']])

    # Retornando o JSON final filtrado e ordenado
    return json.dumps({"data": validated_insights}, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    """
    Ponto de entrada principal do script. Este script atualiza os tokens de acesso
    a cada execução e lista os dispositivos a partir do token selecionado no arquivo de tokens do cliente.
    
    Exemplos de uso:
     ./api_aruba.py -c "<Cliente>" -l "aps" -s "<Site do Tenant>"
     ./api_aruba.py -c "<Cliente>" -l "insights"
    """

    # Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))  # Diretório base
    tokens_folder = os.path.join(base_dir, 'aruba_tokens')  # Pasta onde os tokens estão localizados
    config_file_path = os.path.join(tokens_folder, args.cliente)  # Caminho do arquivo de token do cliente específico
    configuration_parser = configparser.ConfigParser()

    normalized_client_name = None  # Initialize it here

    # Error handling using a single block for consistency
    try:
        if not os.path.exists(config_file_path):
            # Return error in the expected structure instead of raising an exception
            print(json.dumps({"data": [{"error": f"Arquivo de configuração para o cliente {args.cliente} não encontrado."}]}))
            exit(1)

        # Usa read_config_with_lock para ler o arquivo com segurança
        read_config_with_lock(configuration_parser, config_file_path)
        normalized_client_name = args.cliente.strip().upper()

        if normalized_client_name not in configuration_parser.sections():
            # Return error in the expected structure instead of raising an exception
            print(json.dumps({"data": [{"error": f"Cliente {args.cliente} não encontrado em {config_file_path}."}]}))
            exit(1)

        # Atualiza os tokens para o cliente especificado
        renewed_tokens = refresh_token(normalized_client_name, configuration_parser)

        # Check for token errors
        if 'data' in renewed_tokens and 'error' in renewed_tokens['data'][0]:
            print(json.dumps(renewed_tokens, indent=4))
            exit(1)

        # Verifica se renewed_tokens não é um erro
        if renewed_tokens and 'error' not in renewed_tokens:
            # Extrai os tokens
            refresh_token = renewed_tokens.get('refresh_token')
            access_token = renewed_tokens.get('access_token')

            if refresh_token and access_token:
                # Salva o novo refresh_token e access_token apenas se forem diferentes dos atuais
                if configuration_parser[normalized_client_name]['refresh_token'] != refresh_token or \
                        configuration_parser[normalized_client_name]['access_token'] != access_token:
                    # Atualiza a configuração
                    configuration_parser.set(normalized_client_name, "refresh_token", str(refresh_token))
                    configuration_parser.set(normalized_client_name, "access_token", str(access_token))

                    # Escreve os novos tokens no arquivo ini com bloqueio (Linux/Unix)
                    write_config_with_lock(configuration_parser, config_file_path)

        # Manipula as opções de listagem
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

    except Exception as e:
        # Return unexpected errors in the expected structure
        print(json.dumps({"data": [{"error": f"Unexpected error: {str(e)}"}]}))
        exit(1)
