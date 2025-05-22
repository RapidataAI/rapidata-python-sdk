"""
Example: Advanced Classification with Likert Scale

This example demonstrates how to:
1. Create a validation set to ensure quality responses
2. Set up a classification task with Likert scale answers
3. Process and display results

The task asks workers to rate how well images match a description
using a 5-point Likert scale (from "Not at all" to "Perfectly").
"""

from rapidata import RapidataClient, NoShuffle

# ===== VALIDATION DATA =====
# This validation set helps ensure quality responses by providing known examples
VALIDATION_IMAGE_URLS: list[str] = [
    "examples\\email-4o.png",
    "examples\\email-aurora.jpg",
    "examples\\teacher-aurora.jpg",
]

VALIDATION_CONTEXT: str = "A laptop screen with clearly readable text, addressed to the marketing team about an upcoming meeting"

VALIDATION_CONTEXTS: list[str] = [VALIDATION_CONTEXT] * len(VALIDATION_IMAGE_URLS)

# Expected correct answers for each validation image (multiple acceptable answers possible)
VALIDATION_TRUTHS: list[list[str]] = [
    ["5: Perfectly", "4: Very well"],  # First image matches very well
    ["3: Moderately"],                 # Second image matches moderately
    ["1: Not at all"]                  # Third image doesn't match at all
]

# ===== TASK CONFIGURATION =====
# Likert scale options (from lowest to highest agreement)
ANSWER_OPTIONS: list[str] = [
    "1: Not at all",
    "2: A little",
    "3: Moderately", 
    "4: Very well",
    "5: Perfectly"
]

INSTRUCTION: str = "How well does the image match the description?"

# ===== REAL TASK DATA =====
# Images to be classified
IMAGE_URLS: list[str] = [
    "https://assets.rapidata.ai/tshirt-4o.png",       # Related T-Shirt with text
    "https://assets.rapidata.ai/tshirt-aurora.jpg",   # Related T-shirt with text
    "https://assets.rapidata.ai/teamleader-aurora.jpg", # Unrelated image
]

# Description that workers will compare against the images
T_SHIRT_DESCRIPTION: str = "A t-shirt with the text 'Running on caffeine & dreams'"
CONTEXTS: list[str] = [T_SHIRT_DESCRIPTION] * len(IMAGE_URLS)


def create_validation_set(client: RapidataClient) -> str:
    """
    Create a validation set to ensure quality responses.
    
    Args:
        client: The RapidataClient instance
        
    Returns:
        The validation set ID
    """
    validation_set = client.validation.create_classification_set(
        name="Example Likert Scale Validation Set",
        instruction=INSTRUCTION,
        answer_options=ANSWER_OPTIONS,
        contexts=VALIDATION_CONTEXTS,
        datapoints=VALIDATION_IMAGE_URLS,
        truths=VALIDATION_TRUTHS
    )
    return validation_set.id


def main():
    """Run the complete example workflow"""
    # Initialize the client
    client = RapidataClient()
    
    # Step 1: Create validation set
    validation_set_id = create_validation_set(client)
    print(f"Created validation set with ID: {validation_set_id}")
    
    # Step 2: Create and run the classification order
    print("Creating and running classification order...")
    order = client.order.create_classification_order(
        name="Likert Scale Example",  
        instruction=INSTRUCTION,
        answer_options=ANSWER_OPTIONS, 
        contexts=CONTEXTS,
        datapoints=IMAGE_URLS,
        validation_set_id=validation_set_id,  # Using our validation set
        responses_per_datapoint=25,
        settings=[NoShuffle()]               # Keep Likert scale in order
    ).run()  # Start the order
    
    order.display_progress_bar()

    results = order.get_results()
    print(results)

if __name__ == "__main__":
    main()
