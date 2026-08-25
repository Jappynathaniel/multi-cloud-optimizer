from app.connectors.base import CloudConnector, CollectedCost, CollectedResource, CollectionResult


class GCPConnector(CloudConnector):
    """Reads a customer-configured Billing export in BigQuery; no guessed prices."""
    def collect(self) -> CollectionResult:
        from google.cloud import bigquery
        client = bigquery.Client.from_service_account_info(self.config["service_account"])
        table = self.config["billing_table"]  # project.dataset.gcp_billing_export_v1_...
        query = f'''SELECT service.description AS service, project.id AS project_id, location.region AS region,
          SUM(cost) AS cost, currency, MIN(usage_start_time) AS start_time, MAX(usage_end_time) AS end_time
          FROM `{table}` WHERE usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
          GROUP BY service, project_id, region, currency'''
        result = CollectionResult()
        for row in client.query(query).result():
            result.costs.append(CollectedCost(period_start=row.start_time.isoformat(), period_end=row.end_time.isoformat(),
                service_name=row.service, billed_cost=float(row.cost), currency=row.currency, resource_id=row.project_id,
                region=row.region, source="gcp_bigquery_billing_export"))
        return result

