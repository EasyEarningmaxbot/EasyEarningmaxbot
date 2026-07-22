import random
import string

def generate_uncommon_username():
    prefixes = ['rohrz', 'vany', 'zax', 'bren', 'krish', 'miko', 'trix', 'jolt', 'zeno', 'falk']
    suffix_letters = "".join(random.choices(string.ascii_lowercase, k=2))
    suffix_numbers = "".join(random.choices(string.digits, k=3))
    return f"{random.choice(prefixes)}{suffix_letters}{suffix_numbers}"

def generate_first_name():
    first_names = ["Rahim", "Karim", "Sujon", "Tanvir", "Sabbir", "Arif", "Nayeem", "Hasan", "Mehedi", "Sakib", "Rana", "Fahim"]
    return random.choice(first_names)

def generate_last_name():
    last_names = ["Ahmed", "Khan", "Chowdhury", "Hossain", "Islam", "Sheikh", "Uddin", "Rahman", "Miah", "Sarkar"]
    return random.choice(last_names)
