from __future__ import annotations

from dataclasses import replace
from typing import Any
from typing import Collection
from typing import Generator
from typing import Generic
from typing import TypeVar

from litestar.dto.base_dto import AbstractDTO
from litestar.dto.data_structures import DTOFieldDefinition
from litestar.dto.field import extract_dto_field
from litestar.exceptions import ValidationException
from litestar.types.empty import Empty
from litestar.typing import FieldDefinition
from marshmallow.base import SchemaABC
from marshmallow.exceptions import ValidationError

from .utils import get_schema_info


T = TypeVar("T", bound="SchemaABC | Collection[SchemaABC]")


class MarshmallowDTO(AbstractDTO[T], Generic[T]):
    """Support for domain modelling with Marshmallow."""

    def decode_builtins(self, value: dict[str, Any]) -> Any:
        try:
            return super().decode_builtins(value)
        except ValidationError as ex:
            raise ValidationException(extra=ex.messages) from ex

    def decode_bytes(self, value: bytes) -> Any:
        try:
            return super().decode_bytes(value)
        except ValidationError as ex:
            raise ValidationException(extra=ex.messages) from ex

    @classmethod
    def generate_field_definitions(
        cls,
        model_type: type[SchemaABC],
    ) -> Generator[DTOFieldDefinition, None, None]:
        model_info = get_schema_info(model_type)
        model_field_definitions = model_info["field_definitions"]

        for field_name, field_definition in model_field_definitions.items():
            # field_definition = downtype_for_data_transfer(field_definition)
            dto_field = extract_dto_field(
                field_definition,
                field_definition.extra,
            )

            default: Any = Empty
            default_factory: Any = None

            yield replace(
                DTOFieldDefinition.from_field_definition(
                    field_definition=field_definition,
                    dto_field=dto_field,
                    model_name=model_type.__name__,
                    default_factory=default_factory,
                    passthrough_constraints=False,
                ),
                default=default,
                name=field_name,
            )

    @classmethod
    def resolve_generic_wrapper_type(
        cls, field_definition: FieldDefinition
    ) -> tuple[FieldDefinition, FieldDefinition, str] | None:
        """Handle where DTO supported data is wrapped in
        a generic container type.

        Args:
            field_definition: A parsed type annotation
            that represents the annotation used to narrow the DTO type.

        Returns:
            The data model type.
        """
        field_definition = FieldDefinition.from_annotation(
            raw=field_definition.raw,
            annotation=field_definition.annotation,
            name=field_definition.name,
            default=Empty,
            origin=field_definition.annotation.__origin__,
            # default=field.dump_default if hasattr(field, "dump_default")
            # and field.dump_default is not missing else Empty,
        )

        if field_definition.origin and (
            inner_fields := [
                inner_field
                for inner_field in field_definition.inner_types
                if cls.resolve_model_type(
                    inner_field,
                   ).is_subclass_of(
                       cls.model_type,
                )
            ]
        ):
            inner_field = inner_fields[0]
            model_field_definition = cls.resolve_model_type(inner_field)

            for attr, attr_type in cls.get_model_type_hints(
                field_definition.origin
            ).items():
                if isinstance(attr_type.annotation, TypeVar) or any(
                    isinstance(t.annotation, TypeVar)
                    for t in attr_type.inner_types
                ):
                    if attr_type.is_non_string_collection:
                        # the inner type of the collection type is the type var, so we need to specialize the
                        # collection type with the DTO supported type.
                        specialized_annotation = attr_type.safe_generic_origin[
                            model_field_definition.annotation
                        ]
                        return model_field_definition, FieldDefinition.from_annotation(
                            specialized_annotation
                        ), attr
                    return model_field_definition, inner_field, attr
        return None

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        return field_definition.is_subclass_of(SchemaABC)
