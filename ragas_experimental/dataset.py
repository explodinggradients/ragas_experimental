"""A python list like object that contains your evaluation data."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/dataset.ipynb.

# %% auto 0
__all__ = ['BaseModelType', 'Dataset']

# %% ../nbs/dataset.ipynb 3
import typing as t

from fastcore.utils import patch

from .model.pydantic_model import ExtendedPydanticBaseModel as BaseModel
from .utils import create_nano_id, async_to_sync
from .backends.ragas_api_client import RagasApiClient

# %% ../nbs/dataset.ipynb 4
BaseModelType = t.TypeVar("BaseModelType", bound=BaseModel)

class Dataset(t.Generic[BaseModelType]):
    """A list-like interface for managing dataset entries with backend synchronization.
    
    This class behaves like a Python list while synchronizing operations with the
    Ragas backend API.
    """

    def __init__(
        self,
        name: str,
        model: t.Type[BaseModel],
        project_id: str,
        dataset_id: str,
        ragas_api_client: RagasApiClient,
    ):
        self.name = name
        self.model = model
        self.project_id = project_id
        self.dataset_id = dataset_id
        self._ragas_api_client = ragas_api_client
        self._entries: t.List[BaseModelType] = []

        # Initialize column mapping if it doesn't exist yet
        if not hasattr(self.model, "__column_mapping__"):
            self.model.__column_mapping__ = {}
            
        # Get column mappings from API and update the model's mapping
        column_id_map = self._get_column_id_map(dataset_id=dataset_id)
        
        # Update the model's column mapping with the values from the API
        for field_name, column_id in column_id_map.items():
            self.model.__column_mapping__[field_name] = column_id

    def _get_column_id_map(self: "Dataset", dataset_id: str) -> dict:
        """Get a map of column name to column id"""
        sync_func = async_to_sync(self._ragas_api_client.list_dataset_columns)
        columns = sync_func(project_id=self.project_id, dataset_id=dataset_id)
        column_id_map = {column["name"]: column["id"] for column in columns["items"]}

        # add the column id map to the model, selectively overwriting existing column mapping
        for field in self.model.__column_mapping__.keys():
            if field in column_id_map:
                self.model.__column_mapping__[field] = column_id_map[field]
        return column_id_map

    def __getitem__(
        self, key: t.Union[int, slice]
    ) -> t.Union[BaseModelType, "Dataset[BaseModelType]"]:
        """Get an entry by index or slice."""
        if isinstance(key, slice):
            new_dataset = type(self)(
                name=self.name,
                model=self.model,
                project_id=self.project_id,
                dataset_id=self.dataset_id,
                ragas_api_client=self._ragas_api_client,
            )
            new_dataset._entries = self._entries[key]
            return new_dataset
        else:
            return self._entries[key]

    def __setitem__(self, index: int, entry: BaseModelType) -> None:
        """Update an entry at the given index and sync to backend."""
        if not isinstance(entry, self.model):
            raise TypeError(f"Entry must be an instance of {self.model.__name__}")

        # Get existing entry to get its ID
        existing = self._entries[index]
        
        # Update in backend
        self.save(entry)
        
        # Update local cache
        self._entries[index] = entry

    def __repr__(self) -> str:
        return f"Dataset(name={self.name}, model={self.model.__name__}, len={len(self)})"

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> t.Iterator[BaseModelType]:
        return iter(self._entries)

# %% ../nbs/dataset.ipynb 16
import ragas_experimental.typing as rt

# %% ../nbs/dataset.ipynb 17
@patch
def append(self: Dataset, entry: BaseModelType) -> None:
    """Add a new entry to the dataset and sync to Notion."""
    # Create row inside the table

    # first get the columns for the dataset
    column_id_map = self.model.__column_mapping__

    # create the rows
    row_dict_converted = rt.ModelConverter.instance_to_row(entry)
    row_id = create_nano_id()
    row_data = {}
    for column in row_dict_converted["data"]:
        if column["column_id"] in column_id_map:
            row_data[column_id_map[column["column_id"]]] = column["data"]

    sync_func = async_to_sync(self._ragas_api_client.create_dataset_row)
    response = sync_func(
        project_id=self.project_id,
        dataset_id=self.dataset_id,
        id=row_id,
        data=row_data,
    )
    # add the row id to the entry
    entry._row_id = response["id"]
    # Update entry with Notion data (like ID)
    self._entries.append(entry)

# %% ../nbs/dataset.ipynb 20
@patch
def pop(self: Dataset, index: int = -1) -> BaseModelType:
    """Remove and return entry at index, sync deletion to Notion."""
    entry = self._entries[index]
    # get the row id
    row_id = entry._row_id
    if row_id is None:
        raise ValueError("Entry has no row id. This likely means it was not added or synced to the dataset.")

    # soft delete the row
    sync_func = async_to_sync(self._ragas_api_client.delete_dataset_row)
    sync_func(project_id=self.project_id, dataset_id=self.dataset_id, row_id=row_id)

    # Remove from local cache
    return self._entries.pop(index)

# %% ../nbs/dataset.ipynb 24
@patch
def load(self: Dataset) -> None:
    """Load all entries from the backend API."""
    # Get all rows
    sync_func = async_to_sync(self._ragas_api_client.list_dataset_rows)
    response = sync_func(
        project_id=self.project_id,
        dataset_id=self.dataset_id
    )
    
    # Get column mapping (ID -> name)
    column_map = {v: k for k, v in self.model.__column_mapping__.items()}
    
    # Clear existing entries
    self._entries.clear()
    
    # Process rows
    for row in response.get("items", []):
        model_data = {}
        row_id = row.get("id")
        
        # Convert from API data format to model fields
        for col_id, value in row.get("data", {}).items():
            if col_id in column_map:
                field_name = column_map[col_id]
                model_data[field_name] = value
        
        # Create model instance
        entry = self.model(**model_data)
        
        # Store row ID for future operations
        entry._row_id = row_id
        
        self._entries.append(entry)

# %% ../nbs/dataset.ipynb 26
@patch
def load_as_dicts(self: Dataset) -> t.List[t.Dict]:
    """Load all entries as dictionaries."""
    # Get all rows
    sync_func = async_to_sync(self._ragas_api_client.list_dataset_rows)
    response = sync_func(
        project_id=self.project_id,
        dataset_id=self.dataset_id
    )
    
    # Get column mapping (ID -> name)
    column_map = {v: k for k, v in self.model.__column_mapping__.items()}
    
    # Convert to dicts with field names
    result = []
    for row in response.get("items", []):
        item_dict = {}
        for col_id, value in row.get("data", {}).items():
            if col_id in column_map:
                field_name = column_map[col_id]
                item_dict[field_name] = value
        result.append(item_dict)
    
    return result

# %% ../nbs/dataset.ipynb 28
@patch
def to_pandas(self: Dataset) -> "pd.DataFrame":
    """Convert dataset to pandas DataFrame."""
    import pandas as pd
    
    # Make sure we have data
    if not self._entries:
        self.load()
    
    # Convert entries to dictionaries
    data = [entry.model_dump() for entry in self._entries]
    return pd.DataFrame(data)

# %% ../nbs/dataset.ipynb 30
@patch
def save(self: Dataset, item: BaseModelType) -> None:
    """Save changes to an item to the backend."""
    if not isinstance(item, self.model):
        raise TypeError(f"Item must be an instance of {self.model.__name__}")
    
    # Get the row ID
    row_id = None
    if hasattr(item, "_row_id") and item._row_id:
        row_id = item._row_id
    else:
        # Try to find it in our entries by matching
        for i, entry in enumerate(self._entries):
            if id(entry) == id(item):  # Check if it's the same object
                if hasattr(entry, "_row_id") and entry._row_id:
                    row_id = entry._row_id
                    break
    
    if not row_id:
        raise ValueError("Cannot save: item is not from this dataset or was not properly synced")
    
    # Get column mapping and prepare data
    column_id_map = self.model.__column_mapping__
    row_dict = rt.ModelConverter.instance_to_row(item)["data"]
    row_data = {}
    
    for column in row_dict:
        if column["column_id"] in column_id_map:
            row_data[column_id_map[column["column_id"]]] = column["data"]
    
    # Update in backend
    sync_func = async_to_sync(self._ragas_api_client.update_dataset_row)
    response = sync_func(
        project_id=self.project_id,
        dataset_id=self.dataset_id,
        row_id=row_id,
        data=row_data,
    )
    
    # Find and update in local cache if needed
    for i, entry in enumerate(self._entries):
        if hasattr(entry, "_row_id") and entry._row_id == row_id:
            # If it's not the same object, update our copy
            if id(entry) != id(item):
                self._entries[i] = item
            break

# %% ../nbs/dataset.ipynb 34
@patch
def get(self: Dataset, field_value: str, field_name: str = "_row_id") -> t.Optional[BaseModelType]:
    """Get an entry by field value.
    
    Args:
        id_value: The value to match
        field_name: The field to match against (default: "id")
        
    Returns:
        The matching model instance or None if not found
    """
    # Check if we need to load entries
    if not self._entries:
        self.load()
    
    # Search in local entries first
    for entry in self._entries:
        if hasattr(entry, field_name) and getattr(entry, field_name) == field_value:
            return entry
    
    # If not found and field is "id", try to get directly from API
    if field_name == "id":
        # Get column ID for field
        if field_name not in self.model.__column_mapping__:
            return None
        
        column_id = self.model.__column_mapping__[field_name]
        
        # Get rows with filter
        sync_func = async_to_sync(self._ragas_api_client.list_dataset_rows)
        response = sync_func(
            project_id=self.project_id,
            dataset_id=self.dataset_id,
            # We don't have direct filter support in the API client,
            # so this would need to be implemented there.
            # For now, we've already checked our local cache.
        )
        
        # Would parse response here if we had filtering
    
    return None
