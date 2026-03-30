import random
from typing import Any

def get_score(
    phone,
    email,
    birthday=None,
    gender=None,
    first_name=None,
    last_name=None,
) -> float:
    score = 0

    if phone:
        score += 1.5

    if email:
        score += 1.5

    if birthday and gender:
        score += 1.5

    if first_name and last_name:
        score += 0.5

    return score


def get_interests(cid: str) -> list[str]:
    interests = [
        "cars",
        "pets",
        "travel",
        "hi-tech",
        "sport",
        "music",
        "books",
        "tv",
        "cinema",
        "geek",
        "otus",
    ]

    return random.sample(interests, 2)

def get_clients_interests(client_ids: list[Any]) -> dict[str, list[str]]:

    result = {}
    
    for client_id in client_ids:
        client_id_str = str(client_id)
        result[client_id_str] = get_interests(client_id_str)
    
    return result
