#!/usr/bin/env sh
set -eu

ENVIRONMENT="prod"
ENVIRONMENT_EXPLICIT=false
SCHEMA_SOURCE=""

usage() {
    cat <<EOF
Usage: $0 [--environment ENV | --schema-dir DIR]

Options:
  -e, --env, --environment   Environment to use (prod | local)
  --schema-dir DIR          Use branch-built service specs without downloading
  -h, --help                 Show this help

Examples:
  $0                       # uses prod
  $0 --environment local   # uses local
  $0 --schema-dir /tmp/backend-openapi
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -e|--env|--environment)
            [ $# -ge 2 ] || { echo "Error: missing value for $1" >&2; exit 1; }
            ENVIRONMENT="$2"
            ENVIRONMENT_EXPLICIT=true
            shift 2
            ;;
        --schema-dir)
            [ $# -ge 2 ] || { echo "Error: missing value for $1" >&2; exit 1; }
            [ -n "$2" ] || { echo "Error: schema directory must not be empty." >&2; exit 1; }
            SCHEMA_SOURCE="$2"
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

if [ -n "$SCHEMA_SOURCE" ] && [ "$ENVIRONMENT_EXPLICIT" = true ]; then
    echo "Error: choose either --environment or --schema-dir." >&2
    exit 1
fi

case "$ENVIRONMENT" in
    prod)
        BASE_HOST="api.rabbitdata.ch"
        ;;
    local)
        BASE_HOST="api.rapidata.dev"
        ;;
    *)
        echo "Error: unknown environment '$ENVIRONMENT' (expected 'prod' or 'local')" >&2
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
leaderboard
flow
translation
signal
payment
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

if [ -n "$SCHEMA_SOURCE" ]; then
    [ -d "$SCHEMA_SOURCE" ] || { echo "Error: schema directory '$SCHEMA_SOURCE' does not exist." >&2; exit 1; }
    for service in $SERVICES; do
        [ -s "$SCHEMA_SOURCE/$service.openapi.json" ] || { echo "Error: missing $service.openapi.json in '$SCHEMA_SOURCE'." >&2; exit 1; }
    done

    SCHEMA_TEMP=$(mktemp -d)
    trap 'rm -rf "$SCHEMA_TEMP"' EXIT HUP INT TERM
    for spec in "$SCHEMA_SOURCE"/*.openapi.json; do
        case "$(basename "$spec")" in
            rapidata.openapi.json|rapidata.filtered.openapi.json) continue ;;
        esac
        cp "$spec" "$SCHEMA_TEMP/"
    done

    mkdir -p "$SCHEMA_DIR"
    rm -f "$SCHEMA_DIR"/*.openapi.json
    cp "$SCHEMA_TEMP"/*.openapi.json "$SCHEMA_DIR/"
else
    rm -rf "$SCHEMA_DIR"
    mkdir -p "$SCHEMA_DIR"

    for service in $SERVICES; do
        [ -z "$service" ] && continue

        url="https://${BASE_HOST}/${service}/openapi/v1.json"
        output_json="${SCHEMA_DIR}/${service}.openapi.json"

        echo "Fetching ${service} from ${url} (env=${ENVIRONMENT})..."

        download "$url" > "$output_json"
    done
fi

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
    )
  | .components.schemas |= with_entries(
      if .key == "IReferee" or .key == "IRefereeConfig" or .key == "IRefereeConfigModel"
      then .value["x-rapidata-adaptive-stopping-union"] = true
      else . end
      |
      if (.value.properties | has("ambiguityThreshold"))
         and ((.value.properties._t.enum // []) | any(
           . == "AdaptiveStoppingReferee"
           or . == "AdaptiveStoppingRefereeConfig"
           or . == "AdaptiveStoppingRefereeInfo"
         ))
      then .value["x-rapidata-adaptive-stopping-config"] = true
      else . end
      | if ((.value.properties._t.enum // []) | any(
             . == "Compare" or . == "Classify"
             or . == "ComparePayload" or . == "ClassifyPayload"
             or . == "CompareBlueprint" or . == "ClassifyBlueprint"))
        then .value["x-rapidata-answer-controls"] = true
        else . end
      | if ((.value.properties._t.enum // []) | any(
             . == "CompareResult" or . == "AttachCategoryResult"))
        then .value["x-rapidata-explicit-cs-result"] = true
        else . end
      | if (.value.properties | has("adaptiveStopping") or has("stoppingState") or has("cantSolve")
            or (has("estimate") and has("lower") and has("upper")))
        then .value["x-rapidata-preserve-field-presence"] = true
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
