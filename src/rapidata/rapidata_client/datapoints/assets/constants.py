ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
ALLOWED_AUDIO_EXTENSIONS = [".mp3"]
# The asset service classifies every GIF as a video and converts animated ones to MP4.
ALLOWED_VIDEO_EXTENSIONS = [".mp4", ".gif"]

ALLOWED_MEDIA_EXTENSIONS = (
    ALLOWED_IMAGE_EXTENSIONS + ALLOWED_AUDIO_EXTENSIONS + ALLOWED_VIDEO_EXTENSIONS
)
