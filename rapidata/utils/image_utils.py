from io import BytesIO
import PIL.Image as Image

class ImageUtils:

    @staticmethod
    def convert_PIL_image_to_bytes(image: Image.Image):
        """
        Convert a PIL image to bytes with meta data encoded. We can't just use image.tobytes() because this only returns the pixel data.
        """
        buffer = BytesIO()
        image.save(buffer, image.format)
        return buffer.getvalue()