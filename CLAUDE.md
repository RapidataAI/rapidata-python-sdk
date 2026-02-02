please note that there is the RapidataApiClient that wraps every api call to handel backend tracing and error handling.

The backend errors follow a specific format that you can see in the RapidataError class.

When building the docs make sure you use 'uv run --group docs mkdocs build' - otherwise check out the pyproject.toml file for the dependencies.
