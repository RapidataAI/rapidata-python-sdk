class RapidataDataTypes:
    MEDIA = "media" # any form of image, video or audio
    TEXT = "text"

    @classmethod
    def _possible_values(cls):
        return [cls.MEDIA, cls.TEXT]
