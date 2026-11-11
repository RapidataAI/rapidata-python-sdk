# Templates

We run model comparisons for our own benchmarks and for our customers, and a few setups keep giving teams answers they can act on. Templates are the three most useful ones, ready to run. You bring pairs of images or videos, one from each model. We bring the question, the right annotators and 11 votes per pair.

| Template | Annotators answer | Use it to |
| --- | --- | --- |
| [Alignment](#alignment-does-it-follow-the-prompt) | Which image matches the description better? | check how well a model follows prompts |
| [Preference](#preference-which-one-do-people-like) | Which image do you prefer? | find the model people like more |
| [Coherence](#coherence-which-one-looks-ai-generated) | Which image is more likely AI-generated? | catch glitches like extra fingers or warped text |

## Alignment: does it follow the prompt?

Annotators trained for this read the prompt, look at both images and pick the one that matches it better. Send the prompt each pair was made from.

```py
from rapidata import RapidataClient

client = RapidataClient()

job = client.job.template.run_alignment(
    name="my-model vs flux-2",
    datapoints=[["mine/cat.png", "flux/cat.png"],
                ["mine/dog.png", "flux/dog.png"]],
    contexts=["A cat wearing a red scarf",
              "A dog surfing at sunset"],
)
results = job.get_results()
```

## Preference: which one do people like?

A broad crowd picks the image they like more. No prompt needed.

```py
job = client.job.template.run_preference(
    name="my-model vs flux-2",
    datapoints=[["mine/cat.png", "flux/cat.png"],
                ["mine/dog.png", "flux/dog.png"]],
)
results = job.get_results()
```

## Coherence: which one looks AI-generated?

Annotators trained to spot AI mistakes, like extra fingers, warped text or melting objects, pick the image that looks more AI-generated.

```py
job = client.job.template.run_coherence(
    name="my-model vs flux-2",
    datapoints=[["mine/cat.png", "flux/cat.png"],
                ["mine/dog.png", "flux/dog.png"]],
)
results = job.get_results()
```

!!! note "In Coherence, fewer wins is better"
    The winning side is the one that looks more AI-generated, so the better model wins fewer pairs.

## See who won

Name the two sides, and the results count each side's wins:

```py
job = client.job.template.run_preference(
    name="my-model vs flux-2",
    datapoints=[["mine/cat.png", "flux/cat.png"],
                ["mine/dog.png", "flux/dog.png"]],
    a_b_names=["my-model", "flux-2"],
)
job.get_results()["summary"]
# {'my-model_wins_total': 2, 'flux-2_wins_total': 0}
```

The results also hold all 11 votes for every pair.

## Good to know

- **Videos work the same way.** Send `.mp4` files (GIFs count as videos), and the question says "video". Send images and videos in separate calls.
- **Keep prompts short.** Under 200 characters reads best on a phone. We shorten prompts over 400 characters to what the question needs.
- **We maintain the templates.** Every call uses the latest version.
