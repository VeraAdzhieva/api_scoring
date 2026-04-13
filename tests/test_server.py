import requests
import api

def test_online_score_functional(server, base_request):
    url = "http://localhost:8081/method"

    payload = base_request.copy()
    payload["arguments"] = {
        "phone": "79991234567",
        "email": "test@example.com"
    }

    response = requests.post(url, json=payload)

    assert response.status_code == api.OK
    data = response.json()
    assert "response" in data
    assert "score" in data["response"]


def test_admin_score_functional(server, base_request_admin):
    url = "http://localhost:8081/method"
    payload = base_request_admin.copy()
    payload["arguments"] = {
        "phone": "79991234567",
        "email": "test@example.com"
    }

    response = requests.post(url, json=payload)

    assert response.status_code == api.OK
    data = response.json()
    assert data["response"]["score"] == int(api.ADMIN_SALT)