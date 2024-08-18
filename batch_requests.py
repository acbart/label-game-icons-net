"""
A BatchRequest is a pair of files, one containing the metadata and the other containing the actual prompts in jsonl format.
"""
import os
import csv
import json
import yaml
from pydantic import TypeAdapter
from pydantic.dataclasses import dataclass
import dataclasses
from enum import Enum
import logging
from datetime import datetime
from pathlib import Path

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
    # The input_file_id on the GPT API
    input_file_id: str
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
    # The path to this file
    path: str
    # The raw prompt strings to be sent to the GPT API as a jsonl file
    prompts: list[str]

    def __post_init__(self):
        self.prompts = self.load_prompts()
        
    @classmethod
    def make_new(cls, icons: list[str], prompt_id: str, author: str, base_directory: str):
        """
        Create a new batch request.
        """
        # ID is the friendly hash of the prompt_id and icons
        id_values = (prompt_id, tuple(icons))
        id = str(hash(id_values))
        path = os.path.join(base_directory, f"{id}.yaml")
        if os.path.exists(path):
            logger.error(f"Batch request with ID {id} already exists. That means there is already a batch request with the same prompt and icons.")
            return
        return cls(id=id,
                   input_file_id="",
                   prompt_id=prompt_id,
                   icons=icons,
                   when_created=datetime.now().isoformat(),
                   author=author,
                   execution=[],
                   path=path)
    
    def save(self):
        """
        Save the batch request to disk.
        """
        with open(self.path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(dataclasses.asdict(self), f)
    
    def get_status(self):
        if self.input_file_id == "":
            return "created"
        if len(self.execution) == 0:
            return "ready"
        return self.execution[-1].status
        
    def load_prompts(self):
        """
        Load the prompts from the file.
        """
        prompts = []
        prompts_path = Path(self.path).with_suffix('.jsonl')
        with open(prompts_path, 'r', encoding='utf-8') as f:
            for line in f:
                prompts.append(line.strip())
        return prompts


def load_all_batch_requests(search_directory: str) -> list[BatchRequest]:
    """
    Load all batch requests from the specified directory.
    """
    batch_requests = []
    for file in os.listdir(search_directory):
        if file.endswith('.yaml'):
            with open(os.path.join(search_directory, file), 'r', encoding='utf-8') as f:
                batch_requests.append(BatchRequest(**yaml.safe_load(f),
                                                   path=os.path.join(search_directory, file)))
    return batch_requests
    