set -u
python run.py replay --run runs/g1_robot --report runs/p13/regression/replay_g1_robot.json > runs/p13/regression/replay_g1_robot.log 2>&1; echo "g1_robot $?" >> runs/p13/regression/replay_exit.txt
python run.py replay --run runs/g1_hardening --report runs/p13/regression/replay_g1_hardening.json > runs/p13/regression/replay_g1_hardening.log 2>&1; echo "g1_hardening $?" >> runs/p13/regression/replay_exit.txt
python run.py replay --run runs/g2_interventions --report runs/p13/regression/replay_g2_interventions.json > runs/p13/regression/replay_g2_interventions.log 2>&1; echo "g2_interventions $?" >> runs/p13/regression/replay_exit.txt
python run.py replay --run runs/g3_repairs --report runs/p13/regression/replay_g3_repairs.json > runs/p13/regression/replay_g3_repairs.log 2>&1; echo "g3_repairs $?" >> runs/p13/regression/replay_exit.txt
python run.py replay --run runs/g3_5_initial_scene --report runs/p13/regression/replay_g3_5_initial_scene.json > runs/p13/regression/replay_g3_5_initial_scene.log 2>&1; echo "g3_5_initial_scene $?" >> runs/p13/regression/replay_exit.txt
python run.py replay --run runs/g4a_evidence_audit --report runs/p13/regression/replay_g4a_evidence_audit.json > runs/p13/regression/replay_g4a_evidence_audit.log 2>&1; echo "g4a_evidence_audit $?" >> runs/p13/regression/replay_exit.txt
COUNT_OUT=runs/p13/regression/calls.json PROGRESS=runs/p13/regression/progress.jsonl PYTHONPATH=runs/p13/regression python -m pytest -q -p countcalls tests > runs/p13/regression/pytest.log 2>&1; echo "pytest $?" >> runs/p13/regression/pytest_exit.txt
