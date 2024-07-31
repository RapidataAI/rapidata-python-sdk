from PIL import Image

class LocalFileService:
    
    def load_image(self, image_path: str) -> Image.Image:
        return Image.open(image_path)
    
    def load_images(self, image_paths: list[str]) -> list[Image.Image]:
        return [self.load_image(image_path) for image_path in image_paths]