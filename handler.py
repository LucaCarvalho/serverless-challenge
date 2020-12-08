# coding=utf-8

import boto3
from boto3.dynamodb.conditions import Key
import simplejson as json
import pprint
from PIL import Image
import io
import os
from urllib.parse import unquote_plus
import base64

dynamodb = boto3.resource("dynamodb")
s3 = boto3.resource("s3")
dynamodbResource = boto3.resource("dynamodb")

def extractMetadata(event, context):
    #TODO: try - catch
    bucketName = event["Records"][0]["s3"]["bucket"]["name"]
    objectKey = unquote_plus(event["Records"][0]["s3"]["object"]["key"])
    objectSize = event["Records"][0]["s3"]["object"]["size"]

    s3Obj = s3.Object(bucketName, objectKey)
    s3Response = s3Obj.get()

    imageBin = s3Response["Body"].read()
    imageStream = io.BytesIO(imageBin)
    image = Image.open(imageStream)
    
    dbResponse = dynamodb.batch_write_item(
        RequestItems={
            os.environ["DYNAMODB_TABLE"]:[
                {
                    "PutRequest":{
                        "Item":{
                            "s3objectkey":objectKey,
                            "size":objectSize,
                            "type":s3Obj.content_type,
                            "width":image.width,
                            "height":image.height
                        }
                    }
                }
            ]
        }
    )

    if dbResponse["ResponseMetadata"]["HTTPStatusCode"] == 200:
        print("Success!")
    else:
        pprint.pp(dbResponse)

    io.IOBase.close(imageStream)



def getMetadata(event, context):
    s3ObjectMetadata = {}

    try:
        s3ObjectKey = "uploads/"+event["pathParameters"]["s3objectkey"]#
        dbResponse = dynamodbResource.Table(os.environ["DYNAMODB_TABLE"]).query(
            KeyConditionExpression=Key("s3objectkey").eq(s3ObjectKey)
        )

        if dbResponse["Count"] > 0:
            s3ObjectMetadata = dbResponse["Items"][0]
            message = "Item found!"
            statusCode = 200
        else:
            message = "Item not found!"
            statusCode = 404
    except TypeError:
        message = "Missing s3objectkey!"
        statusCode = 400
    except Exception as e:
        message = str(e)
        statusCode = 500

    body = {
        "message": message,
        "s3ObjectMetadata": s3ObjectMetadata,
        "input": event
    }
    response = {
        "statusCode": statusCode,
        "body": json.dumps(body)
    }

    return response

def getImage(event, context):
    contentType = "application/json"
    contentDisposition = "inline"
    isBase64Encoded = False

    try:
        s3ObjectKey = "uploads/"+event["pathParameters"]["s3objectkey"]#
        bucketName = "challenge-bucket"

        s3Obj = s3.Object(bucketName, s3ObjectKey)
        s3Response = s3Obj.get()
        imageBin = s3Response["Body"].read()

        contentType = s3Obj.content_type
        contentDisposition = "attachment"
        isBase64Encoded = True
        body = base64.b64encode(imageBin).decode("utf-8")
        statusCode = 200
    except TypeError:
        body = "Missing s3objectkey!"
        statusCode = 400
    except Exception as e:
        body = str(e)
        statusCode = 500
    
    response = {
        "statusCode": statusCode,
        "isBase64Encoded": isBase64Encoded,
        "headers": {
            "Content-Type": contentType,
            "Content-Disposition": contentDisposition
        },
        "body": body
    }

    return response
        
def infoImages(event, context):
    stats = ""
    try:
        biggest = {"s3objectkey":"", "size":0}
        smallest = {"s3objectkey":"", "size":float("inf")}
        types = dict()

        results = dynamodbResource.Table(os.environ["DYNAMODB_TABLE"]).scan()
        while True:
            for item in results["Items"]:
                if biggest["size"] < item["size"]:
                    biggest["s3objectkey"] = item["s3objectkey"]
                    biggest["size"] = item["size"]
                if item["size"] < smallest["size"]:
                    smallest["s3objectkey"] = item["s3objectkey"]
                    smallest["size"] = item["size"]
                if item["type"] in types:
                    types[item["type"]] += 1
                else:
                    types[item["type"]] = 1

            if "LastEvaluatedKey" not in results:
                break
            results = dynamodbResource.Table(os.environ["DYNAMODB_TABLE"]).scan(ExclusiveStartKey=results["LastEvaluatedKey"])                

        stats = {
            "biggest": biggest,
            "smallest": smallest,
            "types": types
        }

        message = "Done!"
        statusCode = 200

    except Exception as e:
        message = str(e)
        statusCode = 500

    body = {
        "message": message,
        "stats": stats,
        "input": event
    }
    response = {
        "statusCode": statusCode,
        "body": json.dumps(body)
    }

    return response