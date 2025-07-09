import pandas as pd

from rapidata.service.openapi_service import OpenAPIService


class RapidataLeaderboard:
    """
    An instance of a Rapidata leaderboard.

    Used to interact with a specific leaderboard in the Rapidata system, such as retrieving prompts and evaluating models.

    Args:
        name: The name that will be used to identify the leaderboard on the overview.
        instruction: The instruction that will determine what how the models will be evaluated.
        show_prompt: Whether to show the prompt to the users.
        id: The ID of the leaderboard.
        openapi_service: The OpenAPIService instance for API interaction.
    """
    def __init__(self, name: str, instruction: str, show_prompt: bool, id: str, openapi_service: OpenAPIService):
        self.__openapi_service = openapi_service
        self.name = name
        self.instruction = instruction
        self.show_prompt = show_prompt
        self.id = id

    def get_standings(self) -> pd.DataFrame:
        """
        Returns the standings of the leaderboard.
        """
        participants = self.__openapi_service.leaderboard_api.leaderboard_leaderboard_id_participants_get(
            leaderboard_id=self.id
        )

        standings = []
        for participant in participants.items:
            standings.append({
                "name": participant.name,
                "status": participant.status,
                "score": participant.score,
                "wins": participant.wins,
                "total_matches": participant.total_matches
            })

        return pd.DataFrame(standings)

    def __str__(self) -> str:
        return f"RapidataLeaderboard(name={self.name}, instruction={self.instruction}, show_prompt={self.show_prompt}, leaderboard_id={self.id})"
    
    def __repr__(self) -> str:
        return self.__str__()


        


