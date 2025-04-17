__version__ = "0.0.4"
# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/init_module.ipynb.

# %% auto 0
__all__ = []

# %% ../nbs/init_module.ipynb 2
from .project.core import Project
import ragas_experimental.model.notion_typing as nmt
from .model.notion_model import NotionModel
from ragas_experimental.model.pydantic_model import (
    ExtendedPydanticBaseModel as BaseModel,
)

# just import to run the module
import ragas_experimental.project.experiments
import ragas_experimental.project.comparison

# %% ../nbs/init_module.ipynb 3
__all__ = ["Project", "NotionModel", "nmt", "BaseModel"]
