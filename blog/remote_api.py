from collections.abc import Iterable

import httpx
from django.db import models
from rest_framework.serializers import BaseSerializer


class RemoteAPIError(Exception):
    pass


class JSONAPIClient:
    CONTENT_TYPE_JSON = {"Content-type": "application/json; charset=UTF-8"}

    def __init__(
        self, client: httpx.Client, base_url: str, headers: dict[str, str] | None = None
    ) -> None:
        self.base_url = base_url
        self.client = client
        self.headers = headers or {}
        self.headers.update(self.CONTENT_TYPE_JSON)

    def get_detail_url(self, pk: int) -> str:
        return f"{self.base_url.rstrip('/')}/{pk}"

    def retrieve(self, pk: int) -> dict:
        url = self.get_detail_url(pk)
        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def retrieve_list(self) -> list[dict]:
        response = self.client.get(self.base_url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def update(self, pk: int, data: dict) -> dict:
        url = self.get_detail_url(pk)
        response = self.client.put(url, json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def create(self, data: dict) -> dict:
        response = self.client.post(self.base_url, json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def delete(self, pk: int) -> None:
        url = self.get_detail_url(pk)
        response = self.client.delete(url, headers=self.headers)
        response.raise_for_status()


class RemoteModelAPI:
    def __init__(
        self,
        client: JSONAPIClient,
        model_name: str,
        serializer: type[BaseSerializer[models.Model]],
    ) -> None:
        self.client = client
        self.model_name = model_name
        self.serializer = serializer

    def serialize_object(self, obj: models.Model) -> dict:
        return self.serializer(obj).data

    def get_initial_data(self) -> list[models.Model]:
        instances: list[models.Model] = []
        try:
            data = self.client.retrieve_list()
            serializer = self.serializer(data=data, many=True)
            if serializer.is_valid():
                instances = serializer.save()  # type: ignore[assignment]
            else:
                error_msg = f"Error loading {self.model_name}: {serializer.errors!r}."
                raise RemoteAPIError(error_msg)
        except httpx.HTTPError as exc:
            error_msg = f"An error occurred while requesting {exc.request.url!r}: {exc}"
            raise RemoteAPIError(error_msg) from exc
        return instances

    def sync_created(
        self, objects: Iterable[models.Model]
    ) -> tuple[list[models.Model], list[tuple[models.Model, Exception]]]:
        return self._sync("create", objects)

    def sync_updated(
        self, objects: Iterable[models.Model]
    ) -> tuple[list[models.Model], list[tuple[models.Model, Exception]]]:
        return self._sync("update", objects)

    def sync_deleted(
        self, objects: Iterable[models.Model]
    ) -> tuple[list[models.Model], list[tuple[models.Model, Exception]]]:
        return self._sync("delete", objects)

    def _sync(
        self, method: str, objects: Iterable[models.Model]
    ) -> tuple[list[models.Model], list[tuple[models.Model, Exception]]]:
        errors: list[tuple[models.Model, Exception]] = []
        synced_models: list[models.Model] = []
        for obj in objects:
            try:
                match method:
                    case "delete":
                        self.client.delete(obj.pk)
                    case "create":
                        data = self.serialize_object(obj)
                        self.client.create(data)
                    case "update":
                        data = self.serialize_object(obj)
                        self.client.update(obj.pk, data)
                    case _:
                        error_msg = (
                            f"Error syncronazing {self.model_name}: "
                            f"{method} is not a valid method name"
                        )
                        raise RemoteAPIError(error_msg)
                synced_models.append(obj)
            except httpx.HTTPError as exc:
                errors.append((obj, exc))
        return synced_models, errors
