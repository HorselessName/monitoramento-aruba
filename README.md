# ARUBA Monitoring for Zabbix

This integration monitors Access Points (APs), Switches, and Gateways for ARUBA Tenants, providing seamless integration with Zabbix and Grafana Dashboards for easy monitoring and visualization.

## Prerequisites

1. **Python 3 Installation**: Ensure Python 3 is installed on the Zabbix Server.
2. **Required Libraries**: The script requires the `requests` Python library. Install it using:
   ```bash
   pip install requests
   ```

## Script Setup

1. **Script Location**: Place the `api_aruba.py` script in the Zabbix external scripts directory:
   ```bash
   /usr/lib/zabbix/externalscripts/
   ```
2. **API Tokens Folder**: Create a folder named `aruba_tokens` inside the `externalscripts` directory. This folder will store the API tokens used by the script.
   ```bash
   /usr/lib/zabbix/externalscripts/aruba_tokens/
   ```

3. **Token Structure**: For each client, create a token file inside the `aruba_tokens` folder. Name the file after the client, and use the following format for each token:
   ```
   [<CLIENT>]
   client_id = <CLIENT ID GENERATED IN ARUBA API>
   client_secret = <CLIENT SECRET GENERATED IN ARUBA API>
   access_token = <ACCESS TOKEN GENERATED IN ARUBA API>
   refresh_token = <REFRESH TOKEN GENERATED IN ARUBA API>
   ```
   Example:
   ```
   [CustomerA]
   client_id = abc123
   client_secret = def456
   access_token = ghi789
   refresh_token = jkl012
   ```

4. **Permission Setup**: Ensure that the script and token files have the correct permissions and are owned by the Zabbix user:
   ```bash
   chown zabbix:zabbix /usr/lib/zabbix/externalscripts/api_aruba.py
   chmod 750 /usr/lib/zabbix/externalscripts/api_aruba.py
   chown -R zabbix:zabbix /usr/lib/zabbix/externalscripts/aruba_tokens/
   chmod 700 /usr/lib/zabbix/externalscripts/aruba_tokens/
   ```

## Zabbix Template Setup

1. **API Tokens Setup**: Create and configure API tokens in Aruba HPE Cloud Administration for the desired company.
2. **Template Import**: Import the following templates into Zabbix:
   - **Template Aruba - Tenant Monitoring via API**: This template discovers the sites of a company and creates hosts for each company and site.
   - **Template Aruba - Tenant Sites Monitoring via API**: This template contains discovery rules for APs, Switches, and Gateways for each company and site.

3. **HOST Configuration**:
   - When creating a host, apply the **"Tenant Monitoring"** template.
   - Set the macro `{$CUSTOMER_NAME}` in the template to match the `<CLIENT>` name used in the token file (e.g., `CustomerA`), which allows the script to access the relevant tokens and retrieve information for the specified tenant.

## Manual Script Testing

### Windows:
To manually test the script on Windows:
```bash
.\.venv\Scripts\python.exe api_aruba.py -c "CUSTOMER" -s "SITE" -l "aps"
```

### Linux:
To manually test the script on Linux:
```bash
./api_aruba.py -c "CUSTOMER" -l "insights"
```

## Zabbix Version Compatibility

This integration was developed and tested on **Zabbix Version 6.2.9**. If you are using an older or newer version, ensure to update the YAML templates before importing.
