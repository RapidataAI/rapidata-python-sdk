# Development

This page describes the set-up of a development environment. The project uses a generated client based on Rapidata's OpenApi spec located at https://docs.rabbitdata.ch/.

## OpenAPI Client generation

### Download Specs

The specs used for generation are tracked at `openapi/output.swagger.json`. The following steps are only necessary to synchronize the generated client with the latest spec.

This requires [openapi-merge-cli](https://www.npmjs.com/package/openapi-merge-cli) installed globally

```
npm i -g openapi-merge-cli
```

Download and merge the specification from https://docs.rabbitdata.ch/:

```
./openapi/download-and-merge-spec.sh
```

This should have produced/updated the file at `openapi/output.swagger.json`

### Generate OpenAPI Client

This requires [openapi-generator](https://github.com/OpenAPITools/openapi-generator) installed

```
brew install openapi-generator
```

Execute the generation command by running

```
./openapi/generate.sh
```

## Python Package Management

This repository is using [poetry](https://python-poetry.org/) to manage dependencies.

To set-up a python environment using conda, run:
```
conda create -n rapi-client
```

Then let poetry install all dependencies:

```
poetry install
```

This will also install the OpenAPI Client located at `openapi/openapi-client` as a development dependency. So any new generation does not require a re-install.

