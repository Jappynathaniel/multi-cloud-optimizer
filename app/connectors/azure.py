from datetime import datetime, timedelta, timezone
import requests
from app.connectors.base import CloudConnector, CollectedCost, CollectionResult


class AzureConnector(CloudConnector):
    """Read-only Cost Management query. Azure exports should replace this at scale."""
    def collect(self) -> CollectionResult:
        from azure.identity import ClientSecretCredential
        credential = ClientSecretCredential(self.config["tenant_id"], self.config["client_id"], self.config["client_secret"])
        subscription_id = self.config["subscription_id"]
        end, start = datetime.now(timezone.utc).date(), (datetime.now(timezone.utc) - timedelta(days=30)).date()
        scope = f"/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/query"
        query = {"type": "ActualCost", "timeframe": "Custom", "timePeriod": {"from": f"{start}T00:00:00Z", "to": f"{end}T00:00:00Z"},
                 "dataset": {"granularity": "None", "aggregation": {"cost": {"name": "Cost", "function": "Sum"}},
                 "grouping": [{"type": "Dimension", "name": "ServiceName"}]}}
        token = credential.get_token("https://management.azure.com/.default").token
        response = requests.post(f"https://management.azure.com{scope}?api-version=2023-11-01", json=query,
            headers={"Authorization": f"Bearer {token}"}, timeout=60)
        response.raise_for_status()
        properties = response.json()["properties"]
        result = CollectionResult()
        columns = [column["name"] for column in properties["columns"]]
        for row in properties.get("rows", []):
            values = dict(zip(columns, row))
            result.costs.append(CollectedCost(period_start=str(start), period_end=str(end),
                service_name=str(values.get("ServiceName", "Unknown")), billed_cost=float(values.get("Cost", 0)),
                currency=str(values.get("Currency", "USD")), source="azure_cost_management_query", raw=values))
        return result

