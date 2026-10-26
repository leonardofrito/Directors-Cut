"""Prompt-based art direction. These are visual cues, not lens simulation or LUTs."""

STYLE = {
    'Cinematic': 'Cinematic film still, carefully composed, subtle film grain.',
    'Photorealistic': 'Photorealistic photography, realistic materials and detail.',
    'Storyboard sketch': 'Black and white storyboard sketch, expressive ink lines, clear staging, no text.',
    'Pencil drawing': 'Graphite pencil drawing, hand-drawn shading on paper, no text.',
    'Animated': 'Hand-drawn animated feature film still, expressive shapes and painted backgrounds.',
    'Anime': 'Anime film still, expressive linework, detailed painted background.',
    '3D render': 'High-quality 3D rendered film still, physically based materials.',
    'Previsualization': 'Simple cinematic previsualization, clear blocking, neutral materials.',
    'Concept art': 'Concept art, painterly environment, strong visual storytelling.',
    'Watercolor': 'Watercolor painting, translucent pigments, paper texture and soft edges.',
    'Oil painting': 'Oil painting, visible brushwork and layered pigment.',
    'Ink illustration': 'Pen and ink illustration, expressive line weight and crosshatching.',
    'Comic book': 'Comic book illustration, bold ink contours, graphic shading, no panels or lettering.',
    'Graphic novel': 'Graphic novel illustration, expressive ink and nuanced painted shading, no lettering.',
    'Clay animation': 'Clay stop-motion animation still, handmade forms and tactile surfaces.',
    'Cut-paper collage': 'Layered cut-paper illustration, visible paper edges and tactile textures.',
    'Pixel art': 'Pixel art, deliberate pixel clusters and a limited color palette.',
    'Architectural visualization': 'Architectural visualization, precise space, material detail and clear perspective.',
    'Matte painting': 'Cinematic matte painting, expansive environment and layered atmospheric depth.',
    'Fashion editorial': 'Fashion editorial photograph, intentional styling and expressive composition.',
    'Documentary': 'Candid documentary photograph, unposed action and observational composition.',
    'Vintage illustration': 'Vintage printed illustration, textured paper and subtle ink imperfections.',
}
FRAMING = {
    'Extreme wide': 'Extreme wide establishing shot; the environment dominates.',
    'Wide': 'Wide shot showing the subject and its surroundings.',
    'Full body': 'Full body shot, head to feet within the frame.',
    'Cowboy shot': 'Cowboy shot, framing the subject from mid-thigh to above the head.',
    'Medium': 'Medium shot, framing from the waist up.',
    'Medium close-up': 'Medium close-up, framing from the chest up.',
    'Close-up': 'A tight close-up: the face and shoulders, or equivalent upper-body details of a faceless subject, fill most of the frame. Crop away the lower body and most surroundings. Avoid a distant full-body or establishing view.',
    'Extreme close-up': 'An extreme close-up: one small narratively important detail fills almost the entire frame. Crop away the rest of the body and environment rather than showing a complete portrait.',
    'Over-the-shoulder': 'Position the camera just behind one character. Their near shoulder and a partial back-of-head silhouette occupy one foreground edge, softly out of focus; the other character or action is visible beyond, in focus. Show the depth between them, rather than a frontal side-by-side portrait.',
    'Shoulder-level': 'Shoulder-level camera height.',
    'POV': 'First-person point-of-view shot.',
    'Low angle': 'Place the camera below the subject, near knee or ground height, and tilt it upward. Foreground elements loom large, vertical lines rise above the viewer and the subject towers over the camera. Show a clearly upward view rather than an eye-level portrait.',
    'High angle': 'Place the camera clearly above the subject and tilt it downward. Show the top planes of the subject and the ground beyond, making the subject appear smaller within the setting. Avoid an eye-level or upward view.',
    'Aerial': 'Aerial shot from an elevated airborne viewpoint.',
    'Bird’s-eye': 'Bird’s-eye shot looking vertically down from overhead.',
    'Worm’s-eye': 'Worm’s-eye view from ground level looking steeply upward.',
    'Dutch angle': 'Dutch angle, camera rolled to create a deliberately tilted horizon.',
    'Frame within a frame': 'Frame within a frame, surrounding the subject with a doorway, window or foreground shape.',
    'Two-shot': 'Two-shot framing two subjects together.',
    'Profile': 'Side-on profile shot.',
    'Insert detail': 'Insert shot isolating a narratively important object or action.',
    'Silhouette': 'Silhouette composition with a readable dark subject against a bright background.',
    'Symmetrical': 'Centered symmetrical composition with balanced visual geometry.',
    'Negative space': 'Off-center subject with generous negative space.',
    'Deep staging': 'Layered composition with foreground, midground and background action.',
}
CAMERAS = list(FRAMING)
LENS_TYPES = {
    'Spherical / normal': 'Spherical lens, natural rectilinear rendering.',
    'Anamorphic': 'Anamorphic lens character, oval bokeh and subtle horizontal flare.',
    'Fisheye': 'Fisheye lens with deliberately curved barrel distortion.',
    'Tilt-shift': 'Tilt-shift lens look with a selective plane of focus.',
    'Macro': 'Macro lens for close-focus detail and fine surface textures.',
    'Vintage spherical': 'Vintage spherical lens, gentle optical softness and subtle flare.',
}
SENSORS = {
    'Full frame · 36 × 24mm': 'Full-frame 36 x 24mm sensor format look.',
    'Super 35 · cinema': 'Super 35 cinema sensor format look.',
    '35mm motion picture': '35mm motion-picture film format look.',
    'APS-C': 'APS-C sensor format look.',
    'Micro Four Thirds': 'Micro Four Thirds sensor format look.',
    'Super 16': 'Super 16 film format look, intimate texture.',
    'Medium format': 'Medium-format camera look, fine detail and smooth tonal transitions.',
    '65mm / 70mm cinema': 'Large-format 65mm motion-picture photography look.',
    'IMAX · 15/70': 'IMAX 15-perforation 70mm large-format photography look, expansive detail.',
    'Large format · 4 × 5': 'Large-format 4 x 5 view camera photography look.',
}
FOCAL_LENGTHS = [8, 9, 10, 12, 14, 16, 18, 20, 21, 24, 28, 32, 35, 40, 50, 55, 65, 75, 85, 90, 95, 100, 105, 120, 135, 150, 180, 200, 250, 300, 400, 500]
F_STOPS = ['0.7', '0.95', '1', '1.2', '1.4', '1.8', '2', '2.8', '4', '5.6', '8', '11', '16', '22', '32']


def snap_focal_length(value):
    """Five-millimeter detents, retaining the existing 8mm wide-angle endpoint."""
    value = float(value)
    if not 8 <= value <= 500:
        raise ValueError('Focal length must be between 8 and 500mm.')
    return 8 if value <= 9 else min(500, int(value / 5 + .5) * 5)


def aperture_prompt(value):
    if value <= 2:
        depth = 'very shallow depth of field, subject in focus, strongly blurred background and soft bokeh'
    elif value <= 4:
        depth = 'shallow depth of field, subject in focus and a softly blurred background'
    elif value <= 8:
        depth = 'moderate depth of field, more of the scene in focus'
    else:
        depth = 'deep depth of field, foreground and background in focus'
    return f'Aperture f/{value:g}, {depth}.'

# Original combined presets remain readable in older projects.
OPTICS = {'Natural perspective': '', 'Large format · 50mm': 'Large-format camera look, 50mm lens perspective, shallow depth of field.', 'Wide · 24mm': '24mm wide-angle lens perspective, deep focus.', 'Portrait · 85mm': '85mm portrait lens perspective, soft background.', 'Anamorphic · 50mm': '50mm anamorphic lens look, subtle horizontal flare, oval bokeh.'}
LIGHTING = {
    'Natural light': 'Natural available light.',
    'Golden hour': 'Warm golden-hour backlight.',
    'Blue hour': 'Blue-hour twilight, soft cool ambient light.',
    'Overcast': 'Soft overcast daylight, broad diffuse illumination.',
    'Soft window': 'Soft directional window lighting.',
    'Practical night': 'Night scene lit by practical lamps and motivated light sources.',
    'Hard sunlight': 'Hard direct sunlight, crisp shadows.',
    'Dappled sunlight': 'Dappled sunlight broken by foliage, patterned light and shade.',
    'Low-key studio': 'Low-key studio lighting with controlled deep shadows.',
    'High-key studio': 'High-key studio lighting, bright even illumination with gentle shadows.',
    'Soft studio': 'Large softbox studio light, soft shadow transitions.',
    'Hard studio': 'Hard studio key light, defined shadows and graphic contrast.',
    'Three-point': 'Three-point lighting with distinct key, fill and rim lights.',
    'Rembrandt': 'Rembrandt portrait lighting, a small triangle of light on the shadow-side cheek.',
    'Butterfly': 'Butterfly portrait lighting, elevated frontal key and a small shadow below the nose.',
    'Split lighting': 'Split lighting, one side of the face lit and the other in shadow.',
    'Rim light': 'Strong rim light separating the subject from the background.',
    'Backlight': 'Backlit subject with light coming from behind.',
    'Neon': 'Neon tube lighting, luminous colored practical sources and reflected glow.',
    'Colored gels': 'Studio lighting through colored gels, deliberate colored key and fill.',
    'Candlelight': 'Candlelit scene, localized flickering warm light and deep falloff.',
    'Firelight': 'Firelight, irregular warm illumination and flickering shadows.',
    'Moonlight': 'Moonlit night, soft cool directional illumination.',
    'Volumetric': 'Volumetric light shafts visible through atmospheric haze.',
    'Silhouette backlight': 'Bright backlight with the subject rendered as a dark silhouette.',
    'Fluorescent': 'Overhead fluorescent practical lighting.',
}
LIGHT_COLORS = {
    'As scene / preset': '',
    'Warm amber': 'Light color: warm amber.',
    'Tungsten · 3200K': 'Light color: warm tungsten, approximately 3200K.',
    'Neutral white · 4500K': 'Light color: neutral white, approximately 4500K.',
    'Daylight · 5600K': 'Light color: daylight-balanced white, approximately 5600K.',
    'Cool blue': 'Light color: cool blue.',
    'Red': 'Light color: red.',
    'Orange': 'Light color: orange.',
    'Yellow': 'Light color: yellow.',
    'Green': 'Light color: green.',
    'Cyan': 'Light color: cyan.',
    'Magenta': 'Light color: magenta.',
    'Violet': 'Light color: violet.',
    'Pink': 'Light color: pink.',
    'Cyan key / amber rim': 'Cyan key light and warm amber rim light.',
    'Red key / blue fill': 'Red key light and blue fill light.',
    'Magenta key / cyan fill': 'Magenta key light and cyan fill light.',
}
FILM = {
    'Digital clean': 'Clean digital image, minimal grain.',
    'Tungsten 500T': 'Tungsten-balanced 500-speed film look, organic grain, gentle highlight halation.',
    'Daylight 250D': 'Daylight-balanced 250-speed film look, fine grain and natural skin tones.',
    'Black and white': 'Black-and-white film, rich monochrome tonal separation.',
    'Kodak VISION3 50D': 'Kodak VISION3 50D-inspired daylight film look, very fine grain and rich color detail.',
    'Kodak VISION3 200T': 'Kodak VISION3 200T-inspired tungsten film look, fine grain and balanced color.',
    'Kodak VISION3 250D': 'Kodak VISION3 250D-inspired daylight film look, fine grain and natural color.',
    'Kodak VISION3 500T': 'Kodak VISION3 500T-inspired tungsten film look, textured grain and smooth highlight rolloff.',
    'Kodak EKTACOLOR PRO 160': 'Kodak EKTACOLOR PRO 160-inspired color film, soft natural color, flattering skin tones and very fine grain.',
    'Kodak EKTACOLOR PRO 400': 'Kodak EKTACOLOR PRO 400-inspired color film, natural skin tones, balanced color and fine grain.',
    'Kodak EKTACOLOR PRO 800': 'Kodak EKTACOLOR PRO 800-inspired color film, balanced low-light color and natural skin tones.',
    'Kodak EKTAR 100': 'Kodak EKTAR 100-inspired color film, vivid saturated colors, very fine grain and crisp detail.',
    'Fujichrome PROVIA 100F': 'Fujichrome PROVIA 100F-inspired color slide film, balanced medium saturation and contrast, fine grain.',
    'Fujichrome Velvia 50': 'Fujichrome Velvia 50-inspired color slide film, rich saturated greens and blues, strong color contrast.',
    'Warm color negative': 'Warm color-negative film look, golden yellows, gentle reds and warm natural skin tones.',
    'Cool color negative': 'Cool color-negative film look, restrained cyan-blue shadows and neutral highlights.',
    'Pastel color negative': 'Pastel color-negative film look, soft peach, mint and pale blue colors, gentle contrast.',
    'Amber night halation': 'Color film at night, warm amber practical lights, red-orange highlight halation and visible grain.',
    'ILFORD HP5 Plus': 'ILFORD HP5 Plus-inspired black-and-white film, medium contrast and visible organic grain.',
    'ILFORD FP4 Plus': 'ILFORD FP4 Plus-inspired black-and-white film, fine grain and detailed tonal separation.',
    'ILFORD PAN F Plus': 'ILFORD PAN F Plus-inspired black-and-white film, very fine grain, crisp detail and strong contrast.',
    'ILFORD DELTA 100': 'ILFORD DELTA 100-inspired black-and-white film, fine grain and precise detail.',
    'ILFORD DELTA 400': 'ILFORD DELTA 400-inspired black-and-white film, restrained grain for a faster film look.',
    'ILFORD DELTA 3200': 'ILFORD DELTA 3200-inspired black-and-white low-light film look, pronounced grain.',
    'Faded print': 'Aged color print look, faded dyes, lifted blacks and soft grain.',
    'Bleach bypass': 'Bleach-bypass processing look, low color saturation and dense high-contrast tones.',
    'Cross-processed': 'Cross-processed color film look, shifted hues and strong color contrast.',
}
FILM_PALETTES = {
    'Digital clean': ['#293c42', '#618378', '#a9b0a0', '#d7c8ac', '#eee5d4'],
    'Tungsten 500T': ['#182a40', '#375d68', '#8c8470', '#cc8f54', '#efd1a2'],
    'Daylight 250D': ['#34515c', '#718a6b', '#b7ae87', '#d7b194', '#f0dfbf'],
    'Kodak VISION3 50D': ['#2c4c60', '#5b835f', '#a9b47b', '#d9b588', '#f2e6bf'],
    'Kodak VISION3 200T': ['#2a3848', '#677e77', '#b7a485', '#d5ae86', '#f0d9b7'],
    'Kodak VISION3 250D': ['#34515c', '#718a6b', '#b7ae87', '#d7b194', '#f0dfbf'],
    'Kodak VISION3 500T': ['#182a40', '#375d68', '#8c8470', '#cc8f54', '#efd1a2'],
    'Kodak EKTACOLOR PRO 160': ['#4b645c', '#9ba98a', '#c7b59a', '#e2c6b0', '#f4e5d2'],
    'Kodak EKTACOLOR PRO 400': ['#3d5b60', '#7f9877', '#c2a37c', '#d7ae98', '#f0ddc5'],
    'Kodak EKTACOLOR PRO 800': ['#353f50', '#718277', '#a88863', '#cc9b7b', '#edd0b0'],
    'Kodak EKTAR 100': ['#234b7e', '#398450', '#d6b345', '#c44939', '#f0d3a3'],
    'Fujichrome PROVIA 100F': ['#325c82', '#5b8a68', '#a1a974', '#c59078', '#e6d9b7'],
    'Fujichrome Velvia 50': ['#203b84', '#26703b', '#91a93c', '#d5483a', '#e3bc66'],
    'Warm color negative': ['#624b3c', '#b5804c', '#d4a75d', '#e5be98', '#f5e2bd'],
    'Cool color negative': ['#263c52', '#4f798c', '#87a49f', '#bdc8b9', '#e6e5d3'],
    'Pastel color negative': ['#adc8be', '#b3cadb', '#d9b8c3', '#e6c8a8', '#f4e6d6'],
    'Amber night halation': ['#1c273e', '#3d526b', '#93463b', '#d4773c', '#f3c878'],
    'Faded print': ['#565e55', '#8c977d', '#b5a58b', '#c5a89d', '#e5d3ba'],
    'Bleach bypass': ['#252b30', '#525951', '#8d8e7e', '#bbbaa6', '#e8e5d3'],
    'Cross-processed': ['#174748', '#538951', '#c4b847', '#bd4b62', '#e1cbae'],
}
for _film in FILM:
    FILM_PALETTES.setdefault(_film, ['#161616', '#494949', '#858585', '#bebebe', '#f4f4f4'])
GRADE = {
    'Natural': '',
    'Teal and orange': 'Teal shadows and warm orange highlights, cinematic color grading.',
    'Warm': 'Warm color grade, soft amber highlights.',
    'Cool': 'Cool color grade with restrained blue shadows.',
    'Muted': 'Muted saturation and gently lifted blacks.',
    'Golden honey': 'Honey-gold highlights, warm cream midtones and brown shadows.',
    'Amber and navy': 'Amber highlights against deep navy shadows.',
    'Cyan and magenta': 'Cyan shadows with magenta highlights, neon color palette.',
    'Emerald': 'Emerald greens, olive midtones and soft ivory highlights.',
    'Desert sand': 'Sand, terracotta and warm cream palette, restrained saturation.',
    'Pastel': 'Soft pastel palette, low contrast and light airy tones.',
    'Rose': 'Rose and mauve palette, subtle pink highlights.',
    'Lavender dusk': 'Lavender and indigo shadows with peach dusk highlights.',
    'Steel blue': 'Steel-blue palette, restrained saturation and silver highlights.',
    'Sepia': 'Monochrome sepia grade, brown shadows and cream highlights.',
    'Monochrome': 'Neutral black-and-white grade, no color tint.',
    'High contrast': 'Deep blacks, bright highlights and strong tonal contrast.',
    'Faded vintage': 'Faded vintage color grade, lifted blacks and softened saturation.',
    'Forest earth': 'Forest green, warm earth and muted ochre palette.',
    'Cherry red': 'Cherry red accents, burgundy shadows and pale cream highlights.',
}
PALETTES = dict(zip(GRADE, [
    ['#53634b','#899471','#c6bfa4','#d9c9ad','#7f6b59'], ['#143f49','#277c86','#82a6a0','#d69b63','#f5c088'],
    ['#5b3e41','#98574c','#c98b61','#e3b786','#f1d8b5'], ['#27364d','#405777','#6e8aa5','#a7b8ca','#d2d9de'],
    ['#555653','#777c73','#a1a18f','#bdb7a6','#d6cdbb'], ['#473528','#9f6d31','#c99a4a','#e6c47a','#fff0c6'],
    ['#101d39','#243c60','#857258','#d5a35c','#f4d9a1'], ['#113b50','#20a6b3','#70669e','#d84f9a','#f6b5d4'],
    ['#143a30','#2c6850','#78956d','#b6c7a0','#e7edcf'], ['#694939','#ad7353','#c9a27d','#e1c4a0','#f6e4c9'],
    ['#a3c9c5','#c1bedc','#e3bbca','#efd7b4','#f7efdf'], ['#50394b','#8f5d76','#be8192','#dfaeb6','#f3d9cd'],
    ['#25294f','#555280','#8c7da6','#c8a2b6','#f4c8b0'], ['#263846','#536e80','#809ba6','#b6c5c9','#e8ece9'],
    ['#35281f','#6c5038','#a58459','#d1b58a','#f0dfbf'], ['#161616','#494949','#858585','#bebebe','#f4f4f4'],
    ['#090c12','#28303c','#737b82','#c6c3b9','#fff7df'], ['#52584d','#898873','#aaa587','#c7b397','#ead7b8'],
    ['#243a2a','#54694a','#85734e','#b39761','#d5c5a0'], ['#321a26','#792e3e','#ba3549','#e98388','#f6dfc8'],
]))
RATIOS = {'5:4': (960, 768), '4:5': (768, 960), '16:9': (1024, 576), '21:9': (1344, 576), '1:1': (768, 768), '9:16': (576, 1024), '4:3': (896, 672), '3:4': (672, 896), '3:2': (960, 640), '2:3': (640, 960)}


def legacy_camera(data):
    """Translate original combined camera choices when opening older shots."""
    lens = data.get('lens', 'Natural perspective')
    return dict(lens_type='Anamorphic' if lens.startswith('Anamorphic') else 'Spherical / normal',
                sensor='Medium format' if lens.startswith('Large format') else next(iter(SENSORS)),
                focal_length=24 if lens.startswith('Wide') else 85 if lens.startswith('Portrait') else 50)
