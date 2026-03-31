import datetime
import hashlib
import json
import logging
import re
import uuid
from argparse import ArgumentParser
from email.message import Message
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable

import scoring


class Gender(Enum):
    UNKNOWN = 0
    MALE = 1
    FEMALE = 2


class ErrorMessage(Enum):
    BAD_REQUEST = "Bad Request"
    FORBIDDEN = "Forbidden"
    NOT_FOUND = "Not Found"
    INVALID_REQUEST = "Invalid Request"
    INTERNAL_ERROR = "Internal Server Error"


SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"

OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500

ERRORS = {
    BAD_REQUEST: ErrorMessage.BAD_REQUEST.value,
    FORBIDDEN: ErrorMessage.FORBIDDEN.value,
    NOT_FOUND: ErrorMessage.NOT_FOUND.value,
    INVALID_REQUEST: ErrorMessage.INVALID_REQUEST.value,
    INTERNAL_ERROR: ErrorMessage.INTERNAL_ERROR.value,
}


class Fields(type):
    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        cls = super().__new__(mcs, name, bases, namespace)

        fields = {}
        for base in bases:
            if hasattr(base, "_fields"):
                fields.update(base._fields)

        for attr_name, attr_value in namespace.items():
            if attr_name.startswith("_"):
                continue
            if callable(attr_value):
                continue
            if isinstance(attr_value, type):
                continue
            if hasattr(attr_value, "validate") and hasattr(attr_value, "required"):
                fields[attr_name] = attr_value

        cls._fields = fields
        return cls


class BaseField(metaclass=Fields):
    def __init__(self, required: bool = False, nullable: bool = False):
        self.required = required
        self.nullable = nullable

    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        raise NotImplementedError

    def is_empty(self, value: Any) -> bool:
        return value is None or value == ""


class CharField(BaseField):

    def __init__(
        self,
        required: bool = False,
        nullable: bool = False,
        min_length: int = None,
        max_length: int = None,
        pattern: str = None,
    ):
        super().__init__(required=required, nullable=nullable)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None

    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        errors = []
        name = field_name or self.__class__.__name__

        if self.is_empty(value):
            if self.required and not self.nullable:
                errors.append(f"Поле '{name}' обязательно")
            return len(errors) == 0, errors

        if not isinstance(value, str):
            errors.append(f"Поле '{name}' должно быть строкой")
            return False, errors

        if self.min_length and len(value) < self.min_length:
            errors.append(
                f"Поле '{name}' должно быть минимум {self.min_length} символов"
            )

        if self.pattern and not self.pattern.match(value):
            errors.append(f"Поле '{name}' не соответствует формату")

        return len(errors) == 0, errors


class EmailField(BaseField):

    def __init__(self, required: bool = False, nullable: bool = False):
        super().__init__(required=required, nullable=nullable)

    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        errors = []
        name = field_name or "email"

        if self.is_empty(value):
            if self.required and not self.nullable:
                errors.append(f"Поле '{name}' обязательно")
            return len(errors) == 0, errors

        if not isinstance(value, str):
            return False, [f"Поле '{name}' должно быть строкой"]

        if "@" not in value:
            return False, [f"Поле '{name}' должно содержать @"]

        return True, []


class PhoneField(BaseField):

    def __init__(self, required: bool = False, nullable: bool = False):
        super().__init__(required=required, nullable=nullable)

    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        errors = []
        name = field_name or "phone"

        if self.is_empty(value):
            if self.required and not self.nullable:
                errors.append(f"Поле '{name}' обязательно")
            return len(errors) == 0, errors

        if isinstance(value, int):
            value = str(value)
        elif isinstance(value, str):
            value = re.sub(r"[^\d]", "", value)
        else:
            return False, [f"Поле '{name}' должно быть строкой или числом"]

        if len(value) != 11:
            errors.append(f"Поле '{name}' должно содержать 11 цифр")

        if not value.startswith("7"):
            errors.append(f"Поле '{name}' должно начинаться с 7")

        return len(errors) == 0, errors


class DateField(BaseField):

    def __init__(
        self, required: bool = False, nullable: bool = False, max_years_ago: int = 70
    ):
        super().__init__(required=required, nullable=nullable)
        self.max_years_ago = max_years_ago

    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        errors = []
        name = field_name or "date"

        if self.is_empty(value):
            if self.required and not self.nullable:
                errors.append(f"Поле '{name}' обязательно")
            return len(errors) == 0, errors

        if not isinstance(value, str):
            return False, [f"Поле '{name}' должно быть строкой"]

        pattern = r"^\d{2}\.\d{2}\.\d{4}$"
        if not re.match(pattern, value):
            return False, [f"Поле '{name}' должно быть в формате DD.MM.YYYY"]

        try:
            date_value = datetime.datetime.strptime(value, "%d.%m.%Y")
        except ValueError:
            return False, [f"Поле '{name}' содержит невалидную дату"]

        today = datetime.datetime.now()
        years_passed = today.year - date_value.year
        if (today.month, today.day) < (date_value.month, date_value.day):
            years_passed -= 1

        if years_passed > self.max_years_ago:
            return False, [
                f"Поле '{name}' указывает на дату, с которой прошло больше {self.max_years_ago} лет"
            ]

        if date_value > today:
            return False, [f"Поле '{name}' не может быть в будущем"]

        return True, []


class BirthDayField(DateField):
    def __init__(self, required: bool = False, nullable: bool = False):
        super().__init__(required=required, nullable=nullable, max_years_ago=70)


class GenderField(BaseField):

    def __init__(self, required: bool = False, nullable: bool = False):
        super().__init__(required=required, nullable=nullable)

    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        errors = []
        name = field_name or "gender"

        if self.is_empty(value):
            if self.required and not self.nullable:
                errors.append(f"Поле '{name}' обязательно")
            return len(errors) == 0, errors

        if not isinstance(value, int):
            return False, [f"Поле '{name}' должно быть числом"]

        if value not in [0, 1, 2]:
            errors.append(f"Поле '{name}' должно быть 0, 1, или 2")

        return len(errors) == 0, errors


class ClientIDsField(BaseField):

    def __init__(self, required: bool = False, nullable: bool = False):
        super().__init__(required=required, nullable=nullable)

    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        errors = []
        name = field_name or "client_ids"

        if self.is_empty(value):
            if self.required and not self.nullable:
                errors.append(f"Поле '{name}' обязательно")
            return len(errors) == 0, errors

        if not isinstance(value, list):
            return False, [f"Поле '{name}' должно быть списком"]

        if len(value) == 0:
            return False, [f"Поле '{name}' не может быть пустым"]

        for idx, client_id in enumerate(value):
            if not isinstance(client_id, int):
                return False, [f"Поле '{name}[{idx}]' должно быть числом"]

        return True, []


class ArgumentsField(BaseField):

    def __init__(self, required: bool = False, nullable: bool = False):
        super().__init__(required=required, nullable=nullable)

    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        errors = []
        name = field_name or "arguments"

        if self.is_empty(value):
            if self.required and not self.nullable:
                errors.append(f"Поле '{name}' обязательно")
            return len(errors) == 0, errors

        if not isinstance(value, dict):
            return False, [f"Поле '{name}' должно быть объектом"]

        return True, []


class MethodRequest(metaclass=Fields):
    account = CharField(required=True, nullable=False)
    login = CharField(required=True, nullable=False)
    token = CharField(required=True, nullable=False)
    arguments = ArgumentsField(required=True, nullable=False)
    method = CharField(required=True, nullable=False)

    @classmethod
    def validate(cls, data: dict[str, Any]) -> tuple[bool, list[str]]:
        errors = []
        for field_name, field_validator in cls._fields.items():
            value = data.get(field_name)
            is_valid, field_errors = field_validator.validate(value, field_name)
            if not is_valid:
                errors.extend(field_errors)

        if data.get("method") not in ["online_score", "clients_interests"]:
            errors.append(f"Неизвестный метод: {data.get('method')}")

        return len(errors) == 0, errors

    @property
    def is_admin(self) -> bool:
        return self.login == ADMIN_LOGIN


class OnlineScoreRequest(metaclass=Fields):
    first_name = CharField(required=False, nullable=True, min_length=1)
    last_name = CharField(required=False, nullable=True, min_length=1)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    @classmethod
    def validate(
        cls, data: dict[str, Any], ctx: dict[str, Any] = None
    ) -> tuple[bool, list[str]]:
        errors = []
        has_fields = []

        for field_name, field_validator in cls._fields.items():
            value = data.get(field_name)
            is_valid, field_errors = field_validator.validate(value, field_name)
            if not is_valid:
                errors.extend(field_errors)
            elif value is not None and value != "":
                has_fields.append(field_name)

        if not cls._check_field_pairs(data):
            errors.append(
                "Должна присутствовать хотя бы одна пара полей с непустыми значениями"
            )

        if ctx is not None:
            ctx["has"] = has_fields

        return len(errors) == 0, errors

    @classmethod
    def _check_field_pairs(cls, data: dict[str, Any]) -> bool:
        def is_filled(key):
            val = data.get(key)
            return val is not None and val != ""

        if is_filled("phone") and is_filled("email"):
            return True
        if is_filled("first_name") and is_filled("last_name"):
            return True
        if is_filled("gender") and is_filled("birthday"):
            return True

        return False

class ClientsInterestsRequest(metaclass=Fields):
    client_ids = ClientIDsField(required=True, nullable=False)
    date = DateField(required=False, nullable=True, max_years_ago=70)

    @classmethod
    def validate(
        cls, data: dict[str, Any], ctx: dict[str, Any] = None
    ) -> tuple[bool, list[str]]:
        errors = []
        for field_name, field_validator in cls._fields.items():
            value = data.get(field_name)
            is_valid, field_errors = field_validator.validate(value, field_name)
            if not is_valid:
                errors.extend(field_errors)

        if ctx is not None and not errors:
            client_ids = data.get("client_ids", [])
            ctx["nclients"] = len(client_ids)

        return len(errors) == 0, errors


def check_auth(request_data: dict[str, Any]) -> bool:
    token = request_data.get("token", "")

    if not token:
        return False

    login = request_data.get("login", "")

    if login == ADMIN_LOGIN:
        digest = hashlib.sha512(
            (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode("utf-8")
        ).hexdigest()
    else:
        account = request_data.get("account", "") or ""
        digest = hashlib.sha512((account + login + SALT).encode("utf-8")).hexdigest()

    return digest == token


def method_handler(
    request: dict[str, Any], ctx: dict[str, Any], settings: dict[str, Any] = None
) -> tuple[dict[str, Any], int]:

    request_data = request.get("body", {})

    if not request_data:
        return {}, INVALID_REQUEST

    is_valid, errors = MethodRequest.validate(request_data)

    if not check_auth(request_data):
        return {}, FORBIDDEN

    if not is_valid:
        return {"error": errors}, INVALID_REQUEST

    method_name = request_data.get("method")
    arguments = request_data.get("arguments", {})

    if method_name == "online_score":
        is_valid, errors = OnlineScoreRequest.validate(arguments, ctx)
        if not is_valid:
            return {"error": errors}, INVALID_REQUEST

        try:
            if request_data.get("login") == "admin":
                score = int(ADMIN_SALT)
            else:
                score = scoring.get_score(
                    phone=arguments.get("phone"),
                    email=arguments.get("email"),
                    birthday=arguments.get("birthday"),
                    gender=arguments.get("gender"),
                    first_name=arguments.get("first_name"),
                    last_name=arguments.get("last_name"),
                )
            return {"score": score}, OK
        except Exception as e:
            return {"error": str(e)}, INVALID_REQUEST

    elif method_name == "clients_interests":
        is_valid, errors = ClientsInterestsRequest.validate(arguments, ctx)
        if not is_valid:
            return {"error": errors}, INVALID_REQUEST

        try:
            client_ids = arguments.get("client_ids", [])
            interests = scoring.get_clients_interests(client_ids)
            return interests, OK
        except Exception as e:
            return {"error": str(e)}, INVALID_REQUEST
    else:
        return {"error": f"Unknown method: {method_name}"}, INVALID_REQUEST

class MainHTTPHandler(BaseHTTPRequestHandler):
    router: dict[str, Callable] = {"method": method_handler}
    def get_request_id(self, headers: Message) -> str:
        return headers.get("HTTP_X_REQUEST_ID", uuid.uuid4().hex)

    def do_POST(self) -> None:
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers["Content-Length"]))
            request = json.loads(data_string)
        except Exception:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path](
                        {"body": request, "headers": self.headers},
                        context,
                    )
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode("utf-8"))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", action="store", type=int, default=8080)
    parser.add_argument("-l", "--log", action="store", default=None)
    args = parser.parse_args()

    logging.basicConfig(
        filename=args.log,
        level=logging.INFO,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )

    server = HTTPServer(("localhost", args.port), MainHTTPHandler)

    logging.info("Starting server at %s" % args.port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    server.server_close()
