from PIL import Image
from io import BytesIO
import subprocess
import hashlib
import base64
import string

def hash_tuple_simple(input_tuple):
    # Serialize the tuple into a string
    serialized = str(input_tuple)
    
    # Generate a md5 hash of the serialized string
    hash_value = hashlib.md5(serialized.encode()).digest()
    
    # Encode the hash using Base36 (alphanumeric)
    hash_base36 = base36_encode(int.from_bytes(hash_value, 'big'))
    
    return hash_base36

def base36_encode(number, alphabet=string.digits + string.ascii_lowercase):
    """
    Converts an integer to a base36 string.
    https://stackoverflow.com/a/1181922/1718155
    """
    if not isinstance(number, int):
        raise TypeError('number must be an integer')
 
    base36 = ''
    sign = ''
 
    if number < 0:
        sign = '-'
        number = -number
 
    if 0 <= number < len(alphabet):
        return sign + alphabet[number]
 
    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36
 
    return sign + base36

def get_git_username():
    res = subprocess.run(["git", "config", "user.email"], stdout=subprocess.PIPE)
    git_username = res.stdout.strip().decode()
    # If there is an error, raise it
    if res.returncode != 0:
        raise Exception("Error getting git username; please provide an author.")
    return git_username

def partial_dict_key_match(key: str, dictionary: dict) -> dict:
    """
    Returns a dictionary with keys that partially match the input key.
    """
    return [k for k, v in dictionary.items() if k.startswith(key)]


def resize_and_get_base64(image_path: str, size: int):
    # Open the image file
    with Image.open(image_path) as img:
        # Resize the image
        img = img.resize((size, size))
        
        # Save the image to a BytesIO object in PNG format
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        
        # Get the base64 encoded string
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
    return img_base64

