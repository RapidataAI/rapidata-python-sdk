import dotenv
from PIL import Image
import streamlit as st
from streamlit_drawable_canvas import st_canvas
import sys
from pathlib import Path


sys.path.append(str(Path(__file__).parent.parent.parent.resolve()))

from consts import LAST_CREATED_VALIDATION_SET_KEY, DEFAULT_FILE, CREATED_RAPIDS_COUNTER_KEY, DOTENV_PATH, \
    PRODUCTION_ENVIRONMENT, TEST_ENVIRONMENT, CHOSEN_ENVIRONMENT_KEY
from models import ValidationRapid, ValidationRapidCollection, RapidTypes
from rapidata.annot.api import get_validation_rapids, get_validation_set_url, validation_set_from_rapids
from utils import resize_image

@st.cache_resource
def get_collection():
    return ValidationRapidCollection(
        starter_rapid=ValidationRapid(
            name=DEFAULT_FILE,
            image=Image.open(DEFAULT_FILE),
            rapid_id=get_next_rapid_id()
        )
    )

def display_rapid_metadata(rapid: ValidationRapid):
    cols = st.columns(5, vertical_alignment='center')
    with cols[0]:
        st.image(rapid.image, use_container_width=True)
    content = [
        f"ID: {rapid.local_rapid_id}",
        f"Ready ✅" if rapid.is_done() else f"Not Done ❌",
    ]
    for idx in range(1, len(content) + 1):
        with cols[idx]:
            st.write(content[idx - 1])
    with cols[3]:
        select = st.button('Select', key=f'bt_select_{rapid.local_rapid_id}')
        if select:
            get_collection().current_rapid = rapid
            update_canvas_key()
            st.rerun()

    with cols[4]:
        delete = st.button('Delete', key=f'bt_delete_{rapid.local_rapid_id}')
        if delete:
            get_collection().remove_rapid(rapid)
            st.rerun()
    prompt = st.text_input(label='Supply Optional Custom Rapid Prompt?',
                           value=rapid.prompt,
                           placeholder='Where is the dog in this image?',
                           key=f'tb_prompt_{rapid.local_rapid_id}')
    rapid.prompt = prompt

def display_inventory():
    coll = get_collection()
    rapids = coll.rapids
    done_rapids = [r for r in rapids if r.is_done()]
    not_done_rapids = [r for r in rapids if not r.is_done()]
    st.markdown(f"## 🎒 <span style='color: #1E90FF;'>Inventory ({len(done_rapids)}/{len(rapids)} done)</span>", unsafe_allow_html=True)
    for rapid in (not_done_rapids + done_rapids)[:5]:
        with st.container():
            display_rapid_metadata(rapid)

def get_next_rapid_id():
    st.session_state[CREATED_RAPIDS_COUNTER_KEY] += 1
    return st.session_state[CREATED_RAPIDS_COUNTER_KEY]


def render_file_upload():
    uploaded_images = st.file_uploader("➕ Add Single Image:",
                                       type=["png", "jpg"],
                                       key=f'file_uploader_id_{st.session_state.uploader_key}',
                                       accept_multiple_files=True
                                       )
    if uploaded_images:
        for uploaded_image in uploaded_images:
            image = Image.open(uploaded_image)
            get_collection().add_rapids(
                ValidationRapid(uploaded_image.name, image, rapid_id=get_next_rapid_id())
            )
        update_uploader_key()
        update_canvas_key()
        st.rerun()

def render_validation_set_cloning():
    st.write('➕ Add Images From an Existing Validation Set')
    col1, col2 = st.columns(2, vertical_alignment='center')
    with col1:
        validation_set_name = st.text_input(label_visibility='collapsed',
                                            label="Clone an Existing Validation Set :panda_face: :panda_face:",
                                            placeholder="validation_set_id")
    with col2:
        clone = st.button(label="Add All", use_container_width=True)

    if clone:
        rapids = get_validation_rapids(validation_set_name, get_env())
        if rapids is None:
            st.toast('🚫 **Validation set not found!**')
        else:
            get_collection().add_rapids(rapids)


def display_load_options():
    st.markdown("## :rocket: <span style='color: #4CAF50;'>Load</span>", unsafe_allow_html=True)

    with st.container():
        render_file_upload()
        render_validation_set_cloning()

        if val_set := st.session_state[LAST_CREATED_VALIDATION_SET_KEY]:
            st.write('###### You have successfully created a validation set! :boom:')
            st.write(f'{val_set}  [View it Here]({get_validation_set_url(val_set, get_env())})')


def set_env(env: str):
    st.session_state[CHOSEN_ENVIRONMENT_KEY] = env

def get_env():
    return st.session_state[CHOSEN_ENVIRONMENT_KEY]


def display_creation_option():
    st.markdown("## :rocket: <span style='color: #4CAF50;'>Create</span>", unsafe_allow_html=True)

    with st.container():
        col1, col2 = st.columns(2, vertical_alignment='top')

        with col1:
            rapid_type = st.selectbox(
                "Choose the Type of Rapid :family:",
                (RapidTypes.LOCATE,),
            )
            environment = st.selectbox(
                "What environment would you like to use?",
                (TEST_ENVIRONMENT, PRODUCTION_ENVIRONMENT),
                on_change=lambda: set_env(environment)
            )
        with col2:
            global_prompt = st.text_input(
                label="What is the question asked from the user?",
                placeholder="Where is the animal in this image?"
            )

            validation_set_name = st.text_input(
                label="Choose a Name For The Validation Set 🏷",
                placeholder="MyValidationSet"
            )


        create = st.button('Create Validation Set', use_container_width=True)

        if create:
            if any([not r.is_done() for r in get_collection().rapids]):
                st.toast('🚫 **Make Sure To Annotate All Rapids!**')
            elif global_prompt == '':
                st.toast('🚫 **Make Sure To Ask A Question From The User!**')
            elif validation_set_name == '':
                st.toast('🚫 **Validation Set Name Cannot Be empty!**')
            else:
                with st.spinner('In progress...'):
                    validation_set_id = validation_set_from_rapids(name=validation_set_name,
                                                                   global_prompt=global_prompt,
                                                                   rapids=get_collection().rapids,
                                                                   rapid_type=rapid_type,
                                                                   env=environment)
                st.session_state[LAST_CREATED_VALIDATION_SET_KEY] = validation_set_id
                st.toast(f'ValidationSet Created: {validation_set_id}')
                st.balloons()


def display_canvas():
    st.markdown("## 🎨 <span style='color: #00bcd4;'>Annotate</span>", unsafe_allow_html=True)

    if len(get_collection().rapids) == 0:
        st.markdown("### No Rapids found. Upload an Image to start :scream:", unsafe_allow_html=True)
        return

    if get_collection().all_done():
        st.markdown("### You are done annotating! Add more rapids or create a validation set :star2:",
                    unsafe_allow_html=True)
        return

    current_rapid = get_collection().current_rapid
    current_image = current_rapid.image

    resized_image = resize_image(current_image)

    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=3,
        stroke_color="black",
        background_image=resized_image,
        initial_drawing=current_rapid.annotation,
        update_streamlit=True,
        drawing_mode='rect',
        height=resized_image.height,
        width=resized_image.width,
        key=f'canvas_id_{st.session_state.canvas_key}_{current_rapid.local_rapid_id}',
        display_toolbar=False
    )
    if canvas_result.json_data is not None and len(canvas_result.json_data['objects']) > 0:
        get_collection().current_rapid.set_annotation(canvas_result.json_data)
        get_collection().set_next_unannotated_as_current()
        st.rerun()

    reset = st.button('Reset This Annotation')
    if reset:
        get_collection().current_rapid.set_annotation(dict())
        update_canvas_key()
        st.rerun()


def main():
    col1, col2, col3 = st.columns([1, 5, 5])

    with col2:
        display_canvas()
    with col3:#TODO change load and create emojis and colors
        display_load_options()
        st.divider()
        display_creation_option()
        st.divider()
        display_inventory()


def update_uploader_key():
    st.session_state.uploader_key += 1


def update_canvas_key():
    st.session_state.canvas_key += 1


def setup():
    dotenv.load_dotenv(DOTENV_PATH, override=True)
    st.set_page_config(layout="wide")
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0
    if "canvas_key" not in st.session_state:
        st.session_state.canvas_key = 0

    if CREATED_RAPIDS_COUNTER_KEY not in st.session_state:
        st.session_state[CREATED_RAPIDS_COUNTER_KEY] = 0

    if LAST_CREATED_VALIDATION_SET_KEY not in st.session_state:
        st.session_state[LAST_CREATED_VALIDATION_SET_KEY] = 0

    if CHOSEN_ENVIRONMENT_KEY not in st.session_state:
        st.session_state[CHOSEN_ENVIRONMENT_KEY] = TEST_ENVIRONMENT

if __name__ == '__main__':
    setup()
    main()
