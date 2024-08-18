"""
A BatchRequest is a pair of files, one containing the metadata and the other containing the actual prompts in jsonl format.
"""
from typing import Optional
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
from config import Configuration
from icons import Icon, load_all_icons
from prompts import Prompt
from utils import hash_tuple_simple, partial_dict_key_match, resize_and_get_base64
import base64
from tqdm import tqdm
import difflib

logger = logging.getLogger(__name__)


@dataclass
class BatchExecution:
    # The datetime this batch request was executed in ISO
    when_started: str
    # The datetime this batch request was completed in ISO
    when_completed: str
    # The status of this batch request
    status: str
    # The input_file_id on the GPT API
    input_file_id: str
    # The Execution index of this batch request
    execution_id: str
    # The GPT run ID of this batch request
    batch_id: str
    

@dataclass
class RawBatchPrompt:
    custom_id: str
    body: dict
    method: str = "POST"
    url: str = "/v1/chat/completions"


@dataclass
class BatchRequest:
    # The unique ID of this batch request
    id: str
    # The prompt ID for this batch request
    prompt_id: str
    # The size of the icons for this batch request
    size: int
    # The list of icons for this batch request
    icons: list[Icon]
    # Whether or not to use all icons
    use_all_icons: bool
    # The datetime this batch request was created in ISO
    when_created: str
    # The author (GitHub ID) of this batch request
    author: str
    # Execution information
    execution: list[BatchExecution]
    # The path to this file
    path: str
    # The raw prompt strings to be sent to the GPT API as a jsonl file
    prompts: Optional[list[str]] = dataclasses.field(default_factory=list)
        
    @classmethod
    def make_new(cls, icons: list[Icon], all_icons: bool, prompt: Prompt, author: str, size: int, base_directory: str, force: bool):
        """
        Create a new batch request.
        """
        # ID is the friendly hash of the prompt_id and icons
        icon_names = tuple(sorted([icon.name for icon in icons]))
        if all_icons:
            id = f"{prompt.id}-{size}"
        elif len(icons) <= 3:
            short_names = "_".join(sorted(icon_names))
            id = f"{prompt.id}-{size}-{short_names}"
        else:
            id_values = (prompt.id, size, icon_names)
            id = f"{prompt.id}-{size}-{hash_tuple_simple(id_values)}"
        path = os.path.join(base_directory, f"{id}.yaml")
        if os.path.exists(path) and not force:
            logger.error(f"Batch request with ID {id} already exists. That means there is already a batch request with the same prompt and icons.")
            return
        new_request= cls(id=id,
                         prompt_id=prompt.id,
                         icons=icons,
                         use_all_icons=all_icons,
                         size=size,
                         when_created=datetime.now().isoformat(),
                         author=author,
                         execution=[],
                         path=path,
                         prompts=[],
                         )
        new_request.populate_base_prompts(prompt)
        return new_request
    
    def populate_base_prompts(self, prompt: Prompt):
        """
        Populate the prompts for this batch request.
        """
        # Load the base prompt from the prompts file
        prompts_path = Path(self.path).with_suffix('.jsonl')
        with open(prompts_path, 'w', encoding='utf-8') as f:
            for icon in tqdm(self.icons):
                custom_id = f"{self.id}|{icon.name}"
                icon_data = resize_and_get_base64(icon.path, self.size)
                body = prompt.populate(icon.name, icon_data)
                raw_prompt = RawBatchPrompt(custom_id=custom_id, body=body)
                dumped_prompt = dataclasses.asdict(raw_prompt)
                f.write(json.dumps(dumped_prompt) + '\n')
                
    def finalize_prompts(self, execution_id: str, open_ai_config: Configuration):
        """
        Finalize the prompts for this batch request.
        """
        prompts = []
        for prompt in tqdm(self.prompts):
            prompt_dict = json.loads(prompt)
            prompt_dict['body']['model'] = open_ai_config.gpt_model
            prompt_dict['custom_id'] = prompt_dict['custom_id'] + f"|{execution_id}"
            prompts.append(prompt_dict)
        return "\n".join([json.dumps(prompt) for prompt in prompts])
    
    def save(self):
        """
        Save the batch request to disk.
        """
        with open(self.path, 'w', encoding='utf-8') as f:
            raw = dataclasses.asdict(self)
            if raw['use_all_icons']:
                raw.pop('icons')
            else:
                icon_names = []
                for icon in raw['icons']:
                    icon_names.append(icon['name'])
                raw['icons'] = icon_names
            raw.pop('path')
            raw.pop('prompts')
            yaml.safe_dump(raw, f)
    
    def get_status(self):
        if len(self.execution) == 0:
            return "created"
        return self.execution[-1].status
    
    def get_last_execution(self):
        if len(self.execution) == 0:
            return None
        return self.execution[-1]
        
    def load_prompts(self):
        """
        Load the prompts from the file.
        """
        prompts = []
        prompts_path = Path(self.path).with_suffix('.jsonl')
        with open(prompts_path, 'r', encoding='utf-8') as f:
            for line in f:
                prompts.append(line.strip())
        self.prompts = prompts
        return prompts
    
    def start_new_execution(self):
        """
        Start a new execution for this batch request.
        """
        execution_count = len(self.execution)
        new_execution = BatchExecution(when_started=datetime.now().isoformat(),
                                       when_completed="",
                                       status="starting",
                                       input_file_id="",
                                       batch_id="",
                                       execution_id=str(execution_count))
        self.execution.append(new_execution)
        self.save()
        return new_execution
    
    def save_upload(self, execution: BatchExecution, input_file_id: str):
        """
        Save the upload to the batch request.
        """
        execution.input_file_id = input_file_id
        execution.status = "uploaded"
        self.save()
        
    def save_submit(self, execution: BatchExecution, batch_id: str):
        """
        Save the submission to the batch request.
        """
        execution.batch_id = batch_id
        execution.status = "submitted"
        self.save()
    
    def update_execution_status(self, execution: BatchExecution, status: str):
        """
        Update the status of the execution.
        """
        execution.status = status
        self.save()
        
    def complete_execution(self, execution: BatchExecution):
        """
        Complete the execution of the batch request.
        """
        execution.when_completed = datetime.now().isoformat()
        execution.status = "completed"
        self.save()
    
    def save_execution(self, execution: BatchExecution):
        """
        Save the execution to the batch request.
        """
        if len(self.execution) == 0:
            raise ValueError("No execution to save to.")
        if self.execution[-1] != execution:
            raise ValueError("Execution does not match the last execution.")
        self.save()


def load_all_batch_requests(search_directory: str, icon_file: str) -> list[BatchRequest]:
    """
    Load all batch requests from the specified directory.
    """
    all_icons = load_all_icons(icon_file)
    search_icons = {icon.name: icon for icon in all_icons}
    batch_requests = []
    for file in os.listdir(search_directory):
        if file.endswith('.yaml'):
            with open(os.path.join(search_directory, file), 'r', encoding='utf-8') as f:
                raw = yaml.safe_load(f)
                if raw['use_all_icons']:
                    raw['icons'] = all_icons
                else:
                    icons = []
                    for icon in raw['icons']:
                        if icon not in search_icons:
                            raise ValueError(f"Icon {icon} not found in icon file.")
                        found_icon = search_icons[icon]
                        icons.append(found_icon)
                    raw['icons'] = [search_icons[icon] for icon in raw['icons']]
                batch_requests.append(BatchRequest(**raw, path=os.path.join(search_directory, file)))
    return batch_requests
    
def load_batch_request(search_directory: str, batch_id: str, icon_file: str) -> Optional[BatchRequest]:
    """
    Load a specific batch request from the specified directory.
    """
    batch_requests = load_all_batch_requests(search_directory, icon_file)
    search_requests = {request.id: request for request in batch_requests}
    if batch_id in search_requests:
        return search_requests[batch_id]
    else:
        partial_matches = partial_dict_key_match(batch_id, search_requests)
        if len(partial_matches) == 1:
            return search_requests[partial_matches[0]]
        similar_requests = difflib.get_close_matches(batch_id, search_requests.keys())
        if similar_requests:
            logger.error(f"Batch request {batch_id} not found. Did you mean one of these? {similar_requests}")
        else:
            logger.error(f"Batch request {batch_id} not found. Nothing similar found.")
        return None
