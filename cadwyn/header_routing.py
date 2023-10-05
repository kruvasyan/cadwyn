from types import ModuleType

from fastapi import APIRouter
from fastapi_header_versioning.fastapi import HeaderVersionedAPIRouter

from cadwyn.routing import generate_all_router_versions
from cadwyn.structure import VersionBundle


def get_versioned_router(
    *routers: APIRouter,
    versions: VersionBundle,
    latest_schemas_module: ModuleType,
) -> HeaderVersionedAPIRouter:
    router_versions = generate_all_router_versions(
        *routers,
        versions=versions,
        latest_schemas_module=latest_schemas_module,
    )
    root_router = HeaderVersionedAPIRouter()

    for version, router in router_versions.items():
        root_router.include_router(router, version=str(version))

    return root_router