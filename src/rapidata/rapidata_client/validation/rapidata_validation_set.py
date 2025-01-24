class RapidataValidationSet:
    """A class for interacting with a Rapidata validation set.

    Represents a set of all the validation tasks that can be added to an order.

    When added to an order, the tasks will be selected randomly from the set.

    Attributes:
        id (str): The ID of the validation set.
        name (str): The name of the validation set.
    """

    def __init__(self, validation_set_id, name: str):
        self.id = validation_set_id
        self.name = name

    def __str__(self):
        return f"name: '{self.name}' id: {self.id}"

    def __repr__(self):
        return f"name: '{self.name}' id: {self.id}"
