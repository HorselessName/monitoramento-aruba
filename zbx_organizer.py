import json


# Função para filtrar as informações desejadas de cada host
def filtrar_hosts(hosts):
    hosts_filtrados = []
    for host in hosts:
        host_info = {
            "host": host["host"],
            "name": host["name"],
            "templates": " / ".join([template["name"] for template in host.get("templates", [])]),
            "groups": " / ".join([group["name"] for group in host.get("groups", [])])
        }
        hosts_filtrados.append(host_info)
    return hosts_filtrados


# Carrega o arquivo JSON original e processa as informações
def processar_json():
    # Nome do arquivo JSON a ser lido
    input_file = 'zbx_export_hosts.json'
    output_file = 'zbx_filtered_hosts.json'

    # Leitura do arquivo JSON
    with open(input_file, 'r') as f:
        data = json.load(f)

    # Filtrando os hosts
    hosts = data["zabbix_export"]["hosts"]
    hosts_filtrados = filtrar_hosts(hosts)

    # Cria o novo dicionário com os hosts filtrados
    filtered_data = {
        "hosts": hosts_filtrados
    }

    # Escreve o novo JSON em um arquivo
    with open(output_file, 'w') as f:
        json.dump(filtered_data, f, indent=4)

    print(f"Arquivo '{output_file}' gerado com sucesso.")


# Executa o processamento
if __name__ == "__main__":
    processar_json()
