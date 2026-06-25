#!/usr/bin/env sh
set -eu

ENVIRONMENT="prod"

usage() {
    cat <<EOF
Usage: $0 [--environment ENV]

Options:
  -e, --env, --environment   Environment to use (prod | local)
  -h, --help                 Show this help

Examples:
  $0                       # uses prod
  $0 --environment local   # uses local
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -e|--env|--environment)
            [ $# -ge 2 ] || { echo "Error: missing value for $1" >&2; exit 1; }
            ENVIRONMENT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

case "$ENVIRONMENT" in
    prod)
        BASE_HOST="api.rabbitdata.ch"
        ;;
    local)
        BASE_HOST="api.rapidata.dev"
        ;;
    *)
        echo "Error: unknown environment '$ENVIRONMENT' (expected 'prod' or 'staging')" >&2
        exit 1
        ;;
esac

SERVICES="
asset
audience
order
dataset
pipeline
identity
rapid
campaign
validation
workflow
leaderboard
flow
translation
signal
"

download() {
    url=$1
    if command -v wget >/dev/null 2>&1; then
        wget -qO- "$url"
    elif command -v curl >/dev/null 2>&1; then
        curl -fsSL "$url"
    else
        echo "Error: neither wget nor curl is installed." >&2
        exit 1
    fi
}

SCHEMA_DIR="openapi/schemas"

# Update the OpenAPI specs
rm -rf "$SCHEMA_DIR"
mkdir -p "$SCHEMA_DIR"

for service in $SERVICES; do
    [ -z "$service" ] && continue

    url="https://${BASE_HOST}/${service}/openapi/v1.json"
    output_json="${SCHEMA_DIR}/${service}.openapi.json"

    echo "Fetching ${service} from ${url} (env=${ENVIRONMENT})..."

    download "$url" > "$output_json"
done

npx -y @redocly/cli join ./${SCHEMA_DIR}/*.openapi.json -o ./${SCHEMA_DIR}/rapidata.openapi.json

# Filter out anything deprecated so it is not generated into the SDK:
# fully-deprecated operations (whole endpoints), and — recursively —
# deprecated parameters and deprecated schema properties (also pruning the
# latter from any `required` list). This mirrors the endpoint filtering for
# partly-deprecated surfaces like a single deprecated field on a model.
# Note: the `walk` builtin requires jq >= 1.6.
jq '
  del(.paths[][] | select(.deprecated == true))
  | walk(
      if type == "object" then
        ( if (.parameters | type) == "array"
          then .parameters |= map(select(.deprecated != true))
          else . end )
        | ( if (.properties | type) == "object"
            then
              ( [ .properties | to_entries[] | select(.value.deprecated == true) | .key ] ) as $deprecated
              | .properties |= with_entries(select(.value.deprecated != true))
              | ( if (.required | type) == "array"
                  then .required |= map(select(. as $name | ($deprecated | index($name)) | not))
                  else . end )
            else . end )
      else . end
    )' \
   ${SCHEMA_DIR}/rapidata.openapi.json \
   > ${SCHEMA_DIR}/rapidata.filtered.openapi.json

# Regenerate SDK
rm -rf ./openapi/out
npx @openapitools/openapi-generator-cli generate \
  -g python \
  --global-property modelTests=false,modelDocs=false,apiTests=false,apiDocs=false \
  -i ${SCHEMA_DIR}/rapidata.filtered.openapi.json \
  -o ./src \
  -c openapi/config.yaml \
  -t openapi/templates
