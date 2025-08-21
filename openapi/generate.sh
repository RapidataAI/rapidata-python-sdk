#!/bin/bash
# Filter out deprecated endpoints
jq 'del(.paths[][] | select(.deprecated == true))' openapi/output.swagger.json > openapi/filtered.swagger.json

# Generate client using filtered spec
npx openapi-generator-cli generate --global-property modelTests=false,modelDocs=false,apiTests=false,apiDocs=false -i openapi/filtered.swagger.json -g python -o ./src -c openapi/config.yaml -t openapi/templates
