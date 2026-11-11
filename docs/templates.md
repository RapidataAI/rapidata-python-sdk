# Templates

Run a Rapidata-maintained setup on your own pairs in one call. Rapidata picks the question and the audience; every pair gets 11 votes.

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

| Method | You send | Question annotators see |
| --- | --- | --- |
| `run_alignment` | pairs + prompts | "Which image matches the description better?" |
| `run_preference` | pairs | "Which image do you prefer?" |
| `run_coherence` | pairs | "Which image is more likely AI-generated?" |

Videos (`.mp4` and `.gif`) get the same questions with "video". **One media type per call:** send images and videos as two calls.

!!! note "Coherence: the winner looks more AI-generated"
    Annotators pick the file that looks more AI-generated, so the better model wins fewer pairs.

**Name the sides (optional).** `a_b_names=["my-model", "flux-2"]` names the first and second file of every pair; the results show these names instead of A and B.

!!! tip "Keep prompts under 200 characters for better results"
    The SDK warns above 200. Annotators see at most 400: longer prompts are shortened to the part relevant to the question (LLM, cached, billed like `client.context`), and the SDK logs how many.

Each call uses the template's latest version and creates a job definition in your organization.

## What one call sends

1. `GET /job/definition/{definitionId}/revision` reads the template's question and votes. If that revision isn't completed yet, the call reads the latest completed one, which `/run` uses.
2. `POST /dataset` creates a dataset in your organization. For `run_alignment` it carries `contextShortening` with the template's question.
3. The files upload, then one `POST /dataset/{datasetId}/datapoint` per pair. If a pair fails, the call raises a `FailedUploadException` naming the dataset, and no job starts.
4. One `POST /job/definition/{definitionId}/run` starts the job. It is never retried after it may have reached Rapidata: if no answer or a 500 comes back, the call raises a `RapidataError`. A job may have started, so look for it with `client.job.find_jobs(name)` before calling again. Only a job with exactly this name, created after the call began, can be it; the error prints that time.

Template runs don't read `rapidata_config.upload.contextShortening` (only prompts over 400 characters are shortened), `failureTolerance` (any failed pair stops the run) or `checkForExplicitContent` (`POST /job/definition/{definitionId}/run` decides the content check from your organization, and the SDK warns when it is `True`). A job can wait for a manual content review before it starts: always for videos, and for images when the dataset is large or something is flagged. `job.get_results()` then raises with the reason instead of blocking.
