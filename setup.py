from setuptools import find_packages, setup

package_name = 'latency_test_py'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='odiseo',
    maintainer_email='fjrodl@unileon.es',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
    'console_scripts': [
        'publisher_latency = latency_test_py.publisher_latency:main',
        'subscriber_latency = latency_test_py.subscriber_latency:main',
        'publisher_latency_qos = latency_test_py.publisher_latency_qos:main',
        'subscriber_latency_qos = latency_test_py.subscriber_latency_qos:main',
        'subscriber_latency_plot = latency_test_py.subscriber_latency_plot:main',
    ],
    },


)
