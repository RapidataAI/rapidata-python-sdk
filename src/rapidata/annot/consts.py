DEFAULT_FILE = "/Users/marcellschneider/Documents/rapidata/rapidata-python-sdk/src/rapidata/annot/rapidata.png"
DOTENV_PATH = '/Users/marcellschneider/Documents/rapidata/rapidata-python-sdk/src/rapidata/annot/.env'

METADATA_COLUMNS = [
    'image',
    'filename',
    'left',
    'top',
    'width',
    'height'
]

MAX_ANNOTATION_PER_RAPID = 1
CANVAS_WIDTH = 600

PRODUCTION_ENVIRONMENT = 'PRODUCTION'
TEST_ENVIRONMENT = "TEST"

LAST_CREATED_VALIDATION_SET_KEY = 'key_last_created_validation_set'
CREATED_RAPIDS_COUNTER_KEY = "key_created_rapid_count"
CHOSEN_ENVIRONMENT_KEY = "key_chosen_environment"

ARTIFACT_PROMPT = 'Tap the area where the artificially generated image has a mistake'
ALIGNMENT_PROMPT = "Tap the area where the image does not match the description"
LANGUAGES = ['hu']

#ALIGNMENT_VALIDATION_SET = "676153ac1276f33129ab4a66" if ENV == "test" else None
#ARTIFACT_VALIDATION_SET = "676152341276f33129ab4a65" if ENV == "test" else None
