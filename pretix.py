from copy import deepcopy
from dataclasses import dataclass, InitVar
from datetime import datetime
from typing import Optional, Any, Callable, ClassVar


@dataclass(frozen=True)
class PretixObject:
    """
    Any complex type from a pretix OrderJson
    """
    
    @classmethod
    def field_parser(cls) -> dict[str: Callable]:
        """
        dict of input field name type-coersing function. 
        Override in subclasses for from_dict magic
        """
        return {}

    @classmethod
    def from_dict(cls, input: dict[str: Any]):
        """
        Given a dict, make an instance of this class
        """
        obj = deepcopy(input)
        for field, func in cls.field_parser().items():
            if (value := obj.get(field)) is not None:
                obj[field] = func(value)
        return cls(**obj)

    @classmethod
    def from_list(cls, input: list[dict[str, Any]]):
        """
        Given a list of dicts, make a list of instances of this class
        """
        return [cls.from_dict(x) for x in input]


@dataclass(frozen=True)
class RegisteredPretixObject(PretixObject):
    """
    RegisteredPretixObject allows tracking instances of a PretixObject.
    Whenever a new object is created, it is added by id to a class variable
    This allows searching for objects by id
    """
    pretix_registry: ClassVar[dict[type, dict[int, 'RegisteredPretixObject']]] = {}
    pretix_registry_instance_key: ClassVar[str]

    @classmethod
    def get_registry(cls):
        cls.pretix_registry[cls] = cls.pretix_registry.get(cls, {})
        return cls.pretix_registry[cls]

    @classmethod
    def find(cls, key):
        return cls.get_registry().get(key)

    def __post_init__(self):
        self.get_registry()[getattr(self, self.pretix_registry_instance_key)] = self



@dataclass(frozen=True)
class Category(RegisteredPretixObject):
    pretix_registry_instance_key: ClassVar[str] = "id"
    id: int
    name: str
    description: str
    position: int
    internal_name: Optional[str]


@dataclass(frozen=True)
class ItemVariation(RegisteredPretixObject):
    pretix_registry_instance_key: ClassVar[str] = "id"
    id: int
    active: bool
    price: float
    name: str
    description: str
    position: int
    checkin_attention: bool
    checkin_text: str
    require_approval: bool
    require_membership: bool
    sales_channels: list[str]
    available_from: Optional[datetime]
    available_until: Optional[datetime]
    hide_without_voucher: bool
    meta_data: dict

    @classmethod
    def field_parser(cls):
        return dict(
            available_from = datetime.fromisoformat,
            available_until = datetime.fromisoformat
        )

@dataclass(frozen=True)
class Item(RegisteredPretixObject):
    pretix_registry_instance_key: ClassVar[str] = "id"
    id: int
    position: int
    name: str
    internal_name: Optional[str]
    category: Category
    price: float
    tax_rate: float
    tax_name: str
    admission: bool
    personalized: bool
    active: bool
    sales_channels: list[str]
    description: str
    available_from: Optional[datetime]
    available_until: Optional[datetime]
    require_voucher: bool
    hide_without_voucher: bool
    allow_cancel: bool
    require_bundling: bool
    min_per_order: Optional[int]
    max_per_order: Optional[int]
    checkin_attention: bool
    checkin_text: str
    original_price: Optional[float]
    issue_giftcard: bool
    meta_data: dict
    require_membership: bool
    variations: list[ItemVariation]

    @classmethod
    def field_parser(cls):
        return dict(
            available_from = datetime.fromisoformat,
            available_until = datetime.fromisoformat,
            variations = ItemVariation.from_list,
            category = Category.find
        )

@dataclass(frozen=True)
class Question(RegisteredPretixObject):
    pretix_registry_instance_key: ClassVar[str] = "id"
    id: int
    identifier: str
    required: bool
    question: str
    position: int
    hidden: bool
    ask_during_checkin: bool
    help_text: str
    type: str


@dataclass(frozen=True)
class Answer(PretixObject):
    question: Question
    answer: Optional[str]

    @classmethod
    def field_parser(cls):
        return {
            "question": Question.find
        }

@dataclass(frozen=True)
class OrderPosition(RegisteredPretixObject):
    pretix_registry_instance_key: ClassVar[str] = "id"
    id: int
    positionid: int
    item: Item
    variation: Optional[ItemVariation]
    subevent: Optional['Event']
    seat: Optional[Any] # idk
    price: float
    tax_rate: float
    tax_value: float
    attendee_name: str
    attendee_email: str
    company: Optional[str]
    street: Optional[str]
    zipcode: Optional[str]
    country: Optional[str]
    state: Optional[str]
    secret: str
    addon_to: Optional['OrderPosition']
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    blocked: Optional[Any] # idk
    answers: list[Answer]

    @classmethod
    def field_parser(cls):
        return {
            "valid_from": datetime.fromisoformat,
            "valid_until": datetime.fromisoformat, 
            "answers": Answer.from_list,
            "item": Item.find,
            "addon_to": OrderPosition.find
        }


@dataclass(frozen=True)
class Order(RegisteredPretixObject):
    pretix_registry_instance_key: ClassVar = "code"

    code: str
    status: str
    customer: Optional[str]
    testmode: bool
    user: str
    email: str
    phone: str
    locale: str
    comment: str
    custom_followup_at: Optional[datetime]
    require_approval: bool
    checkin_attention: bool
    checkin_text: bool
    sales_channel: str
    expires: datetime
    datetime: datetime
    fees: list[float]
    total: float
    positions: list[OrderPosition]

    @classmethod
    def field_parser(cls):
        return {
            "custom_followup_at": datetime.fromisoformat, 
            "positions": OrderPosition.from_list
        }


@dataclass(frozen=True)
class Event(PretixObject):
    name: str
    slug: str
    organizer: dict[str, str]
    meta_data: dict
    categories: list[Category]
    items: list[Item]
    questions: list[Question]
    orders: list[Order]
    quotas: list[dict] # TODO: make quotas, make sure to update field_parser when you do
    subevents: list # idk

    @classmethod
    def field_parser(cls):
        return {
            "categories": Category.from_list,
            "items": Item.from_list,
            "questions": Question.from_list,
            "orders": Order.from_list
        }
