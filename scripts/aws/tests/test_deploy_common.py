"""
Tests for scripts/aws/common/deploy.py
"""
import boto3
import pytest
from moto import mock_aws
from unittest import TestCase
from common.deploy import get_api_id, get_next_stage, deploy_api, update_stage


class DeployTest(TestCase):
    """
    TestCase class for testing deploy.py
    """

    @mock_aws
    def setUp(self):
        self.rotation = ['red', 'black', 'turquoise']
        self.current_stage = 'black'
        self.api_base_domain = 'api.fake-host.com'
        self.swagger_filename = 'fixtures/swagger.json'

    @pytest.mark.skip(reason="moto does not yet support AWS:ApiGateway:GetBasePathMapping")
    @mock_aws
    def test_get_api_id(self):
        pass

    # Test the ring-based iteration logic
    def test_get_next_stage(self):

        # list of {current: next} keypairs
        expected_rotations = [
            {'current': 'red', 'next': 'black'},
            {'current': 'black', 'next': 'turquoise'},
            {'current': 'turquoise', 'next': 'red'},
            {'current': 'not-in-rotation', 'next': 'red'}
        ]

        for expected_rotation in expected_rotations:
            actual_next_stage = get_next_stage(self.rotation, expected_rotation['current'])
            self.assertEqual(expected_rotation['next'], actual_next_stage)

        # test behavior with a bad rotation
        with self.assertRaises(ValueError):
            get_next_stage([], 'red')

    @pytest.mark.skip(reason="moto does not yet support AWS:ApiGateway:PutRestApi")
    @mock_aws
    def test_deploy_api(self):
        pass

    @pytest.mark.skip(reason="moto does not yet support AWS:ApiGateway:UpdateStage")
    @mock_aws
    def test_update_stage(self):
        pass
