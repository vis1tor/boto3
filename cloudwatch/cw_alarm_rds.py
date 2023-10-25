import boto3

# 경보 매트릭 및 조건 선언
#===================================================================================================================

# 매트릭 구조
# "매트릭명" : ["매트릭 경보명 접미사","경보 통계",'데이터 포인트 표준 단위','경보 평가 기간(분,초,시,일)','경보 조건','임계값','데이터 포인트','데이터 포인트 평가 기간 범위','누락된 데이터 처리 방법','경보 설명']

# DB 경보명 형식 : [DB 식별자]-[매트릭 접미사]-[ALERT] ex) db-instance-1-CPU-ALERT

# DB 인스턴스 매트릭
cw_rds_metric = {
    "CPUUtilization" : ["CPU","Average","Percent",300,"GreaterThanOrEqualToThreshold",10.0,1,1,"missing","CPU 사용률"],
    "DatabaseConnections" : ["DBConnection","Sum","Count",300,"GreaterThanOrEqualToThreshold",10.0,1,1,"missing","DB 인스턴스에 대한 클라이언트 네트워크 연결 수"],
    "FreeStorageSpace" : ["FreeStorage","Average","Bytes",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","사용 가능한 스토리지"],
    "FreeableMemory" : ["FreeMemory","Average","Bytes",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","사용 가능한 메모리"]
}

cw_aurora_metric = {
    "CPUUtilization" : ["CPU","Average","Percent",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","CPU 사용률"],
    "DatabaseConnections" : ["DBConnection","Sum","Count",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","DB 인스턴스에 대한 클라이언트 네트워크 연결 수"],
    "FreeStorageSpace" : ["FreeStorage","Average","Bytes",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","사용 가능한 스토리지"],
    "FreeableMemory" : ["FreeMemory","Average","Bytes",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","사용 가능한 메모리"],
    "Deadlocks" : ["Deadlock","Sum","Count",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","교착 상태 발생 수"]
}
#===================================================================================================================
# SNS ARN - SNS 필요 시 입력
# sns_arn = ""

# DB 인스턴스 정보 조회
def describe_rds_instances(rds_client):
    response = rds_client.describe_db_instances()
    db_instances = response['DBInstances']
    return db_instances

# DB (Aurora 및 RDS) 경보 생성
def create_db_alarm(cloudwatch_client, db_instance_identifier, db_metric):
    for metric_name, metric_info in db_metric.items():
        alarm_name = db_instance_identifier.upper()+"-"+metric_info[0]+"-ALERT"

        response = cloudwatch_client.put_metric_alarm(
            AlarmName = alarm_name,
            #AlarmActions = sns_arn, 경보일 때
            #OKActions = sns_arn, 정상일 때
            MetricName = metric_name,
            Namespace = 'AWS/RDS',
            Statistic = metric_info[1],
            Unit = metric_info[2],
            Period = metric_info[3],
            ComparisonOperator = metric_info[4],
            Threshold = metric_info[5],
            Dimensions=[
                {
                    'Name': 'DBInstanceIdentifier',
                    'Value': db_instance_identifier
                }
            ],
            Tags=[
                {
                    'Key': 'Name',
                    'Value': 'test-alarm'
                },
            ],
            DatapointsToAlarm = metric_info[6],
            EvaluationPeriods = metric_info[7],
            TreatMissingData = metric_info[8],
            AlarmDescription = metric_info[9],
        )
        print('Alarm created successfully:', alarm_name)

def main():
    rds_client = boto3.client('rds')
    cloudwatch_client = boto3.client('cloudwatch')
    db_instances = describe_rds_instances(rds_client)

    for db_instance in db_instances:
        db_instance_identifier = db_instance['DBInstanceIdentifier']

        # DB 엔진명 Prefix 기준으로 Aurora와 RDS 구분
        if db_instance['Engine'].startswith('aurora'):
            create_db_alarm(cloudwatch_client, db_instance_identifier, cw_aurora_metric)
        else:
            create_db_alarm(cloudwatch_client, db_instance_identifier, cw_rds_metric)

if __name__ == '__main__':
    main()
