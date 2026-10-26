"""Optional character design directions, independent of shot presets."""
from .preset_directions import CHARACTER_HINTS, CLOTHING_COLORS
CUSTOM = '__custom__'
MULTI_TRAITS = {'accessories', 'facial_features', 'distinctive_features'}
EXCLUSIVE_TRAITS = {
    'accessories': [('Glasses', 'Sunglasses', 'Oversized surreal glasses'), ('Small earrings', 'Statement earrings')],
    'facial_features': [('High cheekbones', 'Soft cheeks', 'Exaggerated cheekbones'), ('Strong jawline', 'Rounded jawline'), ('Full lips', 'Thin lips'), ('Broad nose', 'Narrow nose', 'Aquiline nose', 'Button nose', 'Oversized nose', 'Tiny nose'), ('Thick eyebrows', 'Fine eyebrows')],
}


def compatible_trait_values(key, values):
    if key == 'accessories' and 'No accessories' in values and len(values)>1:
        return False
    return all(len(set(values).intersection(group))<=1 for group in EXCLUSIVE_TRAITS.get(key, []))
SPECS = [
    ('character_type', 'Character type', 'Average|Bold|Extreme|Insect|Frog|Cat|Dog|Rodent|Bird|Reptile|Alien|Android|Living doll|Clay creature|Inflatable mascot'),
    ('gender', 'Gender presentation', 'Woman|Man|Nonbinary|Androgynous|Gender-fluid'),
    ('age', 'Age', 'Young adult|Adult|Middle-aged adult|Older adult|Elderly person'),
    ('build', 'Build', 'Slender|Lean|Athletic|Muscular|Stocky|Curvy|Plus-size|Broad-shouldered'),
    ('height', 'Height', 'Short|Average height|Tall|Very tall'),
    ('proportions', 'Proportions', 'Balanced proportions|Long legs|Long torso|Petite frame|Broad frame|Stylized elongated proportions'),
    ('heritage', 'Heritage / appearance', 'East Asian|Southeast Asian|South Asian|Black / African diaspora|Middle Eastern|Latino / Latin American|White / European|Indigenous|Mixed heritage'),
    ('skin_tone', 'Skin tone', 'Very fair|Fair|Light beige|Olive|Medium brown|Warm brown|Deep brown|Very deep brown'),
    ('face_shape', 'Face shape', 'Oval face|Round face|Square face|Heart-shaped face|Diamond-shaped face|Long face|Angular face|Soft facial contours'),
    ('neck', 'Neck', 'Short neck|Average-length neck|Long neck|Broad neck|Slender neck'),
    ('eye_shape', 'Eye shape', 'Almond-shaped eyes|Round eyes|Hooded eyes|Monolid eyes|Deep-set eyes|Upturned eyes|Downturned eyes|Wide-set eyes'),
    ('eye_color', 'Eye color', 'Dark brown|Brown|Hazel|Amber|Green|Blue|Gray|Different-colored eyes'),
    ('hairstyle', 'Hairstyle', 'Buzz cut|Pixie cut|Short crop|Bob|Long bob|Shoulder-length hair|Long straight hair|Long wavy hair|Curly hair|Coily hair|Afro|Braids|Box braids|Locs|Cornrows|Ponytail|High bun|Low bun|Shaved head|Bald|Undercut|Side part|Curtain bangs|Blunt bangs|Mullet|Messy curls'),
    ('hair_color', 'Hair color', 'Black hair|Dark brown hair|Chestnut hair|Light brown hair|Blonde hair|Platinum blonde hair|Auburn hair|Red hair|Gray hair|White hair|Silver hair|Pink hair|Blue hair|Purple hair|Two-tone hair'),
    ('facial_features', 'Facial features', 'High cheekbones|Soft cheeks|Strong jawline|Rounded jawline|Full lips|Thin lips|Broad nose|Narrow nose|Aquiline nose|Button nose|Thick eyebrows|Fine eyebrows|Prominent ears|Dimples'),
    ('facial_hair', 'Facial hair', 'Clean-shaven|Light stubble|Heavy stubble|Short beard|Full beard|Goatee|Mustache|Handlebar mustache|Sideburns'),
    ('distinctive_features', 'Distinctive features', 'Freckles|Beauty mark|Visible facial scar|Vitiligo|Heterochromia|Gap between front teeth|Tattooed arms|Subtle facial tattoo|Piercings|Natural skin texture'),
    ('wardrobe', 'Wardrobe', 'Casual basics|Streetwear|Business casual|Tailored suit|Evening wear|Sportswear|Workwear|Vintage clothing|Bohemian clothing|Minimalist clothing|Punk clothing|Gothic clothing|Fantasy costume|Sci-fi costume'),
    ('clothing_color', 'Clothing color', '|'.join(CLOTHING_COLORS)),
    ('accessories', 'Accessories', 'No accessories|Glasses|Sunglasses|Small earrings|Statement earrings|Necklace|Scarf|Hat|Wristwatch|Backpack'),
    ('expression', 'Expression', 'Neutral expression|Gentle smile|Broad smile|Thoughtful expression|Confident expression|Serious expression|Playful expression|Calm expression'),
    ('pose', 'Pose / view', 'Front-facing portrait|Three-quarter portrait|Side-profile portrait|Full-body standing|Seated portrait|Relaxed candid pose|Neutral character turnaround'),
    ('render_style', 'Visual style', 'Photorealistic|Cinematic portrait|Fashion editorial|Natural candid photograph|Studio portrait|Anime|Stylized 3D character|Realistic 3D character|Concept art|Watercolor illustration|Pencil drawing|Comic-book illustration'),
]
EXTRAS = {
    'character_type': 'Average|Bold|Extreme|Insect|Frog|Cat|Dog|Rodent|Bird|Reptile|Alien|Android|Living doll|Clay creature|Inflatable mascot',
    'build': 'Frail|Wiry|Delicate|Heroic muscular|Massive bodybuilder|Exaggerated strongman|Soft rounded silhouette|Tiny body, oversized head|Long-limbed cartoon',
    'proportions': 'Oversized head|Tiny head, massive body|Giant hands|Exaggerated long neck|Squat cartoon proportions|Stretchy rubber-hose proportions',
    'wardrobe': 'Theatrical costume|UK street style|All-white streetwear|Gothic couture|Sporty retro|Retro 1970s|Vintage 1990s|Y2K pop|Cyberpunk techwear|Gorpcore|Cottagecore|Dark academia|Avant-garde runway|Maximalist clashing prints|Space disco|Rococo pop|Retro-futurist|Surreal sculptural fashion',
    'hairstyle': 'Gravity-defying spikes|Giant sculptural beehive|Asymmetric geometric cut|Oversized sculptural curls|Floating braided loops',
    'hair_color': 'Neon green hair|Rainbow gradient hair|Electric orange hair|Chrome metallic hair',
    'facial_features': 'Oversized ears|Oversized nose|Tiny nose|Exaggerated cheekbones|Wide cartoon mouth|Asymmetric sculptural face',
    'distinctive_features': 'Translucent skin|Metallic skin|Bioluminescent markings|Moss and flowers growing from skin|Patchwork fabric skin',
    'accessories': 'Oversized surreal glasses|Sculptural headpiece|Giant statement jewelry|Retro headphones|Inflatable accessories',
    'render_style': 'Claymation|Stop-motion puppet|Felt and fabric puppet|Paper-cut character|Toy photography|Surreal fashion photography|Caricature illustration|Low-poly game character|Pixel art character',
}
TYPE_HINTS = {
    'Alien': 'Replace the human facial anatomy with a clearly nonhuman alien face: pale green skin, an elongated bald cranium, very large dark almond-shaped eyes, tiny nose and small mouth. Keep the teal outfit and portrait framing.',
    'Android': 'Transform the face into an unmistakable humanoid robot: ivory synthetic face plates, visible metallic seams across cheeks and forehead, exposed silver mechanical joints at the neck, glowing blue artificial eyes. Keep the portrait framing and outfit.',
    'Living doll': 'A living porcelain doll with glossy porcelain skin, painted facial features, glass eyes and visible articulated doll joints at the neck.',
    'Clay creature': 'A sculpted clay humanoid character with rounded clay facial forms, visible fingerprints and handmade clay texture across the face and neck.',
    'Inflatable mascot': 'An inflatable vinyl humanoid mascot with a puffy rounded head, inflated cheeks, visible vinyl seams and shiny toy-like surface.',
    'Average': 'A human character with natural, believable facial features. Use the separately specified build, height and body proportions.',
    'Bold': 'A human with striking distinctive facial anatomy: a pronounced jaw, prominent cheekbones and expressive eyebrows. The facial shapes are bold; the rendering medium follows the selected visual style.',
    'Extreme': 'A human with deliberately exaggerated physical anatomy: oversized facial features, unusually prominent cheekbones and an eccentric silhouette. These describe the anatomy, not a cartoon or illustration style. Keep the selected visual rendering medium.',
    'Insect': 'An anthropomorphic insect character with a humanoid body, insect head, antennae and expressive compound eyes.',
    'Frog': 'An anthropomorphic frog character with a humanoid body, frog face, wide mouth and large protruding eyes.',
    'Cat': 'An anthropomorphic cat character with a humanoid body, feline face, pointed ears, fur and whiskers.',
    'Dog': 'A humanoid dog person with a canine head, expressive dog ears, muzzle and fur, on a human-like upright neck and shoulders, wearing human clothing. Human-like anatomy below the head; not an ordinary pet or four-legged dog. Follow the requested portrait crop or body framing.',
    'Rodent': 'An anthropomorphic rodent character with a humanoid body, round ears, short furry muzzle and whiskers.',
    'Bird': 'An anthropomorphic bird character with a humanoid body, feathered bird head and prominent beak.',
    'Reptile': 'An anthropomorphic reptile character with a humanoid body, scaled skin and reptilian facial features.',
}
CATEGORIES = []
for key, label, options in SPECS:
    extra = EXTRAS.get(key, '').split('|') if key in EXTRAS else []
    choices = list(dict.fromkeys((extra + options.split('|')) if key == 'character_type' else (options.split('|') + extra)))
    CATEGORIES.append(dict(id=key, label=label, options=choices, hints=TYPE_HINTS if key == 'character_type' else CHARACTER_HINTS.get(key, {})))

PHOTO_STYLES = {'Photorealistic', 'Cinematic portrait', 'Fashion editorial', 'Natural candid photograph', 'Studio portrait', 'Surreal fashion photography'}


def character_render_direction(settings):
    if settings.get('edit_source') or settings.get('mode') != 'asset' or settings.get('asset_kind', 'character') != 'character':
        return ''
    background = (' Use a seamless pure white studio background. Replace any described environment with white. '
                  'Isolate the character, requested clothing and accessories; only a subtle grounding shadow.')
    style = settings.get('character_traits', {}).get('render_style', {}).get('value', '')
    if style in PHOTO_STYLES:
        features=settings.get('character_traits', {}).get('distinctive_features', {})
        material_skin=bool({'Metallic skin','Translucent skin','Patchwork fabric skin'}.intersection(features.get('values') or [features.get('value')]))
        return ('Rendering medium: a photorealistic ' + style.lower() + ' of a physically present subject. '
                + ('Preserve the specified non-flesh skin material, its surface and light transmission. ' if material_skin else 'Natural skin texture, detailed hair strands, tangible materials and photographic lighting. ')
                +
                'Keep all requested unusual anatomy, but depict it photographically, without cartoon, painting or concept-art rendering.') + background
    if style in CHARACTER_HINTS['render_style']:
        return 'Rendering medium priority: '+CHARACTER_HINTS['render_style'][style]+background
    return background.strip()


def validate_traits(data):
    if not isinstance(data, dict) or set(data) - {item['id'] for item in CATEGORIES}:
        raise ValueError('Invalid character options.')
    result = {}
    for item in CATEGORIES:
        choice = data.get(item['id'], {})
        if not isinstance(choice, dict):
            raise ValueError('Invalid character option: ' + item['label'])
        value, custom = choice.get('value', ''), choice.get('custom', '')
        if value not in ['', CUSTOM, *item['options']] or not isinstance(custom, str) or len(custom) > 500:
            raise ValueError('Invalid character option: ' + item['label'])
        values=choice.get('values', [])
        if not isinstance(values,list) or len(values)>len(item['options']) or any(not isinstance(v,str) or v not in item['options'] for v in values) or (values and (item['id'] not in MULTI_TRAITS or value==CUSTOM or not compatible_trait_values(item['id'],values))):
            raise ValueError('Invalid multiple selections: '+item['label'])
        if values:
            values=list(dict.fromkeys(values));value=values[0]
        if value or custom.strip():
            result[item['id']] = dict(value=value, custom=custom.strip())
            if values:result[item['id']]['values']=values
    return result


def character_prompt(settings):
    if settings.get('mode') != 'asset' or settings.get('asset_kind', 'character') != 'character':
        return ''
    traits = validate_traits(settings.get('character_traits', {}))
    features=traits.get('distinctive_features', {})
    if {'Metallic skin','Translucent skin','Patchwork fabric skin'}.intersection(features.get('values') or [features.get('value')]):
        traits.pop('skin_tone',None)
    roles={ref.get('reference_role') for ref in settings.get('references',[])}
    if 'wardrobe' in roles:
        traits.pop('wardrobe',None)
    if 'hair' in roles:
        traits.pop('hairstyle',None)
        traits.pop('hair_color',None)
    lines = []
    for item in CATEGORIES:
        choice = traits.get(item['id'], {})
        text = choice.get('custom', '') if choice.get('value') == CUSTOM else ', '.join(choice.get('values') or [choice.get('value', '')])
        if text:
            cue = ' '.join(item.get('hints', {}).get(v,v) for v in (choice.get('values') or [choice.get('value','')])) if choice.get('value') != CUSTOM else text
            lines.append(item['label'] + ': ' + cue.rstrip('.') + '.')
    return ' '.join(lines) if lines else ''
