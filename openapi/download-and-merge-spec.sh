#!/bin/bash

rm -rf openapi/spec
mkdir openapi/spec

# Use a function to simulate an associative array
url_for() {
    case $1 in
    "order") echo "https://api.rabbitdata.ch/order/openapi/v1.json" ;;
    "dataset") echo "https://api.rabbitdata.ch/dataset/openapi/v1.json" ;;
    "identity") echo "https://api.rabbitdata.ch/identity/openapi/v1.json" ;;
    "validation") echo "https://api.rabbitdata.ch/validation/openapi/v1.json" ;;
    "rapid") echo "https://api.rabbitdata.ch/rapid/openapi/v1.json" ;;
    "workflow") echo "https://api.rabbitdata.ch/workflow/openapi/v1.json" ;;
    "pipeline") echo "https://api.rabbitdata.ch/pipeline/openapi/v1.json" ;;
    "campaign") echo "https://api.rabbitdata.ch/campaign/openapi/v1.json" ;;
    "leaderboard") echo "https://api.rabbitdata.ch/leaderboard/openapi/v1.json" ;;
    "asset") echo "https://api.rabbitdata.ch/asset/openapi/v1.json" ;;
    "audience") echo "https://api.rabbitdata.ch/audience/openapi/v1.json" ;;
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
