from app.connectors.aws import AWSConnector
from app.connectors.azure import AzureConnector
from app.connectors.gcp import GCPConnector

CONNECTORS = {"aws": AWSConnector, "azure": AzureConnector, "gcp": GCPConnector}

