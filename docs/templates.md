# Templates

We run model comparisons for our own benchmarks and for our customers, and we've found a few setups that work for the most common annotation use cases. To use a template, you only need the image or video pairs, and for alignment also the prompts. Everything else uses our field-tested setup.

| Template | Annotators answer | Use it to |
| --- | --- | --- |
| [Alignment](#alignment-does-it-follow-the-prompt) | Which image matches the description better? | check how well a model follows prompts |
| [Preference](#preference-which-one-do-people-like) | Which image do you prefer? | find the model people like more |
| [Coherence](#coherence-which-one-looks-ai-generated) | Which image is more likely AI-generated? | see which model makes fewer AI mistakes |

## Alignment: does it follow the prompt?

Annotators trained for this read the prompt, look at both images and pick the one that matches it better. Send the prompt each pair was made from.

<div class="preview-gallery">
<div data-preview-embed data-preview-lazy data-preview-campaign="cmp_1abYfMLy0hYeVt">
<div class="phone-preview">
<div class="phone-preview__notch"></div>
<div class="phone-preview__btn phone-preview__btn--left-top"></div>
<div class="phone-preview__btn phone-preview__btn--left-bot"></div>
<div class="phone-preview__btn phone-preview__btn--right"></div>
<iframe class="phone-preview__iframe" allow="clipboard-write" title="Live alignment preview"></iframe>
</div>
<div class="preview-controls">
<button type="button" data-preview-refresh aria-label="Refresh preview"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg><span>Refresh</span></button>
</div>
</div>
</div>

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

<div class="preview-gallery">
<div data-preview-embed data-preview-lazy data-preview-campaign="cmp_1abYgGt4xQgkRv">
<div class="phone-preview">
<div class="phone-preview__notch"></div>
<div class="phone-preview__btn phone-preview__btn--left-top"></div>
<div class="phone-preview__btn phone-preview__btn--left-bot"></div>
<div class="phone-preview__btn phone-preview__btn--right"></div>
<iframe class="phone-preview__iframe" allow="clipboard-write" title="Live preference preview"></iframe>
</div>
<div class="preview-controls">
<button type="button" data-preview-refresh aria-label="Refresh preview"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg><span>Refresh</span></button>
</div>
</div>
</div>

```py
job = client.job.template.run_preference(
    name="my-model vs flux-2",
    datapoints=[["mine/cat.png", "flux/cat.png"],
                ["mine/dog.png", "flux/dog.png"]],
)
results = job.get_results()
```

## Coherence: which one looks AI-generated?

Annotators trained to spot AI mistakes pick the image that looks more AI-generated.

<div class="preview-gallery">
<div data-preview-embed data-preview-lazy data-preview-campaign="cmp_1abYgZcG8wKP7l">
<div class="phone-preview">
<div class="phone-preview__notch"></div>
<div class="phone-preview__btn phone-preview__btn--left-top"></div>
<div class="phone-preview__btn phone-preview__btn--left-bot"></div>
<div class="phone-preview__btn phone-preview__btn--right"></div>
<iframe class="phone-preview__iframe" allow="clipboard-write" title="Live coherence preview"></iframe>
</div>
<div class="preview-controls">
<button type="button" data-preview-refresh aria-label="Refresh preview"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg><span>Refresh</span></button>
</div>
</div>
</div>

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
