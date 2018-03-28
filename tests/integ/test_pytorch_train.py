# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import os
import time
import pytest
from sagemaker.pytorch.estimator import PyTorch
from sagemaker.utils import sagemaker_timestamp
from tests.integ import DATA_DIR
from tests.integ.timeout import timeout, timeout_and_delete_endpoint_by_name

MNIST_DIR = os.path.join(DATA_DIR, 'pytorch_mnist')
MNIST_SCRIPT = os.path.join(MNIST_DIR, 'mnist.py')


@pytest.fixture(scope='module', name='pytorch_training_job')
def fixture_training_job(sagemaker_session, pytorch_full_version):
    with timeout(minutes=15):
        pytorch = PyTorch(entry_point=MNIST_SCRIPT, role='SageMakerRole', framework_version=pytorch_full_version,
                          train_instance_count=1, train_instance_type='ml.c4.xlarge',
                          sagemaker_session=sagemaker_session)

        pytorch.fit({'training': _upload_training_data(pytorch)})
        return pytorch.latest_training_job.name


def test_attach_deploy(pytorch_training_job, sagemaker_session):
    endpoint_name = 'test-pytorch-attach-deploy-{}'.format(sagemaker_timestamp())

    with timeout_and_delete_endpoint_by_name(endpoint_name, sagemaker_session, minutes=20):
        PyTorch.attach(pytorch_training_job, sagemaker_session=sagemaker_session)


def test_async_fit(sagemaker_session, pytorch_full_version):
    training_job_name = ""
    endpoint_name = 'test-pytorch-attach-deploy-{}'.format(sagemaker_timestamp())

    with timeout(minutes=10):
        pytorch = PyTorch(entry_point=MNIST_SCRIPT, role='SageMakerRole', framework_version=pytorch_full_version,
                          train_instance_count=1, train_instance_type='ml.c4.xlarge',
                          sagemaker_session=sagemaker_session)

        pytorch.fit({'training': _upload_training_data(pytorch)}, wait=False)
        training_job_name = pytorch.latest_training_job.name

        print("Waiting to re-attach to the training job: %s" % training_job_name)
        time.sleep(20)

    with timeout_and_delete_endpoint_by_name(endpoint_name, sagemaker_session, minutes=35):
        print("Re-attaching now to: %s" % training_job_name)
        PyTorch.attach(training_job_name=training_job_name, sagemaker_session=sagemaker_session)


def test_failed_training_job(sagemaker_session, pytorch_full_version):
    script_path = os.path.join(MNIST_DIR, 'failure_script.py')

    with timeout(minutes=15):
        pytorch = PyTorch(entry_point=script_path, role='SageMakerRole', framework_version=pytorch_full_version,
                          train_instance_count=1, train_instance_type='ml.c4.xlarge',
                          sagemaker_session=sagemaker_session)

        with pytest.raises(ValueError) as e:
            pytorch.fit(_upload_training_data(pytorch))
        assert 'This failure is expected' in str(e.value)


def _upload_training_data(pytorch):
    return pytorch.sagemaker_session.upload_data(path=os.path.join(MNIST_DIR, 'training'),
                                                 key_prefix='integ-test-data/pytorch_mnist/training')