"""How to run experiments"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/project/experiments.ipynb.

# %% auto 0
__all__ = ['memorable_names', 'create_experiment_columns', 'find_git_root', 'version_experiment', 'cleanup_experiment_branches',
           'ExperimentProtocol']

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
            settings=column["settings"]
        ))
    return await asyncio.gather(*tasks)

# %% ../../nbs/project/experiments.ipynb 5
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


# %% ../../nbs/project/experiments.ipynb 9
@patch
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

# %% ../../nbs/project/experiments.ipynb 12
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

# %% ../../nbs/project/experiments.ipynb 15
import git
import os
from pathlib import Path

# %% ../../nbs/project/experiments.ipynb 16
def find_git_root(start_path: t.Union[str, Path, None] = None) -> Path:
    """Find the root directory of a git repository by traversing up from the start path.
    
    Args:
        start_path: Path to start searching from (defaults to current working directory)
        
    Returns:
        Path: Absolute path to the git repository root
        
    Raises:
        ValueError: If no git repository is found
    """
    # Start from the current directory if no path is provided
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()
    
    # Check if the current directory is a git repository
    current_path = start_path
    while current_path != current_path.parent:  # Stop at filesystem root
        if (current_path / '.git').exists() and (current_path / '.git').is_dir():
            return current_path
        
        # Move up to the parent directory
        current_path = current_path.parent
    
    # Final check for the root directory
    if (current_path / '.git').exists() and (current_path / '.git').is_dir():
        return current_path
    
    # No git repository found
    raise ValueError(f"No git repository found in or above {start_path}")

# %% ../../nbs/project/experiments.ipynb 19
def version_experiment(
    experiment_name: str,
    commit_message: t.Optional[str] = None,
    repo_path: t.Union[str, Path, None] = None,
    create_branch: bool = True,
    stage_all: bool = False,
) -> str:
    """
    Version control the current state of the codebase for an experiment.
    """
    # Default to current directory if no repo path is provided
    if repo_path is None:
        repo_path = find_git_root()
    
    # Initialize git repo object
    repo = git.Repo(repo_path)

    # check if there are any changes to the repo
    has_changes = False
    if stage_all and repo.is_dirty(untracked_files=True):
        print("Staging all changes")
        repo.git.add('.')
        has_changes = True
    elif repo.is_dirty(untracked_files=False):
        print("Staging changes to tracked files")
        repo.git.add('-u')
        has_changes = True
    
    # Check if there are uncommitted changes
    if has_changes:
        # Default commit message if none provided
        if commit_message is None:
            commit_message = f"Experiment: {experiment_name}"
        
        # Commit changes
        commit = repo.index.commit(commit_message)
        commit_hash = commit.hexsha
        print(f"Changes committed with hash: {commit_hash[:8]}")
    else:
        # No changes to commit, use current HEAD
        commit_hash = repo.head.commit.hexsha
        print("No changes detected, nothing to commit")
    
    # Format the branch/tag name
    version_name = f"ragas/{experiment_name}"
    
    # Create branch if requested
    if create_branch:
        branch = repo.create_head(version_name, commit_hash)
        print(f"Created branch: {version_name}")
    
    return commit_hash

# %% ../../nbs/project/experiments.ipynb 20
def cleanup_experiment_branches(
    prefix: str = "ragas/", 
    repo_path: t.Union[str, Path, None] = None,
    interactive: bool = True,
    dry_run: bool = False
) -> t.List[str]:
    """Clean up git branches with the specified prefix."""
    # Find the git repository root if not provided
    if repo_path is None:
        try:
            repo_path = find_git_root()
        except ValueError as e:
            raise ValueError(f"Cannot cleanup branches: {str(e)}")
    
    # Initialize git repo object
    repo = git.Repo(repo_path)
    current_branch = repo.active_branch.name
    
    # Get all branches matching the prefix
    matching_branches = []
    for branch in repo.branches:
        if branch.name.startswith(prefix):
            matching_branches.append(branch.name)
    
    if not matching_branches:
        print(f"No branches found with prefix '{prefix}'")
        return []
    
    # Remove current branch from the list if present
    if current_branch in matching_branches:
        print(f"Note: Current branch '{current_branch}' will be excluded from deletion")
        matching_branches.remove(current_branch)
        
    if not matching_branches:
        print("No branches available for deletion after excluding current branch")
        return []
    
    # Show branches to the user
    print(f"Found {len(matching_branches)} branches with prefix '{prefix}':")
    for branch_name in matching_branches:
        print(f"- {branch_name}")
    
    # Handle confirmation in interactive mode
    proceed = True
    if interactive and not dry_run:
        confirm = input(f"\nDelete these {len(matching_branches)} branches? (y/n): ").strip().lower()
        proceed = (confirm == 'y')
    
    if not proceed:
        print("Operation cancelled")
        return []
    
    # Perform deletion
    deleted_branches = []
    for branch_name in matching_branches:
        if dry_run:
            print(f"Would delete branch: {branch_name}")
            deleted_branches.append(branch_name)
        else:
            try:
                # Delete the branch
                repo.git.branch('-D', branch_name)
                print(f"Deleted branch: {branch_name}")
                deleted_branches.append(branch_name)
            except git.GitCommandError as e:
                print(f"Error deleting branch '{branch_name}': {str(e)}")
    
    if dry_run:
        print(f"\nDry run complete. {len(deleted_branches)} branches would be deleted.")
    else:
        print(f"\nCleanup complete. {len(deleted_branches)} branches deleted.")
    
    return deleted_branches

# %% ../../nbs/project/experiments.ipynb 23
@t.runtime_checkable
class ExperimentProtocol(t.Protocol):
    async def __call__(self, *args, **kwargs): ...
    async def run_async(self, name: str, dataset: Dataset): ...

# %% ../../nbs/project/experiments.ipynb 24
from .naming import MemorableNames

# %% ../../nbs/project/experiments.ipynb 25
memorable_names = MemorableNames()

# %% ../../nbs/project/experiments.ipynb 26
@patch
def experiment(
    self: Project, experiment_model, name_prefix: str = "", save_to_git: bool = True, stage_all: bool = False
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
        async def run_async(dataset: Dataset, name: t.Optional[str] = None, save_to_git: bool = save_to_git, stage_all: bool = stage_all):
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

            # save to git if requested
            if save_to_git:
                repo_path = find_git_root()
                version_experiment(experiment_name=name, repo_path=repo_path, stage_all=stage_all)

            return experiment_view

        wrapped_experiment.__setattr__("run_async", run_async)
        return t.cast(ExperimentProtocol, wrapped_experiment)

    return decorator



# %% ../../nbs/project/experiments.ipynb 30
# this one we have to clean up
from langfuse.decorators import observe

# %% ../../nbs/project/experiments.ipynb 31
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
        @wraps(func)
        async def langfuse_wrapped_func(*args, **kwargs):
            # Apply langfuse observation directly here
            trace_name = f"{name_prefix}-{func.__name__}" if name_prefix else func.__name__
            observed_func = observe(name=trace_name)(func)
            return await observed_func(*args, **kwargs)
        
        # Now create the experiment wrapper with our already-observed function
        experiment_wrapper = self.experiment(experiment_model, name_prefix)(langfuse_wrapped_func)
        
        return t.cast(ExperimentProtocol, experiment_wrapper)

    return decorator

# %% ../../nbs/project/experiments.ipynb 23
from mlflow import trace

@patch
def mlflow_experiment(
    self: Project, experiment_model, name_prefix: str = ""
):
    """Decorator for creating experiment functions with mlflow integration.

    Args:
        experiment_model: The NotionModel type to use for experiment results
        name_prefix: Optional prefix for experiment names

    Returns:
        Decorator function that wraps experiment functions with mlflow observation
    """

    def decorator(func: t.Callable) -> ExperimentProtocol:
        # First, create a base experiment wrapper
        base_experiment = self.experiment(experiment_model, name_prefix)(func)

        # Override the wrapped function to add mlflow observation
        @wraps(func)
        async def wrapped_with_mlflow(*args, **kwargs):
            # wrap the function with mlflow observation
            observed_func = trace(name=f"{name_prefix}-{func.__name__}")(func)
            return await observed_func(*args, **kwargs)

        # Replace the async function to use mlflow
        original_run_async = base_experiment.run_async

        # Use the original run_async but with the mlflow-wrapped function
        async def run_async_with_mlflow(
            dataset: Dataset, name: t.Optional[str] = None
        ):
            # Override the internal wrapped_experiment with our mlflow version
            base_experiment.__wrapped__ = wrapped_with_mlflow

            # Call the original run_async which will now use our mlflow-wrapped function
            return await original_run_async(dataset, name)

        # Replace the run_async method
        base_experiment.__setattr__("run_async", run_async_with_mlflow)

        return t.cast(ExperimentProtocol, base_experiment)

    return decorator

# %% ../../nbs/project/experiments.ipynb 24
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
        
        
        
        
    
