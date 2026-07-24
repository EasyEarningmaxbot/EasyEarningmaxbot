import random
import string

# ⚡ Pre-defined Lists & Constants (মেমোরি লোড কমানোর জন্য)
PREFIXES = ['rohrz', 'vany', 'zax', 'bren', 'krish', 'miko', 'trix', 'jolt', 'zeno', 'falk']
FIRST_NAMES = ["Rahim", "Karim", "Sujon", "Tanvir", "Sabbir", "Arif", "Nayeem", "Hasan", "Mehedi", "Sakib", "Rana", "Fahim"]
LAST_NAMES = ["Ahmed", "Khan", "Chowdhury", "Hossain", "Islam", "Sheikh", "Uddin", "Rahman", "Miah", "Sarkar"]

ASCII_LOWER = string.ascii_lowercase
DIGITS = string.digits


def generate_uncommon_username() -> str:
    """
    আনকমন ইউজারনেম জেনারেটর (Ultra-Fast)
    """
    prefix = random.choice(PREFIXES)
    suffix_letters = "".join(random.choices(ASCII_LOWER, k=2))
    suffix_numbers = "".join(random.choices(DIGITS, k=3))
    return f"{prefix}{suffix_letters}{suffix_numbers}"


def generate_first_name() -> str:
    """
    ফার্স্ট নেম জেনারেটর
    """
    return random.choice(FIRST_NAMES)


def generate_last_name() -> str:
    """
    লাস্ট নেম জেনারেটর
    """
    return random.choice(LAST_NAMES)
