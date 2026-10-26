set -u
python run.py replay --run runs/g1_robot --report runs/p16/regression0/replay_g1_robot.json > runs/p16/regression0/replay_g1_robot.log 2>&1; echo "g1_robot $?" >> runs/p16/regression0/replay_exit.txt
python run.py replay --run runs/g1_hardening --report runs/p16/regression0/replay_g1_hardening.json > runs/p16/regression0/replay_g1_hardening.log 2>&1; echo "g1_hardening $?" >> runs/p16/regression0/replay_exit.txt
python run.py replay --run runs/g2_interventions --report runs/p16/regression0/replay_g2_interventions.json > runs/p16/regression0/replay_g2_interventions.log 2>&1; echo "g2_interventions $?" >> runs/p16/regression0/replay_exit.txt
python run.py replay --run runs/g3_repairs --report runs/p16/regression0/replay_g3_repairs.json > runs/p16/regression0/replay_g3_repairs.log 2>&1; echo "g3_repairs $?" >> runs/p16/regression0/replay_exit.txt
python run.py replay --run runs/g3_5_initial_scene --report runs/p16/regression0/replay_g3_5_initial_scene.json > runs/p16/regression0/replay_g3_5_initial_scene.log 2>&1; echo "g3_5_initial_scene $?" >> runs/p16/regression0/replay_exit.txt
python run.py replay --run runs/g4a_evidence_audit --report runs/p16/regression0/replay_g4a_evidence_audit.json > runs/p16/regression0/replay_g4a_evidence_audit.log 2>&1; echo "g4a_evidence_audit $?" >> runs/p16/regression0/replay_exit.txt
COUNT_OUT=runs/p16/regression0/calls.json PROGRESS=runs/p16/regression0/progress.jsonl PYTHONPATH=runs/p16/regression0 python -m pytest -q -p countcalls tests > runs/p16/regression0/pytest.log 2>&1; echo "pytest $?" >> runs/p16/regression0/pytest_exit.txt
