'''
SelectWords order with validation set
'''

from rapidata import RapidataClient


def new_select_words_order(rapi: RapidataClient):
    # Validation set
    # This will be shown as defined in the ValidationSelection and will make our annotators understand the task better
    validation_set = (
        rapi.new_validation_set(
            name="Example SelectWords Validation Set"
        ).add_rapid(
            rapi.rapid_builder.select_words_rapid()
            .instruction("Click on the words 'give you up'")
            .media("https://i1.sndcdn.com/artworks-XJdVplPCbvDvJlH7-jF9c4A-t500x500.jpg", "never gonna give you up")
            .truths([2, 3, 4])
            .strict_grading(True)
            .build()
        )
    ).create()

    order = (
        rapi.create_select_words_order(name="Example SelectWords Order")
        .instruction("Click on the words you see in the image")
        .media(["https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/03/c3/da/03c3daee-16eb-d1d6-d7bd-dc45959faed8/AppIcon-1x_U007epad-0-85-220-0.png/1200x600wa.png"], ["A few wprds of kindness"])
        .validation_set(validation_set.id)
        .responses(25)
        .run()
    )

    return order

if __name__ == "__main__":
    new_select_words_order(RapidataClient())
