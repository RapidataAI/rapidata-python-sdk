rm -rf openapi/openapi-client

openapi-generator generate -i openapi/output.swagger.json -g python -o openapi/openapi-client --skip-validate-spec