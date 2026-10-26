import json
import os
import re
import shutil
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
from .paths import DATA_ROOT


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    # Windows indexers / OneDrive can briefly hold the destination open.
    for attempt in range(5):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.02 * (attempt + 1))


class Store:
    def __init__(self, root=None):
        self.root = Path(root or os.environ.get('OPENFRAME_PROJECTS', DATA_ROOT / 'projects')).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def folder(self, project_id):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', project_id):
            raise ValueError('Invalid project identifier.')
        folder = (self.root / project_id).resolve()
        if not folder.is_relative_to(self.root):
            raise ValueError('Project is outside the projects folder.')
        return folder

    def load(self, project_id):
        project = json.loads((self.folder(project_id) / 'project.json').read_text(encoding='utf-8'))
        from .assets import unique_names
        unique_names(project)
        # Older projects gain a board without moving or regenerating images.
        if 'storyboard' not in project:
            project['storyboard'] = [self.panel(shot) for shot in project['shots'] if shot.get('approved') and shot.get('mode') != 'video']
        return project

    def save(self, project):
        project['updated_at'] = now()
        write_json(self.folder(project['id']) / 'project.json', project)

    def list(self):
        items = []
        for path in self.root.glob('*/project.json'):
            try:
                items.append(self.load(path.parent.name))
            except (ValueError, OSError):
                continue
        return sorted(items, key=lambda p: p['updated_at'], reverse=True)

    def create(self, name):
        name = name.strip()
        if not name or len(name) > 120:
            raise ValueError('Choose a project name between 1 and 120 characters.')
        slug = re.sub(r'[^A-Za-z0-9_-]+', '_', name).strip('_')[:48] or 'Project'
        project = dict(id=f'{slug}_{uuid.uuid4().hex[:8]}', name=name, created_at=now(), shots=[], storyboard=[])
        self.save(project)
        return project

    def remove(self, project_id):
        """Remove a whole project from the studio, retaining a recovery copy."""
        source = self.folder(project_id)
        if not (source / 'project.json').is_file():
            raise ValueError('Project not found.')
        recovery = (self.root.parent / '.runtime' / 'deleted-projects').resolve()
        recovery.mkdir(parents=True, exist_ok=True)
        target = (recovery / f'{project_id}-{uuid.uuid4().hex[:8]}').resolve()
        if source == self.root or source.parent != self.root or target.parent != recovery:
            raise ValueError('Invalid project removal path.')
        shutil.move(str(source), str(target))

    def shot(self, project, shot_id):
        return next(s for s in project['shots'] if s['id'] == shot_id)

    def add_shot(self, project):
        previous = project['shots'] + project.get('archived_shots', [])
        number = max((int(s['id'].rsplit('_', 1)[-1]) for s in previous), default=0) + 1
        shot = dict(id=f'shot_{number:03d}', title=f'Shot {number:02d}', prompt='', style='Cinematic', camera='Wide', ratio='16:9', steps=25, seed=-1, drafts=[], approved=None)
        project['shots'].append(shot)
        self.save(project)
        return shot

    def file(self, project_id, relative):
        folder = self.folder(project_id)
        result = (folder / relative).resolve()
        if not result.is_relative_to(folder):
            raise ValueError('File is outside the project folder.')
        return result

    def approve(self, project, shot, draft_id):
        draft = next((d for d in shot['drafts'] if d['id'] == draft_id and d['status'] == 'succeeded' and d.get('file')), None)
        if not draft:
            raise ValueError('Choose a completed take to approve.')
        if shot.get('mode') == 'video':
            shot['approved'] = dict(draft_id=draft_id, file=draft['file'], approved_at=now())
            self.save(project)
            return
        target = f'shots/{shot["id"]}/approved.png'
        shutil.copyfile(self.file(project['id'], draft['file']), self.file(project['id'], target))
        shot['approved'] = dict(draft_id=draft_id, file=target, approved_at=now())
        project.setdefault('storyboard', [])
        if not any(panel['shot_id'] == shot['id'] for panel in project['storyboard']):
            project['storyboard'].append(self.panel(shot))
        self.save(project)

    @staticmethod
    def panel(shot):
        return dict(shot_id=shot['id'], title=shot['title'], caption=shot.get('prompt', '')[:2000])

    def edit_storyboard(self, project, data):
        panels = project['storyboard']
        if 'columns' in data:
            if data['columns'] not in (2, 3):
                raise ValueError('Choose a 2 x 2 or 3 x 3 layout.')
            project['storyboard_columns'] = data['columns']
        elif 'order' in data:
            order = data['order']
            expected = {panel['shot_id'] for panel in panels}
            if not isinstance(order, list) or not all(isinstance(x, str) for x in order) or len(order) != len(expected) or set(order) != expected:
                raise ValueError('The storyboard changed. Refresh before rearranging its panels.')
            indexed = {panel['shot_id']: panel for panel in panels}
            project['storyboard'] = [indexed[ident] for ident in order]
        else:
            panel = next(p for p in panels if p['shot_id'] == data['shot_id'])
            title, caption = data.get('title', panel['title']), data.get('caption', panel['caption'])
            if not isinstance(title, str) or not isinstance(caption, str) or len(title) > 120 or len(caption) > 2000:
                raise ValueError('Use up to 120 characters for the title and 2,000 for the caption.')
            panel.update(title=title, caption=caption)
        self.save(project)

    def board(self, project):
        shots = {shot['id']: shot for shot in project['shots'] if shot.get('approved')}
        panels = project.get('storyboard')
        if panels is None:
            panels = [self.panel(shot) for shot in shots.values()]
        return [(panel, shots[panel['shot_id']]) for panel in panels if panel['shot_id'] in shots]

    def export(self, project, columns):
        panels = self.board(project)
        if not panels:
            raise ValueError('Approve at least one frame before exporting.')
        # Multiple pages preserve every approved shot beyond the chosen grid.
        files = []
        font = ImageFont.load_default(size=22)
        caption_font = ImageFont.load_default(size=18)
        measure = ImageDraw.Draw(Image.new('RGB', (1, 1)))
        def wrap(text, chosen_font, width):
            lines = []
            for paragraph in text.split('\n'):
                line = ''
                for word in paragraph.split(' '):
                    candidate = (line + ' ' + word).strip()
                    if line and measure.textlength(candidate, font=chosen_font) > width:
                        lines.append(line)
                        line = ''
                    # Split a long word only if it cannot fit on one line.
                    for char in word:
                        candidate = line + char
                        if measure.textlength(candidate, font=chosen_font) > width and line:
                            lines.append(line)
                            line = char
                        else:
                            line = candidate
                    if line:
                        line += ' '
                lines.append(line.rstrip())
            return lines or ['']
        for start in range(0, len(panels), columns * columns):
            page = panels[start:start + columns * columns]
            width, height, margin = 640, 360, 24
            captions = [(wrap(f'{start + i + 1:02d}  {panel["title"]}', font, width), wrap(panel['caption'], caption_font, width)) for i, (panel, _) in enumerate(page)]
            row_heights = [height + 74] * columns
            for i, (titles, notes) in enumerate(captions):
                row_heights[i // columns] = max(row_heights[i // columns], height + 30 + len(titles) * 28 + len(notes) * 24)
            canvas = Image.new('RGB', (columns * (width + margin) + margin, sum(row_heights) + margin * (columns + 1) + 60), '#211927')
            draw = ImageDraw.Draw(canvas)
            draw.text((margin, 20), project['name'][:100], font=font, fill='#eeeeee')
            for i, (panel, shot) in enumerate(page):
                row = i // columns
                x, y = margin + (i % columns) * (width + margin), 84 + sum(row_heights[:row]) + row * margin
                with Image.open(self.file(project['id'], shot['approved']['file'])) as image:
                    frame = ImageOps.contain(image.convert('RGB'), (width, height))
                    canvas.paste(frame, (x + (width - frame.width) // 2, y + (height - frame.height) // 2))
                titles, notes = captions[i]
                text_y = y + height + 10
                for line in titles:
                    draw.text((x, text_y), line, font=font, fill='#eeeeee')
                    text_y += 28
                for line in notes:
                    draw.text((x, text_y), line, font=caption_font, fill='#c2b8cb')
                    text_y += 24
            relative = f'exports/storyboard_{columns}x{columns}_{start // (columns * columns) + 1:02d}.jpg'
            target = self.file(project['id'], relative)
            target.parent.mkdir(exist_ok=True)
            canvas.save(target, format='JPEG', quality=95, subsampling=0)
            files.append(relative)
        return files

    def export_download(self, project_id, files, columns):
        """One browser download, including every JPEG page for longer boards."""
        if len(files) == 1:
            return files[0]
        relative = f'exports/storyboard_{columns}x{columns}_jpeg_pages.zip'
        with zipfile.ZipFile(self.file(project_id, relative), 'w', compression=zipfile.ZIP_STORED) as bundle:
            for filename in files:
                bundle.write(self.file(project_id, filename), arcname=Path(filename).name)
        return relative
