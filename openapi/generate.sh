./download-spec.sh

npx openapi-merge-cli

rm -rf ../rapidata/openapi-client

openapi-generator generate -i output.swagger.json -g python -o openapi-client --skip-validate-spec