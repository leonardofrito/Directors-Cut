"""Character, location and prop direction catalogs, with explicit prompt cues."""
from .characters import CATEGORIES, CUSTOM, character_prompt
from .presets import STYLE, FRAMING, LIGHTING, LIGHT_COLORS, FILM, GRADE, LENS_TYPES, SENSORS, F_STOPS
from .preset_directions import LOCATION_FRAMING, LOCATION_LENSES, PROP_STYLES
import json
from pathlib import Path


def category(key, label, options, hints=None):
    return dict(id=key, label=label, options=options.split('|') if isinstance(options, str) else list(options), hints=hints or {})


LOCATION = [
    category('location_type', 'Location type', 'Bedroom|Cozy apartment|Artist loft|Luxury hotel|Cafe|Restaurant|Library|Workshop|Neon alley|Underground club|Rooftop|Train station|Desert highway|Forest clearing|Tropical island|Mountain valley|Arctic outpost|Space station|Floating city|Sunken city|Liminal supermarket|Brutalist cathedral|Cloud kingdom|Inside a living organism|Giant miniature world|Impossible staircase|Abandoned theme park|Surreal theater'),
    category('world', 'World / reality', 'Everyday realism|Heightened realism|Dream logic|Surrealism|Fantasy|Dark fantasy|Cyberpunk|Solarpunk|Steampunk|Dieselpunk|Biopunk|Retrofuturism|Post-apocalyptic|Fairy tale|Cosmic science fiction'),
    category('architecture', 'Architecture', 'Modern minimalist|Brutalist|Art deco|Art nouveau|Gothic|Baroque|Industrial|Mid-century modern|Traditional Japanese|Mediterranean|Moroccan riad|Organic biomorphic|Impossible Escher-like geometry|Inflatable architecture|Crystal architecture|Giant mushroom structures|Living coral architecture|Candy-colored toy buildings'),
    category('scale', 'Scale', 'Intimate human scale|Grand monumental scale|Vast open landscape|Tiny miniature diorama|Gigantic oversized furniture|Towering megastructures|Infinite repeating corridors|Pocket universe'),
    category('era', 'Era', 'Contemporary|1920s|1950s|1970s|1980s|1990s|Y2K|Victorian|Medieval|Ancient world|Near future|Distant future|Timeless dream'),
    category('materials', 'Materials', 'Concrete and glass|Warm wood and linen|Stone and iron|Chrome and mirrors|Velvet and gold|Plastic and inflatable vinyl|Ceramic and terracotta|Crystal and ice|Organic flesh-like textures|Moss and reclaimed materials|Paper and cardboard|Felt and wool'),
    category('time', 'Time of day', 'Dawn|Morning|Midday|Afternoon|Golden hour|Blue hour|Night|Midnight|Eternal twilight'),
    category('weather', 'Weather', 'Clear sky|Overcast|Heavy rain|Drizzle|Dense fog|Snowfall|Blizzard|Sandstorm|Tropical humidity|Thunderstorm|Aurora sky|Floating glowing particles'),
    category('atmosphere', 'Atmosphere', 'Peaceful and cozy|Busy and lively|Lonely and melancholic|Mysterious|Playful and absurd|Uneasy liminal space|Opulent theatrical drama|Ethereal wonder|Chaotic maximalism|Quiet abandoned beauty'),
    category('set_dressing', 'Set dressing', 'Empty clean space|Lived-in clutter|Dense plants|Retro electronics|Collected antiques|Surreal giant flowers|Floating objects|Bioluminescent vegetation|Mirrored surfaces|Draped fabric|Abandoned objects|Handmade craft details'),
    category('framing', 'Framing', FRAMING, FRAMING),
    category('lens_type', 'Lens type', LENS_TYPES, LENS_TYPES),
    category('sensor', 'Sensor / film format', SENSORS, SENSORS),
    category('aperture', 'Aperture', [f'f/{stop}' for stop in F_STOPS], {f'f/{stop}':f'Aperture f/{stop}, '+('shallow depth of field and soft background bokeh' if float(stop)<2.8 else 'moderate depth of field' if float(stop)<8 else 'deep focus and readable surroundings') for stop in F_STOPS}),
    category('focal_length', 'Focal length', [f'{mm}mm' for mm in sorted(set(range(5,501,5))|{8,12,14,16,18,24,28})], {f'{mm}mm':f'Focal length: {mm}mm' for mm in range(5,501)}),
    category('lighting', 'Lighting', LIGHTING, LIGHTING),
    category('light_color', 'Light color', LIGHT_COLORS, LIGHT_COLORS),
    category('film', 'Film', FILM, FILM),
    category('grade', 'Grade', GRADE, GRADE),
    category('render_style', 'Visual style', list(STYLE) + ['Surreal architectural photography', 'Miniature set photography', 'Claymation set', 'Paper diorama', 'Dreamlike 3D environment', 'Video-game environment'], STYLE),
]
PROP = [
    category('prop_type', 'Prop type', 'Everyday object|Handheld accessory|Bag|Jewelry|Furniture|Tool|Musical instrument|Food item|Toy|Robot companion|Sci-fi device|Fantasy relic|Surreal sculptural object|Living object'),
    category('design', 'Design language', 'Functional realistic|Minimalist|Vintage|Retro-futurist|Cyberpunk|Art deco|Baroque ornate|Brutalist|Cute toy-like|Grotesque cartoon|Organic biomorphic|Inflatable pop art|Impossible surreal geometry'),
    category('material', 'Material', 'Wood|Brushed metal|Polished chrome|Glass|Ceramic|Leather|Fabric|Plastic|Rubber|Stone|Crystal|Moss|Living organic material|Translucent jelly|Paper and cardboard'),
    category('scale', 'Scale', 'Handheld|Pocket-sized|Human-sized|Oversized|Tiny miniature|Monumental'),
    category('condition', 'Condition', 'Brand new|Lightly worn|Weathered|Rusty|Ancient relic|Broken and repaired|Overgrown with plants|Glowing with energy'),
    category('grade', 'Color palette', GRADE, GRADE),
    category('render_style', 'Visual style', 'Photorealistic product photo|Studio packshot|Toy photography|Concept art|Stylized 3D render|Claymation|Hand-painted illustration|Technical design sheet'),
]
# Curate Assets only. Shared camera/video dictionaries and saved historical choices remain intact.
LEGACY_LOCATION_OPTIONS={c['id']:list(c['options']) for c in LOCATION}
LOCATION_CHOICES={
 'framing':list(LOCATION_FRAMING),
 'lens_type':['Spherical / normal','Anamorphic','Fisheye','Vintage spherical'],
 'sensor':[next(iter(SENSORS)),'APS-C','Super 16','Medium format',next(k for k in SENSORS if k.startswith('IMAX'))],
 'film':['Digital clean','Tungsten 500T','Daylight 250D','Black and white','Faded print','Cross-processed'],
 'lighting':['Soft window','Hard sunlight','Overcast','Practical night','Low-key studio','Rim light','Neon','Volumetric'],
 'light_color':['As scene / preset','Warm amber','Neutral white · 4500K','Cool blue','Red','Cyan','Magenta'],
 'grade':['Natural','Warm','Cool','Teal and orange','Muted','Monochrome'],
}
for c in LOCATION:
    if c['id'] in LOCATION_CHOICES:c['options']=LOCATION_CHOICES[c['id']]
    if c['id']=='framing':c['hints']={**FRAMING,**LOCATION_FRAMING}
    if c['id']=='lens_type':c['hints']={**LENS_TYPES,**LOCATION_LENSES}
for c in PROP:
    if c['id']=='render_style':c['hints']=PROP_STYLES
ASSET_CATEGORIES = dict(character=CATEGORIES, location=LOCATION, prop=PROP)


def preview_images():
    try:
        index = json.loads((Path(__file__).resolve().parent.parent / 'web/assets/previews/index.json').read_text(encoding='utf-8'))
        return index if isinstance(index, dict) else {}
    except (OSError, ValueError):
        return {}


def validate_choices(data, kind):
    categories = ASSET_CATEGORIES[kind]
    if not isinstance(data, dict) or set(data) - {c['id'] for c in categories}:
        raise ValueError('Invalid ' + kind + ' options.')
    result = {}
    for c in categories:
        choice = data.get(c['id'], {})
        if not isinstance(choice, dict):
            raise ValueError('Invalid option: ' + c['label'])
        value, custom = choice.get('value', ''), choice.get('custom', '')
        legacy=LEGACY_LOCATION_OPTIONS.get(c['id'],[]) if kind=='location' else []
        if value not in ['', CUSTOM, *c['options'], *legacy] or not isinstance(custom, str) or len(custom) > 500:
            raise ValueError('Invalid option: ' + c['label'])
        if value or custom.strip():
            result[c['id']] = dict(value=value, custom=custom.strip())
    return result


def asset_prompt(settings):
    if settings.get('edit_source'):
        return ''
    if settings.get('mode') != 'asset':
        return ''
    kind = settings.get('asset_kind', 'character')
    if kind == 'character':
        return character_prompt(settings)
    traits = validate_choices(settings.get(kind + '_traits', {}), kind)
    lines = []
    for c in ASSET_CATEGORIES[kind]:
        choice = traits.get(c['id'], {})
        text = choice.get('custom', '') if choice.get('value') == CUSTOM else choice.get('value', '')
        if text:
            cue = c.get('hints', {}).get(text, text) if choice.get('value') != CUSTOM else text
            if cue:
                lines.append(c['label'] + ': ' + cue.rstrip('.') + '.')
    return ' '.join(lines) if lines else ''
