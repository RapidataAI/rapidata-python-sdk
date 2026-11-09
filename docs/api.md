
```mermaid
classDiagram
    class RapidataClient {
        +RapidataJobManager job
        +RapidataAudienceManager audience
        +RapidataAssetManager asset
        +ValidationSetManager validation
        +RapidataFlowManager flow
        +RapidataBenchmarkManager mri
        +RapidataSignalManager signals
        +RapidataBillingManager billing
    }

    class RapidataJobManager {
        +create_****_job_definition()
        +get_job_definition_by_id()
        +find_job_definitions()
        +get_job_by_id()
        +find_jobs()
    }

    class RapidataAudienceManager {
        +create_audience()
        +get_audience_by_id()
        +find_audiences()
    }

    class RapidataAudience {
        +assign_job()
        +filter()
        +add_****_example()
        +start_recruiting()
    }

    class ValidationSetManager {
        +RapidsManager rapid
        +create_****_set()
        +get_validation_set_by_id()
        +find_validation_sets()
    }

    class RapidsManager {
        +****_rapid()
    }

    RapidataClient --* RapidataJobManager
    RapidataClient --* RapidataAudienceManager
    RapidataClient --* ValidationSetManager
    RapidataAudienceManager --> RapidataAudience
    ValidationSetManager --* RapidsManager

    link RapidataClient "../reference/rapidata/rapidata_client/rapidata_client/" ""
    link RapidataJobManager "../reference/rapidata/rapidata_client/job/rapidata_job_manager/" ""
    link RapidataAudienceManager "../reference/rapidata/rapidata_client/audience/rapidata_audience_manager/" ""
    link RapidataAudience "../reference/rapidata/rapidata_client/audience/rapidata_audience/" ""
    link ValidationSetManager "../reference/rapidata/rapidata_client/validation/validation_set_manager/" ""
    link RapidsManager "../reference/rapidata/rapidata_client/validation/rapids/rapids_manager/" ""

```

# Rapidata API

The Rapidata API builds on the [RapidataClient](reference/rapidata/rapidata_client/rapidata_client.md) class. This class is the entry point for all operations. You collect labels by creating a **job definition** with `job`, then assigning it to an **audience** — the job runs against that audience's annotators and produces results.

### Job related classes

[RapidataJobManager](reference/rapidata/rapidata_client/job/rapidata_job_manager.md) - accessible through the RapidataClient(rapi) under rapi.job. Creates job definitions and looks up jobs.

[RapidataAudienceManager](reference/rapidata/rapidata_client/audience/rapidata_audience_manager.md) - accessible through the RapidataClient(rapi) under rapi.audience. Creates and looks up audiences.

[RapidataAssetManager](reference/rapidata/rapidata_client/asset/rapidata_asset_manager.md) - accessible through the RapidataClient(rapi) under rapi.asset. Uploads media once and returns an `UploadedAsset` to reuse in job definitions.

[RapidataAudience](reference/rapidata/rapidata_client/audience/rapidata_audience.md) - returned by rapi.audience. Runs a job definition with `assign_job()` and narrows the audience with `filter()`.

Filters (`CountryFilter`, `LanguageFilter`, ...), settings (`NoShuffleSetting`, `RapidataSettings`, ...) and selections (`LabelingSelection`, ...) are imported directly from `rapidata`.


### Validation related classes

[ValidationSetManager](reference/rapidata/rapidata_client/validation/validation_set_manager.md) - accessible through the RapidataClient(rapi) under rapi.validation

[RapidsManager](reference/rapidata/rapidata_client/validation/rapids/rapids_manager.md) - accessible through the RapidataClient(rapi) under rapi.validation.rapid. Used to create specific rapids to be added to a validation set.
