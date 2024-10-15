'''
Get results from an order
'''

from examples.compare_order import new_compare_order
from examples.setup_client import setup_client
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder


def get_results(order: RapidataOrder):

    order.display_progress_bar()
    order.get_results()
    

if __name__ == "__main__":
    rapi = setup_client()
    order = new_compare_order(rapi)
    get_results(order)
