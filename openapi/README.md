# Regenerating the API client

Use service specs built from the backend branch when changing a contract that
has not deployed. Production specs cannot generate unreleased models.

1. Collect each service's branch-built OpenAPI document in a directory, named
   `<service>.openapi.json`. The required services are listed in
   `generate-schema.sh`; additional documents such as `workflow.openapi.json`
   are included when supplied. For a partial export, explicitly overlay the
   changed documents on a copy of the repository's unaffected service specs.
2. Run from the repository root:

   ```sh
   ./openapi/generate-schema.sh --schema-dir /tmp/backend-openapi
   ```

3. Record the backend commit and artifact source in the PR. Review both the
   service specs and generated models, then run the repository checks.

The script validates that every required service document is present before
replacing the checked-in specs. It ignores old merged/filtered documents,
joins service specs, filters deprecated surfaces, and uses the generator version
in `openapitools.json` with the repository's config and mustache templates.
The schema directory can be `openapi/schemas` itself. npm tools can still require
network access; `--schema-dir` only disables service-spec downloads.

Use `--environment prod` or `--environment local` to download deployed specs.

The canonical adaptive-referee and explicit answer-control adapters defer to
native generated models once the branch specs declare their fields. Their
narrow deserialization hooks live in the matching mustache templates; do not
add guessed fields to generated models while awaiting an artifact.
