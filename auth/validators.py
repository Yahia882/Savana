import re
from rest_framework import serializers
def validate_email_or_phonenumber(data):
    phone_regex = r"^\+?[1-9]\d{1,14}$"
    if data[0] == "+":
        if not re.match(phone_regex,data):
            raise serializers.ValidationError("this is not a valid number")
    else:
        email_regex = r"^[\w\.-]+@[a-zA-Z\d\.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex,data):
            raise serializers.ValidationError("this is not a valid email")
    
    return data