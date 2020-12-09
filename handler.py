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
    """
    Extrai metadados de objetos carregados no bucket, conforme 'serverless.yml',
    e salva na tabela de metadados (de nome = variável de ambiente 'DYNAMODB_TABLE').

    Metadados salvos: s3objectkey, size, type, width e height

    Args: 
        event: deve conter:
            ["Records"][0]["s3"]["bucket"]["name"]
            ["Records"][0]["s3"]["object"]["key"]
            ["Records"][0]["s3"]["object"]["size"]
        context: não utilizado
    Retorno: None
    """
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
    """
    Retorna uma resposta contendo metadados sobre o item especificado.

    Args:
        event:
            Deve conter uma 's3objectkey' dentro de 'pathParameters', com
            a object key da imagem cujos metadados se quer obter.
        context: não utilizado
    Retorno:
        'response', com 'statusCode' (200, 404, 400 ou 500) adequado,
        e corpo em JSON contendo uma mensagem, os metadados e o evento
        que originou a chamada. Formato do corpo:
        {
            'message': 'mensagem',
            's3ObjectMetadata':{
                's3objectkey': 'uploads/abc.xxx',
                'size': 123,
                'width': 123,
                'height': 123,
                'type': 'image/xxx'
            }
            'input': event
        }
    """
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
    """
    Retorna uma resposta contendo a imagem especificada

    Args:
        event:
            Deve conter uma 's3objectkey' dentro de 'pathParameters', com
            a object key da imagem que se deseja obter.
        context: não utilizado
    Retorno:
        'response', com 'statusCode' (200, 400 ou 500) adequado, e corpo
        em base64 contendo a imagem em si (que será convertido de volta
        para binário pelo API Gateway), ou em texto contendo uma mensagem
        (caso a imagem não seja encontrada).
    """
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
    """
    Retorna informações sobre as imagens cujos metadados estão armazenados

    Args:
        event: não utilizado
        context: não utilizado
    Retorno:
        'response', com 'statusCode' (200 ou 500) adequado, e corpo em 
        JSON, contendo informações sobre a maior imagem, a menor imagem,
        os tipos de imagens e quantidade de cada tipo. Formato do corpo:
        {
            'message': 'mensagem',
            'stats': {
                'biggest': {'s3objectkey':'chave', 'size':123}
                'smallest': {'s3objectkey':'chave', 'size':123}
                'types: {'type1':123, ..., 'typeN':123}
            }
            'input': event
        }
    """
    stats = {}
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