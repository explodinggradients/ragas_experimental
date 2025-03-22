"""Base class from which all discrete metrics should inherit."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/metric/discrete.ipynb.

# %% auto 0
__all__ = ['discrete_metric', 'DiscreteMetric']

# %% ../../nbs/metric/discrete.ipynb 2
import typing as t
from dataclasses import dataclass, field
from pydantic import BaseModel, create_model
from collections import Counter
from . import Metric, MetricResult
from .decorator import create_metric_decorator


@dataclass
class DiscreteMetric(Metric):
    values: t.List[str] = field(default_factory=lambda: ["pass", "fail"])
    
    def _get_response_model(self, with_reasoning: bool) -> t.Type[BaseModel]:
        """Get or create a response model based on reasoning parameter."""
        
        if with_reasoning in self._response_models:
            return self._response_models[with_reasoning]
        
        model_name = 'response_model'
        values = tuple(self.values)
        fields = {"result": (t.Literal[values], ...)}
        
        if with_reasoning:
            fields["reason"] = (str, ...) # type: ignore
        
        model = create_model(model_name, **fields)  # type: ignore
        self._response_models[with_reasoning] = model
        return model 

    def _ensemble(self,results:t.List[MetricResult]) -> MetricResult:


        if len(results)==1:
            return results[0]
            
        candidates = [candidate.result for candidate in results]
        counter = Counter(candidates)
        max_count = max(counter.values())
        for candidate in results:
            if counter[candidate.result] == max_count:
                result = candidate.result              
                reason = candidate.reason
                break
        
        return results[0]


discrete_metric = create_metric_decorator(DiscreteMetric)
