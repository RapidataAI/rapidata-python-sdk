#!/bin/bash

rm -rf openapi/spec
mkdir openapi/spec

# Use a function to simulate an associative array
url_for() {
    case $1 in
    "order") echo "https://api.rabbitdata.ch/Order/swagger/v1/swagger.json" ;;
    "dataset") echo "https://api.rabbitdata.ch/Dataset/swagger/v1/swagger.json" ;;
    "identity") echo "https://api.rabbitdata.ch/Identity/swagger/v1/swagger.json" ;;
    "validation") echo "https://api.rabbitdata.ch/Validation/swagger/v1/swagger.json" ;;
    "rapid") echo "https://api.rabbitdata.ch/Rapid/swagger/v1/swagger.json" ;;
    "workflow") echo "https://api.rabbitdata.ch/Workflow/swagger/v1/swagger.json" ;;
    "pipeline") echo "https://api.rabbitdata.ch/Pipeline/swagger/v1/swagger.json" ;;
    "campaign") echo "https://api.rabbitdata.ch/Campaign/swagger/v1/swagger.json" ;;
    *) echo "" ;;
    esac
}

# List of keys
keys=("order" "dataset" "identity" "validation" "rapid" "workflow" "pipeline" "campaign")

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
