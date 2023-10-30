import boto3
import json
from botocore.exceptions import ClientError

#출발(TGW)/도착지(S3) IAM 유저 AccessKey 정보
#======================================================================
SRC_AWS_ACCESS_KEY_ID = "출발지 액세스 키 ID 입력"
SRC_AWS_SECRET_ACCESS_KEY = "출발지 액세스 키 입력"
SRC_AWS_DEFAULT_REGION = "ap-northeast-2"

DST_AWS_ACCESS_KEY_ID ="목적지 액세스 키 ID 입력"
DST_AWS_SECRET_ACCESS_KEY = "목적지 액세스 키 입력"
DST_AWS_DEFAULT_REGION = "ap-northeast-2"
#======================================================================

CMK_ARN = "목적지 CMK ARN 입력"

#TGW Flow Log 활성화 대상 TGW 태그 및 Flow Log 생성 시, 추가할 태그
#======================================================================
TGW_FILTER_TAG_KEY = "TGW Flow Log 활성화 대상 TGW 태그 키 입력"
TGW_FILTER_TAG_VAL = "TGW Flow Log 활성화 대상 TGW 태그 값 입력"

TGW_FLOW_TAG_KEY = "생성할 TGW Flow Log 태그 키 입력"
TGW_FLOW_TAG_VAL = "생성할 TGW Flow Log 태그 키 입력"
#======================================================================

#S3에 추가할 태그 및 리전
#======================================================================
s3_name = "생성할 S3 이름 입력"
S3_TAG_KEY = "생성할 S3 태그 키 입력"
S3_TAG_VAL = "생성할 S3 태그 키 입력"
s3_region = "ap-northeast-2" # 서울 기준
#======================================================================

src_client = boto3.client('ec2',
                      aws_access_key_id=SRC_AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=SRC_AWS_SECRET_ACCESS_KEY,
                      region_name=SRC_AWS_DEFAULT_REGION
                      )

dst_client = boto3.client('s3',
                      aws_access_key_id=DST_AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=DST_AWS_SECRET_ACCESS_KEY,
                      region_name=DST_AWS_DEFAULT_REGION
                      )

# TGW Flow Log 활성화 대상 TGW를 태그 기준으로 필터
def describe_tgw():
    
    response = src_client.describe_transit_gateways(
        Filters = [
            {
                'Name': f'tag:{TGW_FILTER_TAG_KEY}',
                'Values': [TGW_FILTER_TAG_VAL]
            }
        ]
    )    
    return response


def create_bucket(tgw_owner, s3_name):
    # S3 정책 선언
    dic_s3_policy = {
            "Version": "2012-10-17",
            "Id": "AWSLogDeliveryWrite20150319",
            "Statement": [
                {
                    "Sid": "AWSLogDeliveryWrite",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "delivery.logs.amazonaws.com"
                    },
                    "Action": "s3:PutObject",
                    "Resource": "arn:aws:s3:::"+s3_name+"/AWSLogs/"+tgw_owner+"/*",
                    "Condition": {
                        "StringEquals": {
                            "s3:x-amz-acl": "bucket-owner-full-control",
                            "aws:SourceAccount": tgw_owner
                        },
                        "ArnLike": {
                            "aws:SourceArn": "arn:aws:logs:ap-northeast-2:"+tgw_owner+":*"
                        }
                    }
            },
            {
                "Sid": "AWSLogDeliveryAclCheck",
                "Effect": "Allow",
                "Principal": {
                    "Service": "delivery.logs.amazonaws.com"
                },
                "Action": "s3:GetBucketAcl",
                "Resource": "arn:aws:s3:::"+s3_name,
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": tgw_owner
                    },
                    "ArnLike": {
                        "aws:SourceArn": "arn:aws:logs:ap-northeast-2:"+tgw_owner+":*"
                    }
                }
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
                            'Key': "Name",
                            'Value': s3_name
                        },
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
    
            # S3 암호화
            response = dst_client.put_bucket_encryption(
                Bucket=s3_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [
                        {
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'aws:kms',
                                'KMSMasterKeyID': CMK_ARN
                            },
                            'BucketKeyEnabled': True
                        },
                    ]
                }
            )

    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print(f"\"{s3_name}\" Bucket already exists, skipping...")
        else:
            print("Unknown Error...")


def create_tgw_flow_log(tgw_id, tgw_name, s3_name):
    try:
        response = src_client.create_flow_logs(
            ResourceType='TransitGateway',
            ResourceIds = tgw_id,
            LogDestinationType = 's3',
            LogDestination = 'arn:aws:s3:::'+s3_name,
            LogFormat ="${version} ${resource-type} ${account-id} ${tgw-id} ${tgw-attachment-id} ${tgw-src-vpc-account-id} ${tgw-dst-vpc-account-id} ${tgw-src-vpc-id} ${tgw-dst-vpc-id} ${tgw-src-subnet-id} ${tgw-dst-subnet-id} ${tgw-src-eni} ${tgw-dst-eni} ${tgw-src-az-id} ${tgw-dst-az-id} ${tgw-pair-attachment-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${log-status} ${type} ${packets-lost-no-route} ${packets-lost-blackhole} ${packets-lost-mtu-exceeded} ${packets-lost-ttl-expired} ${tcp-flags} ${region} ${flow-direction} ${pkt-src-aws-service} ${pkt-dst-aws-service}",
            DestinationOptions={
            'FileFormat': 'plain-text',
            'HiveCompatiblePartitions': False,
            'PerHourPartition': False
            },
            TagSpecifications = [
                {
                        'ResourceType': 'vpc-flow-log',
                        'Tags': [
                            {
                                'Key': "Name",
                                'Value': tgw_name + "-FLOW-LOG"
                            },
                            {
                                'Key': TGW_FLOW_TAG_KEY,
                                'Value': TGW_FLOW_TAG_VAL
                            },
                        ]
                    },
                ]
            )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            print(f"\"{tgw_name}\"-FLOW-LOG created successfully")

    except ClientError as e:
        if e.response['Error']['Code'] == 'FlowLogAlreadyExists':
            print(f"\"{tgw_name}-FLOW-LOG\" Flow Log already exists, skipping...")
        else:
            print("Unknown Error...")


def main():
    tgws = describe_tgw()
    
    for tgw in tgws['TransitGateways']:
        for tgw_tag in tgw['Tags']:
            if tgw_tag['Key'] == 'Name':
                tgw_name = tgw_tag['Value']
        tgw_owner = tgw['OwnerId']
        tgw_id = tgw['TransitGatewayId']
      
        create_bucket(tgw_owner, s3_name)
        create_tgw_flow_log([tgw_id], tgw_name, s3_name)
    

if __name__ == "__main__":
    main()
