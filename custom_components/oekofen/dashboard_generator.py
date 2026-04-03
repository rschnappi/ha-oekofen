import yaml

# Sample SENSOR_DEFINITIONS for demonstration purposes
SENSOR_DEFINITIONS = {
    'sensor1': {'name': 'Temperature', 'unit': '°C', 'icon': 'mdi:thermometer'},
    'sensor2': {'name': 'Humidity', 'unit': '%', 'icon': 'mdi:water-percent'},
    # Add more sensors as needed
}

def generate_dashboard_yaml(sensor_definitions):
    dashboard = {'type': 'custom:dashboard', 'cards': []}
    
    for sensor_id, sensor_info in sensor_definitions.items():
        card = {
            'type': 'sensor',
            'entity': f'sensor.{sensor_id}',
            'name': sensor_info['name'],
            'unit': sensor_info['unit'],
            'icon': sensor_info['icon'],
        }
        dashboard['cards'].append(card)
    
    return yaml.dump(dashboard)

if __name__ == '__main__':
    print(generate_dashboard_yaml(SENSOR_DEFINITIONS))
