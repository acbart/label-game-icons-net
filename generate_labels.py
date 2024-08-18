import argparse
import csv
import os
import logging
from batch_requests import load_all_batch_requests, BatchRequest
from icons import load_all_icons
from utils import get_git_username
from prompts import load_all_prompts
from tabulate import tabulate

logger = logging.getLogger(__name__)

DEFAULT_LOG_FILE = "logs/requests.txt"
DEFAULT_BATCH_REQUESTS_DIR = "batch_requests/"
MAIN_ICON_FILE = "icons/all_icons.csv"
PROMPTS_FILE = "vision_prompts.yaml"


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


def make_label_batch_request(prompt_id: str, icons: list[str], icon_file: str, size: int, batch_requests_dir: str, author: str | None):
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
        logger.info(f"Using {len(icons)} icons: {icons}")
        icons = [icon for icon in icons if icon in all_icons]
        
    if author is None:
        author = get_git_username()

    # Create the new BatchRequest
    new_batch = BatchRequest.make_new(icons, prompt_id, author, batch_requests_dir)
    new_batch.save()
    
    print(f"Batch request created with ID: {new_batch.id}")
    

def execute_batch_request(batch_id: str, batch_requests_dir: str):
    """
    Execute a batch request to generate labels for icons.
    """
    pass

def check_batch_request(batch_id: str, batch_requests_dir: str):
    """
    Check the status of a batch request.
    """
    pass

def list_batch_requests(batch_requests_dir: str):
    """
    List all batch requests, locally and remotely.
    """
    print("Listing all batch requests")
    batch_requests = load_all_batch_requests(batch_requests_dir)
    if not batch_requests:
        print("No batch requests found.")
        return
    for batch_request in batch_requests:
        print(f"{batch_request.id}: {batch_request.when_created} - {batch_request.status}")
    

def cancel_batch_request(batch_id: str, batch_requests_dir: str):
    """
    Cancel a batch request.
    """
    pass

def download_batch_request(batch_id: str, batch_requests_dir: str):
    """
    Download the results of a batch request.
    """
    pass




def main():
    parser = argparse.ArgumentParser(description="Batch request management for icon labeling.")
    subparsers = parser.add_subparsers(dest="command")
    
    # Adding config options
    parser.add_argument('--gpt_api_key', type=str, default=None,
                        help="The GPT API key. Can be a file path or None to use the OS environment variable.")
    parser.add_argument('--gpt_model', type=str, default="gpt-4o",
                        help="The GPT model to use. Default is 'gpt-4o'")
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
    
    # Subcommand for make_label_batch_request
    make_parser = subparsers.add_parser('make', help="Make a batch request to generate labels for icons.")
    make_parser.add_argument('prompt_id', type=str, help="The prompt ID for the batch request.")
    make_parser.add_argument('--icons', type=str, nargs='*', help="List of icon file names (0 or more). If not given, then all icons will be used.",
                             default=[])
    make_parser.add_argument('--icon-file', type=str,
                             help=f"Path to a file containing icon file names (one per line). Default is {MAIN_ICON_FILE}", 
                             default=MAIN_ICON_FILE)
    make_parser.add_argument('--size', type=int, default=512, help="The size of the icons to generate labels for.")
    make_parser.add_argument('--author', type=str, default=None,
                             help="The author of the batch request. Defaults to your github ID.")

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

    if args.command == 'make':
        make_label_batch_request(args.prompt_id, args.icons, args.icon_file, args.size, args.batch_requests_dir)
    elif args.command == 'execute':
        execute_batch_request(args.batch_id, args.batch_requests_dir)
    elif args.command == 'check':
        check_batch_request(args.batch_id, args.batch_requests_dir)
    elif args.command == 'list':
        list_batch_requests(args.batch_requests_dir)
    elif args.command == 'cancel':
        cancel_batch_request(args.batch_id, args.batch_requests_dir)
    elif args.command == 'download':
        download_batch_request(args.batch_id, args.batch_requests_dir)
    elif args.command == 'prompts':
        list_prompts(args.prompts_file, args.characters)
    else:
        parser.print_help(args.batch_requests_dir)


if __name__ == "__main__":
    main()
