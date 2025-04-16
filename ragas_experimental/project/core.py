"""Use this class to represent the AI project that we are working on and to interact with datasets and experiments in it."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/project/core.ipynb.

# %% auto 0
__all__ = ['Project', 'create_dataset_columns']

# %% ../../nbs/project/core.ipynb 4
import typing as t
import os
import asyncio

from fastcore.utils import patch
from pydantic import BaseModel

from ..backends.factory import RagasApiClientFactory
from ..backends.ragas_api_client import RagasApiClient
import ragas_experimental.typing as rt
from ..utils import async_to_sync, create_nano_id
from ..dataset import Dataset
from ..experiment import Experiment

# %% ../../nbs/project/core.ipynb 5
class Project:
    def __init__(
        self,
        project_id: str,
        ragas_app_client: t.Optional[RagasApiClient] = None,
    ):
        self.project_id = project_id
        if ragas_app_client is None:
            self._ragas_api_client = RagasApiClientFactory.create()
        else:
            self._ragas_api_client = ragas_app_client

        # create the project
        try:
            sync_version = async_to_sync(self._ragas_api_client.get_project)
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
        sync_version = async_to_sync(self._ragas_api_client.delete_project)
        sync_version(project_id=self.project_id)
        print("Project deleted!")

    def __repr__(self):
        return f"Project(name='{self.name}')"

# %% ../../nbs/project/core.ipynb 8
@patch(cls_method=True)
def get(cls: Project, name: str, ragas_app_client: t.Optional[RagasApiClient] = None) -> Project:
    """Get an existing project by name."""
    # Search for project with given name
    if ragas_app_client is None:
        ragas_app_client = RagasApiClientFactory.create()

    # get the project by name
    sync_version = async_to_sync(ragas_app_client.get_project_by_name)
    project_info = sync_version(
        project_name=name
    )

    # Return Project instance
    return Project(
        project_id=project_info["id"],
        ragas_app_client=ragas_app_client,
    )

# %% ../../nbs/project/core.ipynb 12
async def create_dataset_columns(project_id, dataset_id, columns, create_dataset_column_func):
    tasks = []
    for column in columns:
        tasks.append(create_dataset_column_func(
            project_id=project_id,
            dataset_id=dataset_id,
            id=create_nano_id(),
            name=column["name"],
            type=column["type"],
            settings={
                "max_length": 255,
                "is_required": True,
            },
        ))
    return await asyncio.gather(*tasks)


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
    sync_version = async_to_sync(self._ragas_api_client.create_dataset)
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
        create_dataset_column_func=self._ragas_api_client.create_dataset_column,
    )
        
    # Return a new Dataset instance
    return Dataset(
        name=name if name is not None else model.__name__,
        model=model,
        project_id=self.project_id,
        dataset_id=dataset_info["id"],
        ragas_api_client=self._ragas_api_client,
    )

# %% ../../nbs/project/core.ipynb 17
@patch
def get_dataset_by_id(self: Project, dataset_id: str, model) -> Dataset:
    """Get an existing dataset by name."""
    # Search for database with given name
    sync_version = async_to_sync(self._ragas_api_client.get_dataset)
    dataset_info = sync_version(
        project_id=self.project_id,
        dataset_id=dataset_id
    )

    # For now, return Dataset without model type
    return Dataset(
        name=dataset_info["name"],
        model=model,
        project_id=self.project_id,
        dataset_id=dataset_id,
        ragas_api_client=self._ragas_api_client,
    )

# %% ../../nbs/project/core.ipynb 19
@patch
def get_dataset(self: Project, dataset_name: str, model) -> Dataset:
    """Get an existing dataset by name."""
    # Search for dataset with given name
    sync_version = async_to_sync(self._ragas_api_client.get_dataset_by_name)
    dataset_info = sync_version(
        project_id=self.project_id,
        dataset_name=dataset_name
    )

    # Return Dataset instance
    return Dataset(
        name=dataset_info["name"],
        model=model,
        project_id=self.project_id,
        dataset_id=dataset_info["id"],
        ragas_api_client=self._ragas_api_client,
    )
