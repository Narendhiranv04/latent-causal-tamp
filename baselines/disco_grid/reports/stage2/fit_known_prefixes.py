"""TRAIN-only final P2 fits adding certified pre-interruption iteration prefixes.

Frozen before VAL/TEST. Same P1 initialization, engine, epochs, seeds, Q targets
and O0/O1 supervision as E16. Retain original clean-only P2 as an ablation. All
prior/new fits and controller costs count toward the original 1800-second cap.
"""
import argparse, fcntl, importlib, json, os, pickle, sys, time
from pathlib import Path
from continue_e16 import live_child_cpu, charged_totals


def read(p):return json.loads(p.read_text())


def run(engine,campaign,recovered,controller_commit):
    began=time.monotonic();sys.path.insert(0,str(engine));CA=importlib.import_module('campaign');C=CA.C;D=CA.D;J=CA.J;P=CA.P
    if not (campaign/'continuation_001/COMPLETE.json').exists():raise RuntimeError('Collection still active')
    approved=read(campaign/'manifest.json')['envelope'];CA.validate_authorization(approved,engine/'reports/stage2/cohorts.json')
    prior=read(campaign/'continuation_001/COMPLETE.json')['controller_overhead'];original_accounting=CA.accounting
    if not recovered.resolve().is_relative_to(campaign.resolve()):raise ValueError('Recovery outside approved disk budget')
    records=read(recovered/'manifest.json')['records'];out=campaign/'known_prefix_fit';out.mkdir(exist_ok=False)
    baseline_wall=original_accounting(campaign,training=True)['wall_s']
    J.atomic_json(out/'manifest.json',dict(controller_commit=controller_commit,script_sha256=D.sha256_file(__file__),
        recovery_manifest_sha256=D.sha256_file(recovered/'manifest.json'),protocol='P2 known-iteration-prefix augmentation frozen before VAL/TEST',
        source_engine_commit=read(campaign/'manifest.json')['source_commit'],initialization='same all-feasible P1 by schema/seed; successful-only affects current policy rows',
        limits=approved['neural_training'],no_new_physics=True))
    def overhead():
        pending=list(campaign.glob('training/*/attempts/*/START.json'))
        active=sum(max(0.,time.monotonic()-read(p)['monotonic_start']) for p in pending if not (p.parent/'WATCHDOG_ACCOUNTING.json').exists())
        return dict(cpu_s=prior['cpu_s']+time.process_time(),wall_s=prior['wall_s']+max(0.,time.monotonic()-began-(original_accounting(campaign,training=True)['wall_s']-baseline_wall)-active))
    def charged(root,domain=None,training=False):return charged_totals(original_accounting(root,domain,training),overhead())
    def resources(root,e):
        r=C.require_headroom()
        if charged(root,training=True)['cpu_s']+live_child_cpu()>=e['neural_training']['cpu_s_cap']-6:raise RuntimeError('AGGREGATE_FIT_CPU_LIMIT')
        if sum(p.stat().st_size for p in root.rglob('*') if p.is_file())>e['new_disk_ceiling_gib']*2**30:raise RuntimeError('CAMPAIGN_DISK_LIMIT')
        return r
    CA.accounting=charged;CA.checked_resources=resources
    with (campaign/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for dom in ('2d','3d'):
            try:
                streams=[];provenance=[]
                for rnd in range(2):
                    dirs=[]
                    for p in sorted((campaign/f'trees/{dom}/R{rnd}').glob('*/ATTEMPT_COMPLETE.json')):
                        status=read(p)
                        if status['clean']:dirs.append(Path(status['tree']))
                    for record in records:
                        if record['status']=='CERTIFIED_COMPLETED_ITERATION_PREFIX':
                            td=Path(record['destination'])
                            if td.parent.parent.name==dom and td.parent.name==f'R{rnd}':dirs.append(td)
                    dirs=sorted(dirs)
                    for td in dirs:
                        if (td/'IN_FLIGHT').exists() or (td/'ACTIVE_QUERY.json').exists():raise ValueError('Unreconciled training input')
                        if D.sha256_file(td/'checkpoint.pkl')!=(td/'checkpoint.sha256').read_text():raise ValueError('Checkpoint integrity')
                        ck=pickle.loads((td/'checkpoint.pkl').read_bytes());J.certify_journal(td,ck['sim_transition_calls']+ck['sim_terminal_calls'])
                        provenance.append(dict(path=str(td),checkpoint_sha256=D.sha256_file(td/'checkpoint.pkl'),journal_sha256=D.sha256_file(td/'queries.jsonl'),
                            round=f'R{rnd}',recovered_prefix=(td/'RECOVERY_PROVENANCE.json').exists(),root_id=ck['summary']['root_id']))
                    if not dirs:raise RuntimeError('No eligible round supervision')
                    streams.append([str(p) for p in dirs])
                J.atomic_json(out/f'{dom}_data.json',dict(trees=provenance,independent_roots=len({r['root_id'] for r in provenance})))
                if not any(r['recovered_prefix'] for r in provenance):
                    J.atomic_json(out/f'{dom}_NO_AUGMENTATION.json',dict(reason='No recoverable completed iteration prefixes; original P2 retained'));continue
                fit=campaign/f'training/{dom}_P2Q2_knownprefix';previous=campaign/f'training/{dom}_P1Q1'
                if not (previous/'COMPLETE.json').exists():raise RuntimeError('Missing fully completed P1; cannot claim full cycle')
                CA.dispatch_fit(dom,fit,streams,previous,approved,campaign)
                import torch
                for seed in (0,1,2):
                    a=CA.DS.load_value_checkpoint(fit/f'{P.O0}_all_feasible_s{seed}/value.pt','cpu')[0]
                    b=CA.DS.load_value_checkpoint(fit/f'{P.O0}_successful_only_s{seed}/value.pt','cpu')[0]
                    if any(not torch.equal(v,b.state_dict()[k]) for k,v in a.state_dict().items()):raise RuntimeError('Policy-edge control changed Q weights')
                J.atomic_json(out/f'{dom}_COMPLETE.json',dict(final_fit=str(fit),physical_task_success='NOT_RUN',q_edge_control='bitwise-identical Q weights, seeds 0/1/2',charged_neural_cost_upper_bound=charged(campaign,training=True)))
            except Exception as error:
                J.atomic_json(out/f'{dom}_BLOCKED.json',dict(error=type(error).__name__,reason=str(error),charged_neural_cost_upper_bound=charged(campaign,training=True)))
        J.atomic_json(out/'COMPLETE.json',dict(controller_overhead=overhead(),charged_neural_cost_upper_bound=charged(campaign,training=True)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--engine',type=Path,required=True);p.add_argument('--campaign',type=Path,required=True);p.add_argument('--recovered',type=Path,required=True);p.add_argument('--controller-commit',required=True);a=p.parse_args();run(a.engine,a.campaign,a.recovered,a.controller_commit)
