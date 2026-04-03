# Updated dashboard_generator.py

import os
import yaml
from sensor import SENSOR_DEFINITIONS

class DashboardGenerator:
    def __init__(self):
        self.dashboard = {
            'tabs': [],
        }

    def generate_dashboard(self):
        self.organize_sensors()  
        return yaml.dump(self.dashboard)

    def organize_sensors(self):
        # Organize sensors by categories
        categories = {}
        for sensor in SENSOR_DEFINITIONS:
            category = sensor.get('category', 'Uncategorized')
            if category not in categories:
                categories[category] = []
            categories[category].append(sensor)

        for category, sensors in categories.items():
            self.dashboard['tabs'].append({
                'title': category,
                'sensors': [self.create_sensor_widget(sensor) for sensor in sensors],
            })

    def create_sensor_widget(self, sensor):
        return {
            'id': sensor['id'],
            'type': sensor['type'],
            'editable': True,
            'name': sensor['name'],
            'control': {
                'min': sensor.get('min', 0),
                'max': sensor.get('max', 100),
                'unit_of_measure': sensor.get('unit', 'N/A'),
            }
        }

if __name__ == '__main__':
    generator = DashboardGenerator()
    print(generator.generate_dashboard())