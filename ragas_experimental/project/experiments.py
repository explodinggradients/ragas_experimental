"""How to run experiments"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/project/experiments.ipynb.

# %% auto 0
__all__ = ['memorable_names', 'create_experiment_columns', 'ExperimentProtocol']

# %% ../../nbs/project/experiments.ipynb 2
from tqdm import tqdm
from functools import wraps
import asyncio
from tqdm import tqdm

import typing as t

from fastcore.utils import patch

from .core import Project
from ..model.pydantic_model import ExtendedPydanticBaseModel as BaseModel
from ..utils import async_to_sync, create_nano_id
from ..dataset import Dataset, BaseModelType
from ..experiment import Experiment
import ragas_experimental.typing as rt

# %% ../../nbs/project/experiments.ipynb 4
# %% ../../nbs/project/experiments.ipynb 4
@patch
def create_experiment(
    self: Project, name: str, model: t.Type[BaseModel]
) -> Experiment:
    """Create a new experiment.

    Args:
        name: Name of the experiment
        model: Model class defining the experiment structure

    Returns:
        Experiment: An experiment object for managing results
    """
    # Create the experiment
    sync_version = async_to_sync(self._ragas_api_client.create_experiment)
    experiment_info = sync_version(
        project_id=self.project_id,
        name=name,
    )

    # Create the columns for the experiment
    column_types = rt.ModelConverter.model_to_columns(model)
    sync_version = async_to_sync(create_experiment_columns)
    sync_version(
        project_id=self.project_id,
        experiment_id=experiment_info["id"],
        columns=column_types,
        create_experiment_column_func=self._ragas_api_client.create_experiment_column,
    )
    
    # Return a new Experiment instance
    return Experiment(
        name=name,
        model=model,
        project_id=self.project_id,
        experiment_id=experiment_info["id"],
        ragas_api_client=self._ragas_api_client,
    )

# Add this helper function similar to create_dataset_columns in core.ipynb
async def create_experiment_columns(project_id, experiment_id, columns, create_experiment_column_func):
    tasks = []
    for column in columns:
        tasks.append(create_experiment_column_func(
            project_id=project_id,
            experiment_id=experiment_id,
            id=create_nano_id(),
            name=column["name"],
            type=column["type"],
            settings={
                "max_length": 255,
                "is_required": True,
            },
        ))
    return await asyncio.gather(*tasks)

# %% ../../nbs/project/experiments.ipynb 8
# %% ../../nbs/project/experiments.ipynb 8
@patch
def get_experiment_by_id(self: Project, experiment_id: str, model: t.Type[BaseModel]) -> Experiment:
def get_experiment_by_id(self: Project, experiment_id: str, model: t.Type[BaseModel]) -> Experiment:
    """Get an existing experiment by ID."""
    # Get experiment info
    sync_version = async_to_sync(self._ragas_api_client.get_experiment)
    experiment_info = sync_version(
        project_id=self.project_id,
        experiment_id=experiment_id
    )

    return Experiment(
        name=experiment_info["name"],
        model=model,
        project_id=self.project_id,
        experiment_id=experiment_id,
        ragas_api_client=self._ragas_api_client,
    )

# %% ../../nbs/project/experiments.ipynb 11
@patch
def get_experiment(self: Project, experiment_name: str, model) -> Dataset:
    """Get an existing dataset by name."""
    # Search for dataset with given name
    sync_version = async_to_sync(self._ragas_api_client.get_experiment_by_name)
    exp_info = sync_version(
        project_id=self.project_id,
        experiment_name=experiment_name
    )

    # Return Dataset instance
    return Experiment(
        name=exp_info["name"],
        model=model,
        project_id=self.project_id,
        experiment_id=exp_info["id"],
        ragas_api_client=self._ragas_api_client,
    )

# %% ../../nbs/project/experiments.ipynb 14
@t.runtime_checkable
class ExperimentProtocol(t.Protocol):
    async def __call__(self, *args, **kwargs): ...
    async def run_async(self, name: str, dataset: Dataset): ...

# %% ../../nbs/project/experiments.ipynb 15
# %% ../../nbs/project/experiments.ipynb 15
# this one we have to clean up
from langfuse.decorators import observe

# %% ../../nbs/project/experiments.ipynb 16
# %% ../../nbs/project/experiments.ipynb 16
from .naming import MemorableNames

# %% ../../nbs/project/experiments.ipynb 17
# %% ../../nbs/project/experiments.ipynb 17
memorable_names = MemorableNames()

# %% ../../nbs/project/experiments.ipynb 18
# %% ../../nbs/project/experiments.ipynb 18
@patch
def experiment(
    self: Project, experiment_model, name_prefix: str = ""
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
            if name_prefix:
                name = f"{name_prefix}-{name}"

            experiment_view = None
            try:
                # Create the experiment view upfront
                experiment_view = self.create_experiment(name=name, model=experiment_model)
                
                # Create tasks for all items
                tasks = []
                for item in dataset:
                    tasks.append(wrapped_experiment(item))

            experiment_view = None
            try:
                # Create the experiment view upfront
                experiment_view = self.create_experiment(name=name, model=experiment_model)
                
                # Create tasks for all items
                tasks = []
                for item in dataset:
                    tasks.append(wrapped_experiment(item))

                # Calculate total operations (processing + appending)
                total_operations = len(tasks) * 2  # Each item requires processing and appending
                
                # Use tqdm for combined progress tracking
                results = []
                progress_bar = tqdm(total=total_operations, desc="Running experiment")
                
                # Process all items
                for future in asyncio.as_completed(tasks):
                    result = await future
                    if result is not None:
                        results.append(result)
                    progress_bar.update(1)  # Update for task completion
                
                # Append results to experiment view
                for result in results:
                    experiment_view.append(result)
                    progress_bar.update(1)  # Update for append operation
                    
                progress_bar.close()
                return experiment_view
                
            except Exception as e:
                # Clean up the experiment if there was an error and it was created
                if experiment_view is not None:
                    try:
                        # Delete the experiment (you might need to implement this method)
                        sync_version = async_to_sync(self._ragas_api_client.delete_experiment)
                        sync_version(project_id=self.project_id, experiment_id=experiment_view.experiment_id)
                    except Exception as cleanup_error:
                        print(f"Failed to clean up experiment after error: {cleanup_error}")
                
                # Re-raise the original exception
                raise e
                # Calculate total operations (processing + appending)
                total_operations = len(tasks) * 2  # Each item requires processing and appending
                
                # Use tqdm for combined progress tracking
                results = []
                progress_bar = tqdm(total=total_operations, desc="Running experiment")
                
                # Process all items
                for future in asyncio.as_completed(tasks):
                    result = await future
                    if result is not None:
                        results.append(result)
                    progress_bar.update(1)  # Update for task completion
                
                # Append results to experiment view
                for result in results:
                    experiment_view.append(result)
                    progress_bar.update(1)  # Update for append operation
                    
                progress_bar.close()
                return experiment_view
                
            except Exception as e:
                # Clean up the experiment if there was an error and it was created
                if experiment_view is not None:
                    try:
                        # Delete the experiment (you might need to implement this method)
                        sync_version = async_to_sync(self._ragas_api_client.delete_experiment)
                        sync_version(project_id=self.project_id, experiment_id=experiment_view.experiment_id)
                    except Exception as cleanup_error:
                        print(f"Failed to clean up experiment after error: {cleanup_error}")
                
                # Re-raise the original exception
                raise e

        wrapped_experiment.__setattr__("run_async", run_async)
        return t.cast(ExperimentProtocol, wrapped_experiment)

    return decorator

# %% ../../nbs/project/experiments.ipynb 22
# %% ../../nbs/project/experiments.ipynb 22
@patch
def langfuse_experiment(
    self: Project, experiment_model, name_prefix: str = ""
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
        async def run_async_with_langfuse(
            dataset: Dataset, name: t.Optional[str] = None
        ):
            # Override the internal wrapped_experiment with our Langfuse version
            base_experiment.__wrapped__ = wrapped_with_langfuse

            # Call the original run_async which will now use our Langfuse-wrapped function
            return await original_run_async(dataset, name)

        # Replace the run_async method
        base_experiment.__setattr__("run_async", run_async_with_langfuse)

        return t.cast(ExperimentProtocol, base_experiment)

    return decorator

# %% ../../nbs/project/experiments.ipynb 23
import logging
from ..utils import plot_experiments_as_subplots

@patch
def compare_and_plot(self: Project, experiment_names: t.List[str], model: t.Type[BaseModel], metric_names: t.List[str]):
    """Compare multiple experiments and generate a plot.

    Args:
        experiment_names: List of experiment IDs to compare
        model: Model class defining the experiment structure
    """
    results = {}
    for experiment_name in tqdm(experiment_names, desc="Fetching experiments"):
        experiment = self.get_experiment(experiment_name, model)
        experiment.load()
        results[experiment_name] = {}
        for row in experiment:
            for metric in metric_names:
                if metric not in results[experiment_name]:
                    results[experiment_name][metric] = []
                if hasattr(row, metric):
                    results[experiment_name][metric].append(getattr(row, metric))
                else:
                    results[metric].append(None)
                    logging.warning(f"Metric {metric} not found in row: {row}")
                    
    
    
    fig = plot_experiments_as_subplots(results,experiment_ids=experiment_names)
    fig.show()
        
        
        
        
    
