# Effective Instruction Design for Rapidata Tasks

When creating tasks for human labelers using the Rapidata API, phrasing your instructions well can significantly improve quality and consistency of the responses you receive. This guide provides best practices for designing effective instructions for your Rapidata tasks.

## Time Constraints

Each labeler session has a limited time window of 25 seconds to complete all tasks. With this in mind:

- **Be concise**: Keep instructions as brief as possible while maintaining clarity
- **Use simple language**: Avoid complex terminology or jargon
- **Focus on the essentials**: Include only what is needed to complete the task

## Language Clarity

Since Rapidata tasks are presented to a diverse audience of labelers:

- **Use accessible language**: The average person should be able to understand your instructions clearly
- **Avoid ambiguity**: Ensure there's only one way to interpret your instructions
- **Be specific**: Clearly state what you're looking for in the responses

## Question Framing

The way you frame questions significantly impacts response quality:

### Use Positive Framing
Frame questions in the positive rather than negative. Positive questions are easier to process quickly.

**Better:**
```
"Which image looks more realistic?"
```

**Avoid:**
```
"Which image looks less AI-generated?"
```

### Limit Decision Criteria
Don't overload labelers with multiple criteria in a single question.

**Better:**
```
"What animal is in the image? - rabbit/dog/cat/other"
```

**Avoid:**
```
"Does this image contain a rabbit, a dog, or a cat? - yes/no"
```

### Use Clear Response Options
Provide distinct, non-overlapping response options.

**Better:**
```
"Rate the image quality: poor/acceptable/excellent"
```

**Avoid:**
```
"Rate the image quality: bad/not good/fine/good/great"
```

## Example Implementation

When creating a Rapidata job, implement these principles as follows:

```python
from rapidata import RapidataClient

client = RapidataClient()

# Create audience with clear qualification example
audience = client.audience.create_audience(name="Image Coherence Audience")
audience.add_compare_example(
    instruction="Which image has more glitches and is more likely to be AI generated?",
    datapoint=[
        "https://assets.rapidata.ai/good_ai_generated_image.png",
        "https://assets.rapidata.ai/bad_ai_generated_image.png"
    ],
    truth="https://assets.rapidata.ai/bad_ai_generated_image.png"
)

# Create job definition with clear instruction
job_definition = client.job.create_compare_job_definition(
    name="Image Coherence Comparison",
    instruction="Which image has more glitches and is more likely to be AI generated?",
    datapoints=[
        ["https://assets.rapidata.ai/flux-1.1-pro/33_2.jpg",
         "https://assets.rapidata.ai/stable-diffusion-3/33_0.jpg"]
    ]
)

# Preview before running
job_definition.preview()
```

## Common Task Types and Recommended Instructions

### Image Comparison Tasks

```python
# Comparing image preference
instruction="Which image do you prefer?"

# Comparing prompt adherence
instruction="Which image matches the description better?"

# Comparing image coherence
instruction="Which image has more glitches and is more likely to be AI generated?"

# Comparing two texts
instruction="Which of these sentences makes more sense?"
```

### Classification Tasks

```python
# Simple classification
instruction="What object is in the image?"

# Likert classification (add NoShuffle setting)
instruction="How well does the video match the description?"
answer_options=["1: Perfectly",
                "2: Very well",
                "3: Moderately",
                "4: A little",
                "5: Not at all"]
```

## Monitoring and Iteration

After assigning your job to an audience, monitor the initial responses to see if labelers are understanding your instructions as intended.

You can preview how users will see the task by calling the `.preview()` method on the job definition:
```python
job_definition.preview()
```

If you see that labelers are giving inconsistent or incorrect answers:

1. Review and simplify your instructions
2. Update your audience's qualification examples if needed
3. Create a new job definition with the improved settings

This helps ensure you get high quality results from labelers.

For more information on creating and managing jobs, refer to the [Rapidata API documentation](starting_page.md) and [Understanding the Results](understanding_the_results.md) guide.
