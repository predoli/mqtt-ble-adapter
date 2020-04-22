from setuptools import setup, find_packages


setup(
    name='mqtt-ble-adapter',
    version='0.1',
    packages=find_packages(),
    entry_points={
    "console_scripts": [
        "run-mqtt-ble-adapter = Scripts.runMainController:main",
    ]
}
)