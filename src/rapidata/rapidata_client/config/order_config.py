from pydantic import BaseModel, Field


class OrderConfig(BaseModel):
    """
    Holds the configuration for the order process.

    Attributes:
        minOrderDatapointsForValidation (int): The minimum number of datapoints required so that an automatic validationset gets created if no recommended was found. Defaults to 50.
        autoValidationSetSize (int): The maximum size of the auto-generated validation set. Defaults to 20.
    """

    autoValidationSetCreation: bool = Field(default=True)
    minOrderDatapointsForValidation: int = Field(default=50)
    autoValidationSetSize: int = Field(default=20)
