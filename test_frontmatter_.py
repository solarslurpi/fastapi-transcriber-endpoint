


# Sample text with potential newlines embedded
description_text = '''description:  I am really enjoying using the Bluelab Pulse Meter in my grow room! I go over how it works as well as some potential uses for living soil growers.

We currently have it available on our website for the best price online if anyone wants to try it. https://www.kisorganics.com/products/bluelab-pulse-multimedia-ec-mc-meter?_pos=1&_sid=cfeeacdab&_ss=r
'''



def build_frontmatter():
    metadata = '---\n'

    metadata += "YouTube URL: https://www.youtube.com/abscideve\n"
    tags = ["calcium", "potassium"]
    formatted_tags = ' '.join(f'#{tag}' for tag in tags)
    metadata += f"Tags: {formatted_tags}\n"
    description_text = '''description:  I am really enjoying using the Bluelab Pulse Meter in my grow room! I go over how it works as well as some potential uses for living soil growers.

We currently have it available on our website for the best price online if anyone wants to try it. https://www.kisorganics.com/products/bluelab-pulse-multimedia-ec-mc-meter?_pos=1&_sid=cfeeacdab&_ss=r   https://www.youtube.com/abscideve   \n'''
    description_text = replace_newlines_with_spaces(description_text)
    metadata += description_text
    metadata += '\n---\n\n'
    return metadata

metadata = build_frontmatter()
file_path = r'G:\My Drive\Audios_To_Knowledge\knowledge\AskGrowBuddy\transcripts\test.md'
with open(file_path, 'w', encoding='utf-8') as file:
    file.writelines(metadata)