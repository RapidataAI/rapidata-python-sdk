from rapidata import RapidataClient

DATAPOINTS = [
    "https://assets.rapidata.ai/f9d92460-a362-493c-af91-bf50046453ae.webp",
    "https://assets.rapidata.ai/9bcd8b18-e9ad-4449-84d4-b3d72e200e9c.webp",
    "https://assets.rapidata.ai/266f6446-3ca8-4c2d-b070-13558b35a4e0.webp",
    "https://assets.rapidata.ai/f787f02c-e5d0-43ca-aa6e-aea747845cf3.webp",
    "https://assets.rapidata.ai/7e518a1b-4d1c-4a86-9109-26646684cc02.webp",
    "https://assets.rapidata.ai/10af47bd-3502-4534-b917-73dba5feaf76.webp",
    "https://assets.rapidata.ai/59725ca0-1fd5-4850-a15c-4221e191e293.webp",
    "https://assets.rapidata.ai/65d3939d-c1b8-433c-b180-13dae80f0519.webp",
    "https://assets.rapidata.ai/c13b8feb-fb97-4646-8dfc-97f05d37a637.webp",
    "https://assets.rapidata.ai/586dc517-c987-4d06-8a6f-553508b86356.webp",
    "https://assets.rapidata.ai/f4884ecd-cacb-4387-ab18-3b6e7dcdf10c.webp",
    "https://assets.rapidata.ai/79076f76-a432-4ef9-9007-6d09a218417a.webp"
]

if __name__ == "__main__":
    rapi = RapidataClient()

    order = rapi.order.create_ranking_order(
        name="Example Ranking Order",
        instruction="Which rabbit looks cooler?",
        datapoints=DATAPOINTS,
        responses_per_comparison=1, #Each match is concluded after 1 response
        total_comparison_budget=50, #Make 50 comparisons, each comparison containing 2 datapoints
        random_comparisons_ratio=0.5 #First half of the comparisons are random, the second half are close matchups
    ).run()

    order.display_progress_bar()
    results = order.get_results()
    print(results)
