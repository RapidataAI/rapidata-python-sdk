
```mermaid
classDiagram
    class RapidataClient {
        +RapidataOrderManager order
        +RapidataValidationManager validation
    }
    
    class RapidataOrderManager {
        +RapidataFilters filter
        +RapidataSettings settings
        +RapidataSelections selections
        +create_****_order()
        +get_order_by_id()
        +find_orders()
    }
    
    class RapidataValidationManager {
        +RapidsManager rapid
        +create_****_set()
        +get_validation_set_by_id()
        +find_validation_sets()
    }
    
    class RapidataFilters {
        +user_score
        +age
        +campaign
        +contry
        +gender
        +language
    }
    
    class RapidataSettings {
        +alert_on_fast_response
        +translation_behaviour
        +free_text_minimum_characters
        +no_shuffle
        +play_video_until_the_end
    }
    
    class RapidataSelections {
        +demographic
        +labeling
        +validation
        +conditionl_validation
        +capped
    }
    
    class RapidsManager {
        +****_rapid()
    }

    RapidataClient --* RapidataOrderManager
    RapidataClient --* RapidataValidationManager
    RapidataOrderManager --* RapidataFilters
    RapidataOrderManager --* RapidataSettings
    RapidataOrderManager --* RapidataSelections
    RapidataValidationManager --* RapidsManager

    link RapidataClient "../reference/rapidata/rapidata_client/rapidata_client/" ""
    link RapidataOrderManager "../reference/rapidata/rapidata_client/order/rapidata_order_manager/" ""
    link RapidataValidationManager "../reference/rapidata/rapidata_client/validation/validation_set_manager/" ""
    link RapidataFilters "../reference/rapidata/rapidata_client/filter/rapidata_filters/" ""
    link RapidataSettings "../reference/rapidata/rapidata_client/settings/rapidata_settings/" ""
    link RapidataSelections "../reference/rapidata/rapidata_client/selection/rapidata_selections/" ""
    link RapidsManager "../reference/rapidata/rapidata_client/validation/rapids/rapids_manager/" ""

```

# Rapidata API

The Rapidata API builds on the [RapidataClient](reference/rapidata/rapidata_client/rapidata_client.md) class. This class is the entry point for all operations. The RapidataClient class has two main properties, order and validation, which are used to manage orders and validation sets respectively.

### Order related classes

[RapidataOrderManger](reference/rapidata/rapidata_client/order/rapidata_order_manager.md) - accessible through the RapidataClient(rapi) under rapi.order

[RapidataFilters](reference/rapidata/rapidata_client/filter/rapidata_filters.md) - accessible through the RapidataClient(rapi) under rapi.order

[RapidataSettings](reference/rapidata/rapidata_client/settings/rapidata_settings.md) - accessible through the RapidataClient(rapi) under rapi.order

[RapidataSelections](reference/rapidata/rapidata_client/selection/rapidata_selections.md) - accessible through the RapidataClient(rapi) under rapi.order


### Validation related classes

[RapidataValidationManger](reference/rapidata/rapidata_client/validation/validation_set_manager.md) - accessible through the RapidataClient(rapi) under rapi.validation

[RapidsManager](reference/rapidata/rapidata_client/validation/rapids/rapids_manager.md) - accessible through the RapidataClient(rapi) under rapi.validation
