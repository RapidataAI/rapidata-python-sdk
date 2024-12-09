import os
DEFAULT_FILE = 'rapidata.png'
TEMP_FILE_DIR = str(os.path.join(os.getcwd(), 'rapidata_tmp'))
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

