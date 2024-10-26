from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers
from phonenumber_field.phonenumber import PhoneNumber,validate_region
import json
class phonefield(serializers.CharField):
    def to_internal_value(self, data):
        Data = json.loads(data)
        region = Data.get("region")
        number = Data.get("number")
        validate_region(region)
        if region:
            value = PhoneNumberField(region=region)
            return value.to_internal_value(number)
        
        value = PhoneNumberField()
        return value.to_internal_value(number)
    
    def to_representation(self, value):
        return str(value)
