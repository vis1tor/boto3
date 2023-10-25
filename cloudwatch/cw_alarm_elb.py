import boto3

# 경보 매트릭 및 조건 선언
#===================================================================================================================

# 매트릭 구조
# "매트릭명" : ["매트릭 경보명 접미사","경보 통계",'데이터 포인트 표준 단위','경보 평가 기간(분,초,시,일)','경보 조건','임계값','데이터 포인트','데이터 포인트 평가 기간 범위','누락된 데이터 처리 방법','경보 설명']

# ELB 경보명 형식 : [ELB명]-[매트릭 접미사]-[ALERT] ex) TEST-FEP-NLB-ProcessedBytes-TCP-ALERT
# 대상그룹 경보명 형식 : [대상그룹명]-[매트릭 접미사]-[ALERT] ex) TEST-SFTP-IN-22-TG-UnHealthyCount-ALERT

# NLB 로드 밸런서 매트릭
cw_nlb_metric = {
    "ProcessedBytes_TCP": ["ProcessedBytes-TCP","Sum","Bytes",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","TCP 리스너에서 처리한 총 바이트 수"]
}

# NLB 로드 밸런서 대상 그룹 매트릭
cw_nlb_tg_metric = {
    "UnHealthyHostCount": ["UnHealthyCount","Maximum","Count",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","비정상 상태로 간주되는 대상 수"]
}

# ALB 로드 밸런서 매트릭
cw_alb_metric = {
    "HTTPCode_ELB_3XX_Count" : ["HTTP-3XX-Count","Sum","Count",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","HTTP 3XX 리디렉션 코드의 수"],
    "HTTPCode_ELB_4XX_Count" : ["HTTP-4XX-Count","Sum","Count",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","HTTP 4XX 클라이언트 오류 코드 수"],
    "HTTPCode_ELB_5XX_Count" : ["HTTP-5XX-Count","Sum","Count",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","HTTP 5XX 서버 오류 코드 수"]
}

# ALB 로드 밸런서 대상 그룹 매트릭
cw_alb_tg_metric = {
    "UnHealthyHostCount" : ["UnHealthyCount","Maximum","Count",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","비정상 상태로 간주되는 대상 수"],
    "HTTPCode_Target_3XX_Count" : ["HTTP-3XX-Count","Sum","Count",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","대상에서 생성된 HTTP 3XX 응답 코드 수"],
    "HTTPCode_Target_4XX_Count" : ["HTTP-4XX-Count","Sum","Count",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","대상에서 생성된 HTTP 4XX 응답 코드 수"],
    "HTTPCode_Target_5XX_Count" : ["HTTP-5XX-Count","Sum","Count",300,"GreaterThanOrEqualToThreshold",1.0,1,1,"missing","대상에서 생성된 HTTP 5XX 응답 코드 수"]
}
#===================================================================================================================

# SNS ARN - SNS 필요 시 입력
# sns_arn = ""
#===================================================================================================================

# 로드 밸런서 조회
def describe_elb(elbv2_client):
    elbs = []
    
    response = elbv2_client.describe_load_balancers()
    for elb in response['LoadBalancers']:
        elbs.append(elb)
    
    return elbs

# 로드 밸런서의 리스너 조회
def describe_listeners(elbv2_client, lb_arn):
    response = elbv2_client.describe_listeners(LoadBalancerArn=lb_arn)
    return response['Listeners']

# 로드밸런서 경보 생성
def create_elb_alarm(cloudwatch_client, lb_resource_arn, metric_ns, lb_metric):
    for metric_name, metric_info in lb_metric.items():
        alarm_name = lb_resource_arn.split('/')[2]+"-"+metric_info[0]+"-ALERT"

        response = cloudwatch_client.put_metric_alarm(
            AlarmName = alarm_name,
            #AlarmActions = sns_arn, 경보일 때
            #OKActions = sns_arn, 정상일 때
            MetricName = metric_name,
            Namespace = metric_ns,
            Statistic = metric_info[1],
            Unit = metric_info[2],
            Period = metric_info[3],
            ComparisonOperator = metric_info[4],
            Threshold = metric_info[5],
            Dimensions=[
                {
                    'Name': 'LoadBalancer',
                    'Value': lb_resource_arn.split(':loadbalancer/')[1]
                }
            ],
            Tags=[
                {
                    'Key': 'map-migrated',
                    'Value': 'migI89WC6ABM4'
                },
            ],
            DatapointsToAlarm = metric_info[6],
            EvaluationPeriods = metric_info[7],
            TreatMissingData = metric_info[8],
            AlarmDescription = metric_info[9]
        )
        print('Alarm created successfully:', alarm_name)
#===================================================================================================================

# 로드 밸런서의 대상 그룹(Target Group) 경보 생성
def create_elb_tg_alarm(cloudwatch_client, lb_resource_arn, metric_ns, lb_tg_metric, lb_target_group_arn):

    for metric_name, metric_info in lb_tg_metric.items():
        alarm_name = lb_target_group_arn.split('/')[1]+"-"+metric_info[0]+"-ALERT"

        response = cloudwatch_client.put_metric_alarm(
            AlarmName = alarm_name,
            #AlarmActions = sns_arn,
            MetricName = metric_name,
            Namespace = metric_ns,
            Statistic = metric_info[1],
            Unit = metric_info[2],
            Period = metric_info[3],
            ComparisonOperator = metric_info[4],
            Threshold = metric_info[5],
            Dimensions=[
                {
                    'Name': 'TargetGroup',
                    'Value': lb_target_group_arn
                },
                {
                    'Name': 'LoadBalancer',
                    'Value': lb_resource_arn.split(':loadbalancer/')[1]
                }
            ],
            Tags=[
                {
                    'Key': 'map-migrated',
                    'Value': 'migI89WC6ABM4'
                },
            ],
            DatapointsToAlarm = metric_info[6],
            EvaluationPeriods = metric_info[7],
            TreatMissingData = metric_info[8],
            AlarmDescription = metric_info[9]
        )
        print('Alarm created successfully:', alarm_name)
#===================================================================================================================

def main():
    elbv2_client = boto3.client('elbv2')
    cloudwatch_client = boto3.client('cloudwatch')
    elbs = describe_elb(elbv2_client)

    for lb in elbs :
        # ALB, NLB 분리
        if lb['Type'] == 'network':
            metric_ns = 'AWS/NetworkELB'
            
            create_elb_alarm(cloudwatch_client, lb['LoadBalancerArn'], metric_ns, cw_nlb_metric)
            listeners = describe_listeners(elbv2_client, lb['LoadBalancerArn'])
            
            for listener in listeners:
                #리다이렉트 리스너 예외처리
                if listener.get('DefaultActions')[0].get('Type') == 'redirect':
                    print(f"Alarm creation has failed... This \"{listener.get('ListenerArn').split(':')[5]}\" is a Redirect listener, so it does not have a target group.")
                    
                else:
                    lb_target_group_arn = [tg_arn.get('TargetGroupArn').split(':')[-1] for tg_arn in listener.get('DefaultActions')][0]
                    create_elb_tg_alarm(cloudwatch_client, lb['LoadBalancerArn'], metric_ns, cw_nlb_tg_metric, lb_target_group_arn)

        elif lb['Type'] == 'application':
            metric_ns = 'AWS/ApplicationELB'
            
            create_elb_alarm(cloudwatch_client, lb['LoadBalancerArn'], metric_ns, cw_alb_metric)
            listeners = describe_listeners(elbv2_client, lb['LoadBalancerArn'])
            
            for listener in listeners:
                if listener.get('DefaultActions')[0].get('Type') == 'redirect':
                    print(f" Alarm creation has failed...This \"{listener.get('ListenerArn').split(':')[5]}\" is a Redirect listener, so it does not have a target group.")
                else:
                    lb_target_group_arn = [tg_arn.get('TargetGroupArn').split(':')[-1] for tg_arn in listener.get('DefaultActions')][0]
                    create_elb_tg_alarm(cloudwatch_client, lb['LoadBalancerArn'], metric_ns, cw_alb_tg_metric, lb_target_group_arn)
                
if __name__ == "__main__":
    main()
