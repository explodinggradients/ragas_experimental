"""Use this class to represent the AI project that we are working on and to interact with datasets and experiments in it."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/project/core.ipynb.

# %% auto 0
__all__ = ['Project']

# %% ../../nbs/project/core.ipynb 3
import typing as t
import os

from notion_client import Client as NotionClient
from fastcore.utils import patch

from ..backends.notion_backend import NotionBackend
from ..backends.factory import NotionBackendFactory
from ..model.notion_model import NotionModel
import ragas_annotator.model.notion_typing as nmt
from ..dataset import Dataset
from ..experiment import Experiment

# %% ../../nbs/project/core.ipynb 4
class Project:
    def __init__(
        self,
        name: str,
        notion_backend: t.Optional[NotionBackend] = None,
        notion_api_key: t.Optional[str] = None,
        notion_root_page_id: t.Optional[str] = None,
    ):
        self.name = name
        self.datasets_page_id = ""
        self.experiments_page_id = ""
        self.comparisons_page_id = ""

        if notion_backend is None:
            # check that the environment variables are set
            notion_api_key = os.getenv("NOTION_API_KEY") or notion_api_key
            notion_root_page_id = (
                os.getenv("NOTION_ROOT_PAGE_ID") or notion_root_page_id
            )

            if notion_api_key is None:
                raise ValueError("NOTION_API_KEY is not set")

            if notion_root_page_id is None:
                raise ValueError("NOTION_ROOT_PAGE_ID is not set")

            if notion_api_key == "TEST":
                self._notion_backend = NotionBackendFactory.create(
                    root_page_id=notion_root_page_id,
                    use_mock=True,
                    initialize_project=True,
                )
            else:
                self._notion_backend = NotionBackend(
                    notion_client=NotionClient(auth=notion_api_key),
                    root_page_id=notion_root_page_id,
                )
        else:
            self._notion_backend = notion_backend

        # initialize the project structure
        self.initialize()

    def initialize(self):
        """Initialize the project structure in Notion."""
        root_page_id = self._notion_backend.root_page_id

        # if page doesn't exist, create it
        if not self._notion_backend.page_exists(root_page_id):
            raise ValueError(f"Root page '{root_page_id}' does not exist")
        # if page exists, but structure is invalid
        elif not self._notion_backend.validate_project_structure(root_page_id):
            # create the missing pages
            print(f"Creating missing pages inside root page '{root_page_id}'")
            self._create_project_structure(root_page_id)
        else:
            # if page exists and structure is valid, get the page ids
            # for datasets, experiments, and comparisons
            self.datasets_page_id = self._notion_backend.get_page_id(
                root_page_id, "Datasets"
            )
            self.experiments_page_id = self._notion_backend.get_page_id(
                root_page_id, "Experiments"
            )
            self.comparisons_page_id = self._notion_backend.get_page_id(
                root_page_id, "Comparisons"
            )

    def _create_project_structure(self, root_page_id: str):
        """Create the basic project structure with required pages."""
        # Create each required page
        self.datasets_page_id = self._notion_backend.create_new_page(
            root_page_id, "Datasets"
        )
        self.experiments_page_id = self._notion_backend.create_new_page(
            root_page_id, "Experiments"
        )
        self.comparisons_page_id = self._notion_backend.create_new_page(
            root_page_id, "Comparisons"
        )

    def __repr__(self):
        return f"Project(name='{self.name}', root_page_id={self._notion_backend.root_page_id})"

# %% ../../nbs/project/core.ipynb 9
@patch
def create_dataset(
    self: Project, model: t.Type[NotionModel], name: t.Optional[str] = None
) -> Dataset:
    """Create a new dataset database.

    Args:
        name (str): Name of the dataset
        model (NotionModel): Model class defining the database structure

    Returns:
        Dataset: A new dataset object for managing entries
    """
    # Collect all properties from model fields
    properties = {}
    has_title = False
    for field_name, field in model._fields.items():
        properties.update(field._to_notion_property())
        if isinstance(field, nmt.Title):  # Check if we have a title field
            has_title = True

    if not has_title:
        raise ValueError(
            "In order to create a dataset, the model must have a nmt.Title field"
        )

    # Create the database
    if self.datasets_page_id == "":
        raise ValueError("Datasets page ID is not set")
    database_id = self._notion_backend.create_new_database(
        parent_page_id=self.datasets_page_id,
        title=name if name is not None else model.__name__,
        properties=properties,
    )

    # Return a new Dataset instance
    return Dataset(
        name=name if name is not None else model.__name__,
        model=model,
        database_id=database_id,
        notion_backend=self._notion_backend,
    )

# %% ../../nbs/project/core.ipynb 12
@patch
def get_dataset(self: Project, name: str, model: t.Type[NotionModel]) -> Dataset:
    """Get an existing dataset by name."""
    if self.datasets_page_id == "":
        raise ValueError("Datasets page ID is not set")

    # Search for database with given name
    database_id = self._notion_backend.get_database_id(
        parent_page_id=self.datasets_page_id, name=name, return_multiple=False
    )

    # For now, return Dataset without model type
    return Dataset(
        name=name,
        model=model,
        database_id=database_id,
        notion_backend=self._notion_backend,
    )
