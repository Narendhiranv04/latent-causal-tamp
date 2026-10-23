cd /home/naren/Desktop/boltzmann_lfd
for i in 1 2 3 4; do
  OMP_NUM_THREADS=1 python -c "
import p10_protocol as p, json
print(json.dumps(p.job('p10a_collect_chunk$i', 'collect(1600.0)', 1790.0, module='p10_collect', category='teacher', wall=3600)))
" 2>&1 | tail -1 | cut -c1-300
  python -c "import json; d=json.load(open('runs/p10/p10a/progress.json')); print('done', len(d['done']), 'finished', d.get('finished'))"
  python -c "import json,sys; sys.exit(0 if json.load(open('runs/p10/p10a/progress.json')).get('finished') else 1)" && break
  python -c "import p10_protocol as p,sys; sys.exit(0 if p.CAPS['teacher']-p.spent('teacher')[0] > 130 else 1)" || break
done
echo COLLECT_END
