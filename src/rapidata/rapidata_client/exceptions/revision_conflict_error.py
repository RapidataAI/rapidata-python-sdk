from __future__ import annotations


class RevisionConflictError(Exception):
    """Raised by ``RapidataJobDefinition.save(require_latest=True)`` when another
    revision was saved after this object was loaded. Nothing was created.

    Attributes:
        job_definition_id (str): The job definition that was being saved.
        base_revision (int): The revision the object was loaded at.
        latest_revision (int): The definition's latest revision on the server.
    """

    def __init__(
        self, job_definition_id: str, base_revision: int, latest_revision: int
    ):
        self.job_definition_id = job_definition_id
        self.base_revision = base_revision
        self.latest_revision = latest_revision
        super().__init__(
            f"Job definition '{job_definition_id}' was loaded at revision {base_revision}, "
            f"but revision {latest_revision} has been saved since. "
            "Call reload() to load the latest revision, reapply your changes and save again."
        )
