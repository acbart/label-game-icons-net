import json
import io
import time
import openai
import logging
import base64
import requests
from dataclasses import dataclass

from config import Configuration

logger = logging.getLogger(__name__)


@dataclass
class PromptFunction:
    body: str
    function: dict
    
    def to_json(self):
        return {
            'body': self.body,
            'function': self.function
        }


class OpenAI:
    """
    Simple wrapper around OpenAI's API to make it easier to call functions, send prompts, generate images, and
    create batch files. This class is intended to be used as a singleton, and should be instantiated once and
    passed around as needed.
    
    The class also handles things like retries and rate limiting, and will automatically retry failed requests.
    
    Args:
        config: The configuration object to use for the OpenAI API key and other settings.
    """
    def __init__(self, config: Configuration):
        self.config = config
        self.client = openai.OpenAI(api_key=config.gpt_api_key)
        if not self.client.api_key:
            raise ValueError("OpenAI API key not set!")
        
        
    def encode_image(self, image_file):
        return base64.b64encode(image_file).decode('utf-8')
    
    def get_headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.gpt_api_key}"
        }
        
    def create_completion(self, messages, function):
        return self.client.chat.completions.create(
                model=self.config.gpt_model,
                messages=messages,
                tools=[{"type": "function", "function": function}],
                tool_choice={"type": "function", "function": {
                    "name": function['name']
                }},
                #functions=[function],
                #function_call={'name': function['name']},
                temperature=self.config.gpt_temperature,
                top_p=self.config.gpt_top_p,
                #response_format={"type": "json_object"}
                max_tokens=self.config.gpt_max_tokens,
            )
        
    def run_function(self, messages, function, attempts=3, retry_delay=10):
        def is_valid(response):
            return not response.choices or not response.choices[0].message.tool_calls
        execution = lambda: self.create_completion(messages, function)
        response = self._run_gpt(execution, is_valid, attempts, retry_delay)
        tool_calls = response.choices[0].message.tool_calls[0]

        try:
            args = json.loads(tool_calls.function.arguments)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON returned from OpenAI API: {e}")
            time.sleep(retry_delay)
            return self.run_prompt(execution, is_valid, function, attempts - 1)

        for expected_arg in function['parameters']['required']:
            if expected_arg not in args:
                logger.error(f"Missing required parameter in OpenAI response: {expected_arg}")
                time.sleep(retry_delay)
                return self.run_prompt(execution, is_valid, function, attempts - 1)

        return args, response

    def _run_gpt(self, execution, is_valid, attempts=3, retry_delay=10):
        """
        Runs a prompt through OpenAI's api which calls a function, and parses the result.

        Args:
            messages: A list of messages to pass to the OpenAI api call
            function: The function to pass to the OpenAI api call
        """
        if attempts <= 0:
            # TODO: Allow attempt count to be configurable
            logger.error("Too many attempts to run prompt, aborting.")
            raise Exception("Too many attempts to run prompt, aborting.")
        try:
            response = execution()
            do_retry = False
        except openai.RateLimitError as e:
            # Handle rate limit error (we recommend using exponential backoff)
            logger.error(f"OpenAI API request exceeded rate limit: {e}")
            retry_delay *= 2
            do_retry = True
        except openai.APIConnectionError as e:
            # Handle connection error here
            logger.error(f"Failed to connect to OpenAI API: {e}")
            raise Exception(f"Failed to connect to OpenAI API: {e}")
        except openai.APIStatusError as e:
            # Handle API error here, e.g. retry or log
            logger.error(f"OpenAI API returned an API Error: {e.status_code}\n{e.response}\n{e.response.content}")
            do_retry = True

        if do_retry:
            logger.error(f"Retrying prompt, waiting {retry_delay} seconds ({attempts} attempts left)")
            time.sleep(retry_delay)
            return self.run_prompt(execution, is_valid, function, attempts - 1)

        if is_valid(response):
            logger.error(f"Response returned from OpenAI API was not valid: {response}")
            time.sleep(retry_delay)
            return self.run_prompt(execution, is_valid, function, attempts - 1)

        return response
    
    def prepare_image_messages(self, prompt, image_data):
        base64_image = self.encode_image(image_data)
        messages = [{
            "role": "user",
            "content": [
                { "type": "text", "text": prompt },
                { "type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        }]
        return messages

    def run_image_prompt(self, prompt, image_data, attempts=3, retry_delay=10):
        """
        Runs a prompt through OpenAI's api which calls a function, and parses the result.

        Args:
            image_data: The image data to pass to the Open AI api call
        """
        if attempts <= 0:
            logger.error("Too many attempts to run prompt, aborting.")
            raise Exception("Too many attempts to run prompt, aborting.")
        
        def execution():
            return self.client.chat.completions.create(
                model=self.config.gpt_model,
                messages=self.prepare_image_messages(prompt, image_data),
                max_tokens=self.config.gpt_max_tokens,
            )
        def is_valid(response):
            return not response.choices or not response.choices[0].message.content
        response = self._run_gpt(execution, is_valid, attempts, retry_delay)
        
        return response
    
    def generate_image(self, prompt, size="1024x1024", quality="standard", model="dall-e-3"):
        try:
            response = self.client.images.generate(prompt=prompt, size=size, quality=quality)
        except openai.OpenAIError as e:
            logger.error(f"Error generating image: {e}")
            raise Exception(f"Error generating image: {e}")
        
        if not response.data:
            logger.error(f"Invalid response from OpenAI API: {response}")
            raise Exception(f"Invalid response from OpenAI API: {response}")
        
        return response.data[0].url, response
    
    def create_batch_file(self, prompt_set, function):
        """
        Creates a batch file using the OpenAI API.

        Args:
            prompts: A list of prompts to pass to the OpenAI api call
            function: The function to pass to the OpenAI api call
        """
        messages = [
            self.create_completion(prompt, function)
            for prompt in prompt_set
        ]
        batch_file = io.StringIO(json.dumps(messages))
        batch_input_file = self.client.files.create(file=batch_file, purpose="batch")
        
    def upload_string_as_file(self, contents):
        io_file = io.BytesIO(contents.encode())
        file_object = self.client.files.create(file=io_file, purpose="batch")
        return file_object
        
    
    def submit_batch_file(self, batch_input_file_id, description):
        batch = self.client.batches.create(
            input_file_id=batch_input_file_id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={
                "description": description,
            }
        )
        if batch.errors:
            raise Exception(f"Error submitting batch file: {batch.errors}")
        return batch
        
    def check_batch_file(self, batch_id):
        return self.client.batches.retrieve(batch_id)
    
    def get_batch_file(self, batch_id):
        batch = self.client.batches.retrieve(batch_id)
        output_file_id = batch.output_file_id
        if not output_file_id:
            raise Exception("Batch file is not ready for retrieval yet.")
        return self.client.files.content(output_file_id).text
