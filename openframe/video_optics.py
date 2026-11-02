"""Visible photographic cues for video presets; no claim of physical simulation."""
CAMERA = {
 '8mm film': 'Small-gauge 8mm film appearance: visibly coarse organic grain, soft fine detail, slight frame weave and warm bleeding highlights. The texture is present from the opening frame and remains consistent.',
 '35mm film': '35mm motion-picture film appearance: fine visible organic grain, gentle highlight roll-off, rich midtones and slight film softness, with stable framing. Preserve readable faces and materials.',
 'Modern digital': 'Modern digital cinema appearance: clean stable image, sharply resolved fine detail, neutral color separation and smooth shadow gradients, without coarse film grain, frame weave or blooming highlights.',
 'DV camcorder': 'Early consumer DV camcorder appearance: low-resolution video detail, hard electronic edge sharpening, clipped bright areas, chroma softness and slightly noisy shadows. The scene remains live-action rather than an illustration.'}
LENSES = {
 'Clean': 'Neutral rectilinear optics: straight architectural lines, natural facial proportions, clear edges and restrained flare. Keep color neutral and highlights localized.',
 'Sharp': 'Crisp modern optics: eyelashes, hair strands, fabric weave and in-focus architectural edges are distinctly resolved with strong fine-detail contrast. Sharpness follows the selected focus depth; distant bokeh need not be sharp.',
 'Anamorphic': 'Anamorphic optical character: out-of-focus light points form vertically elongated oval bokeh; bright light sources create thin horizontal flares. Gentle edge stretching and cinematic subject separation are visible without stretching faces.',
 'Vintage anamorphic': 'Vintage anamorphic optics: pronounced oval background bokeh, soft smeared outer edges, warm horizontal highlight streaks and gentle veiling flare. Keep the central subject readable; the effect is optical texture, not camera travel.',
 'Warm vintage': 'Warm vintage glass: amber highlight bloom, gentle fine-detail softness, slightly lifted shadows and reduced contrast near bright light sources. Keep skin believable rather than covering the entire image in an orange tint.',
 'Halation vintage': 'Vintage color-negative film response. A clearly visible, thin, softly feathered reddish fringe closely follows the boundaries of existing bright highlights against darker surfaces. The fringe stays attached to those highlight edges, with a small diffuse light spread into the adjacent image. Fine organic grain, gentle highlight roll-off and softly lifted midtones complete the film texture. This is an optical artifact within the recorded photograph, not a physical object or event in the scene. Retain the existing light sources, objects and atmosphere.'}
SENSORS = {
 'Full frame · 36 × 24mm': 'Full-frame photographic look: natural perspective with clear separation between a focused subject and softly receding surroundings; rich tonal transitions and readable fine detail.',
 'Super 35 · cinema': 'Super 35 cinema look: a clearly readable subject and moderately detailed surroundings, fine film-like texture, controlled contrast and smooth highlights.',
 '35mm motion picture': '35mm motion-picture appearance: restrained organic grain, soft highlight roll-off and clear midtone detail, with coherent photographic depth.',
 'APS-C': 'APS-C photographic look: relatively broad depth of field at comparable framing, with both the main subject and nearby surroundings readable, clean detail and modest background separation.',
 'Micro Four Thirds': 'Small-sensor Micro Four Thirds photographic look: broad depth of field at comparable framing and clear surrounding detail, with less background blur unless a shallow aperture is explicitly selected.',
 'Super 16': 'Super 16 film appearance: conspicuous fine-to-medium organic grain, gently softened fine detail, intimate texture, broad readable focus and softly blooming highlights.',
 'Medium format': 'Medium-format photographic look: exceptionally fine in-focus textures, smooth tonal gradients, strong subject separation and softly receding background detail.',
 '65mm / 70mm cinema': 'Large-format 65/70mm cinema appearance: exceptionally detailed faces and materials, smooth tonal transitions, very fine grain and clear subject separation across a spacious image.',
 'IMAX · 15/70': 'IMAX 15/70 photographic appearance: expansive environmental detail, exceptionally fine textures across the in-focus image, very fine grain and smooth highlights with a strong sense of spatial scale.',
 'Large format · 4 × 5': 'Large-format view-camera appearance: extraordinarily resolved in-focus surfaces, smooth tonal gradients and a clearly defined focus plane with gently receding depth. Keep architecture coherent.'}

def aperture(value):
 number=float(value.removeprefix('f/'))
 if number<2.8:
  cue='Extremely shallow depth of field: the chosen focal subject is sharply resolved while surfaces in front of and behind its focus plane dissolve into a conspicuous creamy blur. Distant light points form large soft bokeh circles.'
 elif number<8:
  cue='Moderate depth of field: the focal subject and nearby details remain readable, with gentle progressive softening farther behind it. Keep some environment recognizable.'
 else:
  cue='Deep focus: the subject, nearby foreground surfaces and distant architectural edges remain distinctly readable together, with crisp material detail rather than large blurred bokeh.'
 return f'Aperture {value}. {cue} Maintain correct exposure; aperture changes focus depth rather than making the image brighter or darker. An explicitly selected sensor look must not override this focus depth.'

def focal(value):
 mm=int(value.removesuffix('mm'))
 if mm<=20:
  cue='An unmistakably ultra-wide lens with exaggerated near-to-far perspective. Close surfaces loom large while distant ones recede sharply; features near the lens gain pronounced perspective distortion and the edges stretch outward. A close-up may stay close: emphasize the expanded depth and wide-lens facial perspective instead of automatically changing it into a distant wide shot.'
 elif mm<=35:
  cue='A wide lens with clear spatial depth, moderate near-to-far size differences and a generous view around the subject. Let camera distance and the requested composition determine how much of the subject is visible.'
 elif mm<=65:
  cue='Natural standard-lens perspective, balanced subject proportions and a familiar sense of distance between foreground and background.'
 elif mm<=105:
  cue='Short-telephoto perspective with gentle compression, flattering facial proportions and background forms appearing larger and closer behind the subject.'
 else:
  cue='Long-telephoto perspective with strongly compressed distances and enlarged background forms packed close behind the subject. The visible environment is a narrow slice, with flattened depth and strong separation between subject and background planes.'
 return f'Photographed with a {value} lens. {cue} This optical appearance is present from the opening frame. Framing and camera movement remain independent creative choices.'
