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
class Icon:
    # The name of the icon
    name: str
    # The path to this icon
    path: str
    
    
def load_all_icons(icon_file: str):
    """
    Load all icons from the icon file.
    """
    if not os.path.isfile(icon_file):
        logger.error(f"Icon file {icon_file} not found.")
        return []
    icons = []
    with open(icon_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            name, path = row
            icons.append(Icon(name=name, path=path))
    return icons
