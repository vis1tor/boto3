import boto3
import json
from botocore.exceptions import ClientError

#출발(ALB)/도착지(S3) IAM AccessKey 정보
#======================================================================
SRC_AWS_ACCESS_KEY_ID = "출발지(PRD) 액세스 키 ID 입력"
SRC_AWS_SECRET_ACCESS_KEY = "출발지(PRD) 액세스 키 입력"
SRC_AWS_DEFAULT_REGION = "ap-northeast-2"

DST_AWS_ACCESS_KEY_ID ="목적지(SEC) 액세스 키 ID 입력"
DST_AWS_SECRET_ACCESS_KEY = "목적지(SEC) 액세스 키 입력"
DST_AWS_DEFAULT_REGION = "ap-northeast-2"
#======================================================================

#Access Log 활성화 대상 ELB 태그 및 리전
#======================================================================
ELB_TAG_KEY = "액세스 로그 활성화 대상 ELB 태그 키 입력"
ELB_TAG_VAL = "액세스 로그 활성화 대상 ELB 태그 값 입력"
elb_region = "600734575887" # 서울 기준
#======================================================================

#S3에 추가할 태그 및 리전
#======================================================================
S3_TAG_KEY = "추가할 S3 태그 키 입력"
S3_TAG_VAL = "추가할 S3 태그 값 입력"
s3_region = "ap-northeast-2" # 서울 기준
#======================================================================

src_client = boto3.client('elbv2',
                      aws_access_key_id=SRC_AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=SRC_AWS_SECRET_ACCESS_KEY,
                      region_name=SRC_AWS_DEFAULT_REGION
                      )

dst_client = boto3.client('s3',
                      aws_access_key_id=DST_AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=DST_AWS_SECRET_ACCESS_KEY,
                      region_name=DST_AWS_DEFAULT_REGION
                      )

def describe_elb(src_client):
    elbs = []

    response = src_client.describe_load_balancers()
    for elb in response['LoadBalancers']:
        elbs.append(elb)
    
    return elbs


def describe_elb_tag(src_client,LoadBalancerArn):
    lb_arn = ""

    response = src_client.describe_tags(
        ResourceArns=[
            LoadBalancerArn,
        ]
    )
    for i in response['TagDescriptions'][0]['Tags']:
        if i['Key'] == ELB_TAG_KEY and i['Value'] == ELB_TAG_VAL:
            lb_arn = LoadBalancerArn
    
    return lb_arn

def modify_elb_attributes(src_client,lb_arn,lb_name,s3_name):
    response = src_client.modify_load_balancer_attributes(
        Attributes=[
            {
                'Key': 'access_logs.s3.enabled',
                'Value': 'true',
            },
             {
                'Key': 'access_logs.s3.bucket',
                'Value': s3_name,
            }
        ],
        LoadBalancerArn=lb_arn
    )
    print(f"The \"{lb_name}\" ALB access logs have been successfully enabled.")
    return response

def create_bucket(dst_client,s3_name):
    
    # S3 정책 선언
    dic_s3_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::"+elb_region+":root"
                },
                "Action": "s3:PutObject",
                "Resource": "arn:aws:s3:::"+s3_name+"/*"
            }
        ]
    }
    
    # Dictionary 형태 Josn 으로 변환
    s3_policy=json.dumps(dic_s3_policy)
    
    try:
        # S3 버킷 생성
        response = dst_client.create_bucket(
            Bucket=s3_name,
            CreateBucketConfiguration={
                'LocationConstraint': s3_region # Seoul  # us-east-1을 제외한 지역은 LocationConstraint 명시해야함.
            }
        )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            print(f"\"{s3_name}\" bucket created successfully")
            
            # S3 태깅
            response = dst_client.put_bucket_tagging(
                Bucket=s3_name,
                Tagging={
                    'TagSet': [
                        {
                            'Key': S3_TAG_KEY,
                            'Value': S3_TAG_VAL
                        },
                    ]
                }
            )
            # S3 정책 적용
            response = dst_client.put_bucket_policy(
                Bucket=s3_name,
                Policy=s3_policy
            )

    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print(f"Bucket \"{s3_name}\" already exists, skipping...")
        else:
            print("Unknown Error...")

def main():
    elbs = describe_elb(src_client)

    for lb in elbs :
        # ALB, NLB 분리
        if lb['Type'] == 'application':
            lb_arn = describe_elb_tag(src_client,lb['LoadBalancerArn'])
            lb_name = lb['LoadBalancerArn'].split('/')[2]

            if lb_arn:
                try:
                    s3_name = lb_name.lower()+"-access-log-s3"
                    create_bucket(dst_client,s3_name)
                    modify_elb_attributes(src_client,lb_arn,lb_name,s3_name)
                except ClientError as e:
                        print(f"Access Denied for \"{s3_name}\". Please check s3bucket permission")
            else:
                print(f"The \"{lb_name}\" ALB does not match the specified tags.")
                continue
                
if __name__ == "__main__":
    main()
