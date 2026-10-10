"""Public protocol checks; contains no task solutions or grading fixtures."""
import argparse
import json
from pathlib import Path
import sys
import urllib.request

from openenv.core import GenericEnvClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://localhost:8000')
    parser.add_argument('--bank', default='workflow_lab/frozen_tasks.json')
    args = parser.parse_args()
    url = args.url.rstrip('/')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from workflow_lab.task_bank import tasks, release_revision
    from workflow_lab.schemas import WorkflowAction, WorkflowObservation

    rows = tasks()
    with urllib.request.urlopen(url + '/schema', timeout=15) as response:
        schema = json.load(response)
    assert schema['action'] == WorkflowAction.model_json_schema()
    assert schema['observation'] == WorkflowObservation.model_json_schema()
    checked = []
    for row in rows:
        with GenericEnvClient(base_url=url).sync() as client:
            result = client.reset(task_id=row['task_id'])
            initial = result.observation
            assert not result.done
            assert initial['task_id'] == row['task_id']
            assert initial['data']['difficulty'] == row['level']
            result = client.step({'op': 'finish'})
            assert result.done and result.reward == 0
        with GenericEnvClient(base_url=url).sync() as client:
            client.reset(task_id=row['task_id'])
            result = client.step({'op': 'commit'})
            assert result.done and result.reward == 0, row['task_id']
        checked.append(row['task_id'])
    print(json.dumps({'release_revision': release_revision(), 'schema': schema,
                      'terminal_tasks': checked, 'unperformed_work_reward': 0}))


if __name__ == '__main__':
    main()
