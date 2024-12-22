from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os

def text_to_handwritten_image(text, upload_folder='static/uploads', font_path='satisfy.ttf', image_size=(1240, 1745), font_size=60):
    # Create an image
    img = Image.new('RGB', image_size, color=(175, 175, 187))
    d = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        return "Font file not found."

    # Draw text with word wrapping
    draw_text_with_wrapping(d, text, font, position=(50, 100), max_width=image_size[0] - 100)
    
    # Save the image
    img_path = os.path.join(upload_folder, 'handwritten_image.png')
    img.save(img_path)

    return img_path

def draw_text_with_wrapping(draw, text, font, position, max_width):
    words = text.split(' ')
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + word + ' '
        text_bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = text_bbox[2] - text_bbox[0]

        if text_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line.strip())
            current_line = word + ' '

    if current_line:
        lines.append(current_line.strip())

    y = position[1]
    for line in lines:
        draw.text((position[0], y), line, font=font, fill=(23, 102, 192))
        line_bbox = draw.textbbox((0, 0), line, font=font)
        line_height = line_bbox[3] - line_bbox[1]
        y += line_height
