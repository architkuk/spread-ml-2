#!/usr/bin/env python3
import os
import re
import argparse

def minify_code(content):
    """
    Removes unnecessary whitespace from the provided code content.
    
    This function:
    - Strips leading and trailing whitespace.
    - Replaces any sequence of whitespace (spaces, tabs, newlines) with a single space.
    
    This results in a compact version of the code.
    """
    return re.sub(r'\s+', ' ', content.strip())

def process_files(directory, output_file, extensions):
    """
    Recursively processes each file in the given directory (and subdirectories)
    that matches one of the specified extensions.
    
    For each file:
    - Reads its content.
    - Minifies the content using the minify_code function.
    - Appends the relative file path and the minified content to the output.
    
    Finally, the output is written to the specified output file.
    """
    output_lines = []
    files_processed = 0

    # Walk through directory recursively
    for root, dirs, files in os.walk(directory):
        for file_name in files:
            if any(file_name.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file_name)
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                minified = minify_code(content)
                # Compute relative file path to show directory structure
                relative_path = os.path.relpath(file_path, directory)
                output_lines.append(relative_path)
                output_lines.append(minified)
                output_lines.append('')  # Blank line as separator
                files_processed += 1

    with open(output_file, 'w', encoding='utf-8') as out_file:
        out_file.write('\n'.join(output_lines))
    
    print(f"Processed {files_processed} file(s). Output written to '{output_file}'.")

def main():
    parser = argparse.ArgumentParser(
        description="Compress code files by removing unnecessary spaces and generate a formatted text file."
    )
    parser.add_argument('directory', type=str, help="Directory containing the code files")
    parser.add_argument('output', type=str, help="Output text file")
    parser.add_argument(
        '--ext', nargs='+', default=['.py', '.js', '.css', '.html'],
        help="File extensions to process (default: .py, .js, .css, .html)"
    )
    args = parser.parse_args()
    process_files(args.directory, args.output, args.ext)

if __name__ == '__main__':
    main()
