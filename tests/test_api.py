import api
import pytest

def call_handler(request):
    _, code = api.method_handler({"body": request}, {})
    return code

class TestMethodRequest:
    def test_bad_method_name(self, base_request):
        data = base_request.copy()
        data["method"] = "unknown_method"
        assert call_handler(data) == api.INVALID_REQUEST

    def test_bad_auth(self, base_request):
        data = base_request.copy()
        data["token"] = "bad_token"
        assert call_handler(data) == api.FORBIDDEN


class TestOnlineScore:
    @pytest.mark.parametrize("args", [
        {"phone": "79990000000", "email": "a@b.c"},
        {"first_name": "Ivan", "last_name": "Ivanov"},
        {"gender": 0, "birthday": "01.01.2000"},
    ])
    def test_valid_pairs(self, base_request, args):
        data = base_request.copy()
        data["arguments"] = args
        assert call_handler(data) == api.OK

    def test_no_pairs(self, base_request):
        data = base_request.copy()
        data["arguments"] = {"phone": "79990000000"}
        assert call_handler(data) == api.INVALID_REQUEST

    def test_admin_score(self, base_request, admin_token):
        data = base_request.copy()
        data["login"] = api.ADMIN_LOGIN
        data["token"] = admin_token
        data["arguments"] = {"phone": "79990000000", "email": "a@b.c"}

        resp, code = api.method_handler({"body": data}, {})
        assert code == api.OK
        assert resp["score"] == 42


class TestClientsInterests:
    def test_valid_request(self, base_request):
        data = base_request.copy()
        data["method"] = "clients_interests"
        data["arguments"] = {"client_ids": [1, 2, 3]}
        assert call_handler(data) == api.OK

    def test_empty_client_ids(self, base_request):
        data = base_request.copy()
        data["method"] = "clients_interests"
        data["arguments"] = {"client_ids": []}
        assert call_handler(data) == api.INVALID_REQUEST

    def test_wrong_type_in_ids(self, base_request):
        data = base_request.copy()
        data["method"] = "clients_interests"
        data["arguments"] = {"client_ids": [1, "two", 3]}
        assert call_handler(data) == api.INVALID_REQUEST