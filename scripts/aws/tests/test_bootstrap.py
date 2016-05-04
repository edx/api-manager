"""
Tests for scripts/aws/bootstrap.py
"""
import boto3
import pytest
from moto import mock_apigateway, mock_route53
from unittest import TestCase
from bootstrap import get_domain, get_base_path, create_apigw_custom_domain_name,\
    create_route53_rs, bootstrap_api, create_base_path_mapping, file_arg_to_string


class BootstrapTest(TestCase):
    """
    TestCase class for testing bootstrap.py
    """

    def setUp(self):
        self.api_base_domain = 'api.fake-host.com'
        self.cloudfront_zone = 'fake-zone'
        self.distribution_name = 'fake-distro'

    @pytest.mark.skip(reason="moto does not yet support AWS:ApiGateway:GetDomainName")
    def test_get_domain(self):
        pass

    @pytest.mark.skip(reason="moto does not yet support AWS:ApiGateway:GetBasePathMapping")
    def test_get_base_path(self):
        pass

    @pytest.mark.skip(reason="moto does not yet support AWS:ApiGateway:CreateDomainName")
    def test_create_apigw_custom_domain_name(self):
        pass

    @pytest.mark.skip(reason="moto does not yet support AWS:Route53:ChangeResourceRecordSets")
    def test_create_route53_rs(self):
        pass
