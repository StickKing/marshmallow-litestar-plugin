from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from litestar.openapi.spec import Schema
from litestar.plugins import InitPlugin
from litestar.plugins import OpenAPISchemaPlugin
from marshmallow.schema import SchemaMeta

from marshmallow_litestar_plugin.utils import get_schema_info


if TYPE_CHECKING:
    from litestar._openapi.schema_generation.schema import SchemaCreator
    from litestar.config.app import AppConfig
    from litestar.typing import FieldDefinition


__all__ = (
    "MarshmallowPlugin",
)


class MarshmallowSchemaPlugin(OpenAPISchemaPlugin):
    __slots__ = ("field_requared_for_json_schema",)

    def __init__(
        self,
        *,
        field_requared_for_json_schema: bool = False,
    ) -> None:
        self.field_requared_for_json_schema = field_requared_for_json_schema

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
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
        schema_info = get_schema_info(
            field_definition.annotation,
            field_requared_for_json_schema=self.field_requared_for_json_schema,
        )
        return schema_creator.create_component_schema(
            field_definition,
            required=sorted(schema_info["requared_fields"]),
            property_fields=schema_info["field_definitions"],
            title="Test",
            # examples=None if model_info.example is None else [model_info.example],
        )


class MarshmallowPlugin(InitPlugin):
    """A plugin that provides marshmallow integration."""

    __slots__ = ("field_requared_for_json_schema",)

    def __init__(
        self,
        *,
        field_requared_for_json_schema: bool = False,
    ) -> None:
        self.field_requared_for_json_schema = field_requared_for_json_schema

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.plugins.extend(
            [
                MarshmallowSchemaPlugin(
                    field_requared_for_json_schema=self.field_requared_for_json_schema,
                ),
            ]
        )
        return app_config
