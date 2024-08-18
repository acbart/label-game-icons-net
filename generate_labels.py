import argparse
import csv
from datetime import datetime
import json
import os
import logging
from batch_requests import load_all_batch_requests, BatchRequest, load_batch_request
from config import Configuration
from icons import load_all_icons
from labels import Label, LabelFile
from openai_api import OpenAI
from utils import get_git_username
from prompts import load_all_prompts, load_prompt
from tabulate import tabulate
import difflib

logger = logging.getLogger(__name__)

DEFAULT_LOG_FILE = "logs/requests.txt"
DEFAULT_BATCH_REQUESTS_DIR = "batch_requests/"
MAIN_ICON_FILE = "icons/all_icons.csv"
PROMPTS_FILE = "vision_prompts.yaml"
DEFAULT_API_KEY_FILE="openai_key.txt"
DEFAULT_MODEL = "gpt-4o-2024-08-06"


def setup_requests_logger(log_file_path: str):
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)


def list_prompts(prompts_file: str, characters: int = 50):
    """
    List all prompts.
    """
    prompts = load_all_prompts(prompts_file)
    # Print out the prompts in a table
    headers = ["ID", "Authors", "Created", "Template"]
    table = []
    for prompt in prompts:
        template = prompt.template[:characters] if characters >= 0 else prompt.template
        table.append([prompt.id, prompt.authors, prompt.when_created, template])
    print(tabulate(table, headers=headers))


def make_label_batch_request(prompt_id: str, icons: list[str], icon_file: str, size: int, batch_requests_dir: str, author: str | None, prompt_file: str, force: bool):
    """
    Make a batch request to generate labels for icons.
    Returns a batch id.
    """
    # Handling icons input for the 'make' command
    if not icon_file:
        logger.error("No icon file specified.")
        return
    elif os.path.isfile(icon_file):
        all_icons = load_all_icons(icon_file)
        logger.info(f"Loaded {len(all_icons)} icons from {icon_file}.")
    else:
        logger.error(f"Icon file {icon_file} not found.")
        return
    
    if icons:
        use_all_icons = False
        # Check for any invalid icons
        icon_names = {icon.name: icon for icon in all_icons}
        for icon in icons:
            if icon not in icon_names:
                similar_icons = difflib.get_close_matches(icon, [icon.name for icon in all_icons])
                if similar_icons:
                    logger.error(f"Icon {icon} not found in icon file. Did you mean one of these? {similar_icons}")
                    return
                else:
                    logger.error(f"Icon {icon} not found in icon file. Nothing similar found.")
                    return
        icons = [icon_names[icon] for icon in icons]
        logger.info(f"Using {len(icons)} icons: {icons}")
    else:
        icons = all_icons
        use_all_icons = True
        logger.info(f"Using all {len(icons)} icons.")
        
    if author is None:
        author = get_git_username()
    
    prompt = load_prompt(prompt_file, prompt_id)
    
    # Create the new BatchRequest
    new_batch = BatchRequest.make_new(icons, use_all_icons, prompt, 
                                      author, size, batch_requests_dir, force)
    if new_batch is not None:
        new_batch.save()
        print(f"Batch request created with ID: {new_batch.id}")
    

def execute_batch_request(batch_id: str, batch_requests_dir: str, icon_file: str, open_ai_config: Configuration):
    """
    Execute a batch request to generate labels for icons.
    """
    openai = OpenAI(open_ai_config)
    request: BatchRequest = load_batch_request(batch_requests_dir, batch_id, icon_file)
    request.load_prompts()
    execution = request.start_new_execution()
    # Load any remaining data into the prompts
    prompts = request.finalize_prompts(execution.execution_id, open_ai_config)
    # Upload the prompts to OpenAI as a batch file
    file_result = openai.upload_string_as_file(prompts)
    request.save_upload(execution, file_result.id)
    # Create the batch job on OpenAI
    batch = openai.submit_batch_file(execution.input_file_id, f"Label Game Icons Project: Batch request {request.id}")
    request.save_submit(execution, batch.id)
    print(f"Batch request {request.id} submitted with batch ID: {batch.id}")
    
    

def check_batch_request(batch_id: str, batch_requests_dir: str, icon_file: str, open_ai_config: Configuration):
    """
    Check the status of a batch request.
    """
    request = load_batch_request(batch_requests_dir, batch_id, icon_file)
    if request is None:
        return
    openai = OpenAI(open_ai_config)
    print(f"Batch request {request.id}: {request.get_status()}")
    execution = request.get_last_execution()
    if execution is None:
        print("No executions yet.")
        return
    if execution.batch_id:
        batch = openai.check_batch_file(execution.batch_id)
        print(f"OpenAI Status for Batch {execution.batch_id}: {batch.status}")
        if batch.errors:
            print(f"Errors: {batch.errors}")
        request.update_execution_status(execution, batch.status)
        print(batch)
        if batch.request_counts.failed:
            print(f"Failed requests: {batch.request_counts.failed}")
        if batch.request_counts.completed:
            print(f"Completed requests: {batch.request_counts.completed}")
    

def list_batch_requests(batch_requests_dir: str, icon_file: str, open_ai_config: Configuration):
    """
    List all batch requests, locally and remotely.
    """
    print("Listing all batch requests")
    batch_requests = load_all_batch_requests(batch_requests_dir, icon_file)
    if not batch_requests:
        print("No batch requests found.")
        return
    for batch_request in batch_requests:
        print(f"{batch_request.id}: {batch_request.when_created} - {batch_request.status}")
    

def cancel_batch_request(batch_id: str, batch_requests_dir: str, icon_file: str, open_ai_config: Configuration):
    """
    Cancel a batch request.
    """
    raise NotImplementedError("Canceling batch requests is not yet implemented.")

def download_batch_request(batch_id: str, batch_requests_dir: str, icon_file: str, open_ai_config: Configuration):
    """
    Download the results of a batch request.
    """
    openai = OpenAI(open_ai_config)
    request = load_batch_request(batch_requests_dir, batch_id, icon_file)
    if request is None:
        return
    execution = request.get_last_execution()
    if execution is None:
        print("No execution found for this batch request.")
        return
    if not execution.batch_id:
        print("No batch ID found for this execution. Perhaps the batch request has not been submitted yet?")
        return
    batch_file = openai.get_batch_file(execution.batch_id)
    request.complete_execution(execution)
    
    executions_directory = os.path.join(batch_requests_dir, "executions")
    os.makedirs(executions_directory, exist_ok=True)
    execution_file = os.path.join(executions_directory, f"{request.id}_{execution.execution_id}.jsonl")
    with open(execution_file, 'w', encoding='utf-8') as f:
        f.write(batch_file)
    
    # {"id": "batch_req_123", "custom_id": "request-2", "response": {"status_code": 200, "request_id": "req_123", "body": {"id": "chatcmpl-123", "object": "chat.completion", "created": 1711652795, "model": "gpt-3.5-turbo-0125", "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello."}, "logprobs": null, "finish_reason": "stop"}], "usage": {"prompt_tokens": 22, "completion_tokens": 2, "total_tokens": 24}, "system_fingerprint": "fp_123"}}, "error": null}
    for line in batch_file.split("\n"):
        if not line:
            continue
        data = json.loads(line)
        given_request_id, icon_name, given_execution_id  = data['custom_id'].split("|")
        label_file = LabelFile(icon_name)
        body = data['response']['body']
        if 'choices' in body:
            choice = body['choices'][0]
            results = json.loads(choice['message']['content'])
            results = results['labels']
            for result in results:
                if label_file.increase_count_if_exists(result['label']):
                    continue
                label = Label.from_gpt(icon_name, result['label'], 
                                       result['relevance'],
                                       request.author, given_request_id, given_execution_id,
                                       body['model'],
                                       data['id'])
                label_file.labels.append(label)
            label_file.save()



def main():
    parser = argparse.ArgumentParser(description="Batch request management for icon labeling.")
    subparsers = parser.add_subparsers(dest="command")
    
    # Adding config options
    parser.add_argument('--gpt_api_key', type=str, default=None,
                        help="The GPT API key. Can be a file path or None to use the OS environment variable.")
    parser.add_argument('--gpt_model', type=str, default=DEFAULT_MODEL,
                        help=f"The GPT model to use. Default is {DEFAULT_MODEL}")
    parser.add_argument('--gpt_temperature', type=float, default=0.7,
                        help="The temperature setting for GPT. Default is 0.7.")
    parser.add_argument('--gpt_top_p', type=float, default=0.9,
                        help="The top_p setting for GPT. Default is 0.9.")
    parser.add_argument('--gpt_max_tokens', type=int, default=300,
                        help="The maximum number of tokens for GPT. Default is 300.")
    parser.add_argument('--log_file', type=str, default=DEFAULT_LOG_FILE,
                        help=f"The log file path. Defaults to {DEFAULT_LOG_FILE}")
    parser.add_argument('--batch_requests_dir', type=str, default=DEFAULT_BATCH_REQUESTS_DIR,
                        help=f"The directory to save batch requests to. Defaults to {DEFAULT_BATCH_REQUESTS_DIR}")
    parser.add_argument('--prompts_file', type=str, default=PROMPTS_FILE,
                        help=f"The path to the prompts file. Defaults to {PROMPTS_FILE}")
    parser.add_argument('--icon-file', type=str,
                             help=f"Path to a file containing icon file names (one per line). Default is {MAIN_ICON_FILE}", 
                             default=MAIN_ICON_FILE)
    
    # Subcommand for make_label_batch_request
    make_parser = subparsers.add_parser('make', help="Make a batch request to generate labels for icons.")
    make_parser.add_argument('prompt_id', type=str, help="The prompt ID for the batch request.")
    make_parser.add_argument('--icons', type=str, nargs='*', help="List of icon file names (0 or more). If not given, then all icons will be used.",
                             default=[])
    make_parser.add_argument('--size', type=int, default=512, help="The size of the icons to generate labels for.")
    make_parser.add_argument('--author', type=str, default=None,
                             help="The author of the batch request. Defaults to your git email address.")
    make_parser.add_argument("--force", action="store_true", help="Force the batch request to be recreated even if it already exists.")

    # Subcommand for execute_batch_request
    execute_parser = subparsers.add_parser('execute', help="Execute a batch request to generate labels for icons.")
    execute_parser.add_argument('batch_id', type=str, help="The batch ID to execute.")
    
    # Subcommand for check_batch_request
    check_parser = subparsers.add_parser('check', help="Check the status of a batch request.")
    check_parser.add_argument('batch_id', type=str, help="The batch ID to check.")
    
    # Subcommand for list_batch_requests
    list_parser = subparsers.add_parser('list', help="List all batch requests.")
    
    # Subcommand for cancel_batch_request
    cancel_parser = subparsers.add_parser('cancel', help="Cancel a batch request.")
    cancel_parser.add_argument('batch_id', type=str, help="The batch ID to cancel.")
    
    # Subcommand for download_batch_request
    download_parser = subparsers.add_parser('download', help="Download the results of a batch request.")
    download_parser.add_argument('batch_id', type=str, help="The batch ID to download.")
    
    # Subcommand for list_prompts
    list_prompts_parser = subparsers.add_parser('prompts', help="List all prompts.")
    list_prompts_parser.add_argument('--characters', type=int, default=50,
                                     help="The number of characters to display for the prompt template. Provide -1 to display the entire template.")

    args = parser.parse_args()
    
    setup_requests_logger(args.log_file)
    
    # Handle the GPT API key
    if args.gpt_api_key:
        if os.path.isfile(args.gpt_api_key):
            with open(args.gpt_api_key, 'r') as f:
                gpt_api_key = f.read().strip()
        else:
            gpt_api_key = args.gpt_api_key
    else:
        gpt_api_key = os.getenv('GPT_API_KEY')
        if not gpt_api_key:
            if os.path.isfile(DEFAULT_API_KEY_FILE):
                with open(DEFAULT_API_KEY_FILE, 'r') as f:
                    gpt_api_key = f.read().strip()
            else:
                logger.error("No GPT API key found.")
        
    open_ai_config = Configuration(gpt_api_key, args.gpt_model, args.gpt_temperature, args.gpt_top_p, args.gpt_max_tokens)

    if args.command == 'make':
        make_label_batch_request(args.prompt_id, args.icons, args.icon_file, args.size, args.batch_requests_dir, args.author, args.prompts_file, args.force)
    elif args.command == 'execute':
        execute_batch_request(args.batch_id, args.batch_requests_dir, args.icon_file, open_ai_config)
    elif args.command == 'check':
        check_batch_request(args.batch_id, args.batch_requests_dir, args.icon_file, open_ai_config)
    elif args.command == 'list':
        list_batch_requests(args.batch_requests_dir, args.icon_file, open_ai_config)
    elif args.command == 'cancel':
        cancel_batch_request(args.batch_id, args.batch_requests_dir, args.icon_file, open_ai_config)
    elif args.command == 'download':
        download_batch_request(args.batch_id, args.batch_requests_dir, args.icon_file, open_ai_config)
    elif args.command == 'prompts':
        list_prompts(args.prompts_file, args.characters)
    else:
        parser.print_help(args.batch_requests_dir)


if __name__ == "__main__":
    main()
