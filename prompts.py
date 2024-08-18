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