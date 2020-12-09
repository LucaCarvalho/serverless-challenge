# serverless-challenge (Luca Carvalho)
Minha solução para o desafio da [Solvimm](https://github.com/solvimm/serverless-challenge)

## Conteúdo
<!--ts-->
* [Instalação](#instalação)
* [Como usar](#como-usar)
* [Funcionalidades](#funcionalidades)
<!--te-->

## Instalação
Esse projeto requer uma conta AWS. Para fazer o seu deployment,
utilizar o framework Serverless.

Primeiramente, para instalar dependências, vá ao diretório-raiz do
projeto e rode:
```bash
npm install
```

Para configurar o Serverless:
```bash
serverless
```

Para fazer o deploy:
```bash
serverless deploy
```

## Como usar
Para alimentar o sistema, basta fazer upload de imagens para o diretório 'uploads/' do bucket 'challenge-bucket'.
As extensões (e respectivos tipos) de imagem permitidos são:
- .jpg/.jpeg
- .tif/.tiff
- .png
- .gif
- .bmp
- .ico

Para consultar informações, é necessário realizar requisições GET para um dos seguintes resources:
- /images/uploads/{s3objectkey SEM 'uploads/'}
- /images/getImage/uploads/{s3objectkey SEM 'uploads/'}
- /images/info

ATENÇÃO: 's3objectkey' NÃO deve conter o prefixo 'uploads/'. Os caminhos acima são os caminhos reais dos
resources, mas, na prática, como todos os 's3objectkey' armazenados têm o prefixo 'uploads/', os caminhos
ficam simplesmente (e devem ser tratados como):
- /images/{s3objectkey}
- /images/getImage/{s3objectkey}
- /images/info
Ou seja, o objeto com s3objectkey='uploads/image.jpg' deve ser passado como '/images/uploads/image.jpg', NÃO
'images/uploads/uploads/image.jpg'.

A seguir, a corpo da resposta de cada uma das requisições (e uma breve descrição):

- /images/{s3objectkey}

Dada uma s3objectkey, são retornados os metadados da imagem correspondente.
```
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
}´
```

- /images/getImage/{s3objectkey}

Dada uma s3objectkey, é retornado o binário da imagem. Contém "Content-Disposition: attachment" no cabeçalho, o que causa o download da mesma caso seja requisitada em browser.
```
(imagem em binário)
```

- /images/info

Retorna informações sobre os metadados armazenados. Especificamente, s3objectkey e tamanho da maior e da menor imagem, os tipos de imagem armazenados e a quantidade de cada tipo.
```
{
    'message': 'mensagem',
    'stats': {
        'biggest': {'s3objectkey':'chave', 'size':123}
        'smallest': {'s3objectkey':'chave', 'size':123}
        'types: {'type1':123, ..., 'typeN':123}
    }
    'input': event
}
```

## Funcionalidades
Resumidamente, quando uma imagem é carregada para a pasta 'uploads/' do bucket 'challenge-bucket', uma função do Lambda ('extractMetadata') é chamada. Ela realiza a extração dos metadados da imagem e os salva em uma tabela do DynamoDB.
Foi implementada uma API REST simples (utilizando o API Gateway) que tem as funcionalidades especificadas acima.

A ilustração, fornecida com o próprio desafio:
![Screenshot](Architecture.png)
