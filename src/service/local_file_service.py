from PIL import Image

class LocalFileService:
    
    def load_image(self, image_path: str) -> Image.Image:
        return Image.open(image_path)
    
    def load_images(self, image_paths: list[str]) -> list[Image.Image]:
        return [self.load_image(image_path) for image_path in image_paths]
    
    def load_video(self, video_path: str):
        return open(video_path, 'rb')
    
    def load_videos(self, video_paths: list[str]):
        return [self.load_video(video_path) for video_path in video_paths]