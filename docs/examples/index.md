# Examples

Every job type the SDK can create, side by side. Pick a tab to see the call that defines it and try the task yourself in the live preview below — it's the same interface the labelers get.

Assigning a definition to an audience, tracking progress, and reading results works the same for every type, so the tabs show only the part that differs. The [Quick Start](../quickstart.md) covers the rest, and each tab links to its full example.

=== "Classification"

    Labelers pick one of your answer options. Use it for categories, quality ratings, or Likert scales.

    ```python
    job_definition = client.job.create_classification_job_definition(
        name="Likert Scale Example",
        instruction="How well does the image match the description?",
        answer_options=["1: Not at all", "2: A little", "3: Moderately", "4: Very well", "5: Perfectly"],
        contexts=CONTEXTS,
        datapoints=IMAGE_URLS,
        settings=[NoShuffleSetting()],
    )
    ```

    [:octicons-arrow-right-24: Full classification example](classify_job.md)

=== "Comparison"

    Labelers see two datapoints and pick one. Works with images, video, audio, and text.

    ```python
    job_definition = client.job.create_compare_job_definition(
        name="Example Image Prompt Alignment Job",
        instruction="Which image follows the prompt more accurately?",
        datapoints=IMAGE_PAIRS,
        contexts=PROMPTS,
    )
    ```

    [:octicons-arrow-right-24: Full comparison example](compare_job.md)

=== "Locate"

    Labelers tap the points in an image that match your instruction — visual artifacts, objects, anything you can describe.

    ```python
    job_definition = client.job.create_locate_job_definition(
        name="Artifact Detection Example",
        instruction="Tap on any visual glitches or errors in the image.",
        datapoints=IMAGE_URLS,
    )
    ```

    [:octicons-arrow-right-24: Full locate example](locate_job.md)

=== "Draw"

    Labelers color in the regions that match your instruction, which gives you localization data rather than single points.

    ```python
    job_definition = client.job.create_draw_job_definition(
        name="Blue Books Example",
        instruction="Color in all the blue books",
        datapoints=IMAGE_URLS,
    )
    ```

    [:octicons-arrow-right-24: Full draw example](draw_job.md)

=== "Select Words"

    Labelers are shown a datapoint together with a sentence and select the words that match your instruction.

    ```python
    job_definition = client.job.create_select_words_job_definition(
        name="Image-Text Alignment Example",
        instruction="The image is based on the text below. Select mistakes, i.e., words that are not aligned with the image.",
        datapoints=IMAGE_URLS,
        sentences=PROMPTS_WITH_NO_MISTAKES,
    )
    ```

    [:octicons-arrow-right-24: Full select words example](select_words_job.md)

=== "Free Text"

    Labelers type their own answer. Use it when the response space is open-ended and you can't enumerate the options.

    ```python
    job_definition = client.job.create_free_text_job_definition(
        name="Example prompt generation",
        instruction="What would you like to ask an AI? Please spell out the question",
        datapoints=["https://assets.rapidata.ai/ai_question.png"],
    )
    ```

    [:octicons-arrow-right-24: Full free text example](free_text_job.md)

=== "Ranking"

    A set of datapoints is ordered through pairwise matchups, with an Elo rating updated after each one. Labelers only ever see two at a time.

    ```python
    job_definition = client.job.create_ranking_job_definition(
        name="Example Ranking Job",
        instruction="Which rabbit looks cooler?",
        datapoints=[DATAPOINTS],
        comparison_budget_per_ranking=50,
    )
    ```

    [:octicons-arrow-right-24: Full ranking example](ranking_job.md)

<div data-preview-embed
     data-preview-map='{"Classification":"cmp_1SCZysSRxUHIJ5","Comparison":"cmp_1SCZyXpfpHFbmd","Locate":"cmp_1SCZhvwq8dKVfQ","Draw":"cmp_1SCZiFks5AUIMi","Select Words":"cmp_1SCZiZoHgeFf8t","Free Text":"cmp_1SCZitM8vyAoTC","Ranking":"cmp_1SCZzu6YH6ncAs"}'>
  <div class="phone-preview">
    <div class="phone-preview__notch"></div>
    <div class="phone-preview__btn phone-preview__btn--left-top"></div>
    <div class="phone-preview__btn phone-preview__btn--left-bot"></div>
    <div class="phone-preview__btn phone-preview__btn--right"></div>
    <iframe class="phone-preview__iframe"
            src="https://rapids.rapidata.ai/preview/campaign?id=cmp_1SCZysSRxUHIJ5&language=en&userSegment=0&refreshCount=0"
            allow="clipboard-write"
            title="Live Rapidata campaign preview"></iframe>
  </div>
  <div class="preview-controls">
    <button type="button" data-preview-refresh aria-label="Refresh preview">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
      <span>Refresh</span>
    </button>
  </div>
</div>

---

Not seeing what you need? [Model Ranking](../mri.md) benchmarks AI models on an ongoing leaderboard, and [Ranking Flows](../flows.md) keeps a ranking up to date without full job setup.
