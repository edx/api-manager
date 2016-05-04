"""
Tests for scripts/aws/flip.py
"""
import boto3
import pytest
from moto import mock_apigateway
from unittest import TestCase
from flip import get_live_stage, update_base_path_mapping


class FlipTest(TestCase):
    """
    TestCase class for testing flip.py
    """

    def setUp(self):
        self.api_base_domain = 'api.fake-host.com'
        self.rotation = ['red', 'black', 'turquoise']
        self.current_stage = 'black'
        self.next_stage = 'turquoise'

    @pytest.mark.skip(reason="moto does not yet support AWS:ApiGateway:GetBasePathMapping")
    def test_get_live_stage(self):
        pass

    @pytest.mark.skip(reason="moto does not yet support AWS:ApiGateway:UpdateBasePathMapping")
    def test_update_base_path_mapping(self):
        pass
