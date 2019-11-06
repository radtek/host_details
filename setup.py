"""
Copyright 2019 Skytap Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from setuptools import setup, find_packages

test_deps = ["coverage",
             "nose",
             "nose-parameterized",
             "mock"]

setup(
    name='host_details',
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    author="Daniel Myers",
    author_email="dmyers@skytap.com",
    license='proprietary',
    url="https://github.com/skytap/host_details",
    extra_requires={
        "test": test_deps
    },
    install_requires=["parameterized",
                      'pyyaml>=3',
                      'Device42',
                      ],
)
