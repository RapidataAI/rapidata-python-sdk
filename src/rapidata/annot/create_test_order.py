from rapidata.annot.api import create_client

VAL_SET_ID = "675ae59ed53e277218a8b638"
client = create_client()

order = client.order.create_locate_order(
    name="My test order",
    target="whats weird",
    datapoints=["/Users/marcellschneider/Documents/rapidata/rapidata-python-sdk/src/rapidata/annot/rapidata.png"],
    responses_per_datapoint=3,
    validation_set_id=VAL_SET_ID,
)

client.validation.create_rapid_set()
order.run()
