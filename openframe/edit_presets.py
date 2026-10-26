"""Optional Qwen image-edit shortcuts; custom details remain a separate prompt."""
PRESETS = {
    'character-sheet': dict(label='Character sheet', hint='Optional: specific views, expressions or details to include…', prompt='Create a clean character reference sheet of the character from <image1>. Show three separate full-body views side by side: front, side profile and back, plus a close-up of the face. Use a seamless white studio background, consistent scale and even lighting. Preserve the exact identity, body proportions, distinctive features, clothing, accessories and rendering medium from the source. Keep the whole silhouette inside each view, with clear space between views. No labels or text.'),
    'a-pose': dict(label='A-pose', hint='Optional: hand position, outfit detail or another adjustment…', prompt='Show the character from <image1> in a neutral front-facing full-body A-pose: standing upright, legs slightly apart, arms straight and angled down about 45 degrees from the shoulders, hands relaxed. Show the complete figure, head to feet, with comfortable margins. Preserve the exact identity, anatomy, proportions, outfit and rendering medium. Repose the same character; do not redesign them.'),
    'front': dict(label='Front view', hint='Optional: expression or details visible from the front…', prompt='Change the view of the character from <image1> to a straight-on front view at eye level. Show the complete standing figure from head to feet, facing the camera with shoulders and hips square to the lens. Preserve the exact identity, distinctive proportions, clothing, accessories and rendering medium.'),
    'side': dict(label='Side view', hint='Optional: left or right side, posture or visible details…', prompt='Change the view of the character from <image1> to a true 90-degree side profile, facing left unless otherwise specified. Show the complete standing figure from head to feet. The shoulders and hips are viewed from the side, not in a three-quarter view. Preserve the exact identity, proportions, clothing, accessories and rendering medium.'),
    'back': dict(label='Back view', hint='Optional: details on the back of the outfit or hair…', prompt='Show a full-body rear view of the character from <image1>, turned 180 degrees away from the camera, from head to feet. The back of the head, outfit and legs face the camera; do not turn the head toward the viewer. Preserve the same identity, body proportions, clothing design, accessories and rendering medium.'),
    'face': dict(label='Face close-up', hint='Optional: a heart tattoo on the face, expression or other detail…', prompt='Reframe the character from <image1> as a close-up of the face, with the entire head, hair and chin visible and a little of the shoulders. Keep the eyes, facial features and skin details clear. Preserve the exact facial identity, unusual proportions, hairstyle, existing markings and rendering medium. Do not normalize exaggerated features.'),
    'legs': dict(label='Legs close-up', hint='Optional: footwear, fabric or a detail on the legs…', prompt='Create a close-up focused on the legs of the character from <image1>, framed from the upper thighs through the feet. Keep both legs and footwear fully readable, with space around the feet. Preserve the exact anatomy, proportions, outfit materials, colors, markings and rendering medium.'),
    'torso': dict(label='Torso close-up', hint='Optional: clothing, chest details or accessories…', prompt='Create a close-up of the torso of the character from <image1>, framed from the base of the neck to the hips. Show the chest, waist, clothing construction and relevant accessories clearly. Preserve the exact body proportions, outfit design, materials, markings and rendering medium.'),
    'hand': dict(label='Hand close-up', hint='Optional: which hand, gesture, jewelry or markings…', prompt='Create a detailed close-up of one hand of the character from <image1>, including the wrist and a little forearm. Show the complete hand and fingertips clearly without cropping. Preserve the character-specific hand anatomy, skin or glove material, proportions, markings, jewelry and rendering medium. Do not turn a nonhuman or exaggerated hand into a generic human hand.'),
}


def choices():
    return [dict(id=key, label=value['label'], hint=value['hint']) for key, value in PRESETS.items()]


def validate(value, source):
    if not isinstance(value, str) or value and value not in PRESETS:
        raise ValueError('Unknown image edit preset.')
    if value and not source:
        raise ValueError('Choose an image to edit before using an edit preset.')
    return value


def prompt(settings):
    preset = PRESETS.get(settings.get('edit_preset')) if settings.get('edit_source') else None
    details = settings.get('prompt', '').strip()
    if not preset:
        return details
    return preset['prompt'] + ('\nAdditional requested changes: ' + details if details else '')
