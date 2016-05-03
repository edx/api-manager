"""
Tests for scripts/aws/deploy.py
"""
import boto3
import pytest
from moto import mock_apigateway
from unittest import TestCase
from deploy import get_api_id, get_next_stage, deploy_api, update_stage


class DeployTest(TestCase):
    """
    TestCase class for testing deploy.py
    """

    @mock_apigateway
    def setUp(self):
        self.access_key = 'fake-access-key'
        self.secret_key = 'fake-secret-key'
        self.rotation = ['red', 'black', 'turquoise']
        self.client = boto3.client('apigateway', 'us-east-1')
        self.rest_api = self.client.create_rest_api(name='test', description='desc')

    @pytest.mark.skip(reason="moto does not yet support AWS:ApiGateway:GetBasePathMapping")
    def test_get_api_id(self):
        pass

    # Test the ring-based iteration logic
    def test_get_next_stage(self):

        # list of {current: next} keypairs
        expected_rotations = [
            {'current': 'red', 'next': 'black'},
            {'current': 'black', 'next': 'turquoise'},
            {'current': 'turquoise', 'next': 'red'}
        ]

        for expected_rotation in expected_rotations:
            actual_next_stage = get_next_stage(self.rotation, expected_rotation['current'])
            self.assertEqual(expected_rotation['next'], actual_next_stage)

    @pytest.mark.xfail(raises=TypeError, reason="moto does not yet support AWS:ApiGateway:PutRestApi")
    @mock_apigateway
    def test_deploy_api(self):
        deploy_api(self.client, self.rest_api['id'], 'bootstrap.json', 'stage', {
            'key1': 'value1',
            'key2': 'value2'
        })

    @pytest.mark.skip(reason="moto does not yet support AWS:ApiGateway:UpdateStage")
    @mock_apigateway
    def test_update_stage(self):
        update_stage(self.client, self.rest_api['id'], 'stage', {
            'log_level': 'INFO',
            'metrics': 'true',
            'caching': 'false',
            'rate_limit': '9',
            'burst_limit': '9000'
        })
