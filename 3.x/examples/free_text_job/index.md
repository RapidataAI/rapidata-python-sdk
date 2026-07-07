# Free Text Job Example

To learn about the basics of creating a job, please refer to the [quickstart guide](../quickstart.md).

In a free text job, labelers answer your instruction with free-form text. Let's assume you want to build a new LLM chatbot and want to know what people might ask it — a free text job gathers those questions directly from real people.

A free text job typically takes longer to complete than other job types, as typing an answer is more involved for the labeler than tapping one.

```python
from rapidata import RapidataClient

client = RapidataClient()

audience = client.audience.get_audience_by_id("global") # (1)!

job_definition = client.job.create_free_text_job_definition(
    name="Example prompt generation",
    instruction="What would you like to ask an AI? Please spell out the question", # (2)!
    datapoints=["https://assets.rapidata.ai/ai_question.png"],
)

job = audience.assign_job(job_definition)
job.view()
job.display_progress_bar()
results = job.get_results()
print(results)
```

1. The global audience (id `global`) already has labelers ready to work, so the job starts collecting responses immediately. You can assign a free text job to any audience — browse them in the [Rapidata Dashboard](https://app.rapidata.ai/audiences).
2. The instruction is shown alongside each datapoint. Each response is the text the labeler typed.

!!! note
    Free text answers can't be graded against a ground truth, so audiences can't be trained with free text qualification examples — use examples of another job type (e.g. classification) if you want a custom audience, see [Custom Audiences](../audiences.md).
