import datetime
import hashlib
import json
import logging
import uuid
from argparse import ArgumentParser
from email.message import Message
from enum import Enum
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer,
)
from typing import Any, Callable
import scoring, re
from abc import ABCMeta, abstractmethod
from datetime import datetime

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

ERRORS = {BAD_REQUEST, FORBIDDEN, NOT_FOUND, INTERNAL_ERROR, INVALID_REQUEST}

MAX_YEARS_AGO = 70

class Fields(ABCMeta):
    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        cls = super().__new__(mcs, name, bases, namespace)
        
        fields = {}
        for base in bases:
            if hasattr(base, '_fields'):
                fields.update(base._fields)
        
        for attr_name, attr_value in namespace.items():
            if hasattr(attr_value, 'validate') and hasattr(attr_value, 'required'):
                fields[attr_name] = attr_value
        
        cls._fields = fields
        return cls

class BaseField(metaclass = Fields):
    def __init__(self, required: bool = False, nullable: bool = False):
        self.required = required
        self.nullable = nullable
    
    @abstractmethod
    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        pass
    
    def is_empty(self, value: Any) -> bool:
        return value is None or value == ''
    
    def check_empty_value(self, value: Any, field_name: str) -> tuple[bool, list[str]]:
        errors = []
        name = field_name or self.__class__.__name__
        
        if self.is_empty(value):
            if self.required and not self.nullable:
                errors.append(f"Поле '{name}' обязательно")
            return len(errors) == 0, errors, False
        
        if value is None and self.nullable:
            return True, [], False 
    
        return True, [], True
    
    def transform(self, value: Any) -> Any:
        return value

class CharField(BaseField):
    def __init__(self,
        required: bool = False,
        nullable: bool = False,
        min_length: int = None,
        max_length: int = None,
        pattern: str = None
    ):
        super().__init__(required=required, nullable=nullable)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None

    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        errors = []
        name = field_name or self.__class__.__name__
        
        is_empty_ok, empty_errors, should_continue = self.check_empty_value(value, name)

        if not should_continue:
            return is_empty_ok, empty_errors
        
        if not isinstance(value, str):
            errors.append(f"Поле '{name}' должно быть строкой")
            return False, errors
       
        if self.pattern and not self.pattern.match(value):
            errors.append(f"Поле '{name}' не соответствует формату")
        
        return len(errors) == 0, errors
    
    def transform(self, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


class ArgumentsField(BaseField):
    def __init__(self, required: bool = False, nullable: bool = False, fields: dict = None):
        super().__init__(required=required, nullable=nullable)
        self.fields = fields or {}
    
    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        errors = []
        name = field_name or 'arguments'
        
        is_empty_ok, empty_errors, should_continue = self.check_empty_value(value, name)
        if not should_continue:
            return is_empty_ok, empty_errors
        
        if not isinstance(value, dict):
            errors.append(f"Поле '{name}' должно быть объектом")
            return False, errors
        
        return len(errors) == 0, errors


class EmailField(CharField):
    def __init__(self, required: bool = False, nullable: bool = False):
        super().__init__(
            required=required,
            nullable=nullable
        )
    
    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        is_valid, errors = super().validate(value, field_name or 'email')
        
        if not is_valid and value and isinstance(value, str):
            errors = [f"Поле '{field_name or 'email'}' должно быть валидным email адресом"]

        if value and value.find("@") > 0:
            errors = [f"Поле '{field_name or 'email'}' должно содеражть знак @"]    
        
        return is_valid, errors


class PhoneField(CharField):
    def __init__(self, required: bool = False, nullable: bool = False, country_code: str = '7'):
        phone_pattern = r'^' + re.escape(country_code) + r'\d{10}$'
        super().__init__(required=required, nullable=nullable, pattern=phone_pattern)
        self.country_code = country_code
    
    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        if isinstance(value, str):
            value = re.sub(r'[^\d]', '', value)
        
        is_valid, errors = super().validate(value, field_name or 'phone')
        
        if not is_valid and value:
            errors = [f"Поле '{field_name or 'phone'}' должно быть номером телефона (+{self.country_code}...)"]
        
        return is_valid, errors
    
    def transform(self, value: Any) -> Any:
        if isinstance(value, str):
            return re.sub(r'[^\d]', '', value)
        return value


class DateField(CharField):

    def __init__(self, required: bool = False, nullable: bool = False):
        date_pattern = r'^\d{2}\.\d{2}\.\d{4}$'
        super().__init__(required=required, nullable=nullable, pattern=date_pattern)
    
    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        is_valid, errors = super().validate(value, field_name or 'date')
        
        if is_valid and value:
            try:
                datetime.strptime(value, '%d.%m.%Y')
            except ValueError:
                errors = [f"Поле '{field_name or 'date'}' должно быть валидной датой (DD.MM.YYYY)"]
                return False, errors
        
        return is_valid, errors


class BirthDayField(DateField):
    def __init__(self, required: bool = False, nullable: bool = False):
        super().__init__(
            required=required,
            nullable=nullable
        )
    
    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        is_valid, errors = super().validate(value, field_name or 'birthday')
        
        if not is_valid:
            return is_valid, errors
        
        if self.is_empty(value) or value is None:
            return True, []
        
        try:
            birthday = datetime.strptime(value, '%d.%m.%Y')
            today = datetime.now()
            years_passed = today.year - birthday.year
        
            if (today.month, today.day) < (birthday.month, birthday.day):
                years_passed -= 1
        
            if years_passed > MAX_YEARS_AGO:
                errors = [f"Поле '{field_name}' указывает на дату, с которой прошло больше {MAX_YEARS_AGO} лет"]
                return False, errors
        except ValueError:
            errors.append(f"Поле '{field_name or 'birthday'}' должно быть валидной датой рождения")
            return False, errors
        
        return len(errors) == 0, []


class GenderField(CharField):
    def __init__(self, required: bool = False, nullable: bool = False):
        super().__init__(required=required, nullable=nullable, pattern=r'^[012]$')
    
    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        if isinstance(value, int):
            value = str(value)
        
        is_valid, errors = super().validate(value, field_name or 'gender')
        
        if not is_valid and value is not None:
            errors = [f"Поле '{field_name or 'gender'}' должно быть 0 (female), 1 (male), или 2 (unspecified)"]
        
        return is_valid, errors


class ClientIDsField(BaseField):
    
    def __init__(self, required: bool = False, nullable: bool = False):
        super().__init__(required=required, nullable=nullable)
    
    def validate(self, value: Any, field_name: str = None) -> tuple[bool, list[str]]:
        errors = []
        name = field_name or 'client_ids'
        
        is_empty_ok, empty_errors, should_continue = self.check_empty_value(value, name)
        if not should_continue:
            return is_empty_ok, empty_errors
        
        if not isinstance(value, list):
            errors.append(f"Поле '{name}' должно быть списком")
            return False, errors
        
        return len(errors) == 0, errors


class ClientsInterestsRequest(metaclass=Fields):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)
    
    @classmethod
    def validate(cls,  data: dict[str, Any]) -> tuple[bool, list[str]]:
        errors = []
        
        for field_name, field_validator in cls._fields.items():
            value = data.get(field_name)
            is_valid, field_errors = field_validator.validate(value, field_name)
            
            if not is_valid:
                errors.extend(field_errors)
        
        return len(errors) == 0, errors


class OnlineScoreRequest(metaclass=Fields):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)
    
    @classmethod
    def validate(cls,  data: dict[str, Any]) -> tuple[bool, list[str]]:
        errors = []
        
        for field_name, field_validator in cls._fields.items():
            value = data.get(field_name)
            is_valid, field_errors = field_validator.validate(value, field_name)
            
            if not is_valid:
                errors.extend(field_errors)
        
        return len(errors) == 0, errors


class MethodRequest(metaclass=Fields):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)
    
    @classmethod
    def validate(cls,  data: dict[str, Any]) -> tuple[bool, list[str]]:
        errors = []
      #  auth = check_auth()
      #  if not auth:
      #      return ErrorMessage(FORBIDDEN), FORBIDDEN
        for field_name, field_validator in cls._fields.items():
            value = data.get(field_name)
            is_valid, field_errors = field_validator.validate(value, field_name)
            
            if not is_valid:
                errors.extend(field_errors)
        
        return len(errors) == 0, errors

    @property
    def is_admin(self) -> bool:
        return self.login == ADMIN_LOGIN


def check_auth(request: MethodRequest) -> bool:
    if request.is_admin:
        digest = hashlib.sha512(
            (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode("utf-8")
        ).hexdigest()
    else:
        digest = hashlib.sha512(
            (request.account + request.login + SALT).encode("utf-8")
        ).hexdigest()
    return digest == request.token
  

def method_handler(
    request: dict[str, Any],
    ctx: dict[str, Any],
    settings:  dict[str, Any]
) -> tuple[dict[str, Any], int]:

    body = request.get('body')
    is_valid, errors = MethodRequest.validate(body)
    if not is_valid:
        return errors, INVALID_REQUEST
    
    method_name = body.get('method')
    arguments = body.get('arguments', {})
    
    if method_name == 'online_score':
        is_valid, errors = OnlineScoreRequest.validate(arguments)
        if not is_valid:
            return errors, BAD_REQUEST
    
        try:
            login = body.get('login', '')
            if login == 'admin':
                score = ADMIN_SALT
            else:
                score = scoring.get_score(
                    phone=arguments.get('phone'),
                    email=arguments.get('email'),
                    birthday=arguments.get('birthday'),
                    gender=arguments.get('gender'),
                    first_name=arguments.get('first_name'),
                    last_name=arguments.get('last_name')
                )
            return {"score": score}, OK
        except Exception:
            return "Internal error", INTERNAL_ERROR
        
    elif method_name == 'clients_interests':
        is_valid, errors = ClientsInterestsRequest.validate(arguments)
        if not is_valid:
            return errors, BAD_REQUEST
        try:
            interests = scoring.get_clients_interests(arguments.get('client_ids'))
            return interests, OK
        except Exception as e:
            return "Internal error", INTERNAL_ERROR
    
    else:
        return f"Unknown method: {method_name}", BAD_REQUEST    
    


class MainHTTPHandler(BaseHTTPRequestHandler):
    router: dict[str, Callable] = {"method": method_handler}

    def get_request_id(self, headers: Message[str, str]) -> str:
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
