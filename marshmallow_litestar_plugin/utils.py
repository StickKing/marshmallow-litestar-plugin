
from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address
from ipaddress import IPv4Interface
from ipaddress import IPv6Address
from ipaddress import IPv6Interface
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import List
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypedDict
from typing import Union

from litestar.types import Empty
from litestar.typing import FieldDefinition
from marshmallow import Schema
from marshmallow import fields
from marshmallow.base import SchemaABC


if TYPE_CHECKING:
    # from marshmallow.base import SchemaABC

    class SchemaInfo(TypedDict):
        """Schema fields info."""

        schema_fields: dict[str, fields.Field]
        field_definitions: dict[str, FieldDefinition]
        requared_fields: list[str]
        # excluded_fields: set[str]


TYPE_MAPPING = {
    **{
        value: key
        for key, value in Schema.TYPE_MAPPING.items()
    },
    fields.IP: Union[IPv4Address, IPv6Address],
    fields.IPv4: IPv4Address,
    fields.IPv6: IPv6Address,
    fields.IPv4Interface: IPv4Interface,
    fields.IPv6Interface: IPv6Interface,
    fields.IPInterface: Union[IPv4Interface, IPv6Interface],
    fields.List: list,
    fields.Url: Path,
    fields.NaiveDateTime: datetime,
    fields.Number: float,
    fields.Email: str,
    fields.AwareDateTime: datetime,
    fields.Raw: None,
    fields.Method: None,
    fields.Enum: None,
    fields.Nested: None,
    fields.List: None,
    fields.Dict: None,
    fields.Mapping: None,
    fields.Tuple: None,
}


class FieldMapper:

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

    def _get_tuple_field_type(self, field: fields.Tuple) -> type[tuple]:
        """Processing ma_fields.Tuple.

        Args:
            field: ma_fields.Tuple field

        Returns:
            python tuple type
        """
        tuple_fields = [
            self(i)
            for i in field.tuple_fields
        ]
        return Tuple.copy_with(tuple(tuple_fields))

    def _get_mapping_field_type(
        self,
        field: fields.Dict | fields.Mapping,
    ) -> Type[dict[Any, Any]] | Type[dict]:
        """Processing ma_fields.Mapping or ma_fields.Dict.

        Args:
            field: ma_fields.Mapping or ma_fields.Dict

        Returns:
            python mapping type
        """
        if field.key_field and field.value_field:
            key_type = self(field.key_field)
            value_type = self(field.value_field)
            return Dict[key_type, value_type]
        return dict

    def _get_nested_field_type(self, field: fields.Nested) -> type[SchemaABC]:
        """Processing ma_fields.Nested.

        Args:
            field: ma_fields.Nested

        Returns:
            marshmallow schema obj
        """
        schema = field.nested
        if callable(schema):
            return schema
        return schema.__class__

    def _check_optional(
        self,
        field: fields.Field,
        field_python_type: type,
    ) -> type | Type[None]:
        """Check optional field

        Args:
            field: marshmallow Field obj
            field_python_type: python type obj

        Returns:
            python type
        """
        if field.allow_none:
            field_python_type = Optional[field_python_type]
        return field_python_type

    def _get_list_field_type(self, field: fields.List) -> type[list]:
        """Processing ma_fields.List.

        Args:
            field: ma_fields.List

        Returns:
            python list type
        """
        field_inner = field.inner
        if callable(field_inner):
            field_inner = field_inner()
        if field_inner.__class__ is fields.Nested:
            field_python_type = self._get_nested_field_type(field_inner)
        else:
            field_python_type = self(field_inner)
        return List[field_python_type]

    def _check_base_ma_field(
        self,
        field_cls: Type[fields.Field],
    ) -> fields.Field:
        """
        Сheck whether the field is custom or a base field.
        If it's custom, we determine its first ma parent.
        """
        if field_cls in TYPE_MAPPING.keys():
            return field_cls

        for cls in field_cls.__bases__:
            if cls in TYPE_MAPPING.keys():
                return cls
            if issubclass(cls, fields.Field):
                return self._check_base_ma_field(cls)

        return fields.Raw

    def __call__(self, field: fields.Field) -> type:
        """Сonvert marshmallow field to python types.

        Args:
            field: marshmallow field

        Returns:
            python type
        """
        if callable(field):
            field = field()

        base_field_cls = self._check_base_ma_field(field.__class__)

        prepare_func = self.field_preparetion.get(base_field_cls)
        if prepare_func is not None:
            return prepare_func(field)

        field_python_type = TYPE_MAPPING[base_field_cls]

        return self._check_optional(field, field_python_type)


def get_excluded_fields(schema: type[Schema]) -> set[str]:
    """Summary excluded Meta fields name.

    Args:
        schema: marshmellow schemas cls

    Returns:
        set with excluded field names
    """
    if hasattr(schema.Meta, "exclude"):
        excluded_fields = set(schema.Meta.exclude)
        for cls in schema.__bases__:
            if issubclass(cls, SchemaABC):
                excluded_fields.update(get_excluded_fields(cls))
        return excluded_fields
    return set()


def get_schema_info(
    schema: Schema,
    *,
    use_field_requared=False,
    remove_excluded_fields=True,
) -> SchemaInfo:
    """Get marshmallow schema info about fields."""
    excluded_fields = set()
    if remove_excluded_fields:
        excluded_fields = get_excluded_fields(schema)

    schema_fields = schema._declared_fields
    field_definitions = {}
    requared_fields = []

    field_preparator = FieldMapper()

    for name, field in schema_fields.items():
        if name in excluded_fields:
            continue

        if callable(field):
            field = field()

        field_python_type = field_preparator(field)

        field_definitions[name] = FieldDefinition.from_annotation(
            raw=field_python_type,
            annotation=field_python_type,
            name=name,
            default=Empty,
            # default=field.dump_default if hasattr(field, "dump_default")
            # and field.dump_default is not missing else Empty,
        )

        if use_field_requared:
            if field.required:
                requared_fields.append(name)
        else:
            requared_fields.append(name)

    return {
        "schema_fields": schema_fields,
        "field_definitions": field_definitions,
        "requared_fields": requared_fields,
        # "excluded_fields": excluded_fields,
    }
