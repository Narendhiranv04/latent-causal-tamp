set -u
python run.py replay --run runs/g1_robot --report runs/p11/regression/replay_g1_robot.json > runs/p11/regression/replay_g1_robot.log 2>&1; echo "g1_robot $?" >> runs/p11/regression/replay_exit.txt
python run.py replay --run runs/g1_hardening --report runs/p11/regression/replay_g1_hardening.json > runs/p11/regression/replay_g1_hardening.log 2>&1; echo "g1_hardening $?" >> runs/p11/regression/replay_exit.txt
python run.py replay --run runs/g2_interventions --report runs/p11/regression/replay_g2_interventions.json > runs/p11/regression/replay_g2_interventions.log 2>&1; echo "g2_interventions $?" >> runs/p11/regression/replay_exit.txt
python run.py replay --run runs/g3_repairs --report runs/p11/regression/replay_g3_repairs.json > runs/p11/regression/replay_g3_repairs.log 2>&1; echo "g3_repairs $?" >> runs/p11/regression/replay_exit.txt
python run.py replay --run runs/g3_5_initial_scene --report runs/p11/regression/replay_g3_5_initial_scene.json > runs/p11/regression/replay_g3_5_initial_scene.log 2>&1; echo "g3_5_initial_scene $?" >> runs/p11/regression/replay_exit.txt
python run.py replay --run runs/g4a_evidence_audit --report runs/p11/regression/replay_g4a_evidence_audit.json > runs/p11/regression/replay_g4a_evidence_audit.log 2>&1; echo "g4a_evidence_audit $?" >> runs/p11/regression/replay_exit.txt
COUNT_OUT=runs/p11/regression/calls.json PROGRESS=runs/p11/regression/progress.jsonl PYTHONPATH=runs/p11/regression python -m pytest -q -p countcalls tests > runs/p11/regression/pytest.log 2>&1; echo "pytest $?" >> runs/p11/regression/pytest_exit.txt
