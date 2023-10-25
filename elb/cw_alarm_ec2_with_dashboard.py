import boto3
import json
from botocore.exceptions import ClientError

# IAM AccessKey 정보
#======================================================================
AWS_ACCESS_KEY_ID = "계정 액세스 키 ID 입력"
AWS_SECRET_ACCESS_KEY = "계정 액세스 키 값 입력"
AWS_DEFAULT_REGION = "ap-northeast-2"
#======================================================================

# IAM AccessKey 정보
#======================================================================
CW_DASHBOARD_NAME = "생성할 대시보드 이름 입력"
#======================================================================

ec2_client = boto3.client('ec2',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_DEFAULT_REGION
)
cloudwatch_client = boto3.client('cloudwatch',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_DEFAULT_REGION
)


# EC2 인스턴스 정보 조회
def describe_ec2_instances(ec2_client):
    response = ec2_client.describe_instances()
    ec2_list = {}
    for reservation in response["Reservations"]:
        for i in reservation["Instances"]:
            for j in i['Tags']:
                if j['Key'] == 'Name':
                    ec2_list[j['Value']] = (i['InstanceId'])
    return  ec2_list


def add_ec2_dashboard(metrics_cpu_val, metrics_status_val, metrics_mem_val, metrics_disk_val):
    body = {
        "widgets": [
            {
                "type": "metric",
                "properties": {
                    "metrics": metrics_cpu_val,
                    "legend": {
                        "position": "right"
                    },
                    "region": AWS_DEFAULT_REGION,
                    "liveData": True,
                    "title": "EC2_CPUUtilization",
                    "view": "timeSeries",
                    "stacked": False,
                }
            },
            {
                "type": "metric",
                "properties": {
                    "metrics": metrics_status_val,
                    "legend": {
                        "position": "right"
                    },
                    "region": AWS_DEFAULT_REGION,
                    "liveData": True,
                    "title": "EC2_StatusCheckFailed",
                    "view": "timeSeries",
                    "stacked": False,
                }
            },
            {
                "type": "metric",
                "properties": {
                    "metrics": metrics_mem_val,
                    "legend": {
                        "position": "right"
                    },
                    "region": AWS_DEFAULT_REGION,
                    "liveData": True,
                    "title": "EC2_Mem_Used_Percent",
                    "view": "timeSeries",
                    "stacked": False,
                }
            },
            {
                "type": "metric",
                "properties": {
                    "metrics": metrics_disk_val,
                    "legend": {
                        "position": "right"
                    },
                    "region": AWS_DEFAULT_REGION,
                    "liveData": True,
                    "title": "EC2_Disk_Used_Percent",
                    "view": "timeSeries",
                    "stacked": False,
                }
            },
        ]
    }
    try:
        response = cloudwatch_client.put_dashboard(
            DashboardName=CW_DASHBOARD_NAME,
            DashboardBody=json.dumps(body)
        )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            print(f"\"{CW_DASHBOARD_NAME}\" cloudwatch dashboard created successfully")
    except ClientError as e:
        if "DashboardName contains invalid characters" in e.response['Error']['Message']:
            print("DashboardName contains invalid characters")
        else:
            print("Unknown Error...")

def main():
    ec2_instances = describe_ec2_instances(ec2_client)
    metrics_cpu_val, metrics_status_val, metrics_mem_val, metrics_disk_val = [], [], [], []

    for ec2_name, ec2_id in ec2_instances.items():
        try:
            # 워커 노드 EC2 인스턴스 예외 처리
            if not ec2_name.endswith('-NG'):
                metrics_cpu_val.append(["AWS/EC2", "CPUUtilization", "InstanceId", ec2_id, {"label": ec2_name +" ("+ ec2_id +")" , "period": 60, "stat": "Average" }])
                metrics_status_val.append(["AWS/EC2", "StatusCheckFailed", "InstanceId", ec2_id, {"label": ec2_name +" ("+ ec2_id +")" , "period": 60, "stat": "Sum",}])
                metrics_mem_val.append(["CWAgent/Linux", "mem_used_percent", "InstanceId", ec2_id, {"label": ec2_name +" ("+ ec2_id +")" , "period": 60, }])
                metrics_disk_val.append(["CWAgent/Linux", "disk_used_percent", "path", "/", "InstanceId", ec2_id, "device", "nvme0n1p1", "fstype", "xfs", {"label": ec2_name +" ("+ ec2_id +")" , "period": 60, }])
            else:
                print("Excluded from metrics... %s is a Woker Node" % ec2_name)
        except KeyError:
                print("error")
                continue
    add_ec2_dashboard(metrics_cpu_val, metrics_status_val, metrics_mem_val, metrics_disk_val)

if __name__ == '__main__':
    main()
