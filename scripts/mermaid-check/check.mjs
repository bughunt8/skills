// Parse exporter output without rendering or starting a browser.
import { execFileSync } from 'node:child_process';
import { mkdtemp, readdir, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const generator = String.raw`
import copy
import sys
from pathlib import Path

root, output = map(Path, sys.argv[1:])
skill = root / 'skills/engineering/openheart-analysis'
sys.path.insert(0, str(skill / 'scripts'))
import openheart
from build_fixture import JAVA_ROOT, fixture

def export(model, name, source):
    destination = openheart.make_destination(output / name)
    openheart.export(model, destination, openheart.validate(model, source))
    expected = {key + '.mmd' for key, graph in model['diagrams'].items()
                if graph['status'] != 'not_requested'}
    if 'activity.mmd' in expected:
        expected.add('ACT.mmd')
    actual = {path.name for path in destination.rglob('*.mmd')}
    if actual != expected:
        raise RuntimeError(f'{name}: incomplete exports: {actual ^ expected}')

models = sorted((skill / 'datasets').glob('*-model.json'))
if not models:
    raise RuntimeError('No OpenHeart model fixtures found')
for path in models:
    model = openheart.load_model(path)
    source = next((base for base in (skill / 'datasets', JAVA_ROOT)
                   if all((base / entry['path']).is_file() for entry in model['files'])), None)
    if source is None:
        raise RuntimeError(f'{path.name}: no fixture source root')
    export(model, path.stem, source)

# Empty fixture views only exercise status flowcharts. Populate every category
# as well so sequence, state and every graph approximation reach their parsers.
model = fixture()
graph = copy.deepcopy(model['diagrams']['cfg'])
for node in graph['nodes']:
    node['id'] = 'presentation:' + node['id']
for ordinal, edge in enumerate(graph['edges'], 1):
    edge['id'] = 'presentation:' + edge['id']
    edge['source'] = 'presentation:' + edge['source']
    edge['target'] = 'presentation:' + edge['target']
    edge['attributes']['ordinal'] = ordinal
for key in model['diagrams']:
    model['diagrams'][key] = copy.deepcopy(graph)
export(model, 'populated-presentations', skill / 'datasets')
`;

async function diagrams(directory) {
  const result = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) result.push(...await diagrams(path));
    else if (entry.isFile() && entry.name.endsWith('.mmd')) result.push(path);
  }
  return result.sort();
}

let temporary;
const dom = new JSDOM('');
try {
  // Mermaid sanitizes labels during parsing; jsdom supplies the DOM API only.
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  const { default: mermaid } = await import('mermaid');
  mermaid.initialize({ startOnLoad: false });
  const { version } = JSON.parse(await readFile(
    new URL('./node_modules/mermaid/package.json', import.meta.url), 'utf8'));
  console.log(`Mermaid parser ${version}; syntax only, no browser`);

  const args = process.argv.slice(2);
  if (args.length !== 0 && (args.length !== 2 || args[0] !== '--check-dir')) {
    throw new Error('Usage: node scripts/mermaid-check/check.mjs [--check-dir DIRECTORY]');
  }
  let directory;
  if (args.length) directory = resolve(args[1]);
  else {
    temporary = await mkdtemp(join(tmpdir(), 'openheart-mermaid-'));
    directory = temporary;
    execFileSync('python3', ['-c', generator, root, directory], { stdio: 'inherit' });
  }
  const files = await diagrams(directory);
  if (!files.length) throw new Error('No Mermaid exports found');
  let failures = 0;
  for (const path of files) {
    const name = relative(directory, path);
    try {
      const result = await mermaid.parse(await readFile(path, 'utf8'));
      if (!result) throw new Error('Parser rejected diagram');
      console.log(`PASS ${name} (${result.diagramType})`);
    } catch (error) {
      failures += 1;
      console.error(`FAIL ${name}: ${error.message}`);
    }
  }
  console.log(`Parsed ${files.length} Mermaid exports; ${failures} syntax errors`);
  if (failures) process.exitCode = 1;
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
} finally {
  dom.window.close();
  if (temporary) await rm(temporary, { recursive: true, force: true });
}
