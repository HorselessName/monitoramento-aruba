# ARUBA Monitoring

Monitors APs, Switches and Gateways.
Made for ease of use to create Grafana Dashboards.

## Manual Script Use for Testing
After setting your Python environment (Requires Requests) do: `.\.venv\Scripts\python.exe api_aruba.py -c "CUSTOMER" -s "SITE" -l "aps"`

## Logic for Using the Template

1. Create and setup API Tokens on the desired company inside Aruba HPE Cloud Administration.
2. The first template discovers the sites of a company (Template Aruba - Tenant Monitoring via API	) and creates hosts for each Company + Site.
3. The second template (Template Aruba - Tenant Sites Monitoring via API) contains the discovery rules for APs, Switches and Gateways for each Company + Site.

## Zabbix Version
This was created using Zabbix Version 6.2.9, so if you're on a older or newer version, you must update the YAML Templates before importing.
