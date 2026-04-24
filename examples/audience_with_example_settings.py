"""
Build a custom audience whose qualification examples are rendered with the
same feature flags (settings) as the real job.

Audience qualification examples used to always render with default settings,
which meant they could look different from the actual task the labeler was
being qualified for. By passing ``settings=[...]`` to ``add_*_example``, the
example is rendered with the same feature flags as the job — so the labeler
qualifies on the UI they will actually see.

Typical use cases:
- Likert / ordered scales: pass ``NoShuffleSetting()`` so the options stay in
  order on both the example and the job.
- Compare tasks with an "Unsure" button: pass ``AllowNeitherBothSetting()``
  so the example matches the job UI.
- Panoramic / 360 compare tasks: pass ``ComparePanoramaSetting()`` so the
  example renders with the same viewer as the job.
"""

from rapidata import (
    AllowNeitherBothSetting,
    NoShuffleSetting,
    RapidataClient,
)

# ===== Ordered Likert scale used by both the example and the job =====
LIKERT_OPTIONS: list[str] = [
    "1: Not at all",
    "2: A little",
    "3: Moderately",
    "4: Very well",
    "5: Perfectly",
]

QUALIFICATION_IMAGE = "https://assets.rapidata.ai/email-4o.png"
QUALIFICATION_CONTEXT = (
    "A laptop screen with clearly readable text, addressed to the marketing "
    "team about an upcoming meeting"
)
QUALIFICATION_TRUTH = ["5: Perfectly", "4: Very well"]

# ===== Compare task used to show AllowNeitherBothSetting on the example =====
LOGO_A = "https://assets.rapidata.ai/rapidata_logo.png"
LOGO_B = "https://assets.rapidata.ai/rapidata_concept_logo.jpg"


def main() -> None:
    client = RapidataClient()

    audience = client.audience.create_audience(
        name="Custom Audience With Example Settings",
    )

    # --- Classification example: keep the Likert scale ordering ---
    # Without NoShuffleSetting, the options would be shuffled when shown to
    # the labeler, making an ordered scale look arbitrary.
    audience.add_classification_example(
        instruction="How well does the image match the description?",
        answer_options=LIKERT_OPTIONS,
        datapoint=QUALIFICATION_IMAGE,
        truth=QUALIFICATION_TRUTH,
        context=QUALIFICATION_CONTEXT,
        settings=[NoShuffleSetting()],
    )

    # --- Compare example: expose the "Unsure" button ---
    # Use the same setting you plan to use on the real job so the labeler
    # qualifies on the exact UI they will later see.
    audience.add_compare_example(
        instruction="Which logo is the actual Rapidata logo?",
        datapoint=[LOGO_A, LOGO_B],
        truth=LOGO_A,
        settings=[AllowNeitherBothSetting()],
    )

    print(f"Audience created: {audience.id}")


if __name__ == "__main__":
    main()
