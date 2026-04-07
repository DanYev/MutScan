#!/bin/bash

directory=systems
pattern=md.log

max_path_length=40  # Set the maximum length for the path

# Function to truncate or pad the path
truncate_or_pad_path() {
    local path="$1"
    local max_length="$2"

    if [ ${#path} -gt $max_length ]; then
        # Truncate and keep the last part of the path after truncation
        echo "...${path: -$(($max_length - 3))}"  # Keep the last part of the path and prefix with '...'
    else
        # Pad the path with spaces to make it exactly $max_length characters
        printf "%-${max_length}s" "$path"
    fi
}

# Find all files in the directory matching the pattern recursively
echo "Checking out $directory"

find "$directory" -type f -name "$pattern" | while read -r file; do
    # Get the relative path to the file
    relative_path=$(realpath --relative-to="$directory" "$file")

    # Truncate or pad the path to ensure it's exactly $max_path_length characters
    truncated_or_padded_path=$(truncate_or_pad_path "$relative_path" "$max_path_length")

    # Use awk to find the last occurrence of "Time" and print the next line
    awk '/Time/ {line=NR} NR==line+1 {next_line=$0} END {if (line) print truncated_or_padded_path ": " next_line}' truncated_or_padded_path="$truncated_or_padded_path" "$file"

done
