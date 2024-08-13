import os
from PIL import Image

class LocalFileService:
    
    def load_image(self, image_path: str) -> Image.Image:
        self.check_file_exists(image_path)
        return Image.open(image_path)
    
    def load_images(self, image_paths: list[str]) -> list[Image.Image]:
        return [self.load_image(image_path) for image_path in image_paths]
    
    def load_video(self, video_path: str):
        self.check_file_exists(video_path)
        return open(video_path, 'rb')
    
    def load_videos(self, video_paths: list[str]):
        return [self.load_video(video_path) for video_path in video_paths]
    
    def _file_exists(self, file_path: str) -> bool:
        return os.path.exists(file_path)
    
    def check_file_exists(self, file_path: str):
        if not self._file_exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found.")