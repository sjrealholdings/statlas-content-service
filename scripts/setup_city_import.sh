#!/bin/bash

echo "🚀 Setting up City Import Environment"
echo "======================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7+ first."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if pip3 is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip3 first."
    exit 1
fi

echo "✅ pip3 found: $(pip3 --version)"

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip3 install -r requirements_cities.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Check if shapefile exists
SHAPEFILE_PATH="../city data/stanford-yk247bg4748-shapefile/yk247bg4748.shp"
if [ -f "$SHAPEFILE_PATH" ]; then
    echo "✅ Stanford shapefile found"
else
    echo "❌ Stanford shapefile not found at: $SHAPEFILE_PATH"
    echo "   Please ensure the shapefile is in the correct location"
    exit 1
fi

echo ""
echo "🎯 Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Update Firestore credentials in db_config.py"
echo "2. Ensure Firebase project is accessible"
echo "3. Run: python3 import_cities.py"
echo ""
echo "📚 See README_CITY_IMPORT.md for detailed instructions"
