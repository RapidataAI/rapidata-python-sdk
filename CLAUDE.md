This Project is a Python SDK for the Rapidata API.

It is built around the RapidataClient class which is the main entry point for interacting with the Rapidata API.

As a customer you can use the RapidataClient class to access the following:
- OrderCreation
- ValidationSetCreation
- AudienceCreation
- JobDefinitionCreation
- BenchmarkCreation / MRI Creation

The whole authentication and backend communication is handled by the OpenAPIService class. It works in combination with the AUTO GENERATED API CLIENT that is used to make the actual API calls.

Note that if there are any changes that have to be made in those files you MUST also update the mustache files under openapi/templates.

please note that there is the RapidataApiClient that wraps every api call to handel backend tracing and error handling.

The backend errors follow a specific format that you can see in the RapidataError class.

When building the docs make sure you use 'uv run --group docs mkdocs build' - otherwise check out the pyproject.toml file for the dependencies.

When writing documentation, make sure to keep focused, easy to understand, and not repeat information. it should highlight the capabilities while not overexaggerating or falling into hyperbole.
when doing type annotations use the "from __future__ import annotations" statement and TYPE_CHECKING to check the types - that way you can eliminate the quotation marks around the types.
