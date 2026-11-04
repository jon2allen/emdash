#!/bin/bash
# pull_melville.sh - Download Herman Melville's works and non-Melville classics from Project Gutenberg
# Usage: ./pull_melville.sh

# Create melville directory if it doesn't exist
mkdir -p melville

# Check if wget is available
hash wget 2>/dev/null || {
    echo "Error: wget is not installed. Please install wget and try again."
    exit 1
}

echo "Downloading Herman Melville's works..."

# Herman Melville's works
wget -q -O melville/moby_dick_full.txt https://www.gutenberg.org/cache/epub/2701/pg2701.txt
wget -q -O melville/omoo.txt https://www.gutenberg.org/cache/epub/4045/pg4045.txt
wget -q -O melville/bartleby_the_scrivener.txt https://www.gutenberg.org/files/11231/11231-0.txt
wget -q -O melville/typee.txt https://www.gutenberg.org/ebooks/1900.txt.utf-8
wget -q -O melville/white_jacket.txt https://www.gutenberg.org/ebooks/10712.txt.utf-8
wget -q -O melville/pierre.txt https://www.gutenberg.org/cache/epub/34970/pg34970.txt
wget -q -O melville/the_confidence_man.txt https://www.gutenberg.org/ebooks/21816.txt.utf-8
wget -q -O melville/billy_budd.txt https://www.gutenberg.org/ebooks/2450.txt.utf-8
wget -q -O melville/benito_cereno.txt https://www.gutenberg.org/ebooks/15859.txt.utf-8

echo "Downloading non-Melville classics..."

# Non-Melville works
echo "Downloading A Tale of Two Cities by Charles Dickens..."
wget -q -O melville/a_tale_of_two_cities.txt https://www.gutenberg.org/ebooks/98.txt.utf-8

echo "Downloading The Adventures of Huckleberry Finn by Mark Twain..."
wget -q -O melville/huckleberry_finn.txt https://www.gutenberg.org/ebooks/76.txt.utf-8

echo "Downloading Frankenstein by Mary Shelley..."
wget -q -O melville/frankenstein.txt https://www.gutenberg.org/ebooks/84.txt.utf-8

echo "All downloads completed successfully!"
echo "Files are saved in the 'melville' directory."