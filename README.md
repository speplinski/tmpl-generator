# TMPL Generator

TMPL Generator is a Python-based system for processing and managing image masks, specifically designed for handling both static masks and dynamic sequences of panoramic images.

## Features

- Processing of both static masks and dynamic sequence frames
- Real-time monitoring of state changes
- Automatic mask combining with proper layering
- Memory usage monitoring
- Support for multiple image formats (PNG, BMP)
- Configurable mask mappings
- Dynamic configuration based on directory content

## Requirements

- Python 3.7 or higher
- Dependencies:
  - numpy
  - opencv-python
  - psutil

## Installation

1. Clone the repository:
```bash
git clone https://github.com/speplinski/tmpl-generator.git
cd tmpl-generator
```

2. Install the package:
```bash
pip install -e .
```

## Project Structure

```
tmpl_generator/
├── landscapes/          # Directory for panorama data
├── results/            # Output directory for processed masks
├── mask_mapping.json   # Configuration file for mask mappings
└── tmpl.log           # State monitoring log file
```

## Configuration

The system uses a JSON configuration file (`mask_mapping.json`) to define mask mappings. Example configuration:

```json
{
    "P1100142": {
        "static_masks": {
            "10":  1,
            "50":  3,
            "70":  10,
            "90":  4,
            "130": 5,
            "245": 8
        },
        "sequence_masks": {
            "35":  2,
            "170": 6
        }
    }
}
```

## Downloading Data

Use the provided script to download and extract the landscape data:

```bash
chmod +x download_landscapes.sh
./download_landscapes.sh
```

Requirements for the download script:
- wget or curl
- 7zip (p7zip-full)

## Usage

Run the main program with a panorama ID:

```bash
python main.py P1100142
```

The system will:
1. Load static masks and sequence frames
2. Monitor the state file (tmpl.log) for updates
3. Process and combine masks based on the current state
4. Save results to the output directory

## Output

- Processed masks are saved as BMP files in the `results` directory
- Each result is numbered sequentially
- Output images maintain consistent dimensions (3840x1280)
- Pixel values correspond to configured indexes

## Memory Management

The system includes built-in memory monitoring that provides:
- Initial memory status
- Memory usage after loading masks
- Memory status during processing
- Total system memory information

## Error Handling

The system includes comprehensive error handling for:
- Missing files or directories
- Invalid mask formats
- Incorrect dimensions
- Non-binary values
- Invalid sequence numbers
- State file reading errors