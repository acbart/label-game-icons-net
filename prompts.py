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
from typing import Optional
import difflib

logger = logging.getLogger(__name__)


@dataclass
class Prompt:
    # The unique ID of this prompt; make sure you include versioning when possible
    id: str
    # The author (GitHub ID) of this prompt, comma-separated
    authors: str
    # When this prompt was created in ISO
    when_created: str
    # The prompt text
    template: str
    # The prompt schema object to return
    schema: dict
    # A changelog of modifications for this prompt, if any
    changelog: Optional[list[str]] = dataclasses.field(default_factory=list)
    
    def populate(self, icon, icon_data):
        # An artist name may precede the icon separated by an underscore
        icon = icon.split("_")[-1]
        return {
            "model": "",
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "schema": self.schema,
                    "name": "icon_labels_response",
                    "strict": True
                }
            },
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.template.format(icon=icon)
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{icon_data}"
                            }
                        }
                    ]
                },
            ],
        }


def load_all_prompts(prompt_file: str) -> list[Prompt]:
    """
    Load all prompts from the prompt file.
    """
    if not os.path.isfile(prompt_file):
        logger.error(f"Prompt file {prompt_file} not found.")
        return []
    prompts = []
    with open(prompt_file, 'r', encoding='utf-8') as f:
        raw_prompts = yaml.safe_load(f)
        prompts = [Prompt(**prompt) for prompt in raw_prompts]
    return prompts


def load_prompt(prompt_file: str, prompt_id: str) -> Optional[Prompt]:
    """
    Load a specific prompt from the prompt file.
    """
    prompts = load_all_prompts(prompt_file)
    search_prompts = {prompt.id: prompt for prompt in prompts}
    if prompt_id in search_prompts:
        return search_prompts[prompt_id]
    else:
        similar_prompts = difflib.get_close_matches(prompt_id, search_prompts.keys())
        if similar_prompts:
            raise ValueError(f"Prompt ID {prompt_id} not found in prompts file. Did you mean one of these? {similar_prompts}")
        else:
            raise ValueError(f"Prompt ID {prompt_id} not found in prompts file. Nothing similar found.")
