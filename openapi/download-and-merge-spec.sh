#!/bin/bash

rm -rf openapi/spec
mkdir openapi/spec

# Use a function to simulate an associative array
url_for() {
    case $1 in
    "order") echo "https://api.rabbitdata.ch/order/swagger/v1/swagger.json" ;;
    "dataset") echo "https://api.rabbitdata.ch/dataset/swagger/v1/swagger.json" ;;
    "identity") echo "https://api.rabbitdata.ch/identity/swagger/v1/swagger.json" ;;
    "validation") echo "https://api.rabbitdata.ch/validation/swagger/v1/swagger.json" ;;
    "rapid") echo "https://api.rabbitdata.ch/rapid/swagger/v1/swagger.json" ;;
    "workflow") echo "https://api.rabbitdata.ch/workflow/swagger/v1/swagger.json" ;;
    "pipeline") echo "https://api.rabbitdata.ch/pipeline/swagger/v1/swagger.json" ;;
    "campaign") echo "https://api.rabbitdata.ch/campaign/swagger/v1/swagger.json" ;;
    "leaderboard") echo "https://api.rabbitdata.ch/leaderboard/swagger/v1/swagger.json" ;;
    "asset") echo "https://api.rabbitdata.ch/asset/swagger/v1/swagger.json" ;;
    "audience") echo "https://api.rabbitdata.ch/audience/swagger/v1/swagger.json" ;;
    *) echo "" ;;
    esac
}

# List of keys
keys=("order" "dataset" "identity" "validation" "rapid" "workflow" "pipeline" "campaign" "leaderboard" "asset" "audience")

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
