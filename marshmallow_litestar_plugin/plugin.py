from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from litestar.openapi.spec import Schema
from litestar.plugins import OpenAPISchemaPlugin
from litestar.plugins import SerializationPlugin
from litestar.types import Empty
from litestar.typing import FieldDefinition
from marshmallow.base import SchemaABC
from marshmallow.schema import SchemaMeta

from marshmallow_litestar_plugin.utils import get_schema_info

from .dto import MarshmallowDTO


if TYPE_CHECKING:
    from litestar._openapi.schema_generation.schema import SchemaCreator
    from litestar.dto import AbstractDTO


__all__ = (
    "MarshmallowSchemaPlugin",
)


class MarshmallowSchemaPlugin(OpenAPISchemaPlugin):
    __slots__ = (
        "use_field_requared",
        "remove_excluded_fields",
    )

    def __init__(
        self,
        *,
        use_field_requared: bool = False,
        remove_excluded_fields: bool = False
    ) -> None:
        """Initialize plugin

        Args:
            use_field_requared: if you want to use the
            required flag from marshmallow fields.
            remove_excluded_fields: if you want to remove excluded (in Meta)
            fields from json schema.
        """
        self.use_field_requared = use_field_requared
        self.remove_excluded_fields = remove_excluded_fields

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        if hasattr(value, "_name") and value._name == "MarshmallowJsonType":
            return True
        return (
            isinstance(value, SchemaMeta) or
            issubclass(value.__class__, SchemaMeta)
        )

    @staticmethod
    def is_undefined_sentinel(value: Any) -> bool:
        return False

    @staticmethod
    def is_constrained_field(field_definition: FieldDefinition) -> bool:
        return False

    def to_openapi_schema(
        self,
        field_definition: FieldDefinition,
        schema_creator: SchemaCreator,
    ) -> Schema:
        """Given a type annotation, transform it into an OpenAPI schema class.

        Args:
            field_definition: FieldDefinition instance.
            schema_creator: An instance of the schema creator class

        Returns:
            An :class:`OpenAPI <litestar.openapi.spec.schema.Schema>` instance.
        """
        if hasattr(field_definition.raw, "__metadata__"):
            field_definition = FieldDefinition.from_annotation(
                raw=field_definition.metadata[0],
                annotation=field_definition.metadata[0],
                name="",
                default=Empty,
                # default=field.dump_default if hasattr(field, "dump_default")
                # and field.dump_default is not missing else Empty,
            )
        schema_info = get_schema_info(
            field_definition.annotation,
            use_field_requared=self.use_field_requared,
        )

        return schema_creator.create_component_schema(
            field_definition,
            required=sorted(schema_info["requared_fields"]),
            property_fields=schema_info["field_definitions"],
            title="",
            # examples=None if model_info.example is
            # None else [model_info.example],
        )


class MarshmallowSerialization(SerializationPlugin):
    """Support for domain modelling with Marshmallow."""

    def supports_type(self, field_definition: FieldDefinition) -> bool:
        """Given a value of indeterminate type,
        determine if this value is supported by the plugin.

        Args:
            field_definition: A parsed type.

        Returns:
            Whether the type is supported by the plugin.
        """
        metadata = field_definition.metadata
        return metadata and issubclass(metadata[0], SchemaABC)

    def create_dto_for_type(
        self,
        field_definition: FieldDefinition,
    ) -> type[AbstractDTO]:
        """Given a parsed type, create a DTO class.

        Args:
            field_definition: A parsed type.

        Returns:
            A DTO class.
        """
        return MarshmallowDTO[field_definition.metadata[0]]
