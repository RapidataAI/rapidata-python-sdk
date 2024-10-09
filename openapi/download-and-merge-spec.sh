#!/bin/bash

rm -rf openapi/spec
mkdir openapi/spec

# Use a function to simulate an associative array
url_for() {
    case $1 in
    "order") echo "https://api.app.rabbitdata.ch/Order/swagger/v1/swagger.json" ;;
    "dataset") echo "https://api.app.rabbitdata.ch/Dataset/swagger/v1/swagger.json" ;;
    "identity") echo "https://api.app.rabbitdata.ch/Identity/swagger/v1/swagger.json" ;;
    "validation") echo "https://api.app.rabbitdata.ch/Validation/swagger/v1/swagger.json" ;;
    "rapid") echo "https://api.rapids.rabbitdata.ch/Rapid/swagger/v1/swagger.json" ;;
    "workflow") echo "https://api.app.rabbitdata.ch/Workflow/swagger/v1/swagger.json" ;;
    "pipeline") echo "https://api.app.rabbitdata.ch/Pipeline/swagger/v1/swagger.json" ;;
    "campaing") echo "https://api.app.rabbitdata.ch/Campaign/swagger/v1/swagger.json" ;;
    *) echo "" ;;
    esac
}

# List of keys
keys=("order" "dataset" "identity" "validation" "rapid" "workflow", "pipeline", "campaing")

for key in "${keys[@]}"; do
    url=$(url_for "$key")
    output_json="openapi/spec/${key}.json"

    # Download the JSON file using curl
    curl -o "$output_json" "$url"

    echo "Downloaded $url to $output_json"

done

# Merge the OpenAPI specs into a single file (output.swagger.json)
cd openapi
npx openapi-merge-cli
