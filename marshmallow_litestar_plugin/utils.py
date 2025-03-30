
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, TypedDict, Tuple
from marshmallow import Schema, fields
from marshmallow import missing
from litestar.types import Empty
from litestar.typing import FieldDefinition
from ipaddress import IPv4Address, IPv6Address
from ipaddress import IPv4Interface, IPv6Interface
from pathlib import Path


if TYPE_CHECKING:

    class SchemaInfo(TypedDict):
        """Schema fields info."""

        schema_fields: dict[str, fields.Field]
        field_definitions: dict[str, FieldDefinition]
        requared_fields: list[str]
        exclude_fields: set[str]


TYPE_MAPPING = {
    **{
        value: key
        for key, value in Schema.TYPE_MAPPING.items()
    },
    fields.IP: IPv4Address | IPv6Address,
    fields.IPv4: IPv4Address,
    fields.IPv6: IPv6Address,
    fields.IPv4Interface: IPv4Interface,
    fields.IPv6Interface: IPv6Interface,
    fields.IPInterface: IPv4Interface | IPv6Interface,
    fields.List: list,
    fields.Tuple: tuple,
    fields.Url: Path,
    fields.NaiveDateTime: datetime,
    fields.Number: float,
    fields.Email: str,
    fields.Dict: dict,
    fields.Mapping: dict,
    fields.Raw: None,
    fields.Enum: Enum,
    fields.Nested: dict,
    fields.AwareDateTime: datetime,
    fields.Method: None,
}


class FieldPreparator:

    __slots__ = ("field_preparetion",)

    def __init__(self) -> None:
        self.field_preparetion = {
            fields.Enum: lambda field: field.enum,
            fields.Nested: self._get_nested_field_type,
            fields.List: self._get_list_field_type,
            fields.Dict: self._get_mapping_field_type,
            fields.Mapping: self._get_mapping_field_type,
            fields.Tuple: self._get_tuple_field_type,
            # fields.Method: self._get_method_field_type,
        }

    # def _get_method_field_type(self, field: fields.Method):
    #     logging.error("method")
    #     method = getattr(field, field.serialize_method_name)
    #     logging.error(method.__annotations__)
    #     return None

    def _get_tuple_field_type(self, field: fields.Tuple):
        tuple_fields = [
            self(i)
            for i in field.tuple_fields
        ]
        return tuple
        return Tuple[tuple_fields]

    def _get_mapping_field_type(self, field: fields.Dict | fields.Mapping):
        if field.key_field and field.value_field:
            key_type = self(field.key_field)
            value_type = self(field.value_field)
            return dict[key_type, value_type]
        return dict

    def _get_nested_field_type(self, field: fields.Nested):
        field_nested = field.nested
        if callable(field_nested):
            field_nested = field_nested()
        return field_nested

    def _check_optional(self, field: fields.Field, field_python_type: type):
        if field.allow_none:
            field_python_type = Optional[field_python_type]
        return field_python_type

    def _get_list_field_type(self, field: fields.List):
        field_inner = field.inner
        if callable(field_inner):
            field_inner = field_inner()
        if field_inner.__class__ is fields.Nested:
            field_python_type = type(self._get_nested_field_type(field_inner))
        else:
            field_python_type = self(field_inner)
        return List[field_python_type]

    def __call__(self, field: fields.Field):
        """Get python field type."""
        if callable(field):
            field = field()
        field_python_type = TYPE_MAPPING[field.__class__]

        prepare_func = self.field_preparetion.get(field.__class__)
        if prepare_func is not None:
            return prepare_func(field)

        return self._check_optional(field, field_python_type)


def get_schema_info(schema: Schema) -> SchemaInfo:
    """Get marshmallow schema info about fields."""
    schema_fields = schema._declared_fields
    field_definitions = {}
    exclude_fields = getattr(schema.Meta, "exclude", [])
    requared_fields = []

    field_preparator = FieldPreparator()

    for name, field in schema_fields.items():
        field_python_type = field_preparator(field)

        field_definitions[name] = FieldDefinition.from_annotation(
            raw=field_python_type,
            annotation=field_python_type,
            name=name,
            default=Empty,
            # default=field.dump_default if hasattr(field, "dump_default") and field.dump_default is not missing else Empty,
        )
        requared_fields.append(name)

    return {
        "schema_fields": schema_fields,
        "field_definitions": field_definitions,
        "requared_fields": requared_fields,
        "exclude_fields": exclude_fields,
    }
