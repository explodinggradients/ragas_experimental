# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/metric/llm.ipynb.

# %% auto 0
__all__ = ['LLM']

# %% ../../nbs/metric/llm.ipynb 1
import openai
import instructor
from dataclasses import dataclass


@dataclass
class LLM:
    def __post_init__(self):
        self.aclient = instructor.from_openai(openai.AsyncOpenAI())
        self.client = instructor.from_openai(openai.OpenAI())

    def generate(self, prompt, response_model):
        return self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt},
            ],
            response_model=response_model,
        )

    async def agenerate(self, prompt, response_model):
        return await self.aclient.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt},
            ],
            response_model=response_model,
        )
