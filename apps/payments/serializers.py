from rest_framework import serializers
from .models import ServicePackage, Transaction

class ServicePackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePackage
        fields = '__all__'

class TransactionSerializer(serializers.ModelSerializer):
    package_name = serializers.CharField(source='package.name', read_only=True)
    
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['user', 'amount', 'status', 'transaction_code', 'created_at']