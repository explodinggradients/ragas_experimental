"""base class for all type of metrics in ragas"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/metric/base.ipynb.

# %% auto 0
__all__ = ['Metric']

# %% ../../nbs/metric/base.ipynb 2
from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
import datasets
from pydantic import BaseModel
import typing as t
import json
from tqdm import tqdm

from ..prompt.base import Prompt
from ..embedding.base import RagasEmbedding
from . import MetricResult
from ..llm import RagasLLM
from ..project.core import Project
from ..model.notion_model import NotionModel
from ..prompt.dynamic_few_shot import DynamicFewShotPrompt


@dataclass
class Metric(ABC):
    """Base class for all metrics in the LLM evaluation library."""
    name: str
    prompt: str | Prompt
    llm: RagasLLM
    _response_models: t.Dict[bool, t.Type[BaseModel]] = field(
        default_factory=dict, init=False, repr=False
    )
    
    def __post_init__(self):
        if isinstance(self.prompt,str):
            self.prompt = Prompt(self.prompt)
    
    @abstractmethod
    def _get_response_model(self, with_reasoning: bool) -> t.Type[BaseModel]:
        """Get the appropriate response model."""
        pass

    @abstractmethod
    def _ensemble(self, results: t.List[MetricResult]) -> MetricResult:
        pass
        
    
    def score(self, reasoning: bool = True, n: int = 1, **kwargs) -> t.Any:
        responses = []
        traces = {}
        traces["input"] = kwargs
        prompt_input = self.prompt.format(**kwargs)
        for _ in range(n):
            response = self.llm.generate(prompt_input, response_model = self._get_response_model(reasoning)) 
            traces['output'] = response.model_dump()
            response = MetricResult(**response.model_dump())
            responses.append(response)
        results = self._ensemble(responses)
        results.traces = traces
        return results


    async def ascore(self, reasoning: bool = True, n: int = 1, **kwargs) -> MetricResult:
        responses = []  # Added missing initialization
        traces = {}
        traces["input"] = kwargs
        prompt_input = self.prompt.format(**kwargs)
        for _ in range(n):
            response = await self.llm.agenerate(prompt_input, response_model = self._get_response_model(reasoning))
            traces['output'] = response.model_dump()
            response = MetricResult(**response.model_dump())  # Fixed missing parentheses
            responses.append(response)
        results = self._ensemble(responses)
        results.traces = traces
        return results
        
    def batch_score(self, inputs: t.List[t.Dict[str, t.Any]], reasoning: bool = True, n: int = 1) -> t.List[t.Any]:
        return [self.score(reasoning, n, **input_dict) for input_dict in inputs]
    
    async def abatch_score(self, inputs: t.List[t.Dict[str, t.Any]], reasoning: bool = True, n: int = 1) -> t.List[MetricResult]:
        async_tasks = []
        for input_dict in inputs:
            # Add reasoning and n to the input parameters
            async_tasks.append(self.ascore(reasoning=reasoning, n=n, **input_dict))
            
        # Run all tasks concurrently and return results
        return await asyncio.gather(*async_tasks)
    
    def train(self,project:Project, experiment_names: t.List[str], model:NotionModel, embedding_model: RagasEmbedding,method: t.Dict[str, t.Any]):
        
        assert isinstance(self.prompt, Prompt)
        self.prompt = DynamicFewShotPrompt.from_prompt(self.prompt,embedding_model)
        datasets = []
        for experiment_name in experiment_names:
            experiment_data = project.get_experiment(experiment_name,model)
            experiment_data.load()
            datasets.append(experiment_data)
        
        total_items = sum([len(dataset) for dataset in datasets])
        with tqdm(total=total_items, desc="Processing examples") as pbar:
            for dataset in datasets:
                for row in dataset:
                    if hasattr(row, f'{self.name}_traces'):
                        traces = json.loads(getattr(row, f'{self.name}_traces'))
                        if traces:
                            self.prompt.add_example(traces['input'],traces['output'])
                    pbar.update(1)
        
                
                
        
        
        
                
