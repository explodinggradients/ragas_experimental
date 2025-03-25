"""How to run experiments"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/project/experiments.ipynb.

# %% auto 0
__all__ = ['memorable_names', 'ExperimentProtocol']

# %% ../../nbs/project/experiments.ipynb 2
from tqdm import tqdm
from functools import wraps
import asyncio

import typing as t

from fastcore.utils import patch

from .core import Project
from ..model.notion_model import NotionModel
from ..experiment import Experiment
from ..dataset import Dataset

# %% ../../nbs/project/experiments.ipynb 3
@patch
def create_experiment(
    self: Project, name: str, model: t.Type[NotionModel]
) -> Experiment:
    """Create a new experiment view.

    Args:
        name: Name of the experiment
        model: Model class defining the experiment structure

    Returns:
        ExperimentView: View for managing experiment results
    """
    if self.experiments_page_id == "":
        raise ValueError("Experiments page ID is not set")

    # Collect all properties from model fields
    properties = {}
    for field_name, field in model._fields.items():
        properties.update(field._to_notion_property())

    # Create the database
    database_id = self._notion_backend.create_new_database(
        parent_page_id=self.experiments_page_id, title=name, properties=properties
    )

    return Experiment(
        name=name,
        model=model,
        database_id=database_id,
        notion_backend=self._notion_backend,
    )

# %% ../../nbs/project/experiments.ipynb 4
@patch
def get_experiment(self: Project, name: str, model: t.Type[NotionModel]) -> Experiment:
    """Get an existing experiment by name."""
    if self.experiments_page_id == "":
        raise ValueError("Experiments page ID is not set")

    # Search for database with given name
    database_id = self._notion_backend.get_database_id(
        parent_page_id=self.experiments_page_id, name=name, return_multiple=False
    )

    return Experiment(
        name=name,
        model=model,
        database_id=database_id,
        notion_backend=self._notion_backend,
    )

# %% ../../nbs/project/experiments.ipynb 5
@t.runtime_checkable
class ExperimentProtocol(t.Protocol):
    async def __call__(self, *args, **kwargs): ...
    async def run_async(self, name: str, dataset: Dataset): ...

# %% ../../nbs/project/experiments.ipynb 6
# this one we have to clean up
from langfuse.decorators import observe

# %% ../../nbs/project/experiments.ipynb 7
from .naming import MemorableNames

# %% ../../nbs/project/experiments.ipynb 8
memorable_names = MemorableNames()

# %% ../../nbs/project/experiments.ipynb 9
@patch
def experiment(
    self: Project, experiment_model: t.Type[NotionModel], name_prefix: str = ""
):
    """Decorator for creating experiment functions without Langfuse integration.

    Args:
        experiment_model: The NotionModel type to use for experiment results
        name_prefix: Optional prefix for experiment names

    Returns:
        Decorator function that wraps experiment functions
    """

    def decorator(func: t.Callable) -> ExperimentProtocol:
        @wraps(func)
        async def wrapped_experiment(*args, **kwargs):
            # Simply call the function without Langfuse observation
            return await func(*args, **kwargs)

        # Add run method to the wrapped function
        async def run_async(dataset: Dataset, name: t.Optional[str] = None):
            # if name is not provided, generate a memorable name
            if name is None:
                name = memorable_names.generate_unique_name()

            # Create tasks for all items
            tasks = []
            for item in dataset:
                tasks.append(wrapped_experiment(item))

            # Use as_completed with tqdm for progress tracking
            results = []
            for future in tqdm(asyncio.as_completed(tasks), total=len(tasks)):
                result = await future
                # Add each result to experiment view as it completes
                if result is not None:
                    results.append(result)

            # upload results to experiment view
            experiment_view = self.create_experiment(name=name, model=experiment_model)
            for result in results:
                experiment_view.append(result)

            return experiment_view

        wrapped_experiment.__setattr__("run_async", run_async)
        return t.cast(ExperimentProtocol, wrapped_experiment)

    return decorator


# %% ../../nbs/project/experiments.ipynb 10
@patch
def langfuse_experiment(
    self: Project, experiment_model: t.Type[NotionModel], name_prefix: str = ""
):
    """Decorator for creating experiment functions with Langfuse integration.

    Args:
        experiment_model: The NotionModel type to use for experiment results
        name_prefix: Optional prefix for experiment names

    Returns:
        Decorator function that wraps experiment functions with Langfuse observation
    """

    def decorator(func: t.Callable) -> ExperimentProtocol:
        # First, create a base experiment wrapper
        base_experiment = self.experiment(experiment_model, name_prefix)(func)
        
        # Override the wrapped function to add Langfuse observation
        @wraps(func)
        async def wrapped_with_langfuse(*args, **kwargs):
            # wrap the function with langfuse observation
            observed_func = observe(name=f"{name_prefix}-{func.__name__}")(func)
            return await observed_func(*args, **kwargs)
        
        # Replace the async function to use Langfuse
        original_run_async = base_experiment.run_async
        
        # Use the original run_async but with the Langfuse-wrapped function
        async def run_async_with_langfuse(dataset: Dataset, name: t.Optional[str] = None):
            # Override the internal wrapped_experiment with our Langfuse version
            base_experiment.__wrapped__ = wrapped_with_langfuse
            
            # Call the original run_async which will now use our Langfuse-wrapped function
            return await original_run_async(dataset, name)
        
        # Replace the run_async method
        base_experiment.__setattr__("run_async", run_async_with_langfuse)
        
        return t.cast(ExperimentProtocol, base_experiment)

    return decorator
