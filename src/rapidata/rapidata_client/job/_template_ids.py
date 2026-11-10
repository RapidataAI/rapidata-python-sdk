from __future__ import annotations

import json
import os

TEMPLATE_IDS_VARIABLE = "RAPIDATA_TEMPLATE_IDS"

TEMPLATE_IDS: dict[str, dict[str, str]] = {
    "rapidata.ai": {
        "alignment/image": "jdf_PLACEHOLDER_prod_alignment_image",
        "alignment/video": "jdf_PLACEHOLDER_prod_alignment_video",
        "preference/image": "jdf_PLACEHOLDER_prod_preference_image",
        "preference/video": "jdf_PLACEHOLDER_prod_preference_video",
        "coherence/image": "jdf_PLACEHOLDER_prod_coherence_image",
        "coherence/video": "jdf_PLACEHOLDER_prod_coherence_video",
    },
    "rabbitdata.ch": {
        "alignment/image": "jdf_1aWV8WjLLGuF9s",
        "alignment/video": "jdf_1aWVGbJ1uYLNFd",
        "preference/image": "jdf_1aWVNF0PBivJq0",
        "preference/video": "jdf_1aWVTwKBWsgSrc",
        "coherence/image": "jdf_1aWVZnHvATz3L1",
        "coherence/video": "jdf_1aWVg9DapcWjW7",
    },
}


def template_id(environment: str, key: str) -> str:
    """The job definition id of the template ``key``, such as ``"alignment/image"``.

    ``RAPIDATA_TEMPLATE_IDS``, a JSON object of one environment's ids, replaces the built-in ones.
    """
    example = f'{{"{key}": "jdf_..."}}'
    override = os.environ.get(TEMPLATE_IDS_VARIABLE)
    if not override:
        ids = TEMPLATE_IDS.get(environment)
        if ids is None:
            raise ValueError(
                f"No Rapidata templates for {environment}. Set {TEMPLATE_IDS_VARIABLE} "
                f"to a JSON object of their ids, such as {example}."
            )
        return ids[key]

    try:
        ids = json.loads(override)
    except json.JSONDecodeError as e:
        raise ValueError(f"{TEMPLATE_IDS_VARIABLE} is not valid JSON: {e}") from e
    definition_id = ids.get(key) if isinstance(ids, dict) else None
    if not isinstance(definition_id, str) or not definition_id:
        raise ValueError(
            f"{TEMPLATE_IDS_VARIABLE} has no id for {key}. Set it to a JSON object "
            f"of template ids, such as {example}."
        )
    return definition_id
