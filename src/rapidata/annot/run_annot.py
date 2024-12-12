import dotenv
from PIL import Image
import streamlit as st
from streamlit_drawable_canvas import st_canvas
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent.resolve()))

from consts import DONE_EMOJI, NOT_DONE_EMOJI, LAST_CREATED_VALIDATION_SET_KEY, DEFAULT_FILE, CREATED_RAPIDS_COUNTER_KEY
from models import ValidationRapid, ValidationRapidCollection, RapidTypes
from api import get_validation_rapids, get_validation_set_url, validation_set_from_rapids
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


def display_metadata():
    st.markdown("## 🎒 <span style='color: #1E90FF;'>Inventory</span>", unsafe_allow_html=True)
    if get_collection().rapids:
        st.write('A rapid is done when there is only one box on it and the prompt is given!')
    coll = get_collection()
    for rapid in coll.rapids[::-1]:
        with st.container(border=True):
            cols = st.columns(5, vertical_alignment='center')
            with cols[0]:
                st.image(rapid.image, use_container_width=True)
            content = [
                f"ID: {rapid.local_rapid_id}",
                f"Ready {DONE_EMOJI}" if rapid.is_done() else f"Not Done {NOT_DONE_EMOJI}",
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
            prompt = st.text_input(label='What should be the user prompt?',
                                   value=rapid.prompt,
                                   placeholder='Where is the dog in the image?',
                                   key=f'tb_prompt_{rapid.local_rapid_id}')
            rapid.prompt = prompt

def get_next_rapid_id():
    st.session_state[CREATED_RAPIDS_COUNTER_KEY] += 1
    return st.session_state[CREATED_RAPIDS_COUNTER_KEY]


def display_file_uploader():
    with st.container(border=True):
        uploaded_images = st.file_uploader("➕Add rapid:",
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


def display_clone_option():
    with st.container(border=True):

        validation_set_name = st.text_input(label="Clone an Existing Validation Set :panda_face: :panda_face:", placeholder="validation_set_id")
        clone = st.button(label="Clone and Add All", use_container_width=True)

        if clone:
            rapids = get_validation_rapids(validation_set_name)
            if rapids is None:
                st.toast('🚫 **Validation set not found!**')
            else:
                get_collection().add_rapids(rapids)


def display_creation_option():
    with st.container(border=True):
        rapid_type = st.selectbox(
            "Choose the Type of Rapid :family:",
            (RapidTypes.LOCATE,),
        )
        validation_set_name = st.text_input(
            label="Choose a Name For The Validation Set 🏷",
            placeholder="MyValidationSet"
        )
        create = st.button('Create Validation Set', use_container_width=True)

        if create:
            if any([not r.is_done() for r in get_collection().rapids]):
                st.toast('🚫 **Make Sure To Finish All Rapids!**')
            elif validation_set_name == '':
                st.toast('🚫 **Validation Set Name Cannot Be empty!**')
            else:
                with st.spinner('In progress...'):
                    validation_set_id = validation_set_from_rapids(name=validation_set_name,
                                                                   rapids=get_collection().rapids,
                                                                   rapid_type=rapid_type)
                st.session_state[LAST_CREATED_VALIDATION_SET_KEY] = validation_set_id
                st.toast(f'ValidationSet Created: {validation_set_id}')
                st.balloons()


def display_cockpit():
    st.markdown("## :rocket: <span style='color: #4CAF50;'>Cockpit</span>", unsafe_allow_html=True)

    display_file_uploader()

    col1, col2 = st.columns(2, vertical_alignment='top')

    with col2:
        display_creation_option()

    with col1:
        display_clone_option()
        if val_set := st.session_state[LAST_CREATED_VALIDATION_SET_KEY]:
            st.write('###### You have successfully created a validation set! :boom:')
            st.write(f'{val_set}  [View it Here]({get_validation_set_url(val_set)})')


def display_canvas():
    st.markdown("## 🎨 <span style='color: #00bcd4;'>Annotate</span>", unsafe_allow_html=True)

    if get_collection().current_rapid is None:
        st.markdown("### No Rapids found. Upload an Image to start :scream:", unsafe_allow_html=True)
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

    reset = st.button('Reset This Annotation')
    if reset:
        get_collection().current_rapid.set_annotation(dict())
        update_canvas_key()
        st.rerun()


def main():
    col1, col2, col3 = st.columns([1, 5, 5])

    with col2:
        display_canvas()
    with col3:
        display_cockpit()
        st.divider()
        display_metadata()


def update_uploader_key():
    st.session_state.uploader_key += 1


def update_canvas_key():
    st.session_state.canvas_key += 1


def setup():
    dotenv.load_dotenv('/Users/sneccello/Documents/rapidata/data_doctor/ranking_poc/.env', override=True)
    st.set_page_config(layout="wide")
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0
    if "canvas_key" not in st.session_state:
        st.session_state.canvas_key = 0

    if CREATED_RAPIDS_COUNTER_KEY not in st.session_state:
        st.session_state[CREATED_RAPIDS_COUNTER_KEY] = 0

    if LAST_CREATED_VALIDATION_SET_KEY not in st.session_state:
        st.session_state[LAST_CREATED_VALIDATION_SET_KEY] = 0

if __name__ == '__main__':
    setup()
    main()
