"""kr-scenario-analyzer: JSON 리포트 생성."""

import json
import os
from datetime import datetime


class ScenarioReportGenerator:

    def __init__(self, output_dir: str = './output'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_json(self, result: dict) -> str:
        report = {
            'skill': 'kr-scenario-analyzer',
            'generated_at': datetime.now().isoformat(),
            'result': result,
        }
        filepath = os.path.join(self.output_dir,
                                'kr_scenario_analysis.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return filepath
