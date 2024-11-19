from rest_framework import serializers
from django.contrib.auth.models import User  # or your custom user model
from django.contrib.auth import authenticate

#create your serializers here
# myapp/serializers.py
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(**data)
        if user:
            if not user.is_active:
                raise serializers.ValidationError("User is deactivated.")
            return user
        raise serializers.ValidationError("Unable to log in with provided credentials.")
