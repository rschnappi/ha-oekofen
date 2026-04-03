import re

# Define a function to extract sensor definitions from sensor.py

def extract_sensor_definitions(sensor_file_path):
    with open(sensor_file_path, 'r') as file:
        content = file.read()

    # Use regex to find all SENSOR_DEFINITIONS
    sensor_definitions = re.findall(r'SENSOR_DEFINITION\s*:\s*\{(.*?)\}', content, re.DOTALL)
    return sensor_definitions

if __name__ == '__main__':
    # Specify the path to the sensor.py file
    sensor_file_path = 'path/to/sensor.py'  # Update this path accordingly
    sensor_definitions = extract_sensor_definitions(sensor_file_path)

    # Print or further process the extracted sensor definitions
    for definition in sensor_definitions:
        print(definition)