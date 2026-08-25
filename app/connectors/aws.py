from datetime import date, timedelta

from app.connectors.base import CloudConnector, CollectedCost, CollectedResource, CollectionResult


class AWSConnector(CloudConnector):
    """Read-only collector using an assumed role or standard AWS credential chain."""

    def _session(self):
        import boto3
        base_session = boto3.Session(
            aws_access_key_id=self.config.get("access_key_id"),
            aws_secret_access_key=self.config.get("secret_access_key"),
            region_name=self.config.get("region", "us-east-1"),
        )
        role_arn = self.config.get("role_arn")
        if not role_arn:
            return base_session
        sts = base_session.client("sts")
        args = {"RoleArn": role_arn, "RoleSessionName": "redbridge-readonly"}
        if self.config.get("external_id"):
            args["ExternalId"] = self.config["external_id"]
        credentials = sts.assume_role(**args)["Credentials"]
        return boto3.Session(aws_access_key_id=credentials["AccessKeyId"],
                             aws_secret_access_key=credentials["SecretAccessKey"],
                             aws_session_token=credentials["SessionToken"],
                             region_name=self.config.get("region", "us-east-1"))

    def collect(self) -> CollectionResult:
        session = self._session()
        region = self.config.get("region", "us-east-1")
        result = CollectionResult()
        ec2 = session.client("ec2", region_name=region)
        for reservation in ec2.describe_instances().get("Reservations", []):
            for instance in reservation.get("Instances", []):
                tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
                result.resources.append(CollectedResource(
                    id=instance["InstanceId"], resource_type="aws.ec2.instance",
                    name=tags.get("Name", instance["InstanceId"]), region=region, tags=tags,
                    configuration={"instance_type": instance.get("InstanceType"), "state": instance.get("State", {}).get("Name")},
                ))
        end, start = date.today(), date.today() - timedelta(days=30)
        ce = session.client("ce", region_name="us-east-1")
        response = ce.get_cost_and_usage(TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="MONTHLY", Metrics=["NetAmortizedCost"], GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}])
        for period in response.get("ResultsByTime", []):
            for group in period.get("Groups", []):
                metric = group["Metrics"]["NetAmortizedCost"]
                result.costs.append(CollectedCost(period_start=period["TimePeriod"]["Start"], period_end=period["TimePeriod"]["End"],
                    service_name=group["Keys"][0], billed_cost=float(metric["Amount"]), currency=metric["Unit"], region=region,
                    source="aws_cost_explorer", raw=group))
        optimizer = session.client("compute-optimizer", region_name=region)
        try:
            result.native_recommendations = optimizer.get_ec2_instance_recommendations().get("instanceRecommendations", [])
        except optimizer.exceptions.OptInRequiredException:
            result.native_recommendations = [{"notice": "AWS Compute Optimizer is not enabled for this account."}]
        return result

