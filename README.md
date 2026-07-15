# dem-client

Cliente DEM que executa regras ativas e envia os resultados para a API.

## Requisitos

- Python 3.10+ (recomendado)
- `bash` disponível no sistema

## Como rodar

1. Abra um terminal na pasta do projeto:

   ```bash
   cd dem-client
   ```

2. Execute o cliente com os parametros da API e do token:

   ```bash
   python3 dem-client.py --API_BASE_URL http://127.0.0.1:3026 --CLIENT_FIXED_TOKEN df991b67-24b2-4121-8c73-9c3ab4b0dba2
   ```

   O cliente envia o header `x-api-token` com este valor padrao:

   ```text
   df991b67-24b2-4121-8c73-9c3ab4b0dba2
   ```

   Se quiser usar outro valor, substitua o parametro `--CLIENT_FIXED_TOKEN`:

   ```bash
   python3 dem-client.py --API_BASE_URL http://127.0.0.1:3026 --CLIENT_FIXED_TOKEN seu-token
   ```

## O que o cliente faz

- Busca as verificações ativas em `GET /api/verifications/active`
- Executa o comando de cada regra localmente
- Valida a saída usando `validationType` e `validationValue`
- Envia o resultado para `POST /api/verification-results`

## Validação

- `exact`: a saída precisa ser igual ao valor informado em `validationValue`
- `regex`: a saída precisa corresponder ao regex informado em `validationValue`
- Se `validationType` ou `validationValue` não vierem preenchidos, a regra é considerada válida apenas pelo código de saída do comando

## Observações

- O comando de cada regra é executado via `bash -lc`
- O resultado é considerado `success` quando o comando termina com código 0 e a validação passa
- Se a API ficar indisponível, o cliente registra um erro amigável e encerra sem retornar falha
