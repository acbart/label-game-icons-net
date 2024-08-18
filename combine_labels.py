import os
import argparse
import csv
import json

DEFAULT_LABEL_DIRECTORY = "labels/"
DEFAULT_OUTPUT_DIRECTORY = "dist/"


def combine_labels(label_directory: str, output_directory: str):
    """
    Combine all the labels in the label directory into a single output file.
    """
    # Get all the label files
    label_files = [file for file in os.listdir(label_directory) if file.endswith('.csv')]
    if not label_files:
        print(f"No label files found in {label_directory}")
        return
    
    # Get all the labels
    all_labels = []
    for label_file in label_files:
        with open(os.path.join(label_directory, label_file), 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip the header
            for row in reader:
                all_labels.append(row)

    # Open the CSV output file
    output_file = os.path.join(output_directory, 'all_labels.csv')
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['icon', 'text'])

        # Write all the labels to the output file
        for label in all_labels:
            writer.writerow([label[0], label[1]])
    
    # Open the JSON output file
    output_file = os.path.join(output_directory, 'all_labels.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json_output = {}
        for label in all_labels:
            icon = label[0]
            text = label[1]
            if icon not in json_output:
                json_output[icon] = []
            json_output[icon].append(text)
        json.dump(json_output, f, indent=4)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Combine label files into a single output file.')
    parser.add_argument('--label_directory', type=str, help='The directory containing the label files. Defaults to "labels/".', default=DEFAULT_LABEL_DIRECTORY)
    parser.add_argument('--output_file', type=str, help='The output file to write the combined labels to. Defaults to "dist/all_labels.csv".', default=DEFAULT_OUTPUT_DIRECTORY)
    args = parser.parse_args()

    combine_labels(args.label_directory, args.output_file)