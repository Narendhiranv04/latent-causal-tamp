"""Reporting fixtures: missing evidence must not become fabricated percentages."""
import importlib.util
import json
from pathlib import Path
import pytest

script = Path(__file__).resolve().parents[1] / 'reports/stage2/report_physical_release.py'
spec = importlib.util.spec_from_file_location('physical_report', script)
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def setup(tmp_path):
    release, metrics, training = [tmp_path / name for name in ('release', 'metrics', 'training')]
    for path in (release, metrics, training):
        path.mkdir()
    write(release/'APPROVED_ENVELOPE.json', dict(host='girish-laptop',global_adapter_call_ceiling=5523,
        ceilings={d:dict(val=3600, test=3600) for d in ('2d','3d')}))
    write(metrics/'FINAL_METRICS.json', dict(metrics={}, paired={}))
    write(training/'RESOURCE_TOTALS.json', dict(recorded_E16_subtotal=dict(cpu_s=10.,active_wall_s=12.)))
    write(training/'STAGE2_FINAL_STATUS.json', dict(gates={}))
    (training/'PAPER_METHODS_AND_RESULTS.md').write_text('Method.\nFinal evaluation is proposed with pending results.')
    return release, metrics, training


def test_missing_test_is_not_zero_success_or_completed(tmp_path):
    paths = setup(tmp_path)
    out = R.report(*paths)
    assert out['physical_status'] == 'PARTIAL_OR_NOT_RUN'
    text = (paths[1]/'FINAL_DISCO_STAGE2_REPORT.md').read_text()
    assert '| 2D | O0 open loop | NOT_RUN |' in text
    assert 'No selection freeze exists' in text
    assert '0.00%' not in text
    assert 'Final evaluation is proposed' not in (paths[1]/'PAPER_METHODS_AND_RESULTS.md').read_text()


def test_unknowns_keep_full_denominator_and_never_hide_in_ci():
    cell = R.measured_cell(dict(status='PARTIAL',n_verified_success=1,
        n_expected_predictions=45,success_rate=1/45,ci95=[0.,.1],
        n_roots=15,n_unresolved_or_unexecuted=9))
    assert '1/45 = 2.22%' in cell and '15 roots; unknown 9' in cell


def test_reporting_refuses_over_budget_evidence(tmp_path):
    paths = setup(tmp_path)
    write(paths[0]/'val_2d/ACCOUNTING.json',dict(cpu_s=3601.,active_wall_s=1.,
        adapter_calls=1,n_attempted=1,n_not_run=0))
    with pytest.raises(ValueError, match='approved ceiling'):
        R.report(*paths)


def test_reporting_refuses_multiple_test_thresholds(tmp_path):
    paths = setup(tmp_path)
    write(paths[1]/'FINAL_METRICS.json',dict(metrics={
        'test|2d|open_loop|O0_P2Q2|0.0':{},
        'test|2d|open_loop|O0_P2Q2|0.15':{}},paired={}))
    with pytest.raises(ValueError,match='Multiple TEST thresholds'):
        R.report(*paths)


def test_unexecuted_or_all_unknown_paired_arms_have_no_point_estimate():
    import sys
    sys.path.insert(0,str(script.parents[2]))
    spec=importlib.util.spec_from_file_location('analysis_report',script.with_name('analyze_evaluation.py'))
    A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
    roots=[dict(root_id='a',family_id='a',K_legacy='1')]
    empty=A.paired_evidence([],[],roots,[0],bootstrap=10)
    assert empty['status']=='NOT_RUN' and empty['delta'] is None and empty['ci95'] is None
    unknown=[dict(root_id='a',seed=0,domain='2d',status='UNRESOLVED',verified=None)]
    censored=A.paired_evidence(unknown,unknown,roots,[0],bootstrap=10)
    assert censored['status']=='UNRESOLVED' and censored['delta'] is None
    assert censored['unresolved_sensitivity']==[-1.,1.]


def test_host_continuation_charges_cancelled_child_and_preserves_job_identity(tmp_path):
    import sys
    sys.path.insert(0,str(script.parents[2]))
    spec=importlib.util.spec_from_file_location('laptop_continuation',script.with_name('continue_physical_laptop.py'))
    L=importlib.util.module_from_spec(spec);spec.loader.exec_module(L)
    prior=tmp_path/'prior';launch=tmp_path/'launch.json'
    write(launch,dict(utc='1970-01-01T00:00:00+00:00'))
    for i,(cpu,end) in enumerate(((2.,10.),(4.,20.))):
        d=prior/'val_2d'/str(i)
        write(d/'WATCHDOG_ACCOUNTING.json',dict(reaped_child_cpu_s=cpu,wall_time_end=end,wall_s=10.))
        (d/'queries.jsonl').write_text(json.dumps(dict(event='started'))+'\n')
    cost=L.previous_cost(prior,launch)
    assert cost['worker_cpu_s']==6. and cost['cpu_s']==26. and cost['active_wall_s']==20.
    assert cost['adapter_calls']==2 and cost['exact_final_controller_cpu_s'] is None
    job=dict(id='fixed',policy='/scratch/nav/disco_grid/p.pt',
        prediction=dict(seq=[[1,4]],status='REPAIR'),teacher_sources={'/home/nav/teacher.py':'hash'})
    moved=L.relocated(job,tmp_path/'rootfs')
    assert moved['id']==job['id'] and moved['prediction']==job['prediction']
    assert moved['policy'].startswith(str(tmp_path/'rootfs'))
    assert job['policy']=='/scratch/nav/disco_grid/p.pt'
