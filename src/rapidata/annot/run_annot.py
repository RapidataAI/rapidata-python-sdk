import os

from consts import DEFAULT_FILE, METADATA_COLUMNS, CANVAS_WIDTH, TEMP_FILE_DIR, DONE_EMOJI, NOT_DONE_EMOJI

from PIL import Image
import streamlit as st
from streamlit_drawable_canvas import st_canvas

from models import ValidationRapid, ValidationRapidCollection
from utils import resize_image, calc_image_scale, image_to_base64, calc_relative_bbox_area







@st.cache_resource
def get_collection():
    return ValidationRapidCollection(add_default=True)


def display_metadata():
    st.markdown("## 🎒 <span style='color: #1E90FF;'>Inventory</span>", unsafe_allow_html=True)
    coll = get_collection()

    for rapid in coll.rapids[::-1]:
        with st.container(border=True):
            cols = st.columns(5, vertical_alignment='center')
            with cols[0]:
                st.image(rapid.image, use_container_width=True)
            content = [
                rapid.name,
                f"Ready {DONE_EMOJI}" if rapid.is_done() else f"Not Done {NOT_DONE_EMOJI}",
            ]
            for idx in range(1, len(content) + 1):
                with cols[idx]:
                    st.write(content[idx - 1])
            with cols[3]:
                select = st.button('select', key=f'bt_select_{rapid.rapid_id}')
                if select:
                    get_collection().current_rapid = rapid
                    update_canvas_key()
                    st.rerun()
            with cols[4]:
                delete = st.button('delete', key=f'bt_delete_{rapid.rapid_id}')
                if delete:
                    get_collection().remove_rapid(rapid)
                    st.rerun()


def display_cockpit():
    st.markdown("## :rocket: <span style='color: #4CAF50;'>Cockpit</span>", unsafe_allow_html=True)


    uploaded_image = st.file_uploader("➕Add rapid:",
                                      type=["png", "jpg"],
                                      key=f'file_uploader_id_{st.session_state.uploader_key}'
                                      )
    if uploaded_image:
        image = Image.open(uploaded_image)
        get_collection().add_rapid(
            ValidationRapid(uploaded_image.name, image)
        )
        update_uploader_key()
        update_canvas_key()
        st.rerun()

    validation_set_name = st.text_input(label='Validation Set Name 🏷️')
    submit_validation_set = st.button(label="Submit Validation Set 📤")
    if submit_validation_set:
        if validation_set_name == "":
            st.toast("🚫 **Make sure to enter a name for the validation set!**")
        elif any([not rapid.is_done() for rapid in get_collection().rapids]):
            st.toast("🚫 **Make sure all rapids are ready to submit!**")
        else:
            st.toast(f"✅ **Submitting {len(get_collection().rapids)} rapids**")


def display_canvas():
    st.markdown("## 🎨 <span style='color: #00bcd4;'>Annotate</span>", unsafe_allow_html=True)
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
        key=f'canvas_id_{st.session_state.canvas_key}_{current_rapid.rapid_id}',
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
    col1, col2, col3 = st.columns([1, 3, 3])

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
    st.set_page_config(layout="wide")
    os.makedirs(TEMP_FILE_DIR, exist_ok=True)
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0
    if "canvas_key" not in st.session_state:
        st.session_state.canvas_key = 0


if __name__ == '__main__':
    setup()
    main()
