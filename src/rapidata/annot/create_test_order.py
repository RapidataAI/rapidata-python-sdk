from rapidata.annot.api import create_client

VAL_SET_ID = "675ac1774c3062b2f53abfeb"
client = create_client()

order = client.order.create_locate_order(
    name="My test order",
    target="whats weird",
    datapoints=["/Users/marcellschneider/Documents/rapidata/rapidata-python-sdk/src/rapidata/annot/rapidata.png"],
    responses_per_datapoint=3,
    validation_set_id=VAL_SET_ID,
)

order.run()
