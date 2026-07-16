from better_profanity import Profanity
from django.core.exceptions import ValidationError
import os

profanity= Profanity()
words_path = os.path.join(os.path.dirname(__file__),'profanity_words.txt')
if os.path.exists(words_path):
    with open(words_path,encoding='utf-8') as f:
        custom_words = [line.strip() for line in f if line.strip()]
    profanity.load_censor_words(custom_words=custom_words)

def validate_no_profanity(value):
    if profanity.contains_profanity(value):
        raise ValidationError('Текст содержит недопустимые выражения(не грубите)')