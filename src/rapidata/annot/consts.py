DEFAULT_FILE = 'rapidata.png'
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

DONE_EMOJI = '✅'
NOT_DONE_EMOJI = '❌'

DOTENV_PATH = '/Users/sneccello/Documents/rapidata/data_doctor/ranking_poc/.env'
ENV = 'test'

if ENV == 'prod':
    DOMAIN = 'rapidata.ai'
else:
    DOMAIN = 'rabbitdata.ch'

LAST_CREATED_VALIDATION_SET_KEY = 'key_last_created_validation_set'
