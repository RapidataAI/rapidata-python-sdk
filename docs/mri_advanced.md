# Model Ranking Insights Advanced

## Overview

To unlock the full potential of Model Ranking Insights (MRI), you can use the advanced features. These include sophisticated configuration options for benchmarks, leaderboards, and evaluation settings that give you fine-grained control over your model evaluation process.

## Benchmark Configuration

### Using Identifiers

In the MRI quickstart we used the prompts to identify the media and create the appropriate matchups. However, more generally you might not have an exact 1-to-1 relationship between prompts and media (e.g., you may have different settings or inputs for the same prompt - for example input images for image-to-video models. More about this below). To handle this case, we allow you to supply your own identifiers, which will then be used when creating the matchups.

```python
# Example 1: Explicit identifiers
benchmark = client.mri.create_new_benchmark(
    name="Preference Benchmark",
    identifiers=["scene_1", "scene_2", "scene_3"],
    prompts=[
        "A serene mountain landscape at sunset",
        "A futuristic city with flying cars",
        "A portrait of a wise old wizard"
    ],
    prompt_assets=[
        "https://assets.rapidata.ai/mountain_sunset.png",
        "https://assets.rapidata.ai/futuristic_city.png", 
        "https://assets.rapidata.ai/wizard_portrait.png"
    ]
)

# Example 2: Identifiers used for the same prompts but different seeding
benchmark = client.mri.create_new_benchmark(
    name="Preference Benchmark",
    identifiers=["seed_1", "seed_2", "seed_3"],
    prompts=["prompt_1", "prompt_1", "prompt_1"],
    prompt_assets=["https://example.com/asset1.jpg", "https://example.com/asset1.jpg", "https://example.com/asset1.jpg"]
)

# Example 3: Using only prompt assets
benchmark = client.mri.create_new_benchmark(
    name="Preference Benchmark",
    identifiers=["image_1", "image_2", "image_3"],   
    prompt_assets=["https://example.com/asset1.jpg", "https://example.com/asset2.jpg", "https://example.com/asset3.jpg"]
)
```

> **Note:** Media assets are images, videos, or audio files that provide visual or auditory context for your evaluation prompts. For example when evaluating image to video models.

### Tagging System

Tags provide metadata for filtering and organizing benchmark results without showing them to evaluators. These tags can also be set and used in the frontend. To view the frontend, you can use the `view` method of the benchmark or leaderboard.

```python
# Tags for filtering leaderboard results
tags = [
    ["landscape", "outdoor", "beach"],
    ["landscape", "outdoor", "mountain"],
    ["outdoor", "city"],
    ["indoor", "vehicle"]
]

benchmark = client.mri.create_new_benchmark(
    name="Tagged Benchmark",
    identifiers=["scene_1", "scene_2", "scene_3", "scene_4"],
    prompts=["A sunny beach", "A mountain landscape", "A city skyline", "A car in a garage"],
    tags=tags
)

# Filter leaderboard results by tags
standings = leaderboard.get_standings(tags=["landscape", "outdoor"])
```

### Adding prompts and assets after benchmark creation

If you have already created a benchmark and want to add new prompts and assets after the fact. Note however that these will only take effect for new models.

```python
# Adding individual prompts with assets
benchmark.add_prompt(
    identifier="new_style",
    prompt="Generate artwork in this new style",
    prompt_asset="https://assets.rapidata.ai/new_style_ref.jpg",
    tags=["abstract", "modern"]
)
```

## Leaderboard Configuration

### Inverse Ranking

For evaluation questions where lower scores are better (e.g., "Which image is worse?"), use inverse ranking.

```python
leaderboard = benchmark.create_leaderboard(
    name="Quality Assessment",
    instruction="Which image has lower quality?",
    inverse_ranking=True,  # Lower scores = better performance
    show_prompt=True,
    show_prompt_asset=True
)
```

### Level of Detail

Controls the number of comparisons performed, affecting accuracy vs. speed.

```python
# Different detail levels
leaderboard_fast = benchmark.create_leaderboard(
    name="Quick Evaluation", 
    instruction="Which image do you prefer?",
    level_of_detail="low"      # Fewer comparisons, faster results
)

leaderboard_precise = benchmark.create_leaderboard(
    name="Precise Evaluation",
    instruction="Which image do you prefer?", 
    level_of_detail="very high"  # More comparisons, higher accuracy
)
```

### Prompt and Asset Display

Control what evaluators see during comparison.

```python
leaderboard = benchmark.create_leaderboard(
    name="Context-Aware Evaluation",
    instruction="Which generated image better matches the prompt?",
    show_prompt=True,           # Show the original text prompt
    show_prompt_asset=True,     # Show reference images/videos
    level_of_detail="medium"
)
```

## Participant Management

### Listing Participants

You can list all participants in a benchmark using the `participants` property:

```python
for participant in benchmark.participants:
    print(f"{participant.name} - {participant.status}")
```

### Submitting Participants

When using `add_model`, participants are created in the `CREATED` state and are not yet submitted for evaluation. You can submit them individually or in bulk:

```python
# Submit a single participant
participant = benchmark.add_model(
    name="ModelA",
    media=["https://example.com/img1.png"],
    identifiers=["scene_1"]
)
participant.run()

# Or add multiple models and submit them all at once
benchmark.add_model(name="ModelB", media=["https://example.com/img2.png"], identifiers=["scene_1"])
benchmark.add_model(name="ModelC", media=["https://example.com/img3.png"], identifiers=["scene_1"])
benchmark.run()  # Submits all participants in CREATED state
```

## References
- [RapidataBenchmarkManager](/reference/rapidata/rapidata_client/benchmark/rapidata_benchmark_manager/)
- [RapidataBenchmark](/reference/rapidata/rapidata_client/benchmark/rapidata_benchmark/)
- [RapidataLeaderboard](/reference/rapidata/rapidata_client/benchmark/leaderboard/rapidata_leaderboard/)
- [BenchmarkParticipant](/reference/rapidata/rapidata_client/benchmark/participant/participant/)

