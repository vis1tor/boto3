import boto3

# 경보 매트릭 및 조건 선언
#===================================================================================================================

# 매트릭 구조
# "매트릭명" : ["매트릭 경보명 접미사","경보 통계",'데이터 포인트 표준 단위','경보 평가 기간(분,초,시,일)','경보 조건','임계값','데이터 포인트','데이터 포인트 평가 기간 범위','누락된 데이터 처리 방법','경보 설명']

# EC2 경보명 형식 : [EC2명]-[매트릭 접미사]-[ALERT] ex) TEST-K8S-MGMT-EC2-CPU-ALERT

# EC2 인스턴스 매트릭
cw_ec2_metric = {
    'CPUUtilization' : ['AWS/EC2','CPU','Average','Percent',60,'GreaterThanOrEqualToThreshold',10.0,1,1,'missing',"CPU 사용률"], # stress -c 1 -t 60 & 명령어로 확인 가능
    'StatusCheckFailed' : ['AWS/EC2','STATUS','Maximum','Count',60,'GreaterThanOrEqualToThreshold',1.0,1,1,'ignore',"인스턴스 상태 검사"], # sudo ifconfig enX0 down 명령어로 확인 가능
}
#===================================================================================================================
# SNS ARN - SNS 필요 시 입력
# sns_arn = ""

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

# EC2 경보 생성
def create_ec2_alarm(cloudwatch_client, ec2_name, ec2_id, ec2_metric):
    for metric_name, metric_info in ec2_metric.items():
        alarm_name = ec2_name+"-"+metric_info[1]+"-ALERT"

        response = cloudwatch_client.put_metric_alarm(
            AlarmName = alarm_name,
            #AlarmActions = sns_arn, 경보일 때
            #OKActions = sns_arn, 정상일 때
            MetricName = metric_name,
            Namespace = metric_info[0],
            Statistic = metric_info[2],
            Unit = metric_info[3],
            Period = metric_info[4],
            ComparisonOperator = metric_info[5],
            Threshold = metric_info[6],
            Dimensions = [
                {
                    "Name": "InstanceId",
                    "Value": "%s" % ec2_id
                }
            ],
            Tags=[
                {
                    'Key': 'map-migrated',
                    'Value': 'migI89WC6ABM4'
                },
            ],
            DatapointsToAlarm = metric_info[7],
            EvaluationPeriods = metric_info[8],
            TreatMissingData = metric_info[9],
            AlarmDescription = metric_info[10]
        )
        print('Alarm has been successfully created:', alarm_name)

def main():
    ec2_client = boto3.client('ec2')
    cloudwatch_client = boto3.client('cloudwatch')
    ec2_instances = describe_ec2_instances(ec2_client)

    for ec2_name, ec2_id in ec2_instances.items():
        try:
            # 노드 그룹 EC2 인스턴스 예외처리
            if not ec2_name.endswith('-NG'):
                create_ec2_alarm(cloudwatch_client, ec2_name, ec2_id, cw_ec2_metric)
            else:
                print("Alarm creation has failed... %s is a Node Group" % ec2_name)
        except KeyError:
                print("error")
                continue

if __name__ == '__main__':
    main()
