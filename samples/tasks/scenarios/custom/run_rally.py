import jinja2
import argparse
import tempfile
import os
import fnmatch
import subprocess
import sys
import yaml

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

@jinja2.contextfunction
def get_context(c):
  return c

def create_rally_input(fp, run_scenarios=None,
                       template_file='scenario.yaml',
                       scenario_directrory='scenarios'):

    jenv = jinja2.Environment(loader=jinja2.FileSystemLoader(THIS_DIR),
                         trim_blocks=True)
    if run_scenarios:
        scenarios = {
            scenario_directrory + '/' + x: os.path.splitext(x)[0]
            for x in os.listdir(scenario_directrory)
                if os.path.isfile(scenario_directrory+os.sep+x) and fnmatch.fnmatch(scenario_directrory+os.sep+x, '*.yaml')  and os.path.splitext(x)[0] in run_scenarios
        }
    else:
        scenarios = {
            scenario_directrory + '/' + x: os.path.splitext(x)[0]
            for x in os.listdir(scenario_directrory)
                if os.path.isfile(scenario_directrory+os.sep+x) and fnmatch.fnmatch(scenario_directrory+os.sep+x, '*.yaml')
        }

    template = jenv.get_template(template_file)
    template.globals['context'] = get_context
    template.globals['callable'] = callable
    context = { 'templates': scenarios }

    footer = (template.render(**context))
    if fp:
        os.write(fp, footer)
    os.close(fp)

#rally task start scenario.yaml --task-args "{cxt_tenants: 1, cxt_users_per_tenant: 4, cxt_network: true, base_network_load_objects: 30, load_type: serial, times: 1, scenarios: [create_and_list_networks, random]}"
def run_rally(template, task_args=None, task_args_file=None):
    cmd = ['rally', 'task', 'start', template]
    if task_args:
        cmd.extend(['--task-args', task_args])
    elif task_args_file:
        cmd.extend(['--task-args-file', task_args_file])

    p = subprocess.Popen(cmd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    while(True):
        next_out = p.stdout.readline()
        yield (next_out)
        if next_out == '' and p.poll() != None:
            break


def main(argv=sys.argv):
    scenarios = []
    ap = argparse.ArgumentParser(
        description="Run rally tasks")
    ap.add_argument("--task-args", type=str,
                    help="""Rally task parameters - a yaml dictionary
                    with the parameters""")
    ap.add_argument("--task-args-file", type=str,
                    help="""It should be either a yaml file which contains
                     all arguments""")
    args = ap.parse_args()
    if args.task_args and args.task_args_file:
        raise argparse.ArgumentError('Either one of task-args or task-args-file to be provided')

    if not args.task_args and not args.task_args_file:
        raise argparse.ArgumentError('Either one of task-args or task-args-file to be provided')

    if args.task_args_file:
        with open(args.task_args_file, 'r') as stream:
            scenarios = yaml.load(stream).get('scenarios', [])

    if args.task_args:
        scenarios = yaml.load(args.task_args).get('scenarios',[])

    (fp, file) = tempfile.mkstemp(dir=THIS_DIR)
    try:
        create_rally_input(fp, scenarios)
        for out in run_rally(file, task_args=args.task_args, task_args_file=args.task_args_file):
            sys.stdout.write(out)
            sys.stdout.flush()
    finally:
        os.remove(file)

    return True


if __name__ == "__main__":
    sys.exit(not main(sys.argv))
