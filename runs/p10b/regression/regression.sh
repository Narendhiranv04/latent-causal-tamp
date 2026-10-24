set -u
python run.py replay --run runs/g1_robot --report runs/p10b/regression/replay_g1_robot.json > runs/p10b/regression/replay_g1_robot.log 2>&1; echo "g1_robot $?" >> runs/p10b/regression/replay_exit.txt
python run.py replay --run runs/g1_hardening --report runs/p10b/regression/replay_g1_hardening.json > runs/p10b/regression/replay_g1_hardening.log 2>&1; echo "g1_hardening $?" >> runs/p10b/regression/replay_exit.txt
python run.py replay --run runs/g2_interventions --report runs/p10b/regression/replay_g2_interventions.json > runs/p10b/regression/replay_g2_interventions.log 2>&1; echo "g2_interventions $?" >> runs/p10b/regression/replay_exit.txt
python run.py replay --run runs/g3_repairs --report runs/p10b/regression/replay_g3_repairs.json > runs/p10b/regression/replay_g3_repairs.log 2>&1; echo "g3_repairs $?" >> runs/p10b/regression/replay_exit.txt
python run.py replay --run runs/g3_5_initial_scene --report runs/p10b/regression/replay_g3_5_initial_scene.json > runs/p10b/regression/replay_g3_5_initial_scene.log 2>&1; echo "g3_5_initial_scene $?" >> runs/p10b/regression/replay_exit.txt
python run.py replay --run runs/g4a_evidence_audit --report runs/p10b/regression/replay_g4a_evidence_audit.json > runs/p10b/regression/replay_g4a_evidence_audit.log 2>&1; echo "g4a_evidence_audit $?" >> runs/p10b/regression/replay_exit.txt
COUNT_OUT=runs/p10b/regression/calls.json PROGRESS=runs/p10b/regression/progress.jsonl PYTHONPATH=runs/p10b/regression python -m pytest -q -p countcalls tests > runs/p10b/regression/pytest.log 2>&1; echo "pytest $?" >> runs/p10b/regression/pytest_exit.txt
