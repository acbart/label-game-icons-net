"""
A BatchRequest is a pair of files, one containing the metadata and the other containing the actual prompts in jsonl format.
"""

import csv
from pydantic import TypeAdapter
from pydantic.dataclasses import dataclass
import dataclasses
from enum import Enum
import logging

logger = logging.getLogger(__name__)


@dataclass
class BatchExecution:
    # The datetime this batch request was executed in ISO
    when_started: str
    # The datetime this batch request was completed in ISO
    when_completed: str
    # The status of this batch request
    status: str
    # The ID of the GPT run that generated this batch request
    gpt_run_id: str
    # The ID of the GPT run that executed this batch request
    gpt_exec_id: str
    # The ID of the GPT run that completed this batch request
    gpt_comp_id: str
    


@dataclass
class BatchRequest:
    # The unique ID of this batch request
    id: str
    # The prompt ID for this batch request
    prompt_id: str
    # The list of icons for this batch request
    icons: list[str]
    # The datetime this batch request was created in ISO
    when_created: str
    # The author (GitHub ID) of this batch request
    author: str
    # Execution information
    execution: list[BatchExecution]
    # The raw prompt strings to be sent to the GPT API as a jsonl file
    prompts: list[str]
    

    def __post_init__(self):
        self.prompts = self.load_prompts()
        
    def load_prompts(self):
        """
        Load the prompts from the file.
        """
        prompts = []
        with open(f'batch_requests/{self.id}.jsonl', 'r', encoding='utf-8') as f:
            for line in f:
                prompts.append(line.strip())
        return prompts

