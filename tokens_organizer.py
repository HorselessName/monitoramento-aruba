import os
import configparser

# Get the directory of the script file
base_dir = os.path.dirname(os.path.abspath(__file__))

# Define the paths
ini_file = os.path.join(base_dir, 'tokens_aruba.ini')  # Ensure we read the correct INI file
output_folder = os.path.join(base_dir, 'aruba_tokens')  # Output folder for token files

# Create the output folder if it doesn't exist
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Read the INI file
config = configparser.ConfigParser()
config.read(ini_file)

# Loop through each section and write to individual files
for section in config.sections():
    # Create a file for each section inside the aruba_tokens folder
    section_file_path = os.path.join(output_folder, section)

    with open(section_file_path, 'w') as section_file:
        # Write the section header
        section_file.write(f'[{section}]\n')

        # Write all key-value pairs under the section
        for key, value in config.items(section):
            section_file.write(f'{key} = {value}\n')

print("Sections have been successfully written to individual files.")
