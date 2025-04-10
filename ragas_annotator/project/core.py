"""Use this class to represent the AI project that we are working on and to interact with datasets and experiments in it."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/project/core.ipynb.

# %% auto 0
__all__ = ['async_to_sync', 'Project']

# %% ../../nbs/project/core.ipynb 4
import typing as t
import os
import asyncio
import functools

from fastcore.utils import patch
from pydantic import BaseModel

from ..backends.factory import RagasApiClientFactory
from ..backends.ragas_api_client import RagasApiClient
import ragas_annotator.typing as rt
from ..dataset import Dataset
from ..experiment import Experiment

# %% ../../nbs/project/core.ipynb 5
def async_to_sync(async_func):
    """Convert an async function to a sync function"""
    @functools.wraps(async_func)
    def sync_wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, async_func(*args, **kwargs))
                    return future.result()
            else:
                return loop.run_until_complete(async_func(*args, **kwargs))
        except RuntimeError:
            return asyncio.run(async_func(*args, **kwargs))
    return sync_wrapper

# %% ../../nbs/project/core.ipynb 6
class Project:
    def _create_ragas_app_client(self):
        if ragas_app_client is None:
            self._ragas_app_client = RagasApiClientFactory.create()
        else:
            self._ragas_app_client = ragas_app_client

    def __init__(
        self,
        project_id: str,
        ragas_app_client: t.Optional[RagasApiClient] = None,
    ):
        self.project_id = project_id
        if ragas_app_client is None:
            self._ragas_app_client = RagasApiClientFactory.create()
        else:
            self._ragas_app_client = ragas_app_client

        # create the project
        try:
            sync_version = async_to_sync(self._ragas_app_client.get_project)
            existing_project = sync_version(project_id=self.project_id)
            self.project_id = existing_project["id"]
            self.name = existing_project["title"]
            self.description = existing_project["description"]
        except Exception as e:
            raise e

    @classmethod
    def create(
        cls,
        name: str,
        description: str = "",
        ragas_app_client: t.Optional[RagasApiClient] = None,
    ):
        ragas_app_client = RagasApiClientFactory.create()
        sync_version = async_to_sync(ragas_app_client.create_project)
        new_project = sync_version(title=name, description=description)
        return cls(new_project["id"], ragas_app_client)

    def delete(self):
        sync_version = async_to_sync(self._ragas_app_client.delete_project)
        sync_version(project_id=self.project_id)
        print("Project deleted!")

    def __repr__(self):
        return f"Project(name='{self.name}')"

# %% ../../nbs/project/core.ipynb 13
@patch
def create_dataset(
    self: Project, model: t.Type[BaseModel], name: t.Optional[str] = None
) -> Dataset:
    """Create a new dataset database.

    Args:
        name (str): Name of the dataset
        model (NotionModel): Model class defining the database structure

    Returns:
        Dataset: A new dataset object for managing entries
    """
    # create the dataset
    sync_version = async_to_sync(self._ragas_app_client.create_dataset)
    dataset_info = sync_version(
        project_id=self.project_id,
        name=name if name is not None else model.__name__,
    )

    # create the columns for the dataset
    column_types = rt.ModelConverter.model_to_columns(model)
    sync_version = async_to_sync(create_dataset_columns)
    sync_version(
        project_id=self.project_id,
        dataset_id=dataset_info["id"],
        columns=column_types,
        create_dataset_column_func=self._ragas_app_client.create_dataset_column,
    )
        
    return
    # Return a new Dataset instance
    return Dataset(
        name=name if name is not None else model.__name__,
        model=model,
        database_id=database_id,
        notion_backend=self._ragas_app_client,
    )

# %% ../../nbs/project/core.ipynb 16
@patch
def get_dataset(self: Project, name: str, model) -> Dataset:
    """Get an existing dataset by name."""
    if self.datasets_page_id == "":
        raise ValueError("Datasets page ID is not set")

    # Search for database with given name
    database_id = self._ragas_app_client.get_database_id(
        parent_page_id=self.datasets_page_id, name=name, return_multiple=False
    )

    # For now, return Dataset without model type
    return Dataset(
        name=name,
        model=model,
        database_id=database_id,
        notion_backend=self._ragas_app_client,
    )
